import { create } from "zustand"

type AuthStore = {
  accessToken: string | null
  setAccessToken: (token: string) => void
  clearAuth: () => void
}

const useAuthStore = create<AuthStore>()((set) => ({
  accessToken: null,
  setAccessToken: (token) => set({ accessToken: token }),
  clearAuth: () => set({ accessToken: null }),
}))

export default useAuthStore
