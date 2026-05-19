<template>
  <AppLayout>
    <div class="page-header">
      <h2>岗位管理</h2>
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon> 创建岗位
      </el-button>
    </div>

    <el-card>
      <el-table :data="jobs" v-loading="loading" style="width: 100%" :scrollable="true">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="title" label="岗位名称" min-width="150" />
        <el-table-column prop="department" label="部门" width="120" />
        <el-table-column prop="requirements" label="岗位要求" min-width="200" show-overflow-tooltip />
        <el-table-column prop="experienceYears" label="经验要求" width="100" />
        <el-table-column prop="educationLevel" label="学历要求" width="100" />
        <el-table-column prop="skills" label="技能要求" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.skills">{{ formatSkills(row.skills) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'OPEN' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="100" :formatter="formatDate" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" @click="viewJob(row)">查看</el-button>
              <el-button size="small" type="primary" @click="editJob(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="deleteJob(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.size"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="fetchJobs"
        @current-change="fetchJobs"
        style="margin-top: 20px; justify-content: center"
      />
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="700px" @close="resetForm">
      <el-form ref="formRef" :model="jobForm" :rules="jobRules" label-width="100px">
        <el-form-item label="岗位名称" prop="title">
          <el-input v-model="jobForm.title" placeholder="岗位名称" />
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="jobForm.department" placeholder="所属部门" />
        </el-form-item>
        <el-form-item label="岗位要求" prop="requirements">
          <el-input v-model="jobForm.requirements" type="textarea" :rows="3" placeholder="岗位具体要求" />
        </el-form-item>
        <el-form-item label="岗位描述" prop="description">
          <el-input v-model="jobForm.description" type="textarea" :rows="3" placeholder="岗位描述" />
        </el-form-item>
        <el-form-item label="经验要求">
          <el-input-number v-model="jobForm.experienceYears" :min="0" :max="30" /> 年
        </el-form-item>
        <el-form-item label="学历要求">
          <el-select v-model="jobForm.educationLevel" placeholder="选择学历要求" style="width: 100%">
            <el-option label="不限" value="" />
            <el-option label="大专" value="大专" />
            <el-option label="本科" value="本科" />
            <el-option label="硕士" value="硕士" />
            <el-option label="博士" value="博士" />
          </el-select>
        </el-form-item>
        <el-form-item label="技能标签">
          <el-tag v-for="tag in jobForm.tags" :key="tag" closable @close="removeTag(tag)" style="margin-right: 8px">
            {{ tag }}
          </el-tag>
          <el-button v-if="isEdit" size="small" @click="extractTags" :loading="extracting">AI 提取标签</el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>
  </AppLayout>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import AppLayout from '@/components/common/AppLayout.vue'
import { getJobs, createJob, updateJob, deleteJob as apiDeleteJob, extractJobTags } from '@/api/job'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const loading = ref(false)
const jobs = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('创建岗位')
const isEdit = ref(false)
const submitting = ref(false)
const extracting = ref(false)
const formRef = ref()
const editorRef = ref()

const pagination = reactive({
  page: 1,
  size: 10,
  total: 0
})

const jobForm = reactive({
  id: null,
  title: '',
  department: '',
  requirements: '',
  description: '',
  experienceYears: 0,
  educationLevel: '',
  tags: [],
  status: 'OPEN'
})

const jobRules = {
  title: [{ required: true, message: '请输入岗位名称', trigger: 'blur' }],
  requirements: [{ required: true, message: '请输入岗位要求', trigger: 'blur' }]
}

const formatDate = (row) => row.createdAt ? dayjs(row.createdAt).format('YYYY-MM-DD') : '-'

const formatSkills = (skills) => {
  if (!skills) return '-'
  try {
    const arr = JSON.parse(skills)
    return arr.join(', ')
  } catch {
    return skills
  }
}

const fetchJobs = async () => {
  loading.value = true
  try {
    const res = await getJobs({ page: pagination.page - 1, size: pagination.size })
    jobs.value = res?.content || res || []
    pagination.total = res?.totalElements || jobs.value.length
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  dialogTitle.value = '创建岗位'
  isEdit.value = false
  dialogVisible.value = true
}

const editJob = (row) => {
  dialogTitle.value = '编辑岗位'
  isEdit.value = true
  jobForm.id = row.id
  jobForm.title = row.title
  jobForm.department = row.department || ''
  jobForm.requirements = row.requirements || ''
  jobForm.description = row.description || ''
  jobForm.experienceYears = row.experienceYears || 0
  jobForm.educationLevel = row.educationLevel || ''
  jobForm.tags = row.skills ? formatSkillsArray(row.skills) : []
  jobForm.status = row.status || 'OPEN'
  dialogVisible.value = true
}

const viewJob = (row) => editJob(row)

const formatSkillsArray = (skills) => {
  if (!skills) return []
  try {
    return JSON.parse(skills)
  } catch {
    return []
  }
}

const deleteJob = async (row) => {
  try {
    await ElMessageBox.confirm(`删除岗位"${row.title}"？`, '确认删除', { type: 'warning' })
    await apiDeleteJob(row.id)
    ElMessage.success('岗位已删除')
    fetchJobs()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

const removeTag = (tag) => {
  jobForm.tags = jobForm.tags.filter(t => t !== tag)
}

const extractTags = async () => {
  if (!jobForm.requirements && !jobForm.description) {
    ElMessage.warning('请先输入岗位要求或描述')
    return
  }
  extracting.value = true
  try {
    const res = await extractJobTags(jobForm.id)
    if (res && res.tags) {
      jobForm.tags = res.tags
      ElMessage.success('标签已提取')
    }
  } catch (error) {
    ElMessage.error('标签提取失败')
  } finally {
    extracting.value = false
  }
}

const resetForm = () => {
  jobForm.id = null
  jobForm.title = ''
  jobForm.department = ''
  jobForm.requirements = ''
  jobForm.description = ''
  jobForm.experienceYears = 0
  jobForm.educationLevel = ''
  jobForm.tags = []
  jobForm.status = 'OPEN'
}

const submitForm = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        const data = {
          title: jobForm.title,
          department: jobForm.department,
          requirements: jobForm.requirements,
          description: jobForm.description,
          experienceYears: jobForm.experienceYears,
          educationLevel: jobForm.educationLevel,
          skills: JSON.stringify(jobForm.tags),
          status: jobForm.status
        }
        if (isEdit.value) {
          await updateJob(jobForm.id, data)
          ElMessage.success('岗位已更新')
        } else {
          const res = await createJob(data)
          // 保存后自动提取标签
          const newId = res?.id || jobForm.id
          if (newId && (jobForm.requirements || jobForm.description)) {
            extracting.value = true
            try {
              const tagRes = await extractJobTags(newId)
              if (tagRes?.tags?.length) {
                jobForm.tags = tagRes.tags
                await updateJob(newId, { ...data, skills: JSON.stringify(tagRes.tags) })
              }
            } catch {}
            extracting.value = false
          }
          ElMessage.success('岗位已创建')
        }
        dialogVisible.value = false
        fetchJobs()
      } catch (error) {
        // Error handled by interceptor
      } finally {
        submitting.value = false
      }
    }
  })
}

onMounted(fetchJobs)
</script>

<style scoped>
.action-buttons {
  display: flex;
  gap: 4px;
  flex-wrap: nowrap;
}
</style>