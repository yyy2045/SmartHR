<template>
  <AppLayout>
    <div class="page-header">
      <h2>智能面试</h2>
      <div class="header-actions">
        <el-button v-if="!sessionId" type="primary" @click="createSession">
          开始面试
        </el-button>
        <el-button v-else type="danger" @click="endInterview">
          结束面试
        </el-button>
      </div>
    </div>

    <el-row :gutter="20" class="interview-container">
      <el-col :span="16">
        <el-card class="chat-card">
          <template #header>
            <div class="chat-header">
              <span>面试会话</span>
              <el-tag v-if="sessionId" type="success">会话: {{ sessionId.slice(0, 8) }}</el-tag>
            </div>
          </template>

          <div ref="chatContainer" class="chat-messages">
            <div
              v-for="(msg, idx) in messages"
              :key="idx"
              :class="['message', msg.role]"
            >
              <div class="message-avatar">
                <el-avatar :size="36" :icon="msg.role === 'interviewer' ? 'User' : 'ChatDotRound'" />
              </div>
              <div class="message-content">
                <div class="message-text">{{ msg.content }}</div>
                <div class="message-time">{{ msg.timestamp }}</div>
              </div>
            </div>

            <div v-if="!messages.length && sessionId" class="empty-state">
              请回答第一个问题开始面试。
            </div>
          </div>

          <div class="chat-input">
            <el-input
              v-model="userAnswer"
              type="textarea"
              :rows="3"
              placeholder="请输入您的回答..."
              :disabled="!sessionId || isComplete"
              @keydown.ctrl.enter="sendAnswer"
            />
            <el-button
              type="primary"
              :disabled="!sessionId || isComplete"
              :loading="sending"
              @click="sendAnswer"
            >
              发送
            </el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card class="eval-card">
          <template #header>
            <span>评估面板</span>
          </template>

          <div class="eval-section">
            <h4>已问问题</h4>
            <el-progress :percentage="(questionsAsked / 10) * 100" :show-text="true" />
            <p class="eval-hint">{{ questionsAsked }} / 10 题</p>
          </div>

          <el-divider />

          <div class="eval-section">
            <h4>技能评分</h4>
            <div v-for="(score, skill) in skillScores" :key="skill" class="skill-item">
              <span>{{ skill }}</span>
              <el-progress :percentage="score" :show-text="false" style="width: 100px" />
              <span class="score-value">{{ score }}</span>
            </div>
            <p v-if="!Object.keys(skillScores).length" class="empty-hint">暂无评估数据</p>
          </div>

          <el-divider />

          <div class="eval-section">
            <h4>行为评分</h4>
            <div v-for="(score, behavior) in behaviorScores" :key="behavior" class="skill-item">
              <span>{{ behavior }}</span>
              <el-progress :percentage="score" :show-text="false" style="width: 100px" />
              <span class="score-value">{{ score }}</span>
            </div>
            <p v-if="!Object.keys(behaviorScores).length" class="empty-hint">暂无评估数据</p>
          </div>

          <el-button v-if="isComplete" type="success" class="report-btn" @click="viewReport">
            查看完整报告
          </el-button>
        </el-card>
      </el-col>
    </el-row>
  </AppLayout>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AppLayout from '@/components/common/AppLayout.vue'
import { createInterviewSession, sendInterviewMessage, endInterview as endInterviewApi, getInterviewSession, getInterviewReport } from '@/api/interview'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'

const router = useRouter()
const route = useRoute()

const sessionId = ref('')
const messages = ref([])
const userAnswer = ref('')
const questionsAsked = ref(0)
const skillScores = ref({})
const behaviorScores = ref({})
const isComplete = ref(false)
const sending = ref(false)
const chatContainer = ref()

