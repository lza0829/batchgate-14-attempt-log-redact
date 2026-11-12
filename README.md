# 02-batchgate（闸序）

Batchgate — 离线作业依赖编排：作业定义 → 依赖就绪检查 → 执行/失败重试 → 产出水位与对账。

与 Feedstitch（多源 Feed 归并）主链路不同，禁止做成 Feed 解析/冲突/回看换皮。

## 启动

```bash
docker compose up --build
```

| 入口 | 地址 |
| --- | --- |
| 前端 | http://localhost:5200 |
| API | http://localhost:10200 |

## 主链

配置作业与依赖 → 触发一次编排 Run → 按依赖顺序执行夹具作业 → 写入尝试记录与产出水位 → 报告对账

## 尝试详情脱敏

- 规则按 JSON 字段名匹配（任意嵌套层级，支持 `a.b` 路径），动作：**掩码**（替换为 `***`）或**丢弃**（移除字段）。
- 主路径：**写入**。编排执行时按当前规则对每条尝试详情脱敏后入库，页面展示与导出读到的均为脱敏结果。
- 页面「脱敏规则」维护规则；「尝试记录」查看脱敏结果并可导出 JSON 包（含 manifest：`attempt_count` 与尝试记录条数一致，附生效规则清单）。
- 改规则后再执行一次编排即可再验：新一次编排的详情按新规则脱敏。
- API：`GET/PUT /api/redaction-rules`，`GET /api/attempts/export?orchestration_id=`。


## 种子说明

- **ingest_orders**：无依赖，写出订单水位。
- **dim_customer**：无依赖，写出客户维表水位。
- **fact_order_daily**：依赖上两者成功且水位推进后才可执行（底座仅做“上游成功”检查，严格水位闸与重试预算留给 0-1 题）。

## 技术栈

Python 3.12 + FastAPI + SQLite；Vue 3 + Vite + Nginx。

## 0-1 切口（未实现）

`dep_gate` / `retry_budget` / `watermark_reconcile` / `sla_breach`
