<template>
  <div class="modal-mask" @click.self="emit('close')">
    <div class="modal-box">
      <h3>登记认养</h3>
      <p class="modal-desc">
        同一块绿地已有在途认养（待签约或履约中）时会被当场退回；联系方式、养护义务可稍后补全，但签约前必须填写完整。
      </p>

      <label class="form-row">
        <span>绿地编号 *</span>
        <input v-model="form.绿地编号" placeholder="例如：PLOT-0201" />
      </label>
      <label class="form-row">
        <span>绿地名称 *</span>
        <input v-model="form.绿地名称" placeholder="例如：朝阳社区公园" />
      </label>
      <label class="form-row">
        <span>认养人 *</span>
        <input v-model="form.认养人" placeholder="认养人姓名或单位名称" />
      </label>
      <label class="form-row">
        <span>联系方式</span>
        <input v-model="form.联系方式" placeholder="认养人联系电话" />
      </label>
      <label class="form-row">
        <span>认养方式</span>
        <select v-model="form.认养方式">
          <option value="认养">认养</option>
          <option value="认建">认建</option>
        </select>
      </label>
      <label class="form-row">
        <span>养护义务</span>
        <textarea v-model="form.养护义务" rows="2" placeholder="例如：每周浇水两次、每月除草一次"></textarea>
      </label>
      <label class="form-row">
        <span>履约期限</span>
        <input v-model="form.履约期限" placeholder="例如：2026-10-01 至 2027-09-30" />
      </label>

      <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

      <div class="modal-actions">
        <button class="btn primary" type="button" :disabled="submitting" @click="submit">
          {{ submitting ? '提交中…' : '确认登记' }}
        </button>
        <button class="btn ghost" type="button" @click="emit('close')">取消</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'

import { request } from '@/api/client'

import type { ActionResult } from './types'

const props = defineProps<{
  operator: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'done', message: string): void
}>()

const form = reactive({
  绿地编号: '',
  绿地名称: '',
  认养人: '',
  联系方式: '',
  认养方式: '认养',
  养护义务: '',
  履约期限: '',
})

const submitting = ref(false)
const errorMessage = ref('')

async function submit() {
  if (submitting.value) return
  submitting.value = true
  errorMessage.value = ''
  try {
    const response = await request('/api/adoption', {
      method: 'POST',
      body: JSON.stringify({ values: { ...form, 经办人: props.operator } }),
    })
    const result = (await response.json()) as ActionResult
    if (!response.ok || !result.ok) {
      errorMessage.value = result.message || '登记未生效，请稍后重试'
      return
    }
    emit('done', result.message)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '登记失败'
  } finally {
    submitting.value = false
  }
}
</script>
