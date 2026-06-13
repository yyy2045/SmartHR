<template>
  <AppLayout>
    <div class="page-header">
      <h2>面试报告</h2>
      <el-button type="primary" @click="exportPDF">
        <el-icon><Download /></el-icon> 导出 PDF
      </el-button>
    </div>

    <div ref="reportContent">
      <el-row :gutter="20">
        <el-col :span="8">
          <el-card class="score-card">
            <div class="overall-score">
              <el-progress
                type="circle"
                :percentage="reportData.overallScore || 0"
                :color="getScoreColor(reportData.overallScore)"
                :width="160"
              />
              <h3>综合评分</h3>
            </div>
            <div class="recommendation">
              <el-tag
                :type="getRecommendationType(reportData.recommendation)"
                size="large"
              >
                {{ reportData.recommendation || '待定' }}
              </el-tag>
            </div>
          </el-card>
        </el-col>

        <el-col :span="16">
          <el-card class="charts-card">
            <el-row :gutter="20">
              <el-col :span="12">
                <h4>技能评分</h4>
                <div ref="skillChartRef" style="width: 100%; height: 250px"></div>
              </el-col>
              <el-col :span="12">
                <h4>行为评分</h4>
                <div ref="behaviorChartRef" style="width: 100%; height: 250px"></div>
              </el-col>
            </el-row>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :span="12">
          <el-card>
            <template #header>
              <span>优势</span>
            </template>
            <ul class="strength-list">
              <li v-for="(strength, idx) in reportData.strengths" :key="idx">{{ strength }}</li>
            </ul>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card>
            <template #header>
              <span>顾虑</span>
            </template>
            <ul class="concern-list">
              <li v-for="(concern, idx) in reportData.concerns" :key="idx">{{ concern }}</li>
            </ul>
          </el-card>
        </el-col>
      </el-row>

      <el-card style="margin-top: 20px">
        <template #header>
          <span>风险点与证据来源</span>
        </template>
        <div class="risk-grid">
          <div>
            <h4>风险点</h4>
            <ul class="concern-list">
              <li v-for="(risk, idx) in reportData.risks" :key="idx">{{ risk }}</li>
            </ul>
            <p v-if="!reportData.risks.length" class="empty-hint">暂无风险点</p>
          </div>
          <div>
            <h4>结论证据</h4>
            <div v-if="reportData.conclusionEvidence.length" class="evidence-list">
              <div v-for="item in reportData.conclusionEvidence" :key="item.chunkId" class="evidence-item">
                <div class="evidence-head">
                  <el-tag size="small">{{ sourceTypeText(item.sourceType) }}</el-tag>
                  <strong>{{ item.title || item.sourceId || '未命名来源' }}</strong>
                </div>
                <p>{{ item.highlight || item.text }}</p>
              </div>
            </div>
            <p v-else class="empty-hint">暂无证据来源</p>
          </div>
        </div>
      </el-card>

      <el-card style="margin-top: 20px">
        <template #header>
          <span>问答摘要</span>
        </template>
        <el-collapse>
          <el-collapse-item
            v-for="(qa, idx) in reportData.qaSummary"
            :key="idx"
            :title="`Q${idx + 1}: ${qa.question}`"
          >
            <p><strong>A:</strong> {{ qa.answer }}</p>
            <p class="eval-note"><em>评估: {{ qa.evaluation }}</em></p>
            <div v-if="qa.basisEvidence && qa.basisEvidence.length" class="qa-evidence">
              <div v-for="item in qa.basisEvidence.slice(0, 3)" :key="item.chunkId" class="evidence-line">
                <el-tag size="small" effect="plain">{{ sourceTypeText(item.sourceType) }}</el-tag>
                <span>{{ item.title || item.sourceId }}</span>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>
      </el-card>

      <el-card v-if="reportData.followUpBasis.length" style="margin-top: 20px">
        <template #header>
          <span>追问依据</span>
        </template>
        <el-timeline>
          <el-timeline-item v-for="item in reportData.followUpBasis" :key="item.question">
            <p class="basis-question">{{ item.question }}</p>
            <div class="qa-evidence">
              <div v-for="evidence in (item.evidence || []).slice(0, 3)" :key="evidence.chunkId" class="evidence-line">
                <el-tag size="small" effect="plain">{{ sourceTypeText(evidence.sourceType) }}</el-tag>
                <span>{{ evidence.title || evidence.sourceId }}</span>
              </div>
            </div>
          </el-timeline-item>
        </el-timeline>
      </el-card>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from '@/components/common/AppLayout.vue'
