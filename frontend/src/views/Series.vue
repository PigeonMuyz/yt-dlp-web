<template>
  <div>
    <div class="page-header">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
          <h1 class="page-title">我的剧集</h1>
          <p class="page-subtitle">手动组建系列视频，按 Emby 电视剧格式存储</p>
        </div>
        <n-button type="primary" @click="showCreateModal = true" v-if="!selectedSeries">
          <template #icon><n-icon><AddOutline /></n-icon></template>
          新建剧集
        </n-button>
        <n-button v-if="selectedSeries" @click="goBack">
          <template #icon><n-icon><ArrowBackOutline /></n-icon></template>
          返回列表
        </n-button>
      </div>
    </div>

    <!-- 剧集列表 -->
    <template v-if="!selectedSeries">
      <div v-if="seriesList.length" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px;">
        <div v-for="s in seriesList" :key="s.id" class="card series-card" @click="openSeries(s.id)">
          <div style="display: flex; align-items: center; gap: 12px;">
            <div v-if="s.poster_url" class="series-poster">
              <img :src="s.poster_url" referrerpolicy="no-referrer" />
            </div>
            <div v-else class="stat-icon teal" style="width: 40px; height: 40px;">
              <n-icon size="20"><TvOutline /></n-icon>
            </div>
            <div style="flex: 1; min-width: 0;">
              <div style="font-weight: 600; font-size: 14px;">{{ s.title }}</div>
              <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">
                {{ s.episode_count }} 集 · Season {{ s.season || 1 }} · {{ s.platform === 'bilibili' ? 'B站' : 'YouTube' }}
              </div>
            </div>
            <n-tag :type="seriesStatusType[s.status]" size="small" round>
              {{ seriesStatusLabel[s.status] }}
            </n-tag>
          </div>
        </div>
      </div>

      <div v-else class="card">
        <div class="empty-state">
          <n-icon size="48" color="var(--text-muted)" style="opacity: 0.4;"><TvOutline /></n-icon>
          <p style="margin-top: 12px;">暂无剧集</p>
          <p style="font-size: 12px; margin-top: 4px; color: var(--text-muted);">将散落的视频组建成一个剧集，按 Emby 电视剧格式存储</p>
          <n-button type="primary" size="small" style="margin-top: 16px;" @click="showCreateModal = true">新建剧集</n-button>
        </div>
      </div>
    </template>

    <!-- 剧集详情 -->
    <template v-if="selectedSeries">
      <!-- 剧集元信息编辑区 -->
      <div class="card" style="margin-bottom: 16px;">
        <div style="display: flex; gap: 16px; align-items: flex-start;">
          <!-- 海报 -->
          <div class="poster-edit" @click="editSeriesInfo">
            <img v-if="detail.poster_url" :src="detail.poster_url" referrerpolicy="no-referrer" />
            <div v-else class="poster-placeholder">
              <n-icon size="24"><ImageOutline /></n-icon>
              <span style="font-size: 11px;">点击设置海报</span>
            </div>
          </div>

          <!-- 信息 -->
          <div style="flex: 1;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
              <div style="flex: 1;">
                <div style="font-size: 18px; font-weight: 700;">{{ detail.title }}
                  <n-button text size="small" @click="editSeriesInfo" style="margin-left: 6px;">
                    <n-icon size="14"><CreateOutline /></n-icon>
                  </n-button>
                </div>
                <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">
                  Season {{ detail.season || 1 }} · {{ detail.episodes?.length || 0 }} 集 ·
                  {{ detail.platform === 'bilibili' ? 'B站' : 'YouTube' }}
                </div>
                <div v-if="detail.description" style="font-size: 13px; color: var(--text-secondary); margin-top: 8px; line-height: 1.5;">
                  {{ detail.description }}
                </div>
                <div v-else style="font-size: 12px; color: var(--text-muted); margin-top: 8px; cursor: pointer;" @click="editSeriesInfo">
                  点击添加剧集描述...
                </div>
              </div>
              <div style="display: flex; gap: 8px; flex-shrink: 0;">
                <n-button type="primary" @click="downloadAll" :loading="downloading" :disabled="!detail.episodes?.length">
                  <template #icon><n-icon><CloudDownloadOutline /></n-icon></template>
                  全部下载
                </n-button>
                <n-button type="error" tertiary @click="deleteSeries">
                  <template #icon><n-icon><TrashOutline /></n-icon></template>
                </n-button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 添加单集 + 集列表 -->
      <div class="card">
        <div style="display: flex; gap: 8px; margin-bottom: 16px;">
          <n-input v-model:value="newEpUrl" type="textarea" :rows="1" placeholder="粘贴视频 URL 添加单集（支持一行一个批量添加）" style="flex: 1;" @keyup.enter.prevent="addEpisode">
            <template #prefix><n-icon><LinkOutline /></n-icon></template>
          </n-input>
          <n-button type="primary" @click="addEpisode" :loading="addingEp" style="align-self: flex-end;">添加</n-button>
        </div>

        <div v-for="ep in detail.episodes" :key="ep.id" class="task-item">
          <div style="width: 32px; text-align: center; flex-shrink: 0;">
            <span style="font-size: 18px; font-weight: 700; color: var(--primary);">{{ ep.episode_number }}</span>
          </div>
          <div class="task-thumb" v-if="ep.thumbnail">
            <img :src="ep.thumbnail" referrerpolicy="no-referrer" />
          </div>
          <div class="task-info">
            <div class="task-title" style="cursor: pointer;" @click="editEpisode(ep)">
              {{ ep.title || '未命名' }}
              <n-icon size="12" style="margin-left: 4px; opacity: 0.4;"><CreateOutline /></n-icon>
            </div>
            <div class="task-meta">
              S{{ String(detail.season || 1).padStart(2, '0') }}E{{ String(ep.episode_number).padStart(2, '0') }}
              <span v-if="ep.duration"> · {{ formatDuration(ep.duration) }}</span>
            </div>
          </div>
          <div class="task-actions">
            <n-tag :type="statusTypeMap[ep.status]" size="small" round>
              {{ statusLabels[ep.status] || ep.status }}
            </n-tag>
            <n-button size="tiny" tertiary type="error" style="margin-top: 6px;" @click="deleteEpisode(ep.id)">
              <template #icon><n-icon size="14"><TrashOutline /></n-icon></template>
            </n-button>
          </div>
        </div>

        <div v-if="!detail.episodes?.length" class="empty-state" style="padding: 40px 0;">
          <n-icon size="36" color="var(--text-muted)" style="opacity: 0.4;"><VideocamOutline /></n-icon>
          <p style="margin-top: 8px; font-size: 13px;">粘贴视频 URL 开始添加集数</p>
        </div>
      </div>
    </template>

    <!-- 创建剧集 Modal -->
    <n-modal v-model:show="showCreateModal" style="max-width: 480px; width: 90%;">
      <n-card title="新建剧集" :bordered="false" style="border-radius: 16px;" closable @close="showCreateModal = false">
        <n-form-item label="剧集标题">
          <n-input v-model:value="newTitle" placeholder="如：某UP主的故事系列" />
        </n-form-item>
        <n-form-item label="描述（可选）">
          <n-input v-model:value="newDesc" type="textarea" :rows="2" placeholder="可选描述" />
        </n-form-item>
        <div style="display: flex; gap: 12px;">
          <n-form-item label="平台" style="flex: 1;">
            <n-select v-model:value="newPlatform" :options="platformOptions" />
          </n-form-item>
          <n-form-item label="季号" style="width: 100px;">
            <n-input-number v-model:value="newSeason" :min="1" />
          </n-form-item>
        </div>
        <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px;">
          <n-button @click="showCreateModal = false">取消</n-button>
          <n-button type="primary" @click="createSeries" :loading="creating">创建</n-button>
        </div>
      </n-card>
    </n-modal>

    <!-- 编辑剧集信息 Modal -->
    <n-modal v-model:show="showEditModal" style="max-width: 480px; width: 90%;">
      <n-card title="编辑剧集信息" :bordered="false" style="border-radius: 16px;" closable @close="showEditModal = false">
        <n-form-item label="剧集标题">
          <n-input v-model:value="editTitle" />
        </n-form-item>
        <n-form-item label="剧集描述">
          <n-input v-model:value="editDesc" type="textarea" :rows="3" placeholder="剧集简介..." />
        </n-form-item>
        <n-form-item label="海报 URL">
          <n-input v-model:value="editPoster" placeholder="输入海报图片 URL（可从 B站封面复制）" />
        </n-form-item>
        <div v-if="editPoster" style="text-align: center; margin-bottom: 12px;">
          <img :src="editPoster" referrerpolicy="no-referrer" style="max-height: 160px; border-radius: 8px;" />
        </div>
        <n-form-item label="季号">
          <n-input-number v-model:value="editSeason" :min="1" />
        </n-form-item>
        <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px;">
          <n-button @click="showEditModal = false">取消</n-button>
          <n-button type="primary" @click="saveSeriesInfo" :loading="saving">保存</n-button>
        </div>
      </n-card>
    </n-modal>

    <!-- 编辑单集 Modal -->
    <n-modal v-model:show="showEpEditModal" style="max-width: 400px; width: 90%;">
      <n-card title="编辑单集" :bordered="false" style="border-radius: 16px;" closable @close="showEpEditModal = false">
        <n-form-item label="集标题">
          <n-input v-model:value="editEpTitle" />
        </n-form-item>
        <n-form-item label="集号">
          <n-input-number v-model:value="editEpNum" :min="1" />
        </n-form-item>
        <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px;">
          <n-button @click="showEpEditModal = false">取消</n-button>
          <n-button type="primary" @click="saveEpisodeInfo" :loading="saving">保存</n-button>
        </div>
      </n-card>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import axios from 'axios'
