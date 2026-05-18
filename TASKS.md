# Cheap Here — Project Tasklist

Track progress across sessions. Check off items as they are completed.

---

## Phase 0 — Repository Hygiene

- [x] Scaffold monorepo directory structure
- [x] Create `.gitignore` (exclude generated JSONs, `dist/`, `node_modules/`, `.db` files)
- [x] Add `frontend/public/data/.gitkeep`
- [x] `git init` and make initial commit
- [ ] Create GitHub repository and push
- [ ] Add branch protection rule on `main`

---

## Phase 1 — ETL Pipeline (Python + DuckDB + il-supermarket-scraper)

### 1.1 Project setup
- [x] `etl/requirements.txt` — `il-supermarket-scraper`, `duckdb`
- [x] Run `pip install -r requirements.txt` in `etl/` locally

### 1.2 Configuration
- [x] `config.py` — load `stores.json` (chain list + output dir) via `$CONFIG_PATH` env var
- [x] Populate `etl/stores.json` with real chain names (`ScraperFactory` keys)
  - [x] Check `ScraperFactory` for available chains (SHUFERSAL, RAMI_LEVY, VICTORY, MEGA, etc.)
  - [x] Start with 1–2 chains and verify end-to-end before enabling all

### 1.3 Downloader (il-supermarket-scraper)
- [x] `scraper.py` — wraps `ScarpingTask`; downloads to temp dir, returns `.xml` paths
- [ ] Test outside Israel (some chains may be geo-blocked; use a proxy or GitHub Actions runner)
- [ ] Tune `limit` in `stores.json` for faster dev iterations (e.g. `5`)

### 1.4 XML Parser
- [x] `parser.py` — `iterparse` state-machine; handles plain and gzip XML
- [x] Tag names normalised to lowercase; strips XML namespaces
- [x] Extracts: `chain_id`, `store_id`, `barcode`, `name`, `price`
- [ ] **Test with real XML files from each chain** — extend `_BARCODE_TAGS` / `_NAME_TAGS` / `_PRICE_TAGS` as needed
- [ ] Handle files where `store_id` is absent from XML (fall back to filename parsing)
- [ ] Add unit tests with local XML fixture files

### 1.5 DuckDB layer
- [x] `db.py` — `Store` class: `create_schema`, `batch_insert`, `find_cheapest`, `close`
- [x] `find_cheapest` — `MIN(price)` CTE joined back to prices table
- [ ] Add index: `CREATE INDEX ON prices (barcode, price)` for faster aggregation on large datasets
- [ ] Add per-chain item count log after ingestion

### 1.6 JSON Export
- [x] `export.py` — writes `store_<id>.json` and `stores.json` index
- [ ] Add `updatedAt` ISO-8601 timestamp field to each store file
- [ ] Add chain metadata (chain name, logo URL) to `stores.json` index
- [ ] Pre-sort items by price ascending so the default table view is instant

### 1.7 End-to-end ETL test
- [ ] Run `python main.py` in `etl/` locally with at least one chain configured
- [ ] Verify `frontend/public/data/` contains at least one `store_*.json`
- [ ] Spot-check a store file: prices are positive, names are valid Hebrew strings
- [ ] Write integration test using a local sample XML fixture

---

## Phase 2 — Frontend (React + Vite + TailwindCSS)

### 2.1 Project setup
- [x] `package.json`, `vite.config.js`, `tailwind.config.js`, `postcss.config.js`
- [ ] Run `npm install` locally
- [ ] Confirm `npm run dev` starts the Vite dev server

### 2.2 Core components
- [x] `App.jsx` — top-level state, store selection handler, fetch logic
- [x] `StoreSelector.jsx` — loads `stores.json`, pill buttons, live search filter
- [x] `ItemsTable.jsx` — sortable columns (name / barcode / price), text filter

