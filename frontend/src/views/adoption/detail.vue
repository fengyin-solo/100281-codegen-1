<template>
  <section class="page" data-module="adoption-detail">
    <header class="page-head">
      <div>
        <h2>认养详情 · {{ row?.认养编号 || `#${route.params.id}` }}</h2>
        <p class="page-desc">状态流转只进不退：待签约 → 履约中 → 已到期；每次变更的时间与经办人见下方流转记录。</p>
      </div>
      <div class="page-actions">
        <button class="btn" type="button" @click="goBack">返回列表</button>
        <button
          v-for="action in row ? availableActions(row) : []"
          :key="action"
          class="btn primary"
          type="button"
          @click="activeAction = action"
        >
          {{ action }}
        </button>
      </div>
    </header>

    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
    <p v-if="notice" class="ok-text">{{ notice }}</p>

    <template v-if="row">
      <dl class="detail-grid">
        <div v-for="field in detailFields" :key="field.label" class="detail-item">
          <dt>{{ field.label }}</dt>
          <dd>
            {{ field.value || '—' }}
            <span v-if="field.label === '认养状态' && row.abnormal" class="tag danger">违约</span>
          </dd>
        </div>
      </dl>

      <h3 class="section-title">流转记录</h3>
      <table class="data-table">
        <thead>
          <tr><th>时间</th><th>经办人</th><th>动作</th><th>说明</th></tr>
        </thead>
        <tbody>
          <tr v-for="(entry, index) in row.history" :key="index">
            <td>{{ entry.时间 }}</td>
            <td>{{ entry.经办人 }}</td>
            <td>{{ entry.动作 }}</td>
            <td>{{ entry.说明 }}</td>
          </tr>
          <tr v-if="!row.history?.length">
            <td colspan="4" class="empty-state">暂无流转记录</td>
          </tr>
        </tbody>
      </table>
    </template>

    <ActionDialog
      v-if="row && activeAction"
      :record="row"
      :action="activeAction"
      :operator="operator"
      @close="activeAction = ''"
      @done="onActionDone"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { request } from '@/api/client'
import { useSessionStore } from '@/stores/session'

import ActionDialog from './ActionDialog.vue'
import { availableActions } from './types'
import type { AdoptionRow } from './types'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const operator = session.operator

const row = ref<AdoptionRow | null>(null)
const errorMessage = ref('')
const notice = ref('')
const activeAction = ref('')

const detailFields = computed(() => {
  if (!row.value) return []
  const r = row.value
  return [
    { label: '认养编号', value: r.认养编号 },
    { label: '认养状态', value: r.status },
    { label: '绿地编号', value: r.绿地编号 },
    { label: '绿地名称', value: r.绿地名称 },
    { label: '认养人', value: r.认养人 },
    { label: '联系方式', value: r.联系方式 },
    { label: '认养方式', value: r.认养方式 },
    { label: '养护义务', value: r.养护义务 },
    { label: '履约期限', value: r.履约期限 },
    { label: '签约日期', value: r.签约日期 },
    { label: '违约次数', value: String(r.违约次数 ?? 0) },
  ]
})

async function reload() {
  errorMessage.value = ''
  try {
    const response = await request(`/api/adoption/${route.params.id}`)
    if (response.status === 404) {
      errorMessage.value = `认养记录 ${route.params.id} 不存在或已归档`
      row.value = null
      return
    }
    if (!response.ok) throw new Error('认养详情读取失败')
    row.value = (await response.json()) as AdoptionRow
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '认养详情读取失败'
  }
}

function goBack() {
  // 有上一步历史就原路返回（列表的筛选与滚动位置由 KeepAlive 保留），否则回列表页
  if (window.history.state?.back) {
    router.back()
  } else {
    void router.push({ name: 'adoption' })
  }
}

async function onActionDone(message: string) {
  activeAction.value = ''
  notice.value = message
  await reload()
}

onMounted(reload)
</script>
