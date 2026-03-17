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
      <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px;">
        配置后，每次下载完成会自动刷新 Emby 媒体库，新视频将立即出现在你的 Emby 中。视频文件按 Emby 规范存储（NFO + poster 封面）。
      </p>
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

    <!-- TMDB 配置 -->
    <div class="card">
      <div class="card-title">
        <n-icon size="16" style="margin-right: 6px; vertical-align: -2px;"><SearchOutline /></n-icon>
        TMDB 元数据
      </div>
      <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px;">
        配置后可在剧集管理中搜索 TMDB 自动填充封面、简介等信息。<a href="https://www.themoviedb.org/settings/api" target="_blank" style="color: var(--primary);">获取 API Key</a>
      </p>
      <n-form-item label="TMDB API Key">
        <n-input v-model:value="tmdbApiKey" placeholder="输入 TMDB API Key (v3 auth)" type="password" show-password-on="click" />
      </n-form-item>
      <n-button type="primary" size="small" @click="saveTmdb">保存</n-button>
    </div>

    <!-- 开发者选项 -->
    <div class="card">
      <div class="card-title">
        <n-icon size="16" style="margin-right: 6px; vertical-align: -2px;"><CodeOutline /></n-icon>
        开发者选项
      </div>
      <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px;">
        启用后，订阅检查只获取最新的几个视频，方便测试功能而不会大量下载。
      </p>
      <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
        <n-switch v-model:value="devMode" />
        <span style="font-size: 14px;">{{ devMode ? '开发模式已启用' : '开发模式已关闭' }}</span>
        <n-tag v-if="devMode" type="warning" size="small" round>测试中</n-tag>
      </div>
      <div v-if="devMode" style="margin-bottom: 12px;">
        <n-form-item label="订阅最多下载视频数">
          <n-input-number v-model:value="devMaxItems" :min="1" :max="50" style="width: 140px;" />
        </n-form-item>
      </div>
      <n-button type="primary" size="small" @click="saveDev">保存</n-button>
      <n-button size="small" style="margin-left: 8px;" @click="checkAllSubs" :loading="checkingAll">立即检查所有订阅</n-button>
    </div>

    <!-- 通知推送 -->
    <div class="card">
      <div class="card-title">
        <n-icon size="16" style="margin-right: 6px; vertical-align: -2px;"><NotificationsOutline /></n-icon>
        通知推送
      </div>
      <div style="display: grid; grid-template-columns: 120px 1fr; gap: 8px 12px; align-items: center; font-size: 13px;">
        <div style="color: var(--text-secondary);">推送方式</div>
        <n-select v-model:value="notifyType" :options="notifyOptions" size="small" style="max-width: 200px;" />
        <template v-if="notifyType">
          <div style="color: var(--text-secondary);">Token / Key</div>
          <n-input v-model:value="notifyToken" :placeholder="notifyType === 'telegram' ? 'bot_token@chat_id' : 'Key'" size="small" style="max-width: 360px;" />
          <div style="color: var(--text-secondary);">{{ notifyType === 'webhook' ? 'Webhook URL' : notifyType === 'bark' ? 'Bark 服务器' : 'Chat ID' }}</div>
          <n-input v-model:value="notifyWebhookUrl" :placeholder="notifyType === 'telegram' ? '可用 token@chatid 格式' : 'https://...'" size="small" style="max-width: 360px;" />
        </template>
      </div>
      <div style="display: flex; gap: 8px; margin-top: 12px;">
        <n-button type="primary" size="small" @click="saveNotify">保存</n-button>
        <n-button size="small" @click="testNotify" :loading="testingNotify">发送测试</n-button>
      </div>
    </div>

    <!-- 限速 -->
    <div class="card">
      <div class="card-title">
        <n-icon size="16" style="margin-right: 6px; vertical-align: -2px;"><SpeedometerOutline /></n-icon>
        下载限速
      </div>
      <div style="display: flex; align-items: center; gap: 12px; font-size: 13px;">
        <n-input-number v-model:value="rateLimit" :min="0" :step="100" style="width: 160px;" size="small" />
        <span style="color: var(--text-secondary);">KB/s（0 = 不限速）</span>
        <n-button type="primary" size="small" @click="saveRateLimit">保存</n-button>
      </div>
    </div>

    <!-- 系统信息 & 更新 -->
    <div class="card">
      <div class="card-title">
        <n-icon size="16" style="margin-right: 6px; vertical-align: -2px;"><InformationCircleOutline /></n-icon>
        系统信息 & 更新
      </div>
      <div style="display: grid; grid-template-columns: 120px 1fr; gap: 8px; font-size: 13px; align-items: center;">
        <div style="color: var(--text-secondary);">当前版本</div>
        <div><code>v{{ version }}</code></div>
        <div style="color: var(--text-secondary);">环境变量代理</div>
        <div><code>{{ envProxy || '未设置' }}</code></div>
        <div style="color: var(--text-secondary);">GitHub 仓库</div>
        <div style="display: flex; gap: 8px; align-items: center;">
          <n-input v-model:value="githubRepo" placeholder="owner/repo" size="small" style="max-width: 240px;" />
          <n-button size="small" @click="saveGitHub">保存</n-button>
        </div>
      </div>
      <div style="display: flex; gap: 8px; margin-top: 16px; align-items: center;">
        <n-button size="small" :loading="checkingUpdate" @click="checkUpdate">检查更新</n-button>
        <n-button v-if="updateInfo.has_update" type="primary" size="small" :loading="updating" @click="doUpdate">🚀 一键更新到 v{{ updateInfo.latest }}</n-button>
        <span v-if="updateInfo.message" style="font-size: 13px; color: var(--text-secondary);">{{ updateInfo.message }}</span>
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
  SearchOutline,
  CodeOutline,
  NotificationsOutline,
  SpeedometerOutline,
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
const tmdbApiKey = ref('')
const devMode = ref(false)
const devMaxItems = ref(5)
const checkingAll = ref(false)
const envProxy = ref('')
const version = ref('1.0.0')
const githubRepo = ref('')
const checkingUpdate = ref(false)
const updating = ref(false)
const updateInfo = ref({ has_update: false, message: '' })
// 通知推送
const notifyType = ref('')
const notifyToken = ref('')
const notifyWebhookUrl = ref('')
const testingNotify = ref(false)
const notifyOptions = [
  { label: '关闭', value: '' },
  { label: 'Telegram', value: 'telegram' },
  { label: 'Bark (iOS)', value: 'bark' },
  { label: 'Webhook', value: 'webhook' },
]
// 限速
const rateLimit = ref(0)

