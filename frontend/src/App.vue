<template>
<n-message-provider>
<n-dialog-provider>
  <div v-if="!isLoginRoute" class="layout">
    <!-- 移动端汉堡菜单 -->
    <div class="mobile-header">
      <button class="mobile-menu-btn" @click="sidebarOpen = !sidebarOpen">
        <n-icon size="22"><MenuOutline /></n-icon>
      </button>
      <span style="font-weight: 700;">yt-dlp Web</span>
    </div>

    <!-- 侧边栏遮罩 -->
    <div v-if="sidebarOpen" class="sidebar-overlay" @click="sidebarOpen = false" />

    <!-- 侧边栏 -->
    <aside class="sidebar" :class="{ open: sidebarOpen }">
      <div class="sidebar-logo">
        <n-icon size="24" color="var(--primary)"><VideocamOutline /></n-icon>
        <span>yt-dlp Web</span>
        <span class="version">v1.0</span>
      </div>

      <!-- 概览 -->
      <div class="nav-group">
        <div class="nav-group-title">概览</div>
        <router-link to="/" class="nav-item" :class="{ active: $route.path === '/' }" @click="sidebarOpen = false">
          <n-icon size="18" class="nav-icon"><GridOutline /></n-icon>仪表盘
        </router-link>
      </div>

      <!-- 下载管理 -->
      <div class="nav-group">
        <div class="nav-group-title">下载管理</div>
        <router-link to="/download" class="nav-item" :class="{ active: $route.path === '/download' }" @click="sidebarOpen = false">
          <n-icon size="18" class="nav-icon"><CloudDownloadOutline /></n-icon>新建下载
        </router-link>
        <router-link to="/tasks" class="nav-item" :class="{ active: $route.path === '/tasks' }" @click="sidebarOpen = false">
          <n-icon size="18" class="nav-icon"><ListOutline /></n-icon>任务队列
        </router-link>
        <router-link to="/history" class="nav-item" :class="{ active: $route.path === '/history' }" @click="sidebarOpen = false">
          <n-icon size="18" class="nav-icon"><TimeOutline /></n-icon>下载历史
        </router-link>
      </div>

      <!-- 订阅管理 -->
      <div class="nav-group">
        <div class="nav-group-title">订阅管理</div>
        <router-link to="/subscriptions" class="nav-item" :class="{ active: $route.path === '/subscriptions' }" @click="sidebarOpen = false">
          <n-icon size="18" class="nav-icon"><NotificationsOutline /></n-icon>我的订阅
        </router-link>
      </div>

      <!-- 系统 -->
      <div class="sidebar-bottom">
        <div class="nav-group-title">系统</div>
        <router-link to="/accounts" class="nav-item" :class="{ active: $route.path === '/accounts' }" @click="sidebarOpen = false">
          <n-icon size="18" class="nav-icon"><KeyOutline /></n-icon>账号管理
        </router-link>
        <router-link to="/settings" class="nav-item" :class="{ active: $route.path === '/settings' }" @click="sidebarOpen = false">
          <n-icon size="18" class="nav-icon"><SettingsOutline /></n-icon>系统设置
        </router-link>
      </div>
    </aside>

    <!-- 主内容 -->
    <main class="main-content">
      <router-view />
    </main>
  </div>

  <!-- 登录页全屏 -->
  <router-view v-else />
</n-dialog-provider>
</n-message-provider>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  MenuOutline,
  VideocamOutline,
  GridOutline,
  CloudDownloadOutline,
  ListOutline,
  TimeOutline,
  NotificationsOutline,
  KeyOutline,
  SettingsOutline,
} from '@vicons/ionicons5'

const route = useRoute()
const sidebarOpen = ref(false)
const isLoginRoute = computed(() => route.path === '/login' || route.path === '/setup')
</script>

<style scoped>
.sidebar-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.3);
  z-index: 99;
}

@media (min-width: 769px) {
  .sidebar-overlay { display: none; }
}
</style>
