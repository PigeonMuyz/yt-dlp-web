<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">任务队列</h1>
      <p class="page-subtitle">查看和管理下载任务</p>
    </div>

    <!-- 状态筛选 -->
    <div class="card">
      <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap: wrap;">
        <n-button v-for="f in filters" :key="f.value" :type="filter===f.value?'primary':'default'" size="small" @click="filter=f.value;loadTasks()">
          <template #icon><n-icon :component="f.icon" size="14" /></template>
          {{ f.label }}
        </n-button>
      </div>

      <!-- 任务列表 -->
      <div v-if="tasks.length">
        <div v-for="t in tasks" :key="t.id" class="task-item">
          <!-- 缩略图 -->
          <div class="task-thumb">
            <img v-if="t.thumbnail" :src="t.thumbnail" />
            <div v-else class="task-thumb-placeholder">
              <n-icon size="20"><VideocamOutline /></n-icon>
            </div>
          </div>

          <!-- 信息 -->
          <div class="task-info">
            <div class="task-title">{{ t.title || '解析中...' }}</div>
            <div class="task-meta">
              <span v-if="t.channel_name">{{ t.channel_name }} ·</span>
              <span>{{ t.platform === 'bilibili' ? 'B站' : 'YouTube' }}</span>
              <span v-if="t.resolution"> · {{ t.resolution }}</span>
              <span v-if="t.codec"> · {{ t.codec.toUpperCase() }}</span>
              <span v-if="t.file_size"> · {{ formatSize(t.file_size) }}</span>
              <span v-if="t.duration"> · {{ formatDuration(t.duration) }}</span>
            </div>
            <!-- 进度条 -->
            <div v-if="t.status === 'downloading'" style="margin-top: 6px;">
              <n-progress type="line" :percentage="t.progress" :height="6" :show-indicator="false" status="info" />
              <div class="task-meta" style="margin-top: 4px;">
                {{ t.progress }}%
                <span v-if="t.speed"> · {{ t.speed }}</span>
                <span v-if="t.eta"> · 剩余 {{ t.eta }}</span>
              </div>
            </div>
            <!-- 错误信息 -->
            <div v-if="t.status === 'failed' && t.error_msg" class="task-error">
              <n-icon size="12"><AlertCircleOutline /></n-icon>
              {{ t.error_msg.substring(0, 120) }}
            </div>
          </div>

          <!-- 状态 + 操作 -->
          <div class="task-actions">
            <n-tag :type="statusTypeMap[t.status]" size="small" round>
              {{ statusLabels[t.status] || t.status }}
            </n-tag>
            <div style="display: flex; gap: 4px; margin-top: 8px;">
              <n-button v-if="t.status === 'failed'" size="tiny" tertiary type="primary" @click="retry(t.id)">
                <template #icon><n-icon size="14"><RefreshOutline /></n-icon></template>
              </n-button>
              <n-button v-if="t.status === 'pending'" size="tiny" tertiary type="warning" @click="cancel(t.id)">
                <template #icon><n-icon size="14"><CloseOutline /></n-icon></template>
              </n-button>
              <n-button size="tiny" tertiary type="error" @click="remove(t.id)">
                <template #icon><n-icon size="14"><TrashOutline /></n-icon></template>
              </n-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="empty-state">
        <n-icon size="48" color="var(--text-muted)" style="opacity: 0.4;"><ListOutline /></n-icon>
        <p style="margin-top: 12px;">暂无任务</p>
      </div>

      <div style="text-align: center; margin-top: 16px;" v-if="tasks.length >= 50">
        <n-button size="small" @click="loadMore">加载更多</n-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import axios from 'axios'
import {
  ListOutline,
  VideocamOutline,
  AlertCircleOutline,
  RefreshOutline,
  CloseOutline,
  TrashOutline,
  CloudDownloadOutline,
  HourglassOutline,
  CheckmarkCircleOutline,
  CloseCircleOutline,
  EllipseOutline,
} from '@vicons/ionicons5'

const message = useMessage()
const tasks = ref([])
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

const statusTypeMap = {
  pending: 'default',
  downloading: 'info',
  processing: 'info',
  completed: 'success',
  failed: 'error',
  cancelled: 'warning',
}

const filters = [
  { label: '全部', value: '', icon: EllipseOutline },
  { label: '下载中', value: 'downloading', icon: CloudDownloadOutline },
  { label: '等待', value: 'pending', icon: HourglassOutline },
  { label: '完成', value: 'completed', icon: CheckmarkCircleOutline },
  { label: '失败', value: 'failed', icon: CloseCircleOutline },
]

function formatSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + ' MB'
  return (bytes / 1024 / 1024 / 1024).toFixed(2) + ' GB'
}

function formatDuration(sec) {
  if (!sec) return ''
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = sec % 60
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${m}:${String(s).padStart(2, '0')}`
}

onMounted(async () => {
  await loadTasks()
  setInterval(async () => {
    if (filter.value === '' || filter.value === 'downloading') {
      await loadTasks()
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

<style scoped>
.task-item {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 14px 0;
  border-bottom: 1px solid var(--border);
}
.task-item:last-child { border-bottom: none; }

.task-thumb {
  width: 120px;
  height: 68px;
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
  background: var(--bg-hover);
}
.task-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.task-thumb-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

.task-info {
  flex: 1;
  min-width: 0;
}
.task-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.task-meta {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}
.task-error {
  font-size: 11px;
  color: #e53e3e;
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.task-actions {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

@media (max-width: 768px) {
  .task-thumb { width: 80px; height: 45px; }
  .task-title { font-size: 13px; }
}
</style>
