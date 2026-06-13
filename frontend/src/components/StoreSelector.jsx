import { useState, useEffect, useMemo } from 'react'
import { chainName as chainLabel, setChainNames } from '../chains'

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
      .then((data) => {
        setChainNames(data.chains)
        setStores(data.stores || [])
      })
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
      <h2 className="text-base font-semibold text-gray-700 mb-4">בחרו סניף</h2>

      <input
        type="search"
        placeholder="חיפוש לפי מספר חנות, שם או עיר…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="w-full sm:w-96 border border-gray-300 rounded-lg px-4 py-2 text-sm mb-5
                   focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      />

      {loading && <p className="text-sm text-gray-400">טוען חנויות…</p>}

      {fetchError && (
        <p className="text-sm text-red-500">
          לא ניתן לטעון את stores.json — הריצו תחילה את תהליך ה‑ETL.
        </p>
      )}

      {!loading && !fetchError && filtered.length === 0 && (
        <p className="text-sm text-gray-400">אין חנויות שתואמות ל‑"{query}".</p>
      )}

      {!loading && !fetchError && grouped.map(([chainId, list]) => (
        <div key={chainId} className="mb-5 last:mb-0">
          <h3 className="text-xs font-semibold text-gray-500 tracking-wider mb-2">
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
                    <span className={`ms-2 text-xs ${isSelected ? 'text-blue-100' : 'text-blue-500'}`}>
                      {sub}
                    </span>
                  )}
                  <span className={`ms-2 text-xs ${isSelected ? 'text-blue-100' : 'text-gray-400'}`}>
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
