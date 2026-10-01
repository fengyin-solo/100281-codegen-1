"""绿地认建认养业务规则：状态流转、重复认养拦截、签约校验与变更留痕都收在这里。

状态机：待签约 → 履约中 → 已到期，只允许逐级推进，不允许跳级。
违约不是独立状态：履约中的记录被标记违约后仍属履约中，必须「重新约定」
养护义务与履约期限才能解除违约标记，之后才允许确认到期。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.store import store

MODULE = "adoption"
STATUS_ORDER = ["待签约", "履约中", "已到期"]
ACTIVE_STATUSES = {"待签约", "履约中"}
ACTIONS = ["签约", "标记违约", "重新约定", "到期确认"]

# 登记认养时必须具备的字段
CREATE_REQUIRED = ["绿地编号", "绿地名称", "认养人"]
# 签约前必须补齐的字段：认养人信息 + 养护义务
SIGN_REQUIRED = ["认养人", "联系方式", "养护义务", "履约期限"]
# 违约后重新约定必须重新填写的字段
RENEW_REQUIRED = ["养护义务", "履约期限"]
# 登记/详情承载的字段全集
ENTRY_FIELDS = [
    "认养编号", "绿地编号", "绿地名称", "认养人", "联系方式",
    "认养方式", "养护义务", "履约期限", "签约日期",
]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _log(entry: dict[str, Any], action: str, operator: str, note: str) -> None:
    """每一次变更都留下时间、经办人、动作与说明。"""
    entry.setdefault("history", []).append(
        {"时间": _now(), "经办人": operator, "动作": action, "说明": note}
    )


def _blank(value: Any) -> bool:
    return not str(value or "").strip()


class AdoptionService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [
                row for row in rows
                if keyword in str(row.get("认养编号", ""))
                or keyword in str(row.get("绿地编号", ""))
                or keyword in str(row.get("认养人", ""))
            ]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def list_adopters(self) -> list[dict[str, Any]]:
        """认养人名录：直接从认养台账聚合，保证另一个页面读到的是同一份数据。"""
        directory: dict[str, dict[str, Any]] = {}
        for row in store.rows(MODULE):
            name = str(row.get("认养人") or "").strip()
            if not name:
                continue
            item = directory.setdefault(name, {
                "认养人": name,
                "联系方式": "",
                "认养记录数": 0,
                "履约中": 0,
                "违约中": 0,
                "已到期": 0,
                "最近认养编号": "",
            })
            item["认养记录数"] += 1
            if row.get("status") == "履约中":
                item["履约中"] += 1
            if row.get("abnormal"):
                item["违约中"] += 1
            if row.get("status") == "已到期":
                item["已到期"] += 1
            if row.get("联系方式"):
                item["联系方式"] = row["联系方式"]
            item["最近认养编号"] = row.get("认养编号", "")
        return list(directory.values())

    def create_entry(
        self, values: dict[str, Any], operator: str
    ) -> tuple[dict[str, Any] | None, str]:
        missing = [field for field in CREATE_REQUIRED if _blank(values.get(field))]
        if missing:
            return None, f"缺少必填字段：{'、'.join(missing)}"
        plot_code = str(values.get("绿地编号") or "").strip()
        for row in store.rows(MODULE):
            if str(row.get("绿地编号")) == plot_code and row.get("status") in ACTIVE_STATUSES:
                return None, (
                    f"绿地 {plot_code} 已存在认养记录（{row.get('认养编号')}，"
                    f"当前状态：{row.get('status')}），本次认养申请已当场退回"
                )
        rows = store.rows(MODULE)
        entry: dict[str, Any] = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry["认养编号"] = f"ADOP-{entry['id']:04d}"
        for field in ENTRY_FIELDS:
            if field == "认养编号":
                continue
            value = values.get(field)
            entry[field] = str(value).strip() if value is not None else ""
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        entry["违约次数"] = 0
        entry["history"] = []
        _log(entry, "登记认养", operator, "认养申请已登记，待补齐资料后签约")
        rows.append(entry)
        return entry, ""

    def run_action(
        self,
        entry_id: int,
        action: str,
        values: dict[str, Any],
        operator: str,
    ) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"认养记录 {entry_id} 不存在或已归档"
        if action not in ACTIONS:
            return None, f"动作「{action}」不属于认建认养可执行范围"
        if action == "签约":
            return self._sign(entry, values, operator)
        if action == "标记违约":
            return self._breach(entry, values, operator)
        if action == "重新约定":
            return self._renew(entry, values, operator)
        return self._expire(entry, operator)

    def _sign(
        self, entry: dict[str, Any], values: dict[str, Any], operator: str
    ) -> tuple[dict[str, Any] | None, str]:
        status = entry.get("status")
        if status == "已到期":
            return None, "该认养已到期结案，不能重复签约"
        if status == "履约中":
            # 幂等：同一认养人重复提交签约只生效一次，不重复写流转记录
            submitter = str(values.get("认养人") or "").strip()
            if submitter and submitter != str(entry.get("认养人")):
                return None, f"该绿地的认养人为「{entry.get('认养人')}」，他人不能重复签约"
            return entry, "该认养人已完成签约，重复提交未重复生效"
        # 待签约 → 履约中：允许用本次提交的内容补齐资料后再校验
        for field in ["联系方式", "认养方式", "养护义务", "履约期限", "签约日期"]:
            value = values.get(field)
            if not _blank(value):
                entry[field] = str(value).strip()
        missing = [field for field in SIGN_REQUIRED if _blank(entry.get(field))]
        if missing:
            return None, f"认养人信息或养护义务不完整，缺少：{'、'.join(missing)}，补齐后才能签约"
        if _blank(entry.get("签约日期")):
            entry["签约日期"] = _today()
        entry["status"] = "履约中"
        entry["pending"] = True
        _log(entry, "签约", operator, "认养签约生效，进入履约期")
        return entry, "签约成功，认养进入履约中"

    def _breach(
        self, entry: dict[str, Any], values: dict[str, Any], operator: str
    ) -> tuple[dict[str, Any] | None, str]:
        if entry.get("status") != "履约中":
            return None, f"当前状态为「{entry.get('status')}」，只有履约中的认养才能标记违约"
        if entry.get("abnormal"):
            return None, "该记录已处于违约状态，请直接重新约定养护义务"
        reason = str(values.get("违约原因") or "").strip() or "未按时履行养护义务"
        entry["abnormal"] = True
        entry["违约次数"] = int(entry.get("违约次数", 0)) + 1
        _log(entry, "标记违约", operator, f"标记违约：{reason}，需重新约定后恢复履约")
        return entry, "已标记违约，需重新约定养护义务与履约期限"

    def _renew(
        self, entry: dict[str, Any], values: dict[str, Any], operator: str
    ) -> tuple[dict[str, Any] | None, str]:
        if entry.get("status") != "履约中":
            return None, f"当前状态为「{entry.get('status')}」，只有履约中的认养才能重新约定"
        if not entry.get("abnormal"):
            return None, "该记录未处于违约状态，无需重新约定"
        missing = [field for field in RENEW_REQUIRED if _blank(values.get(field))]
        if missing:
            return None, f"重新约定需重新填写：{'、'.join(missing)}"
        entry["养护义务"] = str(values["养护义务"]).strip()
        entry["履约期限"] = str(values["履约期限"]).strip()
        entry["abnormal"] = False
        _log(entry, "重新约定", operator, "违约后重新约定养护义务与履约期限，恢复履约中")
        return entry, "已重新约定，认养恢复履约中"

    def _expire(
        self, entry: dict[str, Any], operator: str
    ) -> tuple[dict[str, Any] | None, str]:
        status = entry.get("status")
        if status == "待签约":
            return None, "认养尚未签约，不能跳过签约直接确认到期"
        if status == "已到期":
            return None, "该认养已到期结案，无需重复确认"
        if entry.get("abnormal"):
            return None, "存在未处理的违约，请先重新约定再确认到期"
        entry["status"] = "已到期"
        entry["pending"] = False
        _log(entry, "到期确认", operator, "履约期满，认养到期结案")
        return entry, "认养已到期结案"
