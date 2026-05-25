import api from './index'

// POST /api/knowledge/documents
export function uploadDocument(file, docType, companyId, title) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('docType', docType)
  formData.append('companyId', companyId)
  formData.append('title', title)
  return api.post('/api/knowledge/documents', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// GET /api/knowledge/documents
export function getDocuments(params) {
  return api.get('/api/knowledge/documents', { params })
}

// GET /api/knowledge/documents/:id
export function getDocument(id, companyId) {
  return api.get(`/api/knowledge/documents/${id}`, {
    params: { companyId }
  })
}

// DELETE /api/knowledge/documents/:id
export function deleteDocument(id, companyId) {
  return api.delete(`/api/knowledge/documents/${id}`, {
    params: { companyId }
  })
}

// POST /api/knowledge/documents/:id/reindex
export function reindexDocument(id, companyId) {
  return api.post(`/api/knowledge/documents/${id}/reindex`, null, {
    params: { companyId }
  })
}

// GET /api/knowledge/search
export function searchKnowledge(query, companyId, topK = 5) {
  return api.get('/api/knowledge/search', {
    params: { query, companyId, topK }
  })
}