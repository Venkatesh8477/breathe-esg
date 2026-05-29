import axios from 'axios'

const apiUrl = import.meta.env.VITE_API_URL || ''
const baseURL = apiUrl ? `${apiUrl}/api` : '/api'
const api = axios.create({ baseURL })

api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('access_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

api.interceptors.response.use(
  r => r,
  async err => {
    if (err.response?.status === 401) {
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        try {
          const refreshUrl = apiUrl ? `${apiUrl}/api/auth/token/refresh/` : '/api/auth/token/refresh/'
          const { data } = await axios.post(refreshUrl, { refresh })
          localStorage.setItem('access_token', data.access)
          err.config.headers.Authorization = `Bearer ${data.access}`
          return api(err.config)
        } catch {
          localStorage.clear()
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(err)
  }
)

export default api
