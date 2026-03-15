<template>
  <div class="setup-container">
    <div class="setup-card">
      <h1 class="setup-title">📺 yt-dlp Web</h1>
      <p class="setup-subtitle">首次启动配置</p>

      <n-steps :current="step" size="small" style="margin-bottom: 32px;">
        <n-step title="数据库" />
        <n-step title="Redis" />
        <n-step title="管理员" />
      </n-steps>

      <!-- Step 1: PostgreSQL -->
      <div v-if="step === 1">
        <h3 class="section-title" style="border: none; margin-top: 0;">PostgreSQL 配置</h3>
        <n-alert type="info" style="margin-bottom: 16px;">
          可连接已有的 PostgreSQL 实例，或使用 Docker Compose 内置的。
        </n-alert>
        <div class="form-row">
          <n-form-item label="主机">
            <n-input v-model:value="form.db_host" placeholder="localhost" />
          </n-form-item>
          <n-form-item label="端口">
            <n-input-number v-model:value="form.db_port" :min="1" :max="65535" />
          </n-form-item>
        </div>
        <div class="form-row">
          <n-form-item label="数据库名">
            <n-input v-model:value="form.db_name" placeholder="ytdlp_web" />
          </n-form-item>
        </div>
        <div class="form-row">
          <n-form-item label="用户名">
            <n-input v-model:value="form.db_user" placeholder="ytdlp" />
          </n-form-item>
          <n-form-item label="密码">
            <n-input v-model:value="form.db_password" type="password" placeholder="密码" />
          </n-form-item>
        </div>
        <n-button type="primary" block @click="step = 2" style="margin-top: 12px;">
          下一步
        </n-button>
      </div>

      <!-- Step 2: Redis -->
      <div v-if="step === 2">
        <h3 class="section-title" style="border: none; margin-top: 0;">Redis 配置</h3>
        <div class="form-row">
          <n-form-item label="主机">
            <n-input v-model:value="form.redis_host" placeholder="localhost" />
          </n-form-item>
          <n-form-item label="端口">
            <n-input-number v-model:value="form.redis_port" :min="1" :max="65535" />
          </n-form-item>
        </div>
        <div class="form-row">
          <n-form-item label="DB 编号">
            <n-input-number v-model:value="form.redis_db" :min="0" :max="15" />
          </n-form-item>
          <n-form-item label="密码（可选）">
            <n-input v-model:value="form.redis_password" type="password" placeholder="无密码留空" />
          </n-form-item>
        </div>
        <div style="display: flex; gap: 12px; margin-top: 12px;">
          <n-button @click="step = 1" style="flex: 1;">上一步</n-button>
          <n-button type="primary" @click="step = 3" style="flex: 1;">下一步</n-button>
        </div>
      </div>

      <!-- Step 3: Admin -->
      <div v-if="step === 3">
        <h3 class="section-title" style="border: none; margin-top: 0;">管理员账号</h3>
        <n-form-item label="管理员密码">
          <n-input v-model:value="form.admin_password" type="password" placeholder="设置管理员密码" />
        </n-form-item>
        <n-form-item label="确认密码">
          <n-input v-model:value="confirmPassword" type="password" placeholder="再次输入" />
        </n-form-item>
        <div style="display: flex; gap: 12px; margin-top: 12px;">
          <n-button @click="step = 2" style="flex: 1;">上一步</n-button>
          <n-button type="primary" @click="doSetup" :loading="loading" style="flex: 1;">
            完成配置
          </n-button>
        </div>
      </div>

      <n-alert v-if="error" type="error" style="margin-top: 16px;">{{ error }}</n-alert>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const step = ref(1)
const loading = ref(false)
const error = ref('')
const confirmPassword = ref('')

const form = ref({
  db_host: 'postgres',
  db_port: 5432,
  db_name: 'ytdlp_web',
  db_user: 'ytdlp',
  db_password: '',
  redis_host: 'redis',
  redis_port: 6379,
  redis_db: 0,
  redis_password: '',
  admin_password: '',
})

async function doSetup() {
  if (form.value.admin_password !== confirmPassword.value) {
    error.value = '两次密码不一致'
    return
  }
  if (form.value.admin_password.length < 4) {
    error.value = '密码至少 4 位'
    return
  }

  loading.value = true
  error.value = ''
  try {
    const res = await axios.post('/api/setup', form.value)
    if (res.data.success) {
      alert('初始化完成！请重启 Docker 容器后登录。')
      router.push('/login')
    }
  } catch (e) {
    error.value = e.response?.data?.error || '配置失败'
  } finally {
    loading.value = false
  }
}
</script>
