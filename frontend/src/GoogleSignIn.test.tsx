// @vitest-environment jsdom

import type { ComponentProps } from 'react'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { GoogleLogin, GoogleOAuthProvider } from '@react-oauth/google'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { ApiError, createGoogleChallenge } from './api'
import GoogleSignIn from './GoogleSignIn'

vi.mock('./api', async (importOriginal) => ({
  ...await importOriginal<typeof import('./api')>(),
  createGoogleChallenge: vi.fn(),
}))

vi.mock('@react-oauth/google', () => ({
  GoogleOAuthProvider: vi.fn(({ children }: ComponentProps<typeof GoogleOAuthProvider>) => children),
  GoogleLogin: vi.fn(({ onSuccess }: ComponentProps<typeof GoogleLogin>) => (
    <button type="button" onClick={() => onSuccess({ credential: 'google-id-token' })}>Google SDK button</button>
  )),
}))

const challenge = { nonce: 'one-time-nonce', client_id: 'test.apps.googleusercontent.com' }

beforeEach(() => {
  vi.mocked(createGoogleChallenge).mockResolvedValue(challenge)
  const nonce = document.createElement('meta')
  nonce.name = 'csp-nonce'
  nonce.content = 'response-style-nonce'
  document.head.append(nonce)
})

afterEach(() => {
  cleanup()
  document.querySelector('meta[name="csp-nonce"]')?.remove()
  vi.clearAllMocks()
  vi.useRealTimers()
})

async function loadGoogleScript() {
  await waitFor(() => expect(GoogleOAuthProvider).toHaveBeenCalled())
  act(() => vi.mocked(GoogleOAuthProvider).mock.calls.at(-1)?.[0].onScriptLoadSuccess?.())
}

it('keeps the Google button visible when the backend is not configured', async () => {
  vi.mocked(createGoogleChallenge).mockRejectedValueOnce(new ApiError('Google login is not configured', 503))
  const complete = vi.fn()
  render(<GoogleSignIn onCredential={complete} />)
  expect(await screen.findByText('Google sign-in is not configured yet.')).toBeTruthy()
  expect((screen.getByRole('button', { name: 'Sign in with Google' }) as HTMLButtonElement).disabled).toBe(true)
  expect(GoogleOAuthProvider).not.toHaveBeenCalled()
  expect(complete).not.toHaveBeenCalled()
})

it('passes the server client ID and nonce to Google and exchanges only its ID token', async () => {
  const complete = vi.fn().mockResolvedValue(undefined)
  render(<GoogleSignIn onCredential={complete} />)
  await loadGoogleScript()
  expect(vi.mocked(GoogleOAuthProvider).mock.calls.at(-1)?.[0]).toMatchObject({
    clientId: challenge.client_id, nonce: 'response-style-nonce',
  })
  expect(vi.mocked(GoogleLogin).mock.calls.at(-1)?.[0]).toMatchObject({
    nonce: challenge.nonce, auto_select: false, useOneTap: false, ux_mode: 'popup',
  })
  fireEvent.click(screen.getByRole('button', { name: 'Google SDK button' }))
  await waitFor(() => expect(complete).toHaveBeenCalledExactlyOnceWith('google-id-token'))
})

it('does not exchange the same callback twice while signing in', async () => {
  let finish: () => void = () => {}
  const complete = vi.fn(() => new Promise<void>((resolve) => { finish = resolve }))
  render(<GoogleSignIn onCredential={complete} />)
  await loadGoogleScript()
  const success = vi.mocked(GoogleLogin).mock.calls.at(-1)![0].onSuccess
  act(() => {
    success({ credential: 'google-id-token' })
    success({ credential: 'google-id-token' })
  })
  expect(complete).toHaveBeenCalledTimes(1)
  await act(async () => { finish() })
})

it('shows linking conflicts and obtains a fresh nonce only when retried', async () => {
  const complete = vi.fn().mockRejectedValue(new ApiError('Sign in to your existing account and link Google first', 409))
  render(<GoogleSignIn onCredential={complete} />)
  await loadGoogleScript()
  fireEvent.click(screen.getByRole('button', { name: 'Google SDK button' }))
  expect(await screen.findByText('Sign in to your existing account and link Google first')).toBeTruthy()
  expect(createGoogleChallenge).toHaveBeenCalledTimes(1)
  expect(complete).toHaveBeenCalledTimes(1)
  fireEvent.click(screen.getByRole('button', { name: 'Retry Google sign-in' }))
  await waitFor(() => expect(createGoogleChallenge).toHaveBeenCalledTimes(2))
})

it('preserves the button and offers retry when the Google script fails', async () => {
  render(<GoogleSignIn onCredential={vi.fn()} />)
  await waitFor(() => expect(GoogleOAuthProvider).toHaveBeenCalled())
  act(() => vi.mocked(GoogleOAuthProvider).mock.calls.at(-1)?.[0].onScriptLoadError?.())
  expect(await screen.findByText('Google could not be reached. Please try again.')).toBeTruthy()
  expect(screen.getByRole('button', { name: 'Sign in with Google' })).toBeTruthy()
  expect(screen.getByRole('button', { name: 'Retry Google sign-in' })).toBeTruthy()
})

it('times out a stalled Google script load', async () => {
  vi.useFakeTimers()
  await act(async () => { render(<GoogleSignIn onCredential={vi.fn()} />) })
  act(() => { vi.advanceTimersByTime(15_000) })
  expect(screen.getByText('Google could not be reached. Please try again.')).toBeTruthy()
})

it('expires an unused challenge before its server-side lifetime ends', async () => {
  vi.useFakeTimers()
  await act(async () => { render(<GoogleSignIn onCredential={vi.fn()} />) })
  act(() => vi.mocked(GoogleOAuthProvider).mock.calls.at(-1)?.[0].onScriptLoadSuccess?.())
  act(() => { vi.advanceTimersByTime(240_000) })
  expect(screen.getByText('Google sign-in expired. Please try again.')).toBeTruthy()
})

it('blocks credential exchange while another auth action is pending', async () => {
  const complete = vi.fn()
  render(<GoogleSignIn disabled onCredential={complete} />)
  await loadGoogleScript()
  act(() => vi.mocked(GoogleLogin).mock.calls.at(-1)?.[0].onSuccess({ credential: 'google-id-token' }))
  expect(complete).not.toHaveBeenCalled()
})