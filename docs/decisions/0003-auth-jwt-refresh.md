# 0003 · access는 JWT, refresh는 DB에 해시로 저장하는 무작위 문자열

- **상태**: 채택
- **날짜**: 2026-09-18 (토큰 형식 · 해시 방식은 2026-09-20)

## 맥락

v0의 DRF TokenAuthentication은 앱 클라이언트 기준이었다. 웹 클라이언트로 바뀌면서 httpOnly 쿠키 보관이 필요해졌고, JWT가 학습 목표에 들어 있다. 흐름은 `ARCHITECTURE` 4.1절.

## 결정

- **access 토큰은 JWT**(HS256), 응답 본문으로 주고 메모리에만 둔다.
- **refresh 토큰은 JWT가 아니라 무작위 문자열**이다. JWT의 장점은 "DB를 보지 않고 서명만으로 검증"인데, refresh 토큰은 로그아웃 폐기 · rotation · 탈취 감지를 위해 어차피 매번 DB를 조회해야 한다. 그 순간 이점이 사라지고 만료 로직 · 서명 키 관리만 늘어난다. JWT는 payload를 누구나 읽을 수 있지만 무작위 문자열은 DB 없이는 아무 의미가 없다.
- **refresh 토큰 해시는 argon2가 아니라 SHA-256**이다. argon2가 느린 것은 약한 비밀번호 대입을 막기 위해서인데, 서버가 만든 32바이트 무작위값에는 대입이 성립하지 않는다. salt가 없어 같은 입력이면 같은 해시가 나오므로 `WHERE token_hash = ...`로 바로 조회할 수 있다.
- **외부 로그인은 Discord (OAuth 2.0)**. Steam은 로그인이 아니라 라이브러리 연결 용도로 쓴다.

## 검토한 대안

- **DRF TokenAuthentication 유지** — 스택 전환으로 해당 없음.
- **refresh도 JWT** — 위 이유로 이점이 없다.
- **Steam 로그인** — OAuth가 아닌 OpenID 2.0이라 학습 목표(OAuth 2.0)와 맞지 않는다.
- **GitHub 로그인** — 게이머에게는 Discord가 더 자연스럽다.

## 감수할 것

- refresh 재발급마다 DB 쓰기가 생기고, 동시 재발급은 재사용 감지에 걸린다. 클라이언트가 재발급을 한 번만 보내야 한다 (`ARCHITECTURE` 3.3절 ③).
- 폐기 기록을 지우지 않아 `refresh_tokens` 행이 쌓인다 (F-28).
