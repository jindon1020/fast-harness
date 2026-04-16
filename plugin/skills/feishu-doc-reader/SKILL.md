---
name: feishu-doc-reader
description: 该 skill 用于指导 Agent 完整地读取和提取飞书（Feishu/Lark）云文档的内容。优先使用 lark CLI 获取文档源内容，仅在 CLI 无法覆盖的场景（如画板视觉内容）才降级到浏览器截图。支持通过 HTTP(S) 下载链接将导出文件拉到本地。支持提取纯文本、富文本、表格、图片，以及嵌入的画板（Canvas/Whiteboard）。当需要对飞书文档进行全文分析、格式转换或内容备份时，应使用此 skill。
---

# 飞书云文档全内容提取指南

**原则：lark CLI 优先，浏览器截图作为补充兜底。**

---

## 核心提取流程

### Step 1：解析文档 URL，确定 Token

根据 URL 格式确定文档类型和 token：

| URL 格式 | Token 处理 |
|----------|-----------|
| `/docx/TOKEN` | 直接使用 TOKEN |
| `/doc/TOKEN` | 直接使用 TOKEN |
| `/wiki/TOKEN` | ⚠️ **必须先查 wiki node，获取真实 `obj_token`** |

```bash
# Wiki 链接必须先解析
lark-cli wiki spaces get_node --params '{"token":"WIKI_TOKEN"}'
# 从返回的 node.obj_token 获取真实 token，node.obj_type 确认文档类型
```

---

### Step 2：用 lark CLI 获取文档主体（首选）

```bash
# 获取文档内容（返回含 title、markdown 字段的 JSON）
lark-cli docs +fetch --doc "https://xxx.feishu.cn/docx/TOKEN"

# 或直接传 token
lark-cli docs +fetch --doc TOKEN

# 大文档分页获取（超过 50 blocks 时使用）
lark-cli docs +fetch --doc TOKEN --offset 0 --limit 50
lark-cli docs +fetch --doc TOKEN --offset 50 --limit 50
```

返回的 markdown 字段即为文档的完整文本内容，层级结构（H1、H2、列表、表格等）均已保留。

**解析媒体占位符**：返回的 markdown 中，媒体以 HTML 标签形式出现，需记录以便后续处理：

```html
<image token="TOKEN" width="1833" height="2491"/>   <!-- 图片 -->
<file token="TOKEN" name="file.zip"/>                <!-- 文件 -->
<whiteboard token="TOKEN"/>                          <!-- 画板 -->
```

---

### Step 2b：用户提供「下载链接」时（HTTP 直链）

当用户提供的是**可下载文件的 HTTP(S) URL**（例如飞书文档「导出为 Word/PDF/Markdown」后得到的临时下载链接、云空间文件直链、其他网盘/对象存储直链），**不要**把它当成 docx 网页 URL 去 `+fetch`，应先把文件拉到本地再解析。

```bash
mkdir -p ./downloads
# 使用引号包裹 URL；-L 跟随重定向；-f 失败时不落盘空壳
curl -fL --connect-timeout 30 --max-time 600 --retry 2 -o "./downloads/导出文件.docx" "https://完整下载链接含查询参数"
```

**约定**：

- 根据 `Content-Disposition` 或用户说明选择本地文件名；不确定时用 `download.bin` 再在本地用 `file` 命令识别类型。
- 若 `curl` 得到的是 HTML（体积很小、内容含登录/验证页），说明链接需 Cookie 或已过期：提示用户重新导出、在已登录环境复制「复制为 cURL」并带上 Cookie，或改回 **Step 1–2** 用 `lark-cli docs +fetch` 拉正文。
- 下载完成后：按扩展名处理（`.md`/`.txt` 直接读；`.docx`/`.pdf` 用项目已有文档工具或告知用户需转换后再分析）。

**与文档内嵌文件的区别**：正文中 `<file token="..."/>` 附件仍用下方 **Step 3** 的 `lark-cli docs +media-download`，**不要**对 file token 拼 HTTP 猜测 URL。

---

### Step 3：下载图片 / 文件

```bash
# 下载文档中的图片或文件
lark-cli docs +media-download --token "IMAGE_OR_FILE_TOKEN" --output ./media/
```

对于图片，将下载路径替换回 markdown 中对应的占位符位置。

---

### Step 4：处理画板（Whiteboard / Canvas）

画板的文字和结构信息无法通过 CLI 直接获取完整语义，按以下优先级处理：

#### 4a. 先尝试获取画板缩略图（CLI 方式）

```bash
# 下载画板缩略图（PNG）
lark-cli docs +media-download --token "WHITEBOARD_TOKEN" --output ./media/
```

将缩略图作为视觉输入，用视觉模型分析画板内容，识别节点、连接线、流程图、思维导图结构，输出结构化文字描述。

#### 4b. 降级：浏览器截图（当缩略图分辨率不足时）

仅在以下情况才使用 `browser_subagent`：

- 缩略图文字过小，无法识别
- 画板内容极为复杂，缩略图丢失关键细节

浏览器截图步骤：

1. 用 `browser_subagent` 打开文档页面（遇到登录墙需提示用户提供权限）
2. 定位画板容器，滚动到视口中心
3. 对密集画板放大 150%–200% 后分块截图
4. 用视觉模型分析截图，转为结构化文字

---

### Step 5：合并输出

按文档 Blocks 顺序组织最终内容：

- 文档主体文本：直接来自 CLI 返回的 markdown
- 图片：替换为本地路径或 `![图片描述](./media/xxx.png)`
- 画板：以 `> [画板内容]: ...` 的形式插入到对应位置
- 检查是否遗漏折叠块（Callout）或隐藏内容

---

## 忽略规则

- **视频块**：直接跳过，不截图不描述
- **外部/内部跳转链接**：仅保留链接文本，不深入访问链接目标页面

---

## 工具依赖

本 skill 依赖本机已安装且可用的 **`lark-cli`**，并完成飞书应用认证。命令用法见上文；若需查阅认证与 scope，Claude Code 用户常见路径为（随本机安装位置可能不同）：

- `~/.claude/skills/lark-shared/SKILL.md` — 认证与配置
- `~/.claude/skills/lark-doc/SKILL.md` — `docs +fetch`、`docs +media-download`
- `~/.claude/skills/lark-wiki/SKILL.md` — Wiki 链接解析（`wiki/` URL 必须）

`browser_subagent` — 画板降级截图（可选）
