export interface HistoryEntry {
  时间: string
  经办人: string
  动作: string
  说明: string
}

export interface AdoptionRow {
  id: number
  status: string
  pending: boolean
  abnormal: boolean
  违约次数: number
  认养编号: string
  绿地编号: string
  绿地名称: string
  认养人: string
  联系方式: string
  认养方式: string
  养护义务: string
  履约期限: string
  签约日期: string
  history: HistoryEntry[]
}

export interface ActionResult {
  ok: boolean
  message: string
  entry: AdoptionRow | null
}

/** 各状态下允许执行的动作：待签约只能签约，履约中按是否违约分流，已到期只读。 */
export function availableActions(row: Pick<AdoptionRow, 'status' | 'abnormal'>): string[] {
  if (row.status === '待签约') return ['签约']
  if (row.status === '履约中') return row.abnormal ? ['重新约定'] : ['标记违约', '到期确认']
  return []
}
