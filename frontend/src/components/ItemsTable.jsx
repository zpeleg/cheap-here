import { useState, useMemo } from 'react'

const COLUMNS = [
  { key: 'name',    label: 'Item Name', cmp: (a, b) => a.name.localeCompare(b.name, 'he') },
  { key: 'barcode', label: 'Barcode',   cmp: (a, b) => a.barcode.localeCompare(b.barcode) },
  { key: 'price',   label: 'Price ₪',  cmp: (a, b) => a.price - b.price },
]

export default function ItemsTable({ items, storeID }) {
  const [search, setSearch]     = useState('')
  const [sortKey, setSortKey]   = useState('price')
  const [sortAsc, setSortAsc]   = useState(true)

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
          <h2 className="font-semibold text-gray-800">Store {storeID}</h2>
          <p className="text-xs text-gray-400 mt-0.5">
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
            {visible.map((item) => (
              <tr key={item.barcode} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 text-gray-900">{item.name}</td>
                <td className="px-4 py-3 text-gray-500 font-mono text-xs">{item.barcode}</td>
                <td className="px-4 py-3 font-semibold text-green-700">
                  ₪{item.price.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {visible.length === 0 && (
        <p className="text-center text-gray-400 py-10 text-sm">No items match your filter.</p>
      )}
    </div>
  )
}
