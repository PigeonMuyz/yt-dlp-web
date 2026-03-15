<template>
  <div>
    <div class="page-header">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
          <h1 class="page-title">账号管理</h1>
          <p class="page-subtitle">管理 B站和 YouTube 的登录凭证</p>
        </div>
        <n-button type="primary" @click="showAddModal = true">
          <template #icon><span>➕</span></template>
          添加账号
        </n-button>
      </div>
    </div>

    <!-- 已绑定账号列表 -->
    <div class="card" v-if="cookies.length">
      <div class="card-title">已绑定账号</div>
      <div v-for="c in cookies" :key="c.id" class="account-card">
        <div class="account-avatar" :class="c.platform === 'bilibili' ? 'bili' : 'yt'">
          {{ c.platform === 'bilibili' ? '📺' : '▶️' }}
        </div>
        <div class="account-info">
          <div class="account-name">{{ c.account_name }}</div>
          <div class="account-meta">{{ c.platform === 'bilibili' ? 'Bilibili' : 'YouTube' }} · {{ formatTime(c.created_at) }}</div>
        </div>
        <n-tag :type="c.is_valid ? 'success' : 'error'" size="small" round>
          {{ c.is_valid ? '有效' : '已过期' }}
        </n-tag>
        <n-button text type="error" size="small" @click="deleteCookie(c.id)">删除</n-button>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="card">
      <div class="empty-state">
        <div class="icon">🔑</div>
        <p>暂无绑定账号</p>
        <p style="font-size: 12px; margin-top: 4px;">绑定账号后可下载更高画质的视频</p>
        <n-button type="primary" size="small" style="margin-top: 16px;" @click="showAddModal = true">添加账号</n-button>
      </div>
    </div>

    <!-- 添加账号 Modal -->
    <n-modal v-model:show="showAddModal" :mask-closable="true" style="max-width: 520px; width: 90%;">
      <n-card
        :bordered="false"
        style="border-radius: 16px;"
        :title="step === 1 ? '添加账号' : platformLabel + ' - ' + methodLabel"
        closable
        @close="resetModal"
      >
        <!-- 步骤指示 -->
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 24px;">
          <div :style="stepStyle(1)">1</div>
          <span style="font-size: 13px; color: var(--text-secondary);">选择平台</span>
          <div style="flex: 1; height: 1px; background: var(--border); margin: 0 8px;"></div>
          <div :style="stepStyle(2)">2</div>
          <span style="font-size: 13px; color: var(--text-secondary);">绑定账号</span>
        </div>

        <!-- Step 1: 选择平台 -->
        <template v-if="step === 1">
          <div class="platform-selector">
            <div class="platform-option" :class="{ selected: selectedPlatform === 'bilibili' }" @click="selectedPlatform = 'bilibili'">
              <div class="icon">📺</div>
              <div class="label">Bilibili</div>
              <div class="desc">扫码 / Cookie</div>
            </div>
            <div class="platform-option" :class="{ selected: selectedPlatform === 'youtube' }" @click="selectedPlatform = 'youtube'">
              <div class="icon">▶️</div>
              <div class="label">YouTube</div>
              <div class="desc">Cookie 导入</div>
            </div>
          </div>

          <!-- 绑定方式选择 -->
          <div v-if="selectedPlatform === 'bilibili'" style="margin-bottom: 16px;">
            <div style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">绑定方式</div>
            <n-radio-group v-model:value="bindMethod" name="method">
              <n-space>
                <n-radio value="qrcode">扫码登录</n-radio>
                <n-radio value="cookie">Cookie 导入</n-radio>
              </n-space>
            </n-radio-group>
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px;">
            <n-button @click="resetModal">取消</n-button>
            <n-button type="primary" :disabled="!selectedPlatform" @click="nextStep">下一步</n-button>
          </div>
        </template>

        <!-- Step 2: 绑定操作 -->
        <template v-if="step === 2">
          <!-- B站扫码 -->
          <div v-if="selectedPlatform === 'bilibili' && bindMethod === 'qrcode'">
            <div v-if="!qrImageUrl" style="text-align: center; padding: 20px;">
              <n-button type="primary" @click="fetchBiliQR" :loading="loadingQR">生成登录二维码</n-button>
            </div>
            <div v-else style="text-align: center;">
              <p style="color: var(--text-secondary); margin-bottom: 12px; font-size: 13px;">使用 Bilibili App 扫描二维码</p>
              <img :src="qrImageUrl" style="width: 200px; height: 200px; border-radius: 12px; border: 1px solid var(--border);" />
              <div style="margin-top: 16px;">
                <n-button size="small" @click="checkBiliQR" :loading="checkingQR">检查登录状态</n-button>
                <n-button size="small" style="margin-left: 8px;" @click="fetchBiliQR" :loading="loadingQR">刷新二维码</n-button>
              </div>
              <p v-if="qrStatus" style="margin-top: 12px; font-size: 13px; color: var(--text-secondary);">{{ qrStatus }}</p>
            </div>
          </div>

          <!-- Cookie 粘贴（B站 / YouTube） -->
          <div v-else>
            <n-alert type="info" style="margin-bottom: 16px; border-radius: 10px;">
              <template v-if="selectedPlatform === 'youtube'">
                使用浏览器扩展（如 <strong>Get cookies.txt LOCALLY</strong>）导出 YouTube 的 cookies.txt 文件内容，粘贴至下方。
              </template>
              <template v-else>
                导出 Bilibili 的 cookies.txt 文件内容（Netscape 格式），粘贴至下方。
              </template>
            </n-alert>
            <n-input
              v-model:value="cookieText"
              type="textarea"
              :rows="8"
              placeholder="粘贴 cookies.txt 内容..."
              style="font-family: monospace; font-size: 12px;"
            />
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px;">
            <n-button @click="step = 1">上一步</n-button>
            <n-button
              v-if="!(selectedPlatform === 'bilibili' && bindMethod === 'qrcode')"
              type="primary"
              @click="submitCookie"
              :loading="submitting"
            >
              确认导入
            </n-button>
          </div>
        </template>
      </n-card>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import axios from 'axios'

