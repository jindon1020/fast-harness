# 重构项目上下文配置

> 此配置文件用于 AI 内容生成服务重构项目，被所有 refactor-* commands 和 agents 引用。

## 基本信息

- **项目名称**: AI 内容生成服务重构
- **项目路径**: /Users/geralt/PycharmProjects/hi-media-gen
- **重构方案**: /Users/geralt/PycharmProjects/hi-media-gen/重构执行方案.md
- **技术栈**: Python 3.11 / FastAPI / SQLModel / MySQL
- **重构时间**: 2026-04-21 开始

## 重构目标

将大单体服务拆分为三个独立服务：
1. **ai-drama-module** - 影视业务（剧本、分镜、视频生成）
2. **ai-marketing-module** - 营销业务（文案、海报、短视频）
3. **content-common-module** - 通用能力（team、project、asset 管理）

## 核心原则

- ✅ 只做文件迁移和路由调整，不改业务逻辑
- ✅ 数据库不拆分，服务间通过内网 HTTP 调用
- ✅ 分阶段验证，逐步切换流量
- ❌ 本次不做数据库拆分
- ❌ 本次不做业务逻辑重构

## 目录结构

### 原服务结构（假设）
```
old-service/
├── app/
│   ├── routers/          # API 路由（混合 drama/marketing）
│   ├── services/         # 业务逻辑层
│   ├── dao/              # 数据访问层
│   ├── models/           # 数据库模型
│   ├── schemas/          # 请求/响应模型
│   ├── gateways/         # 外部服务集成
│   └── config/           # 配置文件
├── tests/
└── requirements.txt
```

### 拆分后结构
```
ai-drama-module/
├── app/
│   ├── routers/          # Drama 相关路由
│   ├── services/         # Drama 业务逻辑
│   ├── dao/              # Drama 数据访问
│   ├── schemas/          # Drama 模型
│   ├── clients/          # 内网客户端（调用 common）
│   └── config/           # Drama 配置
└── tests/

ai-marketing-module/
├── app/
│   ├── routers/          # Marketing 相关路由
│   ├── services/         # Marketing 业务逻辑
│   ├── dao/              # Marketing 数据访问
│   ├── schemas/          # Marketing 模型
│   ├── clients/          # 内网客户端（调用 common）
│   └── config/           # Marketing 配置
└── tests/

content-common-module/
├── app/
│   ├── routers/          # 内网接口路由
│   ├── services/         # Team/Project/Asset 服务
│   ├── dao/              # 通用数据访问
│   ├── schemas/          # 通用模型
│   └── config/           # Common 配置
└── tests/
```

## 模块归属规则

### Drama 模块
**文件名包含**：
- `drama`
- `script`（剧本）
- `storyboard`（分镜）
- `video`（视频生成）

**路由路径包含**：
- `/api/drama/`
- `/api/script/`
- `/api/storyboard/`

### Marketing 模块
**文件名包含**：
- `marketing`
- `copywriting`（文案）
- `poster`（海报）
- `short_video`（短视频）

**路由路径包含**：
- `/api/marketing/`
- `/api/copywriting/`
- `/api/poster/`

### Common 模块
**文件名包含**：
- `team`
- `project`
- `asset`
- `user`（用户管理）

**路由路径包含**：
- `/api/team/`
- `/api/project/`
- `/api/asset/`

**默认归属**：无法明确分类的文件归为 common

## 配置归属规则

### 共享配置（所有模块都需要）
- `DATABASE_*` - 数据库连接
- `REDIS_*` - Redis 连接
- `LOG_*` - 日志配置
- `SECRET_KEY` - 密钥

### Drama 专属配置
- `DRAMA_*`
- `VIDEO_*`
- `SCRIPT_*`
- `STORYBOARD_*`

### Marketing 专属配置
- `MARKETING_*`
- `POSTER_*`
- `COPYWRITING_*`

### Common 专属配置
- `TEAM_*`
- `PROJECT_*`
- `ASSET_*`

## 内网调用改造规则

### 识别跨模块调用
以下调用需要改造为内网 HTTP 调用：

**Drama → Common**：
- `team_service.get_team()` → `POST /internal/team/get`
- `project_service.create_project()` → `POST /internal/project/create`
- `asset_service.upload()` → `POST /internal/asset/upload`

**Marketing → Common**：
- `team_service.get_team()` → `POST /internal/team/get`
- `project_service.create_project()` → `POST /internal/project/create`
- `asset_service.upload()` → `POST /internal/asset/upload`

### 内网客户端配置
```python
# app/clients/common_client.py
import httpx

class ContentCommonModuleClient:
    def __init__(self, base_url: str = "http://content-common-module"):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(
                connect=2.0,
                read=10.0,
                write=5.0,
                pool=1.0
            ),
            limits=httpx.Limits(
                max_connections=200,
                max_keepalive_connections=50,
                keepalive_expiry=30.0
            ),
            headers={"Content-Type": "application/json"}
        )
    
    async def get_team(self, team_id: str):
        resp = await self.client.post("/internal/team/get", json={"team_id": team_id})
        resp.raise_for_status()
        return resp.json()

# 全局单例
content_common_module_client = ContentCommonModuleClient()
```

## K8s 部署配置

### Namespace
```yaml
namespace: ai-content-ns
```

