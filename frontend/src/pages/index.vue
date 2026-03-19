<template>
  <v-container class="h-100 d-flex flex-column gr-4">
    <div>
      <h1 v-if="false">日志</h1>
      <div class="d-flex flex-row flex-wrap ga-3">
        <v-btn color="primary" @click="startScanning">开始扫描基质</v-btn>
        <v-select
          v-model="selectedProfile"
          :items="profileItems"
          item-title="name"
          item-value="id"
          label="选择账号"
          density="compact"
          hide-details
          style="max-width: 200px; min-width: 150px"
        >
          <template v-slot:append-item>
            <v-divider class="mb-2"></v-divider>
            <v-list-item @click="showAddProfileDialog = true">
              <template v-slot:prepend>
                <v-icon>mdi-plus</v-icon>
              </template>
              <v-list-item-title>添加新账号</v-list-item-title>
            </v-list-item>
          </template>
        </v-select>
        <v-spacer />
        <v-btn color="error" @click="clearLogs">清空日志</v-btn>
        <v-btn :color="autoScroll ? 'success' : 'warning'" @click="toggleAutoScroll">
          {{ autoScroll ? '自动滚动：开' : '自动滚动：关' }}
        </v-btn>
        <v-tooltip location="bottom" text="日志文件中的日志更全">
          <template #activator="{ props }">
            <v-badge v-bind="props" icon="mdi-help">
              <v-btn color="secondary" @click="openLogsFolder">打开日志文件目录</v-btn>
            </v-badge>
          </template>
        </v-tooltip>
      </div>
    </div>
    <v-card id="log-card" class="flex-grow-1 pa-4 overflow-auto" rounded="lg" variant="outlined">
      <pre v-if="logs.length > 0" class="logs-content text-pre-wrap h-0" v-html="logs.join('')" />
      <pre v-else>暂无日志...</pre>
    </v-card>

    <v-dialog v-model="showAddProfileDialog" max-width="400">
      <v-card>
        <v-card-title>添加新账号</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="newProfileName"
            label="账号名称"
            :rules="[v => !!v || '请输入账号名称']"
            @keyup.enter="createProfile"
          ></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" @click="showAddProfileDialog = false">取消</v-btn>
          <v-btn color="primary" @click="createProfile" :disabled="!newProfileName">创建</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script lang="ts" setup>
import { nextTick, onMounted, ref, watch, computed } from 'vue'
import { clearLogs, logs } from '@/composables/useLogs'

const autoScroll = ref(true)
const selectedProfile = ref<string>('')
const profiles = ref<Array<{id: string, name: string, weapon_count: number}>>([])
const showAddProfileDialog = ref(false)
const newProfileName = ref('')

const LAST_PROFILE_KEY = 'endfield_last_selected_profile'

const profileItems = computed(() => {
  if (profiles.value.length === 0) {
    return [{ id: 'temp', name: '临时账号(不保存数据)', weapon_count: 0 }]
  }
  return [
    { id: 'temp', name: '临时账号(不保存数据)', weapon_count: 0 },
    ...profiles.value.map(p => ({
      id: p.id,
      name: `${p.name}(${p.id.slice(0, 6)})`,
      weapon_count: p.weapon_count
    }))
  ]
})

function toggleAutoScroll() {
  autoScroll.value = !autoScroll.value
}

async function startScanning() {
  const profileId = selectedProfile.value || 'temp'
  await fetch('/api/start_scanning', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profile_id: profileId })
  })
}

function openLogsFolder() {
  fetch('/api/open_logs_folder', { method: 'POST' })
}

async function loadProfiles() {
  try {
    const response = await fetch('/api/user-profile/list')
    if (response.ok) {
      profiles.value = await response.json()
    }
  } catch (error) {
    console.error('Failed to load profiles:', error)
  }
}

async function createProfile() {
  if (!newProfileName.value) return
  
  try {
    const response = await fetch('/api/user-profile/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newProfileName.value })
    })
    
    if (response.ok) {
      const profile = await response.json()
      await loadProfiles()
      selectedProfile.value = profile.id
      showAddProfileDialog.value = false
      newProfileName.value = ''
    }
  } catch (error) {
    console.error('Failed to create profile:', error)
  }
}

watch(
  logs,
  () => {
    if (autoScroll.value) {
      nextTick(() => {
        const logsContainer = document.querySelector('#log-card')
        if (logsContainer) {
          logsContainer.scrollTop = logsContainer.scrollHeight
        }
      })
    }
  },
  { deep: true },
)

watch(selectedProfile, (newVal) => {
  if (newVal && newVal !== 'temp') {
    localStorage.setItem(LAST_PROFILE_KEY, newVal)
  } else {
    localStorage.removeItem(LAST_PROFILE_KEY)
  }
})

onMounted(async () => {
  await loadProfiles()
  
  const lastProfile = localStorage.getItem(LAST_PROFILE_KEY)
  if (lastProfile) {
    const profileExists = profiles.value.some(p => p.id === lastProfile)
    if (profileExists) {
      selectedProfile.value = lastProfile
    } else {
      selectedProfile.value = 'temp'
    }
  } else {
    selectedProfile.value = 'temp'
  }
  
  nextTick(() => {
    const logsContainer = document.querySelector('#log-card')
    if (logsContainer) {
      logsContainer.scrollTop = logsContainer.scrollHeight
      console.log('日志页面已加载，滚动到底部')
    }
  })
})
</script>

<style scoped lang="scss"></style>
