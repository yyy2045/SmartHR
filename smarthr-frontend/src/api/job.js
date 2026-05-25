import api from './index'

// GET /api/jobs
export function getJobs(params) {
  return api.get('/api/jobs', { params })
}

// GET /api/jobs/:id
export function getJob(id) {
  return api.get(`/api/jobs/${id}`)
}

// POST /api/jobs
export function createJob(data) {
  return api.post('/api/jobs', data)
}

// PUT /api/jobs/:id
export function updateJob(id, data) {
  return api.put(`/api/jobs/${id}`, data)
}

// DELETE /api/jobs/:id
export function deleteJob(id) {
  return api.delete(`/api/jobs/${id}`)
}

// POST /api/jobs/:id/extract-tags
export function extractJobTags(jobId) {
  return api.post(`/api/jobs/${jobId}/extract-tags`)
}