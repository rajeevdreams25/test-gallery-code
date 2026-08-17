import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'

/**
 * Like toggle for a publicly reachable photo.
 *
 * Liking needs an account so a count means something and can be undone, so a
 * logged-out visitor is sent to the login page instead of being refused.
 */
export default function LikeButton({ token, count, liked, onChange, onError }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)

  const toggle = async () => {
    if (!user) {
      navigate('/login')
      return
    }
    setBusy(true)
    try {
      const result = liked ? await api.unlikeImage(token) : await api.likeImage(token)
      onChange(result)
    } catch (err) {
      onError?.(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <button
      type="button"
      className={`like ${liked ? 'liked' : ''}`}
      onClick={toggle}
      disabled={busy}
      aria-pressed={liked}
      aria-label={liked ? 'Unlike this photo' : 'Like this photo'}
      title={user ? '' : 'Log in to like this photo'}
    >
      <span aria-hidden="true">{liked ? '♥' : '♡'}</span>
      <span>{count}</span>
    </button>
  )
}