### 服务配置

| 服务 | Service Type | Port | Replicas | 访问方式 |
|------|--------------|------|----------|----------|
| ai-drama-module | LoadBalancer | 8000 | 3 | 公网 |
| ai-marketing-module | LoadBalancer | 8000 | 3 | 公网 |
| content-common-module | ClusterIP | 8000 | 3 | 仅内网 |

### 资源配置
```yaml
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 1000m
    memory: 1Gi
```

## 测试策略

### 测试优先级
- **High**: 创建、更新、删除操作
- **Medium**: 查询操作
- **Low**: 统计、日志等边缘功能

### 测试数据来源
- **优先**：从数据库提取真实数据（10 条样本/表）
- **备选**：从日志解析历史请求

### 测试覆盖目标
- 高优先级接口：100% 覆盖
- 中优先级接口：80% 覆盖
- 低优先级接口：可选

## 性能要求

### 响应时间
- 内网调用增加：< 10ms
- P99 延迟：< 200ms
- 平均延迟：< 100ms

### 错误率
- 生产环境：< 0.1%
- 灰度期间：< 0.5%

### 资源使用
- 数据库连接池：< 总配额的 80%
- CPU 使用率：< 80%
- 内存使用率：< 85%

## 灰度发布策略

### 流量切换节奏
1. **5% 流量**（3 天观察期）
   - 范围：GET 类只读接口
   - 回滚条件：错误率 > 0.5% 或 P99 延迟增加 > 50ms

2. **20% 流量**（3 天观察期）
   - 范围：所有查询接口 + 部分低风险写入接口

3. **50% 流量**（3 天观察期）
   - 范围：所有接口（包括核心写入操作）

4. **100% 流量**（1 周观察期）
   - 全量切换

### 监控指标
**实时监控**（每小时检查）：
- 接口错误率对比（新 vs 旧）
- 接口耗时 P50/P90/P99 对比
- 数据库慢查询数量
- 内网调用失败次数

**业务指标**（每天检查）：
- 用户创建 project 成功率
- 视频生成任务完成率
- 用户投诉工单数量

## 回滚策略

### 触发条件（满足任一即回滚）
- 错误率 > 1% 持续 5 分钟
- P99 延迟增加 > 100ms 持续 10 分钟
- 出现数据错误或丢失
- 核心业务功能不可用

### 回滚步骤
1. 立即将流量切回旧服务（通过 Ingress 权重调整，< 1 分钟生效）
2. 通知相关团队（研发、测试、产品）
3. 保留新服务日志和监控数据用于问题排查
4. 修复问题后重新进入灰度流程

## 验收标准

### 功能验收
- [ ] 所有现有功能测试用例通过（通过率 100%）
- [ ] 新增的内网接口测试用例通过
- [ ] 前端功能无异常（drama 和 marketing 业务）

### 性能验收
- [ ] 接口 P99 延迟增加 < 10ms
- [ ] 压测通过（500 QPS 无异常）
- [ ] 数据库连接数在合理范围（< 总配额的 80%）

### 安全验收
- [ ] algo-manager 公网不可访问（端口扫描验证）
- [ ] content-common-module 仅内网可访问
- [ ] 敏感配置（DB 密码、API key）未硬编码

### 监控验收
- [ ] 三个服务的监控面板配置完成
- [ ] 告警规则测试通过（手动触发验证）
- [ ] 日志可正常查询和过滤

## 工作流程

### 1. 迁移阶段（第 1-2 周）
```bash
# 迁移 drama 模块
/refactor-migrate /path/to/old-service target=drama

# 迁移 marketing 模块
/refactor-migrate /path/to/old-service target=marketing

# 迁移 common 模块
/refactor-migrate /path/to/old-service target=common
```

### 2. 测试阶段（第 3 周）
```bash
# 生成测试用例
/refactor-test-gen module=drama
/refactor-test-gen module=marketing
/refactor-test-gen module=common
```

### 3. 完整执行（推荐）
```bash
# 端到端执行
/refactor-execute target=drama source=/path/to/old-service
/refactor-execute target=marketing source=/path/to/old-service
/refactor-execute target=common source=/path/to/old-service
```

## 注意事项

### 数据库
- ⚠️ 数据库不拆分，三个服务共用同一个 DB
- ⚠️ 注意连接池配额分配
- ⚠️ 事务边界需要仔细验证

### 内网调用
- ⚠️ 所有跨模块调用必须改造为 HTTP 调用
- ⚠️ 添加超时和重试机制
- ⚠️ 错误处理要完善

### 配置管理
- ⚠️ 敏感配置使用环境变量
- ⚠️ 不同环境（dev/test/prod）配置分离
- ⚠️ 配置变更需要重启服务

### 部署
- ⚠️ 先部署 content-common-module（被依赖）
- ⚠️ 再部署 drama 和 marketing 模块
- ⚠️ 灰度发布严格按照节奏执行

## 联系人

- **项目负责人**: [待填写]
- **后端负责人**: [待填写]
- **测试负责人**: [待填写]
- **运维负责人**: [待填写]

## 参考文档

- [重构执行方案](/Users/geralt/PycharmProjects/hi-media-gen/重构执行方案.md)
- [Fast-Harness 设计文档](https://www.anthropic.com/engineering/harness-design-long-running-apps)
