import api from './index'

// POST /knowledge/documents
export function uploadDocument(file, docType, companyId, title) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('docType', docType)
  formData.append('companyId', companyId)
  formData.append('title', title)
  return api.post('/knowledge/documents', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// GET /knowledge/documents
export function getDocuments(params) {
  return api.get('/knowledge/documents', { params })
}

// GET /knowledge/documents/:id
export function getDocument(id, companyId) {
  return api.get(`/knowledge/documents/${id}`, {
    params: { companyId }
  })
}

// DELETE /knowledge/documents/:id
export function deleteDocument(id, companyId) {
  return api.delete(`/knowledge/documents/${id}`, {
    params: { companyId }
  })
}

// POST /knowledge/documents/:id/reindex
export function reindexDocument(id, companyId) {
  return api.post(`/knowledge/documents/${id}/reindex`, null, {
    params: { companyId }
  })
}

// GET /knowledge/search
export function searchKnowledge(query, companyId, topK = 5) {
  return api.get('/knowledge/search', {
    params: { query, companyId, topK }
  })
}