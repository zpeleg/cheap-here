import { useState, useEffect } from 'react'
import StoreSelector from './components/StoreSelector'
import ItemsTable from './components/ItemsTable'
import { setChainNames } from './chains'

const formatUpdated = (iso) => {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return null
  return d.toLocaleString('he-IL', {
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
          <h1 className="text-3xl font-bold text-gray-900">זול פה 🛒</h1>
          <p className="mt-1 text-sm text-gray-500">
            מוצרים שזולים בסניף הזה בלפחות 5% מהחציון בארץ
          </p>
          <details className="mt-2 text-xs text-gray-400">
            <summary className="cursor-pointer select-none hover:text-gray-600">
              מה המשמעות של העמודות?
            </summary>
            <dl className="mt-2 grid max-w-2xl gap-x-3 gap-y-1 sm:grid-cols-[auto_1fr]">
              <dt className="font-medium text-gray-500">מבצע ₪</dt>
              <dd>מחיר ליחידה במבצע כשבסניף יש מבצע פעיל — הקישו לתנאים המלאים של המבצע.</dd>
              <dt className="font-medium text-gray-500">מחיר ₪</dt>
              <dd>מחיר המדף הרגיל של הסניף (מחוק כשמבצע זול ממנו).</dd>
              <dt className="font-medium text-gray-500">במקום אחר ₪</dt>
              <dd>המחיר הזול ביותר לאותו מוצר ברשת מתחרה — הקישו לראות את המחיר בכל רשת.</dd>
              <dt className="font-medium text-gray-500">חציון ₪</dt>
              <dd>המחיר האמצעי של המוצר בכל החנויות בארץ.</dd>
              <dt className="font-medium text-gray-500">מקסימום ₪</dt>
              <dd>המחיר הגבוה ביותר של המוצר בכל הארץ.</dd>
              <dt className="font-medium text-gray-500">חיסכון ₪</dt>
              <dd>כמה חוסכים בקנייה כאן לעומת המחיר החציוני הארצי.</dd>
              <dt className="font-medium text-gray-500">מבצע</dt>
              <dd>כמה אחוזים מתחת לחציון הארצי נמצא מחיר הסניף.</dd>
            </dl>
          </details>
          {updatedAt && formatUpdated(updatedAt) && (
            <p className="mt-2 text-xs text-gray-400">
              עודכן לאחרונה {formatUpdated(updatedAt)}
            </p>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-6">
        <StoreSelector onSelect={handleStoreSelect} selected={store?.key} />

        {loading && (
          <p className="text-center text-gray-400 py-12">טוען נתוני חנות…</p>
        )}

        {error && (
          <div className="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700">
            טעינת החנות {store?.key} נכשלה: {error}
          </div>
        )}

        {!loading && store && !error && items.length === 0 && (
          <p className="text-center text-gray-400 py-12">
            לא נמצאו מוצרים זולים בחנות {store.key}.
          </p>
        )}

        {!loading && items.length > 0 && (
          <ItemsTable items={items} store={store} />
        )}
      </main>
    </div>
  )
}
