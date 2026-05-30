import axios from 'axios'

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8001'

const api = axios.create({ baseURL: BASE_URL })

api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export const authApi = {
  register: (email, password) =>
    api.post('/auth/register', { email, password }),
  login: (email, password) => {
    const form = new FormData()
    form.append('username', email)
    form.append('password', password)
    return api.post('/auth/login', form)
  },
  me: () => api.get('/auth/me'),
}

export const repoApi = {
  ingest:       (github_url, sync_branch = 'main') =>
    api.post('/repos/ingest', { github_url, sync_branch }),
  list:         () => api.get('/repos'),           // ✅ no trailing slash
  delete:       (github_url) =>
    api.delete('/repos/delete-repo', { data: { github_url } }),
  updateBranch: (repo_id, sync_branch) =>
    api.patch(`/repos/${repo_id}/sync-branch`, { sync_branch }),
}

export const chatApi = {
  getConversations: () => api.get('/chat/conversations'),
  getMessages:      (id) => api.get(`/chat/conversation/${id}/messages`),
  deleteConversation: (id) => api.delete(`/chat/conversation/${id}`),
}

export const streamChat = (payload, onEvent, onDone, onError) => {
  const token = localStorage.getItem('token')
  const url   = `${BASE_URL}/chat/send`

  fetch(url, {
    method:  'POST',
    headers: {
      'Content-Type':  'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  })
    .then(async res => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const reader  = res.body.getReader()
      const decoder = new TextDecoder()
      let   buffer  = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop()
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.type === 'done') onDone()
              else onEvent(data)
            } catch {}
          }
        }
      }
    })
    .catch(onError)
}

export default api
