import { ApiError } from './api'

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

async function request<Result>(path: string, options: RequestInit = {}, accessToken?: string): Promise<Result> {
  const headers = new Headers(options.headers)
  if (options.method && options.method !== 'GET') headers.set('X-CSRF-Protection', '1')
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)

  let response: Response
  try {
    response = await fetch(path, {
      ...options,
      credentials: 'include',
      cache: 'no-store',
      headers,
      signal: AbortSignal.timeout(15000),
    })
  } catch {
    throw new ApiError('Unable to reach the server. Please try again.', 0)
  }

  if (response.status === 204) return undefined as Result
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError(errorDetail(body) || 'Request failed.', response.status)
  }
  if (body === null) throw new ApiError('The server returned an unexpected response.', 502)
  return body as Result
}

// Catalog
export const getCountries = () => request<any[]>('/api/v1/countries')
export const getVisas = (countryCode: string) => request<any[]>(`/api/v1/countries/${countryCode}/visas`)
export const getUniversities = (countryCode?: string) => request<any[]>(`/api/v1/universities${countryCode ? `?country_code=${countryCode}` : ''}`)
export const getUniversity = (id: string) => request<any>(`/api/v1/universities/${id}`)
export const getPrograms = (universityId: string) => request<any[]>(`/api/v1/universities/${universityId}/programs`)
export const getProfessors = (universityId: string, departmentId?: string) => request<any[]>(`/api/v1/universities/${universityId}/professors${departmentId ? `?department_id=${departmentId}` : ''}`)
export const getFunding = (universityId: string) => request<any[]>(`/api/v1/universities/${universityId}/funding`)
export const getNews = (limit = 20) => request<any[]>(`/api/v1/news?limit=${limit}`)
export const getAds = (universityId?: string) => request<any[]>(`/api/v1/advertisements${universityId ? `?university_id=${universityId}` : ''}`)

// Profile
export const getAcademicProfile = (token: string) => request<any>('/api/v1/me/academic-profile', {}, token)
export const saveAcademicProfile = (token: string, data: any) => request<any>('/api/v1/me/academic-profile', { method: 'PUT', body: JSON.stringify(data) }, token)
export const getResearchProfile = (token: string) => request<any>('/api/v1/me/research-profile', {}, token)
export const saveResearchProfile = (token: string, data: any) => request<any>('/api/v1/me/research-profile', { method: 'PUT', body: JSON.stringify(data) }, token)
export const getCVs = (token: string) => request<any[]>('/api/v1/me/cvs', {}, token)
export const addCV = (token: string, data: any) => request<any>('/api/v1/me/cvs', { method: 'POST', body: JSON.stringify(data) }, token)
export const getPreferences = (token: string) => request<any[]>('/api/v1/me/preferences', {}, token)
export const addPreference = (token: string, data: any) => request<any>('/api/v1/me/preferences', { method: 'POST', body: JSON.stringify(data) }, token)
export const deletePreference = (token: string, id: string) => request<any>(`/api/v1/me/preferences/${id}`, { method: 'DELETE' }, token)

// Matching
export const getMatches = (token: string) => request<any[]>('/api/v1/matches', {}, token)
export const generateMatches = (token: string) => request<any>('/api/v1/matches/generate', { method: 'POST', body: JSON.stringify({}) }, token)

// Applications
export const getApplications = (token: string) => request<any[]>('/api/v1/applications', {}, token)
export const createApplication = (token: string, data: any) => request<any>('/api/v1/applications', { method: 'POST', body: JSON.stringify(data) }, token)
export const updateApplicationStage = (token: string, id: string, data: any) => request<any>(`/api/v1/applications/${id}/stage`, { method: 'PATCH', body: JSON.stringify(data) }, token)
export const addApplicationDocument = (token: string, id: string, data: any) => request<any>(`/api/v1/applications/${id}/documents`, { method: 'POST', body: JSON.stringify(data) }, token)

// Outreach
export const getOutreach = (token: string) => request<any[]>('/api/v1/outreach', {}, token)
export const createOutreach = (token: string, data: any) => request<any>('/api/v1/outreach', { method: 'POST', body: JSON.stringify(data) }, token)
export const updateOutreachStage = (token: string, id: string, data: any) => request<any>(`/api/v1/outreach/${id}/stage`, { method: 'PATCH', body: JSON.stringify(data) }, token)
export const addOutreachEmail = (token: string, id: string, data: any) => request<any>(`/api/v1/outreach/${id}/emails`, { method: 'POST', body: JSON.stringify(data) }, token)

// Checklists
export const getChecklists = (token: string) => request<any[]>('/api/v1/checklists', {}, token)
export const createChecklist = (token: string, data: any) => request<any>('/api/v1/checklists', { method: 'POST', body: JSON.stringify(data) }, token)
export const addChecklistItem = (token: string, id: string, data: any) => request<any>(`/api/v1/checklists/${id}/items`, { method: 'POST', body: JSON.stringify(data) }, token)
export const completeChecklistItem = (token: string, checklistId: string, itemId: string) => request<any>(`/api/v1/checklists/${checklistId}/items/${itemId}/complete`, { method: 'PATCH' }, token)
