<template>
  <el-aside width="200px" class="app-sidebar">
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
  background: white;
  border-right: 1px solid #e4e7ed;
  height: 100vh;
  position: fixed;
  left: 0;
  top: 0;
}

.sidebar-menu {
  border-right: none;
  height: 100%;
}
</style>