# 园林绿化养护管理平台

面向城市园林绿化植物的栽植养护、修剪造型、病虫害防治、灌溉施肥与绿地巡查的一体化绿化管理后台。

这是一个前后端分离的管理平台：前端 Vue 3 + Vite + TypeScript，后端 FastAPI（Python）。
两边各自独立启动，前端 dev server 已关掉自动打开页面，启动后按终端打印的地址手工打开。

## 目录结构

```text
.
├── frontend/                 Vue 3 + Vite + TypeScript 前端
│   ├── src/views/            每个业务模块一个页面
│   ├── src/api/              统一请求封装
│   ├── src/stores/           会话与筛选状态
│   └── vite.config.ts        dev server 配置（open: false）
├── backend/                  FastAPI（Python） 后端
│   ├── app/routers/          每个业务模块一组接口
│   ├── app/services/         业务规则与状态流转
│   └── app/store.py          内存数据仓库与示例数据
├── .gitignore
└── docker-compose.yml
```

## 启动

### 后端

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
./run.sh
```

健康检查：`curl http://127.0.0.1:8000/api/health`

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端默认监听 `http://127.0.0.1:5173/`，dev server 不会自动打开浏览器，
需要自己访问。`/api` 由 vite 代理到后端 `http://127.0.0.1:8000`。

## 业务模块

| 模块 | 目录 | 业务对象 | 主要字段 |
| --- | --- | --- | --- |
| 绿地台账 | `plot` | 绿地 | 绿地编号、绿地名称、所属区域 |
| 乔木管理 | `tree` | 乔木 | 树木编号、树种名称、胸径 |
| 灌木管理 | `shrub` | 灌木 | 灌木编号、品种名称、栽植面积 |
| 草坪管理 | `lawn` | 草坪 | 草坪编号、草种类型、草坪面积 |
| 花卉造景 | `flower` | 花卉造景 | 造景编号、造景主题、花卉品种 |
| 病虫害防治 | `pest` | 防治记录 | 防治编号、受害植物、病虫种类 |
| 灌溉作业 | `irrigation` | 灌溉任务 | 灌溉编号、灌溉区域、灌溉方式 |
| 施肥作业 | `fertilize` | 施肥记录 | 施肥编号、施肥区域、肥料类型 |
| 修剪造型 | `prune` | 修剪任务 | 修剪编号、修剪对象、修剪类型 |
| 绿地巡查 | `patrol` | 巡查记录 | 巡查编号、巡查区域、巡查日期 |
| 杂草清除 | `weed` | 除草任务 | 除草编号、除草区域、杂草种类 |
| 树木支撑 | `support` | 支撑设施 | 支撑编号、所属树木、支撑方式 |
| 苗木移植 | `transplant` | 移植记录 | 移植编号、移植树种、移植数量 |
| 园建设施 | `facility` | 园建设施 | 设施编号、设施名称、设施类型 |
| 园林机械 | `equipment` | 园林机械 | 机械编号、机械名称、规格型号 |
| 苗木基地 | `seedling` | 苗圃 | 苗圃编号、苗圃名称、苗圃面积 |
| 水体养护 | `waterbody` | 水体 | 水体编号、水体类型、水体面积 |
| 名木古树 | `code` | 名木古树 | 古树编号、树种、树龄 |
| 市民热线 | `complaint` | 热线记录 | 记录编号、来电人、来电内容 |
| 季度养护方案 | `seasonplan` | 养护方案 | 方案编号、方案季度、覆盖绿地 |
| 绿地认建认养 | `adopt` | 认养记录/认养人 | 认养编号、认养绿地、认养人、养护义务 |

## 约定

- 每个模块的前端页面在 `frontend/src/views/<模块>/index.vue`，后端接口在
  `backend/app/routers/<模块>.py`，业务规则在 `backend/app/services/<模块>.py`。
- 列表接口统一返回 `{ items, total, page, size }`，动作接口统一返回 `{ ok, message }`。
- 状态流转只允许在 `app/services` 里改，路由层不做业务判断。

### 绿地认建认养（adopt）

认建认养是一条可追的流转，规则都收在 `backend/app/services/adopt.py`：

- 状态只有 待签约 → 履约中 → 已到期，按动作依次推进，不允许跳级；违约不是独立
  状态：履约中「标记违约」后仍回到履约中（挂违约标志），经「重新约定」清除。
- 每次变更（登记、签约、违约、重新约定、到期）都在记录的 `history` 里追加一条
  时间、经办人、原状态、新状态与说明。
- 同一块绿地存在未到期认养（待签约或履约中）时，新登记当场退回。
- 签约必须齐全认养人姓名、联系方式、养护义务，缺项会在返回信息里逐项点名；
  同一认养人重复提交签约幂等处理，只生效一次、不重复记录。
- 认养人名册页（`/adopt-people`，接口 `GET /api/adopt/people`）不单独存数据，
  实时从认养台账汇总，两处始终是同一份。
- 台账列表页用 keep-alive 缓存，从列表进详情再返回时保留筛选条件、分页和滚动位置；
  在详情页执行过动作返回时，列表会自动刷新。
