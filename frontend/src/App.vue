<template>
  <n-config-provider :theme="darkTheme" :locale="zhCN" :date-locale="dateZhCN">
    <n-message-provider>
      <n-dialog-provider>
        <router-view v-if="$route.name === 'Setup' || $route.name === 'Login'" />
        <div v-else class="layout">
          <aside class="sidebar">
            <div class="sidebar-logo">📺 yt-dlp Web</div>
            <nav class="sidebar-nav">
              <router-link to="/" class="nav-item" :class="{ active: $route.path === '/' }">
                <span class="nav-icon">📊</span> 仪表盘
              </router-link>
              <router-link to="/download" class="nav-item" :class="{ active: $route.path === '/download' }">
                <span class="nav-icon">⬇️</span> 下载
              </router-link>
              <router-link to="/subscriptions" class="nav-item" :class="{ active: $route.path === '/subscriptions' }">
                <span class="nav-icon">🔔</span> 订阅
              </router-link>
              <router-link to="/tasks" class="nav-item" :class="{ active: $route.path === '/tasks' }">
                <span class="nav-icon">📋</span> 任务队列
              </router-link>
              <router-link to="/settings" class="nav-item" :class="{ active: $route.path === '/settings' }">
                <span class="nav-icon">⚙️</span> 设置
              </router-link>
            </nav>
          </aside>
          <main class="main-content">
            <router-view />
          </main>
        </div>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup>
import { darkTheme } from 'naive-ui'
import { zhCN, dateZhCN } from 'naive-ui'
</script>
