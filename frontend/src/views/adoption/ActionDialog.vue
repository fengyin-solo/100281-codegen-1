<template>
  <div class="modal-mask" @click.self="emit('close')">
    <div class="modal-box">
      <h3>{{ action }} · {{ record.认养编号 }}（{{ record.绿地名称 }}）</h3>
      <p class="modal-desc">{{ hint }}</p>

      <template v-if="action === '签约'">
        <label class="form-row">
          <span>认养人</span>
          <input :value="record.认养人" disabled />
        </label>
        <label class="form-row">
          <span>联系方式 *</span>
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
          <span>养护义务 *</span>
          <textarea v-model="form.养护义务" rows="2" placeholder="例如：每周浇水两次、每月除草一次"></textarea>
        </label>
        <label class="form-row">
          <span>履约期限 *</span>
          <input v-model="form.履约期限" placeholder="例如：2026-10-01 至 2027-09-30" />
        </label>
        <label class="form-row">
          <span>签约日期</span>
          <input v-model="form.签约日期" type="date" />
        </label>
      </template>

      <template v-else-if="action === '标记违约'">
        <label class="form-row">
          <span>违约原因</span>
          <textarea v-model="form.违约原因" rows="3" placeholder="例如：连续两周未按约浇水"></textarea>
        </label>
      </template>

      <template v-else-if="action === '重新约定'">
        <label class="form-row">
          <span>养护义务 *（重新约定）</span>
          <textarea v-model="form.养护义务" rows="2"></textarea>
        </label>
        <label class="form-row">
          <span>履约期限 *（重新约定）</span>
          <input v-model="form.履约期限" />
        </label>
      </template>

      <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

      <div class="modal-actions">
        <button class="btn primary" type="button" :disabled="submitting" @click="submit">
          {{ submitting ? '提交中…' : `确认${action}` }}
        </button>
        <button class="btn ghost" type="button" @click="emit('close')">取消</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'

import { request } from '@/api/client'

import type { ActionResult, AdoptionRow } from './types'

const props = defineProps<{
  record: AdoptionRow
  action: string
  operator: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'done', message: string): void
}>()

const HINTS: Record<string, string> = {
  签约: '签约前需补齐认养人联系方式与养护义务；缺项会被退回并说明缺哪一项。同一认养人重复提交只生效一次。',
  标记违约: '认养人未按时履行养护义务时标记违约；标记后仍属履约中，需重新约定才能继续。',
  重新约定: '违约后重新填写养护义务与履约期限，确认后解除违约标记、恢复履约中。',
  到期确认: '确认履约期满，认养状态将变为已到期。',
}

const hint = HINTS[props.action] ?? ''

const today = new Date().toISOString().slice(0, 10)
const form = reactive({
  联系方式: props.record.联系方式 || '',
  认养方式: props.record.认养方式 || '认养',
  养护义务: props.record.养护义务 || '',
  履约期限: props.record.履约期限 || '',
  签约日期: props.record.签约日期 || today,
  违约原因: '',
})

const submitting = ref(false)
const errorMessage = ref('')

async function submit() {
  if (submitting.value) return
  submitting.value = true
  errorMessage.value = ''
  try {
    const response = await request(`/api/adoption/${props.record.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({
        values: {
          action: props.action,
          经办人: props.operator,
          认养人: props.record.认养人,
          ...form,
        },
      }),
    })
    const result = (await response.json()) as ActionResult
    if (!response.ok || !result.ok) {
      errorMessage.value = result.message || '操作未生效，请稍后重试'
      return
    }
    emit('done', result.message)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '操作失败'
  } finally {
    submitting.value = false
  }
}
</script>