const createSession = async () => {
  try {
    const res = await createInterviewSession({
      jobId: Number(route.query.jobId) || 1,
      resumeId: Number(route.query.resumeId) || 1,
      companyId: 1
    })
    if (!res || !res.sessionId) {
      ElMessage.error('创建面试会话失败：服务未返回会话 ID')
      return
    }
    sessionId.value = res.sessionId
    messages.value = []
    if (res.currentQuestion) {
      const questionText = typeof res.currentQuestion === 'string'
        ? res.currentQuestion
        : (res.currentQuestion.question || JSON.stringify(res.currentQuestion))
      messages.value.push({
        role: 'interviewer',
        content: questionText,
        timestamp: dayjs().format('HH:mm')
      })
    }
    ElMessage.success('面试已开始')
  } catch (error) {
    console.error('创建面试会话失败:', error)
    ElMessage.error('创建面试会话失败：' + (error?.response?.data?.message || error?.message || '未知错误'))
  }
}

const sendAnswer = async () => {
  if (!userAnswer.value.trim() || sending.value) return

  sending.value = true
  const answer = userAnswer.value
  userAnswer.value = ''

  messages.value.push({
    role: 'candidate',
    content: answer,
    timestamp: dayjs().format('HH:mm')
  })
  await scrollToBottom()

  try {
    const res = await sendInterviewMessage(sessionId.value, { message: answer })
    if (res && res.currentQuestion) {
      const questionText = typeof res.currentQuestion === 'string'
        ? res.currentQuestion
        : (res.currentQuestion.question || JSON.stringify(res.currentQuestion))
      messages.value.push({
        role: 'interviewer',
        content: questionText,
        timestamp: dayjs().format('HH:mm')
      })
      questionsAsked.value++
    }
    if (res?.skillScores) skillScores.value = res.skillScores
    if (res?.behaviorScores) behaviorScores.value = res.behaviorScores
    if (res?.complete || res?.isComplete) {
      isComplete.value = true
      ElMessage.success('面试已完成')
    }
  } catch (error) {
    ElMessage.error('发送回答失败')
  } finally {
    sending.value = false
    await scrollToBottom()
  }
}

const endInterview = async () => {
  try {
    await endInterviewApi(sessionId.value)
    isComplete.value = true
    ElMessage.success('面试已结束')
  } catch (error) {
    ElMessage.error('结束面试失败')
  }
}

const viewReport = async () => {
  try {
    await endInterviewApi(sessionId.value)
  } catch {}
  router.push(`/report/${sessionId.value}`)
}

const scrollToBottom = async () => {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

onMounted(async () => {
  if (route.params.sessionId) {
    sessionId.value = route.params.sessionId
    try {
      const res = await getInterviewSession(sessionId.value)
      messages.value = res.messages || []
      skillScores.value = res.skillScores || {}
      behaviorScores.value = res.behaviorScores || {}
      isComplete.value = res.isComplete || false
      questionsAsked.value = res.questionsAsked || 0
    } catch (error) {
      console.error('加载会话失败:', error)
    }
  }
})
</script>

<style scoped>
.interview-container {
  height: calc(100vh - 140px);
}

.chat-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  min-height: 400px;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.message.interviewer {
  flex-direction: row;
}

.message.candidate {
  flex-direction: row-reverse;
}

.message-text {
  background: #f5f7fa;
  padding: 12px 16px;
  border-radius: 8px;
  max-width: 70%;
}

.message.candidate .message-text {
  background: #409eff;
  color: white;
}

.message-time {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.chat-input {
  display: flex;
  gap: 10px;
  padding: 20px;
  border-top: 1px solid #e4e7ed;
}

.eval-card {
  height: 100%;
}

.eval-section {
  margin-bottom: 16px;
}

.eval-section h4 {
  margin-bottom: 12px;
  font-size: 14px;
  color: #606266;
}

.skill-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 13px;
}

.score-value {
  width: 30px;
  text-align: right;
  color: #409eff;
  font-weight: 600;
}

.empty-hint {
  color: #909399;
  font-size: 13px;
  font-style: italic;
}

.report-btn {
  width: 100%;
  margin-top: 20px;
}
</style>