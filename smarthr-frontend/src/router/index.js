import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/LoginRegister.vue'),
    meta: { guest: true }
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/dashboard/Dashboard.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/jobs',
    name: 'Jobs',
    component: () => import('@/views/job/JobManagement.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/resumes',
    name: 'Resumes',
    component: () => import('@/views/resume/ResumeManagement.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/interview/:sessionId?',
    name: 'Interview',
    component: () => import('@/views/interview/SmartInterview.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: () => import('@/views/knowledge/KnowledgeBase.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/report/:sessionId',
    name: 'Report',
    component: () => import('@/views/report/InterviewReport.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/config',
    name: 'Config',
    component: () => import('@/views/config/SystemConfig.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard for authentication
router.beforeEach((to, from, next) => {
  const user = localStorage.getItem('user')

  if (to.meta.requiresAuth && !user) {
    next('/login')
  } else if (to.meta.guest && user) {
    next('/')
  } else {
    next()
  }
})

export default router