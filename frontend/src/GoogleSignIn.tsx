import { useEffect, useRef, useState } from 'react'
import { GoogleLogin, GoogleOAuthProvider } from '@react-oauth/google'
import type { CredentialResponse } from '@react-oauth/google'
import { LoaderCircle, RotateCw } from 'lucide-react'
import { ApiError, createGoogleChallenge } from './api'
import type { GoogleChallenge } from './api'

type GoogleState =
  | { status: 'loading' | 'complete' }
  | { status: 'ready', challenge: GoogleChallenge, expiresAt: number }
  | { status: 'unavailable', message: string, retry: boolean }

interface GoogleSignInProps {
  disabled?: boolean
  linking?: boolean
  onCredential: (idToken: string) => Promise<void>
}

export default function GoogleSignIn({ disabled = false, linking = false, onCredential }: GoogleSignInProps) {
  const [state, setState] = useState<GoogleState>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)
  const [scriptLoaded, setScriptLoaded] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [width, setWidth] = useState(240)
  const container = useRef<HTMLDivElement>(null)
  const completing = useRef(false)

  useEffect(() => {
    let active = true
    void createGoogleChallenge()
      .then((challenge) => {
        if (active) setState({ status: 'ready', challenge, expiresAt: Date.now() + 240_000 })
      })
      .catch((failure: unknown) => {
        if (!active) return
        const unconfigured = failure instanceof ApiError
          && failure.status === 503 && failure.message === 'Google login is not configured'
        setState({
          status: 'unavailable',
          message: unconfigured ? 'Google sign-in is not configured yet.'
            : failure instanceof Error ? failure.message : 'Google sign-in is unavailable.',
          retry: true,
        })
      })
    return () => { active = false }
  }, [attempt])

  useEffect(() => {
    if (!container.current || typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(([entry]) => {
      if (entry.contentRect.width > 0) setWidth(Math.min(400, Math.floor(entry.contentRect.width)))
    })
    observer.observe(container.current)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (state.status !== 'ready') return
    const timeout = window.setTimeout(() => setState({
      status: 'unavailable', message: 'Google sign-in expired. Please try again.', retry: true,
    }), Math.max(0, state.expiresAt - Date.now()))
    return () => window.clearTimeout(timeout)
  }, [state])

  useEffect(() => {
    if (state.status !== 'ready' || scriptLoaded) return
    const timeout = window.setTimeout(() => setState({
      status: 'unavailable', message: 'Google could not be reached. Please try again.', retry: true,
    }), 15_000)
    return () => window.clearTimeout(timeout)
  }, [state.status, scriptLoaded])

  async function complete(response: CredentialResponse) {
    if (disabled || completing.current || state.status !== 'ready') return
    if (!response.credential || Date.now() >= state.expiresAt) {
      setState({ status: 'unavailable', message: 'Google sign-in expired. Please try again.', retry: true })
      return
    }
    completing.current = true
    setProcessing(true)
    try {
      await onCredential(response.credential)
      setState({ status: 'complete' })
    } catch (failure) {
      setState({
        status: 'unavailable',
        message: failure instanceof ApiError && failure.status === 401
          ? 'Google sign-in expired or changed in another tab. Please try again.'
          : failure instanceof Error ? failure.message : 'Google sign-in failed. Please try again.',
        retry: true,
      })
    } finally {
      completing.current = false
      setProcessing(false)
    }
  }

  function retry() {
    setState({ status: 'loading' })
    setScriptLoaded(false)
    setAttempt((previous) => previous + 1)
  }

  const loading = state.status === 'loading' || (state.status === 'ready' && !scriptLoaded)

  return (
    <div className="google-auth" aria-busy={loading || processing}>
      <div className="google-button-slot" ref={container}>
        {(state.status !== 'ready' || !scriptLoaded) && (
          <button type="button" className="google-placeholder" disabled>
            <img src="/google-g.png" width="20" height="20" alt="" />
            <span>{linking ? 'Continue with Google' : 'Sign in with Google'}</span>
            {loading && <LoaderCircle className="spin" size={16} aria-hidden="true" />}
          </button>
        )}
        {state.status === 'ready' && (
          <GoogleOAuthProvider
            clientId={state.challenge.client_id}
            nonce={document.querySelector<HTMLMetaElement>('meta[name="csp-nonce"]')?.content}
            onScriptLoadSuccess={() => setScriptLoaded(true)}
            onScriptLoadError={() => setState({
              status: 'unavailable', message: 'Google could not be reached. Please try again.', retry: true,
            })}
          >
            <div className="google-sdk-button" data-ready={scriptLoaded} inert={disabled || processing}>
              <GoogleLogin
                nonce={state.challenge.nonce}
                onSuccess={(response) => void complete(response)}
                onError={() => setState({
                  status: 'unavailable', message: 'Google sign-in did not complete. Please try again.', retry: true,
                })}
                ux_mode="popup"
                auto_select={false}
                useOneTap={false}
                theme="outline"
                size="large"
                shape="rectangular"
                text={linking ? 'continue_with' : 'signin_with'}
                width={width}
              />
            </div>
          </GoogleOAuthProvider>
        )}
      </div>
      {processing && <p className="google-status" role="status">{linking ? 'Linking Google...' : 'Signing in with Google...'}</p>}
      {state.status === 'unavailable' && (
        <div className="google-feedback">
          <p className="google-status" role="status">{state.message}</p>
          {state.retry && (
            <button type="button" className="icon-button" aria-label="Retry Google sign-in"
              title="Retry Google sign-in" disabled={disabled || processing} onClick={retry}>
              <RotateCw size={16} />
            </button>
          )}
        </div>
      )}
    </div>
  )
}