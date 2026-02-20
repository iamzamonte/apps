/**
 * Google Cloud Run - Instagram 프로필 프록시 서버
 *
 * Cloudflare Pages Function에서 요청을 받아
 * Dataimpulse 레지덴셜 프록시를 통해 Instagram 프로필 HTML을 가져옵니다.
 *
 * Cloudflare Workers는 이중 TLS를 지원하지 않으므로,
 * node:tls가 완전히 동작하는 Cloud Run에서 프록시 연결을 처리합니다.
 *
 * 이중 TLS 흐름:
 *   1. tls.connect(proxy:823)          [outer TLS — 프록시 인증]
 *   2. CONNECT instagram.com:443 → 200 OK
 *   3. tls.connect({ socket })         [inner TLS — instagram.com]
 *   4. GET /username/ HTTP/1.0         → HTML 반환
 *
 * 환경변수:
 *   PORT        - 서버 포트 (Cloud Run이 자동으로 설정, 기본값 8080)
 *   API_KEY     - Cloudflare와 공유하는 비밀키 (필수)
 *   PROXY_HOST  - Dataimpulse 프록시 호스트 (예: gw.dataimpulse.com)
 *   PROXY_PORT  - Dataimpulse 프록시 포트 (기본값: 823)
 *   PROXY_USER  - Dataimpulse 로그인
 *   PROXY_PASS  - Dataimpulse 비밀번호
 */

import tls from 'tls';
import express from 'express';

const app = express();
const PORT = process.env.PORT || 8080;
const API_KEY = process.env.API_KEY;

const FETCH_HEADERS = {
  'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
  Accept: 'text/html',
  'Accept-Language': 'en-US,en;q=0.9',
};

/**
 * API 키 검증 미들웨어
 */
function authenticate(req, res, next) {
  if (!API_KEY) {
    console.warn('WARNING: API_KEY is not set. All requests are allowed.');
    return next();
  }

  const providedKey = req.headers['x-api-key'];
  if (providedKey !== API_KEY) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  next();
}

/**
 * Dataimpulse CONNECT 터널을 통해 Instagram 프로필 HTML을 가져옵니다.
 *
 * @param {string} profileUrl - https://www.instagram.com/username/
 * @returns {{ status: number, body: string }}
 */
