import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  Building2,
  CheckCircle2,
  FileText,
  Globe2,
  GraduationCap,
  HeartHandshake,
  Mail,
  Newspaper,
  Plus,
  Search,
  Sparkles,
  Trash2,
  UserRound,
} from 'lucide-react'
import type { Session } from './api'
import * as api from './profmatApi'
import './App.css'

type Tab = 'dashboard' | 'profile' | 'countries' | 'universities' | 'matches' | 'applications' | 'outreach' | 'checklists' | 'news'

const navItems: { id: Tab; label: string; icon: any }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
  { id: 'profile', label: 'Profile', icon: UserRound },
  { id: 'countries', label: 'Countries & Visas', icon: Globe2 },
  { id: 'universities', label: 'Universities', icon: Building2 },
  { id: 'matches', label: 'Matches', icon: Sparkles },
  { id: 'applications', label: 'Applications', icon: FileText },
  { id: 'outreach', label: 'Professor Outreach', icon: Mail },
  { id: 'checklists', label: 'Checklists', icon: CheckCircle2 },
  { id: 'news', label: 'News', icon: Newspaper },
]

export default function ProfmatApp({ session, onLogout }: { session: Session; onLogout: () => void }) {
  const [tab, setTab] = useState<Tab>('dashboard')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const token = session.accessToken

  const show = (msg: string) => { setNotice(msg); setError(''); window.setTimeout(() => setNotice(''), 2800) }
  const err = (e: unknown) => setError(e instanceof Error ? e.message : 'Something went wrong')

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="brand">
          <div className="brand-mark">PS</div>
          <div>
            <p className="brand-name">Professor Search</p>
            <p className="brand-subtitle">PROFMAT Intelligence Platform</p>
          </div>
        </div>
        <nav className="main-nav">
          {navItems.map(item => {
            const Icon = item.icon
            return (
              <button key={item.id} className={`nav-btn ${tab === item.id ? 'active' : ''}`} onClick={() => setTab(item.id)}>
                <Icon size={16} /> {item.label}
              </button>
            )
          })}
        </nav>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div className="user-pill">
            <div className="user-avatar"><UserRound size={18} /></div>
            <div className="user-meta">
              <span className="user-email">{session.user.full_name || session.user.email}</span>
              <span className="user-role">{session.user.role === 'ADMIN' ? 'Administrator' : 'Student'}</span>
            </div>
          </div>
          <button className="ghost-button" onClick={onLogout}>Sign out</button>
        </div>
      </header>
      <main style={{ width: 'min(1200px, calc(100% - 64px))', margin: '0 auto', padding: '40px 0 80px', display: 'flex', flexDirection: 'column', gap: 32 }}>
        {error && <div className="form-alert error"><span>{error}</span></div>}
        {notice && <div className="form-alert notice"><CheckCircle2 size={18} /><span>{notice}</span></div>}
        {tab === 'dashboard' && <Dashboard token={token} setTab={setTab} />}
        {tab === 'profile' && <ProfileTab token={token} show={show} err={err} />}
        {tab === 'countries' && <CountriesTab err={err} />}
        {tab === 'universities' && <UniversitiesTab err={err} />}
        {tab === 'matches' && <MatchesTab token={token} show={show} err={err} />}
        {tab === 'applications' && <ApplicationsTab token={token} show={show} err={err} />}
        {tab === 'outreach' && <OutreachTab token={token} show={show} err={err} />}
        {tab === 'checklists' && <ChecklistsTab token={token} show={show} err={err} />}
        {tab === 'news' && <NewsTab err={err} />}
      </main>
    </div>
  )
}

