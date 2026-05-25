<template>
  <el-aside width="220px" class="app-sidebar">
    <div class="sidebar-header">
      <el-icon class="logo-icon"><Monitor /></el-icon>
      <span class="logo-text">SmartHR</span>
    </div>
    <el-menu
      :default-active="activeMenu"
      router
      class="sidebar-menu"
    >
      <el-menu-item index="/">
        <el-icon><HomeFilled /></el-icon>
        <span>工作台</span>
      </el-menu-item>
      <el-menu-item index="/jobs">
        <el-icon><Briefcase /></el-icon>
        <span>岗位管理</span>
      </el-menu-item>
      <el-menu-item index="/resumes">
        <el-icon><Document /></el-icon>
        <span>简历管理</span>
      </el-menu-item>
      <el-menu-item index="/interview">
        <el-icon><ChatDotRound /></el-icon>
        <span>智能面试</span>
      </el-menu-item>
      <el-menu-item index="/knowledge">
        <el-icon><Collection /></el-icon>
        <span>知识库</span>
      </el-menu-item>
      <el-menu-item index="/config">
        <el-icon><Setting /></el-icon>
        <span>系统配置</span>
      </el-menu-item>
    </el-menu>
  </el-aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const activeMenu = computed(() => route.path)
</script>

<style scoped>
.app-sidebar {
  background: var(--bg-sidebar);
  height: 100vh;
  position: fixed;
  left: 0;
  top: 0;
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo-icon {
  font-size: 24px;
  color: #60a5fa;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: white;
  letter-spacing: 0.5px;
}

.sidebar-menu {
  border-right: none;
  background: transparent;
  margin-top: 8px;
}

:deep(.el-menu-item) {
  color: rgba(255, 255, 255, 0.85);
  margin: 4px 12px;
  border-radius: 8px;
  height: 44px;
  transition: all 0.2s ease;
}

:deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.15);
  color: white;
}

:deep(.el-menu-item.is-active) {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  font-weight: 600;
  border-left: 3px solid #60a5fa;
  margin-left: 9px;
}

:deep(.el-menu-item .el-icon) {
  color: inherit;
}
</style>