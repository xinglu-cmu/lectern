# ADR-009: Web and API on one registrable domain, so the auth cookie stays first-party

**Status:** accepted · 2026-09-24

## Context

The web app deploys to Vercel and the API to the VM (DESIGN §10). Auth (DESIGN §7) pairs a short-lived access JWT held in memory with a rotating refresh token in an `HttpOnly` cookie set by the API. By default the web app would live at `<project>.vercel.app`, and `vercel.app` is on the Public Suffix List, so that hostname is a site of its own. The API, on the VM's IP or any other domain, would then be *cross-site*, which makes its refresh cookie a third-party cookie. Safari blocks third-party cookies by default, Firefox partitions them, and Chrome users can block them, so silent refresh would fail for a large share of visitors. Making it work at all would require `SameSite=None`, which gives up the cookie's built-in CSRF protection.

Options considered:

1. **One custom domain:** `app.<domain>` on Vercel, `api.<domain>` on the VM.
2. **Proxy the API through Vercel rewrites** (`/api/*` on the web origin). Same-origin, but every call and the long-lived SSE progress stream pass through Vercel's proxy (stream timeouts and buffering, an extra hop, bandwidth quota), and the API sees proxy addresses, which complicates per-client rate limiting.
3. **Serve the web app from the VM too.** One origin, but it loses Vercel's CDN and preview deploys and adds a Node process to the VM.
4. **No cookies:** keep the refresh token in `localStorage` and send it as a header. That is a long-lived credential any XSS can read.

## Decision

Option 1. Buy one domain, with DNS on Cloudflare (the R2 account already lives there). `app.<domain>` is a CNAME to Vercel. `api.<domain>` points at the VM, where Caddy terminates TLS with automatic certificates and proxies to the api container. Both hosts share a registrable domain, so they are same-site and the refresh cookie is first-party in every browser.

The cookie is `HttpOnly; Secure; SameSite=Strict; Path=/api/auth` and host-only (no `Domain` attribute), so only `api.<domain>` receives it, and only on the auth endpoints.

Same-site is not same-origin, so CORS is still required: the API allows exactly `https://app.<domain>` with `Access-Control-Allow-Credentials: true`, and the web client sends `credentials: "include"`.

## Rationale

- Browsers' third-party-cookie rules key on the *site* (registrable domain), not the origin. One shared domain is the smallest change that keeps auth working everywhere.
- `SameSite=Strict`, exact-origin CORS and a host-only cookie is the tightest setup that still works.
- SSE and rate limiting keep a direct path to the API, and Vercel keeps doing what it's good at.
- Cost: about $10–15 a year for the domain.

## Consequences

- A domain must exist before auth reaches production (week 4). The landing page can deploy on `*.vercel.app` before that.
- Authenticated data fetching happens in the browser (browser → `api.<domain>`). Next.js server components never see the API's cookie, so they render only public content.
- Vercel preview deployments (`*.vercel.app`) stay cross-site, so logging in against the production API won't work there. Previews are for UI review, or can later get a `preview.<domain>` alias.
- Local development keeps the same shape: `localhost:3000` → `localhost:8080` is same-site, because ports don't change the site.

## Revisit when

The web app moves onto the VM, or the web tier becomes a backend-for-frontend that holds the session server-side.
