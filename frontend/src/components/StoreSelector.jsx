import { useState, useEffect, useMemo } from 'react'

const CHAIN_NAMES = {
  '7290027600007': 'Shufersal',
  '7290058140886': 'Rami Levy',
  '7290873255550': 'Tiv Taam',
  '7290803800003': 'Yohananof',
  '7290103152017': 'Osher Ad',
  '7290696200003': 'Victory',
  '7290058103393': 'Victory',
  '7290058249350': 'Wolt Market',
  '7290058197699': 'Good Pharm',
  '7290055700007': 'Carrefour',
  '7290700100008': 'Hazi Hinam',
}

const chainLabel = (id) => CHAIN_NAMES[id] || id

export default function StoreSelector({ onSelect, selected }) {
  const [stores, setStores] = useState([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState(false)

  useEffect(() => {
    fetch('/data/stores.json')
      .then((r) => {
        if (!r.ok) throw new Error()
        return r.json()
      })
      .then((data) => setStores(data.stores || []))
      .catch(() => setFetchError(true))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return stores
    return stores.filter((s) => {
      const hay = [
        s.storeId,
        s.key,
        s.storeName,
        s.city,
        s.address,
        chainLabel(s.chainId),
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
      return hay.includes(q)
    })
  }, [stores, query])

  const grouped = useMemo(() => {
    const map = new Map()
    for (const s of filtered) {
      if (!map.has(s.chainId)) map.set(s.chainId, [])
      map.get(s.chainId).push(s)
    }
    for (const list of map.values()) {
      list.sort((a, b) => a.storeId.localeCompare(b.storeId, undefined, { numeric: true }))
    }
    return [...map.entries()].sort((a, b) => chainLabel(a[0]).localeCompare(chainLabel(b[0])))
  }, [filtered])

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 className="text-base font-semibold text-gray-700 mb-4">Select a branch</h2>

      <input
        type="search"
        placeholder="Search by store ID, name, or city…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="w-full sm:w-96 border border-gray-300 rounded-lg px-4 py-2 text-sm mb-5
                   focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      />

      {loading && <p className="text-sm text-gray-400">Loading stores…</p>}

      {fetchError && (
        <p className="text-sm text-red-500">
          Could not load stores.json — run the ETL pipeline first.
        </p>
      )}

      {!loading && !fetchError && filtered.length === 0 && (
        <p className="text-sm text-gray-400">No stores match "{query}".</p>
      )}

      {!loading && !fetchError && grouped.map(([chainId, list]) => (
        <div key={chainId} className="mb-5 last:mb-0">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            {chainLabel(chainId)} <span className="text-gray-400 font-normal">({list.length})</span>
          </h3>
          <div className="flex flex-wrap gap-2">
            {list.map((s) => {
              const isSelected = selected === s.key
              const sub = [s.city, s.storeName].filter(Boolean).join(' · ')
              return (
                <button
                  key={s.key}
                  onClick={() => onSelect(s)}
                  title={sub || s.key}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
                    ${
                      isSelected
                        ? 'bg-blue-600 text-white'
                        : 'bg-blue-50 text-blue-700 hover:bg-blue-100'
                    }`}
                >
                  #{s.storeId}
                  {sub && (
                    <span className={`ml-2 text-xs ${isSelected ? 'text-blue-100' : 'text-blue-500'}`}>
                      {sub}
                    </span>
                  )}
                  <span className={`ml-2 text-xs ${isSelected ? 'text-blue-100' : 'text-gray-400'}`}>
                    {s.itemCount}
                  </span>
                </button>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
