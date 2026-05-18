import { useState } from 'react'
import StoreSelector from './components/StoreSelector'
import ItemsTable from './components/ItemsTable'

export default function App() {
  const [storeID, setStoreID] = useState(null)
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleStoreSelect = async (id) => {
    setStoreID(id)
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/data/store_${id}.json`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setItems(await res.json())
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
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-6">
        <StoreSelector onSelect={handleStoreSelect} selected={storeID} />

        {loading && (
          <p className="text-center text-gray-400 py-12">Loading store data…</p>
        )}

        {error && (
          <div className="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700">
            Failed to load store {storeID}: {error}
          </div>
        )}

        {!loading && storeID && !error && items.length === 0 && (
          <p className="text-center text-gray-400 py-12">
            No cheapest items found for store {storeID}.
          </p>
        )}

        {!loading && items.length > 0 && (
          <ItemsTable items={items} storeID={storeID} />
        )}
      </main>
    </div>
  )
}
