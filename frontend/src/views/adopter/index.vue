<template>
  <section class="page" data-module="adopter">
    <header class="page-head">
      <div>
        <h2>认养人名录</h2>
        <p class="page-desc">名录实时读取认建认养台账，与台账同源：台账里登记、签约、违约、到期，这里同步可见。</p>
      </div>
      <div class="page-actions">
        <button class="btn" type="button" @click="reload">刷新</button>
      </div>
    </header>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.认养人">
          <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length" class="empty-state">暂无认养人，可先在认建认养台账登记</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ rows.length }} 位认养人</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { request } from '@/api/client'

type AdopterRow = Record<string, string | number>

const columns = ['认养人', '联系方式', '认养记录数', '履约中', '违约中', '已到期', '最近认养编号']

const rows = ref<AdopterRow[]>([])
const errorMessage = ref('')

async function reload() {
  errorMessage.value = ''
  try {
    const response = await request('/api/adoption/adopters')
    if (!response.ok) throw new Error('认养人名录读取失败')
    const payload = (await response.json()) as { items: AdopterRow[] }
    rows.value = payload.items ?? []
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '认养人名录读取失败'
  }
}

onMounted(reload)
</script>
