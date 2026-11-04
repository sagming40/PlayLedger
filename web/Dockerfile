# 운영 화면 이미지 ─ 빌드한 정적 파일 + Caddy (PLAN M5, decisions/0012)
# 비유: 부엌(Node)에서 요리해 접시(dist)만 매장(Caddy)으로 옮긴다. 부엌 도구는 손님 쪽에 없다

FROM node:24-alpine AS build
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM caddy:2-alpine
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /web/dist /srv