async function fetchViaProxy(profileUrl) {
  const target = new URL(profileUrl);
  const proxyHost = process.env.PROXY_HOST;
  const proxyPort = parseInt(process.env.PROXY_PORT || '823', 10);
  const proxyUser = process.env.PROXY_USER;
  const proxyPass = process.env.PROXY_PASS;

  if (!proxyHost || !proxyUser || !proxyPass) {
    throw new Error('Proxy environment variables not configured');
  }

  const auth = Buffer.from(`${proxyUser}:${proxyPass}`).toString('base64');

  // 1. 프록시에 outer TLS 연결 (포트 823 = HTTPS proxy)
  const outerSocket = await new Promise((resolve, reject) => {
    const s = tls.connect(
      { host: proxyHost, port: proxyPort, rejectUnauthorized: false },
      () => resolve(s),
    );
    s.on('error', (e) => reject(new Error(`Proxy TLS error: ${e.message}`)));
    s.setTimeout(15000, () => {
      s.destroy();
      reject(new Error('Proxy connection timeout'));
    });
  });

  // 2. CONNECT 터널 요청 후 200 OK 대기
  await new Promise((resolve, reject) => {
    const connectReq =
      `CONNECT ${target.hostname}:443 HTTP/1.0\r\n` +
      `Host: ${target.hostname}:443\r\n` +
      `Proxy-Authorization: Basic ${auth}\r\n` +
      `\r\n`;

    outerSocket.write(connectReq, 'utf8');

    let buf = '';
    const onData = (chunk) => {
      buf += chunk.toString('utf8');
      if (buf.includes('\r\n\r\n') || buf.includes('\n\n')) {
        outerSocket.removeListener('data', onData);
        const statusLine = buf.split(/\r?\n/)[0];
        const match = statusLine.match(/HTTP\/[\d.]+\s+(\d+)/);
        const code = match ? parseInt(match[1], 10) : 0;
        if (code === 200) resolve();
        else reject(new Error(`CONNECT failed: ${statusLine.trim()}`));
      }
    };
    outerSocket.on('data', onData);
    outerSocket.once('error', (e) => reject(new Error(`CONNECT error: ${e.message}`)));
  });

  // 3. inner TLS 핸드셰이크 (instagram.com, 터널 위에서)
  const innerSocket = await new Promise((resolve, reject) => {
    const s = tls.connect(
      { socket: outerSocket, host: target.hostname, rejectUnauthorized: false },
      () => resolve(s),
    );
    s.on('error', (e) => reject(new Error(`Instagram TLS error: ${e.message}`)));
  });

  // 4. HTTP GET 요청 전송 (inner TLS 위에서, path 기반)
  const httpRequest =
    `GET ${target.pathname} HTTP/1.0\r\n` +
    `Host: ${target.hostname}\r\n` +
    `User-Agent: ${FETCH_HEADERS['User-Agent']}\r\n` +
    `Accept: text/html\r\n` +
    `Accept-Language: en-US,en;q=0.9\r\n` +
    `Accept-Encoding: identity\r\n` +
    `Connection: close\r\n` +
    `\r\n`;

  await new Promise((resolve, reject) => {
    innerSocket.write(httpRequest, 'utf8', (err) => (err ? reject(err) : resolve()));
  });

  // 5. 전체 응답 수집
  const fullData = await new Promise((resolve, reject) => {
    const chunks = [];
    innerSocket.on('data', (chunk) => chunks.push(chunk));
    innerSocket.on('end', () => resolve(Buffer.concat(chunks)));
    innerSocket.on('error', reject);
  });
  innerSocket.destroy();

  // 6. HTTP 응답 파싱 (status line + body 분리)
  const responseText = fullData.toString('utf8');
  const crlfIndex = responseText.indexOf('\r\n\r\n');
  const lfIndex = responseText.indexOf('\n\n');
  const headerEnd = crlfIndex !== -1 ? crlfIndex : lfIndex;
  const separatorLen = crlfIndex !== -1 ? 4 : 2;

  if (headerEnd === -1) {
    throw new Error(`Invalid proxy response (len=${fullData.length})`);
  }

  const statusLine = responseText.split(/\r?\n/)[0];
  const statusMatch = statusLine.match(/HTTP\/[\d.]+\s+(\d+)/);
  const statusCode = statusMatch ? parseInt(statusMatch[1], 10) : 0;
  const body = responseText.substring(headerEnd + separatorLen);

  return { status: statusCode, body };
}

/**
 * GET /check-account?username=<username>
 *
 * Dataimpulse 프록시를 통해 Instagram 프로필 HTML을 가져와 반환합니다.
 * 파싱은 Cloudflare Pages Function에서 수행합니다.
 */
app.get('/check-account', authenticate, async (req, res) => {
  const { username } = req.query;

  if (!username || typeof username !== 'string') {
    return res.status(400).json({ error: 'Missing or invalid username parameter' });
  }

  const sanitized = username.trim();

  if (sanitized.length === 0 || sanitized.length > 30) {
    return res.status(400).json({ error: 'Username must be 1-30 characters' });
  }

  if (!/^[a-zA-Z0-9._]+$/.test(sanitized)) {
    return res.status(400).json({ error: 'Invalid username format' });
  }

  const profileUrl = `https://www.instagram.com/${encodeURIComponent(sanitized)}/`;

  try {
    const { status, body } = await fetchViaProxy(profileUrl);

    res
      .status(status)
      .set('Content-Type', 'text/html; charset=utf-8')
      .set('Cache-Control', 'no-store')
      .send(body);
  } catch (error) {
    res.status(502).json({ error: error.message || 'Proxy request failed' });
  }
});

/**
 * GET /health
 * Cloud Run 헬스체크 엔드포인트
 */
app.get('/health', (_req, res) => {
  res.json({ status: 'ok' });
});

app.listen(PORT, () => {
  console.log(`unfollowlens-proxy listening on port ${PORT}`);
});
