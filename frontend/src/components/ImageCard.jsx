import { useEffect, useState } from 'react'
import { api } from '../api'

export default function ImageCard({ image, onChanged, onDeleted, onError }) {
  const [src, setSrc] = useState(null)
  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState(image.title)
  const [description, setDescription] = useState(image.description)
  const [replacement, setReplacement] = useState(null)
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)

  // Re-fetch when the file is replaced (updated_at changes), and always revoke
  // the object URL on unmount so blobs don't leak.
  useEffect(() => {
    let url = null
    let cancelled = false

    api
      .imageBlobUrl(image.id)
      .then((objectUrl) => {
        if (cancelled) {
          URL.revokeObjectURL(objectUrl)
          return
        }
        url = objectUrl
        setSrc(objectUrl)
      })
      .catch(() => setSrc(null))

    return () => {
      cancelled = true
      if (url) URL.revokeObjectURL(url)
    }
  }, [image.id, image.updated_at])

  const shareUrl = image.share_token ? `${window.location.origin}/s/${image.share_token}` : null

  const run = async (fn) => {
    setBusy(true)
    try {
      await fn()
    } catch (err) {
      onError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const save = (e) => {
    e.preventDefault()
    run(async () => {
      const updated = await api.updateImage(image.id, {
        title,
        description,
        file: replacement,
      })
      setReplacement(null)
      setEditing(false)
      onChanged(updated)
    })
  }

  const remove = () =>
    run(async () => {
      if (!window.confirm(`Delete "${image.title}"? This can't be undone.`)) return
      await api.deleteImage(image.id)
      onDeleted(image.id)
    })

  const toggleShare = () =>
    run(async () => {
      if (image.share_token) {
        await api.revokeShare(image.id)
        onChanged({ ...image, share_token: null })
      } else {
        const { share_token } = await api.shareImage(image.id)
        onChanged({ ...image, share_token })
      }
    })

  const copyLink = async () => {
    await navigator.clipboard.writeText(shareUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <article className="card image-card">
      <div className="thumb">
        {src ? <img src={src} alt={image.title} /> : <div className="thumb-empty">…</div>}
      </div>

      {editing ? (
        <form className="card-body" onSubmit={save}>
          <label>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label>
            Description
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </label>
          <label>
            Replace file (optional)
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setReplacement(e.target.files[0] || null)}
            />
          </label>
          <div className="row">
            <button type="submit" disabled={busy}>
              Save
            </button>
            <button type="button" className="ghost" onClick={() => setEditing(false)}>
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <div className="card-body">
          <h3>{image.title}</h3>
          {image.description && <p className="muted small">{image.description}</p>}

          <div className="row">
            <button className="ghost" onClick={() => setEditing(true)} disabled={busy}>
              Edit
            </button>
            <button className="ghost" onClick={toggleShare} disabled={busy}>
              {image.share_token ? 'Unshare' : 'Share'}
            </button>
            <button className="ghost danger" onClick={remove} disabled={busy}>
              Delete
            </button>
          </div>

          {shareUrl && (
            <div className="share-box">
              <input readOnly value={shareUrl} onFocus={(e) => e.target.select()} />
              <button className="ghost" onClick={copyLink}>
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
          )}
        </div>
      )}
    </article>
  )
}
