import { describe, it, expect, vi, beforeEach } from 'vitest';

/**
 * Tests for the Cloudflare Pages Function: check-account.js
 *
 * The function fetches Instagram profile HTML pages and parses
 * og:* meta tags to determine account status and profile picture.
 * On 429, it falls back to a residential proxy if configured.
 */

// Mock cloudflare:sockets before importing the handler
const mockConnect = vi.fn();
vi.mock('cloudflare:sockets', () => ({
  connect: mockConnect,
}));

// Import the handler
const { onRequestGet } = await import('../functions/api/check-account.js');

function createContext(searchParams = '', env = {}) {
  return {
    request: {
      url: `https://unfollowlens.com/api/check-account${searchParams}`,
    },
    env,
  };
}

const SCRAPER_ENV = {
  SCRAPER_API_KEY: 'test-api-key-123',
};

const PROXY_ENV = {
  PROXY_HOST: 'gw.dataimpulse.com',
  PROXY_PORT: '823',
  PROXY_USER: 'testuser__cr.us',
  PROXY_PASS: 'testpass',
};

async function parseResponse(response) {
  const body = await response.json();
  return { status: response.status, body, headers: Object.fromEntries(response.headers.entries()) };
}

function mockHtmlResponse(ogImage, ogTitle, ogDescription) {
  const parts = [];
  parts.push('<html><head>');
  if (ogTitle) parts.push(`<meta property="og:title" content="${ogTitle}">`);
  if (ogImage) parts.push(`<meta property="og:image" content="${ogImage}">`);
  if (ogDescription) parts.push(`<meta property="og:description" content="${ogDescription}">`);
  parts.push('</head><body></body></html>');
  return parts.join('\n');
}

function stubFetchHtml(html, status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      status,
      text: () => Promise.resolve(html),
    }),
  );
}

/**
 * Creates a mock TCP socket that simulates the HTTP forward proxy flow:
 * connect → GET (full URL) → proxy returns HTTP response
 */
function createMockProxySocket(httpResponseText) {
  const encoder = new TextEncoder();

  let readCount = 0;
  return {
    writable: {
      getWriter: () => ({
        write: vi.fn().mockResolvedValue(undefined),
        releaseLock: vi.fn(),
      }),
    },
    readable: {
      getReader: () => ({
        read: vi.fn().mockImplementation(() => {
          if (readCount === 0) {
            readCount++;
            return Promise.resolve({
              value: encoder.encode(httpResponseText),
              done: false,
            });
          }
          return Promise.resolve({ value: undefined, done: true });
        }),
      }),
    },
  };
}

function buildHttpResponse(statusCode, body) {
  return `HTTP/1.0 ${statusCode} OK\r\nContent-Type: text/html\r\n\r\n${body}`;
}