import { getInterviewReport } from '@/api/interview'
import * as echarts from 'echarts'
import jsPDF from 'jspdf'
import html2canvas from 'html2canvas'
import { Download } from '@element-plus/icons-vue'

const route = useRoute()
const sessionId = route.params.sessionId

const reportContent = ref()
const skillChartRef = ref()
const behaviorChartRef = ref()

const reportData = ref({
  overallScore: 0,
  recommendation: '',
  skillScores: {},
  behaviorScores: {},
  strengths: [],
  concerns: [],
  risks: [],
  qaSummary: [],
  conclusionEvidence: [],
  followUpBasis: []
})

const getScoreColor = (score) => {
  if (score >= 80) return '#67c23a'
  if (score >= 60) return '#e6a23c'
  return '#f56c6c'
}

const getRecommendationType = (rec) => {
  if (rec === 'HIRE') return 'success'
  if (rec === 'NO_HIRE') return 'danger'
  return 'warning'
}

const sourceTypeText = (type) => {
  const map = {
    job: '岗位',
    resume: '简历',
    knowledge: '知识库',
    interview: '面试'
  }
  return map[type] || type || '证据'
}

const initCharts = () => {
  if (skillChartRef.value && Object.keys(reportData.value.skillScores).length) {
    const skillChart = echarts.init(skillChartRef.value)
    skillChart.setOption({
      radar: {
        indicator: Object.keys(reportData.value.skillScores).map(skill => ({
          name: skill,
          max: 100
        }))
      },
      series: [{
        type: 'radar',
        data: [{
          value: Object.values(reportData.value.skillScores),
          name: '技能'
        }]
      }]
    })
  }

  if (behaviorChartRef.value && Object.keys(reportData.value.behaviorScores).length) {
    const behaviorChart = echarts.init(behaviorChartRef.value)
    behaviorChart.setOption({
      grid: { left: '10%', right: '10%', bottom: '10%', containLabel: true },
      xAxis: { type: 'category', data: Object.keys(reportData.value.behaviorScores) },
      yAxis: { type: 'value', max: 100 },
      series: [{
        type: 'bar',
        data: Object.values(reportData.value.behaviorScores),
        itemStyle: { color: '#409eff' }
      }]
    })
  }
}

const exportPDF = async () => {
  if (!reportContent.value) return
  const canvas = await html2canvas(reportContent.value)
  const pdf = new jsPDF('p', 'mm', 'a4')
  pdf.addImage(canvas.toDataURL('PNG'), 'PNG', 10, 10, 190, 0)
  pdf.save(`interview-report-${sessionId}.pdf`)
}

const fetchReport = async () => {
  try {
    const res = await getInterviewReport(sessionId)
    reportData.value = {
      ...res,
      skillScores: res.skillScores || {},
      behaviorScores: res.behaviorScores || {},
      strengths: res.strengths || [],
      concerns: res.concerns || [],
      risks: res.risks || [],
      qaSummary: res.qaSummary || [],
      conclusionEvidence: res.conclusionEvidence || res.evidence || [],
      followUpBasis: res.followUpBasis || []
    }
    await nextTick()
    initCharts()
  } catch (error) {
    console.error('加载报告失败:', error)
  }
}

onMounted(fetchReport)
</script>

<style scoped>
.score-card {
  text-align: center;
}

.overall-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 20px;
}

.overall-score h3 {
  margin-top: 16px;
  font-weight: normal;
  color: #606266;
}

.recommendation {
  margin-top: 20px;
}

.strength-list, .concern-list {
  list-style: none;
  padding: 0;
}

.strength-list li, .concern-list li {
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.strength-list li:before {
  content: '+ ';
  color: #67c23a;
  font-weight: bold;
}

.concern-list li:before {
  content: '- ';
  color: #f56c6c;
  font-weight: bold;
}

.eval-note {
  margin-top: 8px;
  color: #909399;
}

.risk-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.2fr);
  gap: 20px;
}

.empty-hint {
  color: #909399;
  font-size: 13px;
}

.evidence-list {
  display: grid;
  gap: 10px;
}

.evidence-item {
  padding: 10px 12px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  background: #fafafa;
}

.evidence-head,
.evidence-line {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.evidence-head {
  margin-bottom: 6px;
}

.evidence-head strong,
.evidence-line span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.evidence-item p {
  margin: 0;
  color: #606266;
  font-size: 13px;
  line-height: 1.6;
}

.qa-evidence {
  display: grid;
  gap: 4px;
  margin-top: 8px;
}

.basis-question {
  margin: 0 0 8px;
  color: #303133;
}

@media (max-width: 860px) {
  .risk-grid {
    grid-template-columns: 1fr;
  }
}
</style>
