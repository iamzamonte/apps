/**
 * Dataimpulse 프록시 로컬 테스트 스크립트
 *
 * check-account.js의 fetchViaProxy() 로직을 Node.js로 재현.
 *
 * 포트 823은 TLS(HTTPS proxy)를 사용하며 CONNECT 터널링을 통해 HTTPS 목적지에 접근한다.
 * 흐름:
 *   1. tls.connect → proxy (outer TLS)
 *   2. CONNECT www.instagram.com:443 HTTP/1.0 (프록시 터널 요청)
 *   3. 200 OK 수신
 *   4. tls.connect({ socket: outerSocket }) → instagram.com (inner TLS)
 *   5. GET /username/ HTTP/1.0 (일반 HTTP, inner TLS 위에서)
 *   6. 응답 파싱
 *
 * Usage:
 *   PROXY_USER=xxx PROXY_PASS=yyy node scripts/test-proxy.mjs <instagram_username>
 *
 * 환경변수:
 *   PROXY_HOST  - 프록시 호스트 (기본값: gw.dataimpulse.com)
 *   PROXY_PORT  - 프록시 포트   (기본값: 823)
 *   PROXY_USER  - 프록시 로그인 (필수)
 *   PROXY_PASS  - 프록시 비밀번호 (필수)
 */

import tls from 'tls';

// ─── 설정 ─────────────────────────────────────────────────────────────────

const PROXY_HOST = process.env.PROXY_HOST ?? 'gw.dataimpulse.com';
const PROXY_PORT = parseInt(process.env.PROXY_PORT ?? '823', 10);
const PROXY_USER = process.env.PROXY_USER;
const PROXY_PASS = process.env.PROXY_PASS;

// check-account.js:31-35와 동일한 헤더 상수
const FETCH_HEADERS = {
  'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
  Accept: 'text/html',
  'Accept-Language': 'en-US,en;q=0.9',
};

// ─── 입력 검증 ────────────────────────────────────────────────────────────

const username = process.argv[2];

if (!username) {
  process.stderr.write('Usage: node scripts/test-proxy.mjs <instagram_username>\n');
  process.exit(1);
}

if (!PROXY_USER || !PROXY_PASS) {
  process.stderr.write('Error: PROXY_USER and PROXY_PASS environment variables are required\n');
  process.exit(1);
}

// ─── og 태그 추출 (check-account.js:41-44 재현) ───────────────────────────

function extractMeta(html, property) {
  const escaped = property.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = html.match(new RegExp(`<meta property="${escaped}" content="([^"]*)"`, 'i'));
  return match ? match[1] : null;
}

// ─── HTML 엔티티 디코딩 (check-account.js:47-56 재현) ────────────────────

