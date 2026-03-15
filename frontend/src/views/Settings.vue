<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">系统设置</h1>
      <p class="page-subtitle">配置下载、代理和 Emby 集成</p>
    </div>

    <!-- 代理配置 -->
    <div class="card">
      <div class="card-title">🌐 HTTP 代理</div>
      <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px;">
        下载 YouTube 视频需要配置代理。也可通过 Docker 环境变量 <code>YTDLP_PROXY</code> 设置。
      </p>
      <n-input v-model:value="proxy" placeholder="http://host.docker.internal:7890 或 socks5://..." />
      <n-button type="primary" size="small" style="margin-top: 12px;" @click="saveProxy">保存代理</n-button>
    </div>

    <!-- 下载设置 -->
    <div class="card">
      <div class="card-title">📁 下载设置</div>
      <div class="form-row">
        <n-form-item label="下载目录">
          <n-input v-model:value="downloadDir" placeholder="/media" />
        </n-form-item>
        <n-form-item label="默认分辨率">
          <n-select v-model:value="defaultResolution" :options="resolutionOptions" />
        </n-form-item>
      </div>
      <n-button type="primary" size="small" @click="saveDownload">保存</n-button>
    </div>

    <!-- Emby 配置 -->
    <div class="card">
      <div class="card-title">📺 Emby 集成</div>
      <div class="form-row">
        <n-form-item label="Emby 地址">
          <n-input v-model:value="embyUrl" placeholder="http://192.168.1.100:8096" />
        </n-form-item>
        <n-form-item label="API Key">
          <n-input v-model:value="embyApiKey" placeholder="Emby API Key" type="password" show-password-on="click" />
        </n-form-item>
      </div>
      <n-button type="primary" size="small" @click="saveEmby">保存</n-button>
    </div>

    <!-- 系统信息 -->
    <div class="card">
      <div class="card-title">ℹ️ 系统信息</div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 13px;">
        <div style="color: var(--text-secondary);">版本</div>
        <div>v1.0.0</div>
        <div style="color: var(--text-secondary);">环境变量代理</div>
        <div><code>{{ envProxy || '未设置' }}</code></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import axios from 'axios'

const message = useMessage()

const proxy = ref('')
const downloadDir = ref('/media')
const defaultResolution = ref('1080p')
const embyUrl = ref('')
const embyApiKey = ref('')
const envProxy = ref('')

const resolutionOptions = [
  { label: '2160p (4K)', value: '2160p' },
  { label: '1440p (2K)', value: '1440p' },
  { label: '1080p (Full HD)', value: '1080p' },
  { label: '720p (HD)', value: '720p' },
]

onMounted(async () => {
  try {
    const res = await axios.get('/api/settings')
    if (res.data) {
      proxy.value = res.data.proxy || ''
      downloadDir.value = res.data.download_dir || '/media'
      defaultResolution.value = res.data.default_resolution || '1080p'
      embyUrl.value = res.data.emby_url || ''
      embyApiKey.value = res.data.emby_api_key || ''
      envProxy.value = res.data.env_proxy || ''
    }
  } catch (e) { console.error(e) }
})

async function saveProxy() {
  try {
    await axios.post('/api/settings', { proxy: proxy.value })
    message.success('代理设置已保存')
  } catch (e) { message.error('保存失败') }
}

async function saveDownload() {
  try {
    await axios.post('/api/settings', {
      download_dir: downloadDir.value,
      default_resolution: defaultResolution.value,
    })
    message.success('下载设置已保存')
  } catch (e) { message.error('保存失败') }
}

async function saveEmby() {
  try {
    await axios.post('/api/settings', {
      emby_url: embyUrl.value,
      emby_api_key: embyApiKey.value,
    })
    message.success('Emby 设置已保存')
  } catch (e) { message.error('保存失败') }
}
</script>
