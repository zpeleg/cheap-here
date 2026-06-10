import { useState, useMemo, useEffect } from 'react'
import { chainName } from '../chains'

const COLUMNS = [
  // name can be null (some chains omit it for store-brand barcodes)
  { key: 'name',    label: 'Item Name', cmp: (a, b) => (a.name || '').localeCompare(b.name || '', 'he') },
  { key: 'barcode', label: 'Barcode',   cmp: (a, b) => a.barcode.localeCompare(b.barcode) },
  { key: 'sale',    label: 'Sale ₪',    cmp: (a, b) => salePrice(a) - salePrice(b) },
  { key: 'price',   label: 'Price ₪',   cmp: (a, b) => a.price - b.price },
  { key: 'others',  label: 'Elsewhere ₪', cmp: (a, b, store) => cheapestOtherPrice(a, store) - cheapestOtherPrice(b, store) },
  { key: 'median',  label: 'Median ₪',  cmp: (a, b) => (a.medianPrice ?? 0) - (b.medianPrice ?? 0) },
  { key: 'max',     label: 'Max ₪',     cmp: (a, b) => (a.maxPrice ?? 0) - (b.maxPrice ?? 0) },
  { key: 'saved',   label: 'Saved ₪',   cmp: (a, b) => savedVsMedian(a) - savedVsMedian(b), defaultDesc: true },
  { key: 'deal',    label: 'Deal',      cmp: (a, b) => dealPct(a) - dealPct(b), defaultDesc: true },
]

// Sentinel so unsorted-on-sale-column rows sort last instead of treating
// "no sale" as ₪0. Plays well with both ascending and descending order.
const NO_SALE = Number.POSITIVE_INFINITY

function salePrice(item) {
  return item.sale ? item.sale.perUnitPrice : NO_SALE
}

function effectivePrice(item) {
  return item.effectivePrice ?? (item.sale ? item.sale.perUnitPrice : item.price)
}

// Fraction below the cross-store median (0.23 = 23% cheaper than median).
// Exported items are near the national-cheapest price, but that can still sit
// slightly above the median when prices cluster, so small negatives happen.
// -Infinity sorts rows without median data (pre-feature exports) last.
function dealPct(item) {
  if (!item.medianPrice) return Number.NEGATIVE_INFINITY
  return (item.medianPrice - effectivePrice(item)) / item.medianPrice
}

// Absolute ₪ saved vs the cross-store median. Slightly negative is possible
// (see dealPct); -Infinity sorts missing-data rows last.
function savedVsMedian(item) {
  if (!item.medianPrice) return Number.NEGATIVE_INFINITY
  return item.medianPrice - effectivePrice(item)
}

// Total branches nationally that carry the item, summed across chains.
// null when the export predates chainPrices; those rows pass the min-stores
// filter rather than silently vanishing on old data.
function storeCount(item) {
  if (!item.chainPrices) return null
  return item.chainPrices.reduce((n, [, , branches]) => n + branches, 0)
}

// chainPrices entries ([chainId, minPrice, branchCount], cheapest-first per
// the exporter) for every chain except the one being viewed.
function otherChainPrices(item, store) {
  if (!item.chainPrices) return []
  return item.chainPrices.filter(([chainId]) => chainId !== store?.chainId)
}

// Cheapest competing chain's min price. Infinity sorts items without
// cross-chain data last, same trick as NO_SALE above.
function cheapestOtherPrice(item, store) {
  const others = otherChainPrices(item, store)
  return others.length ? others[0][1] : Number.POSITIVE_INFINITY
}

function formatISODate(iso) {
  if (!iso) return null
  const [y, m, d] = iso.split('-')
  if (!y || !m || !d) return iso
  return `${d}/${m}/${y}`
}

