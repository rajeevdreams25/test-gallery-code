import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import ImageCard from '../components/ImageCard'
import UploadForm from '../components/UploadForm'

export default function Dashboard() {
  const { user, logout } = useAuth()
  const [images, setImages] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .listImages()
      .then(setImages)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const onUploaded = (image) => setImages((prev) => [image, ...prev])
  const onChanged = (image) =>
    setImages((prev) => prev.map((i) => (i.id === image.id ? { ...i, ...image } : i)))
  const onDeleted = (id) => setImages((prev) => prev.filter((i) => i.id !== id))

  return (
    <div className="page">
      <header className="topbar">
        <h1>My Gallery</h1>
        <div className="row">
          <span className="muted small">{user?.email}</span>
          <button className="ghost" onClick={logout}>
            Log out
          </button>
        </div>
      </header>

      {error && (
        <div className="alert" onClick={() => setError('')}>
          {error}
        </div>
      )}

      <UploadForm onUploaded={onUploaded} onError={setError} />

      {loading ? (
        <p className="muted">Loading your pictures…</p>
      ) : images.length === 0 ? (
        <p className="muted">No pictures yet — upload your first one above.</p>
      ) : (
        <div className="grid">
          {images.map((image) => (
            <ImageCard
              key={image.id}
              image={image}
              onChanged={onChanged}
              onDeleted={onDeleted}
              onError={setError}
            />
          ))}
        </div>
      )}
    </div>
  )
}
