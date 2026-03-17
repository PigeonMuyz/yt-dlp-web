<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">系统日志</h1>
      <div style="display: flex; gap: 8px;">
        <n-button size="small" @click="loadLogs" :loading="loading">刷新</n-button>
        <n-button size="small" @click="downloadLog">下载完整日志</n-button>
        <n-switch v-model:value="autoScroll" size="small" />
        <span style="font-size: 13px; color: var(--text-secondary);">自动滚动</span>
      </div>
    </div>

    <div class="card log-container" ref="logRef">
      <pre class="log-content"><template v-for="(line, i) in logLines" :key="i"><span :class="getLogClass(line)">{{ line }}</span>
</template></pre>
      <div v-if="!logLines.length && !loading" style="padding: 40px; text-align: center; color: var(--text-muted);">暂无日志</div>
    </div>

    <div style="text-align: center; padding: 8px; font-size: 12px; color: var(--text-muted);">
      共 {{ totalLines }} 行，显示最近 {{ logLines.length }} 行
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import axios from 'axios'

const logLines = ref([])
const totalLines = ref(0)
const loading = ref(false)
const autoScroll = ref(true)
const logRef = ref(null)
let timer = null

function getLogClass(line) {
  if (line.includes('[ERROR]') || line.includes('ERROR')) return 'log-error'
  if (line.includes('[WARNING]') || line.includes('WARNING')) return 'log-warn'
  if (line.includes('[INFO]')) return 'log-info'
  if (line.includes('[DEBUG]')) return 'log-debug'
  return ''
}

async function loadLogs() {
  loading.value = true
  try {
    const res = await axios.get('/api/logs/recent', { params: { lines: 500 } })
    logLines.value = res.data.lines || []
    totalLines.value = res.data.total || 0
    if (autoScroll.value) {
      nextTick(() => {
        if (logRef.value) logRef.value.scrollTop = logRef.value.scrollHeight
      })
    }
  } catch (e) { console.error(e) }
  finally { loading.value = false }
}

function downloadLog() {
  window.open('/api/logs/download', '_blank')
}

onMounted(() => {
  loadLogs()
  timer = setInterval(loadLogs, 5000)
})

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.log-container {
  max-height: calc(100vh - 220px);
  overflow-y: auto;
  padding: 0 !important;
}
.log-content {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.6;
  padding: 16px;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--text-secondary);
}
.log-error { color: #e88; }
.log-warn { color: #ec9; }
.log-info { color: var(--text-primary); }
.log-debug { color: var(--text-muted); }
</style>
