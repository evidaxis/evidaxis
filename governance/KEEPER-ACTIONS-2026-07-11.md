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

## 2. HF-датасет — ✅ СДЕЛАНО (2026-07-11): huggingface.co/datasets/evidaxis/momentum-snapshots
Залит чисто (2 person-free утечки пойманы и вычищены; fail-closed гвард вшит), авто-обновление в weekly-CI. ⚠️ ОСТАЛОСЬ: удали личный дубль https://huggingface.co/datasets/ivitskiy/momentum-snapshots (Settings → Delete). Ниже — исходная инструкция (архив):

### (архив) HF-датасет `evidaxis/momentum-snapshots` (~10 мин)
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

## 4. CI-деплой VERCEL — ✅ СДЕЛАНО: секреты стоят, авто-деплой на пуш активен (map#16 закрыт). Токен светился в чате — можешь пересоздать на vercel.com/account/tokens и сказать мне.

### (архив) VERCEL_TOKEN
1. vercel.com → Settings → Tokens → создать токен.
2. GitHub evidaxis/evidaxis → Settings → Secrets → Actions: `VERCEL_TOKEN`,
   `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` (значения — в `deploy.env` локально).
3. Дальше моё: активирую deploy-web.yml, деплой уезжает с ноутбука в CI.

## 5. GitLab-зеркало — ⚠️ ОДИН КЛИК ОСТАЛСЯ: вставить SSH-ключ
Deploy/access-токены у тебя отключены Free-тарифом → ушли на SSH deploy-key (приватный
уже в секретах). Открой https://gitlab.com/evidaxis/evidaxis/-/settings/repository →
раздел **Deploy keys** → Add new key → Title `github-mirror` → ✅ **Grant write permissions**
→ в поле Key вставь публичный ключ (я дам в чате) → Add key. Всё, зеркало проснётся на
следующем пуше. (Read-only deploy-token gldt-... можешь удалить — он не годится для push.)

### (архив) Зеркальный remote
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

## 7. Адъюдикация: Invariant-1 ↔ байт-верифицируемость (вскрыто финальным реаудитом)
Веб-версия snapshot.json — person-free ПРОЕКЦИЯ (без личных хэндлов), а SHA256SUMS
пинует КАНОНИЧЕСКИЕ байты git-архива → `sha256sum -c` на веб-скачивании падает.
Ночной фикс: честная подпись на странице бандла («суммы пинуют канонические байты;
веб-JSON — публикационная проекция»). Глубокое решение — твоё, три опции:
(а) оставить как есть (проекция + подпись) — статус-кво, честно;
(б) веб отдаёт сырые байты (хэндлы вернутся на веб-поверхность — против WP-D);
(в) убрать личные слаги из БУДУЩИХ архивных файлов (коллектор пишет canonical/номер,
    слаг остаётся только во внутреннем id_map) — самое чистое, но методологический шаг.
Рекомендую (в) форвардно + (а) для опубликованного. Связано с tombstone-решением WP-D.
