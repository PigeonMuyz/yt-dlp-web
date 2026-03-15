<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">仪表盘</h1>
      <p class="page-subtitle">系统概览</p>
    </div>

    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-value">{{ stats.subscriptions || 0 }}</div>
        <div class="stat-label">订阅数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.downloading || 0 }}</div>
        <div class="stat-label">下载中</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.completed || 0 }}</div>
        <div class="stat-label">已完成</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.failed || 0 }}</div>
        <div class="stat-label">失败</div>
      </div>
    </div>

    <div class="card">
      <h3 style="margin-bottom: 16px;">最近下载</h3>
      <n-data-table :columns="columns" :data="recentTasks" :bordered="false" size="small" />
    </div>

    <div class="card">
      <h3 style="margin-bottom: 16px;">系统状态</h3>
      <n-descriptions :column="2" label-placement="left" size="small">
        <n-descriptions-item label="数据库">
          <n-tag :type="status.database ? 'success' : 'error'" size="small">
            {{ status.database ? '已连接' : '未连接' }}
          </n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="Redis">
          <n-tag :type="status.redis ? 'success' : 'error'" size="small">
            {{ status.redis ? '已连接' : '未连接' }}
          </n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="版本">{{ status.version }}</n-descriptions-item>
      </n-descriptions>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, h } from 'vue'
import { NTag } from 'naive-ui'
import axios from 'axios'

const stats = ref({})
const status = ref({ database: false, redis: false, version: '' })
const recentTasks = ref([])

const statusMap = {
  pending: { label: '等待', type: 'default' },
  downloading: { label: '下载中', type: 'info' },
  completed: { label: '完成', type: 'success' },
  failed: { label: '失败', type: 'error' },
}

const columns = [
  { title: '标题', key: 'title', ellipsis: { tooltip: true } },
  { title: '平台', key: 'platform', width: 80 },
  {
    title: '状态', key: 'status', width: 80,
    render: (row) => h(NTag, { type: statusMap[row.status]?.type || 'default', size: 'small' },
      () => statusMap[row.status]?.label || row.status)
  },
  { title: '编码', key: 'codec', width: 80 },
  { title: '时间', key: 'created_at', width: 160 },
]

onMounted(async () => {
  try {
    const [statusRes, statsRes, tasksRes] = await Promise.all([
      axios.get('/api/status'),
      axios.get('/api/task/stats'),
      axios.get('/api/task/list?limit=10'),
    ])
    status.value = statusRes.data
    stats.value = statsRes.data
    recentTasks.value = tasksRes.data
  } catch (e) {
    console.error(e)
  }
})
</script>