function Dashboard({ token, setTab }: any) {
  const [data, setData] = useState<any>({})
  useEffect(() => {
    Promise.all([
      api.getMatches(token).catch(() => []),
      api.getApplications(token).catch(() => []),
      api.getOutreach(token).catch(() => []),
      api.getChecklists(token).catch(() => []),
    ]).then(([m, a, o, c]) => setData({ m, a, o, c }))
  }, [token])

  const stats = [
    { label: 'Smart Matches', value: data.m?.length || 0, icon: Sparkles, tab: 'matches' as Tab },
    { label: 'Applications', value: data.a?.length || 0, icon: FileText, tab: 'applications' as Tab },
    { label: 'Outreach', value: data.o?.length || 0, icon: Mail, tab: 'outreach' as Tab },
    { label: 'Active Checklists', value: data.c?.length || 0, icon: CheckCircle2, tab: 'checklists' as Tab },
  ]

  return (
    <div className="dashboard">
      <header className="dashboard-hero">
        <div>
          <span className="eyebrow"><GraduationCap size={16} /> Plan your postgraduate journey</span>
          <h1>Track every opportunity in one place</h1>
          <p>Build your profile, discover matching professors and programs, manage applications and outreach, and stay on top of deadlines with intelligent checklists.</p>
        </div>
        <div className="hero-actions">
          <button className="primary-button" onClick={() => setTab('matches')}><Sparkles size={18} /> Generate matches <ArrowRight size={18} /></button>
          <button className="secondary-button" onClick={() => setTab('universities')}><Search size={18} /> Browse universities</button>
        </div>
      </header>
      <div className="stats-grid">
        {stats.map(stat => {
          const Icon = stat.icon
          return (
            <button key={stat.label} className="stat-card" onClick={() => setTab(stat.tab)}>
              <div className="stat-icon"><Icon size={22} /></div>
              <div>
                <p className="stat-label">{stat.label}</p>
                <p className="stat-value">{stat.value}</p>
              </div>
              <ArrowRight size={18} style={{ marginLeft: 'auto', color: 'var(--muted)' }} />
            </button>
          )
        })}
      </div>
      <section>
        <header className="section-header">
          <div>
            <h2>Quick actions</h2>
            <p>Jump straight into the areas that need your attention</p>
          </div>
        </header>
        <div className="panel panel-grid">
          <article className="panel-card">
            <header><h3>Complete your profile</h3><UserRound size={18} /></header>
            <p>Update your academic background, research interests, CV and country preferences to get better matches.</p>
            <button className="link-button" onClick={() => setTab('profile')}>Go to profile <ArrowRight size={16} /></button>
          </article>
          <article className="panel-card">
            <header><h3>Find funding & supervisors</h3><HeartHandshake size={18} /></header>
            <p>Explore universities, programs, professors and funding opportunities curated for your goals.</p>
            <button className="link-button" onClick={() => setTab('universities')}>Browse catalog <ArrowRight size={16} /></button>
          </article>
          <article className="panel-card">
            <header><h3>Stay on track</h3><CheckCircle2 size={18} /></header>
            <p>Use checklists to manage documents, deadlines and follow-ups for every application and outreach.</p>
            <button className="link-button" onClick={() => setTab('checklists')}>View checklists <ArrowRight size={16} /></button>
          </article>
        </div>
      </section>
    </div>
  )
}

function Panel({ title, subtitle, children, action }: any) {
  return (
    <section className="panel">
      <header className="section-header" style={{ padding: '24px 32px 0' }}>
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {action}
      </header>
      <div style={{ padding: '16px 32px 32px', display: 'flex', flexDirection: 'column', gap: 16 }}>{children}</div>
    </section>
  )
}

