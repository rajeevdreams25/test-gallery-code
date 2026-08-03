import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api'

export default function SharedImage() {
  const { token } = useParams()
  const [image, setImage] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .publicImage(token)
      .then(setImage)
      .catch((err) => setError(err.message))
  }, [token])

  if (error) return <div className="center muted">{error}</div>
  if (!image) return <div className="center muted">Loading…</div>

  return (
    <div className="center">
      <div className="card shared">
        {/* Public endpoint — no auth header needed, so the browser can load it directly. */}
        <img src={api.publicFileUrl(token)} alt={image.title} />
        <div className="card-body">
          <h2>{image.title}</h2>
          {image.description && <p className="muted">{image.description}</p>}
          <p className="muted small">Shared from a Personal Gallery</p>
        </div>
      </div>
    </div>
  )
}
