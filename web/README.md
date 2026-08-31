# IterLab web interface

**Next.js (App Router) + React + TypeScript.**

Current scope (skeleton):

- `/register` and `/login` — talk to `POST /api/v1/auth/*`
- `/home` — authenticated placeholder ("under construction") with sign-out
- access token held in memory, refresh token in `localStorage`, automatic
  refresh + retry on a `401`

Projects / Labs / Experiments / Workers pages come next, against the list
endpoints that already exist on the API.

## Develop

```bash
cd web
npm install
cp .env.example .env.local          # point NEXT_PUBLIC_API_BASE_URL at the API
npm run dev                          # http://localhost:3000
```

The API must be running (see the repo root README) and must allow the web
origin via `ITERLAB_CORS_ORIGINS` (default already includes
`http://localhost:3000`).

## With docker-compose

The root `docker-compose.yml` includes a `web` service:

```bash
docker compose --profile bundled-db up --build      # api + web + redis + postgres
# web  -> http://localhost:3000
# api  -> http://localhost:8000  (docs at /docs)
```

`NEXT_PUBLIC_API_BASE_URL` is baked in at build time (Next.js inlines
`NEXT_PUBLIC_*`). Override it via the compose build arg / env var and rebuild.

## Layout

```
src/
  app/
    layout.tsx        root layout + <AuthProvider>
    page.tsx          redirects to /home or /login
    login/            login form
    register/         registration form
    home/             authenticated "under construction" page
  lib/
    api.ts            fetch client + token handling
    auth.tsx          React context: user, login, register, logout
```

## Notes / later

- Refresh tokens in `localStorage` are fine for a skeleton; move them to
  httpOnly cookies (needs a backend change) for production.
- Route protection is client-side only (`/home` redirects if unauthenticated).