function ProfileTab({ token, show, err }: any) {
  const [a, setA] = useState<any>({})
  const [r, setR] = useState<any>({})
  const [cvs, setCvs] = useState<any[]>([])
  const [prefs, setPrefs] = useState<any[]>([])
  useEffect(() => {
    api.getAcademicProfile(token).then(setA).catch(() => {})
    api.getResearchProfile(token).then(setR).catch(() => {})
    api.getCVs(token).then(setCvs).catch(() => {})
    api.getPreferences(token).then(setPrefs).catch(() => {})
  }, [token])
  const saveA = async (e: FormEvent<HTMLFormElement>) => { e.preventDefault(); const f = new FormData(e.currentTarget); const data: any = Object.fromEntries(f); if (data.graduation_year) data.graduation_year = Number(data.graduation_year); try { await api.saveAcademicProfile(token, data); show('Academic profile updated') } catch (ex) { err(ex) } }
  const saveR = async (e: FormEvent<HTMLFormElement>) => { e.preventDefault(); try { await api.saveResearchProfile(token, Object.fromEntries(new FormData(e.currentTarget))); show('Research profile updated') } catch (ex) { err(ex) } }
  const addCv = async (e: FormEvent<HTMLFormElement>) => { e.preventDefault(); const f = new FormData(e.currentTarget); try { await api.addCV(token, Object.fromEntries(f)); show('CV uploaded'); api.getCVs(token).then(setCvs); e.currentTarget.reset() } catch (ex) { err(ex) } }
  const addPref = async (e: FormEvent<HTMLFormElement>) => { e.preventDefault(); const f = new FormData(e.currentTarget); const data: any = Object.fromEntries(f); if (data.priority) data.priority = Number(data.priority); try { await api.addPreference(token, data); show('Preference added'); api.getPreferences(token).then(setPrefs); e.currentTarget.reset() } catch (ex) { err(ex) } }
  const delPref = async (id: string) => { try { await api.deletePreference(token, id); setPrefs((p: any[]) => p.filter((x: any) => x.id !== id)); show('Preference removed') } catch (ex) { err(ex) } }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <header className="section-header">
        <div><h1 style={{ margin: 0 }}>My Profile</h1><p>Keep your academic story up to date to improve match quality</p></div>
      </header>
      <div className="panel">
        <header className="section-header" style={{ padding: '24px 32px 0' }}><div><h2>Academic Profile</h2><p>Education, test scores and background</p></div></header>
        <form onSubmit={saveA} style={{ padding: '16px 32px 32px', display: 'grid', gap: 16 }}>
          <div className="form-grid">
            <div className="field"><label>Degree level</label><input name="degree_level" defaultValue={a.degree_level || ''} placeholder="e.g. Bachelor, Master" /></div>
            <div className="field"><label>Field of study</label><input name="field_of_study" defaultValue={a.field_of_study || ''} placeholder="e.g. Computer Science" /></div>
            <div className="field"><label>Previous university</label><input name="previous_university" defaultValue={a.previous_university || ''} placeholder="University name" /></div>
            <div className="field"><label>GPA</label><input name="gpa" defaultValue={a.gpa || ''} placeholder="e.g. 3.8/4.0" /></div>
            <div className="field"><label>Graduation year</label><input name="graduation_year" type="number" defaultValue={a.graduation_year || ''} placeholder="2024" /></div>
            <div className="field"><label>English test score</label><input name="english_test_score" defaultValue={a.english_test_score || ''} placeholder="IELTS/TOEFL" /></div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}><button className="primary-button"><BookOpen size={18} /> Save academic profile</button></div>
        </form>
      </div>
      <div className="panel">
        <header className="section-header" style={{ padding: '24px 32px 0' }}><div><h2>Research Profile</h2><p>Interests, publications, skills and goals</p></div></header>
        <form onSubmit={saveR} style={{ padding: '16px 32px 32px', display: 'grid', gap: 16 }}>
          <div className="form-grid">
            <div className="field" style={{ gridColumn: '1 / -1' }}><label>Research interests</label><textarea name="research_interests" defaultValue={r.research_interests || ''} placeholder="Describe your research interests..." /></div>
            <div className="field" style={{ gridColumn: '1 / -1' }}><label>Publications</label><textarea name="publications" defaultValue={r.publications || ''} placeholder="List publications, if any" /></div>
            <div className="field" style={{ gridColumn: '1 / -1' }}><label>Skills</label><textarea name="skills" defaultValue={r.skills || ''} placeholder="Technical and research skills" /></div>
            <div className="field" style={{ gridColumn: '1 / -1' }}><label>Research experience</label><textarea name="research_experience" defaultValue={r.research_experience || ''} placeholder="Describe your research experience" /></div>
            <div className="field"><label>Preferred degree</label><input name="preferred_degree" defaultValue={r.preferred_degree || ''} placeholder="MSc / PhD" /></div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}><button className="primary-button"><Sparkles size={18} /> Save research profile</button></div>
        </form>
      </div>
      <div className="panel-grid">
        <section className="panel-card">
          <header><div><h3>CVs</h3><p>Manage your uploaded documents</p></div><FileText size={18} /></header>
          <form onSubmit={addCv} style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <input name="file_url" placeholder="https://.../cv.pdf" required style={{ flex: '1 1 240px', borderRadius: 999, border: '1px solid var(--line)', padding: '8px 16px' }} />
            <input name="version" placeholder="v1.0" style={{ borderRadius: 999, border: '1px solid var(--line)', padding: '8px 16px' }} />
            <button className="primary-button"><Plus size={18} /> Add CV</button>
          </form>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {cvs.length === 0 && <div className="empty-state">No CVs added yet</div>}
            {cvs.map((x: any) => <div key={x.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderRadius: 12, border: '1px solid var(--line)' }}><span>{x.file_url}</span>{x.version && <span className="tag">v{x.version}</span>}</div>)}
          </div>
        </section>
        <section className="panel-card">
          <header><div><h3>Country Preferences</h3><p>Rank where you'd like to study</p></div><Globe2 size={18} /></header>
          <form onSubmit={addPref} style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <input name="country_code" placeholder="US, CA, UK" required style={{ borderRadius: 999, border: '1px solid var(--line)', padding: '8px 16px' }} />
            <input name="priority" type="number" placeholder="Priority 1-10" style={{ borderRadius: 999, border: '1px solid var(--line)', padding: '8px 16px' }} />
            <button className="primary-button"><Plus size={18} /> Add preference</button>
          </form>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {prefs.length === 0 && <div className="empty-state">No preferences added yet</div>}
            {prefs.map((x: any) => <div key={x.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderRadius: 12, border: '1px solid var(--line)' }}><span>{x.country_code}</span><div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>{x.priority && <span className="tag">Priority {x.priority}</span>}<button className="ghost-button" onClick={() => delPref(x.id)}><Trash2 size={16} /></button></div></div>)}
          </div>
        </section>
      </div>
    </div>
  )
}

