<template>
  <AppLayout>
    <div class="page-header">
      <h2>系统配置</h2>
    </div>

    <el-tabs v-model="activeTab" class="config-tabs">
      <el-tab-pane label="数据库" name="database">
        <el-card>
          <template #header>
            <span>数据库连接状态</span>
          </template>
          <el-form label-width="120px">
            <el-form-item label="MySQL">
              <el-tag :type="dbStatus.mysql ? 'success' : 'danger'">
                {{ dbStatus.mysql ? '已连接' : '未连接' }}
              </el-tag>
              <span class="db-info">localhost:3306</span>
            </el-form-item>
            <el-form-item label="Redis">
              <el-tag :type="dbStatus.redis ? 'success' : 'danger'">
                {{ dbStatus.redis ? '已连接' : '未连接' }}
              </el-tag>
              <span class="db-info">localhost:6379</span>
            </el-form-item>
            <el-form-item label="Chroma">
              <el-tag :type="dbStatus.chroma ? 'success' : 'danger'">
                {{ dbStatus.chroma ? '已连接' : '未连接' }}
              </el-tag>
              <span class="db-info">localhost:8000</span>
            </el-form-item>
            <el-form-item>
              <el-button @click="checkConnections" :loading="checking">刷新状态</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="企业信息" name="company">
        <el-card>
          <template #header>
            <span>企业设置</span>
          </template>
          <el-form :model="companyInfo" label-width="120px">
            <el-form-item label="企业名称">
              <el-input v-model="companyInfo.name" />
            </el-form-item>
            <el-form-item label="所属行业">
              <el-input v-model="companyInfo.industry" />
            </el-form-item>
            <el-form-item label="企业简介">
              <el-input v-model="companyInfo.description" type="textarea" :rows="4" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveCompanyInfo" :loading="saving">保存</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </AppLayout>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import AppLayout from '@/components/common/AppLayout.vue'
import { ElMessage } from 'element-plus'
import { checkDbStatus, getCompanyInfo, saveCompanyInfo as saveCompanyApi } from '@/api/config'
import { getCurrentUser } from '@/api/auth'

const activeTab = ref('database')
const saving = ref(false)
const checking = ref(false)

const companyInfo = reactive({
  id: null,
  name: '',
  industry: '',
  description: ''
})

const dbStatus = ref({
  mysql: false,
  redis: false,
  chroma: false
})

const saveCompanyInfoHandler = async () => {
  if (!companyInfo.id) {
    ElMessage.warning('请先获取企业信息')
    return
  }
  saving.value = true
  try {
    await saveCompanyApi(companyInfo)
    ElMessage.success('企业信息已保存')
  } catch (error) {
    ElMessage.error('保存失败: ' + (error.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

const checkConnections = async () => {
  checking.value = true
  try {
    const res = await checkDbStatus()
    dbStatus.value = {
      mysql: !!res.mysql,
      redis: !!res.redis,
      chroma: res.chroma !== false
    }
  } catch (error) {
    console.error('Failed to check db status:', error)
    ElMessage.error('检查连接状态失败')
  } finally {
    checking.value = false
  }
}

const loadCompanyInfo = async () => {
  try {
    const userRes = await getCurrentUser()
    if (userRes && userRes.companyId) {
      const res = await getCompanyInfo(userRes.companyId)
      if (res) {
        companyInfo.id = res.id
        companyInfo.name = res.name || ''
        companyInfo.industry = res.industry || ''
        companyInfo.description = res.description || ''
      }
    }
  } catch (error) {
    console.error('Failed to load company info:', error)
  }
}

onMounted(() => {
  checkConnections()
  loadCompanyInfo()
})

// 暴露方法给模板使用
const saveCompanyInfo = saveCompanyInfoHandler
</script>

<style scoped>
.config-tabs {
  max-width: 800px;
}

.db-info {
  margin-left: 12px;
  color: #909399;
  font-size: 13px;
}
</style>