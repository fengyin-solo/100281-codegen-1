<template>
  <section class="page" data-module="adopt-people">
    <header class="page-head">
      <div>
        <h2>认养人名册</h2>
        <p class="page-desc">本页不单独登记认养人，名册由认养台账实时汇总——台账里认养人、违约状态怎么变，这里就怎么显示，两处始终是同一份。</p>
      </div>
      <div class="page-actions">
        <RouterLink class="btn" to="/adopt">返回认养台账</RouterLink>
      </div>
    </header>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="person in people" :key="`${person.认养人姓名}-${person.联系方式}`" :class="{ 'row-abnormal': person.存在违约 }">
          <td>{{ person.认养人姓名 }}</td>
          <td>{{ person.联系方式 || '—' }}</td>
          <td>{{ person.认养块数 }}</td>
          <td>{{ person.认养编号 }}</td>
          <td>{{ person.认养绿地 }}</td>
          <td>
            <span :class="person.存在违约 ? 'breach-tag' : 'status-tag st-active'">{{ person.状态汇总 }}</span>
          </td>
          <td class="row-actions">
            <RouterLink
              v-for="aid in person.adoption_ids"
              :key="aid"
              class="link"
              :to="`/adopt/${aid}`"
            >{{ aid }}</RouterLink>
          </td>
        </tr>
        <tr v-if="!people.length">
          <td :colspan="columns.length" class="empty-state">名册暂无认养人，签约后自动出现在这里</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ people.length }} 位认养人（数据来源：认养台账）</span>
      <span v-if="message" class="error-text">{{ message }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { request } from '@/api/client'

import type { AdoptPerson } from './types'

const columns = ['认养人姓名', '联系方式', '认养块数', '认养编号', '认养绿地', '状态汇总', '台账记录']
const people = ref<AdoptPerson[]>([])
const message = ref('')

onMounted(async () => {
  try {
    const response = await request('/api/adopt/people')
    if (!response.ok) throw new Error('认养人名册读取失败')
    const payload = await response.json()
    people.value = payload.items ?? []
  } catch (error) {
    message.value = error instanceof Error ? error.message : '认养人名册读取失败'
  }
})
</script>