function decodeHtmlEntities(text) {
  return text
    .replace(/&#064;/g, '@')
    .replace(/&#x2022;/g, '\u2022')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
}

// ─── 계정 파싱 (check-account.js:58-85 재현) ─────────────────────────────

function parseAccountFromHtml(html, uname) {
  const ogImage = extractMeta(html, 'og:image');
  const ogTitle = extractMeta(html, 'og:title');
  const ogDescription = extractMeta(html, 'og:description');

  if (!ogTitle || !ogImage) {
    return { username: uname, status: 'deleted_or_restricted', accessible: false };
  }

  const decodedDesc = ogDescription ? decodeHtmlEntities(ogDescription) : '';
  const isPrivate =
    decodedDesc.includes('This account is private') ||
    decodedDesc.includes('This Account is Private') ||
    decodedDesc.includes('비공개 계정입니다');

  return {
    username: uname,
    status: 'active',
    accessible: true,
    is_private: isPrivate,
    profile_pic_url: decodeHtmlEntities(ogImage),
    og_title: decodeHtmlEntities(ogTitle),
    og_description: decodedDesc,
  };
}

// ─── HTTP 응답 파싱 헬퍼 (check-account.js:174-197 재현) ─────────────────

function parseHttpResponse(fullData) {
  const responseText = fullData.toString('utf8');
  const crlfIndex = responseText.indexOf('\r\n\r\n');
  const lfIndex = responseText.indexOf('\n\n');
  const headerEnd = crlfIndex !== -1 ? crlfIndex : lfIndex;
  const separatorLen = crlfIndex !== -1 ? 4 : 2;

  if (headerEnd === -1) {
    const preview = responseText.substring(0, 200);
    const hexBytes = Array.from(fullData.slice(0, 20))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join(' ');
    throw new Error(
      `Invalid response (len=${fullData.length}, hex=[${hexBytes}], preview=${preview})`,
    );
  }

  const headerSection = responseText.substring(0, headerEnd);
  const body = responseText.substring(headerEnd + separatorLen);
  const statusLine = headerSection.split(/\r?\n/)[0];
  const statusMatch = statusLine.match(/HTTP\/[\d.]+\s+(\d+)/);
  const statusCode = statusMatch ? parseInt(statusMatch[1], 10) : 0;

  return { status: statusCode, body, headerSection };
}

// ─── 스트림 데이터 전체 수집 헬퍼 ────────────────────────────────────────

async function readAll(stream) {
  const chunks = [];
  for await (const chunk of stream) {
    chunks.push(chunk);
  }
  return Buffer.concat(chunks);
}

// ─── 프록시를 통한 Instagram 프로필 요청 ─────────────────────────────────

async function fetchViaProxy(profileUrl) {
  const target = new URL(profileUrl);
  const auth = Buffer.from(`${PROXY_USER}:${PROXY_PASS}`).toString('base64');

  // 1. 프록시에 TLS로 연결 (포트 823 = HTTPS proxy)
  process.stdout.write(`Step 1: TLS connect to ${PROXY_HOST}:${PROXY_PORT}...\n`);
  const outerSocket = await new Promise((resolve, reject) => {
    const s = tls.connect(
      { host: PROXY_HOST, port: PROXY_PORT, rejectUnauthorized: false },
      () => resolve(s),
    );
    s.on('error', (e) => reject(new Error(`Proxy TLS error: ${e.message}`)));
    s.setTimeout(15000, () => {
      s.destroy();
      reject(new Error('Proxy connection timed out after 15s'));
    });
  });
  process.stdout.write(
    `  OK (cipher: ${outerSocket.getCipher()?.name}, authorized: ${outerSocket.authorized})\n`,
  );

  // 2. CONNECT 터널 요청
  process.stdout.write(`Step 2: CONNECT ${target.hostname}:443...\n`);
  const connectReq =
    `CONNECT ${target.hostname}:443 HTTP/1.0\r\n` +
    `Host: ${target.hostname}:443\r\n` +
    `Proxy-Authorization: Basic ${auth}\r\n` +
    `\r\n`;

  await new Promise((resolve, reject) => {
    outerSocket.write(connectReq, 'utf8');

    let buf = '';
    const onData = (chunk) => {
      buf += chunk.toString('utf8');
      if (buf.includes('\r\n\r\n') || buf.includes('\n\n')) {
        outerSocket.removeListener('data', onData);
        const statusLine = buf.split(/\r?\n/)[0];
        const statusMatch = statusLine.match(/HTTP\/[\d.]+\s+(\d+)/);
        const statusCode = statusMatch ? parseInt(statusMatch[1], 10) : 0;
        if (statusCode === 200) {
          process.stdout.write(`  Proxy response: ${statusLine}\n`);
          resolve();
        } else {
          reject(new Error(`CONNECT failed: ${statusLine.trim()}`));
        }
      }
    };
    outerSocket.on('data', onData);
    outerSocket.once('error', (e) => reject(new Error(`CONNECT error: ${e.message}`)));
  });

  // 3. Inner TLS: instagram.com과 TLS 핸드셰이크 (터널 위에서)
  process.stdout.write(`Step 3: Inner TLS to ${target.hostname}...\n`);
  const innerSocket = await new Promise((resolve, reject) => {
    const s = tls.connect(
      { socket: outerSocket, host: target.hostname, rejectUnauthorized: false },
      () => resolve(s),
    );
    s.on('error', (e) => reject(new Error(`Instagram TLS error: ${e.message}`)));
  });
  process.stdout.write(
    `  OK (cipher: ${innerSocket.getCipher()?.name}, authorized: ${innerSocket.authorized})\n`,
  );

  // 4. HTTP GET 요청 전송 (path 기반, inner TLS 위에서)
  process.stdout.write(`Step 4: GET ${target.pathname}...\n`);
  const httpRequest =
    `GET ${target.pathname} HTTP/1.0\r\n` +
    `Host: ${target.hostname}\r\n` +
    `User-Agent: ${FETCH_HEADERS['User-Agent']}\r\n` +
    `Accept: text/html\r\n` +
    `Accept-Language: en-US,en;q=0.9\r\n` +
    `Accept-Encoding: identity\r\n` +
    `Connection: close\r\n` +
    `\r\n`;

  innerSocket.write(httpRequest, 'utf8');

  // 5. 응답 수집 및 파싱
  const fullData = await readAll(innerSocket);
  innerSocket.destroy();
  process.stdout.write(`  Received ${fullData.length} bytes\n\n`);

  return parseHttpResponse(fullData);
}

// ─── 메인 ─────────────────────────────────────────────────────────────────

const profileUrl = `https://www.instagram.com/${encodeURIComponent(username)}/`;
process.stdout.write(`Target: ${profileUrl}\n\n`);

try {
  const { status, body, headerSection } = await fetchViaProxy(profileUrl);

  process.stdout.write(`─── HTTP Response ───────────────────────────\n`);
  process.stdout.write(`Status: ${status}\n`);
  process.stdout.write(`Headers:\n${headerSection}\n\n`);

  if (status === 404) {
    process.stdout.write('Result: deleted (HTTP 404)\n');
    process.exit(0);
  }

  if (status !== 200) {
    process.stderr.write(`Result: unexpected HTTP ${status}\n`);
    process.exit(1);
  }

  const result = parseAccountFromHtml(body, username);

  process.stdout.write(`─── Parsed Account ──────────────────────────\n`);
  process.stdout.write(`Status: ${result.status}\n`);

  if (result.status === 'active') {
    process.stdout.write(`Profile pic: ${result.profile_pic_url}\n`);
    process.stdout.write(`Private: ${result.is_private}\n`);
    process.stdout.write(`OG title: ${result.og_title}\n`);
    if (result.og_description) {
      process.stdout.write(`OG description: ${result.og_description.substring(0, 120)}\n`);
    }
  } else {
    process.stdout.write('No og:title/og:image — login wall or account unavailable\n');
    process.stdout.write(`\nBody preview (first 500 chars):\n${body.substring(0, 500)}\n`);
  }

  process.exit(0);
} catch (err) {
  process.stderr.write(`\nError: ${err.message}\n`);
  process.exit(1);
}
