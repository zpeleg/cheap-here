import { useState, useMemo } from 'react'

const COLUMNS = [
  { key: 'name',    label: 'Item Name', cmp: (a, b) => a.name.localeCompare(b.name, 'he') },
  { key: 'barcode', label: 'Barcode',   cmp: (a, b) => a.barcode.localeCompare(b.barcode) },
  { key: 'sale',    label: 'Sale ₪',    cmp: (a, b) => salePrice(a) - salePrice(b) },
  { key: 'price',   label: 'Price ₪',   cmp: (a, b) => a.price - b.price },
]

const CHAIN_NAMES = {
  '7290027600007': 'Shufersal',
  '7290058140886': 'Rami Levy',
  '7290873255550': 'Tiv Taam',
  '7290803800003': 'Yohananof',
  '7290103152017': 'Osher Ad',
  '7290696200003': 'Victory',
  '7290058103393': 'Victory',
}

// Sentinel so unsorted-on-sale-column rows sort last instead of treating
// "no sale" as ₪0. Plays well with both ascending and descending order.
const NO_SALE = Number.POSITIVE_INFINITY

function salePrice(item) {
  return item.sale ? item.sale.perUnitPrice : NO_SALE
}

function formatISODate(iso) {
  if (!iso) return null
  const [y, m, d] = iso.split('-')
  if (!y || !m || !d) return iso
  return `${d}/${m}/${y}`
}

export default function ItemsTable({ items, store }) {
  const [search, setSearch]     = useState('')
  const [sortKey, setSortKey]   = useState('price')
  const [sortAsc, setSortAsc]   = useState(true)
  const [activeSale, setActiveSale] = useState(null) // { item, sale }

  const toggleSort = (key) => {
    if (sortKey === key) setSortAsc((v) => !v)
    else { setSortKey(key); setSortAsc(true) }
  }

  const visible = useMemo(() => {
    const q = search.toLowerCase()
    const base = q
      ? items.filter(
          (i) => i.name.toLowerCase().includes(q) || i.barcode.includes(q),
        )
      : items

    const col = COLUMNS.find((c) => c.key === sortKey)
    return [...base].sort((a, b) => sortAsc ? col.cmp(a, b) : col.cmp(b, a))
  }, [items, search, sortKey, sortAsc])

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 border-b border-gray-100">
        <div>
          <h2 className="font-semibold text-gray-800">
            {CHAIN_NAMES[store?.chainId] || store?.chainId} · Store #{store?.storeId}
            {store?.storeName && <span className="text-gray-500 font-normal"> — {store.storeName}</span>}
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            {store?.city && <>{store.city} · </>}
            {visible.length} cheapest items nationally
          </p>
        </div>
        <input
          type="search"
          placeholder="Filter by name or barcode…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-full sm:w-64
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
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
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {visible.length === 0 && (
        <p className="text-center text-gray-400 py-10 text-sm">No items match your filter.</p>
      )}

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
