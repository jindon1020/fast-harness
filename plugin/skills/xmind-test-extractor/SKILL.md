---
name: xmind-test-extractor
description: 解压并解析 .xmind 脑图文件，遍历 JSON 树提取 tc-* 测试节点，结合 task_card.json 中的 API 结构生成符合项目规范的结构化 YAML 测试数据和 pytest 集成测试代码。触发词：解析 xmind、提取测试用例、xmind 转测试、集成测试生成、从脑图生成测试。
---

# xmind 测试用例提取与集成测试生成

## Step 1：解压 xmind

xmind 文件本质是 ZIP 压缩包，解压后包含 `content.json`：

```bash
cd /tmp && unzip -o /path/to/sprint.xmind -d xmind_extract
# 预览根节点结构
python3 -c "
import json
data = json.load(open('/tmp/xmind_extract/content.json'))
print(json.dumps(data[0]['rootTopic'], indent=2))
" | head -100
```

## Step 2：理解 content.json 树结构

每个节点的关键字段：

```json
{
  "id": "节点唯一 ID",
  "title": "节点标题（tc-xxx 前缀的即为测试用例）",
  "children": {
    "attached": [ /* 子节点列表，递归同结构 */ ]
  }
}
```

树的典型层级：

```
rootTopic (Sprint 名称)
  └── 模块/功能域节点（如"团队信息"、"成员角色筛选"）
        ├── [优先级标记节点，如"P1"、"P2"]（可选）
        │     └── tc-001 具体场景描述
        └── tc-002 具体场景描述
```

## Step 3：遍历提取测试节点

用以下逻辑提取所有 `tc-*` 节点：

```python
import json, re, subprocess

def extract_all_nodes(node, parent_titles=None):
    """递归遍历，收集所有 tc-* 节点及其祖先上下文"""
    if parent_titles is None:
        parent_titles = []
    results = []
    title = node.get("title", "")
    current_path = parent_titles + [title]

    if re.match(r"tc-", title, re.IGNORECASE):
        results.append({
            "raw_title": title,
            "parent_path": parent_titles,  # 祖先节点标题列表
            "domain": parent_titles[-1] if parent_titles else "",  # 直接父节点 = 业务域
        })

    for child in node.get("children", {}).get("attached", []):
        results.extend(extract_all_nodes(child, current_path))
    return results

data = json.load(open("/tmp/xmind_extract/content.json"))
raw_cases = extract_all_nodes(data[0]["rootTopic"])
```

## Step 4：优先级识别规则

按以下优先级顺序判断，满足第一条即停止：

1. 节点标题含 `tc-p1-` / `tc-P1-` 前缀 → `p1`
2. 节点标题含 `tc-p2-` / `tc-P2-` 前缀 → `p2`
3. 节点标题含 `tc-p3-` / `tc-P3-` 前缀 → `p3`
4. 祖先节点中有标题为 `P1`、`P2`、`P3` 的节点（大小写不敏感）→ 继承该优先级
5. 无任何标记 → 默认 `p1`

## Step 5：识别并跳过纯前端节点

满足以下任一条件，将节点列入 `skipped_cases`（不生成 pytest 代码）：

- 标题包含：`前端`、`UI`、`样式`、`布局`、`动画`、`响应式`、`弹窗`、`Toast`、`复制`、`剪贴板`、`渲染`
- 描述中出现：`纯前端`、`无需后端`、`前端逻辑`
- 祖先节点标题含 `纯前端` / `前端专项`

`skipped_cases` 条目格式：
```yaml
- id: tc-skipped-001
  name: 节点标题
  reason: 纯前端 UI，无需后端接口
```

## Step 6：结合 task_card.json 填充 API 信息

读取 `task_card.json` 的 `affected_apis` 列表，对每个测试节点按以下顺序匹配 API：

1. **精确匹配**：节点标题中出现 API path 关键词（如 `teams/members`、`invite`）
2. **模块匹配**：节点所在业务域与 `affected_apis[].module` 相同
3. **语义匹配**：节点描述动词（创建/获取/更新/删除）与 `method`（POST/GET/PATCH/DELETE）对应

`affected_apis` 字段结构参考：
```json
{
  "affected_apis": [
    {
      "method": "PATCH",
      "path": "/drama-api/teams/{team_id}",
      "module": "team",
      "request_schema": {"avatar": "str", "name": "str"},
      "response_schema": {"code": 0, "result": {}}
    }
  ]
}
```

若 `task_card.json` 中无对应 API，通过 `Grep` 在项目路由文件中搜索（如 `rg "router" app/`）并人工补全。

## Step 7：输出 YAML 测试数据

**文件路径**：`tests/{branch}/{module}_test_data.yaml`

**完整格式**（严格遵循，不使用 `!custom`、`!contains` 等自定义 YAML tag）：

