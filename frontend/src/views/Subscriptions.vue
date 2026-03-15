<template>
  <div>
    <div class="page-header" style="display: flex; justify-content: space-between; align-items: center;">
      <div>
        <h1 class="page-title">订阅管理</h1>
        <p class="page-subtitle">频道 / UP主 / 收藏夹 / 追番</p>
      </div>
      <n-button type="primary" @click="showAdd = true">+ 新建订阅</n-button>
    </div>

    <!-- 订阅列表 -->
    <div v-for="sub in subscriptions" :key="sub.id" class="card" style="display: flex; gap: 16px; align-items: center;">
      <img v-if="sub.thumbnail" :src="sub.thumbnail" style="width: 60px; height: 60px; border-radius: 50%; object-fit: cover;" />
      <div v-else style="width: 60px; height: 60px; border-radius: 50%; background: var(--bg-hover); display: flex; align-items: center; justify-content: center; font-size: 24px;">
        {{ sub.platform === 'youtube' ? '📺' : '📱' }}
      </div>
      <div style="flex: 1; min-width: 0;">
        <h4 style="margin-bottom: 4px;">{{ sub.name }}</h4>
        <p style="color: var(--text-secondary); font-size: 12px;">
          {{ platformLabel(sub.platform) }} · {{ typeLabel(sub.sub_type) }}
          · {{ codecLabel(sub.codec_strategy) }}
          · {{ orgLabel(sub.org_mode) }}
        </p>
      </div>
      <n-tag :type="sub.enabled ? 'success' : 'default'" size="small">
        {{ sub.enabled ? '启用' : '暂停' }}
      </n-tag>
      <n-button-group size="small">
        <n-button @click="checkNow(sub.id)">检查</n-button>
        <n-button @click="toggleSub(sub)">{{ sub.enabled ? '暂停' : '启用' }}</n-button>
        <n-button type="error" @click="deleteSub(sub.id)">删除</n-button>
      </n-button-group>
    </div>

    <n-empty v-if="!subscriptions.length" description="暂无订阅" />

    <!-- 新建订阅弹窗 -->
    <n-modal v-model:show="showAdd" preset="card" title="新建订阅" style="width: 560px;">
      <n-form-item label="平台">
        <n-radio-group v-model:value="newSub.platform">
          <n-radio value="youtube">YouTube</n-radio>
          <n-radio value="bilibili">B站</n-radio>
        </n-radio-group>
      </n-form-item>
      <n-form-item label="类型">
        <n-select v-model:value="newSub.sub_type" :options="typeOptions" />
      </n-form-item>
      <n-form-item label="URL">
        <n-input v-model:value="newSub.url" placeholder="频道/播放列表/收藏夹 URL" />
      </n-form-item>
      <n-form-item label="名称（可选）">
        <n-input v-model:value="newSub.name" placeholder="自动获取" />
      </n-form-item>
      <div class="form-row">
        <n-form-item label="编码策略">
          <n-select v-model:value="newSub.codec_strategy" :options="codecStrategyOptions" />
        </n-form-item>
        <n-form-item label="首选编码">
          <n-select v-model:value="newSub.preferred_codec" :options="codecOptions" />
        </n-form-item>
      </div>
      <div class="form-row">
        <n-form-item label="目录组织">
          <n-select v-model:value="newSub.org_mode" :options="orgOptions" />
        </n-form-item>
        <n-form-item label="检查间隔">
          <n-select v-model:value="newSub.check_interval" :options="intervalOptions" />
        </n-form-item>
      </div>
      <n-button type="primary" block :loading="adding" @click="addSubscription">创建</n-button>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import axios from 'axios'

const message = useMessage()
const subscriptions = ref([])
const showAdd = ref(false)
const adding = ref(false)

const newSub = ref({
  platform: 'youtube',
  sub_type: 'channel',
  url: '',
  name: '',
  codec_strategy: 'dual',
  preferred_codec: 'vp9',
  org_mode: 'by_year',
  check_interval: 3600,
})

const typeOptions = [
  { label: '频道/UP主', value: 'channel' },
  { label: '播放列表', value: 'playlist' },
  { label: '收藏夹', value: 'favorites' },
  { label: '追番', value: 'bangumi' },
  { label: '稍后再看', value: 'watch_later' },
]

const codecStrategyOptions = [
  { label: '单编码', value: 'single' },
  { label: '双编码', value: 'dual' },
  { label: '全部', value: 'all' },
]

const codecOptions = [
  { label: 'VP9', value: 'vp9' },
  { label: 'AV1', value: 'av1' },
  { label: 'HEVC', value: 'hevc' },
  { label: 'H.264', value: 'h264' },
]

const orgOptions = [
  { label: '按年份', value: 'by_year' },
  { label: '按播放列表', value: 'by_playlist' },
  { label: '平铺', value: 'flat' },
  { label: 'Season', value: 'season' },
]

const intervalOptions = [
  { label: '每小时', value: 3600 },
  { label: '每 6 小时', value: 21600 },
  { label: '每天', value: 86400 },
  { label: '每周', value: 604800 },
]

const platformLabel = (p) => p === 'youtube' ? 'YouTube' : 'B站'
const typeLabel = (t) => typeOptions.find(o => o.value === t)?.label || t
const codecLabel = (c) => codecStrategyOptions.find(o => o.value === c)?.label || c
const orgLabel = (o) => orgOptions.find(opt => opt.value === o)?.label || o

onMounted(async () => {
  try {
    const res = await axios.get('/api/subscription/list')
    subscriptions.value = res.data
  } catch (e) { console.error(e) }
})

async function addSubscription() {
  adding.value = true
  try {
    await axios.post('/api/subscription/create', newSub.value)
    message.success('订阅创建成功')
    showAdd.value = false
    const res = await axios.get('/api/subscription/list')
    subscriptions.value = res.data
  } catch (e) {
    message.error(e.response?.data?.detail || '创建失败')
  } finally {
    adding.value = false
  }
}

async function checkNow(id) {
  try {
    await axios.post(`/api/subscription/${id}/check`)
    message.success('已触发检查')
  } catch (e) { message.error('检查失败') }
}

async function toggleSub(sub) {
  await axios.put(`/api/subscription/${sub.id}`, { enabled: !sub.enabled })
  sub.enabled = !sub.enabled
}

async function deleteSub(id) {
  await axios.delete(`/api/subscription/${id}`)
  subscriptions.value = subscriptions.value.filter(s => s.id !== id)
  message.success('已删除')
}
</script>
