import { useEffect, useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import {
  ArrowRight, BadgeCheck, BookOpen, Check, CircleAlert, Eye, EyeOff,
  Link2, LoaderCircle, LockKeyhole, LogOut, Mail, ShieldCheck, UserRound,
} from 'lucide-react'
import {
  ApiError, authenticate, checkHealth, getProfile, linkGoogleAccount, logout,
  refreshSession, signInWithGoogle,
} from './api'
import type { Session } from './api'
import GoogleSignIn from './GoogleSignIn'
import './App.css'

type Mode = 'login' | 'register'
type Pending = 'authenticate' | 'google' | 'profile' | 'logout' | null

function PasswordField({ confirm = false, registering = false }: {
  confirm?: boolean
  registering?: boolean
}) {
  const [visible, setVisible] = useState(false)
  const name = confirm ? 'confirmation' : 'password'
  const label = confirm ? 'Confirm password' : 'Password'

  return (
    <div className="field">
      <label htmlFor={name}>{label}</label>
      <div className="input-wrap">
        <LockKeyhole size={17} aria-hidden="true" />
        <input
          id={name}
          name={name}
          type={visible ? 'text' : 'password'}
          autoComplete={registering ? 'new-password' : 'current-password'}
          placeholder={registering ? 'At least 12 characters' : 'Enter your password'}
          minLength={registering ? 12 : 1}
          maxLength={128}
          required
        />
        <button
          type="button"
          className="icon-button"
          onClick={() => setVisible(!visible)}
          aria-label={`${visible ? 'Hide' : 'Show'} ${label.toLowerCase()}`}
          title={`${visible ? 'Hide' : 'Show'} ${label.toLowerCase()}`}
          aria-pressed={visible}
        >
          {visible ? <EyeOff size={18} /> : <Eye size={18} />}
        </button>
      </div>
    </div>
  )
}

function App() {
  const [mode, setMode] = useState<Mode>('login')
  const [session, setSession] = useState<Session | null>(null)
  const [restoring, setRestoring] = useState(true)
  const [pending, setPending] = useState<Pending>(null)
  const [health, setHealth] = useState<'checking' | 'online' | 'offline'>('checking')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [linkingGoogle, setLinkingGoogle] = useState(false)

  useEffect(() => {
    let active = true
    void checkHealth().then((online) => {
      if (active) setHealth(online ? 'online' : 'offline')
    })
    void refreshSession()
      .then((restored) => {
        if (active) {
          setSession(restored)
          setNotice('Welcome back. Your session is active.')
        }
      })
      .catch((failure: unknown) => {
        if (active && (!(failure instanceof ApiError) || failure.status !== 401)) {
          setError('Your session could not be restored. Please sign in again.')
        }
      })
      .finally(() => { if (active) setRestoring(false) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!session) return
    const timeout = window.setTimeout(() => {
      void refreshSession()
        .then(setSession)
        .catch(() => {
          setSession(null)
          setNotice('')
          setError('Your session ended. Please sign in again.')
        })
    }, Math.max(0, session.expiresAt - Date.now() - 30_000))
    return () => window.clearTimeout(timeout)
  }, [session])

  function changeMode(nextMode: Mode) {
    setMode(nextMode)
    setError('')
    setNotice('')
  }

  function moveTab(event: KeyboardEvent<HTMLButtonElement>) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
    event.preventDefault()
    const nextMode = event.key === 'Home' ? 'login'
      : event.key === 'End' ? 'register' : mode === 'login' ? 'register' : 'login'
    changeMode(nextMode)
    event.currentTarget.parentElement?.querySelector<HTMLButtonElement>(`#tab-${nextMode}`)?.focus()
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (pending) return
    const form = event.currentTarget
    const values = new FormData(form)
    const password = String(values.get('password') ?? '')
    setError('')
    setNotice('')
    if (mode === 'register' && password !== values.get('confirmation')) {
      setError('The passwords do not match.')
      form.querySelector<HTMLInputElement>('#confirmation')?.focus()
      return
    }
    setPending('authenticate')
    try {
      const authenticated = await authenticate(mode, {
        email: String(values.get('email') ?? '').trim(),
        password,
        full_name: String(values.get('full_name') ?? ''),
      })
      form.reset()
      setSession(authenticated)
      setHealth('online')
      setNotice(mode === 'register' ? 'Registration successful.' : 'Login successful.')
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Unable to sign in. Please try again.')
      if (failure instanceof ApiError && failure.status === 0) setHealth('offline')
    } finally {
      setPending(null)
    }
  }

  async function completeGoogleSignIn(idToken: string) {
    if (pending) throw new Error('Another request is in progress. Please try again.')
    setPending('google')
    setError('')
    setNotice('')
    try {
      setSession(await signInWithGoogle(idToken))
      setLinkingGoogle(false)
      setHealth('online')
      setNotice('Signed in with Google.')
    } finally {
      setPending(null)
    }
  }

  async function completeGoogleLink(idToken: string) {
    if (!session || pending) throw new Error('Sign in to your account before linking Google.')
    setPending('google')
    setError('')
    setNotice('')
    try {
      const current = session.expiresAt <= Date.now() ? await refreshSession() : session
      const user = await linkGoogleAccount(idToken, current.accessToken)
      setSession({ ...current, user })
      setLinkingGoogle(false)
      setNotice('Google account linked.')
    } finally {
      setPending(null)
    }
  }

  async function verifyProfile() {
    if (!session || pending) return
    setPending('profile')
    setError('')
    try {
      const current = session.expiresAt <= Date.now() ? await refreshSession() : session
      const profile = await getProfile(current.accessToken)
      setSession({ ...current, user: profile })
      setNotice('Profile confirmed by the server.')
      setHealth('online')
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401) {
        setSession(null)
        setNotice('')
      }
      setError(failure instanceof Error ? failure.message : 'Unable to load your profile.')
    } finally {
      setPending(null)
    }
  }

  async function signOut() {
    if (pending) return
    setPending('logout')
    setError('')
    try {
      await logout()
      setSession(null)
      setMode('login')
      setLinkingGoogle(false)
      setNotice('You have been signed out.')
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Sign out failed. Please try again.')
    } finally {
      setPending(null)
    }
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="/" aria-label="Professor Search home">
          <span className="brand-mark"><BookOpen size={23} strokeWidth={1.7} /></span>
          <span>Professor <strong>Search</strong></span>
        </a>
        <div className={`connection connection-${health}`} role="status">
          <span className="status-dot" aria-hidden="true" />
          {health === 'online' ? 'API online' : health === 'offline' ? 'API offline' : 'Connecting'}
        </div>
      </header>

      <main className="account-layout">
        <section className="account-panel" aria-labelledby="account-heading" aria-busy={restoring}>
          <div className="eyebrow"><span className="short-rule" /> YOUR ACCOUNT</div>
          <h1 id="account-heading">
            {session ? "You're signed in." : mode === 'login' ? 'Welcome back.' : 'Create your account.'}
          </h1>
          <p className="account-subtitle">
            {session ? session.user.full_name || session.user.email : 'Your place in the academic community.'}
          </p>

          {!session && (
            <div className="auth-tabs" role="tablist" aria-label="Account access">
              {(['login', 'register'] as const).map((tab) => (
                <button
                  key={tab}
                  id={`tab-${tab}`}
                  role="tab"
                  type="button"
                  aria-selected={mode === tab}
                  aria-controls="auth-form"
                  tabIndex={mode === tab ? 0 : -1}
                  disabled={!!pending || restoring}
                  onClick={() => changeMode(tab)}
                  onKeyDown={moveTab}
                >
                  {tab === 'login' ? 'Sign in' : 'Create account'}
                </button>
              ))}
            </div>
          )}

          {notice && !error && <div className="notice" role="status"><Check size={18} />{notice}</div>}
          {error && <div className="error-message" role="alert"><CircleAlert size={18} />{error}</div>}

          {restoring ? (
            <div className="restoring"><LoaderCircle className="spin" size={22} /> Checking your session...</div>
          ) : session ? (
            <div className="profile-view">
              <div className="profile-heading">
                <span className="profile-avatar"><UserRound size={25} /></span>
                <div><h2>Account details</h2><span className="session-label"><ShieldCheck size={14} /> Session active</span></div>
              </div>
              <dl className="profile-details">
                <div><dt>Email address</dt><dd>{session.user.email}</dd></div>
                <div><dt>Account ID</dt><dd className="account-id">{session.user.id}</dd></div>
                <div><dt>Role</dt><dd>{session.user.role === 'ADMIN' ? 'Administrator' : 'User'}</dd></div>
                <div><dt>Email status</dt><dd>{session.user.email_verified ? 'Verified' : 'Not yet verified'}</dd></div>
                <div><dt>Joined</dt><dd>{new Date(session.user.created_at).toLocaleDateString(undefined, {
                  year: 'numeric', month: 'short', day: 'numeric',
                })}</dd></div>
              </dl>
              <div className="profile-actions">
                <button className="primary-button" onClick={() => void verifyProfile()} disabled={!!pending}>
                  {pending === 'profile' ? <LoaderCircle className="spin" size={18} /> : <BadgeCheck size={18} />}
                  {pending === 'profile' ? 'Checking...' : 'Check profile'}
                </button>
                <button className="secondary-button" onClick={() => void signOut()} disabled={!!pending}>
                  {pending === 'logout' ? <LoaderCircle className="spin" size={17} /> : <LogOut size={17} />}
                  Sign out
                </button>
              </div>
              <div className="google-link-panel">
                <button type="button" className="secondary-button" disabled={!!pending}
                  aria-expanded={linkingGoogle} aria-controls="google-link"
                  onClick={() => setLinkingGoogle(!linkingGoogle)}>
                  <Link2 size={17} />{linkingGoogle ? 'Cancel linking' : 'Link Google'}
                </button>
                {linkingGoogle && (
                  <div id="google-link">
                    <h3>Link your Google account</h3>
                    <GoogleSignIn linking disabled={!!pending} onCredential={completeGoogleLink} />
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div id="auth-form" role="tabpanel" aria-labelledby={`tab-${mode}`}>
              <GoogleSignIn disabled={!!pending} onCredential={completeGoogleSignIn} />
              <div className="auth-divider"><span>or</span></div>
              <form key={mode} onSubmit={(event) => void submit(event)}>
                <fieldset disabled={!!pending}>
                  {mode === 'register' && (
                    <div className="field">
                      <label htmlFor="full_name">Full name <span className="optional">(optional)</span></label>
                      <div className="input-wrap">
                        <UserRound size={17} aria-hidden="true" />
                        <input id="full_name" name="full_name" autoComplete="name" placeholder="Your full name" maxLength={200} />
                      </div>
                    </div>
                  )}
                  <div className="field">
                    <label htmlFor="email">Email address</label>
                    <div className="input-wrap">
                      <Mail size={17} aria-hidden="true" />
                      <input id="email" name="email" type="email" autoComplete="email" placeholder="you@university.edu" maxLength={320} required />
                    </div>
                  </div>
                  <PasswordField registering={mode === 'register'} />
                  {mode === 'register' && <PasswordField confirm registering />}
                  <button className="primary-button submit-button" type="submit">
                    {pending === 'authenticate' ? 'Please wait...' : mode === 'login' ? 'Sign in' : 'Create account'}
                    {pending === 'authenticate' ? <LoaderCircle className="spin" size={18} /> : <ArrowRight size={18} />}
                  </button>
                </fieldset>
              </form>
            </div>
          )}
          <div className="account-footnote"><LockKeyhole size={14} /> Private account access</div>
        </section>

        <aside className="community-panel" aria-label="Academic community">
          <figure>
            <img src="/campus.jpg" alt="Graduates celebrating together and throwing their caps into the sky" width="1400" height="933" fetchPriority="high" />
            <figcaption><span>The academic community</span><span className="caption-mark" aria-hidden="true">PS / 01</span></figcaption>
          </figure>
          <div className="community-signature"><span className="signature-line" /><BookOpen size={20} strokeWidth={1.5} /><span className="signature-line" /></div>
        </aside>
      </main>

      <footer className="site-footer"><span>Professor Search</span><span>Account access</span></footer>
    </div>
  )
}

export default App
