/**
 * Google Cloud Run - Instagram 프로필 프록시 서버
 *
 * Cloudflare Pages Function이 Instagram에서 429를 받을 때
 * Google의 IP를 통해 Instagram 프로필 HTML을 대신 가져옵니다.
 *
 * 환경변수:
 *   PORT     - 서버 포트 (Cloud Run이 자동으로 설정, 기본값 8080)
 *   API_KEY  - Cloudflare와 공유하는 비밀키 (필수)
 */

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
 * API_KEY 환경변수가 설정된 경우 x-api-key 헤더를 확인합니다.
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
 * GET /check-account?username=<username>
 *
 * Instagram 프로필 HTML을 가져와 그대로 반환합니다.
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
    const response = await fetch(profileUrl, {
      headers: FETCH_HEADERS,
      redirect: 'follow',
      signal: AbortSignal.timeout(10_000),
    });

    const body = await response.text();

    res
      .status(response.status)
      .set('Content-Type', 'text/html; charset=utf-8')
      .set('Cache-Control', 'no-store')
      .send(body);
  } catch (error) {
    const isTimeout = error.name === 'TimeoutError' || error.name === 'AbortError';
    res.status(502).json({
      error: isTimeout ? 'Upstream request timed out' : (error.message || 'Fetch failed'),
    });
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
