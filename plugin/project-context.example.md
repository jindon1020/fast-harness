# 项目上下文配置

> 安装 fast-harness 后，请复制此文件为 `project-context.md` 并根据实际项目填写。
> 然后将 commands 文件中的 `{{占位符}}` 替换为实际值，或运行 `fast-harness/configure.sh`。

## 基本信息

- **项目名称**: my-project
- **项目路径**: /path/to/your/project
- **技术栈**: Python 3.11 / FastAPI / SQLModel / PostgreSQL
- **API 前缀**: /api

## 目录结构

```
app/
├── routers/     # API 路由
├── services/    # 业务逻辑层
├── schemas/     # 请求/响应模型
├── dao/         # 数据访问层
├── models/      # 数据库模型
├── gateways/    # 外部服务集成
└── config/      # 配置文件
tests/
├── sprint_YYYY_MM/   # 按 Sprint 组织测试
.ai/
├── design/           # 设计文档
├── implement/        # implement 流水线文件
├── fix/              # fix 流水线文件
└── refactor/         # refactor 流水线文件
```

## 本地开发环境

- **数据库**: Host: 127.0.0.1 | Port: 3306 | User: root | Pass: 123456 | DB: my-db
- **开发服务器**: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- **健康检查**: `GET http://localhost:8000/healthz`

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
