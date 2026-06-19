import axios, { type InternalAxiosRequestConfig } from "axios"
import useAuthStore from "@/stores/authStore"

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000"
const AUTH_PATH_PREFIX = "/api/v1/auth/"

const apiClient = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,
})

type RetriableRequestConfig = InternalAxiosRequestConfig & {
  _retry?: boolean
}

const getRequestPath = (config: InternalAxiosRequestConfig) => {
  const url = config.url ?? ""
  try {
    return new URL(url, config.baseURL ?? BASE_URL).pathname
  } catch {
    return url
  }
}

const isAuthRequest = (config: InternalAxiosRequestConfig) =>
  getRequestPath(config).startsWith(AUTH_PATH_PREFIX)

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let isRefreshing = false
let refreshQueue: Array<{
  resolve: (token: string) => void
  reject: (error: unknown) => void
}> = []

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as RetriableRequestConfig | undefined

    if (
      originalRequest &&
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !isAuthRequest(originalRequest)
    ) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          refreshQueue.push({
            resolve: (token) => {
              originalRequest.headers.Authorization = `Bearer ${token}`
              resolve(apiClient(originalRequest))
            },
            reject,
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const response = await axios.post(
          `${BASE_URL}/api/v1/auth/refresh`,
          {},
          { withCredentials: true },
        )
        const newToken: string = response.data.access_token
        useAuthStore.getState().setAccessToken(newToken)

        for (const queuedRequest of refreshQueue) {
          queuedRequest.resolve(newToken)
        }
        refreshQueue = []

        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return apiClient(originalRequest)
      } catch (refreshError) {
        useAuthStore.getState().clearAuth()

        for (const queuedRequest of refreshQueue) {
          queuedRequest.reject(refreshError)
        }
        refreshQueue = []

        if (window.location.pathname !== "/login") {
          window.location.assign("/login")
        }
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  },
)

export default apiClient
