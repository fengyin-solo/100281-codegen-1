<template>
  <section class="page" data-module="adopt">
    <header class="page-head">
      <div>
        <h2>绿地认建认养台账</h2>
        <p class="page-desc">认养状态只能按 待签约 → 履约中 → 已到期 依次推进；违约标记后回到履约中重新约定，每次变更都留有时间与经办人。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openDialog('create')">登记认建认养</button>
        <RouterLink class="btn" to="/adopt-people">认养人名册</RouterLink>
        <button class="btn" type="button" @click="exportRows">导出台账</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload(1)">
      <label class="filter-item">
        <span>关键字</span>
        <input v-model="keyword" placeholder="认养编号 / 绿地 / 认养人" />
      </label>
      <label class="filter-item">
        <span>认养状态</span>
        <select v-model="statusFilter">
          <option value="">全部状态</option>
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
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)" :class="{ 'row-abnormal': row.abnormal }">
          <td v-for="column in columns" :key="column">
            <template v-if="column === '认养编号'">
              <RouterLink class="link" :to="`/adopt/${row.id}`">{{ row[column] ?? '—' }}</RouterLink>
            </template>
            <template v-else>{{ row[column] || '—' }}</template>
          </td>
          <td>
            <span class="status-tag" :class="statusClass(row)">{{ row.status }}</span>
            <span v-if="row.abnormal" class="breach-tag">违约待重新约定</span>
          </td>
          <td class="row-actions">
            <button
              v-for="action in availableActions(row)"
              :key="action"
              class="link"
              type="button"
              @click="openDialog(action, row)"
            >
              {{ action }}
            </button>
            <RouterLink class="link" :to="`/adopt/${row.id}`">详情</RouterLink>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 2" class="empty-state">暂无认建认养数据，可先登记一条认养</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条认养记录</span>
      <span class="pager">
        <button class="btn" type="button" :disabled="page <= 1" @click="changePage(page - 1)">上一页</button>
        第 {{ page }} 页（每页 {{ size }} 条）
        <button class="btn" type="button" :disabled="page * size >= total" @click="changePage(page + 1)">下一页</button>
      </span>
      <span v-if="message" :class="messageOk ? 'ok-text' : 'error-text'">{{ message }}</span>
    </footer>

    <ActionDialog
      v-if="dialogMode"
      :mode="dialogMode"
      :entry="dialogEntry"
      @close="dialogMode = ''"
      @submit="handleSubmit"
    />
  </section>
</template>

<script setup lang="ts">
import { nextTick, onActivated, onDeactivated, onMounted, reactive, ref } from 'vue'

import { request } from '@/api/client'

import ActionDialog from './ActionDialog.vue'
import {
  availableActions,
  type ActionResponse,
  type AdoptEntry,
  type AdoptStatus,
  type DialogMode,
} from './types'
import { adoptListRevision } from './revision'

const ENDPOINT = '/api/adopt'
const columns = ['认养编号', '绿地编号', '绿地名称', '所属区域', '认养类型', '认养人姓名', '联系方式', '认养期限', '养护义务'] as const
const statuses: AdoptStatus[] = ['待签约', '履约中', '已到期']
const stats = reactive(
  [
    { label: '待签约', value: 0 },
    { label: '履约中', value: 0 },
    { label: '违约待重新约定', value: 0 },
    { label: '已到期', value: 0 },
  ],
)

const rows = ref<AdoptEntry[]>([])
const total = ref(0)
const page = ref(1)
const size = 10
const keyword = ref('')
const statusFilter = ref('')
const message = ref('')
const messageOk = ref(false)

const dialogMode = ref<DialogMode | ''>('')
const dialogEntry = ref<AdoptEntry | null>(null)

// keep-alive 缓存本页：从详情返回时恢复之前的滚动位置与查询条件。
let loaded = false
let savedScroll = 0

function statusClass(row: AdoptEntry): string {
  return { 待签约: 'st-pending', 履约中: 'st-active', 已到期: 'st-expired' }[row.status] ?? ''
}

function flash(ok: boolean, text: string) {
  messageOk.value = ok
  message.value = text
}

function openDialog(mode: DialogMode, entry: AdoptEntry | null = null) {
  dialogMode.value = mode
  dialogEntry.value = entry
}

async function handleSubmit(values: Record<string, string>) {
  message.value = ''
  const isCreate = dialogMode.value === 'create'
  const action = dialogMode.value
  const targetId = dialogEntry.value?.id
  const url = isCreate ? ENDPOINT : `${ENDPOINT}/${targetId}/actions`
  const bodyValues: Record<string, string> = { ...values }
  const operator = bodyValues._operator || '值班管理员'
  delete bodyValues._operator
  if (!isCreate) bodyValues.action = action
  const body = JSON.stringify({ values: bodyValues, operator })
  try {
    const response = await request(url, { method: 'POST', body })
    const payload = (await response.json()) as ActionResponse
    if (!response.ok || !payload.ok) {
      flash(false, payload.message || '操作未生效，请稍后重试')
      return
    }
    dialogMode.value = ''
    flash(true, payload.message)
    adoptListRevision.bump()
    await reload()
  } catch (error) {
    flash(false, error instanceof Error ? error.message : '操作失败')
  }
}

function changePage(next: number) {
  page.value = next
  void reload()
}

function resetFilters() {
  keyword.value = ''
  statusFilter.value = ''
  void reload(1)
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

async function reload(targetPage?: number) {
  if (targetPage) page.value = targetPage
  message.value = ''
  const query = new URLSearchParams()
  if (keyword.value.trim()) query.set('keyword', keyword.value.trim())
  if (statusFilter.value) query.set('status', statusFilter.value)
  query.set('page', String(page.value))
  query.set('size', String(size))
  try {
    const response = await request(`${ENDPOINT}?${query.toString()}`)
    if (!response.ok) throw new Error('认养台账读取失败')
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
    // 统计卡始终基于全量状态计数，不受当前筛选影响
    const all = await request(`${ENDPOINT}?size=200`)
    if (all.ok) {
      const full = await all.json()
      const items = (full.items ?? []) as AdoptEntry[]
      stats[0].value = items.filter((i) => i.status === '待签约').length
      stats[1].value = items.filter((i) => i.status === '履约中').length
      stats[2].value = items.filter((i) => i.abnormal).length
      stats[3].value = items.filter((i) => i.status === '已到期').length
    }
  } catch (error) {
    flash(false, error instanceof Error ? error.message : '认养台账读取失败')
  }
}

onMounted(() => {
  if (!loaded) {
    loaded = true
    void reload()
  }
})

onActivated(() => {
  // 从详情页执行过动作返回时，台账需要刷新；纯浏览返回则保留原列表与位置。
  if (adoptListRevision.consumeChanged()) void reload()
  nextTick(() => window.scrollTo(0, savedScroll))
})

onDeactivated(() => {
  savedScroll = window.scrollY
})
</script>
