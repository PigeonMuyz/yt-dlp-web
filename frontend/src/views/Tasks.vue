<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">任务队列</h1>
      <p class="page-subtitle">下载任务管理</p>
    </div>

    <div class="stat-grid">
      <div class="stat-card" v-for="(count, status) in stats" :key="status">
        <div class="stat-value">{{ count }}</div>
        <div class="stat-label">{{ statusLabels[status] || status }}</div>
      </div>
    </div>

    <div class="card">
      <div style="display:flex;gap:8px;margin-bottom:16px;">
        <n-button v-for="f in filters" :key="f.value" :type="filter===f.value?'primary':'default'" size="small" @click="filter=f.value;loadTasks()">
          {{ f.label }}
        </n-button>
      </div>

      <n-data-table :columns="columns" :data="tasks" :bordered="false" size="small" />

      <div style="text-align: center; margin-top: 16px;" v-if="tasks.length >= 50">
        <n-button size="small" @click="loadMore">加载更多</n-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, h } from 'vue'
import { NTag, NButton, NProgress, useMessage } from 'naive-ui'
import axios from 'axios'

const message = useMessage()
const tasks = ref([])
const stats = ref({})
const filter = ref('')
const offset = ref(0)

const statusLabels = {
  pending: '等待中',
  downloading: '下载中',
  processing: '处理中',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消',
}

const filters = [
  { label: '全部', value: '' },
  { label: '下载中', value: 'downloading' },
  { label: '等待', value: 'pending' },
  { label: '完成', value: 'completed' },
  { label: '失败', value: 'failed' },
]

const statusTypeMap = {
  pending: 'default',
  downloading: 'info',
  processing: 'info',
  completed: 'success',
  failed: 'error',
  cancelled: 'warning',
}

const columns = [
  { title: '标题', key: 'title', ellipsis: { tooltip: true }, minWidth: 200 },
  { title: '平台', key: 'platform', width: 70 },
  { title: '编码', key: 'codec', width: 70 },
  {
    title: '状态', key: 'status', width: 80,
    render: (row) => h(NTag, { type: statusTypeMap[row.status], size: 'small' }, () => statusLabels[row.status] || row.status)
  },
  {
    title: '进度', key: 'progress', width: 80,
    render: (row) => row.status === 'downloading' ? h(NProgress, { type: 'line', percentage: row.progress, height: 6 }) : ''
  },
  {
    title: '操作', key: 'actions', width: 100,
    render: (row) => {
      const btns = []
      if (row.status === 'failed') btns.push(h(NButton, { size: 'tiny', onClick: () => retry(row.id) }, () => '重试'))
      if (row.status === 'pending') btns.push(h(NButton, { size: 'tiny', onClick: () => cancel(row.id) }, () => '取消'))
      btns.push(h(NButton, { size: 'tiny', type: 'error', onClick: () => remove(row.id) }, () => '删除'))
      return h('div', { style: 'display:flex;gap:4px' }, btns)
    }
  },
]

onMounted(async () => {
  await Promise.all([loadTasks(), loadStats()])
  // Auto refresh
  setInterval(async () => {
    if (filter.value === '' || filter.value === 'downloading') {
      await loadTasks()
      await loadStats()
    }
  }, 5000)
})

async function loadTasks() {
  offset.value = 0
  const params = { limit: 50, offset: 0 }
  if (filter.value) params.status = filter.value
  const res = await axios.get('/api/task/list', { params })
  tasks.value = res.data
}

async function loadMore() {
  offset.value += 50
  const params = { limit: 50, offset: offset.value }
  if (filter.value) params.status = filter.value
  const res = await axios.get('/api/task/list', { params })
  tasks.value.push(...res.data)
}

async function loadStats() {
  const res = await axios.get('/api/task/stats')
  stats.value = res.data
}

async function retry(id) {
  await axios.post(`/api/task/${id}/retry`)
  message.success('已重新加入队列')
  await loadTasks()
}

async function cancel(id) {
  await axios.post(`/api/task/${id}/cancel`)
  await loadTasks()
}

async function remove(id) {
  await axios.delete(`/api/task/${id}`)
  tasks.value = tasks.value.filter(t => t.id !== id)
}
</script>