function DataList({ items, render }: any) {
  if (!items?.length) return <div className="empty-state">Nothing here yet</div>
  return <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>{items.map((item: any, idx: number) => <div key={item.id || idx} style={{ padding: '16px 20px', borderRadius: 14, border: '1px solid var(--line)', display: 'flex', flexDirection: 'column', gap: 8 }}>{render(item)}</div>)}</div>
}

function CountriesTab({ err }: any) {
  const [countries, setCountries] = useState<any[]>([])
  const [visas, setVisas] = useState<any[]>([])
  const [sel, setSel] = useState('')
  useEffect(() => { api.getCountries().then(setCountries).catch(err) }, [err])
  const loadVisas = async (code: string) => { setSel(code); try { setVisas(await api.getVisas(code)) } catch (ex) { err(ex) } }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <header className="section-header"><div><h1 style={{ margin: 0 }}>Countries & Visa Information</h1><p>Explore study destinations and entry requirements</p></div></header>
      <div className="panel-grid">
        <section className="panel">
          <header className="section-header" style={{ padding: '24px 32px 0' }}><div><h2>Countries</h2><p>Select a country to view visas</p></div></header>
          <div style={{ padding: '16px 32px 32px', display: 'flex', flexDirection: 'column', gap: 10 }}>
            {countries.map((c: any) => <button key={c.country_code} className="secondary-button" style={{ justifyContent: 'space-between' }} onClick={() => loadVisas(c.country_code)}><span>{c.name} ({c.country_code})</span><ArrowRight size={16} /></button>)}
          </div>
        </section>
        <section className="panel">
          <header className="section-header" style={{ padding: '24px 32px 0' }}><div><h2>Visa Information {sel && `• ${sel}`}</h2><p>Requirements and processing times</p></div></header>
          <div style={{ padding: '16px 32px 32px', display: 'flex', flexDirection: 'column', gap: 12 }}>
            {visas.length === 0 && <div className="empty-state">Select a country to load visa details</div>}
            {visas.map((v: any) => <article key={v.id} style={{ padding: '18px 22px', borderRadius: 14, border: '1px solid var(--line)', display: 'flex', flexDirection: 'column', gap: 8 }}><div style={{ display: 'flex', justifyContent: 'space-between' }}><h3 style={{ margin: 0 }}>{v.visa_type}</h3>{v.processing_time && <span className="tag">{v.processing_time}</span>}</div>{v.requirements && <p style={{ margin: 0, color: 'var(--muted)' }}>{v.requirements}</p>}</article>)}
          </div>
        </section>
      </div>
    </div>
  )
}

