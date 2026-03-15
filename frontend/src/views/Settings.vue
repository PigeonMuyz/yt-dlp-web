<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">设置</h1>
      <p class="page-subtitle">系统配置和账号管理</p>
    </div>

    <!-- 账号绑定 -->
    <div class="card">
      <h3 style="margin-bottom: 16px;">🔑 账号绑定</h3>

      <n-tabs type="segment" style="margin-bottom: 16px;">
        <n-tab-pane name="bilibili" tab="📱 B站扫码">
          <div v-if="!showBiliQR">
            <n-button type="primary" @click="biliAuth">生成二维码</n-button>
          </div>
          <div v-else style="text-align: center;">
            <p style="margin-bottom: 12px; color: var(--text-secondary);">使用 B站App 扫描二维码</p>
            <img v-if="biliQRImageUrl" :src="biliQRImageUrl" style="width: 200px; height: 200px; background: white; border-radius: 8px; padding: 8px;" />
            <br />
            <n-button size="small" style="margin-top: 12px;" @click="checkBiliQR" :loading="checkingBili">
              检查登录状态
            </n-button>
            <n-button size="small" style="margin-top: 12px; margin-left: 8px;" @click="showBiliQR = false">
              取消
            </n-button>
          </div>
        </n-tab-pane>

        <n-tab-pane name="bilibili-cookie" tab="📋 B站 Cookie">
          <n-alert type="info" style="margin-bottom: 12px;">
            如果扫码有问题，可以直接粘贴 cookies.txt 内容（Netscape 格式）
          </n-alert>
          <n-input v-model:value="biliCookieText" type="textarea" :rows="5" placeholder="粘贴 B站 cookies.txt 内容..." />
          <n-button type="primary" size="small" style="margin-top: 8px;" @click="importBiliCookies">导入</n-button>
        </n-tab-pane>

        <n-tab-pane name="youtube" tab="📺 YouTube Cookie">
          <n-alert type="info" style="margin-bottom: 12px;">
            使用浏览器扩展（如 Get cookies.txt LOCALLY）导出 YouTube 的 cookies.txt，粘贴内容或上传文件。
          </n-alert>
          <n-input v-model:value="ytCookieText" type="textarea" :rows="5" placeholder="粘贴 YouTube cookies.txt 内容..." />
          <div style="display: flex; gap: 8px; margin-top: 8px;">
            <n-button type="primary" size="small" @click="importYtCookies">导入</n-button>
            <n-upload :action="'/api/auth/youtube/cookies/upload'" :show-file-list="false" @finish="onYtUpload">
              <n-button size="small">上传文件</n-button>
            </n-upload>
          </div>
        </n-tab-pane>
      </n-tabs>

      <!-- 已绑定账号 -->
      <h4 style="margin-top: 16px; margin-bottom: 8px;">已绑定账号</h4>
      <n-data-table :columns="cookieColumns" :data="cookies" :bordered="false" size="small" />
      <n-empty v-if="!cookies.length" description="暂无绑定账号" style="margin: 12px 0;" />
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
      <n-button type="primary" size="small" @click="saveSettings">保存</n-button>
    </div>

    <!-- 代理配置 -->
    <div class="card">
      <h3 style="margin-bottom: 16px;">🌐 代理配置</h3>
      <n-form-item label="HTTP 代理">
        <n-input v-model:value="proxy" placeholder="http://127.0.0.1:7890 或 socks5://..." />
      </n-form-item>
      <n-button type="primary" size="small" @click="saveSettings">保存</n-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, h } from 'vue'
import { NButton, NTag, useMessage } from 'naive-ui'
import axios from 'axios'

const message = useMessage()
const cookies = ref([])

// B站扫码
const showBiliQR = ref(false)
const biliQRKey = ref('')
const biliQRImageUrl = ref('')
const checkingBili = ref(false)

// Cookie 导入
const biliCookieText = ref('')
const ytCookieText = ref('')

// 设置
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
    title: '', key: 'actions', width: 60,
    render: (row) => h(NButton, { size: 'tiny', type: 'error', onClick: () => deleteCookie(row.id) }, () => '删除')
  },
]

onMounted(loadCookies)

async function loadCookies() {
  try {
    const res = await axios.get('/api/auth/cookies')
    cookies.value = res.data
  } catch (e) { console.error(e) }
}

// ========== B站扫码 ==========
async function biliAuth() {
  try {
    const res = await axios.get('/api/auth/bilibili/qrcode')
    biliQRKey.value = res.data.qrcode_key
    biliQRImageUrl.value = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(res.data.qr_url)}`
    showBiliQR.value = true
  } catch (e) {
    message.error('获取二维码失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function checkBiliQR() {
  checkingBili.value = true
  try {
    const res = await axios.post(`/api/auth/bilibili/check?qrcode_key=${biliQRKey.value}`)
    if (res.data.status === 'success') {
      message.success('B站登录成功！')
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

// ========== Cookie 导入 ==========
async function importBiliCookies() {
  if (!biliCookieText.value.trim()) return message.warning('请粘贴 Cookie 内容')
  try {
    const res = await axios.post('/api/auth/bilibili/cookies', { cookie_text: biliCookieText.value, platform: 'bilibili' })
    message.success(res.data.message)
    biliCookieText.value = ''
    await loadCookies()
  } catch (e) {
    message.error(e.response?.data?.detail || '导入失败')
  }
}

async function importYtCookies() {
  if (!ytCookieText.value.trim()) return message.warning('请粘贴 Cookie 内容')
  try {
    const res = await axios.post('/api/auth/youtube/cookies', { cookie_text: ytCookieText.value, platform: 'youtube' })
    message.success(res.data.message)
    ytCookieText.value = ''
    await loadCookies()
  } catch (e) {
    message.error(e.response?.data?.detail || '导入失败')
  }
}

function onYtUpload({ event }) {
  try {
    const res = JSON.parse(event.target.response)
    message.success(res.message || 'cookies 文件已上传')
    loadCookies()
  } catch (e) {
    message.error('上传失败')
  }
}

async function deleteCookie(id) {
  await axios.delete(`/api/auth/cookies/${id}`)
  await loadCookies()
}

async function saveSettings() {
  try {
    await axios.post('/api/setup', {
      emby_url: embyUrl.value,
      emby_api_key: embyApiKey.value,
      proxy: proxy.value,
    })
    message.success('设置已保存')
  } catch (e) {
    message.error('保存失败')
  }
}
</script>
