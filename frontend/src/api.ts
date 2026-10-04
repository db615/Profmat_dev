export interface User {
  id: string
  email: string
  full_name: string | null
  role: 'USER' | 'ADMIN'
  is_active: boolean
  email_verified: boolean
  created_at: string
}

export interface Session {
  accessToken: string
  expiresAt: number
  user: User
}

interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  user: User
}

export interface Credentials {
  email: string
  password: string
  full_name?: string
}

export interface GoogleChallenge {
  nonce: string
  client_id: string
}

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function errorDetail(body: unknown): string | null {
  if (!body || typeof body !== 'object' || !('detail' in body)) return null
  if (typeof body.detail === 'string') return body.detail
  if (Array.isArray(body.detail)) {
    return body.detail
      .map((item: { msg?: string }) => item.msg)
      .filter(Boolean)
      .join('. ')
  }
  return null
}

async function request<Result>(path: string, options: RequestInit = {}): Promise<Result> {
  const headers = new Headers(options.headers)
  if (options.method === 'POST') headers.set('X-CSRF-Protection', '1')
  if (options.body) headers.set('Content-Type', 'application/json')

  let response: Response
  try {
    response = await fetch(`/api/v1/auth${path}`, {
      ...options,
      credentials: 'include',
      cache: 'no-store',
      headers,
      signal: AbortSignal.timeout(15_000),
    })
  } catch {
    throw new ApiError('Unable to reach the server. Please try signing in again.', 0)
  }

  if (response.status === 204) return undefined as Result
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const fallback = response.status === 429
      ? 'Too many attempts. Wait a minute and try again.'
      : 'The server is unavailable. Please try again shortly.'
    throw new ApiError(errorDetail(body) || fallback, response.status)
  }
  if (body === null) throw new ApiError('The server returned an unexpected response.', 502)
  return body as Result
}

function sessionFromToken(result: TokenResponse): Session {
  return {
    accessToken: result.access_token,
    expiresAt: Date.now() + result.expires_in * 1000,
    user: result.user,
  }
}

function withSessionLock<Result>(operation: () => Promise<Result>): Promise<Result> {
  if (typeof navigator !== 'undefined' && navigator.locks) {
    return navigator.locks.request('professor-search-auth-session', operation)
  }
  return operation()
}

export function authenticate(mode: 'login' | 'register', credentials: Credentials): Promise<Session> {
  const body = mode === 'register'
    ? { ...credentials, full_name: credentials.full_name?.trim() || undefined }
    : { email: credentials.email, password: credentials.password }
  return withSessionLock(async () => sessionFromToken(await request<TokenResponse>(`/${mode}`, {
    method: 'POST',
    body: JSON.stringify(body),
  })))
}

let googleChallengeInFlight: Promise<GoogleChallenge> | null = null

export function createGoogleChallenge(): Promise<GoogleChallenge> {
  if (!googleChallengeInFlight) {
    googleChallengeInFlight = withSessionLock(() => request<GoogleChallenge>('/google/nonce', {
      method: 'POST',
    })).finally(() => { googleChallengeInFlight = null })
  }
  return googleChallengeInFlight
}

export function signInWithGoogle(idToken: string): Promise<Session> {
  return withSessionLock(async () => sessionFromToken(await request<TokenResponse>('/google', {
    method: 'POST',
    body: JSON.stringify({ id_token: idToken }),
  })))
}

export function linkGoogleAccount(idToken: string, accessToken: string): Promise<User> {
  return withSessionLock(() => request<User>('/google/link', {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ id_token: idToken }),
  }))
}

let refreshInFlight: Promise<Session> | null = null

export function refreshSession(): Promise<Session> {
  if (!refreshInFlight) {
    refreshInFlight = withSessionLock(async () => sessionFromToken(
      await request<TokenResponse>('/refresh', { method: 'POST' }),
    )).finally(() => { refreshInFlight = null })
  }
  return refreshInFlight
}

export function getProfile(accessToken: string): Promise<User> {
  return request<User>('/me', { headers: { Authorization: `Bearer ${accessToken}` } })
}

export function logout(): Promise<void> {
  return withSessionLock(() => request<void>('/logout', { method: 'POST' }))
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch('/health/ready', {
      cache: 'no-store',
      signal: AbortSignal.timeout(5000),
    })
    return response.ok
  } catch {
    return false
  }
}