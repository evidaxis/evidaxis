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
npm run check                       # dist invariant gate (em-dash / SSR charts / JSON-LD / headings) before prod
cp vercel.json dist/vercel.json
mkdir -p dist/.vercel
cat > dist/.vercel/project.json <<JSON
{"projectId":"${VERCEL_PROJECT_ID}","orgId":"${VERCEL_ORG_ID}","projectName":"${VERCEL_PROJECT_NAME:-evidaxis}"}
JSON
# Provenance: record exactly what is being shipped, bound to the git tree it
# was built from, BEFORE deploying. Until the build moves into CI (fast-follow
# below), this manifest is what makes the laptop-built prod HTML auditable.
GIT_SHA=$(git -C "$REPO" rev-parse HEAD)
GIT_DIRTY=$(git -C "$REPO" status --porcelain | wc -l | tr -d ' ')
DIST_SHA=$(cd dist && find . -type f ! -path './.vercel/*' -print0 | sort -z | xargs -0 shasum -a 256 | shasum -a 256 | cut -d' ' -f1)
mkdir -p "$REPO/data/integrity"
cat > "$REPO/data/integrity/site-manifest-$(date -u +%Y-%m-%dT%H%M%SZ).json" <<MANIFEST
{
  "v": "site_manifest_1",
  "deployed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "git_commit": "${GIT_SHA}",
  "working_tree_dirty_files": ${GIT_DIRTY},
  "dist_sha256": "${DIST_SHA}",
  "note": "sha256 over the sorted per-file sha256 list of web/dist; laptop-built (see deploy.sh); binds the shipped HTML to the source tree"
}
MANIFEST
cd dist
vercel deploy --prod --yes
# Notify Bing/Yandex (and ChatGPT-fast-index via Bing) of changed URLs.
sleep 5 && python3 ../../etl/indexnow.py || true
# Fast-follow: replace this with Vercel root=repo + git-push CI
# (.github/workflows/deploy-web.yml is staged for that; needs VERCEL_TOKEN secret).