import {
  AddOutline,
  ArrowBackOutline,
  TvOutline,
  CloudDownloadOutline,
  TrashOutline,
  LinkOutline,
  VideocamOutline,
  CreateOutline,
  ImageOutline,
} from '@vicons/ionicons5'

const message = useMessage()

const seriesList = ref([])
const selectedSeries = ref(null)
const detail = ref({})

// 创建
const showCreateModal = ref(false)
const newTitle = ref('')
const newDesc = ref('')
const newPlatform = ref('bilibili')
const newSeason = ref(1)
const creating = ref(false)

// 添加集
const newEpUrl = ref('')
const addingEp = ref(false)
const downloading = ref(false)

// 编辑剧集
const showEditModal = ref(false)
const editTitle = ref('')
const editDesc = ref('')
const editPoster = ref('')
const editSeason = ref(1)
const saving = ref(false)

// 海报快捷编辑
const editingPoster = ref(false)

// 编辑单集
const showEpEditModal = ref(false)
const editEpId = ref(null)
const editEpTitle = ref('')
const editEpNum = ref(1)

const platformOptions = [
  { label: 'Bilibili', value: 'bilibili' },
  { label: 'YouTube', value: 'youtube' },
]

const seriesStatusLabel = { draft: '编辑中', downloading: '下载中', completed: '已完成', partial: '部分完成' }
const seriesStatusType = { draft: 'default', downloading: 'info', completed: 'success', partial: 'warning' }

