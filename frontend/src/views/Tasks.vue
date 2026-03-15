<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">任务列表</h1>
      <p class="page-subtitle">查看和管理所有下载任务</p>
    </div>

    <!-- Tab 切换：进行中 / 历史记录 -->
    <div class="card">
      <n-tabs v-model:value="activeTab" type="line" @update:value="onTabChange">
        <n-tab-pane name="tasks" tab="进行中">
          <!-- 状态筛选 -->
          <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap;">
            <n-button v-for="f in taskFilters" :key="f.value" :type="filter===f.value?'primary':'default'" size="small" @click="filter=f.value;loadTasks()">
              <template #icon><n-icon :component="f.icon" size="14" /></template>
              {{ f.label }}
            </n-button>
          </div>

          <div v-if="tasks.length">
            <div v-for="t in tasks" :key="t.id" class="task-item">
              <div class="task-thumb">
                <img v-if="t.thumbnail" :src="t.thumbnail" referrerpolicy="no-referrer" />
                <div v-else class="task-thumb-placeholder">
                  <n-icon size="20"><VideocamOutline /></n-icon>
                </div>
              </div>
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
                <div v-if="t.status === 'downloading'" style="margin-top:6px;">
                  <n-progress type="line" :percentage="t.progress" :height="6" :show-indicator="false" status="info" />
                  <div class="task-meta" style="margin-top:4px;">
                    {{ t.progress }}%
                    <span v-if="t.speed"> · {{ t.speed }}</span>
                    <span v-if="t.eta"> · 剩余 {{ t.eta }}</span>
                  </div>
                </div>
                <div v-if="t.status === 'failed' && t.error_msg" class="task-error">
                  <n-icon size="12"><AlertCircleOutline /></n-icon>
                  {{ t.error_msg.substring(0, 150) }}
                </div>
              </div>
              <div class="task-actions">
                <n-tag :type="statusTypeMap[t.status]" size="small" round>
                  {{ statusLabels[t.status] || t.status }}
                </n-tag>
                <div style="display:flex;gap:4px;margin-top:8px;">
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
          <!-- 分页 -->
          <div v-if="totalTasks > pageSize" style="display: flex; justify-content: center; margin-top: 16px;">
            <n-pagination v-model:page="currentPage" :page-count="Math.ceil(totalTasks / pageSize)" :page-size="pageSize" @update:page="loadTasks" />
          </div>
          <div v-else-if="!tasks.length" class="empty-state">
            <n-icon size="48" color="var(--text-muted)" style="opacity:0.4;"><ListOutline /></n-icon>
            <p style="margin-top:12px;">暂无任务</p>
          </div>
        </n-tab-pane>

        <n-tab-pane name="history" tab="下载历史">
          <div v-if="history.length">
            <div v-for="h in history" :key="h.id" class="task-item">
              <div class="task-thumb">
                <div class="task-thumb-placeholder">
                  <n-icon size="20"><CheckmarkCircleOutline /></n-icon>
                </div>
              </div>
              <div class="task-info">
                <div class="task-title">{{ h.title }}</div>
                <div class="task-meta">
                  <span v-if="h.channel_name">{{ h.channel_name }} ·</span>
                  <span>{{ h.platform === 'bilibili' ? 'B站' : 'YouTube' }}</span>
                  <span v-if="h.resolution"> · {{ h.resolution }}</span>
                  <span v-if="h.codec"> · {{ h.codec.toUpperCase() }}</span>
                  <span v-if="h.file_size"> · {{ formatSize(h.file_size) }}</span>
                </div>
                <div class="task-meta" style="margin-top:2px;">
                  <span v-if="h.file_path" style="font-size:11px; color:var(--text-muted);">{{ h.file_path }}</span>
                </div>
              </div>
              <div class="task-actions">
                <span style="font-size:12px; color:var(--text-muted);">{{ formatDate(h.downloaded_at) }}</span>
              </div>
            </div>
          </div>
          <div v-else class="empty-state">
            <n-icon size="48" color="var(--text-muted)" style="opacity:0.4;"><TimeOutline /></n-icon>
            <p style="margin-top:12px;">暂无下载历史</p>
          </div>
        </n-tab-pane>
      </n-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
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
  TimeOutline,
} from '@vicons/ionicons5'

const message = useMessage()
const tasks = ref([])
const history = ref([])
const filter = ref('')
const activeTab = ref('tasks')
const currentPage = ref(1)
const pageSize = 20
const totalTasks = ref(0)
let refreshTimer = null

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

const taskFilters = [
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

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function onTabChange(tab) {
  if (tab === 'history') loadHistory()
}

onMounted(async () => {
  await loadTasks()
  refreshTimer = setInterval(async () => {
    if (activeTab.value === 'tasks') await loadTasks()
  }, 5000)
})

onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})

async function loadTasks() {
  const offset = (currentPage.value - 1) * pageSize
  const params = { limit: pageSize, offset }
  if (filter.value) params.status = filter.value
  const [res, statsRes] = await Promise.all([
    axios.get('/api/task/list', { params }),
    axios.get('/api/task/stats'),
  ])
  tasks.value = res.data
  totalTasks.value = filter.value ? (statsRes.data[filter.value] || 0) : (statsRes.data.total || 0)
}

async function loadHistory() {
  const res = await axios.get('/api/task/history', { params: { limit: 50, offset: 0 } })
  history.value = res.data
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
