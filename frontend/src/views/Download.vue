<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">下载</h1>
      <p class="page-subtitle">输入视频 URL 开始下载</p>
    </div>

    <!-- URL 输入 -->
    <div class="card">
      <n-input-group>
        <n-input
          v-model:value="url"
          placeholder="粘贴 YouTube / B站 视频链接..."
          size="large"
          @keyup.enter="parseUrl"
          clearable
        />
        <n-button type="primary" size="large" :loading="parsing" @click="parseUrl">
          解析
        </n-button>
      </n-input-group>
    </div>

    <!-- 视频信息 -->
    <div v-if="videoInfo" class="card" style="display: flex; gap: 20px;">
      <img
        :src="videoInfo.thumbnail"
        style="width: 240px; height: 135px; border-radius: 8px; object-fit: cover; flex-shrink: 0;"
      />
      <div style="flex: 1; min-width: 0;">
        <h3 style="margin-bottom: 8px;">{{ videoInfo.title }}</h3>
        <p style="color: var(--text-secondary); font-size: 13px;">
          {{ videoInfo.uploader }} · {{ formatDuration(videoInfo.duration) }}
          · {{ videoInfo.platform === 'bilibili' ? 'B站' : 'YouTube' }}
        </p>
        <p style="color: var(--text-secondary); font-size: 12px; margin-top: 8px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
          {{ videoInfo.description }}
        </p>
      </div>
    </div>

    <!-- 下载配置 -->
    <div v-if="videoInfo" class="card">
      <h3 style="margin-bottom: 16px;">下载配置</h3>

      <div class="form-row">
        <n-form-item label="编码格式">
          <n-select v-model:value="codec" :options="codecOptions" />
        </n-form-item>
        <n-form-item label="最大分辨率">
          <n-select v-model:value="maxRes" :options="resOptions" />
        </n-form-item>
      </div>

      <n-form-item label="字幕语言">
        <n-input v-model:value="subtitleLangs" placeholder="zh-Hans,en,ja" />
      </n-form-item>

      <n-form-item label="分类目录">
        <n-input v-model:value="category" placeholder="YouTube 或 B站" />
      </n-form-item>

      <n-button type="primary" size="large" block :loading="downloading" @click="startDownload">
        ⬇️ 开始下载
      </n-button>
    </div>

    <!-- 可用格式 -->
    <div v-if="videoInfo && videoInfo.formats?.length" class="card">
      <n-collapse>
        <n-collapse-item title="可用格式详情" name="formats">
          <n-data-table :columns="formatColumns" :data="videoInfo.formats" :bordered="false" size="small" :max-height="300" />
        </n-collapse-item>
      </n-collapse>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useMessage } from 'naive-ui'
import axios from 'axios'

const message = useMessage()
const url = ref('')
const parsing = ref(false)
const downloading = ref(false)
const videoInfo = ref(null)
const codec = ref('vp9')
const maxRes = ref('')
const subtitleLangs = ref('zh-Hans,en,ja')
const category = ref('YouTube')

const codecOptions = [
  { label: 'VP9（YouTube 推荐）', value: 'vp9' },
  { label: 'AV1（高质量）', value: 'av1' },
  { label: 'HEVC/H.265（B站推荐）', value: 'hevc' },
  { label: 'H.264（最兼容）', value: 'h264' },
  { label: '自动（最佳）', value: '' },
]

const resOptions = [
  { label: '不限', value: '' },
  { label: '4K (2160p)', value: '2160p' },
  { label: '1080p', value: '1080p' },
  { label: '720p', value: '720p' },
]

const formatColumns = [
  { title: '格式', key: 'format_id', width: 60 },
  { title: '分辨率', key: 'resolution', width: 100 },
  { title: '编码', key: 'vcodec', width: 100 },
  { title: '音频', key: 'acodec', width: 80 },
  { title: '大小', key: 'filesize', width: 100, render: (row) => formatSize(row.filesize) },
  { title: '帧率', key: 'fps', width: 60 },
]

function formatDuration(seconds) {
  if (!seconds) return ''
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  if (h) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${m}:${String(s).padStart(2, '0')}`
}

function formatSize(bytes) {
  if (!bytes) return '-'
  if (bytes > 1073741824) return (bytes / 1073741824).toFixed(1) + ' GB'
  if (bytes > 1048576) return (bytes / 1048576).toFixed(1) + ' MB'
  return (bytes / 1024).toFixed(0) + ' KB'
}

async function parseUrl() {
  if (!url.value) return
  parsing.value = true
  videoInfo.value = null
  try {
    const res = await axios.post('/api/download/parse', { url: url.value })
    videoInfo.value = res.data
    // 自动设置平台和编码
    if (res.data.platform === 'bilibili') {
      category.value = 'B站'
      codec.value = 'hevc'
    } else {
      category.value = 'YouTube'
      codec.value = 'vp9'
    }
  } catch (e) {
    message.error(e.response?.data?.detail || '解析失败')
  } finally {
    parsing.value = false
  }
}

async function startDownload() {
  downloading.value = true
  try {
    const res = await axios.post('/api/download/start', {
      url: url.value,
      title: videoInfo.value.title,
      codec: codec.value,
      max_resolution: maxRes.value,
      subtitle_langs: subtitleLangs.value,
      category: category.value,
    })
    message.success(`任务已加入队列 (ID: ${res.data.task_id})`)
  } catch (e) {
    message.error(e.response?.data?.detail || '下载失败')
  } finally {
    downloading.value = false
  }
}
</script>