function UniversitiesTab({ err }: any) {
  const [unis, setUnis] = useState<any[]>([])
  const [progs, setProgs] = useState<any[]>([])
  const [profs, setProfs] = useState<any[]>([])
  const [fund, setFund] = useState<any[]>([])
  const [sel, setSel] = useState('')
  useEffect(() => { api.getUniversities().then(setUnis).catch(err) }, [err])
  const load = async (id: string) => { setSel(id); try { const [p, pr, f] = await Promise.all([api.getPrograms(id), api.getProfessors(id), api.getFunding(id)]); setProgs(p); setProfs(pr); setFund(f) } catch (ex) { err(ex) } }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <header className="section-header"><div><h1 style={{ margin: 0 }}>Universities & Programs</h1><p>Discover departments, supervisors and funding</p></div></header>
      <div className="panel-grid">
        <section className="panel">
          <header className="section-header" style={{ padding: '24px 32px 0' }}><div><h2>Universities</h2></div></header>
          <div style={{ padding: '16px 32px 32px', display: 'flex', flexDirection: 'column', gap: 10 }}>{unis.map((u: any) => <button key={u.id} className="secondary-button" style={{ justifyContent: 'space-between' }} onClick={() => load(u.id)}><span>{u.name}</span><ArrowRight size={16} /></button>)}</div>
        </section>
        <section className="panel">
          <header className="section-header" style={{ padding: '24px 32px 0' }}><div><h2>Details</h2><p>Programs, professors and funding</p></div></header>
          <div style={{ padding: '16px 32px 32px', display: 'flex', flexDirection: 'column', gap: 24 }}>
            {!sel && <div className="empty-state">Select a university to explore</div>}
            {sel && <>
              <div><h3>Programs</h3><DataList items={progs} render={(p: any) => <div style={{ display: 'flex', justifyContent: 'space-between' }}><div><strong>{p.name}</strong><p style={{ margin: 0, color: 'var(--muted)' }}>{p.field_of_study || p.degree_level}</p></div>{p.degree_level && <span className="tag">{p.degree_level}</span>}</div>} /></div>
              <div><h3>Professors</h3><DataList items={profs} render={(p: any) => <div style={{ display: 'flex', justifyContent: 'space-between' }}><div><strong>{p.name}</strong><p style={{ margin: 0, color: 'var(--muted)' }}>{p.designation || p.research_areas}</p></div>{p.email && <span className="tag">{p.email}</span>}</div>} /></div>
              <div><h3>Funding</h3><DataList items={fund} render={(f: any) => <div style={{ display: 'flex', justifyContent: 'space-between' }}><div><strong>{f.title}</strong><p style={{ margin: 0, color: 'var(--muted)' }}>{f.funding_type} {f.amount ? `• ${f.amount}` : ''}</p></div></div>} /></div>
            </>}
          </div>
        </section>
      </div>
    </div>
  )
}

function MatchesTab({ token, show, err }: any) {
  const [matches, setMatches] = useState<any[]>([])
  const load = () => api.getMatches(token).then(setMatches).catch(err)
  useEffect(() => { load() }, [token])
  const gen = async () => { try { await api.generateMatches(token); show('Matches generated'); load() } catch (ex) { err(ex) } }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <header className="section-header"><div><h1 style={{ margin: 0 }}>Smart Matches</h1><p>Personalized recommendations based on your profile</p></div><button className="primary-button" onClick={gen}><Sparkles size={18} /> Generate new matches</button></header>
      <Panel title="Your matches" subtitle="Review and save opportunities">
        <DataList items={matches} render={(m: any) => <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}><div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}><div style={{ display: 'flex', alignItems: 'center', gap: 10 }}><strong>Match Score: {m.match_score}</strong><span className="tag">{m.status}</span></div><p style={{ margin: 0, color: 'var(--muted)' }}>{m.explanation}</p></div></div>} />
      </Panel>
    </div>
  )
}

