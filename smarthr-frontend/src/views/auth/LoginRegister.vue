<template>
  <div class="login-page">
    <div class="login-left">
      <div class="brand-content">
        <div class="brand-icon">
          <el-icon :size="48"><Monitor /></el-icon>
        </div>
        <h1 class="brand-title">SmartHR</h1>
        <p class="brand-subtitle">智能招聘平台</p>
        <div class="divider"></div>
        <p class="brand-desc">基于 AI 的多智能体协作招聘系统，<br/>助力企业高效选拔人才</p>
        <ul class="feature-list">
          <li><el-icon><Check /></el-icon> 智能简历匹配</li>
          <li><el-icon><Check /></el-icon> AI 面试评估</li>
          <li><el-icon><Check /></el-icon> 企业知识库</li>
          <li><el-icon><Check /></el-icon> 数据驱动决策</li>
        </ul>
      </div>
    </div>

    <div class="login-right">
      <div class="login-card">
        <h2 class="card-title">{{ activeTab === 'login' ? '欢迎回来' : '创建账号' }}</h2>
        <p class="card-tip">{{ activeTab === 'login' ? '请登录您的账号' : '开始免费使用' }}</p>

        <el-tabs v-model="activeTab" class="login-tabs">
          <el-tab-pane label="登录" name="login">
            <el-form
              ref="loginFormRef"
              :model="loginForm"
              :rules="loginRules"
              label-position="top"
              @submit.prevent="handleLogin"
            >
              <el-form-item prop="email">
                <el-input
                  v-model="loginForm.email"
                  placeholder="请输入邮箱"
                  :prefix-icon="Message"
                  size="large"
                />
              </el-form-item>
              <el-form-item prop="password">
                <el-input
                  v-model="loginForm.password"
                  type="password"
                  placeholder="请输入密码"
                  show-password
                  :prefix-icon="Lock"
                  @keyup.enter="handleLogin"
                  size="large"
                />
              </el-form-item>
              <el-button
                type="primary"
                :loading="loading"
                class="login-btn"
                native-type="submit"
                @click="handleLogin"
              >
                登录
              </el-button>
            </el-form>
          </el-tab-pane>

          <el-tab-pane label="注册" name="register">
            <el-form
              ref="registerFormRef"
              :model="registerForm"
              :rules="registerRules"
              label-position="top"
              @submit.prevent="handleRegister"
            >
              <el-form-item prop="name">
                <el-input v-model="registerForm.name" placeholder="请输入姓名" :prefix-icon="User" size="large" />
              </el-form-item>
              <el-form-item prop="email">
                <el-input v-model="registerForm.email" placeholder="请输入邮箱" :prefix-icon="Message" size="large" />
              </el-form-item>
              <el-form-item prop="password">
                <el-input
                  v-model="registerForm.password"
                  type="password"
                  placeholder="请输入密码"
                  show-password
                  :prefix-icon="Lock"
                  size="large"
                />
              </el-form-item>
              <el-form-item prop="companyName">
                <el-input v-model="registerForm.companyName" placeholder="请输入公司名称" :prefix-icon="OfficeBuilding" size="large" />
              </el-form-item>
              <el-button
                type="primary"
                :loading="loading"
                class="login-btn"
                native-type="submit"
                @click="handleRegister"
              >
                注册
              </el-button>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import { Message, Lock, User, OfficeBuilding, Monitor, Check } from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()

const activeTab = ref('login')
const loading = ref(false)
const loginFormRef = ref()
const registerFormRef = ref()

const loginForm = reactive({
  email: '',
  password: ''
})

const registerForm = reactive({
  name: '',
  email: '',
  password: '',
  companyName: ''
})

const loginRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

const registerRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6个字符', trigger: 'blur' }
  ],
  companyName: [{ required: true, message: '请输入公司名称', trigger: 'blur' }]
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        await authStore.login(loginForm.email, loginForm.password)
        ElMessage.success('登录成功')
        router.push('/')
      } catch (error) {
        // Error handled by interceptor
      } finally {
        loading.value = false
      }
    }
  })
}

const handleRegister = async () => {
  if (!registerFormRef.value) return
  await registerFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        await authStore.register({
          name: registerForm.name,
          email: registerForm.email,
          password: registerForm.password,
          role: 'HR',
          companyName: registerForm.companyName
        })
        ElMessage.success('注册成功')
        router.push('/')
      } catch (error) {
        // Error handled by interceptor
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
}

.login-left {
  flex: 1;
  background: linear-gradient(135deg, #1e3a5f 0%, #3b82f6 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.login-left::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(255,255,255,0.08) 0%, transparent 50%);
  animation: float 15s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(2%, 2%); }
}

.brand-content {
  color: white;
  text-align: center;
  padding: 40px;
  position: relative;
  z-index: 10;
}

.brand-icon {
  width: 80px;
  height: 80px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24px;
  color: #60a5fa;
}

.brand-title {
  font-size: 42px;
  font-weight: 700;
  margin-bottom: 8px;
  letter-spacing: 2px;
}

.brand-subtitle {
  font-size: 18px;
  opacity: 0.9;
  margin-bottom: 32px;
}

.divider {
  width: 60px;
  height: 3px;
  background: #60a5fa;
  margin: 0 auto 32px;
  border-radius: 2px;
}

.brand-desc {
  font-size: 16px;
  line-height: 1.8;
  opacity: 0.85;
  margin-bottom: 32px;
}

.feature-list {
  list-style: none;
  padding: 0;
  text-align: left;
  display: inline-block;
}

.feature-list li {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  font-size: 15px;
  opacity: 0.9;
}

.feature-list .el-icon {
  color: #60a5fa;
  font-size: 18px;
}

.login-right {
  width: 480px;
  background: #fffbf0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.login-card {
  width: 100%;
  max-width: 360px;
}

.card-title {
  font-size: 28px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 8px;
}

.card-tip {
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 32px;
}

.login-tabs {
  margin-bottom: 24px;
}

:deep(.el-tabs__item) {
  font-size: 16px;
  font-weight: 500;
  color: #9ca3af;
}

:deep(.el-tabs__item.is-active) {
  color: var(--primary-color);
}

:deep(.el-tabs__active-bar) {
  background-color: var(--primary-color);
}

:deep(.el-input__wrapper) {
  border-radius: var(--radius-md);
  box-shadow: 0 0 0 1px #e5e7eb inset;
}

:deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #d1d5db inset;
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--primary-color) inset;
}

:deep(.el-button--primary) {
  background: var(--primary-color);
  border-color: var(--primary-color);
  border-radius: var(--radius-md);
  height: 44px;
  font-size: 16px;
  font-weight: 600;
  transition: all 0.3s ease;
  margin-top: 8px;
}

:deep(.el-button--primary:hover) {
  background: var(--primary-dark);
  border-color: var(--primary-dark);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
}
</style>