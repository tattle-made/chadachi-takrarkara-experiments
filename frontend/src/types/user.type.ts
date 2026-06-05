export type UserRole = "admin" | "manager" | "member"

export type User = {
  id: number
  email: string
  role: UserRole
  is_active: boolean
}
