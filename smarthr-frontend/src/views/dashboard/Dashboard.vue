<template>
  <AppLayout>
    <div class="page-header">
      <h2>工作台</h2>
      <el-button type="primary" @click="quickActions">
        <el-icon><Plus /></el-icon> 快捷操作
      </el-button>
    </div>

    <div class="card-grid">
      <div class="stat-card">
        <div class="stat-label">岗位总数</div>
        <div class="stat-value">{{ stats.totalJobs }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">进行中的面试</div>
        <div class="stat-value">{{ stats.activeInterviews }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">本周新增简历</div>
        <div class="stat-value">{{ stats.resumesThisWeek }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">已生成报告</div>
        <div class="stat-value">{{ stats.reportsGenerated }}</div>
      </div>
    </div>

    <el-row :gutter="20">
      <el-col :span="12">
        <el-card class="recent-card">
          <template #header>
            <div class="card-header">
              <span>最近岗位</span>
              <el-button text type="primary" @click="$router.push('/jobs')">查看全部</el-button>
            </div>
          </template>
          <el-table :data="recentJobs" style="width: 100%">
            <el-table-column prop="title" label="岗位名称" />
            <el-table-column prop="department" label="部门" width="120" />
            <el-table-column prop="createdAt" label="发布时间" width="100" :formatter="formatDate" />
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card class="recent-card">
          <template #header>
            <div class="card-header">
              <span>面试安排</span>
              <el-button text type="primary" @click="$router.push('/interview')">查看全部</el-button>
            </div>
          </template>
          <el-table :data="upcomingInterviews" style="width: 100%">
            <el-table-column prop="candidateName" label="候选人" />
            <el-table-column prop="jobTitle" label="应聘岗位" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'IN_PROGRESS' ? 'success' : 'info'">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </AppLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/components/common/AppLayout.vue'
import { getJobs } from '@/api/job'
import { getInterviewSessions } from '@/api/interview'
import dayjs from 'dayjs'

const router = useRouter()

const stats = ref({
  totalJobs: 0,
  activeInterviews: 0,
  resumesThisWeek: 0,
  reportsGenerated: 0
})

const recentJobs = ref([])
const upcomingInterviews = ref([])

const formatDate = (row) => {
  return row.createdAt ? dayjs(row.createdAt).format('MM-DD') : '-'
}

const quickActions = () => {
  router.push('/jobs')
}

onMounted(async () => {
  try {
    const [jobsRes, interviewsRes] = await Promise.all([
      getJobs({ page: 0, size: 5 }),
      getInterviewSessions({ status: 'IN_PROGRESS' })
    ])

    recentJobs.value = jobsRes?.content || jobsRes || []
    upcomingInterviews.value = interviewsRes?.content || interviewsRes || []
    stats.value.totalJobs = jobsRes?.totalElements || recentJobs.value.length
    stats.value.activeInterviews = interviewsRes?.totalElements || upcomingInterviews.value.length
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  }
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.recent-card {
  margin-bottom: 20px;
}
</style>