---
name: api-skill
description: Produces minimal backend API specs as JSON with only an apis array; each request parameter includes in=query|body. Use for 后端对接文档, 接口规范, API 变更说明, or PRD-to-contract without frontend method names.
---

# 后端对接接口规范（JSON，仅 `apis`）

## 何时使用

输出**可机读**的后端协议：变更类型（added/modified/deleted）、请求参数**区分 query / body**、响应形状说明。不写前端封装名。

## 根结构（精简）

**仅**一个键：

```json
{ "apis": [ /* 接口条目 */ ] }
```

不输出 `document`、`deleted`、`integrationNotes`、`auditAgainstPdf` 等顶层块；若有补充说明用对话正文，不塞进协议 JSON。

## `apis[]` 单条

| 字段 | 必填 | 说明 |
|------|------|------|
| `method` | 是 | `GET` / `POST` / `PATCH` / `DELETE` 等 |
| `path` | 是 | 路径，不含 host |
| `params` | 否 | 请求参数对象，**每个参数必须带 `in`** |
| `items` | 是 | 本条接口的变更与响应说明 |

## `params` 与 `in`（告知后端 query / body）

- 键：参数名（英文，与真实 query key 或 body 字段名一致）。
- 值：对象，**必须包含**：
  - **`in`**：`"query"` | `"body"` — 区分 URL 查询参数与请求体字段。
  - **`required`**：boolean。
  - **`description`**：string。
- 可选：与 body 复杂结构相关的 **`type`**、**`itemSchema`**、**`sortFields`**（排序说明挂在某个 `in: "query"` 的参数对象上即可）。

约定：

- **GET**：参数一般全为 `"in": "query"`。
- **POST/PATCH**：常用 query 传 `team_id` 等，业务负载在 **`in": "body"`**。
- 若某接口无请求参数，可省略 `params` 或写 `{}`。

## `items[]`

| 字段 | 说明 |
|------|------|
| `changeType` | `added` \| `modified` \| `deleted` |
| `scope` | `query` \| `body` \| `response` \| `response.listItem` \| `query.sort`（排序维度说明时用） |
| `name` | 参数名（scope 为 query/body 时） |
| `field` | 响应字段名（scope 为 response 时） |
| 其余 | `required`、`type`、`properties`、`itemSchema`、`example`、`maxItems`、`description` 按需 |

**删除**：下线参数或字段用 `changeType: "deleted"` 写在对应接口的 `items` 里即可，不再单独维护顶层 `deleted` 数组。

## 其它约定

- JSON **key 全英文**；名称搜索参数名默认 **`keyword`**（除非需求另有命名）。
- 排序：在 `params` 里用某 key（如 `sort_by`）`in: "query"`，并在该对象内附 `sortFields` 数组说明可排序字段。

## 样例

见 [reference-template.json](reference-template.json)。

## 生成步骤（简）

1. 列出 method + path。
2. 填 `params`，**每条补 `in: "query" | "body"`**。
3. 写 `items`（added/modified/deleted + response 形状）。
