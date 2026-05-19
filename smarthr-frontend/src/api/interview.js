import api from './index'

// POST /api/interview/sessions
export function createInterviewSession(data) {
  return api.post('/api/interview/sessions', data)
}

// GET /api/interview/sessions
export function getInterviewSessions(params) {
  return api.get('/api/interview/sessions', { params })
}

// GET /api/interview/sessions/:id
export function getInterviewSession(id) {
  return api.get(`/api/interview/sessions/${id}`)
}

// POST /api/interview/sessions/:id/message
export function sendInterviewMessage(sessionId, data) {
  return api.post(`/api/interview/sessions/${sessionId}/message`, data)
}

// POST /api/interview/sessions/:id/end
export function endInterview(sessionId) {
  return api.post(`/api/interview/sessions/${sessionId}/end`)
}

// GET /api/interview/sessions/:id/report
export function getInterviewReport(sessionId) {
  return api.get(`/api/interview/sessions/${sessionId}/report`)
}

// GET /api/interview/sessions/:id/resume
export function getInterviewResume(sessionId) {
  return api.get(`/api/interview/sessions/${sessionId}/resume`)
}