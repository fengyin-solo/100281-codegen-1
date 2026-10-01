"""绿地认建认养接口：登记认养、签约、标记违约、重新约定、到期确认与认养人名录。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.adoption import AdoptionService

router = APIRouter(prefix="/api/adoption", tags=["绿地认建认养"])

service = AdoptionService()

STATUSES = ["待签约", "履约中", "已到期"]


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按认养编号、绿地编号或认养人检索"),
    status: str | None = Query(default=None, description="待签约、履约中、已到期"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按关键字与认养状态过滤认养台账列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/adopters")
def list_adopters() -> dict[str, Any]:
    """认养人名录：与认养台账同源，直接从台账聚合，供另一个页面读取。"""
    items = service.list_adopters()
    return {"items": items, "total": len(items)}


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出认养台账清单：返回当前台账的全量数据。"""
    items, total = service.list_entries(page=1, size=10000)
    return {"module": "adoption", "total": total, "items": items}


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条认养明细（含流转记录）；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"认养记录 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条认养；同一块绿地已有在途认养时当场退回，缺字段时说清缺哪一项。"""
    operator = str(payload.values.get("经办人") or "值班管理员")
    entry, message = service.create_entry(payload.values, operator)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message="认养已登记，待签约", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条认养执行签约、标记违约、重新约定、到期确认；越级或缺项会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    operator = str(payload.values.get("经办人") or "值班管理员")
    entry, message = service.run_action(entry_id, action, payload.values, operator)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
