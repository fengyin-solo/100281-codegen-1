<template>
  <div class="modal-mask" @click.self="$emit('close')">
    <div class="modal">
      <header class="modal-head">
        <h3>{{ title }}</h3>
        <button class="link" type="button" @click="$emit('close')">关闭</button>
      </header>
      <p v-if="subtitle" class="modal-sub">{{ subtitle }}</p>
      <form class="modal-form" @submit.prevent="submit">
        <label v-for="field in textFields" :key="field.key" class="form-item" :class="{ required: field.required }">
          <span>{{ field.label }}</span>
          <textarea
            v-if="field.multiline"
            v-model="form[field.key]"
            rows="2"
            :placeholder="field.placeholder"
          ></textarea>
          <input v-else v-model="form[field.key]" :placeholder="field.placeholder" />
        </label>
        <label class="form-item required">
          <span>经办人</span>
          <input v-model="form._operator" placeholder="本次变更由谁经办" />
        </label>
        <footer class="modal-foot">
          <button class="btn primary" type="submit">确认提交</button>
          <button class="btn ghost" type="button" @click="$emit('close')">取消</button>
        </footer>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'

import type { AdoptEntry, DialogMode } from './types'
import { BREACH_ACTION, REAGREE_ACTION, SIGN_ACTION } from './types'

const props = defineProps<{ mode: DialogMode; entry: AdoptEntry | null }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'submit', values: Record<string, string>): void
}>()

interface FieldDef {
  key: string
  label: string
  required?: boolean
  multiline?: boolean
  placeholder?: string
}

const FIELD_DEFS: Record<DialogMode, { title: string; subtitle: string; fields: FieldDef[] }> = {
  create: {
    title: '认建认养登记',
    subtitle: '登记后进入「待签约」。同一块绿地若已有未到期认养，登记会被当场退回。',
    fields: [
      { key: '认养编号', label: '认养编号', required: true, placeholder: '如 ADPT-0006' },
      { key: '绿地编号', label: '绿地编号', required: true, placeholder: '认养的是哪块绿地' },
      { key: '绿地名称', label: '绿地名称', required: true, placeholder: '与绿地台账一致' },
      { key: '所属区域', label: '所属区域' },
      { key: '认养类型', label: '认养类型', placeholder: '认养 / 认建 / 认建认养' },
    ],
  },
  [SIGN_ACTION]: {
    title: '认养签约',
    subtitle: '认养人信息（姓名、联系方式）与养护义务齐全才能签约，缺项会被退回并点明缺哪一项。',
    fields: [
      { key: '认养人姓名', label: '认养人姓名', required: true },
      { key: '联系方式', label: '联系方式', required: true },
      { key: '认养期限', label: '认养期限', placeholder: '如 2026-10-01 至 2027-09-30' },
      { key: '养护义务', label: '养护义务', required: true, multiline: true, placeholder: '浇水、修剪、补植等具体义务与频次' },
    ],
  },
  [BREACH_ACTION]: {
    title: '标记违约',
    subtitle: '认养人未按时履行养护义务时标记；记录留在「履约中」，随后须与认养人重新约定。',
    fields: [
      { key: '违约说明', label: '违约说明', multiline: true, placeholder: '哪项养护义务未按时履行' },
    ],
  },
  [REAGREE_ACTION]: {
    title: '重新约定养护义务',
    subtitle: '与认养人重新约定养护义务后继续履约，违约标记随即清除。',
    fields: [
      { key: '养护义务', label: '重新约定的养护义务', required: true, multiline: true },
      { key: '约定说明', label: '约定说明', multiline: true },
    ],
  },
  办理到期: {
    title: '办理到期',
    subtitle: '确认认养期满、无未处理违约后归档；到期后该绿地可以重新发起认养。',
    fields: [],
  },
}

const def = FIELD_DEFS[props.mode]
const title = def.title
const subtitle = def.subtitle
const textFields = def.fields

const form = reactive<Record<string, string>>({ _operator: '' })

// 每次打开（mode/entry 变化）都回填一次：签约和重新约定默认带出原登记内容。
watch(
  () => [props.mode, props.entry?.id],
  () => {
    for (const key of Object.keys(form)) delete form[key]
    form._operator = '值班管理员'
    for (const field of textFields) {
      form[field.key] = field.key === '违约说明' || field.key === '约定说明'
        ? ''
        : String(props.entry?.[field.key] ?? '')
    }
  },
  { immediate: true },
)

function submit() {
  emit('submit', { ...form })
}
</script>
