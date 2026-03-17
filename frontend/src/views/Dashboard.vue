<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">仪表盘</h1>
      <p class="page-subtitle">欢迎回来！这是您的下载概览。</p>
    </div>

    <!-- 统计卡片 -->
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-icon teal">
          <n-icon size="22"><NotificationsOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">活跃订阅</div>
          <div class="stat-value">{{ stats.subscriptions }}</div>
          <div class="stat-sub">个频道</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon blue">
          <n-icon size="22"><CloudDownloadOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">下载中</div>
          <div class="stat-value">{{ stats.downloading }}</div>
          <div class="stat-sub">个任务</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon green">
          <n-icon size="22"><CheckmarkCircleOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">已完成</div>
          <div class="stat-value">{{ stats.completed }}</div>
          <div class="stat-sub">个视频</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon orange">
          <n-icon size="22"><TodayOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">今日下载</div>
          <div class="stat-value">{{ stats.today }}</div>
          <div class="stat-sub">个视频</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon red">
          <n-icon size="22"><CloseCircleOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">失败</div>
          <div class="stat-value">{{ stats.failed }}</div>
          <div class="stat-sub">个任务</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon purple">
          <n-icon size="22"><ServerOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">存储占用</div>
          <div class="stat-value">{{ formatSize(stats.storage_bytes) }}</div>
          <div class="stat-sub">{{ stats.pending || 0 }} 个等待中</div>
        </div>
      </div>
    </div>

    <!-- 7天趋势 -->
    <div class="card" v-if="stats.trend && stats.trend.length">
      <div class="card-title">7 天下载趋势</div>
      <div class="trend-chart">
        <div v-for="d in stats.trend" :key="d.date" class="trend-bar-wrap">
          <div class="trend-count">{{ d.count }}</div>
          <div class="trend-bar" :style="{ height: barHeight(d.count) + 'px' }"></div>
          <div class="trend-date">{{ d.date }}</div>
        </div>
      </div>
    </div>

    <!-- 系统状态 -->
    <div class="card">
      <div class="card-title">系统状态</div>
      <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px;">
        <div class="account-card" style="margin: 0;">
          <div class="stat-icon" :class="status.database ? 'green' : 'red'" style="width: 36px; height: 36px;">
            <n-icon size="18"><ServerOutline /></n-icon>
          </div>
          <div class="account-info">
            <div class="account-name">PostgreSQL</div>
            <div class="account-meta">{{ status.database ? '已连接' : '未连接' }}</div>
          </div>
        </div>
        <div class="account-card" style="margin: 0;">
          <div class="stat-icon" :class="status.redis ? 'green' : 'red'" style="width: 36px; height: 36px;">
            <n-icon size="18"><FlashOutline /></n-icon>
          </div>
          <div class="account-info">
            <div class="account-name">Redis</div>
            <div class="account-meta">{{ status.redis ? '已连接' : '未连接' }}</div>
          </div>
        </div>
        <div class="account-card" style="margin: 0;">
          <div class="stat-icon teal" style="width: 36px; height: 36px;">
            <n-icon size="18"><InformationCircleOutline /></n-icon>
          </div>
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
          <div class="stat-icon blue" style="width: 36px; height: 36px;">
            <n-icon size="18"><CloudDownloadOutline /></n-icon>
          </div>
          <div class="account-info">
            <div class="account-name">新建下载</div>
            <div class="account-meta">输入视频链接快速下载</div>
          </div>
          <n-icon size="16" color="var(--text-muted)"><ChevronForwardOutline /></n-icon>
        </div>
        <div class="account-card" style="cursor: pointer;" @click="$router.push('/accounts')">
          <div class="stat-icon orange" style="width: 36px; height: 36px;">
            <n-icon size="18"><KeyOutline /></n-icon>
          </div>
          <div class="account-info">
            <div class="account-name">账号管理</div>
            <div class="account-meta">绑定 B站 / YouTube 账号</div>
          </div>
          <n-icon size="16" color="var(--text-muted)"><ChevronForwardOutline /></n-icon>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import {
  NotificationsOutline,
  CloudDownloadOutline,
  CheckmarkCircleOutline,
  CloseCircleOutline,
  ServerOutline,
  FlashOutline,
  InformationCircleOutline,
  KeyOutline,
  ChevronForwardOutline,
  TodayOutline,
} from '@vicons/ionicons5'

const status = ref({ database: false, redis: false, version: '' })
const stats = ref({ subscriptions: 0, downloading: 0, completed: 0, failed: 0, today: 0, storage_bytes: 0, pending: 0, trend: [] })

function formatSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  let val = bytes
  while (val >= 1024 && i < units.length - 1) { val /= 1024; i++ }
  return val.toFixed(i > 0 ? 1 : 0) + ' ' + units[i]
}

function barHeight(count) {
  const max = Math.max(...stats.value.trend.map(d => d.count), 1)
  return Math.max(4, (count / max) * 80)
}

onMounted(async () => {
  try {
    const [statusRes, taskRes] = await Promise.all([
      axios.get('/api/status'),
      axios.get('/api/task/stats').catch(() => ({ data: {} })),
    ])
    status.value = statusRes.data
    if (taskRes.data) {
      stats.value = { ...stats.value, ...taskRes.data }
    }
  } catch (e) {
    console.error(e)
  }
})
</script>

<style scoped>
.trend-chart {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  height: 120px;
  padding: 8px 0;
}
.trend-bar-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.trend-bar {
  width: 100%;
  max-width: 48px;
  background: linear-gradient(180deg, var(--accent-color), var(--accent-hover));
  border-radius: 4px 4px 0 0;
  min-height: 4px;
  transition: height 0.3s ease;
}
.trend-count {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
}
.trend-date {
  font-size: 11px;
  color: var(--text-muted);
}
.stat-icon.purple {
  background: rgba(168, 85, 247, 0.15);
  color: #a855f7;
}
.stat-icon.orange {
  background: rgba(249, 115, 22, 0.15);
  color: #f97316;
}
@media (max-width: 480px) {
  .trend-chart { gap: 4px; }
  .trend-bar { max-width: 32px; }
}
</style>
