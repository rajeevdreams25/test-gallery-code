const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const TOKEN_KEY = 'gallery_token'

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

async function request(path, { method = 'GET', body, auth = true, json = true } = {}) {
  const headers = {}
  if (auth) {
    const token = tokenStore.get()
    if (token) headers.Authorization = `Bearer ${token}`
  }
  if (json && body !== undefined) headers['Content-Type'] = 'application/json'

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: json && body !== undefined ? JSON.stringify(body) : body,
  })

  if (res.status === 401) {
    tokenStore.clear()
    throw new ApiError('Your session expired. Please log in again.', 401)
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const data = await res.json()
      if (typeof data.detail === 'string') detail = data.detail
      else if (Array.isArray(data.detail)) detail = data.detail[0]?.msg || detail
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, res.status)
  }

  if (res.status === 204) return null
  return res.json()
}

/** Fetch a protected image as a blob URL — <img src> can't send an auth header. */
async function fetchBlobUrl(path) {
  const token = tokenStore.get()
  const res = await fetch(`${API_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new ApiError(`Could not load image (${res.status})`, res.status)
  return URL.createObjectURL(await res.blob())
}

export const api = {
  register: (email, password) =>
    request('/auth/register', { method: 'POST', body: { email, password }, auth: false }),

  login: (email, password) =>
    request('/auth/login', { method: 'POST', body: { email, password }, auth: false }),

  me: () => request('/auth/me'),

  listImages: () => request('/images'),

  uploadImage: (file, title, description) => {
    const form = new FormData()
    form.append('file', file)
    form.append('title', title || '')
    form.append('description', description || '')
    return request('/images', { method: 'POST', body: form, json: false })
  },

  updateImage: (id, { title, description, file }) => {
    const form = new FormData()
    if (title !== undefined) form.append('title', title)
    if (description !== undefined) form.append('description', description)
    if (file) form.append('file', file)
    return request(`/images/${id}`, { method: 'PUT', body: form, json: false })
  },

  deleteImage: (id) => request(`/images/${id}`, { method: 'DELETE' }),

  shareImage: (id) => request(`/images/${id}/share`, { method: 'POST' }),

  revokeShare: (id) => request(`/images/${id}/share`, { method: 'DELETE' }),

  imageBlobUrl: (id) => fetchBlobUrl(`/images/${id}/file`),

  publicImage: (token) => request(`/public/${token}`, { auth: false }),

  publicFileUrl: (token) => `${API_URL}/public/${token}/file`,
}

export { API_URL, ApiError }
