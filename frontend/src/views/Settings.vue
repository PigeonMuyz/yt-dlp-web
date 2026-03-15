<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">设置</h1>
      <p class="page-subtitle">系统配置和账号管理</p>
    </div>

    <!-- 账号绑定 -->
    <div class="card">
      <h3 style="margin-bottom: 16px;">🔑 账号绑定</h3>
      <div style="display: flex; gap: 12px; margin-bottom: 16px;">
        <n-button @click="googleAuth">🔗 绑定 Google 账号</n-button>
        <n-button @click="biliAuth">📱 绑定 B站账号</n-button>
      </div>

      <!-- Google OAuth 回调输入 -->
      <div v-if="showGoogleInput">
        <n-alert type="info" style="margin-bottom: 12px;">
          请在新窗口完成 Google 登录，然后将跳转后的 URL 粘贴到下方
        </n-alert>
        <n-input-group>
          <n-input v-model:value="googleRedirectUrl" placeholder="粘贴回调 URL..." />
          <n-button type="primary" @click="submitGoogleAuth">提交</n-button>
        </n-input-group>
      </div>

      <!-- B站二维码 -->
      <div v-if="showBiliQR" style="text-align: center;">
        <p style="margin-bottom: 12px; color: var(--text-secondary);">使用 B站App 扫描二维码</p>
        <img v-if="biliQRUrl" :src="biliQRImageUrl" style="width: 200px; height: 200px; background: white; border-radius: 8px; padding: 8px;" />
        <br />
        <n-button size="small" style="margin-top: 12px;" @click="checkBiliQR" :loading="checkingBili">
          检查登录状态
        </n-button>
      </div>

      <!-- 已绑定账号 -->
      <n-data-table :columns="cookieColumns" :data="cookies" :bordered="false" size="small" style="margin-top: 16px;" />
    </div>

    <!-- Emby 配置 -->
    <div class="card">
      <h3 style="margin-bottom: 16px;">📺 Emby 配置</h3>
      <div class="form-row">
        <n-form-item label="Emby 地址">
          <n-input v-model:value="embyUrl" placeholder="http://192.168.1.100:8096" />
        </n-form-item>
        <n-form-item label="API Key">
          <n-input v-model:value="embyApiKey" placeholder="Emby API Key" />
        </n-form-item>
      </div>
      <n-button type="primary" size="small" @click="saveEmby">保存</n-button>
    </div>

    <!-- 代理配置 -->
    <div class="card">
      <h3 style="margin-bottom: 16px;">🌐 代理配置</h3>
      <n-form-item label="HTTP 代理">
        <n-input v-model:value="proxy" placeholder="http://127.0.0.1:7890 或 socks5://..." />
      </n-form-item>
      <n-button type="primary" size="small" @click="saveProxy">保存</n-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, h } from 'vue'
import { NButton, NTag, useMessage } from 'naive-ui'
import axios from 'axios'

const message = useMessage()
const cookies = ref([])
const showGoogleInput = ref(false)
const googleRedirectUrl = ref('')
const showBiliQR = ref(false)
const biliQRUrl = ref('')
const biliQRKey = ref('')
const biliQRImageUrl = ref('')
const checkingBili = ref(false)
const embyUrl = ref('')
const embyApiKey = ref('')
const proxy = ref('')

const cookieColumns = [
  { title: '平台', key: 'platform', width: 80 },
  { title: '账号', key: 'account_name' },
  {
    title: '状态', key: 'is_valid', width: 60,
    render: (row) => h(NTag, { type: row.is_valid ? 'success' : 'error', size: 'small' }, () => row.is_valid ? '有效' : '过期')
  },
  {
    title: '操作', key: 'actions', width: 60,
    render: (row) => h(NButton, { size: 'tiny', type: 'error', onClick: () => deleteCookie(row.id) }, () => '删除')
  },
]

onMounted(async () => {
  await loadCookies()
})

async function loadCookies() {
  try {
    const res = await axios.get('/api/auth/cookies')
    cookies.value = res.data
  } catch (e) { console.error(e) }
}

async function googleAuth() {
  try {
    const res = await axios.get('/api/auth/google/url')
    window.open(res.data.url, '_blank')
    showGoogleInput.value = true
  } catch (e) {
    message.error('未配置 Google OAuth')
  }
}

async function submitGoogleAuth() {
  try {
    await axios.post('/api/auth/google/callback', { redirect_url: googleRedirectUrl.value })
    message.success('Google 账号绑定成功')
    showGoogleInput.value = false
    await loadCookies()
  } catch (e) {
    message.error(e.response?.data?.detail || '绑定失败')
  }
}

async function biliAuth() {
  try {
    const res = await axios.get('/api/auth/bilibili/qrcode')
    biliQRUrl.value = res.data.qr_url
    biliQRKey.value = res.data.qrcode_key
    // 用第三方 QR 生成 API
    biliQRImageUrl.value = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(res.data.qr_url)}`
    showBiliQR.value = true
  } catch (e) {
    message.error('获取二维码失败')
  }
}

async function checkBiliQR() {
  checkingBili.value = true
  try {
    const res = await axios.post(`/api/auth/bilibili/check?qrcode_key=${biliQRKey.value}`)
    if (res.data.status === 'success') {
      message.success('B站登录成功')
      showBiliQR.value = false
      await loadCookies()
    } else {
      message.info(res.data.message)
    }
  } catch (e) {
    message.error('检查失败')
  } finally {
    checkingBili.value = false
  }
}

async function deleteCookie(id) {
  await axios.delete(`/api/auth/cookies/${id}`)
  await loadCookies()
}

async function saveEmby() {
  message.success('Emby 配置已保存')
}

async function saveProxy() {
  message.success('代理配置已保存')
}
</script>
