import api from './index'

// GET /api/resumes
export function getResumes(params) {
  return api.get('/api/resumes', { params })
}

// GET /api/resumes/:id
export function getResume(id) {
  return api.get(`/api/resumes/${id}`)
}

// POST /api/resumes/upload
export function uploadResume(file, jobId, candidateName, companyId) {
  const formData = new FormData()
  formData.append('file', file)
  if (jobId) {
    formData.append('jobId', jobId)
  }
  if (candidateName) {
    formData.append('candidateName', candidateName)
  }
  if (companyId) {
    formData.append('companyId', companyId)
  }
  return api.post('/api/resumes/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// POST /api/resumes/:id/match
export function matchResume(resumeId, jobId) {
  return api.post(`/api/resumes/${resumeId}/match`, null, { params: { jobId } })
}

// DELETE /api/resumes/:id
export function deleteResume(id) {
  return api.delete(`/api/resumes/${id}`)
}

// POST /api/resumes/:id/parse
export function parseResume(resumeId) {
  return api.post(`/api/resumes/${resumeId}/parse`)
}

// GET /api/resumes/stats/count-this-week
export function getResumesCountThisWeek() {
  return api.get('/api/resumes/stats/count-this-week')
}