const message = useMessage()

// 状态
const cookies = ref([])
const showAddModal = ref(false)
const step = ref(1)
const selectedPlatform = ref('bilibili')
const bindMethod = ref('qrcode')
const cookieText = ref('')
const submitting = ref(false)

// B站扫码
const qrImageUrl = ref('')
const qrcodeKey = ref('')
const loadingQR = ref(false)
const checkingQR = ref(false)
const qrStatus = ref('')

const platformLabel = computed(() => selectedPlatform.value === 'bilibili' ? 'Bilibili' : 'YouTube')
const methodLabel = computed(() => {
  if (selectedPlatform.value === 'youtube') return 'Cookie 导入'
  return bindMethod.value === 'qrcode' ? '扫码登录' : 'Cookie 导入'
})

function stepStyle(n) {
  const active = step.value >= n
  return {
    width: '28px', height: '28px', borderRadius: '50%',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: '13px', fontWeight: '600',
    background: active ? 'var(--primary)' : 'var(--bg-hover)',
    color: active ? '#fff' : 'var(--text-muted)',
  }
}

function nextStep() { step.value = 2 }

function resetModal() {
  showAddModal.value = false
  step.value = 1
  cookieText.value = ''
  qrImageUrl.value = ''
  qrStatus.value = ''
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('zh-CN')
}

onMounted(loadCookies)

async function loadCookies() {
  try {
    const res = await axios.get('/api/auth/cookies')
    cookies.value = res.data
  } catch (e) { console.error(e) }
}

// B站扫码
async function fetchBiliQR() {
  loadingQR.value = true
  qrStatus.value = ''
  try {
    const res = await axios.get('/api/auth/bilibili/qrcode')
    qrcodeKey.value = res.data.qrcode_key
    qrImageUrl.value = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(res.data.qr_url)}`
  } catch (e) {
    message.error('获取二维码失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loadingQR.value = false
  }
}

async function checkBiliQR() {
  checkingQR.value = true
  try {
    const res = await axios.post(`/api/auth/bilibili/check?qrcode_key=${qrcodeKey.value}`)
    if (res.data.status === 'success') {
      message.success('B站登录成功！')
      resetModal()
      await loadCookies()
    } else {
      qrStatus.value = res.data.message
    }
  } catch (e) {
    message.error('检查失败')
  } finally {
    checkingQR.value = false
  }
}

// Cookie 导入
async function submitCookie() {
  if (!cookieText.value.trim()) return message.warning('请粘贴 Cookie 内容')
  submitting.value = true
  try {
    const endpoint = selectedPlatform.value === 'youtube' ? '/api/auth/youtube/cookies' : '/api/auth/bilibili/cookies'
    const res = await axios.post(endpoint, {
      cookie_text: cookieText.value,
      platform: selectedPlatform.value,
    })
    message.success(res.data.message)
    resetModal()
    await loadCookies()
  } catch (e) {
    message.error(e.response?.data?.detail || '导入失败')
  } finally {
    submitting.value = false
  }
}

async function deleteCookie(id) {
  await axios.delete(`/api/auth/cookies/${id}`)
  message.success('已删除')
  await loadCookies()
}
</script>
