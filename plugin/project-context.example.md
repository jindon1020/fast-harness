# 项目上下文配置

> 安装 fast-harness 后，复制此文件为 `project-context.md` 并根据实际项目填写。
> 或运行 `.ether/configure.sh` 交互式生成。
> 此文件被所有 Agent 和 Command 统一引用，修改一处全局生效。

## 基本信息

- **项目名称**: my-project
- **项目路径**: 当前工作目录（Workspace 根目录）
- **技术栈**: Python 3.11 / FastAPI / SQLModel / MySQL
- **API 前缀**: /api

## 目录结构

```
app/
├── routers/     # API 路由（入口层）
├── services/    # 业务逻辑层
├── schemas/     # 请求/响应模型
├── dao/         # 数据访问层
├── models/      # 数据库模型
├── gateways/    # 外部服务集成
└── config/      # 配置文件
tests/
├── {branch}/    # 按 Git 分支组织测试
.ai/
├── design/      # 设计文档
├── implement/   # implement 流水线文件
├── fix/         # fix 流水线文件
├── modify/      # modify 流水线文件
└── refactor/    # refactor 流水线文件
```

## 分层架构约定

```
routers/    ← 入口层，只做请求解析与响应封装
    ↓
services/   ← 业务逻辑层，编排 DAO/Gateway
    ↓
dao/        ← 数据访问层，只做 CRUD
models/     ← 数据库模型，纯数据定义
schemas/    ← 请求/响应契约，纯数据定义
gateways/   ← 外部服务调用
config/     ← 配置读取
utils/      ← 纯工具函数
```

依赖方向：只允许向下引用，严禁向上/跨层引用。

## 本地开发环境

- **虚拟环境激活**: `source .venv/bin/activate`
- **开发服务器**: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- **健康检查**: `GET http://localhost:8000/healthz`

## 编码约定

- **响应格式**: `{"code": 0, "data": ..., "message": "success"}`
- **错误处理**: 抛出 `BizException`，全局 handler 捕获
- **日志**: 使用 `loguru` 的 `logger`，禁止 `print()` 和标准库 `logging`
- **注释语言**: 中文
- **Commit 格式**: `<类型>: <简短描述>`（中文）

## 基础设施

> 中间件连接配置（MySQL、Redis、Kafka 等）在 `.ether/config/infrastructure.json` 中管理。
> Agent 通过 Connector Skills（db-connector、redis-connector 等）读取配置并连接。
