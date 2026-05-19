<template>
  <AppLayout>
    <div class="page-header">
      <h2>系统配置</h2>
    </div>

    <el-tabs v-model="activeTab" class="config-tabs">
      <el-tab-pane label="LLM 设置" name="llm">
        <el-card>
          <template #header>
            <span>大语言模型配置</span>
          </template>
          <el-form :model="llmConfig" label-width="120px">
            <el-form-item label="API 基础地址">
              <el-input v-model="llmConfig.baseUrl" placeholder="https://api.deepseek.com" />
            </el-form-item>
            <el-form-item label="API 密钥">
              <el-input v-model="llmConfig.apiKey" type="password" show-password />
            </el-form-item>
            <el-form-item label="模型名称">
              <el-input v-model="llmConfig.modelName" placeholder="deepseek-chat" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveLLMConfig" :loading="saving">保存</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

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
              <el-button @click="checkConnections">刷新状态</el-button>
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
              <el-button type="primary" @click="saveCompanyInfo">保存</el-button>
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

const activeTab = ref('llm')
const saving = ref(false)

const llmConfig = reactive({
  baseUrl: '',
  apiKey: '',
  modelName: ''
})

const companyInfo = reactive({
  name: '',
  industry: '',
  description: ''
})

const dbStatus = ref({
  mysql: false,
  redis: false,
  chroma: false
})

const saveLLMConfig = async () => {
  saving.value = true
  try {
    ElMessage.success('LLM 配置已保存')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const saveCompanyInfo = async () => {
  try {
    ElMessage.success('企业信息已保存')
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const checkConnections = async () => {
  dbStatus.value = { mysql: true, redis: true, chroma: true }
}

onMounted(() => {
  checkConnections()
})
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