const statusLabels = {
  pending: '等待', downloading: '下载中', processing: '处理中',
  completed: '完成', failed: '失败', cancelled: '取消',
}
const statusTypeMap = {
  pending: 'default', downloading: 'info', processing: 'info',
  completed: 'success', failed: 'error', cancelled: 'warning',
}

function formatDuration(sec) {
  if (!sec) return ''
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

onMounted(loadList)

async function loadList() {
  const res = await axios.get('/api/series')
  seriesList.value = res.data
}

function goBack() {
  selectedSeries.value = null
  loadList()  // 返回时重新加载列表
}

async function createSeries() {
  if (!newTitle.value.trim()) return message.warning('请输入标题')
  creating.value = true
  try {
    const res = await axios.post('/api/series', {
      title: newTitle.value,
      description: newDesc.value,
      platform: newPlatform.value,
      season: newSeason.value,
    })
    message.success('剧集已创建')
    showCreateModal.value = false
    newTitle.value = ''
    newDesc.value = ''
    await loadList()
    openSeries(res.data.id)
  } catch (e) {
    message.error('创建失败')
  } finally {
    creating.value = false
  }
}

async function openSeries(id) {
  selectedSeries.value = id
  const res = await axios.get(`/api/series/${id}`)
  detail.value = res.data
}

// ---------- 剧集编辑 ----------

function editSeriesInfo() {
  editTitle.value = detail.value.title || ''
  editDesc.value = detail.value.description || ''
  editPoster.value = detail.value.poster_url || ''
  editSeason.value = detail.value.season || 1
  showEditModal.value = true
}

async function saveSeriesInfo() {
  saving.value = true
  try {
    await axios.put(`/api/series/${selectedSeries.value}`, {
      title: editTitle.value,
      description: editDesc.value,
      poster_url: editPoster.value,
      season: editSeason.value,
    })
    message.success('已保存')
    showEditModal.value = false
    await openSeries(selectedSeries.value)
  } catch (e) {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}

// ---------- 单集编辑 ----------

function editEpisode(ep) {
  editEpId.value = ep.id
  editEpTitle.value = ep.title || ''
  editEpNum.value = ep.episode_number
  showEpEditModal.value = true
}

async function saveEpisodeInfo() {
  saving.value = true
  try {
    await axios.put(`/api/series/${selectedSeries.value}/episodes/${editEpId.value}`, {
      title: editEpTitle.value,
      episode_number: editEpNum.value,
    })
    message.success('已保存')
    showEpEditModal.value = false
    await openSeries(selectedSeries.value)
  } catch (e) {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}

// ---------- 添加/删除集 ----------

async function addEpisode() {
  const text = newEpUrl.value.trim()
  if (!text) return
  addingEp.value = true
  try {
    const urls = text.split('\n').map(u => u.trim()).filter(u => u)
    if (urls.length > 1) {
      await axios.post(`/api/series/${selectedSeries.value}/episodes/batch`, { urls })
      message.success(`已添加 ${urls.length} 集`)
    } else {
      await axios.post(`/api/series/${selectedSeries.value}/episodes`, { video_url: urls[0] })
      message.success('已添加')
    }
    newEpUrl.value = ''
    await openSeries(selectedSeries.value)
  } catch (e) {
    message.error('添加失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    addingEp.value = false
  }
}

async function deleteEpisode(epId) {
  await axios.delete(`/api/series/${selectedSeries.value}/episodes/${epId}`)
  await openSeries(selectedSeries.value)
}

async function deleteSeries() {
  await axios.delete(`/api/series/${selectedSeries.value}`)
  message.success('已删除')
  selectedSeries.value = null
  await loadList()
}

async function downloadAll() {
  downloading.value = true
  try {
    const res = await axios.post(`/api/series/${selectedSeries.value}/download`)
    message.success(res.data.message || `已创建 ${res.data.tasks_created} 个下载任务`)
    await openSeries(selectedSeries.value)
  } catch (e) {
    message.error(e.response?.data?.detail || '下载失败')
  } finally {
    downloading.value = false
  }
}
</script>

<style scoped>
.series-card {
  cursor: pointer;
  padding: 16px;
  transition: transform 0.15s, box-shadow 0.15s;
}
.series-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}
.series-poster {
  width: 40px;
  height: 56px;
  border-radius: 6px;
  overflow: hidden;
  flex-shrink: 0;
}
.series-poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.poster-edit {
  width: 100px;
  height: 140px;
  border-radius: 10px;
  overflow: hidden;
  flex-shrink: 0;
  cursor: pointer;
  border: 2px dashed var(--border);
  transition: border-color 0.2s;
}
.poster-edit:hover { border-color: var(--primary); }
.poster-edit img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.poster-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: var(--text-muted);
}

.task-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
}
.task-item:last-child { border-bottom: none; }
.task-thumb {
  width: 100px;
  height: 56px;
  border-radius: 6px;
  overflow: hidden;
  flex-shrink: 0;
  background: var(--bg-hover);
}
.task-thumb img { width: 100%; height: 100%; object-fit: cover; }
.task-info { flex: 1; min-width: 0; }
.task-title {
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.task-meta { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }
.task-actions {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}
</style>
