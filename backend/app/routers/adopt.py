"""绿地认建认养接口：认养台账、状态流转动作与从台账派生的认养人名册。

路由层不做业务判断，校验与状态机都收在 AdoptService；这里只负责把业务拒绝
（AdoptError）翻译成统一的 { ok, message } 动作结果。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.adopt import AdoptError, AdoptService

router = APIRouter(prefix="/api/adopt", tags=["绿地认建认养"])

service = AdoptService()

LIST_FIELDS = [
    "认养编号",
    "绿地编号",
    "绿地名称",
    "所属区域",
    "认养类型",
    "认养人姓名",
    "联系方式",
    "认养期限",
    "养护义务",
    "签约日期",
]
STATUSES = ["待签约", "履约中", "已到期"]


def _operator(payload: EntryPayload) -> str | None:
    # 优先取顶层 operator；也兼容早期把经办人混在 values 里的提交方式。
    value = (payload.operator or payload.values.pop("_operator", "")).strip()
    return value or None


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按认养编号、绿地编号、绿地名称或认养人检索"),
    status: str | None = Query(default=None, description="待签约、履约中、已到期"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按关键字与状态过滤认养台账；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/people")
def list_people() -> dict[str, Any]:
    """认养人名册：数据实时来自认养台账，不另存副本，保证两处读到同一份。"""
    return {"module": "adopt", "total": len(service.list_people()), "items": service.list_people()}


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出认养台账清单：返回全量数据。"""
    items, total = service.list_entries(page=1, size=10000)
    return {"module": "adopt", "total": total, "items": items}


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条认养明细（含流转记录）；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"认养记录 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条认养：同绿地重复认养当场退回，缺必填字段时点明缺哪一项。"""
    operator = _operator(payload)
    try:
        entry = service.create_entry(payload.values, operator=operator)
    except AdoptError as exc:
        return ActionResult(ok=False, message=exc.message)
    return ActionResult(ok=True, message="认养登记成功，当前状态：待签约", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """执行签约、标记违约、重新约定、办理到期；跳级或条件不满足会被拦下并说明原因。"""
    operator = _operator(payload)
    action = str(payload.values.get("action") or "").strip()
    try:
        entry, message = service.run_action(entry_id, action, payload.values, operator=operator)
    except AdoptError as exc:
        return ActionResult(ok=False, message=exc.message)
    return ActionResult(ok=True, message=message, entry=entry)
