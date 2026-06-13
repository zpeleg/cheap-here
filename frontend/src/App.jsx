import { useState, useEffect } from 'react'
import StoreSelector from './components/StoreSelector'
import ItemsTable from './components/ItemsTable'
import { setChainNames } from './chains'

const formatUpdated = (iso) => {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return null
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function App() {
  const [store, setStore] = useState(null)
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [updatedAt, setUpdatedAt] = useState(null)

  // The data export stamps stores.json with the time the ETL last ran; surface
  // it so visitors know how fresh the prices are.
  useEffect(() => {
    fetch('/data/stores.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.chains) setChainNames(data.chains)
        setUpdatedAt(data?.updatedAt ?? null)
      })
      .catch(() => {})
  }, [])

  const handleStoreSelect = async (s) => {
    setStore(s)
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/data/store_${s.key}.json`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setItems(data.items || [])
    } catch (e) {
      setError(e.message)
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">Cheap Here 🛒</h1>
          <p className="mt-1 text-sm text-gray-500">
            Items where this branch has the cheapest price nationally
          </p>
          {updatedAt && formatUpdated(updatedAt) && (
            <p className="mt-2 text-xs text-gray-400">
              Last updated {formatUpdated(updatedAt)}
            </p>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-6">
        <StoreSelector onSelect={handleStoreSelect} selected={store?.key} />

        {loading && (
          <p className="text-center text-gray-400 py-12">Loading store data…</p>
        )}

        {error && (
          <div className="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700">
            Failed to load store {store?.key}: {error}
          </div>
        )}

        {!loading && store && !error && items.length === 0 && (
          <p className="text-center text-gray-400 py-12">
            No cheapest items found for store {store.key}.
          </p>
        )}

        {!loading && items.length > 0 && (
          <ItemsTable items={items} store={store} />
        )}
      </main>
    </div>
  )
}
