import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  ApiError, authenticate, createGoogleChallenge, getProfile, linkGoogleAccount,
  logout, refreshSession, signInWithGoogle,
} from './api'

const user = {
  id: 'test-user-id',
  email: 'member@example.com',
  full_name: 'Test Member',
  role: 'USER',
  is_active: true,
  email_verified: false,
  created_at: '2026-09-27T00:00:00Z',
}
const token = { access_token: 'test-access-token', token_type: 'bearer', expires_in: 900, user }
const fetchMock = vi.fn<typeof fetch>()
const lockMock = vi.fn((_name: string, operation: () => Promise<unknown>) => operation())

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
  vi.stubGlobal('navigator', { locks: { request: lockMock } })
})

afterEach(() => {
  vi.resetAllMocks()
  vi.unstubAllGlobals()
})

describe('authentication requests', () => {
  it('registers with cookies and the CSRF header', async () => {
    fetchMock.mockResolvedValueOnce(Response.json(token, { status: 201 }))
    const session = await authenticate('register', {
      email: user.email,
      password: 'a sufficiently long password',
      full_name: ' Test Member ',
    })
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/auth/register')
    expect(options?.credentials).toBe('include')
    expect(new Headers(options?.headers).get('X-CSRF-Protection')).toBe('1')
    expect(JSON.parse(options?.body as string).full_name).toBe('Test Member')
    expect(session.user).toEqual(user)
    expect(session.accessToken).toBe('test-access-token')
    expect(session.expiresAt).toBeGreaterThan(Date.now())
    expect(lockMock).toHaveBeenCalledWith('professor-search-auth-session', expect.any(Function))
  })

  it('omits registration-only fields from login', async () => {
    fetchMock.mockResolvedValueOnce(Response.json(token))
    await authenticate('login', { email: user.email, password: 'password', full_name: 'Ignored' })
    expect(JSON.parse(fetchMock.mock.calls[0][1]?.body as string)).toEqual({
      email: user.email, password: 'password',
    })
  })

  it('coalesces Google challenges and binds them to the browser cookie', async () => {
    const challenge = { nonce: 'browser-bound-nonce', client_id: 'client.apps.googleusercontent.com' }
    fetchMock.mockResolvedValueOnce(Response.json(challenge))
    const first = createGoogleChallenge()
    const second = createGoogleChallenge()
    expect(first).toBe(second)
    expect(await first).toEqual(challenge)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/auth/google/nonce')
    expect(options?.method).toBe('POST')
    expect(options?.credentials).toBe('include')
    expect(new Headers(options?.headers).get('X-CSRF-Protection')).toBe('1')
  })

  it('reports an unconfigured Google provider without inventing a client ID', async () => {
    fetchMock.mockResolvedValueOnce(Response.json({
      detail: 'Google login is not configured',
    }, { status: 503 }))
    await expect(createGoogleChallenge()).rejects.toThrow('Google login is not configured')
  })

  it('exchanges the Google ID token for a server-authenticated session', async () => {
    fetchMock.mockResolvedValueOnce(Response.json(token))
    const session = await signInWithGoogle('google-id-token')
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/auth/google')
    expect(options?.credentials).toBe('include')
    expect(new Headers(options?.headers).get('X-CSRF-Protection')).toBe('1')
    expect(JSON.parse(options?.body as string)).toEqual({ id_token: 'google-id-token' })
    expect(session.user).toEqual(user)
    expect(session.accessToken).toBe('test-access-token')
    expect(lockMock).toHaveBeenCalledWith('professor-search-auth-session', expect.any(Function))
  })

  it('does not retry a rejected one-time Google token exchange', async () => {
    fetchMock.mockResolvedValueOnce(Response.json({ detail: 'Invalid credentials' }, { status: 401 }))
    await expect(signInWithGoogle('invalid-id-token')).rejects.toMatchObject({ status: 401 })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('requires the current session when linking an existing account to Google', async () => {
    fetchMock.mockResolvedValueOnce(Response.json({ ...user, email_verified: true }))
    const linked = await linkGoogleAccount('google-id-token', 'current-access-token')
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/auth/google/link')
    expect(new Headers(options?.headers).get('Authorization')).toBe('Bearer current-access-token')
    expect(new Headers(options?.headers).get('X-CSRF-Protection')).toBe('1')
    expect(JSON.parse(options?.body as string)).toEqual({ id_token: 'google-id-token' })
    expect(linked.email_verified).toBe(true)
  })

  it('coalesces simultaneous refresh requests', async () => {
    fetchMock.mockResolvedValueOnce(Response.json(token))
    const first = refreshSession()
    const second = refreshSession()
    expect(first).toBe(second)
    await Promise.all([first, second])
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/auth/refresh')
  })

  it('does not retry failed refreshes', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('Network unavailable'))
    await expect(refreshSession()).rejects.toMatchObject({ status: 0 })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('displays backend errors without treating them as a successful session', async () => {
    fetchMock.mockResolvedValueOnce(Response.json({ detail: 'Invalid credentials' }, { status: 401 }))
    await expect(authenticate('login', { email: user.email, password: 'wrong' }))
      .rejects.toEqual(new ApiError('Invalid credentials', 401))
  })

  it('handles FastAPI validation errors', async () => {
    fetchMock.mockResolvedValueOnce(Response.json({
      detail: [{ loc: ['body', 'password'], msg: 'Password is too short' }],
    }, { status: 422 }))
    await expect(authenticate('register', { email: user.email, password: 'short' }))
      .rejects.toThrow('Password is too short')
  })

  it('uses the access token for the protected profile', async () => {
    fetchMock.mockResolvedValueOnce(Response.json(user))
    expect(await getProfile('test-access-token')).toEqual(user)
    expect(new Headers(fetchMock.mock.calls[0][1]?.headers).get('Authorization'))
      .toBe('Bearer test-access-token')
  })

  it('handles the empty logout response', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }))
    await expect(logout()).resolves.toBeUndefined()
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/auth/logout')
  })
})