const resolutionOptions = [
  { label: '最佳画质', value: 'best' },
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
      tmdbApiKey.value = res.data.tmdb_api_key || ''
      devMode.value = res.data.dev_mode || false
      devMaxItems.value = res.data.dev_max_items || 5
      envProxy.value = res.data.env_proxy || ''
      version.value = res.data.version || '1.0.0'
      githubRepo.value = res.data.github_repo || ''
      notifyType.value = res.data.notify_type || ''
      notifyToken.value = res.data.notify_token || ''
      notifyWebhookUrl.value = res.data.notify_webhook_url || ''
      rateLimit.value = res.data.rate_limit || 0
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

async function saveTmdb() {
  try {
    await axios.post('/api/settings', { tmdb_api_key: tmdbApiKey.value })
    message.success('TMDB 设置已保存')
  } catch (e) { message.error('保存失败') }
}

async function saveDev() {
  try {
    await axios.post('/api/settings', { dev_mode: devMode.value, dev_max_items: devMaxItems.value })
    message.success('开发者选项已保存')
  } catch (e) { message.error('保存失败') }
}

async function checkAllSubs() {
  checkingAll.value = true
  try {
    const res = await axios.post('/api/subscription/check-all')
    message.success(res.data.message)
  } catch (e) { message.error('触发失败') }
  finally { checkingAll.value = false }
}

async function saveGitHub() {
  try {
    await axios.post('/api/settings', { github_repo: githubRepo.value })
    message.success('GitHub 仓库已保存')
  } catch (e) { message.error('保存失败') }
}

async function checkUpdate() {
  checkingUpdate.value = true
  try {
    const res = await axios.get('/api/check-update')
    updateInfo.value = res.data
    if (res.data.has_update) {
      message.info(`发现新版本 v${res.data.latest}`)
    } else {
      message.success(res.data.message)
    }
  } catch (e) { message.error('检查失败') }
  finally { checkingUpdate.value = false }
}

async function doUpdate() {
  updating.value = true
  try {
    const res = await axios.post('/api/update')
    message.success(res.data.message)
  } catch (e) { message.error('更新失败') }
  finally { updating.value = false }
}

async function saveNotify() {
  try {
    await axios.post('/api/settings', {
      notify_type: notifyType.value,
      notify_token: notifyToken.value,
      notify_webhook_url: notifyWebhookUrl.value,
    })
    message.success('通知设置已保存')
  } catch (e) { message.error('保存失败') }
}

async function testNotify() {
  testingNotify.value = true
  try {
    const res = await axios.post('/api/notify/test')
    message.success(res.data.message)
  } catch (e) { message.error('测试失败') }
  finally { testingNotify.value = false }
}

async function saveRateLimit() {
  try {
    await axios.post('/api/settings', { rate_limit: rateLimit.value })
    message.success(`限速设置已保存${rateLimit.value > 0 ? ': ' + rateLimit.value + ' KB/s' : ': 不限速'}`)
  } catch (e) { message.error('保存失败') }
}
</script>
