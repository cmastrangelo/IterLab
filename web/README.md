# IterLab web interface

**Next.js (App Router) + React + TypeScript.**

Current scope:

- `/register` and `/login` — talk to `POST /api/v1/auth/*`
- app shell with a left navbar listing all labs
- `/labs/[labId]` — lab overview (repo, settings, benchmark list)
- `/labs/[labId]/benchmarks` — benchmark tab; renders each benchmark's live
  leaderboard from `GET /api/v1/benchmarks/{id}/leaderboard`
- access token held in memory, refresh token in `localStorage`, automatic
  refresh + retry on a `401`

Experiments / Workers pages and candidate runs come next.

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
    layout.tsx              root layout + <AuthProvider>
    page.tsx                redirects to /labs or /login
    login/  register/       auth forms
    (app)/
      layout.tsx            app shell: auth guard + left navbar
      labs/page.tsx         redirects to the first lab
      labs/[labId]/
        layout.tsx          lab header + tab nav
        page.tsx             Overview
        benchmarks/page.tsx  Benchmarks tab + leaderboard table
  lib/
    api.ts                  fetch client + token handling + typed endpoints
    auth.tsx                React context: user, login, register, logout
```

## Notes / later

- Refresh tokens in `localStorage` are fine for a skeleton; move them to
  httpOnly cookies (needs a backend change) for production.
- Route protection is client-side only (`/home` redirects if unauthenticated).
