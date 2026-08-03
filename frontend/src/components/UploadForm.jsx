import { useRef, useState } from 'react'
import { api } from '../api'

export default function UploadForm({ onUploaded, onError }) {
  const [file, setFile] = useState(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [busy, setBusy] = useState(false)
  const fileInput = useRef(null)

  const submit = async (e) => {
    e.preventDefault()
    if (!file) return
    setBusy(true)
    try {
      const created = await api.uploadImage(file, title, description)
      onUploaded(created)
      setFile(null)
      setTitle('')
      setDescription('')
      if (fileInput.current) fileInput.current.value = ''
    } catch (err) {
      onError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="card upload-form" onSubmit={submit}>
      <input
        ref={fileInput}
        type="file"
        accept="image/*"
        onChange={(e) => setFile(e.target.files[0] || null)}
        required
      />
      <input placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
      <input
        placeholder="Description"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <button type="submit" disabled={!file || busy}>
        {busy ? 'Uploading…' : 'Upload'}
      </button>
    </form>
  )
}
