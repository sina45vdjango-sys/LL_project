# DEFERRED.md — what this run deliberately did **not** do

Everything below is out of scope for the `audit-quality` run by the owner's own
instruction. No item here was implemented, and nothing here is half-done.

## Security and production

| Item | Audit IDs | Why it is deferred |
|---|---|---|
| Login throttling, lockout, moving `/admin/` off its default path | P-03 | A rate limiter and an admin path change are deployment decisions (which limiter, what ceiling, what path). They also change how the owner signs in. Out of scope by instruction. |
| `Content-Security-Policy` and `Permissions-Policy` headers | P-13 | A strict CSP needs a nonce or hash for the inline pre-paint theme script. That is a shell-wide change with a real chance of blanking the page if it is got wrong, and it is a deployment concern. |
| Deployment configuration (`STATIC_ROOT`, `collectstatic`, gunicorn/uvicorn, nginx, TLS) | P-23 | Belongs to launch, not to the front end. |
| `Secure` cookies, HSTS, `SECURE_SSL_REDIRECT` | P-24 | Meaningless on the local HTTP server this run tests against, and switching them on would break every form and every login during local testing. |
| Analytics and error monitoring | P-04, P-29 | Every option is a third-party service with an account, a privacy position and a cost decision. The owner has to choose it. |
| A cache backend (`CACHES`) | P-22 | The audit's performance defect was removable with cheaper queries instead (see P-02 in `REPORT.md`), so no cache was needed. Choosing one remains a deployment decision. |
| Password reset and an email backend | P-09 | Needs an email provider and an account. Deferred by instruction. |

## Launch work

| Item | Audit IDs | Why it is deferred |
|---|---|---|
| SEO: meta description, canonical, Open Graph, JSON-LD, `robots.txt`, `sitemap.xml` | P-10, P-11 | Launch work. Note that a sitemap is only meaningful once a public origin exists. |
| Contact, privacy policy and terms pages | P-08 | The owner must be named, and the privacy text depends on decisions about analytics and hosting that are themselves deferred. |
| Pricing, plans, checkout, payment provider | P-05 | A business decision, not an engineering one. |
| The A2 course | P-30 (partly) | A second course is a content project of the same size again. |
| A standalone free-writing task beyond the exam's guided parts | P-25 (partly) | Deferred as a separate product decision; the exam's SCHREIBEN section now asks for real sentence production instead (see `REPORT.md`). |
| Email digests and streak reminders | — | Needs the email backend, which is deferred. |
| PWA / offline install | — | Out of scope. |
| An A1 certificate or credential | — | Out of scope, and it has legal weight the owner has not chosen to take on. |

## A note for anything that ever adds microphone recording

The speaking page records locally in the browser (nothing is uploaded). Browsers only
grant microphone access on a **secure context**: `https://`, or the special case of
`http://localhost` / `http://127.0.0.1`. On the LAN address the project documents for
showing the site to other people (`http://10.x.x.x:8000/`) the browser will refuse the
microphone, so the record buttons will report that the microphone is unavailable and the
rest of the page still works. Any future feature that needs the microphone — automatic
pronunciation scoring, for instance — **requires HTTPS outside localhost**.

## Anything needing an owner decision

Those are not here; they are in `OWNER-DECISIONS.md`.
