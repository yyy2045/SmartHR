<template>
  <AppLayout>
    <div class="page-content">
      <div class="page-header">
        <h2>简历管理</h2>
        <el-button type="primary" @click="showUploadDialog = true">
          <el-icon><Upload /></el-icon> 上传简历
        </el-button>
      </div>

      <el-card style="width: 100%">
        <el-table :data="resumes" v-loading="loading" style="width: 100%" table-layout="auto">
          <el-table-column type="index" label="#" width="60" />
          <el-table-column prop="candidateName" label="候选人" min-width="120" />
          <el-table-column prop="jobId" label="应聘岗位" min-width="120">
            <template #default="{ row }">
              <span v-if="getJobTitle(row.jobId)">{{ getJobTitle(row.jobId) }}</span>
              <span v-else-if="row.jobId">岗位 #{{ row.jobId }}</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column prop="matchScore" label="匹配度" min-width="120">
            <template #default="{ row }">
              <el-tag v-if="row.matchScore" :type="getMatchType(row.matchScore)">{{ row.matchScore }}%</el-tag>
              <el-tag v-else type="info">-</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" min-width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" size="small">{{ row.status || '未解析' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="createdAt" label="上传时间" min-width="150" :formatter="formatDate" />
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <div class="action-buttons">
                <el-button size="small" @click="viewMatch(row)">匹配</el-button>
                <el-button size="small" type="primary" @click="startInterview(row)">面试</el-button>
                <el-button size="small" type="danger" plain @click="removeResume(row)">删除</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-dialog v-model="showUploadDialog" title="上传简历" width="500px">
        <el-form ref="uploadFormRef" :model="uploadForm" label-width="100px">
          <el-form-item label="候选人姓名" prop="candidateName">
            <el-input v-model="uploadForm.candidateName" placeholder="请输入候选人姓名" />
          </el-form-item>
          <el-form-item label="应聘岗位" prop="jobId">
            <el-select v-model="uploadForm.jobId" placeholder="选择应聘岗位" style="width: 100%">
              <el-option label="暂不选择" :value="null" />
              <el-option v-for="job in jobOptions" :key="job.id" :label="job.title" :value="job.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="简历文件">
            <el-upload
              ref="uploadRef"
              drag
              :auto-upload="false"
              :limit="1"
              accept=".pdf,.doc,.docx"
              :on-change="handleFileChange"
            >
              <el-icon><UploadFilled /></el-icon>
              <div>将文件拖到此处，或<em>点击上传</em></div>
              <template #tip>
                <div class="el-upload__tip">支持 PDF、Word 格式，最大 5MB</div>
              </template>
            </el-upload>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showUploadDialog = false">取消</el-button>
          <el-button type="primary" @click="uploadResume" :loading="uploading">上传</el-button>
        </template>
      </el-dialog>

      <el-dialog v-model="showMatchDialog" title="匹配详情" width="600px">
        <div v-if="matchResult">
          <el-progress :percentage="Math.round(matchResult.matchScore || 0)" :color="getMatchColor(matchResult.matchScore)" />
          <el-divider />
          <h4>匹配要点</h4>
          <ul v-if="matchResult.matchingPoints && matchResult.matchingPoints.length">
            <li v-for="(point, idx) in matchResult.matchingPoints" :key="idx">
              <b>{{ point['技能'] || point.skill }}</b>
              <el-tag size="small" :type="getLevelType(point['等级'] || point.level)">{{ point['等级'] || point.level }}</el-tag>
              — {{ point['详情'] || point.details }}
            </li>
          </ul>
          <p v-else>暂无匹配要点</p>
          <h4>风险要点</h4>
          <ul v-if="matchResult.riskPoints && matchResult.riskPoints.length">
            <li v-for="(risk, idx) in matchResult.riskPoints" :key="idx">
              <b>{{ risk['技能'] || risk.skill }}</b>
              <el-tag size="small" :type="getLevelType(risk['等级'] || risk.level)">{{ risk['等级'] || risk.level }}</el-tag>
              — {{ risk['详情'] || risk.details }}
            </li>
          </ul>
          <p v-else>暂无风险要点</p>
        </div>
      </el-dialog>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/components/common/AppLayout.vue'
import { getResumes, uploadResume as apiUploadResume, matchResume, deleteResume as apiDeleteResume } from '@/api/resume'
import { getJobs } from '@/api/job'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, UploadFilled } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const authStore = useAuthStore()

const router = useRouter()
const loading = ref(false)
const resumes = ref([])
const jobOptions = ref([])
const jobMap = ref({})
const showUploadDialog = ref(false)
const showMatchDialog = ref(false)
const uploading = ref(false)
const uploadRef = ref()
const uploadFormRef = ref()
const selectedFile = ref(null)
const matchResult = ref(null)

const uploadForm = reactive({
  candidateName: '',
  jobId: null
})

const formatDate = (row) => row.createdAt ? dayjs(row.createdAt).format('YYYY-MM-DD') : '-'

const getMatchType = (score) => {
  if (!score) return 'info'
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
}

const getMatchColor = (score) => {
  if (score >= 80) return '#67c23a'
  if (score >= 60) return '#e6a23c'
  return '#f56c6c'
}

const getLevelType = (level) => {
  if (!level) return 'info'
  const l = String(level).toLowerCase()
  if (l === '高' || l === 'high') return 'danger'
  if (l === '中' || l === 'medium') return 'warning'
  return 'info'
}

const getStatusType = (status) => {
  if (status === 'PARSED') return 'success'
  if (status === 'MATCHED') return 'warning'
  return 'info'
}

const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

const uploadResume = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请选择文件')
    return
  }
  uploading.value = true
  try {
    const userCompanyId = authStore.user?.companyId || 1
    await apiUploadResume(selectedFile.value, uploadForm.jobId, uploadForm.candidateName, userCompanyId)
    ElMessage.success('简历上传成功')
    showUploadDialog.value = false
    uploadForm.candidateName = ''
    uploadForm.jobId = null
    selectedFile.value = null
    fetchResumes()
  } catch (error) {
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

const viewMatch = async (row) => {
  try {
    const res = await matchResume(row.id, row.jobId || 1)
    matchResult.value = res
    row.matchScore = Math.round(res.matchScore || 0)
    row.status = 'MATCHED'
    showMatchDialog.value = true
  } catch (error) {
    ElMessage.error('匹配失败')
  }
}

const formatPoint = (point) => {
  if (typeof point === 'string') return point
  if (point && typeof point === 'object') {
    return point.description || point.point || point.text || JSON.stringify(point)
  }
  return ''
}

const startInterview = (row) => {
  router.push(`/interview?resumeId=${row.id}&jobId=${row.jobId || 1}`)
}

const removeResume = async (row) => {
  try {
    await ElMessageBox.confirm(`删除此简历？`, '确认删除', { type: 'warning' })
    await apiDeleteResume(row.id)
    ElMessage.success('简历已删除')
    fetchResumes()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

const fetchResumes = async () => {
  loading.value = true
  try {
    const res = await getResumes({ page: 0, size: 20 })
    resumes.value = res?.content || res || []
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const fetchJobs = async () => {
  try {
    const res = await getJobs({ page: 0, size: 100 })
    jobOptions.value = res?.content || res || []
    // Build jobMap for quick lookup
    jobOptions.value.forEach(job => {
      jobMap.value[job.id] = job.title
    })
  } catch (error) {
    console.error(error)
  }
}

const getJobTitle = (jobId) => {
  return jobMap.value[jobId] || null
}

onMounted(() => {
  fetchResumes()
  fetchJobs()
})
</script>

<style scoped>
.page-content {
  width: 100%;
  box-sizing: border-box;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.action-buttons {
  display: flex;
  gap: 6px;
  flex-wrap: nowrap;
}
</style>