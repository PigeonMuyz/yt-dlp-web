<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">任务列表</h1>
      <p class="page-subtitle">查看和管理所有下载任务</p>
    </div>

    <div class="card">
      <n-tabs v-model:value="activeTab" type="line" @update:value="onTabChange">
        <n-tab-pane name="tasks" tab="进行中">
          <!-- 工具栏 -->
          <div class="toolbar">
            <div class="filter-group">
              <n-button v-for="f in taskFilters" :key="f.value"
                :type="filter===f.value?'primary':'default'" size="small"
                @click="filter=f.value;currentPage=1;loadTasks()">
                <template #icon><n-icon :component="f.icon" size="14" /></template>
                {{ f.label }}
              </n-button>
            </div>
            <div class="action-group">
              <n-button size="small" type="warning" :loading="retryingAll" @click="retryAllFailed">
                <template #icon><n-icon size="14"><RefreshOutline /></n-icon></template>
                重试所有失败
              </n-button>
              <n-button size="small" type="error" @click="clearCompleted">
                <template #icon><n-icon size="14"><TrashOutline /></n-icon></template>
                清除已完成
              </n-button>
            </div>
          </div>

          <!-- 任务列表 -->
          <div v-if="tasks.length" class="task-list">
            <div v-for="t in tasks" :key="t.id" class="task-row" :class="'status-' + t.status">
              <!-- 缩略图 -->
              <div class="task-thumb">
                <img v-if="t.thumbnail" :src="'/api/thumb?url=' + encodeURIComponent(t.thumbnail)" loading="lazy" referrerpolicy="no-referrer" />
                <div v-else class="task-thumb-placeholder">
                  <n-icon size="20"><VideocamOutline /></n-icon>
                </div>
              </div>

              <!-- 信息区 -->
              <div class="task-body">
                <div class="task-title">{{ t.title || '解析中...' }}</div>
                <div class="task-meta-row">
                  <span class="meta-platform">{{ t.platform === 'bilibili' ? 'B站' : 'YouTube' }}</span>
                  <span v-if="t.channel_name" class="meta-sep">{{ t.channel_name }}</span>
                  <span v-if="t.resolution" class="meta-sep">{{ t.resolution }}</span>
                  <span v-if="t.codec" class="meta-sep">{{ t.codec.toUpperCase() }}</span>
                  <span v-if="t.duration" class="meta-sep">{{ formatDuration(t.duration) }}</span>
                  <span v-if="t.file_size" class="meta-sep">{{ formatSize(t.file_size) }}</span>
                </div>

                <!-- 下载进度 -->
                <div v-if="t.status === 'downloading'" class="progress-area">
                  <n-progress type="line" :percentage="t.progress || 0" :height="6" :show-indicator="false" status="info" />
                  <div class="progress-detail">
                    <span>{{ t.progress || 0 }}%</span>
                    <span v-if="t.speed">{{ t.speed }}</span>
                    <span v-if="t.eta">剩余 {{ t.eta }}</span>
                  </div>
                </div>

                <!-- 错误信息 -->
                <div v-if="t.status === 'failed' && t.error_msg" class="task-error">
                  <n-icon size="12"><AlertCircleOutline /></n-icon>
                  {{ t.error_msg.substring(0, 150) }}
                </div>
              </div>

              <!-- 状态 + 操作 -->
              <div class="task-controls">
                <n-tag :type="statusTypeMap[t.status]" size="small" round>
                  {{ statusLabels[t.status] || t.status }}
                </n-tag>
                <div class="task-btns">
                  <n-tooltip v-if="t.status === 'failed' || t.status === 'pending'" trigger="hover">
                    <template #trigger>
                      <n-button size="tiny" circle tertiary type="primary" @click="retry(t.id)">
                        <template #icon><n-icon size="14"><RefreshOutline /></n-icon></template>
                      </n-button>
                    </template>
                    重试
                  </n-tooltip>
                  <n-tooltip v-if="t.status === 'downloading' || t.status === 'pending'" trigger="hover">
                    <template #trigger>
                      <n-button size="tiny" circle tertiary type="warning" @click="cancel(t.id)">
                        <template #icon><n-icon size="14"><StopOutline /></n-icon></template>
                      </n-button>
                    </template>
                    取消
                  </n-tooltip>
                  <n-tooltip trigger="hover">
                    <template #trigger>
                      <n-button size="tiny" circle tertiary type="error" @click="remove(t.id)">
                        <template #icon><n-icon size="14"><TrashOutline /></n-icon></template>
                      </n-button>
                    </template>
                    删除
                  </n-tooltip>
                </div>
              </div>
            </div>
          </div>

          <div v-else class="empty-state">
            <n-icon size="48" color="var(--text-muted)" style="opacity:0.4;"><ListOutline /></n-icon>
            <p style="margin-top:12px;">暂无任务</p>
          </div>

          <!-- 分页 -->
          <div v-if="totalTasks > 0" class="pagination-bar">
            <span>共 {{ totalTasks }} 条</span>
            <n-pagination v-if="totalTasks > pageSize" v-model:page="currentPage"
              :page-count="Math.ceil(totalTasks / pageSize)" :page-size="pageSize"
              @update:page="loadTasks" />
          </div>
        </n-tab-pane>

        <n-tab-pane name="history" tab="下载历史">
          <div v-if="history.length" class="task-list">
            <div v-for="h in history" :key="h.id" class="task-row status-completed">
              <div class="task-thumb">
                <div class="task-thumb-placeholder" style="color: var(--success);">
                  <n-icon size="20"><CheckmarkCircleOutline /></n-icon>
                </div>
              </div>
              <div class="task-body">
                <div class="task-title">{{ h.title }}</div>
                <div class="task-meta-row">
                  <span class="meta-platform">{{ h.platform === 'bilibili' ? 'B站' : 'YouTube' }}</span>
                  <span v-if="h.channel_name" class="meta-sep">{{ h.channel_name }}</span>
                  <span v-if="h.resolution" class="meta-sep">{{ h.resolution }}</span>
                  <span v-if="h.codec" class="meta-sep">{{ h.codec.toUpperCase() }}</span>
                  <span v-if="h.file_size" class="meta-sep">{{ formatSize(h.file_size) }}</span>
                </div>
                <div v-if="h.file_path" class="task-meta-row" style="font-size:11px; color:var(--text-muted); margin-top:2px;">
                  {{ h.file_path }}
                </div>
              </div>
              <div class="task-controls">
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
  TrashOutline,
  CloudDownloadOutline,
  HourglassOutline,
  CheckmarkCircleOutline,
  CloseCircleOutline,
  EllipseOutline,
  TimeOutline,
  StopOutline,
} from '@vicons/ionicons5'

