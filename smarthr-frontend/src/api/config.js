import api from './index'

// 企业信息
export function saveCompanyInfo(data) {
  return api.put('/companies/' + data.id, data)
}

export function getCompanyInfo(id) {
  return api.get('/companies/' + id)
}

// 数据库连接状态
export function checkDbStatus() {
  return api.get('/health/db-status')
}