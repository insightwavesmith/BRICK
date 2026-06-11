# Cloud Run 용. 2단계: 빌드(vite) → 런타임(순수 node, 의존성 0).
FROM node:22-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production
# 서버는 외부 의존성이 없다 → dist + server 만 복사
COPY --from=build /app/dist ./dist
COPY --from=build /app/server ./server
EXPOSE 8080
CMD ["node", "server/index.mjs"]
