<template>
  <section class="page" data-module="adoption">
    <header class="page-head">
      <div>
        <h2>绿地认建认养管理</h2>
        <p class="page-desc">
          认养状态按待签约、履约中、已到期依次流转，不允许跳级；违约需重新约定后恢复履约，每次变更都记录时间与经办人。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="showCreate = true">登记认养</button>
        <button class="btn" type="button" @click="exportRows">导出认养台账清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label class="filter-item">
        <span>关键字</span>
        <input v-model="keyword" placeholder="认养编号 / 绿地编号 / 认养人" />
      </label>
      <label class="filter-item">
        <span>认养状态</span>
        <select v-model="status">
          <option value="">全部</option>
          <option v-for="s in statuses" :key="s" :value="s">{{ s }}</option>
        </select>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>认养状态</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.id">
          <td v-for="column in columns" :key="column">{{ row[column] || '—' }}</td>
          <td>
            {{ row.status }}<span v-if="row.abnormal" class="tag danger">违约</span>
          </td>
          <td class="row-actions">
            <button class="link" type="button" @click="goDetail(row)">详情</button>
            <button
              v-for="action in availableActions(row)"
              :key="action"
              class="link"
              type="button"
              @click="openAction(row, action)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 2" class="empty-state">暂无认养记录，可先登记认养</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条认养记录</span>
      <span v-if="notice" class="ok-text">{{ notice }}</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <CreateDialog
      v-if="showCreate"
      :operator="operator"
      @close="showCreate = false"
      @done="onCreated"
    />
    <ActionDialog
      v-if="activeRow && activeAction"
      :record="activeRow"
      :action="activeAction"
      :operator="operator"
      @close="closeAction"
      @done="onActionDone"
    />
  </section>
</template>

<script setup lang="ts">
import { nextTick, onActivated, onDeactivated, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { request } from '@/api/client'
import { useSessionStore } from '@/stores/session'

import ActionDialog from './ActionDialog.vue'
import CreateDialog from './CreateDialog.vue'
import { availableActions } from './types'
import type { AdoptionRow } from './types'

defineOptions({ name: 'AdoptionList' })

const ENDPOINT = '/api/adoption'
const columns = ['认养编号', '绿地编号', '绿地名称', '认养人', '联系方式', '认养方式', '履约期限', '签约日期'] as const
const statuses = ['待签约', '履约中', '已到期']

const router = useRouter()
const session = useSessionStore()
const operator = session.operator

const rows = ref<AdoptionRow[]>([])
const total = ref(0)
const keyword = ref('')
const status = ref('')
const errorMessage = ref('')
const notice = ref('')
const stats = ref([
  { label: '待签约', value: 0 },
  { label: '履约中', value: 0 },
  { label: '违约中', value: 0 },
  { label: '已到期', value: 0 },
])

const showCreate = ref(false)
const activeRow = ref<AdoptionRow | null>(null)
const activeAction = ref('')

// 列表 → 详情 → 返回：组件被 KeepAlive 缓存，筛选条件不丢；
// 滚动位置在离开时记下、回来时恢复，浏览器前进后退与页内返回都生效。
let savedScrollY = 0
let firstActivation = true

onMounted(() => {
  void refresh()
})

onActivated(async () => {
  if (firstActivation) {
    firstActivation = false
    return
  }
  await refresh()
  await nextTick()
  window.scrollTo({ top: savedScrollY })
})

onDeactivated(() => {
  savedScrollY = window.scrollY
})

async function refresh() {
  await Promise.all([reload(), loadStats()])
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams()
  if (keyword.value.trim()) query.set('keyword', keyword.value.trim())
  if (status.value) query.set('status', status.value)
  query.set('size', '200')
  try {
    const response = await request(`${ENDPOINT}?${query.toString()}`)
    if (!response.ok) throw new Error('认养列表读取失败')
    const payload = (await response.json()) as { items: AdoptionRow[]; total: number }
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '认养列表读取失败'
  }
}

async function loadStats() {
  try {
    const response = await request(`${ENDPOINT}?size=200`)
    if (!response.ok) return
    const payload = (await response.json()) as { items: AdoptionRow[] }
    const items = payload.items ?? []
    stats.value = [
      { label: '待签约', value: items.filter((row) => row.status === '待签约').length },
      { label: '履约中', value: items.filter((row) => row.status === '履约中').length },
      { label: '违约中', value: items.filter((row) => row.abnormal).length },
      { label: '已到期', value: items.filter((row) => row.status === '已到期').length },
    ]
  } catch {
    // 统计卡片失败不阻塞列表
  }
}

function resetFilters() {
  keyword.value = ''
  status.value = ''
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function goDetail(row: AdoptionRow) {
  void router.push({ name: 'adoption-detail', params: { id: row.id } })
}

function openAction(row: AdoptionRow, action: string) {
  activeRow.value = row
  activeAction.value = action
}

function closeAction() {
  activeRow.value = null
  activeAction.value = ''
}

async function onActionDone(message: string) {
  closeAction()
  notice.value = message
  await refresh()
}

async function onCreated(message: string) {
  showCreate.value = false
  notice.value = message
  await refresh()
}
</script>