export default function ItemsTable({ items, store }) {
  const [search, setSearch]     = useState('')
  const [minStores, setMinStores] = useState('') // hide items carried by fewer branches
  const [sortKey, setSortKey]   = useState('deal')
  const [sortAsc, setSortAsc]   = useState(false) // deal sorts best-first by default
  const [activeSale, setActiveSale] = useState(null) // { item, sale }
  const [chainTip, setChainTip] = useState(null) // { item, left, top, bottom, above }

  // The tooltip is position:fixed (the table's overflow-x-auto would clip an
  // absolutely positioned one), so any scroll leaves it floating — dismiss.
  useEffect(() => {
    if (!chainTip) return
    const hide = () => setChainTip(null)
    window.addEventListener('scroll', hide, true)
    return () => window.removeEventListener('scroll', hide, true)
  }, [chainTip])

  const showChainTip = (item, cell) => {
    const rect = cell.getBoundingClientRect()
    const estHeight = item.chainPrices.length * 28 + 40
    setChainTip({
      item,
      left: Math.max(8, Math.min(rect.left, window.innerWidth - 288)),
      top: rect.bottom + 6,
      bottom: window.innerHeight - rect.top + 6,
      above: rect.bottom + estHeight + 6 > window.innerHeight,
    })
  }

  const toggleSort = (key) => {
    if (sortKey === key) setSortAsc((v) => !v)
    else {
      setSortKey(key)
      setSortAsc(!COLUMNS.find((c) => c.key === key).defaultDesc)
    }
  }

  const visible = useMemo(() => {
    const q = search.toLowerCase()
    let base = q
      ? items.filter(
          (i) => (i.name || '').toLowerCase().includes(q) || i.barcode.includes(q),
        )
      : items

    const threshold = Number(minStores) || 0
    if (threshold > 1) {
      base = base.filter((i) => {
        const n = storeCount(i)
        return n == null || n >= threshold
      })
    }

    const col = COLUMNS.find((c) => c.key === sortKey)
    return [...base].sort((a, b) => sortAsc ? col.cmp(a, b, store) : col.cmp(b, a, store))
  }, [items, search, minStores, sortKey, sortAsc, store])

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 border-b border-gray-100">
        <div>
          <h2 className="font-semibold text-gray-800">
            {chainName(store?.chainId)} · Store #{store?.storeId}
            {store?.storeName && <span className="text-gray-500 font-normal"> — {store.storeName}</span>}
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            {store?.city && <>{store.city} · </>}
            {visible.length} items cheapest in the country here (or within 5%)
          </p>
        </div>
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-gray-500 whitespace-nowrap">
            Sold in ≥
            <input
              type="number"
              min="2"
              placeholder="any"
              value={minStores}
              onChange={(e) => setMinStores(e.target.value)}
              className="border border-gray-300 rounded-lg px-2 py-1.5 text-sm w-16 text-gray-900
                         focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            stores
          </label>
          <input
            type="search"
            placeholder="Filter by name or barcode…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-full sm:w-64
                       focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  onClick={() => toggleSort(col.key)}
                  className="px-4 py-3 cursor-pointer select-none hover:bg-gray-100 whitespace-nowrap"
                >
                  {col.label}
                  {sortKey === col.key && (
                    <span className="ml-1 text-blue-500">
                      {sortAsc ? '↑' : '↓'}
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {visible.map((item) => {
              const hasSale = !!item.sale
              const pct = item.medianPrice ? dealPct(item) : null
              const saved = item.medianPrice != null ? savedVsMedian(item) : null
              const others = otherChainPrices(item, store)
              return (
                <tr key={item.barcode} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 text-gray-900">{item.name}</td>
                  <td className="px-4 py-3 text-gray-500 font-mono text-xs">{item.barcode}</td>
                  <td className="px-4 py-3">
                    {hasSale ? (
                      <button
                        type="button"
                        onClick={() => setActiveSale({ item, sale: item.sale })}
                        className="inline-flex items-center gap-1 rounded-md bg-red-600 px-2.5 py-1
                                   text-xs font-semibold text-white shadow-sm
                                   hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
                        title="Click for sale details"
                      >
                        <span aria-hidden>*</span> {item.sale.perUnitPrice.toFixed(2)}
                      </button>
                    ) : (
                      <span className="text-gray-300">—</span>
                    )}
                  </td>
                  <td className={
                    'px-4 py-3 font-semibold ' +
                    (hasSale ? 'text-gray-400 line-through' : 'text-green-700')
                  }>
                    ₪{item.price.toFixed(2)}
                  </td>
                  <td
                    className="px-4 py-3 whitespace-nowrap"
                    onMouseEnter={others.length ? (e) => showChainTip(item, e.currentTarget) : undefined}
                    onMouseLeave={others.length ? () => setChainTip(null) : undefined}
                  >
                    {others.length ? (
                      <span className="cursor-help border-b border-dotted border-gray-400">
                        <span className="text-gray-700">₪{others[0][1].toFixed(2)}</span>
                        <span className="ml-1 text-xs text-gray-400">{chainName(others[0][0])}</span>
                        {others.length > 1 && (
                          <span className="ml-1 text-xs font-medium text-blue-500">+{others.length - 1}</span>
                        )}
                      </span>
                    ) : (
                      <span className="text-gray-300">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {item.medianPrice != null ? `₪${item.medianPrice.toFixed(2)}` : <span className="text-gray-300">—</span>}
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {item.maxPrice != null ? `₪${item.maxPrice.toFixed(2)}` : <span className="text-gray-300">—</span>}
                  </td>
                  <td className={
                    'px-4 py-3 font-medium ' +
                    (saved != null && saved < 0 ? 'text-gray-400' : 'text-green-700')
                  }>
                    {saved != null
                      ? `${saved < 0 ? '−' : ''}₪${Math.abs(saved).toFixed(2)}`
                      : <span className="text-gray-300 font-normal">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    {pct != null ? (
                      <span className={
                        'inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold ' +
                        (pct < 0 ? 'bg-gray-100 text-gray-500' : 'bg-green-100 text-green-700')
                      }>
                        {pct < 0 ? '+' : '−'}{Math.abs(Math.round(pct * 100))}%
                      </span>
                    ) : (
                      <span className="text-gray-300">—</span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {visible.length === 0 && (
        <p className="text-center text-gray-400 py-10 text-sm">No items match your filter.</p>
      )}

      {chainTip && <ChainPricesTip tip={chainTip} store={store} />}

      {activeSale && (
        <SaleModal
          item={activeSale.item}
          sale={activeSale.sale}
          onClose={() => setActiveSale(null)}
        />
      )}
    </div>
  )
}

function ChainPricesTip({ tip, store }) {
  const { item, left, top, bottom, above } = tip
  return (
    <div
      className="fixed z-50 w-72 rounded-lg border border-gray-200 bg-white
                 shadow-lg pointer-events-none"
      style={{ left, ...(above ? { bottom } : { top }) }}
    >
      <div className="px-3 py-1.5 border-b border-gray-100 text-[11px] font-medium uppercase
                      tracking-wider text-gray-400">
        Cheapest per chain
      </div>
      <div className="py-1">
        {item.chainPrices.map(([chainId, price, branches]) => {
          const isHere = chainId === store?.chainId
          return (
            <div
              key={chainId}
              className={
                'flex items-baseline justify-between gap-4 px-3 py-1 text-xs ' +
                (isHere ? 'bg-blue-50' : '')
              }
            >
              <span className={isHere ? 'font-semibold text-blue-700' : 'text-gray-700'}>
                {chainName(chainId)}
                {isHere && ' · here'}
                <span className="ml-1 text-gray-400 font-normal">
                  {branches > 1 ? `${branches} stores` : '1 store'}
                </span>
              </span>
              <span className={'font-medium ' + (isHere ? 'text-blue-700' : 'text-gray-900')}>
                ₪{price.toFixed(2)}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function SaleModal({ item, sale, onClose }) {
  const qty = sale.minQty || 1
  const qtyDisplay = Number.isInteger(qty) ? qty : qty.toFixed(2)
  const validUntil = formatISODate(sale.endDate)
  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-lg max-w-sm w-full overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="bg-gray-100 px-4 py-2 text-sm font-semibold text-gray-700 text-center">
          Sale details
        </div>
        <div className="p-5 space-y-2 text-center">
          <p className="text-sm text-gray-500 truncate">{item.name}</p>
          <p className="text-base text-gray-900">
            {qtyDisplay} unit{qty === 1 ? '' : 's'} for ₪{sale.totalPrice.toFixed(2)}
          </p>
          <p className="text-sm text-gray-500">
            (₪{sale.perUnitPrice.toFixed(2)} per unit)
          </p>
          {sale.description && (
            <p className="text-xs text-gray-400 pt-1">{sale.description}</p>
          )}
          {validUntil && (
            <p className="text-sm text-gray-600 pt-2">Valid until {validUntil}</p>
          )}
        </div>
        <div className="px-5 pb-4 text-center">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md bg-gray-200 px-4 py-1.5 text-sm font-medium text-gray-700
                       hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-400"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
