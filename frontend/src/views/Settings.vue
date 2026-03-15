<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">系统设置</h1>
      <p class="page-subtitle">配置下载、代理和 Emby 集成</p>
    </div>

    <!-- 代理配置 -->
    <div class="card">
      <div class="card-title">
        <n-icon size="16" style="margin-right: 6px; vertical-align: -2px;"><GlobeOutline /></n-icon>
        HTTP 代理
      </div>
      <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px;">
        下载 YouTube 视频需要配置代理。也可通过 Docker 环境变量 <code>YTDLP_PROXY</code> 设置。
      </p>
      <n-input v-model:value="proxy" placeholder="http://host.docker.internal:7890 或 socks5://..." />
      <n-button type="primary" size="small" style="margin-top: 12px;" @click="saveProxy">保存代理</n-button>
    </div>

    <!-- 下载目录 -->
    <div class="card">
      <div class="card-title">
        <n-icon size="16" style="margin-right: 6px; vertical-align: -2px;"><FolderOpenOutline /></n-icon>
        下载目录
      </div>
      <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px;">
        设置根目录和分类子目录。下载的视频将按类型自动归入对应目录（兼容 Emby 媒体库结构）。
      </p>
      <n-form-item label="根目录" style="margin-bottom: 12px;">
        <n-input v-model:value="downloadDir" placeholder="/media">
          <template #prefix><n-icon><ServerOutline /></n-icon></template>
        </n-input>
      </n-form-item>
      <div class="form-row" style="margin-bottom: 12px;">
        <n-form-item label="单品目录">
          <n-input v-model:value="dirVideos" placeholder="单品">
            <template #prefix><n-icon><FilmOutline /></n-icon></template>
          </n-input>
          <template #feedback>
            <span style="font-size: 11px; color: var(--text-muted);">单个视频（电影 NFO）→ {{ downloadDir }}/{{ dirVideos }}/标题/</span>
          </template>
        </n-form-item>
        <n-form-item label="剧集目录">
          <n-input v-model:value="dirSeries" placeholder="剧集">
            <template #prefix><n-icon><TvOutline /></n-icon></template>
          </n-input>
          <template #feedback>
            <span style="font-size: 11px; color: var(--text-muted);">追番/连续剧（电视剧 NFO）→ {{ downloadDir }}/{{ dirSeries }}/番名/S01/</span>
          </template>
        </n-form-item>
      </div>
      <n-form-item label="合集目录" style="margin-bottom: 12px; max-width: calc(50% - 8px);">
        <n-input v-model:value="dirCollections" placeholder="合集">
          <template #prefix><n-icon><AlbumsOutline /></n-icon></template>
        </n-input>
        <template #feedback>
          <span style="font-size: 11px; color: var(--text-muted);">播放列表/合集 → {{ downloadDir }}/{{ dirCollections }}/合集名/</span>
        </template>
      </n-form-item>
      <div class="form-row" style="margin-bottom: 0;">
        <n-form-item label="默认分辨率">
          <n-select v-model:value="defaultResolution" :options="resolutionOptions" />
        </n-form-item>
        <div></div>
      </div>
      <n-button type="primary" size="small" style="margin-top: 12px;" @click="saveDownload">保存下载设置</n-button>
    </div>

    <!-- Emby 配置 -->
    <div class="card">
      <div class="card-title">
        <n-icon size="16" style="margin-right: 6px; vertical-align: -2px;"><TvOutline /></n-icon>
        Emby 集成
      </div>
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
      <div class="card-title">
        <n-icon size="16" style="margin-right: 6px; vertical-align: -2px;"><InformationCircleOutline /></n-icon>
        系统信息
      </div>
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
import {
  GlobeOutline,
  FolderOpenOutline,
  ServerOutline,
  FilmOutline,
  TvOutline,
  AlbumsOutline,
  InformationCircleOutline,
} from '@vicons/ionicons5'

const message = useMessage()

const proxy = ref('')
const downloadDir = ref('/media')
const defaultResolution = ref('1080p')
const dirVideos = ref('单品')
const dirSeries = ref('剧集')
const dirCollections = ref('合集')
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
      dirVideos.value = res.data.dir_videos || '单品'
      dirSeries.value = res.data.dir_series || '剧集'
      dirCollections.value = res.data.dir_collections || '合集'
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
      dir_videos: dirVideos.value,
      dir_series: dirSeries.value,
      dir_collections: dirCollections.value,
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
