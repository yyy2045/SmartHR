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

      <el-tab-pane label="RAG评测" name="ragEvaluation">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>RAGas评测</span>
              <div class="header-buttons">
                <el-button size="small" @click="rebuildIndex" :loading="rebuilding">
                  重建索引
                </el-button>
                <el-button type="primary" size="small" @click="runEvaluation" :loading="evaluating">
                  运行评测
                </el-button>
              </div>
            </div>
          </template>

          <el-alert
            v-if="rebuildResult"
            class="evaluation-notes"
            :title="`索引重建完成：业务文档 ${rebuildResult.businessDocuments || 0} 条，知识库成功 ${rebuildResult.knowledgeIndexed || 0} 条，失败 ${rebuildResult.knowledgeFailed || 0} 条`"
            type="success"
            show-icon
            :closable="false"
          />

          <div class="evaluation-summary">
            <div class="summary-item">
              <span class="summary-label">状态</span>
              <el-tag :type="evaluationStatusType">{{ evaluationStatusText }}</el-tag>
            </div>
            <div class="summary-item">
              <span class="summary-label">评测器</span>
              <span>{{ ragEvaluation.evaluator || '-' }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">样本数</span>
              <span>{{ ragEvaluation.sampleCount || 0 }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">阈值</span>
              <span>{{ toPercent(ragEvaluation.threshold) }}%</span>
            </div>
          </div>

          <div class="metric-grid">
            <div v-for="metric in metricItems" :key="metric.key" class="metric-item">
              <div class="metric-head">
                <span>{{ metric.label }}</span>
                <strong>{{ toPercent(metric.value) }}%</strong>
              </div>
              <el-progress :percentage="toPercent(metric.value)" :show-text="false" />
            </div>
          </div>

          <el-alert
            v-if="ragEvaluation.notes"
            class="evaluation-notes"
            :title="ragEvaluation.notes"
            type="info"
            show-icon
            :closable="false"
          />

          <div v-if="failedSamples.length" class="failed-samples">
            <h4>未达标样本</h4>
            <div v-for="sample in failedSamples" :key="sample.question" class="failed-sample">
              <div class="failed-question">{{ sample.question }}</div>
              <div class="failed-reason">{{ sample.reason || '指标低于阈值' }}</div>
            </div>
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </AppLayout>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import AppLayout from '@/components/common/AppLayout.vue'
import { ElMessage } from 'element-plus'
import {
  checkDbStatus,
  getCompanyInfo,
  getRagEvaluation,
  rebuildRagIndex,
  runRagEvaluation,
  saveCompanyInfo as saveCompanyApi
} from '@/api/config'
import { getCurrentUser } from '@/api/auth'

const activeTab = ref('database')
const saving = ref(false)
const checking = ref(false)
const evaluating = ref(false)
const rebuilding = ref(false)
const rebuildResult = ref(null)

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

const ragEvaluation = ref({
  status: 'empty',
  evaluator: '',
  threshold: 0.7,
  sampleCount: 0,
  metrics: {},
  failedSamples: [],
  notes: ''
})

const metricLabels = {
  faithfulness: '忠实度',
  answerRelevancy: '答案相关性',
  contextPrecision: '上下文精确率',
  contextRecall: '上下文召回率'
}

const metricItems = computed(() => {
  const metrics = ragEvaluation.value.metrics || {}
  return Object.keys(metricLabels).map(key => ({
    key,
    label: metricLabels[key],
    value: Number(metrics[key] || 0)
  }))
})

const failedSamples = computed(() => ragEvaluation.value.failedSamples || [])

const evaluationStatusType = computed(() => {
  if (ragEvaluation.value.status === 'passed') return 'success'
  if (ragEvaluation.value.status === 'failed') return 'danger'
  return 'info'
})

const evaluationStatusText = computed(() => {
  const statusMap = {
    passed: '通过',
    failed: '未通过',
    empty: '暂无记录'
  }
  return statusMap[ragEvaluation.value.status] || ragEvaluation.value.status || '暂无记录'
})

const toPercent = value => {
  const number = Number(value || 0)
  if (Number.isNaN(number)) return 0
  return Math.max(0, Math.min(100, Math.round(number * 100)))
}

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

const loadRagEvaluation = async () => {
  try {
    const res = await getRagEvaluation()
    if (res) {
      ragEvaluation.value = {
        ...ragEvaluation.value,
        ...res,
        metrics: res.metrics || {},
        failedSamples: res.failedSamples || []
      }
    }
  } catch (error) {
    console.error('Failed to load rag evaluation:', error)
  }
}

const runEvaluation = async () => {
  evaluating.value = true
  try {
    const payload = {
      companyId: companyInfo.id ? String(companyInfo.id) : undefined,
      threshold: ragEvaluation.value.threshold || 0.7,
      topK: 5
    }
    const res = await runRagEvaluation(payload)
    ragEvaluation.value = {
      ...ragEvaluation.value,
      ...res,
      metrics: res.metrics || {},
      failedSamples: res.failedSamples || []
    }
    ElMessage.success('RAG评测已完成')
  } catch (error) {
    ElMessage.error('RAG评测失败: ' + (error.message || '未知错误'))
  } finally {
    evaluating.value = false
  }
}

const rebuildIndex = async () => {
  rebuilding.value = true
  try {
    const payload = {
      companyId: companyInfo.id ? String(companyInfo.id) : undefined
    }
    rebuildResult.value = await rebuildRagIndex(payload)
    ElMessage.success('RAG索引已重建')
  } catch (error) {
    ElMessage.error('RAG索引重建失败: ' + (error.message || '未知错误'))
  } finally {
    rebuilding.value = false
  }
}

onMounted(() => {
  checkConnections()
  loadCompanyInfo()
  loadRagEvaluation()
})

// 暴露方法给模板使用
const saveCompanyInfo = saveCompanyInfoHandler
</script>

<style scoped>
.config-tabs {
  max-width: 920px;
}

.db-info {
  margin-left: 12px;
  color: #909399;
  font-size: 13px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.header-buttons {
  display: flex;
  gap: 8px;
}

.evaluation-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.summary-item {
  min-height: 56px;
  padding: 10px 12px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  background: #fafafa;
}

.summary-label {
  display: block;
  margin-bottom: 6px;
  color: #909399;
  font-size: 12px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.metric-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  color: #303133;
  font-size: 13px;
}

.evaluation-notes {
  margin-top: 18px;
}

.failed-samples {
  margin-top: 20px;
}

.failed-samples h4 {
  margin: 0 0 10px;
  font-size: 14px;
  color: #303133;
}

.failed-sample {
  padding: 10px 12px;
  border: 1px solid #fde2e2;
  border-radius: 6px;
  background: #fef0f0;
}

.failed-sample + .failed-sample {
  margin-top: 8px;
}

.failed-question {
  color: #303133;
  font-size: 13px;
}

.failed-reason {
  margin-top: 4px;
  color: #c45656;
  font-size: 12px;
}

@media (max-width: 720px) {
  .evaluation-summary,
  .metric-grid {
    grid-template-columns: 1fr;
  }
}
</style>