describe('check-account API', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockConnect.mockReset();
  });

  describe('input validation', () => {
    it('returns 400 when username is missing', async () => {
      const response = await onRequestGet(createContext(''));
      const { status, body } = await parseResponse(response);

      expect(status).toBe(400);
      expect(body.error).toBe('Missing or invalid username parameter');
    });

    it('returns 400 when username is empty string', async () => {
      const response = await onRequestGet(createContext('?username='));
      const { status, body } = await parseResponse(response);

      expect(status).toBe(400);
      expect(body.error).toBe('Missing or invalid username parameter');
    });

    it('returns 400 for invalid username format', async () => {
      const response = await onRequestGet(createContext('?username=test<script>'));
      const { status, body } = await parseResponse(response);

      expect(status).toBe(400);
      expect(body.username).toBe('test<script>');
      expect(body.error).toBe('Invalid username format');
      expect(body.accessible).toBe(false);
    });

    it('returns 400 for username with spaces', async () => {
      const response = await onRequestGet(createContext('?username=test%20user'));
      const { status, body } = await parseResponse(response);

      expect(status).toBe(400);
      expect(body.error).toBe('Invalid username format');
    });

    it('returns 400 for username exceeding 30 characters', async () => {
      const longName = 'a'.repeat(31);
      const response = await onRequestGet(createContext(`?username=${longName}`));
      const { status, body } = await parseResponse(response);

      expect(status).toBe(400);
      expect(body.error).toBe('Username must be 1-30 characters');
    });

    it('accepts username at exactly 30 characters', async () => {
      const maxName = 'a'.repeat(30);
      const html = mockHtmlResponse(
        'https://cdn.instagram.com/pic.jpg',
        `User (&#064;${maxName})`,
        '100 Followers',
      );
      stubFetchHtml(html);

      const response = await onRequestGet(createContext(`?username=${maxName}`));
      const { status, body } = await parseResponse(response);

      expect(status).toBe(200);
      expect(body.username).toBe(maxName);
    });

    it('accepts valid usernames with dots and underscores', async () => {
      const html = mockHtmlResponse(
        'https://cdn.instagram.com/pic.jpg',
        'Test (&#064;test.user_name) &#x2022; Instagram',
        '100 Followers, 50 Following',
      );
      stubFetchHtml(html);

      const response = await onRequestGet(createContext('?username=test.user_name'));
      const { status, body } = await parseResponse(response);

      expect(status).toBe(200);
      expect(body.username).toBe('test.user_name');
      expect(body.status).toBe('active');
    });
  });

  describe('Instagram HTML page parsing', () => {
    it('returns active status for public user with profile pic', async () => {
      const html = mockHtmlResponse(
        'https://cdn.instagram.com/profile.jpg',
        'Instagram (&#064;instagram) &#x2022; Instagram photos and videos',
        '699M Followers, 194 Following, 8324 Posts',
      );
      stubFetchHtml(html);

      const response = await onRequestGet(createContext('?username=instagram'));
      const { status, body } = await parseResponse(response);

      expect(status).toBe(200);
      expect(body).toEqual({
        username: 'instagram',
        status: 'active',
        accessible: true,
        is_private: false,
        profile_pic_url: 'https://cdn.instagram.com/profile.jpg',
      });
    });

    it('detects private accounts from og:description', async () => {
      const html = mockHtmlResponse(
        'https://cdn.instagram.com/private.jpg',
        'Private User (&#064;private_user) &#x2022; Instagram',
        'This account is private',
      );
      stubFetchHtml(html);

      const response = await onRequestGet(createContext('?username=private_user'));
      const { status, body } = await parseResponse(response);

      expect(status).toBe(200);
      expect(body.is_private).toBe(true);
      expect(body.accessible).toBe(true);
      expect(body.profile_pic_url).toBe('https://cdn.instagram.com/private.jpg');
    });

    it('detects Korean private account text', async () => {
      const html = mockHtmlResponse(
        'https://cdn.instagram.com/kr.jpg',
        'User (&#064;kr_user)',
        '비공개 계정입니다',
      );
      stubFetchHtml(html);

      const response = await onRequestGet(createContext('?username=kr_user'));
      const { body } = await parseResponse(response);

      expect(body.is_private).toBe(true);
    });

    it('returns deleted_or_restricted when og tags are missing', async () => {
      const html = '<html><head><title>Instagram</title></head><body></body></html>';
      stubFetchHtml(html);

      const response = await onRequestGet(createContext('?username=gone_user'));
      const { status, body } = await parseResponse(response);

      expect(status).toBe(200);
      expect(body.status).toBe('deleted_or_restricted');
      expect(body.accessible).toBe(false);
    });

    it('returns deleted_or_restricted when og:image is missing', async () => {
      const html = mockHtmlResponse(null, 'Some Title', 'Some description');
      stubFetchHtml(html);

      const response = await onRequestGet(createContext('?username=no_image_user'));
      const { body } = await parseResponse(response);

      expect(body.status).toBe('deleted_or_restricted');
      expect(body.accessible).toBe(false);
    });

    it('returns deleted for 404 response', async () => {
      stubFetchHtml('', 404);

      const response = await onRequestGet(createContext('?username=deleted_user'));
      const { status, body } = await parseResponse(response);

      expect(status).toBe(200);
      expect(body.status).toBe('deleted');
      expect(body.accessible).toBe(false);
    });

    it('returns unknown for unexpected status codes', async () => {
      stubFetchHtml('', 500);

      const response = await onRequestGet(createContext('?username=server_error'));
      const { status, body } = await parseResponse(response);

      expect(status).toBe(200);
      expect(body.status).toBe('unknown');
      expect(body.accessible).toBe(true);
      expect(body.error).toBe('HTTP 500');
    });

    it('returns error when fetch throws', async () => {
      vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network timeout')));

      const response = await onRequestGet(createContext('?username=timeout_user'));
      const { status, body } = await parseResponse(response);

      expect(status).toBe(200);
      expect(body.status).toBe('error');
      expect(body.accessible).toBe(true);
      expect(body.error).toBe('Network timeout');
    });

    it('decodes HTML entities in profile_pic_url', async () => {
      const html = mockHtmlResponse(
        'https://cdn.instagram.com/pic.jpg?w=100&amp;h=100&amp;quality=80',
        'User (&#064;testuser)',
        'Description',
      );
      stubFetchHtml(html);

      const response = await onRequestGet(createContext('?username=testuser'));
      const { body } = await parseResponse(response);

      expect(body.profile_pic_url).toBe('https://cdn.instagram.com/pic.jpg?w=100&h=100&quality=80');
    });

    it('treats public account without private text as not private', async () => {
      const html = mockHtmlResponse(
        'https://cdn.instagram.com/public.jpg',
        'Public User (&#064;public_user)',
        '1000 Followers, 500 Following, 200 Posts',
      );
      stubFetchHtml(html);

      const response = await onRequestGet(createContext('?username=public_user'));
      const { body } = await parseResponse(response);

      expect(body.is_private).toBe(false);
    });
  });

  describe('response headers', () => {
    it('includes no-cache headers on all responses', async () => {
      const response = await onRequestGet(createContext(''));
      const cacheControl = response.headers.get('Cache-Control');

      expect(cacheControl).toBe('no-store, no-cache, must-revalidate');
    });

    it('includes no-cache headers on success response', async () => {
      const html = mockHtmlResponse(
        'https://cdn.instagram.com/pic.jpg',
        'User (&#064;test)',
        'Description',
      );
      stubFetchHtml(html);

      const response = await onRequestGet(createContext('?username=test'));
      const cacheControl = response.headers.get('Cache-Control');

      expect(cacheControl).toBe('no-store, no-cache, must-revalidate');
    });
  });

  describe('request to Instagram', () => {
    it('fetches Instagram profile page with Googlebot user agent', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        status: 200,
        text: () =>
          Promise.resolve(
            mockHtmlResponse(
              'https://cdn.instagram.com/pic.jpg',
              'User (&#064;testuser)',
              'Description',
            ),
          ),
      });
      vi.stubGlobal('fetch', mockFetch);

      await onRequestGet(createContext('?username=testuser'));

      expect(mockFetch).toHaveBeenCalledOnce();
      const [url, options] = mockFetch.mock.calls[0];

      expect(url).toBe('https://www.instagram.com/testuser/');
      expect(options.headers['User-Agent']).toContain('Googlebot');
      expect(options.headers['Accept']).toBe('text/html');
    });

    it('encodes username in profile URL', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        status: 200,
        text: () =>
          Promise.resolve(
            mockHtmlResponse('https://cdn.instagram.com/pic.jpg', 'User', 'Description'),
          ),
      });
      vi.stubGlobal('fetch', mockFetch);

      await onRequestGet(createContext('?username=user.name'));

      const [url] = mockFetch.mock.calls[0];
      expect(url).toBe('https://www.instagram.com/user.name/');
    });
  });

  describe('username sanitization', () => {
    it('trims whitespace from username', async () => {
      const html = mockHtmlResponse(
        'https://cdn.instagram.com/pic.jpg',
        'Instagram (&#064;instagram)',
        'Description',
      );
      stubFetchHtml(html);

      const response = await onRequestGet(createContext('?username=%20instagram%20'));
      const { body } = await parseResponse(response);

      expect(body.username).toBe('instagram');
    });
  });

  describe('429 handling without proxy', () => {
    it('returns unknown on 429 when proxy is not configured', async () => {
      const mockFetch = vi
        .fn()
        .mockResolvedValue({ status: 429, text: () => Promise.resolve('') });
      vi.stubGlobal('fetch', mockFetch);

      const response = await onRequestGet(createContext('?username=blocked_user'));
      const { status, body } = await parseResponse(response);

      expect(mockFetch).toHaveBeenCalledOnce();
      expect(status).toBe(200);
      expect(body.status).toBe('unknown');
      expect(body.error).toBe('HTTP 429');
    });

    it('does not retry on non-429 errors', async () => {
      const mockFetch = vi
        .fn()
        .mockResolvedValue({ status: 503, text: () => Promise.resolve('') });
      vi.stubGlobal('fetch', mockFetch);

      const response = await onRequestGet(createContext('?username=error503'));
      const { status, body } = await parseResponse(response);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(status).toBe(200);
      expect(body.status).toBe('unknown');
      expect(body.error).toBe('HTTP 503');
    });

    it('does not call proxy when direct fetch succeeds', async () => {
      const html = mockHtmlResponse(
        'https://cdn.instagram.com/pic.jpg',
        'User (&#064;directuser)',
        '100 Followers',
      );
      stubFetchHtml(html);

      const response = await onRequestGet(createContext('?username=directuser', PROXY_ENV));
      const { body } = await parseResponse(response);

      expect(body.status).toBe('active');
      expect(mockConnect).not.toHaveBeenCalled();
    });
  });

  describe('429 scraping API fallback', () => {
    it('falls back to scraping API on 429 and returns active account', async () => {
      const html = mockHtmlResponse(
        'https://cdn.instagram.com/api_pic.jpg',
        'User (&#064;apiuser) &#x2022; Instagram',
        '200 Followers, 50 Following',
      );
      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce({ status: 429, text: () => Promise.resolve('') })
        .mockResolvedValueOnce({ status: 200, text: () => Promise.resolve(html) });
      vi.stubGlobal('fetch', mockFetch);

      const response = await onRequestGet(createContext('?username=apiuser', SCRAPER_ENV));
      const { status, body } = await parseResponse(response);

      expect(status).toBe(200);
      expect(body.status).toBe('active');
      expect(body.username).toBe('apiuser');
      expect(body.profile_pic_url).toBe('https://cdn.instagram.com/api_pic.jpg');
      expect(mockFetch).toHaveBeenCalledTimes(2);
      expect(mockConnect).not.toHaveBeenCalled();
    });

    it('returns deleted when scraping API gets 404', async () => {
      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce({ status: 429, text: () => Promise.resolve('') })
        .mockResolvedValueOnce({ status: 404, text: () => Promise.resolve('Not Found') });
      vi.stubGlobal('fetch', mockFetch);

      const response = await onRequestGet(createContext('?username=gone_api', SCRAPER_ENV));
      const { body } = await parseResponse(response);

      expect(body.status).toBe('deleted');
      expect(body.accessible).toBe(false);
    });

    it('falls through to proxy when scraping API fails', async () => {
      const html = mockHtmlResponse(
        'https://cdn.instagram.com/proxy_fallback.jpg',
        'User (&#064;fallbackuser)',
        '100 Followers',
      );
      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce({ status: 429, text: () => Promise.resolve('') })
        .mockRejectedValueOnce(new Error('ScraperAPI timeout'));
      vi.stubGlobal('fetch', mockFetch);

      const httpResponse = buildHttpResponse(200, html);
      const mockSocket = createMockProxySocket(httpResponse);
      mockConnect.mockReturnValue(mockSocket);

      const env = { ...SCRAPER_ENV, ...PROXY_ENV };
      const response = await onRequestGet(createContext('?username=fallbackuser', env));
      const { body } = await parseResponse(response);

      expect(body.status).toBe('active');
      expect(mockConnect).toHaveBeenCalledOnce();
    });

    it('returns unknown when scraping API fails and no proxy configured', async () => {
      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce({ status: 429, text: () => Promise.resolve('') })
        .mockRejectedValueOnce(new Error('ScraperAPI error'));
      vi.stubGlobal('fetch', mockFetch);

      const response = await onRequestGet(createContext('?username=nofallback', SCRAPER_ENV));
      const { body } = await parseResponse(response);

      expect(body.status).toBe('unknown');
      expect(body.error).toBe('HTTP 429');
    });

    it('prioritizes scraping API over proxy when both configured', async () => {
      const html = mockHtmlResponse(
        'https://cdn.instagram.com/api_priority.jpg',
        'User (&#064;priorityuser)',
        '300 Followers',
      );
      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce({ status: 429, text: () => Promise.resolve('') })
        .mockResolvedValueOnce({ status: 200, text: () => Promise.resolve(html) });
      vi.stubGlobal('fetch', mockFetch);

      const env = { ...SCRAPER_ENV, ...PROXY_ENV };
      const response = await onRequestGet(createContext('?username=priorityuser', env));
      const { body } = await parseResponse(response);

      expect(body.status).toBe('active');
      expect(mockConnect).not.toHaveBeenCalled();
    });

    it('falls through to proxy when scraping API returns non-2xx non-404', async () => {
      const html = mockHtmlResponse(
        'https://cdn.instagram.com/proxy_recover.jpg',
        'User (&#064;recoveruser)',
        '100 Followers',
      );
      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce({ status: 429, text: () => Promise.resolve('') })
        .mockResolvedValueOnce({ status: 500, text: () => Promise.resolve('Internal Error') });
      vi.stubGlobal('fetch', mockFetch);

      const httpResponse = buildHttpResponse(200, html);
      const mockSocket = createMockProxySocket(httpResponse);
      mockConnect.mockReturnValue(mockSocket);

      const env = { ...SCRAPER_ENV, ...PROXY_ENV };
      const response = await onRequestGet(createContext('?username=recoveruser', env));
      const { body } = await parseResponse(response);

      expect(body.status).toBe('active');
      expect(mockConnect).toHaveBeenCalledOnce();
    });

    it('does not call scraping API when direct fetch succeeds', async () => {
      const html = mockHtmlResponse(
        'https://cdn.instagram.com/direct.jpg',
        'User (&#064;directuser)',
        '100 Followers',
      );
      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce({ status: 200, text: () => Promise.resolve(html) });
      vi.stubGlobal('fetch', mockFetch);

      const response = await onRequestGet(createContext('?username=directuser', SCRAPER_ENV));
      const { body } = await parseResponse(response);

      expect(body.status).toBe('active');
      expect(mockFetch).toHaveBeenCalledOnce();
    });
  });

  describe('429 proxy fallback', () => {
    it('falls back to proxy on 429 and returns active account', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ status: 429, text: () => Promise.resolve('') }),
      );

      const html = mockHtmlResponse(
        'https://cdn.instagram.com/proxy_pic.jpg',
        'User (&#064;proxyuser) &#x2022; Instagram',
        '500 Followers, 100 Following',
      );
      const httpResponse = buildHttpResponse(200, html);
      const mockSocket = createMockProxySocket(httpResponse);
      mockConnect.mockReturnValue(mockSocket);

      const response = await onRequestGet(createContext('?username=proxyuser', PROXY_ENV));
      const { status, body } = await parseResponse(response);

      expect(status).toBe(200);
      expect(body.status).toBe('active');
      expect(body.username).toBe('proxyuser');
      expect(body.profile_pic_url).toBe('https://cdn.instagram.com/proxy_pic.jpg');
      expect(mockConnect).toHaveBeenCalledOnce();
    });

    it('returns deleted when proxy gets 404', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ status: 429, text: () => Promise.resolve('') }),
      );

      const httpResponse = buildHttpResponse(404, 'Not Found');
      const mockSocket = createMockProxySocket(httpResponse);
      mockConnect.mockReturnValue(mockSocket);

      const response = await onRequestGet(createContext('?username=gone_user', PROXY_ENV));
      const { body } = await parseResponse(response);

      expect(body.status).toBe('deleted');
      expect(body.accessible).toBe(false);
    });

    it('returns unknown when proxy connection fails', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ status: 429, text: () => Promise.resolve('') }),
      );

      mockConnect.mockImplementation(() => {
        throw new Error('Connection refused');
      });

      const response = await onRequestGet(createContext('?username=proxy_fail', PROXY_ENV));
      const { body } = await parseResponse(response);

      expect(body.status).toBe('unknown');
      expect(body.error).toContain('proxy failed');
      expect(body.error).toContain('Connection refused');
    });

    it('returns unknown when proxy returns invalid response', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ status: 429, text: () => Promise.resolve('') }),
      );

      const mockSocket = createMockProxySocket('invalid data without headers');
      mockConnect.mockReturnValue(mockSocket);

      const response = await onRequestGet(createContext('?username=proxy_bad', PROXY_ENV));
      const { body } = await parseResponse(response);

      expect(body.status).toBe('unknown');
      expect(body.error).toContain('proxy failed');
    });

    it('returns unknown when proxy also gets 429', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ status: 429, text: () => Promise.resolve('') }),
      );

      const httpResponse = buildHttpResponse(429, 'Rate limited');
      const mockSocket = createMockProxySocket(httpResponse);
      mockConnect.mockReturnValue(mockSocket);

      const response = await onRequestGet(createContext('?username=double429', PROXY_ENV));
      const { body } = await parseResponse(response);

      expect(body.status).toBe('unknown');
      expect(body.error).toBe('HTTP 429 (via proxy)');
    });
  });
});
