import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import LikeButton from '../components/LikeButton'

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
          <div className="row space-between">
            <h2>{image.title}</h2>
            <LikeButton
              token={token}
              count={image.like_count}
              liked={image.liked_by_me}
              onChange={(result) => setImage((prev) => ({ ...prev, ...result }))}
              onError={setError}
            />
          </div>
          {image.description && <p className="muted">{image.description}</p>}
          <p className="muted small">
            Shared from a Personal Gallery · <Link to="/explore">Explore public photos</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
