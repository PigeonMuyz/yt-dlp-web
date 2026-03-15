<template>
  <div class="setup-container">
    <div class="setup-card">
      <h1 class="setup-title">📺 yt-dlp Web</h1>
      <p class="setup-subtitle">管理员登录</p>

      <n-form-item label="用户名">
        <n-input v-model:value="username" placeholder="admin" @keyup.enter="doLogin" />
      </n-form-item>
      <n-form-item label="密码">
        <n-input v-model:value="password" type="password" placeholder="密码" @keyup.enter="doLogin" />
      </n-form-item>
      <n-button type="primary" block :loading="loading" @click="doLogin" style="margin-top: 8px;">
        登录
      </n-button>
      <n-alert v-if="error" type="error" style="margin-top: 16px;">{{ error }}</n-alert>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const username = ref('admin')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function doLogin() {
  loading.value = true
  error.value = ''
  try {
    const res = await axios.post('/api/auth/login', {
      username: username.value,
      password: password.value,
    })
    localStorage.setItem('token', res.data.token)
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>
