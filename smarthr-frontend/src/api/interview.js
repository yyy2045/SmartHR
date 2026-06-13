import api from './index'

export function getInterviewSessions(params) {
  return api.get('/interview/sessions', { params })
}

export function createInterviewSession(data) {
  return api.post('/interview/sessions', data)
}

export function getInterviewSession(id) {
  return api.get(`/interview/sessions/${id}`)
}

export function sendInterviewMessage(sessionId, data) {
  return api.post(`/interview/sessions/${sessionId}/message`, data)
}

export function endInterview(sessionId) {
  return api.post(`/interview/sessions/${sessionId}/end`)
}

export function getInterviewReport(sessionId) {
  return api.get(`/interview/sessions/${sessionId}/report`)
}

export function getInterviewResume(sessionId) {
  return api.post(`/interview/sessions/${sessionId}/resume`)
}

export function getReportsCount() {
  return api.get('/interview/reports/stats/count')
}
