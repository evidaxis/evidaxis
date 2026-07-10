# Действия хранителя — утро 2026-07-11 (после ночного прохода FIX-SPEC)

> Всё ниже подготовлено ночной сменой; каждый пункт = минимальный клик.
> Порядок = приоритет.

## 1. Zenodo v2 — новая версия под concept-DOI (~10 мин) — САМЫЙ БОЛЬШОЙ GEO-РЫЧАГ
Корпус чист (ось-2 линкована, идентичность content-addressed, person-free).
1. zenodo.org → My uploads → Evidaxis genesis deposit → **New version**.
2. Залить: `data/snapshots/2026-07-10/` (все 5 файлов) + `web/dist/llms.txt` +
   `CONSTITUTION.md` + `governance/` (6 драфтов можно позже, не блокер).
3. Title: `Evidaxis Observatory — snapshot 2026-07-10 (m2, 134 systems)`.
   Creator: `Evidaxis` (Organizational). License: CC0-1.0. Publish.
4. Сказать в чате новый version-DOI → я вошью в About/JSON-LD (follow-up WP-F).

## 2. HF-датасет `evidaxis/momentum-snapshots` (~10 мин)
1. huggingface.co → org evidaxis → New Dataset → `momentum-snapshots`, публичный, CC0.
2. Дать мне WRITE-токен (Settings → Access Tokens → fine-grained, только этот repo)
   → положить в `~/Projects/Evidaxis/etl/.env` строкой `HF_TOKEN=hf_...`
3. Дальше моё: карточка + parquet/JSON выгрузка + еженедельный авто-аплоад в weekly-CI.

## 3. Wikidata — НЕ СОЗДАВАТЬ (spar-22 остаётся в силе)
Проверил собственный леджер: spar-22 (2026-06-30, MiniMax+Kimi слепая конвергенция)
явно отменил создание: сам-депонированный DOI ≠ независимый якорь; COI-патруль риск;
founder указывать открыто, когда создадим. **Триггер: ≥1 настоящее независимое
стороннее упоминание Evidaxis** (журналист/блог/чужой датасет-каталог). HF+Zenodo v2 —
это путь К упоминанию, не замена. Ничего не делать до триггера.

## 4. CI-деплой: VERCEL_TOKEN (map#16 «прод-HTML не выводим из git») (~5 мин)
1. vercel.com → Settings → Tokens → создать токен.
2. GitHub evidaxis/evidaxis → Settings → Secrets → Actions: `VERCEL_TOKEN`,
   `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` (значения — в `deploy.env` локально).
3. Дальше моё: активирую deploy-web.yml, деплой уезжает с ноутбука в CI.

## 5. Зеркальный remote (map#7, вторая половина) (~5 мин)
GitLab (или Codeberg) → новый пустой проект `evidaxis/evidaxis` → deploy-token с
правом push → мне в `etl/.env` (`MIRROR_URL=`, `MIRROR_TOKEN=`) → я вошью
mirror-push шаг в weekly-CI. (SWH-архивация уже живёт, это второй слой.)

## 6. Governance-адъюдикации (голосом/кивком, я запишу)
- **СРОЧНОЕ (гейт ~15.07):** `DRAFT-m3-quarantine-adjudication.md` — рекомендация
  CONFIRM (m3 на живой линии через воронку + форвард-амендмент §4).
- `DRAFT-doctrine-v3-supersession.md` — подпись датированной суперсессии HALT.
- `DRAFT-succession-lock.md` · `DRAFT-donor-caps.md` (кап 33%?) ·
  `DRAFT-fork-license-covenant.md` · `DRAFT-provenance-quarantine.md`.
- `CANDIDATES-expansion-2026-07-10.md` — тайминг когорты gui-agents (не срочно).
