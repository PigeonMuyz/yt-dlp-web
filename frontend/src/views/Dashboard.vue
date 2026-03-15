<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">仪表盘</h1>
      <p class="page-subtitle">欢迎回来！这是您的下载概览。</p>
    </div>

    <!-- 统计卡片 -->
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-icon teal">🔔</div>
        <div class="stat-content">
          <div class="stat-label">活跃订阅</div>
          <div class="stat-value">{{ stats.subscriptions }}</div>
          <div class="stat-sub">个频道</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon blue">⬇️</div>
        <div class="stat-content">
          <div class="stat-label">下载中</div>
          <div class="stat-value">{{ stats.downloading }}</div>
          <div class="stat-sub">个任务</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon green">✅</div>
        <div class="stat-content">
          <div class="stat-label">已完成</div>
          <div class="stat-value">{{ stats.completed }}</div>
          <div class="stat-sub">个视频</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon red">❌</div>
        <div class="stat-content">
          <div class="stat-label">失败</div>
          <div class="stat-value">{{ stats.failed }}</div>
          <div class="stat-sub">个任务</div>
        </div>
      </div>
    </div>

    <!-- 系统状态 -->
    <div class="card">
      <div class="card-title">系统状态</div>
      <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px;">
        <div class="account-card" style="margin: 0;">
          <div class="stat-icon" :class="status.database ? 'green' : 'red'" style="width: 36px; height: 36px; font-size: 16px;">
            {{ status.database ? '✅' : '❌' }}
          </div>
          <div class="account-info">
            <div class="account-name">PostgreSQL</div>
            <div class="account-meta">{{ status.database ? '已连接' : '未连接' }}</div>
          </div>
        </div>
        <div class="account-card" style="margin: 0;">
          <div class="stat-icon" :class="status.redis ? 'green' : 'red'" style="width: 36px; height: 36px; font-size: 16px;">
            {{ status.redis ? '✅' : '❌' }}
          </div>
          <div class="account-info">
            <div class="account-name">Redis</div>
            <div class="account-meta">{{ status.redis ? '已连接' : '未连接' }}</div>
          </div>
        </div>
        <div class="account-card" style="margin: 0;">
          <div class="stat-icon teal" style="width: 36px; height: 36px; font-size: 16px;">📦</div>
          <div class="account-info">
            <div class="account-name">版本</div>
            <div class="account-meta">{{ status.version || 'v1.0.0' }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 快捷操作 -->
    <div class="card">
      <div class="card-title">快捷操作</div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
        <div class="account-card" style="cursor: pointer;" @click="$router.push('/download')">
          <div class="stat-icon blue" style="width: 36px; height: 36px; font-size: 16px;">⬇️</div>
          <div class="account-info">
            <div class="account-name">新建下载</div>
            <div class="account-meta">输入视频链接快速下载</div>
          </div>
          <span style="color: var(--text-muted);">›</span>
        </div>
        <div class="account-card" style="cursor: pointer;" @click="$router.push('/accounts')">
          <div class="stat-icon orange" style="width: 36px; height: 36px; font-size: 16px;">🔑</div>
          <div class="account-info">
            <div class="account-name">账号管理</div>
            <div class="account-meta">绑定 B站 / YouTube 账号</div>
          </div>
          <span style="color: var(--text-muted);">›</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const status = ref({ database: false, redis: false, version: '' })
const stats = ref({ subscriptions: 0, downloading: 0, completed: 0, failed: 0 })

onMounted(async () => {
  try {
    const [statusRes, taskRes] = await Promise.all([
      axios.get('/api/status'),
      axios.get('/api/task/stats').catch(() => ({ data: {} })),
    ])
    status.value = statusRes.data
    if (taskRes.data) {
      stats.value = {
        subscriptions: taskRes.data.subscriptions || 0,
        downloading: taskRes.data.downloading || 0,
        completed: taskRes.data.completed || 0,
        failed: taskRes.data.failed || 0,
      }
    }
  } catch (e) {
    console.error(e)
  }
})
</script>
