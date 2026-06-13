# Cheap Here — Improvement Backlog

The app's idea: **"I'm at (or near) branch X — what should I buy here?"** It surfaces
the items where a given branch has the national-best price. It is *not* an item-search /
"where is milk cheapest" tool — that's what CHP / Pricez already do. Keep features aligned
with the branch-first framing.

---

## 1. Location-based features (next focus)

The selector currently forces you to know a store ID. Make the app start from *where you
are* and lead you to the branches whose cheap-lists are worth checking.

- [ ] **City filter on the branch selector.** `city` is already resolved via
      [cbs_cities.json](etl/cbs_cities.json) / [cities.py](etl/cities.py) — expose it as a
      filter / grouping in [StoreSelector.jsx](frontend/src/components/StoreSelector.jsx).
- [ ] **"Branches near me" via geolocation.** Sort/filter branches by distance from the
      user's location. Needs lat/long per branch — the Stores XML feeds don't reliably
      include coordinates (`StoreInfo` only has address + city, see [db.py](etl/db.py:49)),
      so this likely requires geocoding by address/city in the ETL. Note as a dependency.
- [ ] **Map view of branches** (cluster pins by chain), tapping a pin opens that branch's
      cheap-list.
- [ ] **Default to a location-aware landing view** instead of the full alphabetical store
      list — "stores near you" first, full list as fallback.
- [ ] **Nearby trip suggestion.** Given the user's location, highlight the 2–3 nearest
      branches and what each is best for — still branch-first, just multi-branch.

---

## 2. Frontend UX / mobile

- [ ] **Fix the "Elsewhere" tooltip on touch devices.** It's driven purely by
      `onMouseEnter`/`onMouseLeave` ([ItemsTable.jsx](frontend/src/components/ItemsTable.jsx:225)),
      so the per-chain breakdown is dead on phones. Make it tap-to-open like the sale modal.
- [ ] **Mobile card layout.** The 9-column table only horizontally scrolls below `sm`;
      collapse to cards (TASKS 2.5).
- [ ] **RTL / Hebrew.** `index.html` is `lang="en"` with no `dir="rtl"`; item names are
      Hebrew. Add proper RTL handling on item cells / layout.
- [ ] **Cache fetched store JSON in `sessionStorage`.** Store files are large (Rami Levy /
      Victory ≈ 1.5 MB) and re-fetched + re-parsed on every (re)selection.
- [ ] **Virtual scrolling / pagination** for large branch lists.
- [ ] **Loading skeleton + empty-state illustration** instead of plain "Loading…" text.

---

## 3. ETL / data

- [ ] **Price history + drop alerts.** Pipeline overwrites daily with no persistence.
      Store daily snapshots → sparklines per item + "price dropped" highlights (Phase 5).
- [ ] **Item categories.** No categorization today; add a coarse barcode-prefix / keyword
      heuristic so a branch's cheap-list can be browsed by aisle (dairy, cleaning, …).
- [ ] **`run_summary.json` for observability.** Emit per-chain item/store counts + runtime
      + timestamp so the frontend can show coverage and a silently-broken chain is visible.
- [x] **Move chain metadata into `stores.json`.** Chain names now live in
      [chains.py](etl/chains.py); the ETL writes the present-chain subset into the
      `chains` map in `stores.json` and the frontend reads it at runtime
      ([chains.js](frontend/src/chains.js)) instead of hardcoding. Logos can be
      added to the same map later (TASKS 1.6).

---

## 4. Infra / quality

- [ ] **More tests.** Only [test_export.py](etl/test_export.py) (2 tests) exists. The
      promo-flattening logic in [db.py](etl/db.py:352) is gnarly and untested — add
      fixtures. No frontend tests at all (Vitest + a Playwright smoke test, TASKS 2.6).
- [ ] **Lint job in CI** — `eslint` on frontend, a Python linter on ETL (TASKS 3.3).
- [ ] **Job timeout + data artifact upload** in the pipeline for debugging failed runs.
- [ ] **SEO / polish:** [index.html](frontend/index.html) has no meta description, OG
      tags, or favicon.

---

## 5. Quick fixes / bugs

- [x] **Duplicate chain entry.** `VICTORY_NEW_SOURCE` dedup'd and the chain list
      hoisted to a shared top-level `chains` key in [stores.json](etl/stores.json);
      profiles now differ only by `limit`.
- [ ] **Empty tracked `logging.log`** at the repo root — drop it / gitignore it.
