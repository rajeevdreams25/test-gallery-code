import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import LikeButton from '../components/LikeButton'

const PAGE_SIZE = 24

export default function Explore() {
  const { user } = useAuth()
  const [items, setItems] = useState([])
  const [cursor, setCursor] = useState(null)
  const [done, setDone] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const sentinel = useRef(null)
  // Guards against a second fetch firing before the first one lands - both
  // from StrictMode's double effect and from fast scrolling.
  const inFlight = useRef(false)
  const nextCursor = useRef(null)

  const loadMore = useCallback(async () => {
    if (inFlight.current || done) return
    inFlight.current = true
    setLoading(true)
    try {
      const page = await api.publicFeed(nextCursor.current, PAGE_SIZE)
      setItems((prev) => {
        // Belt and braces: a photo published mid-scroll could otherwise
        // appear on two pages.
        const seen = new Set(prev.map((i) => i.share_token))
        return [...prev, ...page.items.filter((i) => !seen.has(i.share_token))]
      })
      nextCursor.current = page.next_cursor
      setCursor(page.next_cursor)
      if (!page.next_cursor) setDone(true)
      setError('')
    } catch (err) {
      setError(err.message)
      setDone(true) // stop hammering a failing endpoint
    } finally {
      inFlight.current = false
      setLoading(false)
    }
  }, [done])

  useEffect(() => {
    loadMore()
    // Intentionally once on mount; later pages come from the observer below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const node = sentinel.current
    if (!node || done) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) loadMore()
      },
      // Start fetching a screenful early so scrolling stays smooth.
      { rootMargin: '400px' }
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [loadMore, done, cursor])

  const applyLike = (token, result) =>
    setItems((prev) =>
      prev.map((i) =>
        i.share_token === token
          ? { ...i, like_count: result.like_count, liked_by_me: result.liked_by_me }
          : i
      )
    )

  return (
    <div className="page">
      <header className="topbar">
        <h1>Explore</h1>
        <div className="row">
          {user ? (
            <Link to="/dashboard">My gallery</Link>
          ) : (
            <>
              <Link to="/login">Log in</Link>
              <Link to="/register">Sign up</Link>
            </>
          )}
        </div>
      </header>

      <p className="muted small">Photos people have published to the public gallery.</p>

      {error && <div className="alert">{error}</div>}

      <div className="grid">
        {items.map((item) => (
          <article className="card image-card" key={item.share_token}>
            <Link to={`/s/${item.share_token}`} className="thumb">
              <img src={api.publicFileUrl(item.share_token)} alt={item.title} loading="lazy" />
            </Link>
            <div className="card-body">
              <div className="row space-between">
                <h3>{item.title}</h3>
                <LikeButton
                  token={item.share_token}
                  count={item.like_count}
                  liked={item.liked_by_me}
                  onChange={(result) => applyLike(item.share_token, result)}
                  onError={setError}
                />
              </div>
              {item.description && <p className="muted small">{item.description}</p>}
            </div>
          </article>
        ))}
      </div>

      {loading && <p className="muted center-text">Loading photos…</p>}

      {!loading && items.length === 0 && !error && (
        <p className="muted center-text">
          Nothing published yet. {user ? 'Publish one from your gallery.' : ''}
        </p>
      )}

      {done && items.length > 0 && <p className="muted center-text small">That’s everything.</p>}

      {/* Scrolling this into view loads the next page. */}
      <div ref={sentinel} aria-hidden="true" />
    </div>
  )
}