function ApplicationsTab({ token, show, err }: any) {
  const [apps, setApps] = useState<any[]>([])
  const load = () => api.getApplications(token).then(setApps).catch(err)
  useEffect(() => { load() }, [token])
  const create = async (e: FormEvent<HTMLFormElement>) => { e.preventDefault(); const f = new FormData(e.currentTarget); const data: any = Object.fromEntries(f); try { await api.createApplication(token, data); show('Application created'); load(); e.currentTarget.reset() } catch (ex) { err(ex) } }
  const stage = async (id: string, st: string) => { try { await api.updateApplicationStage(token, id, { stage: st }); show('Stage updated'); load() } catch (ex) { err(ex) } }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <header className="section-header"><div><h1 style={{ margin: 0 }}>University Applications</h1><p>Track every application from draft to decision</p></div></header>
      <Panel title="Create application" subtitle="Add a new target program">
        <form onSubmit={create} className="form-grid">
          <div className="field"><label>University ID</label><input name="university_id" required placeholder="UUID" /></div>
          <div className="field"><label>Course Program ID</label><input name="course_program_id" required placeholder="UUID" /></div>
          <div className="field"><label>Application type</label><input name="application_type" placeholder="Direct / Through portal" /></div>
          <div className="field"><label>Initial stage</label><input name="stage" defaultValue="SAVED" /></div>
          <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'flex-end' }}><button className="primary-button"><Plus size={18} /> Create application</button></div>
        </form>
      </Panel>
      <Panel title="My applications" subtitle="Manage stages and documents">
        <DataList items={apps} render={(a: any) => <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}><div><strong>Application</strong><p style={{ margin: 0, color: 'var(--muted)' }}>Stage: {a.stage}</p></div><div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}><button className="secondary-button" onClick={() => stage(a.id, 'PREPARING_DOCUMENTS')}>Preparing</button><button className="secondary-button" onClick={() => stage(a.id, 'SUBMITTED')}>Submitted</button><button className="secondary-button" onClick={() => stage(a.id, 'UNDER_REVIEW')}>Under Review</button></div></div>} />
      </Panel>
    </div>
  )
}

function OutreachTab({ token, show, err }: any) {
  const [list, setList] = useState<any[]>([])
  const load = () => api.getOutreach(token).then(setList).catch(err)
  useEffect(() => { load() }, [token])
  const create = async (e: FormEvent<HTMLFormElement>) => { e.preventDefault(); const f = new FormData(e.currentTarget); const data: any = Object.fromEntries(f); try { await api.createOutreach(token, data); show('Outreach created'); load(); e.currentTarget.reset() } catch (ex) { err(ex) } }
  const stage = async (id: string, st: string) => { try { await api.updateOutreachStage(token, id, { stage: st }); show('Stage updated'); load() } catch (ex) { err(ex) } }
  const email = async (id: string) => { const subj = prompt('Email subject'); const body = prompt('Email body'); if (!subj) return; try { await api.addOutreachEmail(token, id, { subject: subj, body, direction: 'OUTBOUND' }); show('Email logged') } catch (ex) { err(ex) } }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <header className="section-header"><div><h1 style={{ margin: 0 }}>Professor Outreach</h1><p>Plan, send and track emails to potential supervisors</p></div></header>
      <Panel title="Start outreach" subtitle="Connect with a professor">
        <form onSubmit={create} className="form-grid">
          <div className="field"><label>Professor ID</label><input name="professor_id" required placeholder="UUID" /></div>
          <div className="field"><label>Purpose</label><input name="purpose" required placeholder="PhD opportunity / Research collaboration" /></div>
          <div className="field"><label>Stage</label><input name="stage" defaultValue="RESEARCHING" /></div>
          <div className="field"><label>Response status</label><input name="response_status" defaultValue="PENDING" /></div>
          <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'flex-end' }}><button className="primary-button"><Plus size={18} /> Create outreach</button></div>
        </form>
      </Panel>
      <Panel title="Active outreach" subtitle="Track conversations">
        <DataList items={list} render={(o: any) => <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}><div><strong>Outreach</strong><p style={{ margin: 0, color: 'var(--muted)' }}>Stage: {o.stage} • Status: {o.response_status}</p></div><div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}><button className="secondary-button" onClick={() => stage(o.id, 'DRAFTING_EMAIL')}>Draft</button><button className="secondary-button" onClick={() => stage(o.id, 'SENT')}>Sent</button><button className="secondary-button" onClick={() => stage(o.id, 'WAITING_FOR_REPLY')}>Waiting</button><button className="primary-button" onClick={() => email(o.id)}><Mail size={16} /> Log email</button></div></div>} />
      </Panel>
    </div>
  )
}

