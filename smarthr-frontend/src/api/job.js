import api from './index'

// GET /jobs
export function getJobs(params) {
  return api.get('/jobs', { params })
}

// GET /jobs/:id
export function getJob(id) {
  return api.get(`/jobs/${id}`)
}

// POST /jobs
export function createJob(data) {
  return api.post('/jobs', data)
}

// PUT /jobs/:id
export function updateJob(id, data) {
  return api.put(`/jobs/${id}`, data)
}

// DELETE /jobs/:id
export function deleteJob(id) {
  return api.delete(`/jobs/${id}`)
}

// POST /jobs/:id/extract-tags
export function extractJobTags(jobId) {
  return api.post(`/jobs/${jobId}/extract-tags`)
}