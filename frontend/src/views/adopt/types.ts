/** 绿地认建认养：台账、流转动作与认养人名册共用的类型定义。 */

export type AdoptStatus = '待签约' | '履约中' | '已到期'

export interface AdoptHistoryItem {
  时间: string
  动作: string
  经办人: string
  原状态: string
  新状态: string
  说明: string
}

export interface AdoptEntry {
  id: number
  status: AdoptStatus
  pending: boolean
  abnormal: boolean
  违约次数: number
  认养编号: string
  绿地编号: string
  绿地名称: string
  所属区域: string
  认养类型: string
  认养人姓名: string
  联系方式: string
  认养期限: string
  养护义务: string
  签约日期: string
  经办人: string
  history: AdoptHistoryItem[]
  [key: string]: unknown
}

export interface AdoptPerson {
  认养人姓名: string
  联系方式: string
  认养块数: number
  认养编号: string
  认养绿地: string
  状态汇总: string
  存在违约: boolean
  adoption_ids: number[]
}

export interface ActionResponse {
  ok: boolean
  message: string
  entry: AdoptEntry | null
}

export const SIGN_ACTION = '签约'
export const BREACH_ACTION = '标记违约'
export const REAGREE_ACTION = '重新约定'
export const EXPIRE_ACTION = '办理到期'

export type DialogAction =
  | typeof SIGN_ACTION
  | typeof BREACH_ACTION
  | typeof REAGREE_ACTION
  | typeof EXPIRE_ACTION
export type DialogMode = 'create' | DialogAction

/** 按当前状态给出可执行动作；最终能否执行以后端状态机为准。 */
export function availableActions(entry: AdoptEntry): DialogAction[] {
  if (entry.status === '待签约') return [SIGN_ACTION]
  if (entry.status === '履约中') {
    return entry.abnormal ? [REAGREE_ACTION] : [BREACH_ACTION, EXPIRE_ACTION]
  }
  return []
}