const message = useMessage()
const tasks = ref([])
const history = ref([])
const filter = ref('')
const activeTab = ref('tasks')
const currentPage = ref(1)
const pageSize = 20
const totalTasks = ref(0)
const retryingAll = ref(false)
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
  const res = await axios.get('/api/task/list', { params })
  tasks.value = res.data.tasks || res.data || []
  totalTasks.value = res.data.total || tasks.value.length
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

async function retryAllFailed() {
  retryingAll.value = true
  try {
    // 获取所有失败任务
    const res = await axios.get('/api/task/list', { params: { status: 'failed', limit: 500 } })
    const allFailed = res.data.tasks || res.data || []
    const failedIds = allFailed.map(t => t.id)
    if (!failedIds.length) {
      message.warning('没有失败的任务')
      return
    }
    await axios.post('/api/task/batch', { action: 'retry', task_ids: failedIds })
    message.success(`已重试 ${failedIds.length} 个失败任务`)
    await loadTasks()
  } catch (e) { message.error('批量重试失败') }
  finally { retryingAll.value = false }
}

async function cancel(id) {
  await axios.post(`/api/task/${id}/cancel`)
  message.success('已取消')
  await loadTasks()
}

async function remove(id) {
  try {
    await axios.delete(`/api/task/${id}`)
    tasks.value = tasks.value.filter(t => t.id !== id)
    totalTasks.value = Math.max(0, totalTasks.value - 1)
    message.success('已删除')
  } catch (e) { message.error('删除失败') }
}

async function clearCompleted() {
  try {
    const res = await axios.get('/api/task/list', { params: { status: 'completed', limit: 500 } })
    const completed = res.data.tasks || res.data || []
    if (!completed.length) {
      message.warning('没有已完成的任务')
      return
    }
    await axios.post('/api/task/batch', { action: 'delete', task_ids: completed.map(t => t.id) })
    message.success(`已清除 ${completed.length} 个已完成任务`)
    await loadTasks()
  } catch (e) { message.error('清除失败') }
}
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.filter-group {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.action-group {
  display: flex;
  gap: 6px;
}

.task-list {
  display: flex;
  flex-direction: column;
}

.task-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
  transition: background 0.15s;
}
.task-row:hover {
  background: var(--bg-hover);
  margin: 0 -16px;
  padding-left: 16px;
  padding-right: 16px;
}
.task-row:last-child { border-bottom: none; }

.task-row.status-failed { border-left: 3px solid #e53e3e; padding-left: 11px; }
.task-row.status-downloading { border-left: 3px solid var(--primary); padding-left: 11px; }
.task-row.status-completed { border-left: 3px solid #38a169; padding-left: 11px; }

.task-thumb {
  width: 100px;
  height: 56px;
  border-radius: 6px;
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

.task-body {
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
.task-meta-row {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 0;
  flex-wrap: wrap;
}
.meta-platform {
  background: var(--bg-hover);
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 11px;
  margin-right: 6px;
}
.meta-sep::before {
  content: '·';
  margin: 0 4px;
  color: var(--text-muted);
}
.meta-sep:first-child::before { display: none; }

.progress-area {
  margin-top: 8px;
}
.progress-detail {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.task-error {
  font-size: 11px;
  color: #e53e3e;
  margin-top: 6px;
  display: flex;
  align-items: flex-start;
  gap: 4px;
  line-height: 1.4;
}

.task-controls {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}
.task-btns {
  display: flex;
  gap: 4px;
}

.pagination-bar {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  font-size: 13px;
  color: var(--text-secondary);
}

@media (max-width: 768px) {
  .task-row { gap: 10px; padding: 10px 0; }
  .task-thumb { width: 64px; height: 36px; }
  .task-title { font-size: 13px; }
  .task-controls { flex-direction: row; align-items: center; }
  .toolbar { flex-direction: column; align-items: flex-start; }
}
</style>
