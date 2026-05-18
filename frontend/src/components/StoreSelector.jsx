import { useState, useEffect } from 'react'

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
      .then((data) => setStores([...data].sort()))
      .catch(() => setFetchError(true))
      .finally(() => setLoading(false))
  }, [])

  const filtered = stores.filter((id) =>
    id.toLowerCase().includes(query.toLowerCase()),
  )

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 className="text-base font-semibold text-gray-700 mb-4">Select a branch</h2>

      <input
        type="search"
        placeholder="Search by store ID…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="w-full sm:w-72 border border-gray-300 rounded-lg px-4 py-2 text-sm mb-5
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

      {!loading && !fetchError && (
        <div className="flex flex-wrap gap-2">
          {filtered.map((id) => (
            <button
              key={id}
              onClick={() => onSelect(id)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
                ${
                  selected === id
                    ? 'bg-blue-600 text-white'
                    : 'bg-blue-50 text-blue-700 hover:bg-blue-100'
                }`}
            >
              {id}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
