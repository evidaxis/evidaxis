#!/usr/bin/env bash
# Preview deploy (NOT production): builds the static site locally and pushes the
# prebuilt dist/ to Vercel as a PREVIEW deployment with its own unique URL.
# Production (evidaxis.org) is never touched — that is deploy.sh (--prod) only.
# Same gitignored deploy.env (repo root) supplies the project/org ids.
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
[ -f "$REPO/deploy.env" ] && { set -a; . "$REPO/deploy.env"; set +a; }
: "${VERCEL_PROJECT_ID:?set VERCEL_PROJECT_ID in deploy.env}"
: "${VERCEL_ORG_ID:?set VERCEL_ORG_ID in deploy.env}"
cd "$REPO/web"
npm run build
npm run check                       # dist invariant gate before any push
cp vercel.json dist/vercel.json
mkdir -p dist/.vercel
cat > dist/.vercel/project.json <<JSON
{"projectId":"${VERCEL_PROJECT_ID}","orgId":"${VERCEL_ORG_ID}","projectName":"${VERCEL_PROJECT_NAME:-evidaxis}"}
JSON
cd dist
# no --prod -> preview deployment, isolated URL, production alias untouched
vercel deploy --yes
