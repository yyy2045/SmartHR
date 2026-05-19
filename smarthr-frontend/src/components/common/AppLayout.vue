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
  margin-left: 200px;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  width: calc(100% - 200px);
  max-width: 100%;
}

.content-main {
  flex: 1;
  padding: 20px;
  background: #f5f7fa;
  width: 100%;
  box-sizing: border-box;
}

.content-main :deep(.el-card) {
  width: 100%;
}

.content-main :deep(.el-table) {
  width: 100% !important;
}
</style>