```yaml
# {module} 模块测试数据
# 由 integration-test-gen-agent 自动生成
# 源文件: {xmind_filename}
# Sprint: {sprint}

api_base: /drama-api
module: {module}
sprint: {sprint}

test_cases:
  - id: tc-001
    name: 管理员更新头像成功
    priority: p1
    owner: ""
    precondition: 已登录账号为管理员
    api_path: /teams/{team_id}
    method: PATCH
    request:
      body:
        avatar: "https://example.com/new_avatar.png"
    expected:
      code: 0

  - id: tc-002
    name: 上传非图片格式头像，返回错误
    priority: p1
    owner: ""
    precondition: 已登录账号为管理员
    api_path: /teams/{team_id}
    method: PATCH
    request:
      body:
        avatar: "https://example.com/avatar.exe"
    expected:
      code_not_zero: true    # 替代 !custom "!=0"
      error_type: format_error

  - id: tc-003
    name: 成员列表按角色筛选，仅展示对应角色
    priority: p1
    owner: ""
    precondition: 已登录账号为管理员
    api_path: /teams/{team_id}/members
    method: GET
    request:
      params:
        role: admin
    expected:
      code: 0
      fields: [data, total]
      members_role: admin     # 替代 members.role: admin

skipped_cases:
  - id: tc-skipped-001
    name: 点击复制邀请链接会弹出提示
    reason: 前端剪贴板操作，无需后端接口
```

> **YAML 约束**：
> - 不使用 `!custom`、`!contains` 等自定义 YAML tag（标准 `yaml.safe_load` 无法解析）
> - 错误码非零用 `code_not_zero: true` 表达
> - 字符串包含断言用 `message_contains: "关键词"` 表达
> - 动态表达式（如 `"a" * 256`）展开为实际字面值

## Step 8：输出 pytest 集成测试代码

**文件路径**：`tests/{branch}/{module}_api_test.py`

**完整模板**（严格对齐 `examples/sprint8/team_api_test.py` 风格）：

```python
"""
{module} 模块 API 集成测试
由 integration-test-gen-agent 自动生成
源文件: {xmind_filename}
Sprint: {sprint}
生成时间: {date}
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.dependencies import get_db_session, get_user_id
from app.permissions.dependencies import auth_project, AuthResult


@pytest.fixture
def client(db_session: Session):
    """创建测试客户端，覆盖 DB / 用户 / 权限依赖"""
    def get_db_override():
        yield db_session

    def get_user_override():
        return "test_user_int"

    def get_auth_override(user_id, project_id, action, sess, object_type):
        return AuthResult.ok()

    app.dependency_overrides[get_db_session] = get_db_override
    app.dependency_overrides[get_user_id] = get_user_override
    app.dependency_overrides[auth_project] = get_auth_override

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def team_id():
    return "test_team_001"


# ── 按业务域（xmind 父节点）分组为 class ──────────────────────────

class TestTeamInfo:
    """团队信息相关接口测试"""

    @pytest.mark.p1
    def test_update_avatar_success(self, client, team_id):
        """
        用例: tc-001 - 管理员更新头像成功
        优先级: P1
        接口: PATCH /drama-api/teams/{team_id}
        """
        response = client.patch(
            f"/drama-api/teams/{team_id}",
            json={"avatar": "https://example.com/new_avatar.png"}
        )
        assert response.status_code == 200
        assert response.json().get("code") == 0

    @pytest.mark.p1
    def test_update_avatar_invalid_format(self, client, team_id):
        """
        用例: tc-002 - 上传非图片格式头像，返回错误
        优先级: P1
        接口: PATCH /drama-api/teams/{team_id}
        """
        response = client.patch(
            f"/drama-api/teams/{team_id}",
            json={"avatar": "https://example.com/avatar.exe"}
        )
        assert response.status_code in [400, 422]
        assert response.json().get("code") != 0
```

**类命名规则**：将 xmind 父节点标题转为 `TestCamelCase`（如"团队信息"→ `TestTeamInfo`，"成员角色筛选"→ `TestMemberRoleFilter`）

**方法命名规则**：`test_{动词}_{主语}_{场景}`，全部小写加下划线，去除 ID 前缀

**pytest.mark 规则**：每个方法用 `@pytest.mark.p1` / `@pytest.mark.p2` / `@pytest.mark.p3` 标记（从 Step 4 识别结果）

**断言层级**（必须全部覆盖，不只断言 status_code）：
1. `assert response.status_code == 200`（或 `in [400, 422]` 等）
2. `assert response.json().get("code") == 0`（或 `!= 0`）
3. 有明确返回字段时：`assert "field_name" in response.json().get("result", {})`

## 完整执行检查清单

```
- [ ] Step 1: 解压 xmind，确认 content.json 存在
- [ ] Step 2: 预览根节点，理解脑图层级结构
- [ ] Step 3: 运行提取脚本，打印所有 tc-* 节点列表
- [ ] Step 4: 为每个节点标注优先级
- [ ] Step 5: 识别纯前端节点，移入 skipped_cases
- [ ] Step 6: 读取 task_card.json，为每个 tc 匹配 API
- [ ] Step 7: 生成 {module}_test_data.yaml（无自定义 tag）
- [ ] Step 8: 生成 {module}_api_test.py（TestClient + DI 覆盖）
- [ ] 验证: python -m py_compile tests/{branch}/{module}_api_test.py
```
