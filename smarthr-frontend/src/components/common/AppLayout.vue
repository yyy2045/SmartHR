<template>
  <div class="app-wrapper">
    <AppSidebar />
    <div class="main-wrapper">
      <AppHeader />
      <el-main class="content-main">
        <slot />
      </el-main>
    </div>
  </div>
</template>

<script setup>
import AppHeader from '@/components/common/AppHeader.vue'
import AppSidebar from '@/components/common/AppSidebar.vue'
</script>

<style scoped>
.app-wrapper {
  display: flex;
  min-height: 100vh;
  width: 100%;
  overflow-x: hidden;
}

.main-wrapper {
  flex: 1;
  margin-left: var(--sidebar-width);
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  width: calc(100% - var(--sidebar-width));
  max-width: 100%;
}

.content-main {
  flex: 1;
  padding: 24px;
  background: var(--bg-page);
  width: 100%;
  box-sizing: border-box;
}

.content-main :deep(.el-card) {
  width: 100%;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: none;
}

.content-main :deep(.el-table) {
  width: 100% !important;
}

.content-main :deep(.el-table__header th) {
  background: #f9fafb;
  color: #374151;
  font-weight: 600;
}
</style>