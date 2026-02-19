FROM node:22-slim

# 보안: root가 아닌 전용 사용자로 실행
RUN addgroup --system --gid 1001 nodejs \
  && adduser --system --uid 1001 appuser

WORKDIR /app

# 의존성만 먼저 복사 (레이어 캐시 활용)
COPY package.json ./
RUN npm install --omit=dev

# 소스 복사 후 소유권 변경
COPY --chown=appuser:nodejs index.js ./

USER appuser

# Cloud Run은 PORT 환경변수를 자동으로 설정합니다
EXPOSE 8080

CMD ["node", "index.js"]