function ChecklistsTab({ token, show, err }: any) {
  const [lists, setLists] = useState<any[]>([])
  const load = () => api.getChecklists(token).then(setLists).catch(err)
  useEffect(() => { load() }, [token])
  const create = async (e: FormEvent<HTMLFormElement>) => { e.preventDefault(); const f = new FormData(e.currentTarget); const data: any = Object.fromEntries(f); try { await api.createChecklist(token, data); show('Checklist created'); load(); e.currentTarget.reset() } catch (ex) { err(ex) } }
  const addItem = async (id: string) => { const title = prompt('Task title'); if (!title) return; try { await api.addChecklistItem(token, id, { title }); show('Task added'); load() } catch (ex) { err(ex) } }
  const done = async (cid: string, iid: string) => { try { await api.completeChecklistItem(token, cid, iid); show('Task completed'); load() } catch (ex) { err(ex) } }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <header className="section-header"><div><h1 style={{ margin: 0 }}>Checklists</h1><p>Never miss a deadline or document</p></div></header>
      <Panel title="Create checklist" subtitle="Link to application or outreach">
        <form onSubmit={create} className="form-grid">
          <div className="field"><label>Title</label><input name="title" required placeholder="PhD Application Checklist" /></div>
          <div className="field"><label>Type</label><input name="checklist_type" required placeholder="application / outreach" /></div>
          <div className="field"><label>Application ID (optional)</label><input name="university_application_id" placeholder="UUID" /></div>
          <div className="field"><label>Outreach ID (optional)</label><input name="professor_outreach_id" placeholder="UUID" /></div>
          <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'flex-end' }}><button className="primary-button"><Plus size={18} /> Create checklist</button></div>
        </form>
      </Panel>
      <Panel title="Your checklists" subtitle="Track tasks">
        {lists.length === 0 && <div className="empty-state">No checklists yet</div>}
        {lists.map((l: any) => <article key={l.id} style={{ padding: '20px 24px', borderRadius: 14, border: '1px solid var(--line)', display: 'flex', flexDirection: 'column', gap: 14 }}><div style={{ display: 'flex', justifyContent: 'space-between' }}><div><strong>{l.title}</strong><p style={{ margin: 0, color: 'var(--muted)' }}>{l.checklist_type} • {l.status}</p></div><button className="secondary-button" onClick={() => addItem(l.id)}><Plus size={16} /> Add task</button></div>{l.items?.map((it: any) => <div key={it.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', borderRadius: 12, background: 'var(--soft)' }}><span style={{ textDecoration: it.status === 'COMPLETED' ? 'line-through' : 'none' }}>{it.title}</span>{it.status !== 'COMPLETED' && <button className="link-button" onClick={() => done(l.id, it.id)}>Mark complete</button>}</div>)}</article>)}
      </Panel>
    </div>
  )
}

function NewsTab({ err }: any) {
  const [news, setNews] = useState<any[]>([])
  useEffect(() => { api.getNews().then(setNews).catch(err) }, [err])
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <header className="section-header"><div><h1 style={{ margin: 0 }}>News & Updates</h1><p>Stay informed about opportunities</p></div></header>
      <div className="panel-grid">
        {news.length === 0 && <div className="panel-card"><div className="empty-state">No news available</div></div>}
        {news.map((n: any) => (
          <article key={n.id} className="panel-card">
            <header>
              <div>
                <h3>{n.title}</h3>
                {n.published_at && <p>{new Date(n.published_at).toLocaleDateString()}</p>}
              </div>
              <Newspaper size={18} />
            </header>
            <p>{n.content}</p>
            {n.source_url && (
              <a href={n.source_url} target="_blank" rel="noreferrer" className="link-button">
                Read more <ArrowRight size={16} />
              </a>
            )}
          </article>
        ))}
      </div>
    </div>
  )
}
