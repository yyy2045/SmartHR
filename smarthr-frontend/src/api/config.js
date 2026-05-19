import api from './index'

// LLM 配置
export function saveLlmConfig(data) {
  return api.post('/api/config/llm', data)
}

export function getLlmConfig() {
  return api.get('/api/config/llm')
}

// 企业信息
export function saveCompanyInfo(data) {
  return api.put('/api/companies/' + data.id, data)
}

export function getCompanyInfo(id) {
  return api.get('/api/companies/' + id)
}

// 数据库连接状态
export function checkDbStatus() {
  return api.get('/api/health/db-status')
}