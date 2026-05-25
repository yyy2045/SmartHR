import api from './index'

// GET /resumes
export function getResumes(params) {
  return api.get('/resumes', { params })
}

// GET /resumes/:id
export function getResume(id) {
  return api.get(`/resumes/${id}`)
}

// POST /resumes/upload
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
  return api.post('/resumes/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// POST /resumes/:id/match
export function matchResume(resumeId, jobId) {
  return api.post(`/resumes/${resumeId}/match`, null, { params: { jobId } })
}

// DELETE /resumes/:id
export function deleteResume(id) {
  return api.delete(`/resumes/${id}`)
}

// POST /resumes/:id/parse
export function parseResume(resumeId) {
  return api.post(`/resumes/${resumeId}/parse`)
}

// GET /resumes/stats/count-this-week
export function getResumesCountThisWeek() {
  return api.get('/resumes/stats/count-this-week')
}