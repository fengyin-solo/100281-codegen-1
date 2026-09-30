"""绿地认建认养业务规则：认养状态机、重复认养拦截、签约校验与认养人名册口径。

状态主线只有 待签约 → 履约中 → 已到期 三级，只允许依次推进，不允许跳级。
违约不是第四种状态：履约中未按时履行养护义务时「标记违约」，记录留在履约中并挂
违约标志，经办人再与认养人「重新约定」养护义务后闭环。每一次状态变化都追加一条
带时间和经办人的流转记录。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.store import store

MODULE = "adopt"

STATUS_PENDING = "待签约"
STATUS_ACTIVE = "履约中"
STATUS_EXPIRED = "已到期"
STATUS_ORDER = [STATUS_PENDING, STATUS_ACTIVE, STATUS_EXPIRED]
# 未到期的认养都会占用绿地：待签约的登记同样挡住重复认养。
ACTIVE_STATUSES = {STATUS_PENDING, STATUS_ACTIVE}

ACTION_SIGN = "签约"
ACTION_BREACH = "标记违约"
ACTION_REAGREE = "重新约定"
ACTION_EXPIRE = "办理到期"
VALID_ACTIONS = {ACTION_SIGN, ACTION_BREACH, ACTION_REAGREE, ACTION_EXPIRE}

CREATE_REQUIRED = ["认养编号", "绿地编号", "绿地名称"]
# 签约时必须齐全：认养人信息（姓名、联系方式）+ 养护义务，缺一项都要在提示里点出来。
SIGN_REQUIRED = ["认养人姓名", "联系方式", "养护义务"]
ENTRY_FIELDS = [
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
    "经办人",
]

DEFAULT_OPERATOR = "值班管理员"


class AdoptError(Exception):
    """业务规则拒绝请求时抛出，message 可以直接展示给经办人。"""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _clean(values: dict[str, Any], field: str) -> str:
    return str(values.get(field) or "").strip()


class AdoptService:
    # ---------------------------------------------------------------- 列表/明细
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = list(store.rows(MODULE))
        if keyword:
            kw = keyword.strip()
            rows = [
                row
                for row in rows
                if kw in str(row.get("认养编号", ""))
                or kw in str(row.get("绿地编号", ""))
                or kw in str(row.get("绿地名称", ""))
                or kw in str(row.get("认养人姓名", ""))
            ]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    # ---------------------------------------------------------------- 认养人名册
    def list_people(self) -> list[dict[str, Any]]:
        """认养人名册不单独存一份，全部由认养台账实时汇总，保证两处读到同一份。"""
        groups: dict[tuple[str, str], dict[str, Any]] = {}
        order: list[tuple[str, str]] = []
        for row in store.rows(MODULE):
            name = str(row.get("认养人姓名") or "").strip()
            if not name:
                # 待签约、还没填认养人的登记不进入名册
                continue
            phone = str(row.get("联系方式") or "").strip()
            key = (name, phone)
            if key not in groups:
                order.append(key)
                groups[key] = {
                    "认养人姓名": name,
                    "联系方式": phone,
                    "认养块数": 0,
                    "认养编号": [],
                    "认养绿地": [],
                    "状态汇总": [],
                    "存在违约": False,
                    "adoption_ids": [],
                }
            group = groups[key]
            group["认养块数"] += 1
            group["认养编号"].append(str(row.get("认养编号") or ""))
            group["认养绿地"].append(
                f"{row.get('绿地名称', '')}（{row.get('绿地编号', '')}）"
            )
            label = "违约待重新约定" if row.get("abnormal") else str(row.get("status", ""))
            if label not in group["状态汇总"]:
                group["状态汇总"].append(label)
            group["存在违约"] = group["存在违约"] or bool(row.get("abnormal"))
            group["adoption_ids"].append(int(row.get("id", 0)))

        people: list[dict[str, Any]] = []
        for key in order:
            group = dict(groups[key])
            group["认养编号"] = "、".join(group["认养编号"])
            group["认养绿地"] = "、".join(group["认养绿地"])
            group["状态汇总"] = "、".join(group["状态汇总"])
            people.append(group)
        return people

    # ---------------------------------------------------------------- 登记
    def create_entry(
        self, values: dict[str, Any], operator: str | None = None
    ) -> dict[str, Any]:
        missing = [field for field in CREATE_REQUIRED if not _clean(values, field)]
        if missing:
            raise AdoptError(
                f"认养登记被退回：缺少必填字段（{'、'.join(missing)}），请补齐后再提交"
            )

        plot_code = _clean(values, "绿地编号")
        holder = self._active_adoption(plot_code)
        if holder is not None:
            raise AdoptError(
                f"绿地 {plot_code} 已被认养编号 {holder.get('认养编号')} 认养"
                f"（当前状态：{holder.get('status')}），同一块绿地不能重复认养，登记当场退回"
            )

        rows = store.rows(MODULE)
        entry: dict[str, Any] = {
            "id": max((int(row.get("id", 0)) for row in rows), default=0) + 1
        }
        for field in ENTRY_FIELDS:
            entry[field] = _clean(values, field)
        entry["status"] = STATUS_PENDING
        entry["pending"] = True
        entry["abnormal"] = False
        entry["违约次数"] = 0
        entry["history"] = []
        op = operator or entry["经办人"] or DEFAULT_OPERATOR
        entry["经办人"] = op
        self._record(entry, "认养登记", op, "—", STATUS_PENDING, "提交认建认养申请")
        rows.append(entry)
        return entry

    # ---------------------------------------------------------------- 动作分发
    def run_action(
        self,
        entry_id: int,
        action: str,
        values: dict[str, Any] | None = None,
        operator: str | None = None,
    ) -> tuple[dict[str, Any], str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            raise AdoptError(f"认养记录 {entry_id} 不存在或已归档")
        if action not in VALID_ACTIONS:
            raise AdoptError(f"动作「{action}」不属于绿地认建认养可执行范围")
        values = values or {}
        op = (operator or _clean(values, "经办人") or DEFAULT_OPERATOR).strip()

        if action == ACTION_SIGN:
            return self._sign(entry, values, op)
        if action == ACTION_BREACH:
            return self._mark_breach(entry, values, op)
        if action == ACTION_REAGREE:
            return self._reagree(entry, values, op)
        return self._expire(entry, values, op)

    # ---------------------------------------------------------------- 签约
    def _sign(
        self, entry: dict[str, Any], values: dict[str, Any], operator: str
    ) -> tuple[dict[str, Any], str]:
        current = str(entry.get("status"))

        # 已合并认养人在本次提交与原登记里填写的信息后再校验。
        merged = {
            field: _clean(values, field) or str(entry.get(field) or "").strip()
            for field in SIGN_REQUIRED
        }
        name, phone = merged["认养人姓名"], merged["联系方式"]

        if current == STATUS_EXPIRED:
            raise AdoptError("该认养已到期，不能再签约；如需继续认养请重新登记")
        if current == STATUS_ACTIVE:
            same_person = (
                bool(name)
                and name == str(entry.get("认养人姓名") or "").strip()
                and phone == str(entry.get("联系方式") or "").strip()
            )
            if same_person:
                # 同一认养人重复点签约：原样返回，不再产生状态变化和流转记录。
                return entry, "该认养已签约生效，同一认养人重复提交签约只生效一次，本次未重复记录"
            raise AdoptError(
                f"该绿地已由认养人{entry.get('认养人姓名') or ''}签约，不能重复签约"
            )

        missing = [field for field in SIGN_REQUIRED if not merged[field]]
        if missing:
            labels = {
                "认养人姓名": "认养人姓名（认养人信息）",
                "联系方式": "联系方式（认养人信息）",
                "养护义务": "养护义务",
            }
            raise AdoptError(
                "签约被退回：认养人信息或养护义务不完整，缺少"
                f"（{'、'.join(labels[f] for f in missing)}），请补齐后再签约"
            )

        for field in ("认养人姓名", "联系方式", "养护义务", "认养期限", "认养类型", "所属区域"):
            submitted = _clean(values, field)
            if submitted:
                entry[field] = submitted
        entry["签约日期"] = _clean(values, "签约日期") or _today()
        self._set_status(entry, STATUS_ACTIVE)
        self._record(entry, ACTION_SIGN, operator, STATUS_PENDING, STATUS_ACTIVE, "双方签约，进入履约")
        return entry, "签约成功，认养进入履约中"

    # ---------------------------------------------------------------- 违约
    def _mark_breach(
        self, entry: dict[str, Any], values: dict[str, Any], operator: str
    ) -> tuple[dict[str, Any], str]:
        self._ensure_status(entry, STATUS_ACTIVE, ACTION_BREACH)
        if entry.get("abnormal"):
            raise AdoptError("该认养已标记违约，请先与认养人重新约定养护义务，不要重复标记")
        entry["abnormal"] = True
        entry["违约次数"] = int(entry.get("违约次数", 0)) + 1
        reason = _clean(values, "违约说明") or "未按时履行养护义务"
        # 违约不改变主状态：标记后仍回到履约中，等待重新约定。
        self._record(entry, ACTION_BREACH, operator, STATUS_ACTIVE, STATUS_ACTIVE, reason)
        return entry, "已标记违约并回到履约中，请尽快与认养人重新约定养护义务"

    def _reagree(
        self, entry: dict[str, Any], values: dict[str, Any], operator: str
    ) -> tuple[dict[str, Any], str]:
        self._ensure_status(entry, STATUS_ACTIVE, ACTION_REAGREE)
        if not entry.get("abnormal"):
            raise AdoptError("当前没有待处理的违约记录，不能执行重新约定")
        new_duty = _clean(values, "养护义务")
        if new_duty:
            entry["养护义务"] = new_duty
        entry["abnormal"] = False
        remark = _clean(values, "约定说明") or "已重新约定养护义务，继续履约"
        self._record(entry, ACTION_REAGREE, operator, STATUS_ACTIVE, STATUS_ACTIVE, remark)
        return entry, "重新约定完成，认养继续按约履约"

    # ---------------------------------------------------------------- 到期
    def _expire(
        self, entry: dict[str, Any], values: dict[str, Any], operator: str
    ) -> tuple[dict[str, Any], str]:
        self._ensure_status(entry, STATUS_ACTIVE, ACTION_EXPIRE)
        if entry.get("abnormal"):
            raise AdoptError("该认养尚有违约未处理，请先重新约定养护义务后再办理到期")
        self._set_status(entry, STATUS_EXPIRED)
        self._record(entry, ACTION_EXPIRE, operator, STATUS_ACTIVE, STATUS_EXPIRED, "认养期满，台账归档")
        return entry, "认养已到期归档，该绿地可重新发起认养"

    # ---------------------------------------------------------------- 内部工具
    def _active_adoption(self, plot_code: str) -> dict[str, Any] | None:
        """返回占用该绿地的未到期认养（待签约或履约中）；没有则 None。"""
        for row in store.rows(MODULE):
            if (
                str(row.get("绿地编号") or "").strip() == plot_code
                and row.get("status") in ACTIVE_STATUSES
            ):
                return row
        return None

    def _ensure_status(
        self, entry: dict[str, Any], expected: str, action: str
    ) -> None:
        current = str(entry.get("status"))
        if current != expected:
            raise AdoptError(
                f"当前状态为「{current}」，不能执行{action}（须先处于「{expected}」）；"
                "认养状态只能按 待签约 → 履约中 → 已到期 依次推进，不允许跳级"
            )

    def _set_status(self, entry: dict[str, Any], target: str) -> None:
        entry["status"] = target
        entry["pending"] = target == STATUS_PENDING
        entry["abnormal"] = bool(entry.get("abnormal")) and target != STATUS_EXPIRED

    def _record(
        self,
        entry: dict[str, Any],
        action: str,
        operator: str,
        from_status: str,
        to_status: str,
        remark: str = "",
    ) -> None:
        history = entry.setdefault("history", [])
        history.append(
            {
                "时间": _now(),
                "动作": action,
                "经办人": operator or DEFAULT_OPERATOR,
                "原状态": from_status,
                "新状态": to_status,
                "说明": remark,
            }
        )
