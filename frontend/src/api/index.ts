import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios'

const instance: AxiosInstance = axios.create({
  baseURL: 'http://localhost:8080',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

instance.interceptors.request.use((config) => {
  const requestId = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
  config.headers['X-Request-Id'] = requestId
  return config
})

instance.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data
  },
  (error) => {
    const message = error.response?.data?.message || error.message || '请求失败'
    console.error(`[API Error] ${message}`)
    return Promise.reject(error)
  },
)

export function get<T = any>(url: string, params?: Record<string, any>, config?: AxiosRequestConfig): Promise<T> {
  return instance.get(url, { params, ...config })
}

export function post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
  return instance.post(url, data, config)
}

export function put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
  return instance.put(url, data, config)
}

export function del<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return instance.delete(url, config)
}

export default instance