<template>
  <section class="page" data-module="adopt-detail">
    <header class="page-head">
      <div>
        <h2>认养详情 <span class="muted-inline">{{ entry?.认养编号 }}</span></h2>
        <p class="page-desc">同一块绿地的认养全貌：基本信息、当前状态与每一次变更的时间、经办人。</p>
      </div>
      <div class="page-actions">
        <button class="btn" type="button" @click="goBack">返回台账列表</button>
      </div>
    </header>

    <p v-if="message" :class="messageOk ? 'ok-text' : 'error-text'">{{ message }}</p>

    <template v-if="entry">
      <div class="detail-status">
        <span class="status-tag" :class="statusClass">{{ entry.status }}</span>
        <span v-if="entry.abnormal" class="breach-tag">违约待重新约定</span>
        <span class="muted-inline">累计违约 {{ entry.违约次数 }} 次</span>
      </div>

      <div class="detail-grid">
        <article v-for="field in infoFields" :key="field" class="info-card">
          <span class="stat-label">{{ field }}</span>
          <strong class="info-value">{{ entry[field] || '—' }}</strong>
        </article>
      </div>

      <div class="detail-actions">
        <button
          v-for="action in availableActions(entry)"
          :key="action"
          class="btn primary"
          type="button"
          @click="openDialog(action)"
        >
          {{ action }}
        </button>
        <span v-if="!availableActions(entry).length" class="muted-inline">
          {{ entry.status === '已到期' ? '认养已到期归档，如需继续认养请重新登记' : '当前没有可执行动作' }}
        </span>
      </div>

      <h3 class="timeline-title">流转记录（{{ entry.history.length }} 次变更）</h3>
      <table class="data-table">
        <thead>
          <tr>
            <th>时间</th><th>动作</th><th>经办人</th><th>原状态</th><th>新状态</th><th>说明</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, idx) in [...entry.history].reverse()" :key="idx">
            <td>{{ item.时间 }}</td>
            <td>{{ item.动作 }}</td>
            <td>{{ item.经办人 }}</td>
            <td>{{ item.原状态 }}</td>
            <td>{{ item.新状态 }}</td>
            <td>{{ item.说明 || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </template>

    <p v-else-if="!loading" class="empty-state">认养记录不存在或已归档</p>

    <ActionDialog
      v-if="dialogMode"
      :mode="dialogMode"
      :entry="entry"
      @close="dialogMode = ''"
      @submit="handleSubmit"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { request } from '@/api/client'

import ActionDialog from './ActionDialog.vue'
import { adoptListRevision } from './revision'
import { availableActions, type ActionResponse, type AdoptEntry, type AdoptStatus, type DialogAction } from './types'

const route = useRoute()
const router = useRouter()

const entry = ref<AdoptEntry | null>(null)
const loading = ref(true)
const message = ref('')
const messageOk = ref(false)
const dialogMode = ref<DialogAction | ''>('')

const infoFields = [
  '认养编号', '绿地编号', '绿地名称', '所属区域', '认养类型',
  '认养人姓名', '联系方式', '认养期限', '签约日期', '经办人', '养护义务',
]

const statusClass = computed(() => {
  const map: Record<AdoptStatus, string> = {
    待签约: 'st-pending', 履约中: 'st-active', 已到期: 'st-expired',
  }
  return entry.value ? map[entry.value.status] : ''
})

function flash(ok: boolean, text: string) {
  messageOk.value = ok
  message.value = text
}

function openDialog(action: DialogAction) {
  dialogMode.value = action
}

async function loadEntry() {
  loading.value = true
  message.value = ''
  try {
    const response = await request(`/api/adopt/${route.params.id}`)
    if (!response.ok) throw new Error('认养记录不存在或已归档')
    entry.value = await response.json()
  } catch (error) {
    entry.value = null
    flash(false, error instanceof Error ? error.message : '认养详情读取失败')
  } finally {
    loading.value = false
  }
}

async function handleSubmit(values: Record<string, string>) {
  const action = dialogMode.value
  const valuesCopy = { ...values }
  const operator = valuesCopy._operator || '值班管理员'
  delete valuesCopy._operator
  try {
    const response = await request(`/api/adopt/${entry.value?.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { ...valuesCopy, action }, operator }),
    })
    const payload = (await response.json()) as ActionResponse
    if (!response.ok || !payload.ok) {
      flash(false, payload.message || '操作未生效，请稍后重试')
      return
    }
    dialogMode.value = ''
    flash(true, payload.message)
    adoptListRevision.bump()
    await loadEntry()
  } catch (error) {
    flash(false, error instanceof Error ? error.message : '操作失败')
  }
}

// 返回台账：router.back() 回到缓存中的列表页（筛选、分页、滚动位置都保留）。
function goBack() {
  if (window.history.state?.back) {
    router.back()
  } else {
    router.push('/adopt')
  }
}

onMounted(loadEntry)
</script>
