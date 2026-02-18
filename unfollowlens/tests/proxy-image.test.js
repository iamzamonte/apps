import { describe, it, expect, vi, beforeEach } from 'vitest';

/**
 * Tests for the Cloudflare Pages Function: proxy-image.js
 *
 * The function proxies Instagram CDN images server-side
 * to bypass Referer-based hotlink protection.
 */

const { onRequestGet } = await import('../functions/api/proxy-image.js');

function createContext(searchParams = '') {
  return {
    request: {
      url: `https://unfollowlens.com/api/proxy-image${searchParams}`,
    },
  };
}

async function parseJsonResponse(response) {
  const body = await response.json();
  return { status: response.status, body };
}

function mockImageResponse(contentType = 'image/jpeg', bytes = [0xff, 0xd8], extraHeaders = {}) {
  const imageBytes = new Uint8Array(bytes);
  return {
    ok: true,
    status: 200,
    headers: new Headers({
      'content-type': contentType,
      'content-length': String(imageBytes.length),
      ...extraHeaders,
    }),
    arrayBuffer: () => Promise.resolve(imageBytes.buffer),
  };
}

describe('proxy-image API', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('input validation', () => {
    it('returns 400 when url parameter is missing', async () => {
      const response = await onRequestGet(createContext(''));
      const { status, body } = await parseJsonResponse(response);
      expect(status).toBe(400);
      expect(body.error).toBe('Missing url parameter');
    });

    it('returns 400 for non-Instagram domain', async () => {
      const url = encodeURIComponent('https://evil.com/image.jpg');
      const response = await onRequestGet(createContext(`?url=${url}`));
      const { status, body } = await parseJsonResponse(response);
      expect(status).toBe(400);
      expect(body.error).toContain('URL not allowed');
    });

    it('returns 400 for HTTP (non-HTTPS) URL', async () => {
      const url = encodeURIComponent('http://scontent.cdninstagram.com/pic.jpg');
      const response = await onRequestGet(createContext(`?url=${url}`));
      const { status, body } = await parseJsonResponse(response);
      expect(status).toBe(400);
      expect(body.error).toContain('URL not allowed');
    });

    it('returns 400 for malformed URL', async () => {
      const response = await onRequestGet(createContext('?url=not-a-url'));
      const { status, body } = await parseJsonResponse(response);
      expect(status).toBe(400);
      expect(body.error).toContain('URL not allowed');
    });
  });

  describe('allowed domains', () => {
    it('accepts scontent.cdninstagram.com URLs', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(mockImageResponse()));

      const url = encodeURIComponent('https://scontent.cdninstagram.com/v/t51/profile.jpg');
      const response = await onRequestGet(createContext(`?url=${url}`));
      expect(response.status).toBe(200);
      expect(response.headers.get('Content-Type')).toBe('image/jpeg');
    });

    it('accepts fbcdn.net URLs', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(mockImageResponse()));

      const url = encodeURIComponent('https://scontent-iad3-2.xx.fbcdn.net/v/t51/photo.jpg');
      const response = await onRequestGet(createContext(`?url=${url}`));
      expect(response.status).toBe(200);
    });
  });

  describe('upstream error handling', () => {
    it('returns 502 when upstream returns non-200', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: false, status: 403, headers: new Headers({}) }),
      );

      const url = encodeURIComponent('https://scontent.cdninstagram.com/pic.jpg');
      const response = await onRequestGet(createContext(`?url=${url}`));
      const { status, body } = await parseJsonResponse(response);
      expect(status).toBe(502);
      expect(body.error).toContain('HTTP 403');
    });

    it('returns 502 when upstream returns non-image content-type', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'text/html' }),
          arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
        }),
      );

      const url = encodeURIComponent('https://scontent.cdninstagram.com/pic.jpg');
      const response = await onRequestGet(createContext(`?url=${url}`));
      const { status, body } = await parseJsonResponse(response);
      expect(status).toBe(502);
      expect(body.error).toContain('not return an image');
    });

    it('returns 502 when content-length exceeds limit', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({
          ok: true,
          status: 200,
          headers: new Headers({
            'content-type': 'image/jpeg',
            'content-length': String(10 * 1024 * 1024),
          }),
          arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
        }),
      );

      const url = encodeURIComponent('https://scontent.cdninstagram.com/pic.jpg');
      const response = await onRequestGet(createContext(`?url=${url}`));
      const { status, body } = await parseJsonResponse(response);
      expect(status).toBe(502);
      expect(body.error).toContain('too large');
    });

    it('returns 502 when fetch throws', async () => {
      vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Connection refused')));

      const url = encodeURIComponent('https://scontent.cdninstagram.com/pic.jpg');
      const response = await onRequestGet(createContext(`?url=${url}`));
      const { status, body } = await parseJsonResponse(response);
      expect(status).toBe(502);
      expect(body.error).toBe('Connection refused');
    });
  });

  describe('successful proxy', () => {
    it('returns image bytes with correct content-type and length', async () => {
      const imageBytes = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a];
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(mockImageResponse('image/png', imageBytes)));

      const url = encodeURIComponent('https://scontent.cdninstagram.com/profile.png');
      const response = await onRequestGet(createContext(`?url=${url}`));

      expect(response.status).toBe(200);
      expect(response.headers.get('Content-Type')).toBe('image/png');
      expect(response.headers.get('Content-Length')).toBe(String(imageBytes.length));

      const body = await response.arrayBuffer();
      expect(new Uint8Array(body)).toEqual(new Uint8Array(imageBytes));
    });

    it('includes cache headers on success', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(mockImageResponse()));

      const url = encodeURIComponent('https://scontent.cdninstagram.com/pic.jpg');
      const response = await onRequestGet(createContext(`?url=${url}`));

      const cacheControl = response.headers.get('Cache-Control');
      expect(cacheControl).toContain('public');
      expect(cacheControl).toContain('max-age=86400');
      expect(cacheControl).toContain('s-maxage=604800');
    });

    it('passes Googlebot user agent to upstream', async () => {
      const mockFetch = vi.fn().mockResolvedValue(mockImageResponse());
      vi.stubGlobal('fetch', mockFetch);

      const url = encodeURIComponent('https://scontent.cdninstagram.com/pic.jpg');
      await onRequestGet(createContext(`?url=${url}`));

      expect(mockFetch).toHaveBeenCalledOnce();
      const [, options] = mockFetch.mock.calls[0];
      expect(options.headers['User-Agent']).toContain('Googlebot');
      expect(options.headers['Accept']).toBe('image/*');
    });
  });

  describe('error response headers', () => {
    it('includes no-store cache header on error responses', async () => {
      const response = await onRequestGet(createContext(''));
      expect(response.headers.get('Cache-Control')).toBe('no-store');
    });
  });
});
