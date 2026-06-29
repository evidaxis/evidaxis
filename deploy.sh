#!/usr/bin/env bash
# Day-1 deploy: build the static site locally (it reads ../data which Vercel's own
# build can't see yet) and push the prebuilt dist/ to the Evidaxis Vercel project.
# Robust against the dist/.vercel link being wiped on rebuild.
#
# Vercel project/org ids are NOT hardcoded — they load from a gitignored `deploy.env`
# at the repo root (see deploy.env.example), keeping the team/project ids out of the
# public repo. Set VERCEL_PROJECT_ID + VERCEL_ORG_ID there (or in the environment).
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
[ -f "$REPO/deploy.env" ] && { set -a; . "$REPO/deploy.env"; set +a; }
: "${VERCEL_PROJECT_ID:?set VERCEL_PROJECT_ID in deploy.env (repo root) or the environment}"
: "${VERCEL_ORG_ID:?set VERCEL_ORG_ID in deploy.env (repo root) or the environment}"
cd "$REPO/web"
npm run build
cp vercel.json dist/vercel.json
mkdir -p dist/.vercel
cat > dist/.vercel/project.json <<JSON
{"projectId":"${VERCEL_PROJECT_ID}","orgId":"${VERCEL_ORG_ID}","projectName":"${VERCEL_PROJECT_NAME:-evidaxis}"}
JSON
cd dist
vercel deploy --prod --yes
# Notify Bing/Yandex (and ChatGPT-fast-index via Bing) of changed URLs.
sleep 5 && python3 ../../etl/indexnow.py || true
# Fast-follow: replace this with Vercel root=repo + git-push CI.
