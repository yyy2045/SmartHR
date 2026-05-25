import api from './index'

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