### 2.3 UX improvements
- [ ] Display chain name alongside store ID (requires chain metadata in `stores.json`)
- [ ] Add a "Cheapest items in the whole country" view (cross-store minimum)
- [ ] Add pagination or virtual scrolling for stores with >500 items
- [ ] Show a loading skeleton instead of plain "Loading…" text
- [ ] Add empty-state illustration for "no stores loaded yet"
- [ ] RTL layout support for Hebrew item names (`dir="rtl"` on table cells)
- [ ] Add a "Copy barcode" button on each row

### 2.4 Performance
- [ ] Cache fetched store JSON in `sessionStorage` to avoid re-fetching on re-select
- [ ] Add `<link rel="prefetch">` for the last-selected store

### 2.5 Accessibility & polish
- [ ] Keyboard navigation in `StoreSelector` (arrow keys, Enter to select)
- [ ] ARIA labels on sort buttons
- [ ] Favicon and Open Graph meta tags in `index.html`
- [ ] Mobile: collapse table to card layout below `sm` breakpoint

### 2.6 Frontend tests
- [ ] Set up Vitest
- [ ] Unit test `ItemsTable` sorting and filtering logic
- [ ] Unit test `StoreSelector` search filter
- [ ] Add a Playwright smoke test: select a store → table renders rows

---

## Phase 3 — CI/CD Pipeline (GitHub Actions)

### 3.1 Pipeline file
- [x] `pipeline.yml` — push to `main` + daily cron at 02:00 UTC + `workflow_dispatch`
- [x] Python 3.12 setup for ETL; Node.js 20 setup for frontend (separate steps)
- [x] ETL `pip install -r requirements.txt` + `python main.py`
- [x] Verification step (fail loudly if no `store_*.json` generated)
- [x] Frontend `npm ci` + `npm run build`
- [x] Cloudflare Pages deploy action

### 3.2 Secrets & configuration
- [ ] Add `CLOUDFLARE_API_TOKEN` to GitHub repository secrets
- [ ] Add `CLOUDFLARE_ACCOUNT_ID` to GitHub repository secrets
- [ ] Create Cloudflare Pages project named `cheap-here`
- [ ] Set custom domain on Cloudflare Pages (optional)

### 3.3 Robustness
- [ ] Add a job-level timeout (`timeout-minutes: 30`) to prevent runaway ETL
- [ ] Upload `frontend/public/data/` as a workflow artifact for debugging failed runs
- [ ] Send a Slack / email notification on pipeline failure
- [ ] Add a separate `lint` job: `tsc --noEmit` on ETL + `eslint` on frontend

### 3.4 Observability
- [ ] Log total item count, store count, and runtime duration at pipeline end
- [ ] Write a `run_summary.json` (counts, timestamp, duration) for the frontend to display
- [ ] Set up Cloudflare Analytics on the Pages project

---

## Phase 4 — Data Quality & Chain Coverage

- [ ] Map out all Israeli chains that publish public price XML feeds
- [ ] Confirm XML schema per chain and update `DOC_FIELDS` / `ITEM_FIELDS` as needed
- [ ] Handle chains that publish per-store files (discover and loop all store URLs)
- [ ] Handle chains that publish a single national file with a `storeId` per item
- [ ] Deduplicate barcodes that appear under multiple names (pick the most common name)
- [ ] Filter out non-product entries (price = 0 or barcode = "0")
- [ ] Validate that `stores.json` index matches the deployed store files exactly

---

## Phase 5 — Optional Enhancements

- [ ] Price history: persist daily snapshots and show a sparkline per item
- [ ] "Price alert" mode: compare today's file against yesterday's and highlight drops
- [ ] Category grouping using barcode prefix heuristics or a lookup table
- [ ] Search across all stores (national cheapest per barcode, not per branch)
- [ ] PWA: add `manifest.json` and a service worker for offline access
- [ ] Dark mode toggle

---

## Definition of Done

A session is shippable when:
1. `python main.py` in `/etl` (with chains configured) produces at least one `store_*.json` with valid data
2. `npm run build` in `/frontend` exits 0
3. The GitHub Actions pipeline runs green end-to-end
4. The Cloudflare Pages URL loads, shows stores, and a store selection renders a populated table
