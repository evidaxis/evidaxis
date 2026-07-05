# Analytics & observability — Evidaxis

> created 2026-07-05 · owner: Claude (Igor's second brain)

Wiring lives in [`web/src/components/Analytics.astro`](web/src/components/Analytics.astro)
(single guarded entry, PROD-only, no-op without keys) mounted in `web/src/layouts/Base.astro`.
Keys are client-side **publishable** (visible in the browser by design, not secrets); the
build reads them from `web/.env` as `PUBLIC_*`, recorded here for recoverability.

## Stack (4 layers + errors)

| Layer | Tool | Role | Key |
|---|---|---|---|
| Aggregate traffic (cookieless) | **Vercel Web Analytics** | how many / where from | (platform, enable in dashboard) |
| Real-user CWV | **Vercel Speed Insights** | performance, measure-don't-guess | (platform, enable in dashboard) |
| Behaviour | **Microsoft Clarity** | heatmaps + session replay | `xhnec3inys` |
| Marketing / attribution | **Google Analytics 4** | Google ecosystem, Ads, BigQuery | `G-J01XVSMNHR` |
| Product analytics | **PostHog** (project `evidaxis` / 498568) | funnels/flags/replay, portfolio standard | `phc_o8NsUUG9UXZNpgqDWy78HvwhcipjyxTWNdePZBxdEzAN` @ `https://us.i.posthog.com` |
| Errors (pre-existing) | **Sentry** | client JS errors | DSN in `web/.env` |

Load strategy: gtag `async`; Clarity self-deferring; PostHog stub now + `.init()` on idle;
Vercel scripts `defer`. **Partytown deliberately deferred** — added only if Speed Insights
shows main-thread cost (sensors first, optimize on data).

## PostHog org "Ivitskiy" — project map (split done 2026-07-05)

| id | project | use |
|---|---|---|
| 498067 | Legacy (mixed xray+checker, pre-split) | historical archive, no new ingestion |
| 498568 | **evidaxis** | this site |
| 498569 | **ad-xray** | app (re-point ~/Projects/ad-xray to `phc_nsaLht2xGG5GAMcfjZTzXH2Q3TsDrZjpF4ZS3BcYtaVg`) |
| 498570 | **ai-checker** | app (re-point ~/Projects/ai-checker to `phc_tZbyq6nfwKU2nrrNbh8PCBb8T5v2rrbuBVJajHK8qvSF`) |

## One-time settings to apply (do now, lossy if set late)

**GA4** (analytics.google.com → property Evidaxis):
1. Admin → Data Streams → Web stream → **Enhanced measurement: ON** (default; keep — free scroll/outbound/file/video events).
2. Admin → Data Settings → **Data Retention → 14 months** (default 2; bump to max).
3. Admin → Product Links → **BigQuery** → link. GCP project **`evidaxis-analytics`** already created + BigQuery API enabled + billing linked (2026-07-05, via gcloud). In the wizard: Choose project `evidaxis-analytics` → Data location **US** (Igor's call — targets/sells into Silicon Valley; region is locked after creation) → Export type **Daily** for BOTH Event data and User data (free at this volume, fuller ownership) → Submit. Streaming off, advertising identifiers off. (**Not retroactive** — that's why it is set up before traffic.)
4. Admin → Product Links → **Search Console** → link (join queries + behaviour).
5. Admin → Product Links → **Google Ads** → link (for future paid traffic / conversion import).
6. Optional later: **Google Signals** OFF until EU consent story is settled (avoids extra consent obligation).

**Clarity** (clarity.microsoft.com → project Evidaxis):
- Defaults are good. Settings → **Masking = Balanced** (keep; hides text input, safe for GDPR).
- Settings → **GA integration** → connect the GA4 property (lets you jump from a GA segment straight to its Clarity recordings).
- No cost, unlimited; nothing else required.

**Vercel** (dashboard → project evidaxis):
- Analytics tab → **Enable Web Analytics** and **Enable Speed Insights** (required or `/_vercel/*` scripts 404).

## Roadmap triggers (not now — конституция №6, don't build on empty)

- **Consent banner / Consent Mode v2**: activate when real EU traffic arrives (GA4 + Clarity + PostHog stack raises the consent case). Natural home = client GTM.
- **Server-side GTM**: only at meaningful paid-traffic volume, one container portfolio-wide.
- **Vercel ISR** for the long-tail `/e/` pages: when page count crosses ~thousands (needs `@astrojs/vercel` adapter; currently pure static).
