# Claude Code Agent SDK 文档

> 来源: https://code.claude.com/docs/zh-CN/agent-sdk/overview
> 提取日期: 2026-05-20
> 提取方式: 自动浏览器抓取

---

## 目录


### Agent SDK

- [概览](#概览)
- [快速开始](#快速开始)

### 核心概念

- [代理循环如何工作](#代理循环如何工作)
- [使用 Claude Code 功能](#使用-Claude-Code-功能)
- [使用会话](#使用会话)

### 输入和输出

- [流式输入](#流式输入)
- [处理批准和用户输入](#处理批准和用户输入)
- [实时流式传输响应](#实时流式传输响应)
- [Structured outputs](#Structured-outputs)

### 使用工具扩展

- [为 Claude 提供自定义工具](#为-Claude-提供自定义工具)
- [使用 MCP 连接外部工具](#使用-MCP-连接外部工具)
- [使用工具搜索扩展到多个工具](#使用工具搜索扩展到多个工具)
- [SDK 中的子代理](#SDK-中的子代理)

### 自定义行为

- [修改系统提示词](#修改系统提示词)
- [SDK 中的 slash commands](#SDK-中的-slash-commands)
- [SDK 中的 Agent Skills](#SDK-中的-Agent-Skills)
- [SDK 中的 Plugins](#SDK-中的-Plugins)

### 控制和可观测性

- [配置权限](#配置权限)
- [使用 hooks 拦截和控制代理行为](#使用-hooks-拦截和控制代理行为)
- [File checkpointing](#File-checkpointing)
- [跟踪成本和使用情况](#跟踪成本和使用情况)
- [Observability](#Observability)
- [待办事项列表](#待办事项列表)

### 部署

- [托管 Agent SDK](#托管-Agent-SDK)
- [Secure deployment](#Secure-deployment)

### SDK 参考

- [TypeScript SDK](#TypeScript-SDK)
- [TypeScript V2（已移除）](#TypeScript-V2（已移除）)
- [Python SDK](#Python-SDK)
- [迁移指南](#迁移指南)

---

# 概览

> 章节: Agent SDK | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/overview

---

AGENT SDK
Agent SDK 概览

使用 Claude Code 作为库构建生产级 AI 代理

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

Starting June 15, 2026, Agent SDK and claude -p usage on subscription plans will draw from a new monthly Agent SDK credit, separate from your interactive usage limits. See Use the Claude Agent SDK with your Claude plan for details.
构建能够自主读取文件、运行命令、搜索网络、编辑代码等的 AI 代理。Agent SDK 为您提供了与 Claude Code 相同的工具、代理循环和上下文管理，可在 Python 和 TypeScript 中编程。
Python
TypeScript
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def main():
    async for message in query(
        prompt="Find and fix the bug in auth.py",
        options=ClaudeAgentOptions(allowed_tools=["Read", "Edit", "Bash"]),
    ):
        print(message)  # Claude reads the file, finds the bug, edits it


asyncio.run(main())

Agent SDK 包含用于读取文件、运行命令和编辑代码的内置工具，因此您的代理可以立即开始工作，无需您实现工具执行。深入了解快速入门或探索使用 SDK 构建的真实代理：
快速入门
在几分钟内构建一个 bug 修复代理
示例代理
电子邮件助手、研究代理等
​
开始使用
1

安装 SDK

TypeScript
Python
npm install @anthropic-ai/claude-agent-sdk

TypeScript SDK 为您的平台捆绑了一个本地 Claude Code 二进制文件作为可选依赖项，因此您无需单独安装 Claude Code。
2

设置您的 API 密钥

从控制台获取 API 密钥，然后将其设置为环境变量：
export ANTHROPIC_API_KEY=your-api-key

SDK 还支持通过第三方 API 提供商进行身份验证：
Amazon Bedrock：设置 CLAUDE_CODE_USE_BEDROCK=1 环境变量并配置 AWS 凭证
Claude Platform on AWS：设置 CLAUDE_CODE_USE_ANTHROPIC_AWS=1 和 ANTHROPIC_AWS_WORKSPACE_ID，然后配置 AWS 凭证
Google Vertex AI：设置 CLAUDE_CODE_USE_VERTEX=1 环境变量并配置 Google Cloud 凭证
Microsoft Azure：设置 CLAUDE_CODE_USE_FOUNDRY=1 环境变量并配置 Azure 凭证
有关详细信息，请参阅 Bedrock、Claude Platform on AWS、Vertex AI 或 Azure AI Foundry 的设置指南。
除非事先获得批准，否则 Anthropic 不允许第三方开发人员为其产品（包括基于 Claude Agent SDK 构建的代理）提供 claude.ai 登录或速率限制。请改用本文档中描述的 API 密钥身份验证方法。
3

运行您的第一个代理

此示例创建一个代理，该代理使用内置工具列出当前目录中的文件。
Python
TypeScript
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def main():
    async for message in query(
        prompt="What files are in this directory?",
        options=ClaudeAgentOptions(allowed_tools=["Bash", "Glob"]),
    ):
        if hasattr(message, "result"):
            print(message.result)


asyncio.run(main())

准备好构建了吗？ 按照快速入门在几分钟内创建一个查找和修复 bug 的代理。
​
功能
使 Claude Code 强大的一切都可在 SDK 中使用：
内置工具
Hooks
子代理
MCP
权限
会话
您的代理可以开箱即用地读取文件、运行命令和搜索代码库。关键工具包括：
工具	功能
Read	读取工作目录中的任何文件
Write	创建新文件
Edit	对现有文件进行精确编辑
Bash	运行终端命令、脚本、git 操作
Monitor	监视后台脚本并对每个输出行作为事件做出反应
Glob	按模式查找文件（**/*.ts、src/**/*.py）
Grep	使用正则表达式搜索文件内容
WebSearch	搜索网络以获取当前信息
WebFetch	获取并解析网页内容
AskUserQuestion	向用户提出带有多选选项的澄清问题
此示例创建一个代理，该代理在您的代码库中搜索 TODO 注释：
Python
TypeScript
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def main():
    async for message in query(
        prompt="Find all TODO comments and create a summary",
        options=ClaudeAgentOptions(allowed_tools=["Read", "Glob", "Grep"]),
    ):
        if hasattr(message, "result"):
            print(message.result)


asyncio.run(main())

​
Claude Code 功能
SDK 还支持 Claude Code 的基于文件系统的配置。使用默认选项，SDK 从您的工作目录中的 .claude/ 和 ~/.claude/ 加载这些。要限制加载哪些源，请在您的选项中设置 setting_sources（Python）或 settingSources（TypeScript）。
功能	描述	位置
Skills	在 Markdown 中定义的专门功能	.claude/skills/*/SKILL.md
Slash commands	用于常见任务的自定义命令	.claude/commands/*.md
Memory	项目上下文和说明	CLAUDE.md 或 .claude/CLAUDE.md
Plugins	使用自定义命令、代理和 MCP 服务器扩展	通过 plugins 选项编程
​
将 Agent SDK 与其他 Claude 工具进行比较
Claude 平台提供了多种使用 Claude 构建的方式。以下是 Agent SDK 的适用场景：
Agent SDK vs Client SDK
Agent SDK vs Claude Code CLI
Agent SDK vs Managed Agents
Anthropic Client SDK 为您提供直接 API 访问：您发送提示并自己实现工具执行。Agent SDK 为您提供具有内置工具执行的 Claude。
使用 Client SDK，您实现工具循环。使用 Agent SDK，Claude 处理它：
Python
TypeScript
# Client SDK: You implement the tool loop
response = client.messages.create(...)
while response.stop_reason == "tool_use":
    result = your_tool_executor(response.tool_use)
    response = client.messages.create(tool_result=result, **params)

# Agent SDK: Claude handles tools autonomously
async for message in query(prompt="Fix the bug in auth.py"):
    print(message)

​
更新日志
查看完整的更新日志以了解 SDK 更新、bug 修复和新功能：
TypeScript SDK：查看 CHANGELOG.md
Python SDK：查看 CHANGELOG.md
​
报告 bug
如果您在 Agent SDK 中遇到 bug 或问题：
TypeScript SDK：在 GitHub 上报告问题
Python SDK：在 GitHub 上报告问题
​
品牌指南
对于集成 Claude Agent SDK 的合作伙伴，使用 Claude 品牌是可选的。在您的产品中引用 Claude 时：
允许：
“Claude Agent”（首选用于下拉菜单）
“Claude”（当已在标记为”Agents”的菜单中时）
” Powered by Claude”（如果您有现有的代理名称）
不允许：
“Claude Code” 或 “Claude Code Agent”
Claude Code 品牌的 ASCII 艺术或模仿 Claude Code 的视觉元素
您的产品应保持自己的品牌，不应显示为 Claude Code 或任何 Anthropic 产品。如有关于品牌合规性的问题，请联系 Anthropic 销售团队。
​
许可证和条款
Claude Agent SDK 的使用受 Anthropic 商业服务条款管制，包括当您使用它为您自己的客户和最终用户提供的产品和服务时，除非特定组件或依赖项由该组件的 LICENSE 文件中指示的不同许可证覆盖。
​
后续步骤
快速入门
构建一个在几分钟内查找和修复 bug 的代理
示例代理
电子邮件助手、研究代理等
TypeScript SDK
完整的 TypeScript API 参考和示例
Python SDK
完整的 Python API 参考和示例

此页面对您有帮助吗？

是
否
快速开始
⌘I

---

# 快速开始

> 章节: Agent SDK | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/quickstart

---

AGENT SDK
快速开始

使用 Python 或 TypeScript Agent SDK 开始构建能够自主工作的 AI 代理

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

使用 Agent SDK 构建一个 AI 代理，它可以读取你的代码、发现错误并修复它们，所有这一切都无需手动干预。
你将做什么：
使用 Agent SDK 设置一个项目
创建一个包含一些有缺陷代码的文件
运行一个代理，自动查找并修复错误
​
前置条件
Node.js 18+ 或 Python 3.10+
一个 Anthropic 账户（在此注册）
​
设置
1

创建项目文件夹

为此快速开始创建一个新目录：
mkdir my-agent && cd my-agent

对于你自己的项目，你可以从任何文件夹运行 SDK；默认情况下，它将有权访问该目录及其子目录中的文件。
2

安装 SDK

为你的语言安装 Agent SDK 包：
TypeScript
Python (uv)
Python (pip)
npm install @anthropic-ai/claude-agent-sdk

TypeScript SDK 为你的平台捆绑了一个本地 Claude Code 二进制文件作为可选依赖项，所以你不需要单独安装 Claude Code。
3

设置你的 API 密钥

从 Claude 控制台获取 API 密钥，然后在你的项目目录中创建一个 .env 文件：
ANTHROPIC_API_KEY=your-api-key

SDK 还支持通过第三方 API 提供商进行身份验证：
Amazon Bedrock：设置 CLAUDE_CODE_USE_BEDROCK=1 环境变量并配置 AWS 凭证
Claude Platform on AWS：设置 CLAUDE_CODE_USE_ANTHROPIC_AWS=1 和 ANTHROPIC_AWS_WORKSPACE_ID，然后配置 AWS 凭证
Google Vertex AI：设置 CLAUDE_CODE_USE_VERTEX=1 环境变量并配置 Google Cloud 凭证
Microsoft Azure：设置 CLAUDE_CODE_USE_FOUNDRY=1 环境变量并配置 Azure 凭证
有关详细信息，请参阅 Bedrock、Claude Platform on AWS、Vertex AI 或 Azure AI Foundry 的设置指南。
除非事先获得批准，否则 Anthropic 不允许第三方开发者提供 claude.ai 登录或对其产品的速率限制，包括基于 Claude Agent SDK 构建的代理。请改用本文档中描述的 API 密钥身份验证方法。
​
创建一个有缺陷的文件
此快速开始将引导你构建一个可以查找和修复代码中错误的代理。首先，你需要一个包含一些有意错误的文件供代理修复。在 my-agent 目录中创建 utils.py 并粘贴以下代码：
def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)


def get_user_name(user):
    return user["name"].upper()

此代码有两个错误：
calculate_average([]) 会因除以零而崩溃
get_user_name(None) 会因 TypeError 而崩溃
​
构建一个查找和修复错误的代理
如果你使用 Python SDK，创建 agent.py，或者如果使用 TypeScript，创建 agent.ts：
Python
TypeScript
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage


async def main():
    # Agentic loop: streams messages as Claude works
    async for message in query(
        prompt="Review utils.py for bugs that would cause crashes. Fix any issues you find.",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Edit", "Glob"],  # Tools Claude can use
            permission_mode="acceptEdits",  # Auto-approve file edits
        ),
    ):
        # Print human-readable output
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    print(block.text)  # Claude's reasoning
                elif hasattr(block, "name"):
                    print(f"Tool: {block.name}")  # Tool being called
        elif isinstance(message, ResultMessage):
            print(f"Done: {message.subtype}")  # Final result


asyncio.run(main())

此代码有三个主要部分：
query：创建 agentic 循环的主入口点。它返回一个异步迭代器，所以你使用 async for 来流式传输 Claude 工作时的消息。查看 Python 或 TypeScript SDK 参考中的完整 API。
prompt：你想让 Claude 做什么。Claude 根据任务确定要使用哪些工具。
options：代理的配置。此示例使用 allowedTools 预先批准 Read、Edit 和 Glob，以及 permissionMode: "acceptEdits" 来自动批准文件更改。其他选项包括 systemPrompt、mcpServers 等。查看 Python 或 TypeScript 的所有选项。
async for 循环在 Claude 思考、调用工具、观察结果并决定下一步做什么时继续运行。每次迭代都会产生一条消息：Claude 的推理、工具调用、工具结果或最终结果。SDK 处理编排（工具执行、上下文管理、重试），所以你只需使用流。当 Claude 完成任务或遇到错误时，循环结束。
循环内的消息处理过滤人类可读的输出。如果没有过滤，你会看到原始消息对象，包括系统初始化和内部状态，这对调试很有用，但通常很冗长。
此示例使用流式传输来实时显示进度。如果你不需要实时输出（例如，对于后台作业或 CI 管道），你可以一次性收集所有消息。有关详细信息，请参阅流式传输与单轮模式。
​
运行你的代理
你的代理已准备好。使用以下命令运行它：
Python
TypeScript
python3 agent.py

运行后，检查 utils.py。你会看到处理空列表和空用户的防御性代码。你的代理自主地：
读取 utils.py 以理解代码
分析了逻辑并识别了会导致崩溃的边界情况
编辑了文件以添加适当的错误处理
这就是 Agent SDK 的与众不同之处：Claude 直接执行工具，而不是要求你实现它们。
如果你看到”API key not found”，请确保你已在 .env 文件或 shell 环境中设置了 ANTHROPIC_API_KEY 环境变量。有关更多帮助，请参阅完整故障排除指南。
​
尝试其他提示
现在你的代理已设置好，尝试一些不同的提示：
"Add docstrings to all functions in utils.py"
"Add type hints to all functions in utils.py"
"Create a README.md documenting the functions in utils.py"
​
自定义你的代理
你可以通过更改选项来修改代理的行为。以下是一些示例：
添加网络搜索功能：
Python
TypeScript
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Edit", "Glob", "WebSearch"], permission_mode="acceptEdits"
)

给 Claude 一个自定义系统提示：
Python
TypeScript
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Edit", "Glob"],
    permission_mode="acceptEdits",
    system_prompt="You are a senior Python developer. Always follow PEP 8 style guidelines.",
)

在终端中运行命令：
Python
TypeScript
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Edit", "Glob", "Bash"], permission_mode="acceptEdits"
)

启用 Bash 后，尝试："Write unit tests for utils.py, run them, and fix any failures"
​
关键概念
工具控制你的代理可以做什么：
工具	代理可以做什么
Read、Glob、Grep	只读分析
Read、Edit、Glob	分析和修改代码
Read、Edit、Bash、Glob、Grep	完全自动化
权限模式控制你想要多少人工监督：
模式	行为	用例
acceptEdits	自动批准文件编辑和常见文件系统命令，询问其他操作	受信任的开发工作流
dontAsk	拒绝不在 allowedTools 中的任何内容	锁定的无头代理
auto（仅 TypeScript）	模型分类器批准或拒绝每个工具调用	具有安全防护的自主代理
bypassPermissions	运行每个工具而不提示	沙箱 CI、完全受信任的环境
default	需要 canUseTool 回调来处理批准	自定义批准流程
上面的示例使用 acceptEdits 模式，它自动批准文件操作，以便代理可以在没有交互式提示的情况下运行。如果你想提示用户批准，使用 default 模式并提供一个 canUseTool 回调来收集用户输入。为了获得更多控制，请参阅权限。
​
故障排除
​
API 错误 thinking.type.enabled 不支持此模型
Claude Opus 4.7 用 thinking.type.adaptive 替换了 thinking.type.enabled。当你选择 claude-opus-4-7 时，较旧的 Agent SDK 版本会失败，出现以下 API 错误：
API Error: 400 {"type":"invalid_request_error","message":"\"thinking.type.enabled\" is not supported for this model. Use \"thinking.type.adaptive\" and \"output_config.effort\" to control thinking behavior."}

升级到 Agent SDK v0.2.111 或更高版本以使用 Opus 4.7。
​
后续步骤
现在你已经创建了你的第一个代理，学习如何扩展其功能并将其定制到你的用例：
权限：控制你的代理可以做什么以及何时需要批准
Hooks：在工具调用之前或之后运行自定义代码
会话：构建维护上下文的多轮代理
MCP 服务器：连接到数据库、浏览器、API 和其他外部系统
托管：将代理部署到 Docker、云和 CI/CD
示例代理：查看完整示例：电子邮件助手、研究代理等

此页面对您有帮助吗？

是
否
概览
代理循环如何工作
⌘I

---

# 代理循环如何工作

> 章节: 核心概念 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/agent-loop

---

核心概念
代理循环如何工作

了解消息生命周期、工具执行、上下文窗口和支持 SDK 代理的架构。

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

Agent SDK 让你能够在自己的应用程序中嵌入 Claude Code 的自主代理循环。SDK 是一个独立的包，让你能够以编程方式控制工具、权限、成本限制和输出。你不需要安装 Claude Code CLI 就能使用它。
启动代理时，SDK 运行与 Claude Code 相同的执行循环：Claude 评估你的提示，调用工具采取行动，接收结果，然后重复直到任务完成。本页解释循环内部发生的情况，以便你能够有效地构建、调试和优化代理。
​
循环概览
每个代理会话都遵循相同的周期：
接收提示。 Claude 接收你的提示，以及系统提示、工具定义和对话历史。SDK 产生一个 SystemMessage，子类型为 "init"，包含会话元数据。
评估并响应。 Claude 评估当前状态并确定如何继续。它可能用文本响应、请求一个或多个工具调用，或两者都有。SDK 产生一个 AssistantMessage，包含文本和任何工具调用请求。
执行工具。 SDK 运行每个请求的工具并收集结果。每组工具结果反馈给 Claude 以做出下一个决定。你可以使用 hooks 在工具运行前拦截、修改或阻止工具调用。
重复。 步骤 2 和 3 作为一个循环重复。每个完整循环是一个轮次。Claude 继续调用工具并处理结果，直到产生没有工具调用的响应。
返回结果。 SDK 产生最终的 AssistantMessage，包含文本响应（无工具调用），然后是 ResultMessage，包含最终文本、令牌使用、成本和会话 ID。
一个快速问题（“这里有什么文件？“）可能需要一两个轮次调用 Glob 并响应结果。一个复杂任务（“重构认证模块并更新测试”）可以跨多个轮次链接数十个工具调用，读取文件、编辑代码和运行测试，Claude 根据每个结果调整其方法。
​
轮次和消息
轮次是循环内的一个往返：Claude 产生包含工具调用的输出，SDK 执行这些工具，结果自动反馈给 Claude。这发生在不将控制权交回给你的代码的情况下。轮次继续进行，直到 Claude 产生没有工具调用的输出，此时循环结束并交付最终结果。
考虑对于提示”修复 auth.ts 中的失败测试”的完整会话可能是什么样子。
首先，SDK 将你的提示发送给 Claude 并产生一个 SystemMessage，包含会话元数据。然后循环开始：
轮次 1： Claude 调用 Bash 运行 npm test。SDK 产生一个 AssistantMessage，包含工具调用，执行命令，然后产生一个 UserMessage，包含输出（三个失败）。
轮次 2： Claude 在 auth.ts 和 auth.test.ts 上调用 Read。SDK 返回文件内容并产生一个 AssistantMessage。
轮次 3： Claude 调用 Edit 修复 auth.ts，然后调用 Bash 重新运行 npm test。所有三个测试都通过。SDK 产生一个 AssistantMessage。
最后轮次： Claude 产生仅包含文本的响应，没有工具调用：“修复了认证错误，所有三个测试现在都通过了。” SDK 产生最终的 AssistantMessage，包含此文本，然后是 ResultMessage，包含相同的文本加上成本和使用情况。
那是四个轮次：三个有工具调用，一个最终仅包含文本的响应。
你可以使用 max_turns / maxTurns 限制循环，它仅计算工具使用轮次。例如，上面循环中的 max_turns=2 会在编辑步骤之前停止。你也可以使用 max_budget_usd / maxBudgetUsd 根据支出阈值限制轮次。
没有限制的情况下，循环运行直到 Claude 自己完成，这对于范围明确的任务很好，但对于开放式提示（“改进这个代码库”）可能运行很长时间。为生产代理设置预算是一个很好的默认值。有关选项参考，请参阅下面的 轮次和预算。
​
消息类型
当循环运行时，SDK 产生一个消息流。每条消息都有一个类型，告诉你它来自循环的哪个阶段。五个核心类型是：
SystemMessage： 会话生命周期事件。subtype 字段区分它们："init" 是第一条消息（会话元数据），"compact_boundary" 在 压缩 后触发。在 TypeScript 中，压缩边界是其自己的 SDKCompactBoundaryMessage 类型，而不是 SDKSystemMessage 的子类型。
AssistantMessage： 在每个 Claude 响应后发出，包括最终仅包含文本的响应。包含该轮次的文本内容块和工具调用块。
UserMessage： 在每个工具执行后发出，包含发送回 Claude 的工具结果内容。也为你在循环中间流式传输的任何用户输入发出。
StreamEvent： 仅在启用部分消息时发出。包含原始 API 流事件（文本增量、工具输入块）。请参阅 流式响应。
ResultMessage： 标记代理循环的结束。包含最终文本结果、令牌使用、成本和会话 ID。检查 subtype 字段以确定任务是否成功或达到限制。少数尾随系统事件（如 prompt_suggestion）可能在其后到达，因此迭代流直到完成，而不是在结果处中断。请参阅 处理结果。
这五种类型涵盖了两个 SDK 中完整的代理循环生命周期。TypeScript SDK 还产生额外的可观测性事件（hook 事件、工具进度、速率限制、任务通知），提供额外的细节，但不是驱动循环所必需的。有关完整列表，请参阅 Python 消息类型参考 和 TypeScript 消息类型参考。
​
处理消息
你处理哪些消息取决于你正在构建什么：
仅最终结果： 处理 ResultMessage 以获取输出、成本以及任务是否成功或达到限制。
进度更新： 处理 AssistantMessage 以查看 Claude 每个轮次在做什么，包括它调用了哪些工具。
实时流式传输： 启用部分消息（Python 中的 include_partial_messages，TypeScript 中的 includePartialMessages）以实时获取 StreamEvent 消息。请参阅 实时流式响应。
检查消息类型的方式取决于 SDK：
Python： 使用从 claude_agent_sdk 导入的类的 isinstance() 检查消息类型（例如，isinstance(message, ResultMessage)）。
TypeScript： 检查 type 字符串字段（例如，message.type === "result"）。AssistantMessage 和 UserMessage 在 .message 字段中包装原始 API 消息，因此内容块位于 message.message.content，而不是 message.content。

示例：检查消息类型并处理结果

​
工具执行
工具赋予你的代理采取行动的能力。没有工具，Claude 只能用文本响应。有了工具，Claude 可以读取文件、运行命令、搜索代码并与外部服务交互。
​
内置工具
SDK 包含与 Claude Code 相同的工具：
类别	工具	它们做什么
文件操作	Read、Edit、Write	读取、修改和创建文件
搜索	Glob、Grep	按模式查找文件，使用正则表达式搜索内容
执行	Bash	运行 shell 命令、脚本、git 操作
Web	WebSearch、WebFetch	搜索网络、获取和解析页面
发现	ToolSearch	动态查找和按需加载工具，而不是预加载所有工具
编排	Agent、Skill、AskUserQuestion、TaskCreate、TaskUpdate	生成子代理、调用技能、询问用户、跟踪任务
除了内置工具，你还可以：
使用 MCP 服务器 连接外部服务（数据库、浏览器、API）
使用 自定义工具处理程序 定义自定义工具
通过 设置源 加载项目技能以实现可重用工作流
​
工具权限
Claude 根据任务确定调用哪些工具，但你控制这些调用是否被允许执行。你可以自动批准特定工具、完全阻止其他工具，或要求对所有工具进行批准。三个选项一起工作以确定什么运行：
allowed_tools / allowedTools 自动批准列出的工具。具有 ["Read", "Glob", "Grep"] 在其允许工具列表中的只读代理运行这些工具而不提示。未列出的工具仍然可用但需要权限。
disallowed_tools / disallowedTools 阻止列出的工具，无论其他设置如何。有关在工具运行前检查规则的顺序，请参阅 权限。
permission_mode / permissionMode 控制对不被允许或拒绝规则覆盖的工具发生什么。有关可用模式，请参阅 权限模式。
你也可以使用 "Bash(npm *)" 之类的规则来限制单个工具，以仅允许特定命令。有关完整规则语法，请参阅 权限。
当工具被拒绝时，Claude 接收拒绝消息作为工具结果，通常尝试不同的方法或报告它无法继续。
​
并行工具执行
当 Claude 在单个轮次中请求多个工具调用时，两个 SDK 都可以根据工具并发或顺序运行它们。只读工具（如 Read、Glob、Grep 和标记为只读的 MCP 工具）可以并发运行。修改状态的工具（如 Edit、Write 和 Bash）顺序运行以避免冲突。
自定义工具默认为顺序执行。要为自定义工具启用并行执行，请在其注释中设置 readOnlyHint。TypeScript 和 Python SDK 都使用来自 MCP SDK 的此字段名。
​
控制循环如何运行
你可以限制循环进行多少轮次、成本多少、Claude 推理的深度，以及工具是否需要在运行前获得批准。所有这些都是 ClaudeAgentOptions（Python）/ Options（TypeScript）上的字段。
​
轮次和预算
选项	它控制什么	默认值
最大轮次（max_turns / maxTurns）	最大工具使用往返次数	无限制
最大预算（max_budget_usd / maxBudgetUsd）	停止前的最大成本	无限制
当达到任一限制时，SDK 返回一个 ResultMessage，包含相应的错误子类型（error_max_turns 或 error_max_budget_usd）。有关如何检查这些子类型，请参阅 处理结果，有关语法，请参阅 ClaudeAgentOptions / Options。
​
努力级别
effort 选项控制 Claude 应用多少推理。较低的努力级别每个轮次使用更少的令牌并降低成本。并非所有模型都支持努力参数。有关哪些模型支持它，请参阅 Effort。
级别	行为	适合
"low"	最小推理，快速响应	文件查找、列出目录
"medium"	平衡推理	常规编辑、标准任务
"high"	彻底分析	重构、调试
"xhigh"	扩展推理深度	编码和代理任务；在 Opus 4.7 上推荐
"max"	最大推理深度	需要深度分析的多步骤问题
如果你不设置 effort，Python SDK 会将参数保留未设置，并遵从模型的默认行为。TypeScript SDK 默认为 "high"。
effort 在每个响应内交换延迟和令牌成本以获得推理深度。扩展思考 是一个单独的功能，在输出中产生可见的思维链块。它们是独立的：你可以设置 effort: "low" 并启用扩展思考，或 effort: "max" 而不启用它。
对于执行简单、范围明确的任务（如列出文件或运行单个 grep）的代理，使用较低的努力来降低成本和延迟。在顶级 query() 选项中为整个会话设置 effort，或在 AgentDefinition 上使用 effort 字段为每个子代理设置以覆盖会话级别。
​
权限模式
权限模式选项（Python 中的 permission_mode，TypeScript 中的 permissionMode）控制代理是否在使用工具前请求批准：
模式	行为
"default"	不被允许规则覆盖的工具触发你的批准回调；没有回调意味着拒绝
"acceptEdits"	自动批准文件编辑和常见文件系统命令（mkdir、touch、mv、cp 等）；其他 Bash 命令遵循默认规则
"plan"	只读工具运行；Claude 探索并产生计划而不编辑你的源文件
"dontAsk"	从不提示。由 权限规则 预批准的工具运行，其他一切被拒绝
"auto"（仅 TypeScript）	使用模型分类器批准或拒绝每个工具调用。有关可用性和行为，请参阅 自动模式
"bypassPermissions"	运行所有允许的工具而不询问。在 Unix 上以 root 身份运行时无法使用。仅在隔离环境中使用，其中代理的操作无法影响你关心的系统
对于交互式应用程序，使用 "default" 和工具批准回调来显示批准提示。对于开发机器上的自主代理，"acceptEdits" 自动批准文件编辑和常见文件系统命令（mkdir、touch、mv、cp 等），同时仍然在允许规则后面限制其他 Bash 命令。为 CI、容器或其他隔离环境保留 "bypassPermissions"。有关完整详情，请参阅 权限。
​
模型
如果你不设置 model，SDK 使用 Claude Code 的默认值，这取决于你的身份验证方法和订阅。显式设置它（例如，model="claude-sonnet-4-6"）以固定特定模型或使用较小的模型以获得更快、更便宜的代理。有关可用 ID，请参阅 models。
​
上下文窗口
上下文窗口是会话期间可用于 Claude 的信息总量。它在会话内的轮次之间不重置。一切都累积：系统提示、工具定义、对话历史、工具输入和工具输出。在轮次之间保持相同的内容（系统提示、工具定义、CLAUDE.md）自动进行提示缓存，这减少了重复前缀的成本和延迟。
​
什么消耗上下文
以下是每个组件如何影响 SDK 中上下文的方式：
源	何时加载	影响
系统提示	每个请求	小的固定成本，始终存在
CLAUDE.md 文件	会话开始，通过 settingSources	每个请求中的完整内容（但提示缓存，所以仅第一个请求支付全部成本）
工具定义	每个请求；MCP 架构默认延迟	内置工具架构在每个请求中加载。工具搜索默认延迟 MCP 工具架构，在 Vertex AI 或非第一方 ANTHROPIC_BASE_URL 上回退到预先加载。有关完整矩阵，请参阅配置工具搜索
对话历史	在轮次中累积	随着每个轮次增长：提示、响应、工具输入、工具输出
技能描述	会话开始，通过设置源	简短摘要；完整内容仅在调用时加载
大型工具输出消耗大量上下文。读取大文件或运行具有详细输出的命令可以在单个轮次中使用数千个令牌。上下文在轮次中累积，因此具有许多工具调用的较长会话比短会话构建更多上下文。
​
自动压缩
当上下文窗口接近其限制时，SDK 自动压缩对话：它总结较旧的历史以释放空间，保持你最近的交换和关键决定完整。当这发生时，SDK 在流中发出一条消息，其 type: "system" 和 subtype: "compact_boundary"（在 Python 中这是一个 SystemMessage；在 TypeScript 中它是一个单独的 SDKCompactBoundaryMessage 类型）。
压缩用摘要替换较旧的消息，因此对话早期的特定指令可能不会被保留。持久规则属于 CLAUDE.md（通过 settingSources 加载），而不是初始提示，因为 CLAUDE.md 内容在每个请求上重新注入。
你可以通过多种方式自定义压缩行为：
CLAUDE.md 中的总结指令： 压缩器像任何其他上下文一样读取你的 CLAUDE.md，所以你可以包含一个部分告诉它在总结时保留什么。部分标题是自由形式的（不是魔法字符串）；压缩器根据意图匹配。
PreCompact hook： 在压缩发生前运行自定义逻辑，例如存档完整成绩单。hook 接收一个 trigger 字段（manual 或 auto）。请参阅 hooks。
手动压缩： 发送 /compact 作为提示字符串以按需触发压缩。（以这种方式发送的斜杠命令是 SDK 输入，而不是仅限 CLI 的快捷方式。请参阅 SDK 中的斜杠命令。）

示例：CLAUDE.md 中的总结指令

​
保持上下文高效
对于长时间运行的代理的几个策略：
为子任务使用子代理。 每个子代理以新鲜对话开始（没有先前的消息历史，尽管它确实加载自己的系统提示和项目级上下文，如 CLAUDE.md）。它看不到父级的轮次，只有其最终响应作为工具结果返回给父级。主代理的上下文增长该摘要，而不是完整的子任务成绩单。有关详情，请参阅子代理继承什么。
对工具有选择性。 每个工具定义占用上下文空间。在 AgentDefinition 上使用 tools 字段将子代理限制在它们需要的最小集合。
监视 MCP 服务器成本。 MCP 工具搜索默认延迟 MCP 工具架构，并按需加载它们。当工具搜索关闭、在 Vertex AI 上或在非第一方 ANTHROPIC_BASE_URL 后面时，每个 MCP 服务器将其所有工具架构添加到每个请求，因此具有许多工具的几个服务器可以在代理执行任何工作之前消耗大量上下文。
对常规任务使用较低的努力。 为仅需要读取文件或列出目录的代理设置努力为 "low"。这减少了令牌使用和成本。
有关每个功能上下文成本的详细分解，请参阅理解上下文成本。
​
会话和连续性
与 SDK 的每次交互都创建或继续一个会话。从 ResultMessage.session_id（在两个 SDK 中都可用）捕获会话 ID 以稍后恢复。TypeScript SDK 也将其作为初始化 SystemMessage 上的直接字段公开；在 Python 中它嵌套在 SystemMessage.data 中。
当你恢复时，来自先前轮次的完整上下文被恢复：读取的文件、执行的分析和采取的操作。你也可以分叉一个会话以分支到不同的方法而不修改原始方法。
有关恢复、继续和分叉模式的完整指南，请参阅 会话管理。
在 Python 中，ClaudeSDKClient 跨多个调用自动处理会话 ID。有关详情，请参阅 Python SDK 参考。
​
处理结果
当循环结束时，ResultMessage 告诉你发生了什么并给你输出。subtype 字段（在两个 SDK 中都可用）是检查终止状态的主要方式。
结果子类型	发生了什么	result 字段可用？
success	Claude 正常完成了任务	是
error_max_turns	在完成前达到 maxTurns 限制	否
error_max_budget_usd	在完成前达到 maxBudgetUsd 限制	否
error_during_execution	错误中断了循环（例如，API 失败或取消的请求）	否
error_max_structured_output_retries	结构化输出验证在配置的重试限制后失败	否
result 字段（最终文本输出）仅在 success 变体上存在，因此在读取它之前始终检查子类型。所有结果子类型都包含 total_cost_usd、usage、num_turns 和 session_id，因此你可以跟踪成本并在错误后恢复。在 Python 中，total_cost_usd 和 usage 被类型化为可选的，在某些错误路径上可能是 None，因此在格式化它们之前进行保护。有关解释 usage 字段的详情，请参阅 跟踪成本和使用。
结果还包括一个 stop_reason 字段（TypeScript 中的 string | null，Python 中的 str | None），指示模型为什么在其最后轮次停止生成。常见值是 end_turn（模型正常完成）、max_tokens（达到输出令牌限制）和 refusal（模型拒绝了请求）。在错误结果子类型上，stop_reason 携带循环结束前最后一个助手响应的值。要检测拒绝，检查 stop_reason === "refusal"（TypeScript）或 stop_reason == "refusal"（Python）。有关完整类型，请参阅 SDKResultMessage（TypeScript）或 ResultMessage（Python）。
​
Hooks
Hooks 是在循环中特定点触发的回调：在工具运行前、返回后、代理完成时等。一些常用的 hooks 是：
Hook	何时触发	常见用途
PreToolUse	在工具执行前	验证输入、阻止危险命令
PostToolUse	在工具返回后	审计输出、触发副作用
UserPromptSubmit	当发送提示时	将额外上下文注入提示
Stop	当代理完成时	验证结果、保存会话状态
SubagentStart / SubagentStop	当子代理生成或完成时	跟踪和聚合并行任务结果
PreCompact	在上下文压缩前	在总结前存档完整成绩单
Hooks 在你的应用程序进程中运行，而不是在代理的上下文窗口内，因此它们不消耗上下文。Hooks 也可以短路循环：拒绝工具调用的 PreToolUse hook 防止它执行，Claude 接收拒绝消息。
两个 SDK 都支持上述所有事件。TypeScript SDK 包括 Python 尚不支持的额外事件。有关完整事件列表、每个 SDK 的可用性和完整回调 API，请参阅 使用 hooks 控制执行。
​
将其全部放在一起
此示例将本页的关键概念组合到修复失败测试的单个代理中。它使用允许的工具（自动批准，以便代理自主运行）、项目设置和轮次和推理努力的安全限制来配置代理。当循环运行时，它捕获会话 ID 以进行潜在恢复、处理最终结果并打印总成本。
Python
TypeScript
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage


async def run_agent():
    session_id = None

    async for message in query(
        prompt="Find and fix the bug causing test failures in the auth module",
        options=ClaudeAgentOptions(
            allowed_tools=[
                "Read",
                "Edit",
                "Bash",
                "Glob",
                "Grep",
            ],  # Listing tools here auto-approves them (no prompting)
            setting_sources=[
                "project"
            ],  # Load CLAUDE.md, skills, hooks from current directory
            max_turns=30,  # Prevent runaway sessions
            effort="high",  # Thorough reasoning for complex debugging
        ),
    ):
        # Handle the final result
        if isinstance(message, ResultMessage):
            session_id = message.session_id  # Save for potential resumption

            if message.subtype == "success":
                print(f"Done: {message.result}")
            elif message.subtype == "error_max_turns":
                # Agent ran out of turns. Resume with a higher limit.
                print(f"Hit turn limit. Resume session {session_id} to continue.")
            elif message.subtype == "error_max_budget_usd":
                print("Hit budget limit.")
            else:
                print(f"Stopped: {message.subtype}")
            if message.total_cost_usd is not None:
                print(f"Cost: ${message.total_cost_usd:.4f}")


asyncio.run(run_agent())

​
后续步骤
现在你理解了循环，以下是根据你正在构建的内容去往的地方：
还没有运行代理？ 从 快速入门 开始，获取 SDK 安装并查看完整示例端到端运行。
准备好连接到你的项目？ 加载 CLAUDE.md、技能和文件系统 hooks，以便代理自动遵循你的项目约定。
构建交互式 UI？ 启用 流式传输 以在循环运行时显示实时文本和工具调用。
需要对代理能做什么进行更严格的控制？ 使用 权限 锁定工具访问，并使用 hooks 在工具执行前审计、阻止或转换工具调用。
运行长期或昂贵的任务？ 将隔离的工作卸载到 子代理 以保持你的主上下文精简。
有关代理循环的更广泛概念图（不是 SDK 特定的），请参阅 Claude Code 如何工作。

此页面对您有帮助吗？

是
否
快速开始
使用 Claude Code 功能
⌘I

---

# 使用 Claude Code 功能

> 章节: 核心概念 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/claude-code-features

---

核心概念
在 SDK 中使用 Claude Code 功能

将项目说明、skills、hooks 和其他 Claude Code 功能加载到您的 SDK 代理中。

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

Agent SDK 建立在与 Claude Code 相同的基础之上，这意味着您的 SDK 代理可以访问相同的基于文件系统的功能：项目说明（CLAUDE.md 和规则）、skills、hooks 等。
当您省略 settingSources 时，query() 读取与 Claude Code CLI 相同的文件系统设置：用户、项目和本地设置、CLAUDE.md 文件以及 .claude/ skills、代理和命令。要在没有这些的情况下运行，请传递 settingSources: []，这会将代理限制为您以编程方式配置的内容。无论此选项如何，都会读取托管策略设置和全局 ~/.claude.json 配置。请参阅 settingSources 不控制的内容。
有关每个功能的概念概述以及何时使用它，请参阅 扩展 Claude Code。
​
使用 settingSources 控制文件系统设置
设置源选项（Python 中的 setting_sources、TypeScript 中的 settingSources）控制 SDK 加载哪些基于文件系统的设置。传递显式列表以选择加入特定源，或传递空数组以禁用用户、项目和本地设置。
此示例通过将 settingSources 设置为 ["user", "project"] 来加载用户级和项目级设置：
Python
TypeScript
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage

async for message in query(
    prompt="Help me refactor the auth module",
    options=ClaudeAgentOptions(
        # "user" loads from ~/.claude/, "project" loads from ./.claude/ in cwd.
        # Together they give the agent access to CLAUDE.md, skills, hooks, and
        # permissions from both locations.
        setting_sources=["user", "project"],
        allowed_tools=["Read", "Edit", "Bash"],
    ),
):
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if hasattr(block, "text"):
                print(block.text)
    if isinstance(message, ResultMessage) and message.subtype == "success":
        print(f"\nResult: {message.result}")

每个源从特定位置加载设置，其中 <cwd> 是您通过 cwd 选项传递的工作目录，或者如果未设置则为进程的当前目录。有关完整的类型定义，请参阅 SettingSource（TypeScript）或 SettingSource（Python）。
源	加载的内容	位置
"project"	项目 CLAUDE.md、.claude/rules/*.md、项目 skills、项目 hooks、项目 settings.json	<cwd>/.claude/ 用于 settings.json 和 hooks；<cwd> 和每个父目录用于 CLAUDE.md 和规则；<cwd> 和每个父目录直到存储库根目录用于 skills
"user"	用户 CLAUDE.md、~/.claude/rules/*.md、用户 skills、用户设置	~/.claude/
"local"	CLAUDE.local.md、.claude/settings.local.json	<cwd>/.claude/ 用于 settings.local.json；<cwd> 和每个父目录用于 CLAUDE.local.md
省略 settingSources 等同于 ["user", "project", "local"]。
cwd 选项确定 SDK 查找项目级输入的位置。CLAUDE.md 和规则从 <cwd> 和每个父目录加载。Skills 从 <cwd> 和每个父目录直到存储库根目录加载。项目 settings.json 和 hooks 仅从 <cwd>/.claude/ 加载，没有父目录回退。
​
settingSources 不控制的内容
settingSources 涵盖用户、项目和本地设置。无论其值如何，都会读取一些输入：
输入	行为	禁用方式
托管策略设置	主机上存在时始终加载	删除托管设置文件
~/.claude.json 全局配置	始终读取	使用 env 中的 CLAUDE_CONFIG_DIR 重新定位
~/.claude/projects/<project>/memory/ 处的自动内存	默认加载到系统提示中	在设置中设置 autoMemoryEnabled: false，或在 env 中设置 CLAUDE_CODE_DISABLE_AUTO_MEMORY=1
不要依赖默认 query() 选项进行多租户隔离。因为上述输入无论 settingSources 如何都会被读取，SDK 进程可能会获取主机级配置和按目录内存。对于多租户部署，在自己的文件系统中运行每个租户，并设置 settingSources: [] 加上 env 中的 CLAUDE_CODE_DISABLE_AUTO_MEMORY=1。请参阅 安全部署。
​
项目说明（CLAUDE.md 和规则）
CLAUDE.md 文件和 .claude/rules/*.md 文件为您的代理提供关于您的项目的持久上下文：编码约定、构建命令、架构决策和说明。当 settingSources 包含 "project"（如上面的示例）时，SDK 在会话开始时将这些文件加载到上下文中。然后代理遵循您的项目约定，而无需在每个提示中重复它们。
​
CLAUDE.md 加载位置
级别	位置	加载时间
项目（根）	<cwd>/CLAUDE.md 或 <cwd>/.claude/CLAUDE.md	settingSources 包含 "project"
项目规则	<cwd>/.claude/rules/*.md 和 .claude/rules/*.md 在每个父目录中	settingSources 包含 "project"
项目（父目录）	cwd 上方目录中的 CLAUDE.md 文件	settingSources 包含 "project"，在会话开始时加载
项目（子目录）	cwd 子目录中的 CLAUDE.md 文件	settingSources 包含 "project"，当代理读取该子树中的文件时按需加载
本地	<cwd>/CLAUDE.local.md 和 CLAUDE.local.md 在每个父目录中	settingSources 包含 "local"
用户	~/.claude/CLAUDE.md	settingSources 包含 "user"
用户规则	~/.claude/rules/*.md	settingSources 包含 "user"
所有级别都是累加的：如果项目和用户 CLAUDE.md 文件都存在，代理会看到两者。级别之间没有硬优先级规则；如果说明冲突，结果取决于 Claude 如何解释它们。编写不冲突的规则，或在更具体的文件中明确说明优先级（“这些项目说明覆盖任何冲突的用户级默认值”）。
您也可以通过 systemPrompt 直接注入上下文，而无需使用 CLAUDE.md 文件。请参阅 修改系统提示。当您希望在交互式 Claude Code 会话和 SDK 代理之间共享相同的上下文时，使用 CLAUDE.md。
有关如何构建和组织 CLAUDE.md 内容，请参阅 管理 Claude 的内存。
​
Skills
Skills 是 markdown 文件，为您的代理提供专业知识和可调用的工作流。与 CLAUDE.md（每个会话都加载）不同，skills 按需加载。代理在启动时接收 skill 描述，并在相关时加载完整内容。
Skills 通过 settingSources 从文件系统中发现。当 query() 上的 skills 选项被省略时，发现的用户和项目 skills 会被启用，Skill 工具可用，与 CLI 行为相匹配。要控制启用哪些 skills，请将 skills 作为 "all"、skill 名称列表或 [] 传递以禁用所有。SDK 在设置 skills 时会自动启用 Skill 工具，因此您无需将其添加到 allowedTools。
Python
TypeScript
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

# Skills in .claude/skills/ are discovered automatically
# when settingSources includes "project"
async for message in query(
    prompt="Review this PR using our code review checklist",
    options=ClaudeAgentOptions(
        setting_sources=["user", "project"],
        skills="all",
        allowed_tools=["Read", "Grep", "Glob"],
    ),
):
    if isinstance(message, ResultMessage) and message.subtype == "success":
        print(message.result)

Skills 必须创建为文件系统工件（.claude/skills/<name>/SKILL.md）。SDK 没有用于注册 skills 的编程 API。有关完整详情，请参阅 SDK 中的 Agent Skills。
有关创建和使用 skills 的更多信息，请参阅 SDK 中的 Agent Skills。
​
Hooks
SDK 支持两种定义 hooks 的方式，它们并行运行：
文件系统 hooks： 在 settings.json 中定义的 shell 命令，当 settingSources 包含相关源时加载。这些与您为 交互式 Claude Code 会话 配置的 hooks 相同。
编程 hooks： 直接传递给 query() 的回调函数。这些在您的应用程序进程中运行，可以返回结构化决策。请参阅 使用 hooks 控制执行。
两种类型在相同的 hook 生命周期中执行。如果您已经在项目的 .claude/settings.json 中有 hooks，并且您设置 settingSources: ["project"]，那些 hooks 会在 SDK 中自动运行，无需额外配置。
Hook 回调接收工具输入并返回决策字典。返回 {}（空字典）意味着允许工具继续。返回 {"decision": "block", "reason": "..."} 会阻止执行，原因会作为工具结果发送给 Claude。有关完整的回调签名和返回类型，请参阅 hooks 指南。
Python
TypeScript
from claude_agent_sdk import query, ClaudeAgentOptions, HookMatcher, ResultMessage


# PreToolUse hook callback. Positional args:
#   input_data: HookInput dict with tool_name, tool_input, hook_event_name
#   tool_use_id: str | None, the ID of the tool call being intercepted
#   context: HookContext, carries session metadata
async def audit_bash(input_data, tool_use_id, context):
    command = input_data.get("tool_input", {}).get("command", "")
    if "rm -rf" in command:
        return {"decision": "block", "reason": "Destructive command blocked"}
    return {}  # Empty dict: allow the tool to proceed


# Filesystem hooks from .claude/settings.json run automatically
# when settingSources loads them. You can also add programmatic hooks:
async for message in query(
    prompt="Refactor the auth module",
    options=ClaudeAgentOptions(
        setting_sources=["project"],  # Loads hooks from .claude/settings.json
        hooks={
            "PreToolUse": [
                HookMatcher(matcher="Bash", hooks=[audit_bash]),
            ]
        },
    ),
):
    if isinstance(message, ResultMessage) and message.subtype == "success":
        print(message.result)

​
何时使用哪种 hook 类型
Hook 类型	最适合
文件系统（settings.json）	在 CLI 和 SDK 会话之间共享 hooks。支持 "command"（shell 脚本）、"http"（POST 到端点）、"mcp_tool"（调用连接的 MCP 服务器的工具）、"prompt"（LLM 评估提示）和 "agent"（生成验证器代理）。这些在主代理和它生成的任何子代理中触发。
编程（query() 中的回调）	应用程序特定的逻辑；返回结构化决策；进程内集成。仅限于主会话。
TypeScript SDK 支持超出 Python 的其他 hook 事件，包括 SessionStart、SessionEnd、TeammateIdle 和 TaskCompleted。有关完整的事件兼容性表，请参阅 hooks 指南。
有关编程 hooks 的完整详情，请参阅 使用 hooks 控制执行。有关文件系统 hook 语法，请参阅 Hooks。
​
选择正确的功能
Agent SDK 为您提供了多种方式来扩展代理的行为。如果您不确定使用哪种，此表将常见目标映射到正确的方法。
您想要…	使用	SDK 表面
设置代理始终遵循的项目约定	CLAUDE.md	settingSources: ["project"] 自动加载它
为代理提供它在相关时加载的参考材料	Skills	settingSources + skills 选项
运行可重用的工作流（部署、审查、发布）	用户可调用的 skills	settingSources + skills 选项
将隔离的子任务委托给新的上下文（研究、审查）	子代理	agents 参数 + allowedTools: ["Agent"]
协调多个 Claude Code 实例，具有共享任务列表和直接的代理间消息传递	代理团队	不直接通过 SDK 选项配置。代理团队是一个 CLI 功能，其中一个会话充当团队负责人，协调独立队友之间的工作
在工具调用上运行确定性逻辑（审计、阻止、转换）	Hooks	hooks 参数带回调，或通过 settingSources 加载的 shell 脚本
为 Claude 提供对外部服务的结构化工具访问	MCP	mcpServers 参数
子代理与代理团队： 子代理是临时的和隔离的：新对话、一个任务、摘要返回给父代理。代理团队协调多个独立的 Claude Code 实例，这些实例共享任务列表并直接相互消息传递。代理团队是一个 CLI 功能。有关详情，请参阅 子代理继承的内容 和 代理团队比较。
您启用的每个功能都会增加代理的上下文窗口。有关每个功能的成本以及这些功能如何分层组合，请参阅 扩展 Claude Code。
​
相关资源
扩展 Claude Code：所有扩展功能的概念概述，包含比较表和上下文成本分析
SDK 中的 Skills：使用 skills 的完整指南
子代理：为隔离的子任务定义和调用子代理
Hooks：在关键执行点拦截和控制代理行为
权限：使用模式、规则和回调控制工具访问
系统提示：在不使用 CLAUDE.md 文件的情况下注入上下文

此页面对您有帮助吗？

是
否
代理循环如何工作
使用会话
⌘I

---

# 使用会话

> 章节: 核心概念 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/sessions

---

核心概念
使用会话

会话如何保持代理对话历史记录，以及何时使用 continue、resume 和 fork 返回到之前的运行。

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

会话是 SDK 在代理工作时积累的对话历史记录。它包含您的提示、代理进行的每个工具调用、每个工具结果和每个响应。SDK 会自动将其写入磁盘，以便您稍后可以返回到它。
返回到会话意味着代理具有之前的完整上下文：它已经读取的文件、它已经执行的分析、它已经做出的决定。您可以提出后续问题、从中断中恢复或分支以尝试不同的方法。
会话保持对话，而不是文件系统。要快照和还原代理所做的文件更改，请使用文件检查点。
本指南涵盖如何为您的应用选择正确的方法、自动跟踪会话的 SDK 接口、如何捕获会话 ID 以及手动使用 resume 和 fork 的方法，以及关于在主机之间恢复会话需要了解的内容。
​
选择一种方法
您需要多少会话处理取决于应用的形状。当您发送应该共享上下文的多个提示时，会话管理就会发挥作用。在单个 query() 调用中，代理已经根据需要进行了尽可能多的轮次，权限提示和 AskUserQuestion 是在循环中处理的（它们不会结束调用）。
您正在构建的内容	使用什么
一次性任务：单个提示，无后续	无需额外操作。一个 query() 调用可以处理它。
在一个进程中进行多轮聊天	ClaudeSDKClient（Python）或 continue: true（TypeScript）。SDK 为您跟踪会话，无需 ID 处理。
在进程重启后从中断处继续	continue_conversation=True（Python）/ continue: true（TypeScript）。恢复目录中最近的会话，无需 ID。
恢复特定的过去会话（不是最近的）	捕获会话 ID 并将其传递给 resume。
尝试替代方法而不丢失原始方法	Fork 会话。
无状态任务，不希望任何内容写入磁盘（仅 TypeScript）	设置 persistSession: false。会话仅在调用期间存在于内存中。Python 始终保持到磁盘。
​
Continue、resume 和 fork
Continue、resume 和 fork 是您在 query() 上设置的选项字段（Python 中的 ClaudeAgentOptions，TypeScript 中的 Options）。
Continue 和 resume 都会选择现有会话并添加到其中。区别在于它们如何找到该会话：
Continue 在当前目录中查找最近的会话。您无需跟踪任何内容。当您的应用一次运行一个对话时效果很好。
Resume 采用特定的会话 ID。您跟踪 ID。当您有多个会话（例如，多用户应用中每个用户一个）或想要返回到不是最近的会话时需要。
Fork 不同：它创建一个新会话，从原始会话历史记录的副本开始。原始会话保持不变。使用 fork 尝试不同的方向，同时保持返回的选项。
​
自动会话管理
两个 SDK 都提供了一个接口，可以跨调用为您跟踪会话状态，因此您无需手动传递 ID。将这些用于单个进程中的多轮对话。
​
Python：ClaudeSDKClient
ClaudeSDKClient 在内部处理会话 ID。每次调用 client.query() 都会自动继续同一会话。调用 client.receive_response() 以迭代当前查询的消息。客户端通常用作异步上下文管理器。
此示例针对同一 client 运行两个查询。第一个要求代理分析一个模块；第二个要求它重构该模块。因为两个调用都通过同一客户端实例进行，第二个查询具有来自第一个查询的完整上下文，无需任何显式 resume 或会话 ID：
Python
import asyncio
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
)


def print_response(message):
    """Print only the human-readable parts of a message."""
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                print(block.text)
    elif isinstance(message, ResultMessage):
        cost = (
            f"${message.total_cost_usd:.4f}"
            if message.total_cost_usd is not None
            else "N/A"
        )
        print(f"[done: {message.subtype}, cost: {cost}]")


async def main():
    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Edit", "Glob", "Grep"],
    )

    async with ClaudeSDKClient(options=options) as client:
        # First query: client captures the session ID internally
        await client.query("Analyze the auth module")
        async for message in client.receive_response():
            print_response(message)

        # Second query: automatically continues the same session
        await client.query("Now refactor it to use JWT")
        async for message in client.receive_response():
            print_response(message)


asyncio.run(main())

有关何时使用 ClaudeSDKClient 与独立 query() 函数的详细信息，请参阅 Python SDK 参考。
​
TypeScript：continue: true
TypeScript SDK 没有像 Python 的 ClaudeSDKClient 那样的会话保持客户端对象。相反，在每个后续 query() 调用上传递 continue: true，SDK 会在当前目录中选择最近的会话。无需 ID 跟踪。
此示例进行两个单独的 query() 调用。第一个创建一个新会话；第二个设置 continue: true，这告诉 SDK 在磁盘上查找并恢复最近的会话。代理具有来自第一个调用的完整上下文：
TypeScript
import { query } from "@anthropic-ai/claude-agent-sdk";

// First query: creates a new session
for await (const message of query({
  prompt: "Analyze the auth module",
  options: { allowedTools: ["Read", "Glob", "Grep"] }
})) {
  if (message.type === "result" && message.subtype === "success") {
    console.log(message.result);
  }
}

// Second query: continue: true resumes the most recent session
for await (const message of query({
  prompt: "Now refactor it to use JWT",
  options: {
    continue: true,
    allowedTools: ["Read", "Edit", "Write", "Glob", "Grep"]
  }
})) {
  if (message.type === "result" && message.subtype === "success") {
    console.log(message.result);
  }
}

实验性的 V2 会话 API（提供了带有 send / stream 模式的 createSession()）已在 TypeScript Agent SDK 0.3.142 中移除。使用 query() 函数和本页面上描述的会话选项。
​
将会话选项与 query() 一起使用
​
捕获会话 ID
Resume 和 fork 需要会话 ID。从结果消息上的 session_id 字段读取它（Python 中的 ResultMessage，TypeScript 中的 SDKResultMessage），该字段存在于每个结果上，无论成功还是错误。在 TypeScript 中，ID 也可以作为初始化 SystemMessage 上的直接字段更早获得；在 Python 中，它嵌套在 SystemMessage.data 内。
Python
TypeScript
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage


async def main():
    session_id = None

    async for message in query(
        prompt="Analyze the auth module and suggest improvements",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Glob", "Grep"],
        ),
    ):
        if isinstance(message, ResultMessage):
            session_id = message.session_id
            if message.subtype == "success":
                print(message.result)

    print(f"Session ID: {session_id}")
    return session_id


session_id = asyncio.run(main())

​
按 ID 恢复
将会话 ID 传递给 resume 以返回到该特定会话。代理从会话中断的任何地方继续，具有完整的上下文。恢复的常见原因：
跟进已完成的任务。 代理已经分析了某些内容；现在您希望它根据该分析采取行动，而无需重新读取文件。
从限制中恢复。 第一次运行以 error_max_turns 或 error_max_budget_usd 结束（请参阅处理结果）；使用更高的限制恢复。
重启您的进程。 您在关闭前捕获了 ID，并希望恢复对话。
此示例使用后续提示恢复捕获会话 ID 中的会话。因为您正在恢复，代理已经在上下文中具有先前的分析：
Python
TypeScript
# Earlier session analyzed the code; now build on that analysis
async for message in query(
    prompt="Now implement the refactoring you suggested",
    options=ClaudeAgentOptions(
        resume=session_id,
        allowed_tools=["Read", "Edit", "Write", "Glob", "Grep"],
    ),
):
    if isinstance(message, ResultMessage) and message.subtype == "success":
        print(message.result)

如果 resume 调用返回新会话而不是预期的历史记录，最常见的原因是不匹配的 cwd。会话存储在 ~/.claude/projects/<encoded-cwd>/*.jsonl 下，其中 <encoded-cwd> 是绝对工作目录，每个非字母数字字符都被替换为 -（所以 /Users/me/proj 变成 -Users-me-proj）。如果您的 resume 调用从不同的目录运行，SDK 会在错误的位置查找。会话文件也需要存在于当前机器上。
要在机器之间或在无服务器环境中恢复会话，请使用 SessionStore 适配器将记录镜像到共享存储。
​
Fork 以探索替代方案
Forking 创建一个新会话，从原始会话历史记录的副本开始，但从该点开始分支。fork 获得自己的会话 ID；原始的 ID 和历史记录保持不变。您最终会得到两个独立的会话，可以分别恢复。
Forking 分支对话历史记录，而不是文件系统。如果 forked 代理编辑文件，这些更改是真实的，对在同一目录中工作的任何会话都可见。要分支和还原文件更改，请使用文件检查点。
此示例基于捕获会话 ID：您已经在 session_id 中分析了一个身份验证模块，并希望探索 OAuth2 而不丢失 JWT 焦点线程。第一个块 forks 会话并捕获 fork 的 ID（forked_id）；第二个块恢复原始 session_id 以继续沿着 JWT 路径。您现在有两个会话 ID 指向两个单独的历史记录：
Python
TypeScript
# Fork: branch from session_id into a new session
forked_id = None
async for message in query(
    prompt="Instead of JWT, implement OAuth2 for the auth module",
    options=ClaudeAgentOptions(
        resume=session_id,
        fork_session=True,
    ),
):
    if isinstance(message, ResultMessage):
        forked_id = message.session_id  # The fork's ID, distinct from session_id
        if message.subtype == "success":
            print(message.result)

print(f"Forked session: {forked_id}")

# Original session is untouched; resuming it continues the JWT thread
async for message in query(
    prompt="Continue with the JWT approach",
    options=ClaudeAgentOptions(resume=session_id),
):
    if isinstance(message, ResultMessage) and message.subtype == "success":
        print(message.result)

​
跨主机恢复
会话文件是创建它们的机器的本地文件。要在不同的主机上恢复会话（CI 工作者、临时容器、无服务器），您有两个选项：
移动会话文件。 从第一次运行中保持 ~/.claude/projects/<encoded-cwd>/<session-id>.jsonl，并在调用 resume 之前将其恢复到新主机上的相同路径。cwd 必须匹配。
不依赖会话恢复。 捕获您需要的结果（分析输出、决定、文件差异）作为应用状态，并将其传递到新会话的提示中。这通常比在周围运送记录文件更强大。
两个 SDK 都公开了用于枚举磁盘上的会话和读取其消息的函数：TypeScript 中的 listSessions() 和 getSessionMessages()，Python 中的 list_sessions() 和 get_session_messages()。使用它们来构建自定义会话选择器、清理逻辑或记录查看器。
两个 SDK 也公开了用于查找和改变单个会话的函数：Python 中的 get_session_info()、rename_session() 和 tag_session()，以及 TypeScript 中的 getSessionInfo()、renameSession() 和 tagSession()。使用它们按标签组织会话或给它们人类可读的标题。
​
相关资源
代理循环如何工作：了解会话中的轮次、消息和上下文累积
文件检查点：跟踪和还原会话中的文件更改
Python ClaudeAgentOptions：Python 的完整会话选项参考
TypeScript Options：TypeScript 的完整会话选项参考

此页面对您有帮助吗？

是
否
使用 Claude Code 功能
流式输入
⌘I

---

# 流式输入

> 章节: 输入和输出 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/streaming-vs-single-mode

---

输入和输出
流式输入

理解 Claude Agent SDK 的两种输入模式及何时使用每种模式

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

​
概述
Claude Agent SDK 支持两种不同的输入模式来与代理交互：
流式输入模式（默认和推荐）- 一个持久的、交互式的会话
单消息输入 - 使用会话状态和恢复的一次性查询
本指南解释了每种模式的差异、优势和用例，以帮助您为应用程序选择正确的方法。
​
流式输入模式（推荐）
流式输入模式是使用 Claude Agent SDK 的首选方式。它提供对代理功能的完全访问，并支持丰富的交互式体验。
它允许代理作为一个长期运行的进程运行，接收用户输入、处理中断、显示权限请求并处理会话管理。
​
工作原理
Environment/
File System
Tools/Hooks
Claude Agent
Your Application
Environment/
File System
Tools/Hooks
Claude Agent
Your Application
Session stays alive
Persistent file system
state maintained
Initialize with AsyncGenerator
Yield Message 1
Execute tools
Read files
File contents
Write/Edit files
Success/Error
Stream partial response
Stream more content...
Complete Message 1
Yield Message 2 + Image
Process image & execute
Access filesystem
Operation results
Stream response 2
Queue Message 3
Interrupt/Cancel
Handle interruption
​
优势
图像上传
直接将图像附加到消息中以进行视觉分析和理解
队列消息
发送多条按顺序处理的消息，具有中断能力
工具集成
在会话期间完全访问所有工具和自定义 MCP 服务器
Hooks 支持
使用生命周期 hooks 在各个点自定义行为
实时反馈
查看生成的响应，而不仅仅是最终结果
上下文持久性
自然地跨多个回合维护对话上下文
​
实现示例
TypeScript
Python
import { query, type SDKUserMessage } from "@anthropic-ai/claude-agent-sdk";
import { readFile } from "fs/promises";

async function* generateMessages(): AsyncGenerator<SDKUserMessage> {
  // First message
  yield {
    type: "user",
    message: {
      role: "user",
      content: "Analyze this codebase for security issues"
    },
    parent_tool_use_id: null
  };

  // Wait for conditions or user input
  await new Promise((resolve) => setTimeout(resolve, 2000));

  // Follow-up with image
  yield {
    type: "user",
    message: {
      role: "user",
      content: [
        {
          type: "text",
          text: "Review this architecture diagram"
        },
        {
          type: "image",
          source: {
            type: "base64",
            media_type: "image/png",
            data: await readFile("diagram.png", "base64")
          }
        }
      ]
    },
    parent_tool_use_id: null
  };
}

// Process streaming responses
for await (const message of query({
  prompt: generateMessages(),
  options: {
    maxTurns: 10,
    allowedTools: ["Read", "Grep"]
  }
})) {
  if (message.type === "result" && message.subtype === "success") {
    console.log(message.result);
  }
}

​
单消息输入
单消息输入更简单但功能更受限。
​
何时使用单消息输入
在以下情况下使用单消息输入：
您需要一次性响应
您不需要图像附件、hooks 等
您需要在无状态环境中运行，例如 lambda 函数
​
限制
单消息输入模式不支持：
消息中的直接图像附件
动态消息队列
实时中断
Hook 集成
自然的多轮对话
​
实现示例
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

// Simple one-shot query
for await (const message of query({
  prompt: "Explain the authentication flow",
  options: {
    maxTurns: 1,
    allowedTools: ["Read", "Grep"]
  }
})) {
  if (message.type === "result" && message.subtype === "success") {
    console.log(message.result);
  }
}

// Continue conversation with session management
for await (const message of query({
  prompt: "Now explain the authorization process",
  options: {
    continue: true,
    maxTurns: 1
  }
})) {
  if (message.type === "result" && message.subtype === "success") {
    console.log(message.result);
  }
}


此页面对您有帮助吗？

是
否
使用会话
处理批准和用户输入
⌘I

---

# 处理批准和用户输入

> 章节: 输入和输出 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/user-input

---

输入和输出
处理批准和用户输入

向用户显示 Claude 的批准请求和澄清问题，然后将他们的决定返回给 SDK。

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

在处理任务时，Claude 有时需要与用户进行沟通。它可能需要在删除文件前获得许可，或需要询问为新项目使用哪个数据库。您的应用程序需要向用户显示这些请求，以便 Claude 可以继续使用他们的输入。
Claude 在两种情况下请求用户输入：当它需要使用工具的权限（如删除文件或运行命令）时，以及当它有澄清问题（通过 AskUserQuestion 工具）时。两者都会触发您的 canUseTool 回调，该回调会暂停执行，直到您返回响应。这与普通对话轮次不同，在普通对话轮次中 Claude 完成后等待您的下一条消息。
对于澄清问题，Claude 生成问题和选项。您的角色是向用户呈现这些问题，并返回他们的选择。您不能向此流程添加自己的问题；如果您需要自己询问用户某些内容，请在应用程序逻辑中单独进行。
回调可以无限期地保持待处理状态。执行保持暂停状态，直到您的回调返回，SDK 仅在查询本身被取消时才取消等待。如果用户可能需要比您的进程能够合理保持运行的时间更长的时间来响应，请返回 defer hook 决定，它允许进程退出并稍后从持久化会话恢复。
本指南向您展示如何检测每种类型的请求并做出适当的响应。
​
检测 Claude 何时需要输入
在您的查询选项中传递 canUseTool 回调。每当 Claude 需要用户输入时，回调就会触发，接收工具名称和输入作为参数：
Python
TypeScript
async def handle_tool_request(tool_name, input_data, context):
    # 提示用户并返回允许或拒绝
    ...


options = ClaudeAgentOptions(can_use_tool=handle_tool_request)

回调在两种情况下触发：
工具需要批准：Claude 想要使用不被权限规则或模式自动批准的工具。检查 tool_name 以获取工具（例如 "Bash"、"Write"）。
Claude 提出问题：Claude 调用 AskUserQuestion 工具。检查 tool_name == "AskUserQuestion" 以不同方式处理它。如果您指定 tools 数组，请包含 AskUserQuestion 以使其工作。有关详细信息，请参阅处理澄清问题。
要自动允许或拒绝工具而不提示用户，请改用 hooks。Hooks 在 canUseTool 之前执行，可以根据您自己的逻辑允许、拒绝或修改请求。您还可以使用 PermissionRequest hook 在 Claude 等待批准时发送外部通知（Slack、电子邮件、推送）。
​
处理工具批准请求
一旦您在查询选项中传递了 canUseTool 回调，当 Claude 想要使用不被自动批准的工具时，它就会触发。您的回调接收三个参数：
参数	描述
toolName	Claude 想要使用的工具的名称（例如 "Bash"、"Write"、"Edit"）
input	Claude 传递给工具的参数。内容因工具而异。
options (TS) / context (Python)	附加上下文，包括可选的 suggestions（建议的 PermissionUpdate 条目以避免重新提示）和取消信号。在 TypeScript 中，signal 是 AbortSignal；在 Python 中，信号字段保留供将来使用。有关 Python，请参阅 ToolPermissionContext。
input 对象包含工具特定的参数。常见示例：
工具	输入字段
Bash	command、description、timeout
Write	file_path、content
Edit	file_path、old_string、new_string
Read	file_path、offset、limit
有关完整的输入架构，请参阅 SDK 参考：Python | TypeScript。
您可以向用户显示此信息，以便他们可以决定是否允许或拒绝该操作，然后返回适当的响应。
以下示例要求 Claude 创建和删除测试文件。当 Claude 尝试每个操作时，回调会将工具请求打印到终端并提示进行 y/n 批准。
Python
TypeScript
import asyncio

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query
from claude_agent_sdk.types import (
    HookMatcher,
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)


async def can_use_tool(
    tool_name: str, input_data: dict, context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    # 显示工具请求
    print(f"\nTool: {tool_name}")
    if tool_name == "Bash":
        print(f"Command: {input_data.get('command')}")
        if input_data.get("description"):
            print(f"Description: {input_data.get('description')}")
    else:
        print(f"Input: {input_data}")

    # 获取用户批准
    response = input("Allow this action? (y/n): ")

    # 根据用户的响应返回允许或拒绝
    if response.lower() == "y":
        # 允许：工具使用原始（或修改的）输入执行
        return PermissionResultAllow(updated_input=input_data)
    else:
        # 拒绝：工具不执行，Claude 看到该消息
        return PermissionResultDeny(message="User denied this action")


# 必需的解决方法：虚拟 hook 保持流打开以供 can_use_tool 使用
async def dummy_hook(input_data, tool_use_id, context):
    return {"continue_": True}


async def prompt_stream():
    yield {
        "type": "user",
        "message": {
            "role": "user",
            "content": "Create a test file in /tmp and then delete it",
        },
    }


async def main():
    async for message in query(
        prompt=prompt_stream(),
        options=ClaudeAgentOptions(
            can_use_tool=can_use_tool,
            hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[dummy_hook])]},
        ),
    ):
        if isinstance(message, ResultMessage) and message.subtype == "success":
            print(message.result)


asyncio.run(main())

在 Python 中，can_use_tool 需要流模式和返回 {"continue_": True} 的 PreToolUse hook 以保持流打开。没有此 hook，流会在权限回调被调用之前关闭。
此示例使用 y/n 流，其中除 y 之外的任何输入都被视为拒绝。在实践中，您可能会构建一个更丰富的 UI，让用户修改请求、提供反馈或完全重定向 Claude。有关所有响应方式，请参阅响应工具请求。
​
响应工具请求
您的回调返回两种响应类型之一：
响应	Python	TypeScript
允许	PermissionResultAllow(updated_input=...)	{ behavior: "allow", updatedInput }
拒绝	PermissionResultDeny(message=...)	{ behavior: "deny", message }
允许时，传递工具输入（原始或修改的）。拒绝时，提供说明原因的消息。Claude 会看到此消息并可能调整其方法。
Python
TypeScript
from claude_agent_sdk.types import PermissionResultAllow, PermissionResultDeny

# 允许工具执行
return PermissionResultAllow(updated_input=input_data)

# 阻止工具
return PermissionResultDeny(message="User rejected this action")

除了允许或拒绝之外，您还可以修改工具的输入或提供帮助 Claude 调整其方法的上下文：
批准：让工具按 Claude 请求的方式执行
批准并进行更改：在执行前修改输入（例如，清理路径、添加约束）
批准并记住：回显建议的权限规则，以便匹配的调用在下次跳过提示
拒绝：阻止工具并告诉 Claude 原因
建议替代方案：阻止但指导 Claude 朝向用户想要的方向
完全重定向：使用流输入向 Claude 发送全新指令
批准
批准并进行更改
批准并记住
拒绝
建议替代方案
完全重定向
用户按原样批准该操作。从您的回调中传递 input 不变，工具完全按 Claude 请求的方式执行。
Python
TypeScript
async def can_use_tool(tool_name, input_data, context):
    print(f"Claude wants to use {tool_name}")
    approved = await ask_user("Allow this action?")

    if approved:
        return PermissionResultAllow(updated_input=input_data)
    return PermissionResultDeny(message="User declined")

​
处理澄清问题
当 Claude 需要在具有多个有效方法的任务上获得更多指导时，它会调用 AskUserQuestion 工具。这会触发您的 canUseTool 回调，其中 toolName 设置为 AskUserQuestion。输入包含 Claude 的问题作为多选选项，您向用户显示这些问题并返回他们的选择。
澄清问题在 plan 模式中特别常见，其中 Claude 探索代码库并在提出计划前提出问题。这使 plan 模式非常适合交互式工作流，您希望 Claude 在进行更改前收集需求。
以下步骤显示如何处理澄清问题：
1

传递 canUseTool 回调

在您的查询选项中传递 canUseTool 回调。默认情况下，AskUserQuestion 可用。如果您指定 tools 数组来限制 Claude 的功能（例如，仅具有 Read、Glob 和 Grep 的只读代理），请在该数组中包含 AskUserQuestion。否则，Claude 将无法提出澄清问题：
Python
TypeScript
async for message in query(
    prompt="Analyze this codebase",
    options=ClaudeAgentOptions(
        # 在您的工具列表中包含 AskUserQuestion
        tools=["Read", "Glob", "Grep", "AskUserQuestion"],
        can_use_tool=can_use_tool,
    ),
):
    print(message)

2

检测 AskUserQuestion

在您的回调中，检查 toolName 是否等于 AskUserQuestion 以不同方式处理它与其他工具：
Python
TypeScript
async def can_use_tool(tool_name: str, input_data: dict, context):
    if tool_name == "AskUserQuestion":
        # 您从用户收集答案的实现
        return await handle_clarifying_questions(input_data)
    # 正常处理其他工具
    return await prompt_for_approval(tool_name, input_data)

3

解析问题输入

输入包含 Claude 在 questions 数组中的问题。每个问题都有 question（要显示的文本）、options（选择）和 multiSelect（是否允许多个选择）：
{
  "questions": [
    {
      "question": "How should I format the output?",
      "header": "Format",
      "options": [
        { "label": "Summary", "description": "Brief overview" },
        { "label": "Detailed", "description": "Full explanation" }
      ],
      "multiSelect": false
    },
    {
      "question": "Which sections should I include?",
      "header": "Sections",
      "options": [
        { "label": "Introduction", "description": "Opening context" },
        { "label": "Conclusion", "description": "Final summary" }
      ],
      "multiSelect": true
    }
  ]
}

有关完整字段描述，请参阅问题格式。
4

从用户收集答案

向用户呈现问题并收集他们的选择。您如何执行此操作取决于您的应用程序：终端提示、Web 表单、移动对话框等。
5

将答案返回给 Claude

将 answers 对象构建为记录，其中每个键是 question 文本，每个值是所选选项的 label：
来自问题对象	用作
question 字段（例如 "How should I format the output?"）	键
所选选项的 label 字段（例如 "Summary"）	值
对于多选问题，传递标签数组或用 ", " 连接它们。如果您支持自由文本输入，使用用户的自定义文本作为值。
Python
TypeScript
return PermissionResultAllow(
    updated_input={
        "questions": input_data.get("questions", []),
        "answers": {
            "How should I format the output?": "Summary",
            "Which sections should I include?": ["Introduction", "Conclusion"],
        },
    }
)

​
问题格式
输入包含 Claude 在 questions 数组中生成的问题。每个问题都有这些字段：
字段	描述
question	要显示的完整问题文本
header	问题的短标签（最多 12 个字符）
options	2-4 个选择的数组，每个都有 label 和 description。TypeScript：可选 preview（请参阅下文）
multiSelect	如果为 true，用户可以选择多个选项
您的回调接收的结构：
{
  "questions": [
    {
      "question": "How should I format the output?",
      "header": "Format",
      "options": [
        { "label": "Summary", "description": "Brief overview of key points" },
        { "label": "Detailed", "description": "Full explanation with examples" }
      ],
      "multiSelect": false
    }
  ]
}

​
选项预览 (TypeScript)
toolConfig.askUserQuestion.previewFormat 向每个选项添加 preview 字段，以便您的应用可以在标签旁显示视觉模型。没有此设置，Claude 不会生成预览，该字段不存在。
previewFormat	preview 包含
未设置（默认）	字段不存在。Claude 不会生成预览。
"markdown"	ASCII 艺术和围栏代码块
"html"	样式的 <div> 片段（SDK 在您的回调运行前拒绝 <script>、<style> 和 <!DOCTYPE>）
该格式适用于会话中的所有问题。Claude 在视觉比较有帮助的选项上包含 preview（布局选择、配色方案），并在不会的地方省略它（是/否确认、仅文本选择）。在呈现前检查 undefined。
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Help me choose a card layout",
  options: {
    toolConfig: {
      askUserQuestion: { previewFormat: "html" }
    },
    canUseTool: async (toolName, input) => {
      // input.questions[].options[].preview 是 HTML 字符串或 undefined
      return { behavior: "allow", updatedInput: input };
    }
  }
})) {
  // ...
}

带有 HTML 预览的选项：
{
  "label": "Compact",
  "description": "Title and metric value only",
  "preview": "<div style=\"padding:12px;border:1px solid #ddd;border-radius:8px\"><div style=\"font-size:12px;color:#666\">Active users</div><div style=\"font-size:28px;font-weight:600\">1,284</div></div>"
}

​
响应格式
返回 answers 对象，将每个问题的 question 字段映射到所选选项的 label：
字段	描述
questions	传递原始问题数组（工具处理需要）
answers	对象，其中键是问题文本，值是所选标签
对于多选问题，传递标签数组或用 ", " 连接它们。对于自由文本输入，直接使用用户的自定义文本。
{
  "questions": [
    // ...
  ],
  "answers": {
    "How should I format the output?": "Summary",
    "Which sections should I include?": ["Introduction", "Conclusion"]
  }
}

​
支持自由文本输入
Claude 的预定义选项并不总是涵盖用户想要的内容。要让用户输入自己的答案：
在 Claude 的选项后显示额外的”其他”选择，接受文本输入
使用用户的自定义文本作为答案值（不是单词”其他”）
有关完整实现，请参阅下面的完整示例。
​
完整示例
当 Claude 需要用户输入来继续时，它会提出澄清问题。例如，当被要求帮助为移动应用程序决定技术栈时，Claude 可能会询问跨平台与原生、后端偏好或目标平台。这些问题帮助 Claude 做出与用户偏好相匹配的决定，而不是猜测。
此示例在终端应用程序中处理这些问题。以下是每个步骤发生的情况：
路由请求：canUseTool 回调检查工具名称是否为 "AskUserQuestion" 并路由到专用处理程序
显示问题：处理程序循环遍历 questions 数组并打印每个问题及编号选项
收集输入：用户可以输入数字来选择选项，或直接输入自由文本（例如”jquery”、“i don’t know”）
映射答案：代码检查输入是数字（使用选项的标签）还是自由文本（使用文本直接）
返回给 Claude：响应包括原始 questions 数组和 answers 映射
Python
TypeScript
import asyncio

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query
from claude_agent_sdk.types import HookMatcher, PermissionResultAllow


def parse_response(response: str, options: list) -> str:
    """将用户输入解析为选项编号或自由文本。"""
    try:
        indices = [int(s.strip()) - 1 for s in response.split(",")]
        labels = [options[i]["label"] for i in indices if 0 <= i < len(options)]
        return ", ".join(labels) if labels else response
    except ValueError:
        return response


async def handle_ask_user_question(input_data: dict) -> PermissionResultAllow:
    """显示 Claude 的问题并收集用户答案。"""
    answers = {}

    for q in input_data.get("questions", []):
        print(f"\n{q['header']}: {q['question']}")

        options = q["options"]
        for i, opt in enumerate(options):
            print(f"  {i + 1}. {opt['label']} - {opt['description']}")
        if q.get("multiSelect"):
            print("  (Enter numbers separated by commas, or type your own answer)")
        else:
            print("  (Enter a number, or type your own answer)")

        response = input("Your choice: ").strip()
        answers[q["question"]] = parse_response(response, options)

    return PermissionResultAllow(
        updated_input={
            "questions": input_data.get("questions", []),
            "answers": answers,
        }
    )


async def can_use_tool(
    tool_name: str, input_data: dict, context
) -> PermissionResultAllow:
    # 将 AskUserQuestion 路由到我们的问题处理程序
    if tool_name == "AskUserQuestion":
        return await handle_ask_user_question(input_data)
    # 为此示例自动批准其他工具
    return PermissionResultAllow(updated_input=input_data)


async def prompt_stream():
    yield {
        "type": "user",
        "message": {
            "role": "user",
            "content": "Help me decide on the tech stack for a new mobile app",
        },
    }


# 必需的解决方法：虚拟 hook 保持流打开以供 can_use_tool 使用
async def dummy_hook(input_data, tool_use_id, context):
    return {"continue_": True}


async def main():
    async for message in query(
        prompt=prompt_stream(),
        options=ClaudeAgentOptions(
            can_use_tool=can_use_tool,
            hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[dummy_hook])]},
        ),
    ):
        if isinstance(message, ResultMessage) and message.subtype == "success":
            print(message.result)


asyncio.run(main())

​
限制
子代理：AskUserQuestion 目前在通过 Agent 工具生成的子代理中不可用
问题限制：每个 AskUserQuestion 调用支持 1-4 个问题，每个 2-4 个选项
​
获取用户输入的其他方式
canUseTool 回调和 AskUserQuestion 工具涵盖了大多数批准和澄清场景，但 SDK 提供了其他从用户获取输入的方式：
​
流输入
当您需要以下情况时，使用流输入：
在任务中断代理：在 Claude 工作时发送取消信号或改变方向
提供额外上下文：添加 Claude 需要的信息而无需等待它提出问题
构建聊天界面：让用户在长时间运行的操作期间发送后续消息
流输入非常适合对话式 UI，用户在整个执行过程中与代理交互，而不仅仅在批准检查点。
​
自定义工具
当您需要以下情况时，使用自定义工具：
收集结构化输入：构建超越 AskUserQuestion 多选格式的表单、向导或多步工作流
集成外部批准系统：连接到现有的票务、工作流或批准平台
实现特定领域的交互：创建针对您的应用程序需求定制的工具，如代码审查界面或部署清单
自定义工具让您完全控制交互，但需要比使用内置 canUseTool 回调更多的实现工作。
​
相关资源
配置权限：设置权限模式和规则
使用 hooks 控制执行：在代理生命周期的关键点运行自定义代码
TypeScript SDK 参考：完整的 canUseTool API 文档

此页面对您有帮助吗？

是
否
流式输入
实时流式传输响应
⌘I

---

# 实时流式传输响应

> 章节: 输入和输出 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/streaming-output

---

输入和输出
实时流式传输响应

当文本和工具调用流入时，从 Agent SDK 获取实时响应

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

默认情况下，Agent SDK 在 Claude 完成生成每个响应后会产生完整的 AssistantMessage 对象。要在文本和工具调用生成时接收增量更新，请通过在选项中将 include_partial_messages（Python）或 includePartialMessages（TypeScript）设置为 true 来启用部分消息流式传输。
本页面涵盖输出流式传输（实时接收令牌）。有关输入模式（如何发送消息），请参阅向代理发送消息。您也可以通过 CLI 使用 Agent SDK 流式传输响应。
​
启用流式输出
要启用流式传输，请在选项中将 include_partial_messages（Python）或 includePartialMessages（TypeScript）设置为 true。这会导致 SDK 产生包含原始 API 事件的 StreamEvent 消息，这些事件在到达时产生，除了通常的 AssistantMessage 和 ResultMessage 之外。
您的代码需要：
检查每条消息的类型以区分 StreamEvent 和其他消息类型
对于 StreamEvent，提取 event 字段并检查其 type
查找 content_block_delta 事件，其中 delta.type 是 text_delta，这些事件包含实际的文本块
下面的示例启用流式传输并在文本块到达时打印它们。注意嵌套的类型检查：首先是 StreamEvent，然后是 content_block_delta，最后是 text_delta：
Python
TypeScript
from claude_agent_sdk import query, ClaudeAgentOptions
from claude_agent_sdk.types import StreamEvent
import asyncio


async def stream_response():
    options = ClaudeAgentOptions(
        include_partial_messages=True,
        allowed_tools=["Bash", "Read"],
    )

    async for message in query(prompt="List the files in my project", options=options):
        if isinstance(message, StreamEvent):
            event = message.event
            if event.get("type") == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    print(delta.get("text", ""), end="", flush=True)


asyncio.run(stream_response())

​
StreamEvent 参考
启用部分消息后，您会收到包装在对象中的原始 Claude API 流式事件。该类型在每个 SDK 中有不同的名称：
Python: StreamEvent（从 claude_agent_sdk.types 导入）
TypeScript: SDKPartialAssistantMessage，其中 type: 'stream_event'
两者都包含原始 Claude API 事件，而不是累积的文本。您需要自己提取和累积文本增量。以下是每种类型的结构：
Python
TypeScript
@dataclass
class StreamEvent:
    uuid: str  # 此事件的唯一标识符
    session_id: str  # 会话标识符
    event: dict[str, Any]  # 原始 Claude API 流事件
    parent_tool_use_id: str | None  # 如果来自子代理，则为父工具 ID

event 字段包含来自 Claude API 的原始流事件。常见的事件类型包括：
事件类型	描述
message_start	新消息的开始
content_block_start	新内容块的开始（文本或工具使用）
content_block_delta	内容的增量更新
content_block_stop	内容块的结束
message_delta	消息级别的更新（停止原因、使用情况）
message_stop	消息的结束
​
消息流
启用部分消息后，您会按以下顺序接收消息：
StreamEvent (message_start)
StreamEvent (content_block_start) - 文本块
StreamEvent (content_block_delta) - 文本块...
StreamEvent (content_block_stop)
StreamEvent (content_block_start) - tool_use 块
StreamEvent (content_block_delta) - 工具输入块...
StreamEvent (content_block_stop)
StreamEvent (message_delta)
StreamEvent (message_stop)
AssistantMessage - 包含所有内容的完整消息
... 工具执行 ...
... 下一轮的更多流事件 ...
ResultMessage - 最终结果

未启用部分消息（Python 中的 include_partial_messages，TypeScript 中的 includePartialMessages）时，您会收到除 StreamEvent 之外的所有消息类型。常见类型包括 SystemMessage（会话初始化）、AssistantMessage（完整响应）、ResultMessage（最终结果）和指示何时压缩对话历史的紧凑边界消息（TypeScript 中的 SDKCompactBoundaryMessage；Python 中的 SystemMessage，子类型为 "compact_boundary"）。
​
流式传输文本响应
要在生成文本时显示它，请查找 content_block_delta 事件，其中 delta.type 是 text_delta。这些包含增量文本块。下面的示例在每个块到达时打印它：
Python
TypeScript
from claude_agent_sdk import query, ClaudeAgentOptions
from claude_agent_sdk.types import StreamEvent
import asyncio


async def stream_text():
    options = ClaudeAgentOptions(include_partial_messages=True)

    async for message in query(prompt="Explain how databases work", options=options):
        if isinstance(message, StreamEvent):
            event = message.event
            if event.get("type") == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    # 在每个文本块到达时打印它
                    print(delta.get("text", ""), end="", flush=True)

    print()  # 最后的换行符


asyncio.run(stream_text())

​
流式传输工具调用
工具调用也会增量流式传输。您可以跟踪工具何时开始、在生成时接收其输入，以及查看它们何时完成。下面的示例跟踪当前被调用的工具并在流式传输时累积 JSON 输入。它使用三种事件类型：
content_block_start：工具开始
content_block_delta，带有 input_json_delta：输入块到达
content_block_stop：工具调用完成
Python
TypeScript
from claude_agent_sdk import query, ClaudeAgentOptions
from claude_agent_sdk.types import StreamEvent
import asyncio


async def stream_tool_calls():
    options = ClaudeAgentOptions(
        include_partial_messages=True,
        allowed_tools=["Read", "Bash"],
    )

    # 跟踪当前工具并累积其输入 JSON
    current_tool = None
    tool_input = ""

    async for message in query(prompt="Read the README.md file", options=options):
        if isinstance(message, StreamEvent):
            event = message.event
            event_type = event.get("type")

            if event_type == "content_block_start":
                # 新工具调用开始
                content_block = event.get("content_block", {})
                if content_block.get("type") == "tool_use":
                    current_tool = content_block.get("name")
                    tool_input = ""
                    print(f"Starting tool: {current_tool}")

            elif event_type == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "input_json_delta":
                    # 在流式传输时累积 JSON 输入
                    chunk = delta.get("partial_json", "")
                    tool_input += chunk
                    print(f"  Input chunk: {chunk}")

            elif event_type == "content_block_stop":
                # 工具调用完成 - 显示最终输入
                if current_tool:
                    print(f"Tool {current_tool} called with: {tool_input}")
                    current_tool = None


asyncio.run(stream_tool_calls())

​
构建流式 UI
此示例将文本和工具流式传输结合到一个有凝聚力的 UI 中。它跟踪代理当前是否正在执行工具（使用 in_tool 标志）以显示状态指示器，如 [Using Read...]，同时工具运行。当不在工具中时文本正常流式传输，工具完成会触发”完成”消息。此模式对于需要在多步骤代理任务期间显示进度的聊天界面很有用。
Python
TypeScript
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
from claude_agent_sdk.types import StreamEvent
import asyncio
import sys


async def streaming_ui():
    options = ClaudeAgentOptions(
        include_partial_messages=True,
        allowed_tools=["Read", "Bash", "Grep"],
    )

    # 跟踪我们当前是否在工具调用中
    in_tool = False

    async for message in query(
        prompt="Find all TODO comments in the codebase", options=options
    ):
        if isinstance(message, StreamEvent):
            event = message.event
            event_type = event.get("type")

            if event_type == "content_block_start":
                content_block = event.get("content_block", {})
                if content_block.get("type") == "tool_use":
                    # 工具调用开始 - 显示状态指示器
                    tool_name = content_block.get("name")
                    print(f"\n[Using {tool_name}...]", end="", flush=True)
                    in_tool = True

            elif event_type == "content_block_delta":
                delta = event.get("delta", {})
                # 仅在不执行工具时流式传输文本
                if delta.get("type") == "text_delta" and not in_tool:
                    sys.stdout.write(delta.get("text", ""))
                    sys.stdout.flush()

            elif event_type == "content_block_stop":
                if in_tool:
                    # 工具调用完成
                    print(" done", flush=True)
                    in_tool = False

        elif isinstance(message, ResultMessage):
            # 代理完成所有工作
            print(f"\n\n--- Complete ---")


asyncio.run(streaming_ui())

​
已知限制
某些 SDK 功能与流式传输不兼容：
扩展思考：当您显式设置 max_thinking_tokens（Python）或 maxThinkingTokens（TypeScript）时，不会发出 StreamEvent 消息。您只会在每个轮次后收到完整消息。请注意，思考在 SDK 中默认禁用，因此流式传输有效，除非您启用它。
结构化输出：JSON 结果仅出现在最终 ResultMessage.structured_output 中，而不是作为流式增量。有关详细信息，请参阅结构化输出。
​
后续步骤
现在您可以实时流式传输文本和工具调用，请探索这些相关主题：
交互式与一次性查询：为您的用例选择输入模式
结构化输出：从代理获取类型化的 JSON 响应
权限：控制代理可以使用哪些工具

此页面对您有帮助吗？

是
否
处理批准和用户输入
Structured outputs
⌘I

---

# Structured outputs

> 章节: 输入和输出 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/structured-outputs

---

Observability with OpenTelemetry

> 注意: 此页面暂无中文翻译，以下为英文原版内容。

The Claude Agent SDK supports OpenTelemetry tracing for monitoring agent performance, debugging issues, and understanding agent behavior in production.

## Enabling OpenTelemetry

Set the environment variable to enable tracing:

```
CLAUDE_CODE_ENABLE_OTEL=1
```

Or configure it programmatically:

**Python:**
```python
options = ClaudeAgentOptions(
    enable_otel=True,
    otel_endpoint="http://localhost:4317",
)
```

**TypeScript:**
```typescript
const options: ClaudeAgentOptions = {
    enableOtel: true,
    otelEndpoint: "http://localhost:4317",
};
```

## What's Traced

The SDK emits spans for:
- Each agent turn (prompt → response)
- Tool calls (Bash, Read, Write, Edit, etc.)
- Sub-agent invocations
- MCP tool calls
- Hook executions

Each span includes attributes like model name, token usage, tool name, and duration.

## Exporting Traces

Traces can be exported to any OpenTelemetry-compatible backend:
- **Jaeger**: `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317`
- **Honeycomb**: Set `OTEL_EXPORTER_OTLP_HEADERS=x-honeycomb-team=your-api-key`
- **Datadog**: Use the Datadog Agent OTLP ingest
- **Grafana Cloud**: Configure with your Grafana Cloud OTLP endpoint

## Example: Local Debugging with Jaeger

```bash
# Start Jaeger
docker run -d --name jaeger -p 16686:16686 -p 4317:4317 jaegertracing/all-in-one:latest

# Run your agent with tracing
CLAUDE_CODE_ENABLE_OTEL=1 OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 python my_agent.py

# View traces at http://localhost:16686
```

Traces help you understand where your agent spends time, identify slow tool calls, and debug complex multi-turn interactions.

---

# 为 Claude 提供自定义工具

> 章节: 使用工具扩展 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/custom-tools

---

使用工具扩展
为 Claude 提供自定义工具

使用 Claude Agent SDK 的进程内 MCP 服务器定义自定义工具，以便 Claude 可以调用您的函数、访问您的 API 并执行特定领域的操作。

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

自定义工具通过让您定义 Claude 在对话期间可以调用的自己的函数来扩展 Agent SDK。使用 SDK 的进程内 MCP 服务器，您可以让 Claude 访问数据库、外部 API、特定领域的逻辑或应用程序需要的任何其他功能。
本指南涵盖如何使用输入架构和处理程序定义工具、将它们捆绑到 MCP 服务器中、将它们传递给 query，以及控制 Claude 可以访问哪些工具。它还涵盖错误处理、工具注释和返回非文本内容（如图像）。
​
快速参考
如果您想…	执行此操作
定义工具	使用 @tool（Python）或 tool()（TypeScript），包含名称、描述、架构和处理程序。请参阅创建自定义工具。
向 Claude 注册工具	在 create_sdk_mcp_server / createSdkMcpServer 中包装并传递给 query() 中的 mcpServers。请参阅调用自定义工具。
预先批准工具	添加到您的允许工具列表。请参阅配置允许的工具。
从 Claude 的上下文中删除内置工具	传递仅列出您想要的内置工具的 tools 数组。请参阅配置允许的工具。
让 Claude 并行调用工具	在没有副作用的工具上设置 readOnlyHint: true。请参阅添加工具注释。
处理错误而不停止循环	返回 isError: true 而不是抛出异常。请参阅处理错误。
返回图像或文件	在内容数组中使用 image 或 resource 块。请参阅返回图像和资源。
返回机器可读的 JSON 结果	在结果上设置 structuredContent。请参阅返回结构化数据。
扩展到许多工具	使用工具搜索按需加载工具。
​
创建自定义工具
工具由四个部分定义，作为参数传递给 TypeScript 中的 tool() 助手或 Python 中的 @tool 装饰器：
名称： Claude 用来调用工具的唯一标识符。
描述： 工具的功能。Claude 读取此内容以决定何时调用它。
输入架构： Claude 必须提供的参数。在 TypeScript 中，这始终是 Zod 架构，处理程序的 args 会自动从中获得类型。在 Python 中，这是一个将名称映射到类型的字典，如 {"latitude": float}，SDK 会为您将其转换为 JSON Schema。Python 装饰器还接受完整的 JSON Schema 字典，当您需要枚举、范围、可选字段或嵌套对象时。
处理程序： 当 Claude 调用工具时运行的异步函数。它接收验证的参数，必须返回一个对象，包含：
content（必需）：结果块的数组，每个块的 type 为 "text"、"image" 或 "resource"。有关非文本块，请参阅返回图像和资源。
structuredContent（可选）：保存结果作为机器可读数据的 JSON 对象，与 content 一起返回。请参阅返回结构化数据。
isError（可选）：设置为 true 以表示工具失败，以便 Claude 可以对其做出反应。请参阅处理错误。
定义工具后，使用 createSdkMcpServer（TypeScript）或 create_sdk_mcp_server（Python）将其包装在服务器中。服务器在应用程序内进程内运行，而不是作为单独的进程。
​
天气工具示例
此示例定义了一个 get_temperature 工具并将其包装在 MCP 服务器中。它仅设置工具；要将其传递给 query 并运行它，请参阅下面的调用自定义工具。
Python
TypeScript
from typing import Any
import httpx
from claude_agent_sdk import tool, create_sdk_mcp_server


# Define a tool: name, description, input schema, handler
@tool(
    "get_temperature",
    "Get the current temperature at a location",
    {"latitude": float, "longitude": float},
)
async def get_temperature(args: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": args["latitude"],
                "longitude": args["longitude"],
                "current": "temperature_2m",
                "temperature_unit": "fahrenheit",
            },
        )
        data = response.json()

    # Return a content array - Claude sees this as the tool result
    return {
        "content": [
            {
                "type": "text",
                "text": f"Temperature: {data['current']['temperature_2m']}°F",
            }
        ]
    }


# Wrap the tool in an in-process MCP server
weather_server = create_sdk_mcp_server(
    name="weather",
    version="1.0.0",
    tools=[get_temperature],
)

有关完整的参数详细信息，包括 JSON Schema 输入格式和返回值结构，请参阅 tool() TypeScript 参考或 @tool Python 参考。
要使参数可选：在 TypeScript 中，向 Zod 字段添加 .default()。在 Python 中，字典架构将每个键视为必需的，因此将参数从架构中省略，在描述字符串中提及它，并在处理程序中使用 args.get() 读取它。下面的 get_precipitation_chance 工具展示了两种模式。
​
调用自定义工具
通过 mcpServers 选项将您创建的 MCP 服务器传递给 query。mcpServers 中的键成为每个工具的完全限定名称中的 {server_name} 段：mcp__{server_name}__{tool_name}。在 allowedTools 中列出该名称，以便工具运行而无需权限提示。
这些代码片段重用上面示例中的 weatherServer 来询问 Claude 特定位置的天气。
Python
TypeScript
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage


async def main():
    options = ClaudeAgentOptions(
        mcp_servers={"weather": weather_server},
        allowed_tools=["mcp__weather__get_temperature"],
    )

    async for message in query(
        prompt="What's the temperature in San Francisco?",
        options=options,
    ):
        # ResultMessage is the final message after all tool calls complete
        if isinstance(message, ResultMessage) and message.subtype == "success":
            print(message.result)


asyncio.run(main())

​
添加更多工具
一个服务器在其 tools 数组中列出的工具数量不限。如果有多个工具在一个服务器上，您可以在 allowedTools 中单独列出每个工具，或使用通配符 mcp__weather__* 来覆盖服务器公开的每个工具。
下面的示例向天气工具示例中的 weatherServer 添加第二个工具 get_precipitation_chance，并使用数组中的两个工具重建它。
Python
TypeScript
# Define a second tool for the same server
@tool(
    "get_precipitation_chance",
    "Get the hourly precipitation probability for a location. "
    "Optionally pass 'hours' (1-24) to control how many hours to return.",
    {"latitude": float, "longitude": float},
)
async def get_precipitation_chance(args: dict[str, Any]) -> dict[str, Any]:
    # 'hours' isn't in the schema - read it with .get() to make it optional
    hours = args.get("hours", 12)
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": args["latitude"],
                "longitude": args["longitude"],
                "hourly": "precipitation_probability",
                "forecast_days": 1,
            },
        )
        data = response.json()
    chances = data["hourly"]["precipitation_probability"][:hours]

    return {
        "content": [
            {
                "type": "text",
                "text": f"Next {hours} hours: {'%, '.join(map(str, chances))}%",
            }
        ]
    }


# Rebuild the server with both tools in the array
weather_server = create_sdk_mcp_server(
    name="weather",
    version="1.0.0",
    tools=[get_temperature, get_precipitation_chance],
)

此数组中的每个工具在每个回合都会消耗上下文窗口空间。如果您定义了数十个工具，请参阅工具搜索以按需加载它们。
​
添加工具注释
工具注释是描述工具行为方式的可选元数据。在 TypeScript 中作为 tool() 助手的第五个参数传递，或在 Python 中通过 @tool 装饰器的 annotations 关键字参数传递。所有提示字段都是布尔值。
字段	默认值	含义
readOnlyHint	false	工具不修改其环境。控制工具是否可以与其他只读工具并行调用。
destructiveHint	true	工具可能执行破坏性更新。仅供参考。
idempotentHint	false	使用相同参数的重复调用没有额外效果。仅供参考。
openWorldHint	true	工具到达流程外的系统。仅供参考。
注释是元数据，不是强制执行。标记为 readOnlyHint: true 的工具如果处理程序这样做，仍然可以写入磁盘。保持注释与处理程序准确。
此示例向天气工具示例中的 get_temperature 工具添加 readOnlyHint。
Python
TypeScript
from claude_agent_sdk import tool, ToolAnnotations


@tool(
    "get_temperature",
    "Get the current temperature at a location",
    {"latitude": float, "longitude": float},
    annotations=ToolAnnotations(
        readOnlyHint=True
    ),  # Lets Claude batch this with other read-only calls
)
async def get_temperature(args):
    return {"content": [{"type": "text", "text": "..."}]}

请参阅 TypeScript 或 Python 参考中的 ToolAnnotations。
​
控制工具访问
天气工具示例注册了一个服务器并在 allowedTools 中列出了工具。本部分涵盖工具名称的构造方式以及当您有多个工具或想要限制内置工具时如何限制访问。
​
工具名称格式
当 MCP 工具暴露给 Claude 时，它们的名称遵循特定格式：
模式：mcp__{server_name}__{tool_name}
示例：服务器 weather 中名为 get_temperature 的工具变成 mcp__weather__get_temperature
​
配置允许的工具
tools 选项和允许/不允许列表影响两个层：可用性（控制工具是否出现在 Claude 的上下文中）和权限（控制 Claude 尝试调用后是否批准调用）。tools 和裸名称 disallowedTools 条目改变可用性。allowedTools 和作用域 disallowedTools 规则仅改变权限。
选项	层	效果
tools: ["Read", "Grep"]	可用性	仅列出的内置工具在 Claude 的上下文中。未列出的内置工具被删除。MCP 工具不受影响。
tools: []	可用性	所有内置工具都被删除。Claude 只能使用您的 MCP 工具。
允许的工具	权限	列出的工具运行而无需权限提示。未列出的工具保持可用；调用通过权限流进行。
不允许的工具	两者	裸工具名称（如 "Bash"）将工具从 Claude 的上下文中删除，与从 tools 中省略它相同。作用域规则（如 "Bash(rm *)"）将工具保留在上下文中，仅拒绝匹配的调用。
要完全删除内置工具，请从 tools 中省略它或在 disallowedTools 中列出其裸名称（Python：disallowed_tools）；两者都将工具保留在上下文之外，以便 Claude 永远不会尝试它。作用域 disallowedTools 规则会阻止匹配的调用但保留工具可见，因此 Claude 可能会浪费一个回合尝试它。有关完整的评估顺序，请参阅配置权限。
​
处理错误
您的处理程序报告错误的方式决定了代理循环是继续还是停止：
发生的情况	结果
处理程序抛出未捕获的异常	代理循环停止。Claude 永远看不到错误，query 调用失败。
处理程序捕获错误并返回 isError: true（TS）/ "is_error": True（Python）	代理循环继续。Claude 将错误视为数据，可以重试、尝试不同的工具或解释失败。
下面的示例在处理程序内部捕获两种失败，而不是让它们抛出。非 200 HTTP 状态从响应中捕获并作为错误结果返回。网络错误或无效 JSON 由周围的 try/except（Python）或 try/catch（TypeScript）捕获，也作为错误结果返回。在这两种情况下，处理程序正常返回，代理循环继续。
Python
TypeScript
import json
import httpx
from typing import Any


@tool(
    "fetch_data",
    "Fetch data from an API",
    {"endpoint": str},  # Simple schema
)
async def fetch_data(args: dict[str, Any]) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(args["endpoint"])
            if response.status_code != 200:
                # Return the failure as a tool result so Claude can react to it.
                # is_error marks this as a failed call rather than odd-looking data.
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"API error: {response.status_code} {response.reason_phrase}",
                        }
                    ],
                    "is_error": True,
                }

            data = response.json()
            return {"content": [{"type": "text", "text": json.dumps(data, indent=2)}]}
    except Exception as e:
        # Catching here keeps the agent loop alive. An uncaught exception
        # would end the whole query() call.
        return {
            "content": [{"type": "text", "text": f"Failed to fetch data: {str(e)}"}],
            "is_error": True,
        }

​
返回图像和资源
工具结果中的 content 数组接受 text、image 和 resource 块。您可以在同一响应中混合它们。
​
图像
图像块以 base64 编码的方式内联携带图像字节。没有 URL 字段。要返回位于 URL 的图像，在处理程序中获取它，读取响应字节，并在返回之前进行 base64 编码。结果作为视觉输入处理。
字段	类型	注释
type	"image"	
data	string	Base64 编码的字节。仅原始 base64，没有 data:image/...;base64, 前缀
mimeType	string	必需。例如 image/png、image/jpeg、image/webp、image/gif
Python
TypeScript
import base64
import httpx


# Define a tool that fetches an image from a URL and returns it to Claude
@tool("fetch_image", "Fetch an image from a URL and return it to Claude", {"url": str})
async def fetch_image(args):
    async with httpx.AsyncClient() as client:  # Fetch the image bytes
        response = await client.get(args["url"])

    return {
        "content": [
            {
                "type": "image",
                "data": base64.b64encode(response.content).decode(
                    "ascii"
                ),  # Base64-encode the raw bytes
                "mimeType": response.headers.get(
                    "content-type", "image/png"
                ),  # Read MIME type from the response
            }
        ]
    }

​
资源
资源块嵌入由 URI 标识的内容片段。URI 是 Claude 引用的标签；实际内容位于块的 text 或 blob 字段中。当您的工具生成稍后按名称寻址有意义的内容时使用此功能，例如生成的文件或来自外部系统的记录。
字段	类型	注释
type	"resource"	
resource.uri	string	内容的标识符。任何 URI 方案
resource.text	string	内容，如果是文本。提供此项或 blob，不能两者都提供
resource.blob	string	内容 base64 编码，如果是二进制
resource.mimeType	string	可选
此示例显示从工具处理程序内部返回的资源块。URI file:///tmp/report.md 是 Claude 可以稍后引用的标签；SDK 不从该路径读取。
TypeScript
Python
return {
  content: [
    {
      type: "resource",
      resource: {
        uri: "file:///tmp/report.md", // Label for Claude to reference, not a path the SDK reads
        mimeType: "text/markdown",
        text: "# Report\n..." // The actual content, inline
      }
    }
  ]
};

这些块形状来自 MCP CallToolResult 类型。有关完整定义，请参阅 MCP 规范。
​
返回结构化数据
structuredContent 是结果上的可选 JSON 对象，与 content 数组分开。使用它返回原始值，Claude 可以将其作为精确字段读取，而不是从文本字符串或图像中解析它们。
当设置 structuredContent 时，Claude 接收 JSON 加上来自 content 的任何图像或资源块。来自 content 的文本块不被转发，因为假设它们复制结构化数据。下面的示例将图表呈现为图像块，并从同一处理程序的 structuredContent 中返回其后面的数据点。
TypeScript
return {
  content: [
    {
      type: "image",
      data: chartPngBuffer.toString("base64"),
      mimeType: "image/png"
    }
  ],
  structuredContent: {
    series: "temperature_2m",
    unit: "fahrenheit",
    points: [62.1, 63.4, 65.0, 64.2]
  }
};

Python @tool 装饰器仅从处理程序的返回字典转发 content 和 is_error。要从 Python 返回 structuredContent，请运行独立 MCP 服务器而不是进程内 SDK 服务器。
​
示例：单位转换器
此工具在长度、温度和重量的单位之间转换值。用户可以询问”将 100 公里转换为英里”或”72°F 是多少摄氏度”，Claude 从请求中选择正确的单位类型和单位。
它演示了两种模式：
枚举架构： unit_type 被限制为一组固定值。在 TypeScript 中，使用 z.enum()。在 Python 中，字典架构不支持枚举，因此需要完整的 JSON Schema 字典。
不支持的输入处理： 当找不到转换对时，处理程序返回 isError: true，以便 Claude 可以告诉用户出了什么问题，而不是将失败视为正常结果。
Python
TypeScript
from typing import Any
from claude_agent_sdk import tool, create_sdk_mcp_server


# z.enum() in TypeScript becomes an "enum" constraint in JSON Schema.
# The dict schema has no equivalent, so full JSON Schema is required.
@tool(
    "convert_units",
    "Convert a value from one unit to another",
    {
        "type": "object",
        "properties": {
            "unit_type": {
                "type": "string",
                "enum": ["length", "temperature", "weight"],
                "description": "Category of unit",
            },
            "from_unit": {
                "type": "string",
                "description": "Unit to convert from, e.g. kilometers, fahrenheit, pounds",
            },
            "to_unit": {"type": "string", "description": "Unit to convert to"},
            "value": {"type": "number", "description": "Value to convert"},
        },
        "required": ["unit_type", "from_unit", "to_unit", "value"],
    },
)
async def convert_units(args: dict[str, Any]) -> dict[str, Any]:
    conversions = {
        "length": {
            "kilometers_to_miles": lambda v: v * 0.621371,
            "miles_to_kilometers": lambda v: v * 1.60934,
            "meters_to_feet": lambda v: v * 3.28084,
            "feet_to_meters": lambda v: v * 0.3048,
        },
        "temperature": {
            "celsius_to_fahrenheit": lambda v: (v * 9) / 5 + 32,
            "fahrenheit_to_celsius": lambda v: (v - 32) * 5 / 9,
            "celsius_to_kelvin": lambda v: v + 273.15,
            "kelvin_to_celsius": lambda v: v - 273.15,
        },
        "weight": {
            "kilograms_to_pounds": lambda v: v * 2.20462,
            "pounds_to_kilograms": lambda v: v * 0.453592,
            "grams_to_ounces": lambda v: v * 0.035274,
            "ounces_to_grams": lambda v: v * 28.3495,
        },
    }

    key = f"{args['from_unit']}_to_{args['to_unit']}"
    fn = conversions.get(args["unit_type"], {}).get(key)

    if not fn:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Unsupported conversion: {args['from_unit']} to {args['to_unit']}",
                }
            ],
            "is_error": True,
        }

    result = fn(args["value"])
    return {
        "content": [
            {
                "type": "text",
                "text": f"{args['value']} {args['from_unit']} = {result:.4f} {args['to_unit']}",
            }
        ]
    }


converter_server = create_sdk_mcp_server(
    name="converter",
    version="1.0.0",
    tools=[convert_units],
)

定义服务器后，以与天气示例相同的方式将其传递给 query。此示例在循环中发送三个不同的提示，以显示同一工具处理不同的单位类型。对于每个响应，它检查 AssistantMessage 对象（包含 Claude 在该回合中进行的工具调用）并在打印最终 ResultMessage 文本之前打印每个 ToolUseBlock。这让您看到 Claude 何时使用工具与从其自己的知识中回答。
Python
TypeScript
import asyncio
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    ResultMessage,
    AssistantMessage,
    ToolUseBlock,
)


async def main():
    options = ClaudeAgentOptions(
        mcp_servers={"converter": converter_server},
        allowed_tools=["mcp__converter__convert_units"],
    )

    prompts = [
        "Convert 100 kilometers to miles.",
        "What is 72°F in Celsius?",
        "How many pounds is 5 kilograms?",
    ]

    for prompt in prompts:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, ToolUseBlock):
                        print(f"[tool call] {block.name}({block.input})")
            elif isinstance(message, ResultMessage) and message.subtype == "success":
                print(f"Q: {prompt}\nA: {message.result}\n")


asyncio.run(main())

​
后续步骤
自定义工具在标准接口中包装异步函数。您可以在同一服务器中混合本页上的模式：单个服务器可以在彼此旁边保存数据库工具、API 网关工具和图像渲染器。
从这里：
如果您的服务器增长到数十个工具，请参阅工具搜索以延迟加载它们，直到 Claude 需要它们。
要连接到外部 MCP 服务器（文件系统、GitHub、Slack）而不是构建自己的，请参阅连接 MCP 服务器。
要控制哪些工具自动运行与需要批准，请参阅配置权限。
​
相关文档
TypeScript SDK 参考
Python SDK 参考
MCP 文档
SDK 概述

此页面对您有帮助吗？

是
否
Structured outputs
使用 MCP 连接外部工具
⌘I

---

# 使用 MCP 连接外部工具

> 章节: 使用工具扩展 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/mcp

---

使用工具扩展
使用 MCP 连接外部工具

配置 MCP 服务器以扩展您的代理的外部工具。涵盖传输类型、大型工具集的工具搜索、身份验证和错误处理。

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

Model Context Protocol (MCP) 是一个开放标准，用于将 AI 代理连接到外部工具和数据源。使用 MCP，您的代理可以查询数据库、与 Slack 和 GitHub 等 API 集成，以及连接到其他服务，而无需编写自定义工具实现。
MCP 服务器可以作为本地进程运行、通过 HTTP 连接或直接在您的 SDK 应用程序中执行。
本页面涵盖 Agent SDK 的 MCP 配置。要将 MCP 服务器添加到 Claude Code CLI 以便在每个项目中加载，请参阅 MCP 安装范围。
​
快速开始
此示例使用 HTTP 传输 连接到 Claude Code 文档 MCP 服务器，并使用 allowedTools 与通配符来允许来自服务器的所有工具。
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Use the docs MCP server to explain what hooks are in Claude Code",
  options: {
    mcpServers: {
      "claude-code-docs": {
        type: "http",
        url: "https://code.claude.com/docs/mcp"
      }
    },
    allowedTools: ["mcp__claude-code-docs__*"]
  }
})) {
  if (message.type === "result" && message.subtype === "success") {
    console.log(message.result);
  }
}

代理连接到文档服务器，搜索有关 hooks 的信息，并返回结果。
​
添加 MCP 服务器
您可以在调用 query() 时在代码中配置 MCP 服务器，或在通过 settingSources 加载的 .mcp.json 文件中配置。
​
在代码中
在 mcpServers 选项中直接传递 MCP 服务器：
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "List files in my project",
  options: {
    mcpServers: {
      filesystem: {
        command: "npx",
        args: ["-y", "@modelcontextprotocol/server-filesystem", "/Users/me/projects"]
      }
    },
    allowedTools: ["mcp__filesystem__*"]
  }
})) {
  if (message.type === "result" && message.subtype === "success") {
    console.log(message.result);
  }
}

​
从配置文件
在项目根目录创建一个 .mcp.json 文件。当启用 project 设置源时，该文件会被选中，这对默认 query() 选项是默认的。如果您显式设置 settingSources，请包含 "project" 以便加载此文件：
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/me/projects"]
    }
  }
}

​
允许 MCP 工具
MCP 工具需要明确的权限才能让 Claude 使用它们。没有权限，Claude 会看到工具可用，但无法调用它们。
​
工具命名约定
MCP 工具遵循命名模式 mcp__<server-name>__<tool-name>。例如，名为 "github" 的 GitHub 服务器与 list_issues 工具变成 mcp__github__list_issues。
​
使用 allowedTools 授予访问权限
使用 allowedTools 指定 Claude 可以使用哪些 MCP 工具：
const _ = {
  options: {
    mcpServers: {
      // your servers
    },
    allowedTools: [
      "mcp__github__*", // All tools from the github server
      "mcp__db__query", // Only the query tool from db server
      "mcp__slack__send_message" // Only send_message from slack server
    ]
  }
};

通配符 (*) 让您允许来自服务器的所有工具，而无需逐个列出每一个。
对于 MCP 访问，优先使用 allowedTools 而不是权限模式。 permissionMode: "acceptEdits" 不会自动批准 MCP 工具（仅文件编辑和文件系统 Bash 命令）。permissionMode: "bypassPermissions" 确实会自动批准 MCP 工具，但也会禁用所有其他安全提示，这比必要的范围更广。allowedTools 中的通配符仅授予您想要的 MCP 服务器，没有其他。请参阅 权限模式 以获得完整比较。
​
发现可用工具
要查看 MCP 服务器提供的工具，请检查服务器的文档或连接到服务器并检查 system init 消息：
for await (const message of query({ prompt: "...", options })) {
  if (message.type === "system" && message.subtype === "init") {
    console.log("Available MCP tools:", message.mcp_servers);
  }
}

​
传输类型
MCP 服务器使用不同的传输协议与您的代理通信。检查服务器的文档以查看它支持哪种传输：
如果文档给您一个要运行的命令（如 npx @modelcontextprotocol/server-github），请使用 stdio
如果文档给您一个 URL，请使用 HTTP 或 SSE
如果您在代码中构建自己的工具，请使用 SDK MCP 服务器
​
stdio 服务器
通过 stdin/stdout 通信的本地进程。对于在同一台机器上运行的 MCP 服务器，请使用此选项：
在代码中
.mcp.json
TypeScript
Python
const _ = {
  options: {
    mcpServers: {
      github: {
        command: "npx",
        args: ["-y", "@modelcontextprotocol/server-github"],
        env: {
          GITHUB_TOKEN: process.env.GITHUB_TOKEN
        }
      }
    },
    allowedTools: ["mcp__github__list_issues", "mcp__github__search_issues"]
  }
};

​
HTTP/SSE 服务器
对于云托管的 MCP 服务器和远程 API，请使用 HTTP 或 SSE：
在代码中
.mcp.json
TypeScript
Python
const _ = {
  options: {
    mcpServers: {
      "remote-api": {
        type: "sse",
        url: "https://api.example.com/mcp/sse",
        headers: {
          Authorization: `Bearer ${process.env.API_TOKEN}`
        }
      }
    },
    allowedTools: ["mcp__remote-api__*"]
  }
};

对于可流式传输的 HTTP 传输，请改用 "type": "http"。在 .mcp.json 和其他 JSON 配置文件中，"streamable-http" 被接受作为 "http" 的别名。编程式 mcpServers 选项仅接受 "http"。
​
SDK MCP 服务器
直接在应用程序代码中定义自定义工具，而不是运行单独的服务器进程。有关实现详情，请参阅 自定义工具指南。
​
MCP 工具搜索
当您配置了许多 MCP 工具时，工具定义可能会消耗上下文窗口的很大一部分。工具搜索通过从上下文中隐藏工具定义并仅加载 Claude 每轮需要的工具来解决此问题。
工具搜索默认启用。有关配置选项和详情，请参阅 工具搜索。
有关更多详情，包括最佳实践和将工具搜索与自定义 SDK 工具一起使用，请参阅 工具搜索指南。
​
身份验证
大多数 MCP 服务器需要身份验证才能访问外部服务。通过服务器配置中的环境变量传递凭据。
​
通过环境变量传递凭据
使用 env 字段将 API 密钥、令牌和其他凭据传递给 MCP 服务器：
在代码中
.mcp.json
TypeScript
Python
const _ = {
  options: {
    mcpServers: {
      github: {
        command: "npx",
        args: ["-y", "@modelcontextprotocol/server-github"],
        env: {
          GITHUB_TOKEN: process.env.GITHUB_TOKEN
        }
      }
    },
    allowedTools: ["mcp__github__list_issues"]
  }
};

有关带有调试日志的完整工作示例，请参阅 从存储库列出问题。
​
远程服务器的 HTTP 标头
对于 HTTP 和 SSE 服务器，直接在服务器配置中传递身份验证标头：
在代码中
.mcp.json
TypeScript
Python
const _ = {
  options: {
    mcpServers: {
      "secure-api": {
        type: "http",
        url: "https://api.example.com/mcp",
        headers: {
          Authorization: `Bearer ${process.env.API_TOKEN}`
        }
      }
    },
    allowedTools: ["mcp__secure-api__*"]
  }
};

​
OAuth2 身份验证
MCP 规范支持 OAuth 2.1 用于授权。SDK 不会自动处理 OAuth 流程，但您可以在应用程序中完成 OAuth 流程后通过标头传递访问令牌：
TypeScript
Python
// After completing OAuth flow in your app
const accessToken = await getAccessTokenFromOAuthFlow();

const options = {
  mcpServers: {
    "oauth-api": {
      type: "http",
      url: "https://api.example.com/mcp",
      headers: {
        Authorization: `Bearer ${accessToken}`
      }
    }
  },
  allowedTools: ["mcp__oauth-api__*"]
};

​
示例
​
从存储库列出问题
此示例连接到 GitHub MCP 服务器 以列出最近的问题。该示例包括调试日志以验证 MCP 连接和工具调用。
在运行之前，创建一个具有 repo 范围的 GitHub 个人访问令牌 并将其设置为环境变量：
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "List the 3 most recent issues in anthropics/claude-code",
  options: {
    mcpServers: {
      github: {
        command: "npx",
        args: ["-y", "@modelcontextprotocol/server-github"],
        env: {
          GITHUB_TOKEN: process.env.GITHUB_TOKEN
        }
      }
    },
    allowedTools: ["mcp__github__list_issues"]
  }
})) {
  // Verify MCP server connected successfully
  if (message.type === "system" && message.subtype === "init") {
    console.log("MCP servers:", message.mcp_servers);
  }

  // Log when Claude calls an MCP tool
  if (message.type === "assistant") {
    for (const block of message.message.content) {
      if (block.type === "tool_use" && block.name.startsWith("mcp__")) {
        console.log("MCP tool called:", block.name);
      }
    }
  }

  // Print the final result
  if (message.type === "result" && message.subtype === "success") {
    console.log(message.result);
  }
}

​
查询数据库
此示例使用 Postgres MCP 服务器 查询数据库。连接字符串作为参数传递给服务器。代理自动发现数据库架构、编写 SQL 查询并返回结果：
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

// Connection string from environment variable
const connectionString = process.env.DATABASE_URL;

for await (const message of query({
  // Natural language query - Claude writes the SQL
  prompt: "How many users signed up last week? Break it down by day.",
  options: {
    mcpServers: {
      postgres: {
        command: "npx",
        // Pass connection string as argument to the server
        args: ["-y", "@modelcontextprotocol/server-postgres", connectionString]
      }
    },
    // Allow only read queries, not writes
    allowedTools: ["mcp__postgres__query"]
  }
})) {
  if (message.type === "result" && message.subtype === "success") {
    console.log(message.result);
  }
}

​
错误处理
MCP 服务器可能因各种原因连接失败：服务器进程可能未安装、凭据可能无效，或远程服务器可能无法访问。
SDK 在每个查询开始时发出一个 system 消息，子类型为 init。此消息包括每个 MCP 服务器的连接状态。检查 status 字段以在代理开始工作之前检测连接失败：
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Process data",
  options: {
    mcpServers: {
      "data-processor": dataServer
    }
  }
})) {
  if (message.type === "system" && message.subtype === "init") {
    const failedServers = message.mcp_servers.filter((s) => s.status !== "connected");

    if (failedServers.length > 0) {
      console.warn("Failed to connect:", failedServers);
    }
  }

  if (message.type === "result" && message.subtype === "error_during_execution") {
    console.error("Execution failed");
  }
}

​
故障排除
​
服务器显示”失败”状态
检查 init 消息以查看哪些服务器连接失败：
if (message.type === "system" && message.subtype === "init") {
  for (const server of message.mcp_servers) {
    if (server.status === "failed") {
      console.error(`Server ${server.name} failed to connect`);
    }
  }
}

常见原因：
缺少环境变量：确保设置了所需的令牌和凭据。对于 stdio 服务器，检查 env 字段是否与服务器期望的匹配。
服务器未安装：对于 npx 命令，验证包存在且 Node.js 在您的 PATH 中。
无效的连接字符串：对于数据库服务器，验证连接字符串格式以及数据库是否可访问。
网络问题：对于远程 HTTP/SSE 服务器，检查 URL 是否可达以及任何防火墙是否允许连接。
​
工具未被调用
如果 Claude 看到工具但不使用它们，请检查您是否已使用 allowedTools 授予权限：
const _ = {
  options: {
    mcpServers: {
      // your servers
    },
    allowedTools: ["mcp__servername__*"] // Required for Claude to use the tools
  }
};

​
连接超时
MCP SDK 对服务器连接的默认超时为 60 秒。如果您的服务器需要更长时间才能启动，连接将失败。对于需要更多启动时间的服务器，请考虑：
使用更轻量级的服务器（如果可用）
在启动代理之前预热服务器
检查服务器日志以了解缓慢初始化的原因
​
相关资源
自定义工具指南：构建您自己的 MCP 服务器，与您的 SDK 应用程序在进程中运行
权限：使用 allowedTools 和 disallowedTools 控制您的代理可以使用哪些 MCP 工具
TypeScript SDK 参考：完整的 API 参考，包括 MCP 配置选项
Python SDK 参考：完整的 API 参考，包括 MCP 配置选项
MCP 服务器目录：浏览可用的 MCP 服务器，用于数据库、API 等

此页面对您有帮助吗？

是
否
为 Claude 提供自定义工具
使用工具搜索扩展到多个工具
⌘I

---

# 使用工具搜索扩展到多个工具

> 章节: 使用工具扩展 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/tool-search

---

使用工具扩展
使用工具搜索扩展到多个工具

通过动态发现和按需加载，将您的代理扩展到数千个工具。

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

工具搜索使您的代理能够通过动态发现和按需加载来处理数百或数千个工具。代理不是将所有工具定义预先加载到上下文窗口中，而是搜索您的工具目录并仅加载它需要的工具。
当工具库扩展时，这种方法解决了两个挑战：
上下文效率： 工具定义可能会消耗上下文窗口的大部分（50个工具可能使用10-20K个令牌），留下较少的空间用于实际工作。
工具选择准确性： 一次加载超过30-50个工具时，工具选择准确性会下降。
工具搜索默认启用。本页面涵盖它的工作原理、如何配置它以及如何优化工具发现。
​
工具搜索的工作原理
当工具搜索处于活动状态时，工具定义会从上下文窗口中隐藏。代理会收到可用工具的摘要，并在任务需要尚未加载的功能时搜索相关工具。最相关的3-5个工具被加载到上下文中，在后续轮次中保持可用。如果对话足够长，SDK会压缩早期消息以释放空间，之前发现的工具可能会被移除，代理会根据需要再次搜索。
工具搜索在Claude首次发现工具时增加一个额外的往返（搜索步骤），但对于大型工具集，这被每个轮次中较小的上下文所抵消。对于少于约10个工具的情况，预先加载所有工具通常更快。
有关底层API机制的详细信息，请参阅API中的工具搜索。
工具搜索需要Claude Sonnet 4或更高版本，或Claude Opus 4或更高版本。Haiku模型不支持工具搜索。
​
配置工具搜索
工具搜索默认启用。在Vertex AI上默认禁用，其中支持Claude Sonnet 4.5及更高版本以及Claude Opus 4.5及更高版本。当ANTHROPIC_BASE_URL指向非第一方主机时也会禁用，因为大多数代理不转发tool_reference块。您可以使用ENABLE_TOOL_SEARCH环境变量覆盖任一默认值：
值	行为
（未设置）	工具搜索处于启用状态。工具定义被延迟并按需发现。在Vertex AI或非第一方ANTHROPIC_BASE_URL上回退到预先加载。
true	工具搜索始终启用。SDK即使在Vertex AI和通过代理上也会发送beta标头。在Sonnet 4.5或Opus 4.5之前的Vertex AI模型上，或在不支持tool_reference块的代理上，请求会失败。
auto	检查所有工具定义的组合令牌计数与模型的上下文窗口。如果超过10%，工具搜索激活。如果低于10%，所有工具正常加载到上下文中。
auto:N	与auto相同，但具有自定义百分比。auto:5在工具定义超过上下文窗口的5%时激活。较低的值更早激活。
false	工具搜索关闭。所有工具定义在每个轮次上都加载到上下文中。
工具搜索适用于所有已注册的工具，无论它们来自远程MCP服务器还是自定义SDK MCP服务器。使用auto时，阈值基于所有服务器上所有工具定义的组合大小。
在query()上的env选项中设置值。此示例连接到公开许多工具的远程MCP服务器，使用通配符预先批准所有工具，并使用auto:5，以便当工具定义超过上下文窗口的5%时激活工具搜索：
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Find and run the appropriate database query",
  options: {
    mcpServers: {
      "enterprise-tools": {
        // Connect to a remote MCP server
        type: "http",
        url: "https://tools.example.com/mcp"
      }
    },
    allowedTools: ["mcp__enterprise-tools__*"], // Wildcard pre-approves all tools from this server
    env: {
      ENABLE_TOOL_SEARCH: "auto:5" // Activate tool search when tools exceed 5% of context
    }
  }
})) {
  if (message.type === "result" && message.subtype === "success") {
    console.log(message.result);
  }
}

将ENABLE_TOOL_SEARCH设置为"false"会禁用工具搜索，并在每个轮次上将所有工具定义加载到上下文中。这消除了搜索往返，当工具集很小（少于约10个工具）且定义在上下文窗口中舒适地适配时，这可能会更快。
​
优化工具发现
搜索机制将查询与工具名称和描述进行匹配。像search_slack_messages这样的名称比query_slack更广泛地出现在各种请求中。具有特定关键字的描述（“按关键字、频道或日期范围搜索Slack消息”）比通用描述（“查询Slack”）匹配更多查询。
您还可以添加一个系统提示部分，列出可用的工具类别。这为代理提供了关于可以搜索什么类型工具的上下文：
You can search for tools to interact with Slack, GitHub, and Jira.

​
限制
最大工具数： 您的目录中最多10,000个工具
搜索结果： 每次搜索返回3-5个最相关的工具
模型支持： Claude Sonnet 4及更高版本、Claude Opus 4及更高版本（不支持Haiku）
​
相关文档
API中的工具搜索：工具搜索的完整API文档，包括自定义实现
连接MCP服务器：通过MCP服务器连接到外部工具
自定义工具：使用SDK MCP服务器构建您自己的工具
TypeScript SDK参考：完整API参考
Python SDK参考：完整API参考

此页面对您有帮助吗？

是
否
使用 MCP 连接外部工具
SDK 中的子代理
⌘I

---

# SDK 中的子代理

> 章节: 使用工具扩展 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/subagents

---

使用工具扩展
SDK 中的子代理

定义和调用子代理以隔离上下文、并行运行任务，以及在 Claude Agent SDK 应用程序中应用专门的指令。

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

子代理是您的主代理可以生成的独立代理实例，用于处理专注的子任务。 使用子代理来隔离专注子任务的上下文、并行运行多个分析，以及应用专门的指令，而不会使主代理的提示词过于复杂。
本指南说明如何使用 agents 参数在 SDK 中定义和使用子代理。
​
概述
您可以通过三种方式创建子代理：
以编程方式：在您的 query() 选项中使用 agents 参数（TypeScript、Python）
基于文件系统：在 .claude/agents/ 目录中将代理定义为 markdown 文件（请参阅将子代理定义为文件）
内置通用代理：Claude 可以随时通过 Agent 工具调用内置的 general-purpose 子代理，无需您定义任何内容
本指南重点介绍编程方法，这是 SDK 应用程序的推荐方法。
定义子代理时，Claude 根据每个子代理的 description 字段确定是否调用它。编写清晰的描述，说明何时应使用子代理，Claude 将自动委派适当的任务。您也可以在提示词中按名称显式请求子代理（例如，“使用代码审查员代理来…”）。
​
使用子代理的好处
​
上下文隔离
每个子代理在其自己的新对话中运行。中间工具调用和结果保留在子代理内部；只有其最终消息返回到父代理。请参阅子代理继承的内容以了解子代理上下文中的确切内容。
示例： research-assistant 子代理可以探索数十个文件，而这些内容都不会在主对话中累积。父代理收到的是简洁的摘要，而不是子代理读取的每个文件。
​
并行化
多个子代理可以并发运行，大大加快复杂工作流的速度。
示例： 在代码审查期间，您可以同时运行 style-checker、security-scanner 和 test-coverage 子代理，将审查时间从几分钟减少到几秒钟。
​
专门的指令和知识
每个子代理都可以有定制的系统提示词，具有特定的专业知识、最佳实践和约束。
示例： database-migration 子代理可以具有关于 SQL 最佳实践、回滚策略和数据完整性检查的详细知识，这些在主代理的指令中将是不必要的噪音。
​
工具限制
子代理可以限制为特定工具，降低意外操作的风险。
示例： doc-reviewer 子代理可能只能访问 Read 和 Grep 工具，确保它可以分析但永远不会意外修改您的文档文件。
​
创建子代理
​
以编程方式定义（推荐）
使用 agents 参数直接在代码中定义子代理。此示例创建两个子代理：一个具有只读访问权限的代码审查员和一个可以执行命令的测试运行器。Agent 工具必须包含在 allowedTools 中，因为 Claude 通过 Agent 工具调用子代理。
Python
TypeScript
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition


async def main():
    async for message in query(
        prompt="Review the authentication module for security issues",
        options=ClaudeAgentOptions(
            # Agent tool is required for subagent invocation
            allowed_tools=["Read", "Grep", "Glob", "Agent"],
            agents={
                "code-reviewer": AgentDefinition(
                    # description tells Claude when to use this subagent
                    description="Expert code review specialist. Use for quality, security, and maintainability reviews.",
                    # prompt defines the subagent's behavior and expertise
                    prompt="""You are a code review specialist with expertise in security, performance, and best practices.

When reviewing code:
- Identify security vulnerabilities
- Check for performance issues
- Verify adherence to coding standards
- Suggest specific improvements

Be thorough but concise in your feedback.""",
                    # tools restricts what the subagent can do (read-only here)
                    tools=["Read", "Grep", "Glob"],
                    # model overrides the default model for this subagent
                    model="sonnet",
                ),
                "test-runner": AgentDefinition(
                    description="Runs and analyzes test suites. Use for test execution and coverage analysis.",
                    prompt="""You are a test execution specialist. Run tests and provide clear analysis of results.

Focus on:
- Running test commands
- Analyzing test output
- Identifying failing tests
- Suggesting fixes for failures""",
                    # Bash access lets this subagent run test commands
                    tools=["Bash", "Read", "Grep"],
                ),
            },
        ),
    ):
        if hasattr(message, "result"):
            print(message.result)


asyncio.run(main())

​
AgentDefinition 配置
字段	类型	必需	描述
description	string	是	何时使用此代理的自然语言描述
prompt	string	是	代理的系统提示词，定义其角色和行为
tools	string[]	否	允许的工具名称数组。如果省略，继承所有工具
disallowedTools	string[]	否	要从代理的工具集中移除的工具名称数组
model	string	否	此代理的模型覆盖。接受别名，如 'sonnet'、'opus'、'haiku'、'inherit'，或完整的模型 ID。如果省略，默认为主模型
skills	string[]	否	在启动时预加载到代理上下文中的技能名称列表。未列出的技能仍可通过 Skill 工具调用
memory	'user' | 'project' | 'local'	否	此代理的内存源
mcpServers	(string | object)[]	否	此代理可用的 MCP 服务器，按名称或内联配置
maxTurns	number	否	代理停止前的最大代理轮数
background	boolean	否	调用时将此代理作为非阻塞后台任务运行
effort	'low' | 'medium' | 'high' | 'xhigh' | 'max' | number	否	此代理的推理工作量级别
permissionMode	PermissionMode	否	此代理内工具执行的权限模式
在 Python SDK 中，这些字段名称使用 camelCase 以匹配线路格式。有关详细信息，请参阅 AgentDefinition 参考。
子代理无法生成自己的子代理。不要在子代理的 tools 数组中包含 Agent。
​
基于文件系统的定义（替代方案）
您也可以在 .claude/agents/ 目录中将子代理定义为 markdown 文件。有关此方法的详细信息，请参阅 Claude Code 子代理文档。以编程方式定义的代理优先于具有相同名称的基于文件系统的代理。
即使不定义自定义子代理，当 Agent 在您的 allowedTools 中时，Claude 也可以生成内置的 general-purpose 子代理。这对于委派研究或探索任务而无需创建专门的代理很有用。
​
子代理继承的内容
子代理的上下文窗口从新开始（无父对话），但不是空的。从父代理到子代理的唯一通道是 Agent 工具的提示词字符串，因此请直接在该提示词中包含子代理需要的任何文件路径、错误消息或决策。
子代理接收	子代理不接收
其自己的系统提示词（AgentDefinition.prompt）和 Agent 工具的提示词	父代理的对话历史或工具结果
项目 CLAUDE.md（通过 settingSources 加载）	预加载的技能内容，除非在 AgentDefinition.skills 中列出
工具定义（从父代理继承，或 tools 中的子集）	父代理的系统提示词
父代理逐字接收子代理的最终消息作为 Agent 工具结果，但可能在其自己的响应中总结它。要在面向用户的响应中逐字保留子代理输出，请在您传递给主 query() 调用的提示词或 systemPrompt 选项中包含一条指令。
​
调用子代理
​
自动调用
Claude 根据任务和每个子代理的 description 自动决定何时调用子代理。例如，如果您定义了一个 performance-optimizer 子代理，其描述为”用于查询调优的性能优化专家”，当您的提示词提到优化查询时，Claude 将调用它。
编写清晰、具体的描述，以便 Claude 可以将任务匹配到正确的子代理。
​
显式调用
要保证 Claude 使用特定的子代理，请在您的提示词中按名称提及它：
"Use the code-reviewer agent to check the authentication module"

这绕过自动匹配并直接调用命名的子代理。
​
动态代理配置
您可以根据运行时条件动态创建代理定义。此示例创建一个安全审查员，具有不同的严格级别，对严格审查使用更强大的模型。
Python
TypeScript
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition


# Factory function that returns an AgentDefinition
# This pattern lets you customize agents based on runtime conditions
def create_security_agent(security_level: str) -> AgentDefinition:
    is_strict = security_level == "strict"
    return AgentDefinition(
        description="Security code reviewer",
        # Customize the prompt based on strictness level
        prompt=f"You are a {'strict' if is_strict else 'balanced'} security reviewer...",
        tools=["Read", "Grep", "Glob"],
        # Key insight: use a more capable model for high-stakes reviews
        model="opus" if is_strict else "sonnet",
    )


async def main():
    # The agent is created at query time, so each request can use different settings
    async for message in query(
        prompt="Review this PR for security issues",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Grep", "Glob", "Agent"],
            agents={
                # Call the factory with your desired configuration
                "security-reviewer": create_security_agent("strict")
            },
        ),
    ):
        if hasattr(message, "result"):
            print(message.result)


asyncio.run(main())

​
检测子代理调用
子代理通过 Agent 工具调用。要检测何时调用子代理，请检查 tool_use 块，其中 name 是 "Agent"。来自子代理上下文内的消息包含 parent_tool_use_id 字段。
工具名称在 Claude Code v2.1.63 中从 "Task" 重命名为 "Agent"。当前 SDK 版本在 tool_use 块中发出 "Agent"，但在 system:init 工具列表和 result.permission_denials[].tool_name 中仍使用 "Task"。检查 block.name 中的两个值可确保跨 SDK 版本的兼容性。
此示例遍历流式消息，记录何时调用子代理以及后续消息何时源自该子代理的执行上下文。
消息结构在 SDK 之间有所不同。在 Python 中，内容块直接通过 message.content 访问。在 TypeScript 中，SDKAssistantMessage 包装 Claude API 消息，因此内容通过 message.message.content 访问。
Python
TypeScript
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition, ToolUseBlock


async def main():
    async for message in query(
        prompt="Use the code-reviewer agent to review this codebase",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Glob", "Grep", "Agent"],
            agents={
                "code-reviewer": AgentDefinition(
                    description="Expert code reviewer.",
                    prompt="Analyze code quality and suggest improvements.",
                    tools=["Read", "Glob", "Grep"],
                )
            },
        ),
    ):
        # Check for subagent invocation. Match both names: older SDK
        # versions emitted "Task", current versions emit "Agent".
        if hasattr(message, "content") and message.content:
            for block in message.content:
                if isinstance(block, ToolUseBlock) and block.name in (
                    "Task",
                    "Agent",
                ):
                    print(f"Subagent invoked: {block.input.get('subagent_type')}")

        # Check if this message is from within a subagent's context
        if hasattr(message, "parent_tool_use_id") and message.parent_tool_use_id:
            print("  (running inside subagent)")

        if hasattr(message, "result"):
            print(message.result)


asyncio.run(main())

​
恢复子代理
子代理可以恢复以继续中断的地方。恢复的子代理保留其完整的对话历史，包括所有先前的工具调用、结果和推理。子代理从停止的地方继续，而不是重新开始。
当子代理完成时，Claude 在 Agent 工具结果中接收其代理 ID。要以编程方式恢复子代理：
捕获会话 ID：在第一个查询期间从消息中提取 session_id
提取代理 ID：从消息内容中解析 agentId
恢复会话：在第二个查询的选项中传递 resume: sessionId，并在您的提示词中包含代理 ID
您必须恢复同一会话以访问子代理的记录。默认情况下，每个 query() 调用都会启动一个新会话，因此请传递 resume: sessionId 以在同一会话中继续。
如果您使用的是自定义代理（而不是内置代理），您还需要在两个查询的 agents 参数中传递相同的代理定义。
下面的示例演示了此流程：第一个查询运行子代理并捕获会话 ID 和代理 ID，然后第二个查询恢复会话以提出需要来自第一个分析的上下文的后续问题。
TypeScript
Python
import { query, type SDKMessage } from "@anthropic-ai/claude-agent-sdk";

// Helper to extract agentId from message content
// Stringify to avoid traversing different block types (TextBlock, ToolResultBlock, etc.)
function extractAgentId(message: SDKMessage): string | undefined {
  if (message.type !== "assistant" && message.type !== "user") return undefined;
  // Stringify the content so we can search it without traversing nested blocks
  const content = JSON.stringify(message.message.content);
  const match = content.match(/agentId:\s*([a-f0-9-]+)/);
  return match?.[1];
}

let agentId: string | undefined;
let sessionId: string | undefined;

// First invocation - use the Explore agent to find API endpoints
for await (const message of query({
  prompt: "Use the Explore agent to find all API endpoints in this codebase",
  options: { allowedTools: ["Read", "Grep", "Glob", "Agent"] }
})) {
  // Capture session_id from ResultMessage (needed to resume this session)
  if ("session_id" in message) sessionId = message.session_id;
  // Search message content for the agentId (appears in Agent tool results)
  const extractedId = extractAgentId(message);
  if (extractedId) agentId = extractedId;
  // Print the final result
  if ("result" in message) console.log(message.result);
}

// Second invocation - resume and ask follow-up
if (agentId && sessionId) {
  for await (const message of query({
    prompt: `Resume agent ${agentId} and list the top 3 most complex endpoints`,
    options: { allowedTools: ["Read", "Grep", "Glob", "Agent"], resume: sessionId }
  })) {
    if ("result" in message) console.log(message.result);
  }
}

子代理记录独立于主对话而持久存在：
主对话压缩：当主对话压缩时，子代理记录不受影响。它们存储在单独的文件中。
会话持久性：子代理记录在其会话内持久存在。您可以通过恢复同一会话在重启 Claude Code 后恢复子代理。
自动清理：记录根据 cleanupPeriodDays 设置进行清理（默认：30 天）。
​
工具限制
子代理可以通过 tools 字段具有受限的工具访问：
省略该字段：代理继承所有可用工具（默认）
指定工具：代理只能使用列出的工具
此示例创建一个只读分析代理，可以检查代码但无法修改文件或运行命令。
Python
TypeScript
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition


async def main():
    async for message in query(
        prompt="Analyze the architecture of this codebase",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Grep", "Glob", "Agent"],
            agents={
                "code-analyzer": AgentDefinition(
                    description="Static code analysis and architecture review",
                    prompt="""You are a code architecture analyst. Analyze code structure,
identify patterns, and suggest improvements without making changes.""",
                    # Read-only tools: no Edit, Write, or Bash access
                    tools=["Read", "Grep", "Glob"],
                )
            },
        ),
    ):
        if hasattr(message, "result"):
            print(message.result)


asyncio.run(main())

​
常见工具组合
用例	工具	描述
只读分析	Read、Grep、Glob	可以检查代码但不能修改或执行
测试执行	Bash、Read、Grep	可以运行命令并分析输出
代码修改	Read、Edit、Write、Grep、Glob	完整的读/写访问，无命令执行
完全访问	所有工具	从父代理继承所有工具（省略 tools 字段）
​
故障排除
​
Claude 不委派给子代理
如果 Claude 直接完成任务而不是委派给您的子代理：
包含 Agent 工具：子代理通过 Agent 工具调用，因此它必须在 allowedTools 中
使用显式提示：在您的提示词中按名称提及子代理（例如，“使用代码审查员代理来…”）
编写清晰的描述：准确解释何时应使用子代理，以便 Claude 可以适当地匹配任务
​
基于文件系统的代理未加载
在 .claude/agents/ 中定义的代理仅在启动时加载。如果在 Claude Code 运行时创建新的代理文件，请重启会话以加载它。
​
Windows：长提示词失败
在 Windows 上，具有非常长提示词的子代理可能因命令行长度限制（8191 个字符）而失败。保持提示词简洁或使用基于文件系统的代理来处理复杂指令。
​
相关文档
Claude Code 子代理：包括基于文件系统的定义的全面子代理文档
SDK 概述：Claude Agent SDK 入门

此页面对您有帮助吗？

是
否
使用工具搜索扩展到多个工具
修改系统提示词
⌘I

---

# 修改系统提示词

> 章节: 自定义行为 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/modifying-system-prompts

---

自定义行为
修改系统提示词

在 claude_code 预设和自定义系统提示词之间进行选择，并通过 CLAUDE.md、输出样式、追加或完全自定义提示词来自定义行为。

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

系统提示词定义了 Claude 的行为、能力和响应风格。从用于 CLI 或 IDE 类编码工具的 claude_code 预设开始，其中人类观察并指导工作。为具有不同界面、身份或权限模型的代理编写自己的提示词。
本页涵盖：
系统提示词如何工作，包含一个决策表，用于在预设、带有 append 的预设和自定义提示词之间进行选择
自定义代理行为，使用 CLAUDE.md 文件、输出样式、append 或自定义字符串
比较四种方法，按持久性、范围和它们保留的内容进行比较
组合方法，将自定义方法分层组合在一起
​
系统提示词的工作原理
系统提示词是初始指令集，它塑造了 Claude 在整个对话中的行为方式。Agent SDK 有三个起点：
最小默认值：当你在 TypeScript 中不设置 systemPrompt 或在 Python 中不设置 system_prompt 时，SDK 使用最小提示词，涵盖工具调用但省略了 Claude Code 的编码指南、响应风格和项目上下文。这与 claude -p 不同，后者默认使用完整的 Claude Code 提示词。如果你从 CLI 迁移并想要匹配的行为，请设置 claude_code 预设。
claude_code 预设：Claude Code CLI 使用的完整系统提示词，包含工具使用说明、代码风格和格式化指南、响应语气和详细程度规则、安全和安全指令，以及关于工作目录和环境的上下文。在 TypeScript 中设置 systemPrompt: { type: "preset", preset: "claude_code" }，或在 Python 中设置 system_prompt={"type": "preset", "preset": "claude_code"}，可选择使用 append 在末尾添加你自己的指令。
自定义字符串：你自己编写的提示词。SDK 仅发送你提供的内容。
​
决定起点
决定因素是你的代理与 Claude Code 的相似程度：一个在存储库中运行的编码代理，有人类观看流式输出并指导工作。你的产品离这个越远，你就越想编写自己的提示词。
你正在构建	使用	你获得的内容
一个 CLI 或类似 IDE 的编码工具，其中人类观看和指导，Claude Code 的默认值是你想要的	claude_code 预设	完整的 Claude Code 提示词：工具指导、安全规则、终端友好的响应、存储库约定感知
相同类型的工具，加上产品特定的规则，如编码标准、输出格式或域上下文	claude_code 预设加 append	上述所有内容，加上你的指令添加在预设之后。没有任何内容被删除，所以这是风险最低的自定义
具有不同表面、身份或权限模型的代理，或非编码代理	自定义提示词字符串	仅你编写的内容。你负责替换你的代理仍然需要的工具指导和安全指令
一个薄工具调用循环，没有代理角色，你在用户提示词中提供所有行为	无 systemPrompt 选项	最小默认值：工具调用支持，仅此而已
“不同于 Claude Code” 通常意味着以下之一：
不同的表面：输出不是由触发它的人在终端中读取的。聊天 UI、结构化输出消费者和非编码自动化各自需要一个与其输出呈现和审查方式相匹配的提示词。无人值守的编码自动化，如修复 lint 错误或审查差异的 CI 作业，仍然适合预设，因为工作本身就是预设为之编写的。
不同的身份：代理不应该将自己呈现为 Claude Code。支持机器人、数据分析助手或任何特定领域的代理需要自己的名称、范围和角色。
不同的权限模型：代理自主运行，无需人类批准每一步，或在一组狭窄的资源上运行。Claude Code 的提示词假设人类在循环中，可以访问完整的工具集。
非编码任务：Claude Code 提示词的大部分是编码指导。对于研究、内容或运营代理，该指导与你实际需要的指令竞争。
比较表显示了每种自定义方法保留的内容。
​
自定义 agent 行为
输出样式、append 和自定义提示词字符串各自直接改变系统提示词。CLAUDE.md 采用不同的方式：SDK 读取它并将其内容作为项目上下文注入到对话中，而不是注入到系统提示词中，因此它与你选择的任何系统提示词一起塑造行为。Skills、hooks 和 permissions 也在系统提示词之外塑造行为，并在各自的页面上介绍。
​
CLAUDE.md 文件用于项目级指令
CLAUDE.md 文件为 Claude 提供持久的项目上下文和指令。SDK 将其内容注入到对话中，而不是注入到系统提示词中，因此它们可以与任何系统提示词配置一起工作。关于在 CLAUDE.md 中放什么、在哪里放置它以及如何编写有效的指令，请参阅 Claude 如何记住你的项目。本节涵盖 SDK 特定的内容：CLAUDE.md 如何加载。
当匹配的设置源被启用时，SDK 读取 CLAUDE.md：'project' 从工作目录加载 CLAUDE.md 或 .claude/CLAUDE.md，'user' 加载 ~/.claude/CLAUDE.md。默认 query() 选项启用两个源，因此 CLAUDE.md 会自动加载。如果你在 TypeScript 中显式设置 settingSources 或在 Python 中设置 setting_sources，请包含你需要的源。CLAUDE.md 加载由设置源控制，而不是由 claude_code 预设控制。
​
使用 SDK 加载 CLAUDE.md
要加载 CLAUDE.md，请设置 settingSources 以包含你的 CLAUDE.md 所在的级别。下面的示例加载项目级 CLAUDE.md 以及 claude_code 预设，因此 Claude 既有完整的编码 agent 提示词，也有你的项目约定：
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

const messages = [];

for await (const message of query({
  prompt: "Add a new React component for user profiles",
  options: {
    systemPrompt: {
      type: "preset",
      preset: "claude_code" // 使用 Claude Code 的系统提示词
    },
    settingSources: ["project"] // 从项目加载 CLAUDE.md
  }
})) {
  messages.push(message);
}

// 现在 Claude 可以访问来自 CLAUDE.md 的项目指南

CLAUDE.md 在项目的所有会话中持久存在，通过 git 与你的团队共享，并自动发现而无需代码更改。如果你传递空的 settingSources 数组，则不会加载。
​
输出样式用于持久配置
输出样式是保存的配置，可以修改 Claude 的系统提示词。它们存储为 markdown 文件，可以在会话和项目中重复使用。
​
创建输出样式
输出样式是一个 markdown 文件，其 frontmatter 中有元数据，后面是提示词内容。将其保存到 ~/.claude/output-styles/ 以获得在每个项目中可用的用户级样式，或保存到你的存储库中的 .claude/output-styles/ 以获得可以提交和与你的团队共享的项目级样式。
默认情况下，自定义输出样式会用你自己的指令替换 claude_code 预设的软件工程指令。要保留它们并在其基础上分层你的指令，请在 frontmatter 中设置 keep-coding-instructions: true。当你的 agent 仍在进行软件工程工作时保留它们。当你完全替换角色时省略它们。
下面的示例定义了一个代码审查角色，它保留了编码指令，因为审查代码仍然受益于 Claude Code 的安全性和代码质量指导。将其保存为 ~/.claude/output-styles/code-reviewer.md 以在项目中可用：
~/.claude/output-styles/code-reviewer.md
---
name: Code Reviewer
description: Thorough code review assistant
keep-coding-instructions: true
---

You are an expert code reviewer.

For every code submission:
1. Check for bugs and security issues
2. Evaluate performance
3. Suggest improvements
4. Rate code quality (1-10)

​
激活输出样式
创建后，通过以下方式激活输出样式：
CLI：运行 /config 并选择输出样式
设置：在 .claude/settings.local.json 中设置 outputStyle
TypeScript SDK：在传递给 query() 的内联 settings 对象内设置 outputStyle，或将 settings 指向设置它的设置文件。outputStyle 不是顶级 Options 字段
Python SDK 没有以编程方式选择输出样式的选项。对于无法写入 .claude/settings.local.json 的仅代码部署，请改用 append 或自定义提示词字符串。
SDK 用户注意： 当你在选项中包含 settingSources: ['user'] 或 settingSources: ['project']（TypeScript）/ setting_sources=["user"] 或 setting_sources=["project"]（Python）时，输出样式会被加载。
​
追加到 claude_code 预设
你可以使用带有 append 属性的 Claude Code 预设来添加自定义指令，同时保留所有内置功能。
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

const messages = [];

for await (const message of query({
  prompt: "Help me write a Python function to calculate fibonacci numbers",
  options: {
    systemPrompt: {
      type: "preset",
      preset: "claude_code",
      append: "Always include detailed docstrings and type hints in Python code."
    }
  }
})) {
  messages.push(message);
  if (message.type === "assistant") {
    console.log(message.message.content);
  }
}

​
改进跨用户和机器的提示词缓存
默认情况下，两个使用相同 claude_code 预设和 append 文本的会话，如果从不同的工作目录运行，仍然无法共享提示词缓存条目。这是因为预设在你的 append 文本之前在系统提示词中嵌入了每个会话的上下文：工作目录、它是否是 git 存储库、平台、活跃的 shell、操作系统版本和自动记忆路径。该上下文中的任何差异都会产生不同的系统提示词和缓存未命中。CLAUDE.md 内容不会影响系统提示词缓存，因为 SDK 将其注入到对话中，而不是系统提示词。
要使系统提示词在会话中相同，请在 TypeScript 中设置 excludeDynamicSections: true，或在 Python 中设置 "exclude_dynamic_sections": True。每个会话的上下文移动到第一条用户消息中，只在系统提示词中保留静态预设和你的 append 文本，以便相同的配置在用户和机器之间共享缓存条目。
excludeDynamicSections 需要 @anthropic-ai/claude-agent-sdk v0.2.98 或更高版本，或 Python 的 claude-agent-sdk v0.1.58 或更高版本。它仅适用于预设对象形式，当 systemPrompt 是字符串时无效。
以下示例将共享的 append 块与 excludeDynamicSections 配对，以便从不同目录运行的 agent 群可以重复使用相同的缓存系统提示词：
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Triage the open issues in this repo",
  options: {
    systemPrompt: {
      type: "preset",
      preset: "claude_code",
      append: "You operate Acme's internal triage workflow. Label issues by component and severity.",
      excludeDynamicSections: true
    }
  }
})) {
  // ...
}

权衡： 工作目录、git 存储库标志、平台、活跃的 shell、操作系统版本和自动记忆路径仍然会到达 Claude，但作为第一条用户消息的一部分，而不是系统提示词。用户消息中的指令比系统提示词中的相同文本的权重略低，因此在推理当前目录或自动记忆路径时，Claude 可能会更少地依赖它们。当跨会话缓存重复使用比最大化权威环境上下文更重要时，启用此选项。
对于非交互式 CLI 模式中的等效标志，请参阅 --exclude-dynamic-system-prompt-sections。
​
自定义系统提示词
你可以提供自定义字符串作为 systemPrompt 以完全用你自己的指令替换默认值。
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

const customPrompt = `You are a Python coding specialist.
Follow these guidelines:
- Write clean, well-documented code
- Use type hints for all functions
- Include comprehensive docstrings
- Prefer functional programming patterns when appropriate
- Always explain your code choices`;

const messages = [];

for await (const message of query({
  prompt: "Create a data processing pipeline",
  options: {
    systemPrompt: customPrompt
  }
})) {
  messages.push(message);
  if (message.type === "assistant") {
    console.log(message.message.content);
  }
}

​
比较四种方法
这四种自定义方法在存储位置、共享方式以及从 claude_code 预设保留的内容方面有所不同。
功能	CLAUDE.md	输出样式	带有追加的 systemPrompt	自定义 systemPrompt
持久性	每个项目文件	保存为文件	仅会话	仅会话
可重用性	每个项目	跨项目	代码重复	代码重复
管理	在文件系统上	CLI + 文件	在代码中	在代码中
默认工具	保留	保留	保留	丢失（除非包含）
内置安全	维护	维护	维护	必须添加
环境上下文	自动	自动	自动	必须提供
自定义级别	仅添加	替换或扩展默认	仅添加	完全控制
版本控制	与项目一起	是	与代码一起	与代码一起
范围	项目特定	用户或项目	代码会话	代码会话
“带有追加”是指在 TypeScript 中使用 systemPrompt: { type: "preset", preset: "claude_code", append: "..." }，或在 Python 中使用 system_prompt={"type": "preset", "preset": "claude_code", "append": "..."}。CLAUDE.md 不会改变系统提示本身：SDK 将其内容作为项目上下文注入到对话中。
​
用例和最佳实践
​
何时使用 CLAUDE.md
使用 CLAUDE.md 来存储应该应用于项目中每个会话的指令，无论该会话使用哪个系统提示词：编码标准、常见命令、架构上下文和团队约定。CLAUDE.md 被提交到你的存储库，因此它与它描述的代码保持同步。有关完整指导，请参阅 何时添加到 CLAUDE.md。
当启用 project 设置源时，CLAUDE.md 文件会加载，这对默认的 query() 选项是这样的。如果你显式设置 settingSources（TypeScript）或 setting_sources（Python），请包含 'project' 以继续加载项目级 CLAUDE.md。
​
何时使用输出样式
输出样式用于你想在 CLI 和 SDK 中重复使用的角色，而无需更改应用程序代码。因为它们作为文件存在于 .claude/output-styles 中，同一个角色可从 CLI 中的 /config 和加载匹配设置源的任何 SDK 会话中获得。
最适合：
跨会话的持久行为更改
团队共享配置
专门的助手，如代码审查者、数据科学家或 DevOps 助手
需要版本控制的复杂提示词修改
示例：
创建专用的 SQL 优化助手
构建安全聚焦的代码审查者
开发具有特定教学法的教学助手
​
何时使用带有追加的 systemPrompt
当 claude_code 预设已经适合你的产品，而你只需要添加额外指令时，使用 append。你保留预设的工具指导、安全规则和编码约定，而无需重新实现它们。
最适合：
添加特定的编码标准或偏好
自定义输出格式
添加特定领域的知识
修改响应详细程度
增强 Claude Code 的默认行为而不失去工具指令
​
何时使用自定义 systemPrompt
当你的代理的表面、身份或权限模型与 Claude Code 的不同时，使用自定义提示词，如 决定起点 中所述。你定义完整的指令集，包括你的代理需要的任何工具指导和安全规则。
最适合：
完全控制 Claude 的行为
专门的单会话任务
测试新的提示词策略
不需要默认工具的情况
构建具有独特行为的专门代理
​
组合方法
这些方法可以组合使用。持久化的输出样式或 CLAUDE.md 设置长期行为，而 append 在不触及保存配置的情况下在顶部分层会话特定的指令。
​
将输出样式与会话特定的添加组合
下面的示例假设代码审查员输出样式已经处于活动状态。append 块在角色的基础上分层会话特定的焦点区域，因此单个审查会话可以优先考虑 OAuth 和令牌存储，而无需更改保存的输出样式：
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

// 假设"Code Reviewer"输出样式处于活动状态（通过 /config 或设置）
// 添加会话特定的焦点区域
const messages = [];

for await (const message of query({
  prompt: "Review this authentication module",
  options: {
    systemPrompt: {
      type: "preset",
      preset: "claude_code",
      append: `
        For this review, prioritize:
        - OAuth 2.0 compliance
        - Token storage security
        - Session management
      `
    }
  }
})) {
  messages.push(message);
}

​
另请参阅
输出样式：为 CLI 创建、管理和共享输出样式，包括文件格式和存储位置
Claude 如何记住您的项目：CLAUDE.md 中应放入的内容、放置位置以及如何编写有效的项目说明
TypeScript SDK 参考：完整的 Options 类型，包括 systemPrompt、settingSources 和 settings
Python SDK 参考：完整的 ClaudeAgentOptions 类型，包括 system_prompt 和 setting_sources
Settings：settings.json 参考，包括输出样式和其他配置的存储位置

此页面对您有帮助吗？

是
否
SDK 中的子代理
SDK 中的 slash commands
⌘I

---

# SDK 中的 slash commands

> 章节: 自定义行为 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/slash-commands

---

自定义行为
SDK 中的 slash commands

学习如何通过 SDK 使用 slash commands 来控制 Claude Code 会话

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

Slash commands 提供了一种方式来控制 Claude Code 会话，使用以 / 开头的特殊命令。这些命令可以通过 SDK 发送，以执行诸如压缩上下文、列出上下文使用情况或调用自定义命令等操作。只有在不需要交互式终端的情况下工作的命令才能通过 SDK 分派；system/init 消息列出了在您的会话中可用的命令。
​
发现可用的 Slash Commands
Claude Agent SDK 在系统初始化消息中提供有关可用 slash commands 的信息。在您的会话开始时访问此信息：
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Hello Claude",
  options: { maxTurns: 1 }
})) {
  if (message.type === "system" && message.subtype === "init") {
    console.log("Available slash commands:", message.slash_commands);
    // Example output: ["/compact", "/context", "/usage"]
  }
}

​
发送 Slash Commands
通过在您的提示字符串中包含 slash commands 来发送它们，就像常规文本一样：
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

// Send a slash command
for await (const message of query({
  prompt: "/compact",
  options: { maxTurns: 1 }
})) {
  if (message.type === "result" && message.subtype === "success") {
    console.log("Command executed:", message.result);
  }
}

​
常见的 Slash Commands
​
/compact - 压缩对话历史
/compact 命令通过总结较早的消息同时保留重要上下文来减少您的对话历史的大小：
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "/compact",
  options: { maxTurns: 1 }
})) {
  if (message.type === "system" && message.subtype === "compact_boundary") {
    console.log("Compaction completed");
    console.log("Pre-compaction tokens:", message.compact_metadata.pre_tokens);
    console.log("Trigger:", message.compact_metadata.trigger);
  }
}

​
清除对话
交互式 /clear 命令在 SDK 中不可用。每个 query() 调用已经开始一个新的对话，所以要清除上下文，请结束当前的 query() 并开始一个新的。之前的对话保存在磁盘上，可以通过将其会话 ID 传递给 resume 选项 来返回。
​
创建自定义 Slash Commands
除了使用内置 slash commands 外，您还可以创建自己的自定义命令，这些命令可通过 SDK 使用。自定义命令定义为特定目录中的 markdown 文件，类似于 subagents 的配置方式。
.claude/commands/ 目录是旧版格式。推荐的格式是 .claude/skills/<name>/SKILL.md，它支持相同的 slash command 调用（/name）加上 Claude 的自主调用。有关当前格式，请参阅 Skills。CLI 继续支持两种格式，下面的示例对于 .claude/commands/ 仍然准确。
​
文件位置
自定义 slash commands 根据其范围存储在指定的目录中：
项目命令：.claude/commands/ - 仅在当前项目中可用（旧版；优先使用 .claude/skills/）
个人命令：~/.claude/commands/ - 在您的所有项目中可用（旧版；优先使用 ~/.claude/skills/）
​
文件格式
每个自定义命令都是一个 markdown 文件，其中：
文件名（不带 .md 扩展名）成为命令名称
文件内容定义命令的功能
可选的 YAML frontmatter 提供配置
​
基本示例
创建 .claude/commands/refactor.md：
Refactor the selected code to improve readability and maintainability.
Focus on clean code principles and best practices.

这创建了 /refactor 命令，您可以通过 SDK 使用它。
​
带有 Frontmatter
创建 .claude/commands/security-check.md：
---
allowed-tools: Read, Grep, Glob
description: Run security vulnerability scan
model: claude-opus-4-7
---

Analyze the codebase for security vulnerabilities including:
- SQL injection risks
- XSS vulnerabilities
- Exposed credentials
- Insecure configurations

​
在 SDK 中使用自定义命令
一旦在文件系统中定义，自定义命令就会自动通过 SDK 可用：
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

// Use a custom command
for await (const message of query({
  prompt: "/refactor src/auth/login.ts",
  options: { maxTurns: 3 }
})) {
  if (message.type === "assistant") {
    console.log("Refactoring suggestions:", message.message);
  }
}

// Custom commands appear in the slash_commands list
for await (const message of query({
  prompt: "Hello",
  options: { maxTurns: 1 }
})) {
  if (message.type === "system" && message.subtype === "init") {
    // Will include both built-in and custom commands
    console.log("Available commands:", message.slash_commands);
    // Example: ["/compact", "/context", "/usage", "/refactor", "/security-check"]
  }
}

​
高级功能
​
参数和占位符
自定义命令支持使用占位符的动态参数：
创建 .claude/commands/fix-issue.md：
---
argument-hint: [issue-number] [priority]
description: Fix a GitHub issue
---

Fix issue #$1 with priority $2.
Check the issue description and implement the necessary changes.

在 SDK 中使用：
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

// Pass arguments to custom command
for await (const message of query({
  prompt: "/fix-issue 123 high",
  options: { maxTurns: 5 }
})) {
  // Command will process with $1="123" and $2="high"
  if (message.type === "result" && message.subtype === "success") {
    console.log("Issue fixed:", message.result);
  }
}

​
Bash 命令执行
自定义命令可以执行 bash 命令并包含其输出：
创建 .claude/commands/git-commit.md：
---
allowed-tools: Bash(git add *), Bash(git status *), Bash(git commit *)
description: Create a git commit
---

## Context

- Current status: !`git status`
- Current diff: !`git diff HEAD`

## Task

Create a git commit with appropriate message based on the changes.

​
文件引用
使用 @ 前缀包含文件内容：
创建 .claude/commands/review-config.md：
---
description: Review configuration files
---

Review the following configuration files for issues:
- Package config: @package.json
- TypeScript config: @tsconfig.json
- Environment config: @.env

Check for security issues, outdated dependencies, and misconfigurations.

​
使用命名空间进行组织
在子目录中组织命令以获得更好的结构：
.claude/commands/
├── frontend/
│   ├── component.md      # Creates /component (project:frontend)
│   └── style-check.md     # Creates /style-check (project:frontend)
├── backend/
│   ├── api-test.md        # Creates /api-test (project:backend)
│   └── db-migrate.md      # Creates /db-migrate (project:backend)
└── review.md              # Creates /review (project)

子目录出现在命令描述中，但不影响命令名称本身。
​
实际示例
​
代码审查命令
创建 .claude/commands/code-review.md：
---
allowed-tools: Read, Grep, Glob, Bash(git diff *)
description: Comprehensive code review
---

## Changed Files
!`git diff --name-only HEAD~1`

## Detailed Changes
!`git diff HEAD~1`

## Review Checklist

Review the above changes for:
1. Code quality and readability
2. Security vulnerabilities
3. Performance implications
4. Test coverage
5. Documentation completeness

Provide specific, actionable feedback organized by priority.

​
测试运行器命令
创建 .claude/commands/test.md：
---
allowed-tools: Bash, Read, Edit
argument-hint: [test-pattern]
description: Run tests with optional pattern
---

Run tests matching pattern: $ARGUMENTS

1. Detect the test framework (Jest, pytest, etc.)
2. Run tests with the provided pattern
3. If tests fail, analyze and fix them
4. Re-run to verify fixes

通过 SDK 使用这些命令：
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

// Run code review
for await (const message of query({
  prompt: "/code-review",
  options: { maxTurns: 3 }
})) {
  // Process review feedback
}

// Run specific tests
for await (const message of query({
  prompt: "/test auth",
  options: { maxTurns: 5 }
})) {
  // Handle test results
}

​
另请参阅
Slash Commands - 完整的 slash command 文档
SDK 中的 Subagents - 类似的基于文件系统的 subagents 配置
TypeScript SDK 参考 - 完整的 API 文档
SDK 概述 - 一般 SDK 概念
CLI 参考 - 命令行界面

此页面对您有帮助吗？

是
否
修改系统提示词
SDK 中的 Agent Skills
⌘I

---

# SDK 中的 Agent Skills

> 章节: 自定义行为 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/skills

---

自定义行为
SDK 中的 Agent Skills

使用 Claude Agent SDK 中的 Agent Skills 扩展 Claude 的专业能力

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

​
概述
Agent Skills 通过专业能力扩展 Claude，Claude 会在相关时自动调用这些能力。Skills 被打包为 SKILL.md 文件，包含说明、描述和可选的支持资源。
有关 Skills 的全面信息，包括优势、架构和编写指南，请参阅 Agent Skills 概述。
​
Skills 如何与 SDK 配合使用
使用 Claude Agent SDK 时，Skills 的工作方式如下：
定义为文件系统工件：在特定目录（.claude/skills/）中创建为 SKILL.md 文件
从文件系统加载：Skills 从由 settingSources（TypeScript）或 setting_sources（Python）管理的文件系统位置加载
自动发现：加载文件系统设置后，在启动时从用户和项目目录发现 Skill 元数据；触发时加载完整内容
由模型调用：Claude 根据上下文自动选择何时使用它们
通过 skills 选项过滤：发现的 Skills 默认启用。传递 Skill 名称列表、"all" 或 [] 来控制会话中可用的 Skills
与子代理（可以通过编程方式定义）不同，Skills 必须创建为文件系统工件。SDK 不提供用于注册 Skills 的编程 API。
Skills 通过文件系统设置源发现。使用默认 query() 选项时，SDK 加载用户和项目源，因此 ~/.claude/skills/、<cwd>/.claude/skills/ 和 <cwd> 到存储库根目录之间任何父目录中的 .claude/skills/ 中的 Skills 可用。如果显式设置 settingSources，请包含 'user' 或 'project' 以保持 Skill 发现，或使用 plugins 选项 从特定路径加载 Skills。
​
在 SDK 中使用 Skills
在 query() 上设置 skills 选项以控制会话中可用的 Skills。省略时，发现的 Skills 启用且 Skill 工具可用，与 CLI 行为匹配。传递 "all" 以启用每个发现的 Skill，传递 Skill 名称列表以仅启用那些，或传递 [] 以禁用所有。设置 skills 时，SDK 自动启用 Skill 工具，因此无需在 allowedTools 中列出它。
配置后，Claude 自动从文件系统发现 Skills 并在与用户请求相关时调用它们。
Python
TypeScript
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def main():
    options = ClaudeAgentOptions(
        cwd="/path/to/project",  # Project with .claude/skills/
        setting_sources=["user", "project"],  # Load Skills from filesystem
        skills="all",  # Enable every discovered Skill
        allowed_tools=["Read", "Write", "Bash"],
    )

    async for message in query(
        prompt="Help me process this PDF document", options=options
    ):
        print(message)


asyncio.run(main())

要仅启用特定 Skills，请传递它们的名称。名称与 SKILL.md 中的 name 字段或 Skill 的目录名称匹配。对于插件提供的 Skills，使用 plugin:skill。
Python
TypeScript
options = ClaudeAgentOptions(skills=["pdf", "docx"])

skills 选项是上下文过滤器，不是沙箱。未列出的 Skills 对模型隐藏，并被 Skill 工具拒绝，但它们的文件仍在磁盘上，可通过 Read 和 Bash 访问。
​
Skill 位置
Skills 根据您的 settingSources/setting_sources 配置从文件系统目录加载：
项目 Skills（.claude/skills/）：通过 git 与您的团队共享 - 当 setting_sources 包含 "project" 时加载
用户 Skills（~/.claude/skills/）：跨所有项目的个人 Skills - 当 setting_sources 包含 "user" 时加载
插件 Skills：与已安装的 Claude Code 插件捆绑
​
创建 Skills
Skills 定义为包含带有 YAML frontmatter 和 Markdown 内容的 SKILL.md 文件的目录。description 字段确定 Claude 何时调用您的 Skill。
示例目录结构：
.claude/skills/processing-pdfs/
└── SKILL.md

有关创建 Skills 的完整指导，包括 SKILL.md 结构、多文件 Skills 和示例，请参阅：
Claude Code 中的 Agent Skills：包含示例的完整指南
Agent Skills 最佳实践：编写指南和命名约定
​
工具限制
SKILL.md 中的 allowed-tools frontmatter 字段仅在直接使用 Claude Code CLI 时受支持。通过 SDK 使用 Skills 时不适用。
使用 SDK 时，通过查询配置中的主 allowedTools 选项控制工具访问。
要在 SDK 应用程序中控制 Skills 的工具访问，使用 allowedTools 预先批准特定工具。没有 canUseTool 回调时，列表中没有的任何内容都被拒绝：
假设第一个示例中的导入语句在以下代码片段中。
Python
TypeScript
options = ClaudeAgentOptions(
    setting_sources=["user", "project"],  # Load Skills from filesystem
    skills="all",
    allowed_tools=["Read", "Grep", "Glob"],
)

async for message in query(prompt="Analyze the codebase structure", options=options):
    print(message)

​
发现可用的 Skills
要查看 SDK 应用程序中可用的 Skills，只需询问 Claude：
Python
TypeScript
options = ClaudeAgentOptions(
    setting_sources=["user", "project"],  # Load Skills from filesystem
    skills="all",
)

async for message in query(prompt="What Skills are available?", options=options):
    print(message)

Claude 将根据您当前的工作目录和已安装的插件列出可用的 Skills。
​
测试 Skills
通过提出与其描述匹配的问题来测试 Skills：
Python
TypeScript
options = ClaudeAgentOptions(
    cwd="/path/to/project",
    setting_sources=["user", "project"],  # Load Skills from filesystem
    skills="all",
    allowed_tools=["Read", "Bash"],
)

async for message in query(prompt="Extract text from invoice.pdf", options=options):
    print(message)

如果描述与您的请求匹配，Claude 会自动调用相关的 Skill。
​
故障排除
​
找不到 Skills
检查 settingSources 配置：Skills 通过 user 和 project 设置源发现。如果显式设置 settingSources/setting_sources 并省略这些源，Skills 不会加载：
Python
TypeScript
# Skills not loaded: setting_sources excludes user and project
options = ClaudeAgentOptions(setting_sources=[], skills="all")

# Skills loaded: user and project sources included
options = ClaudeAgentOptions(
    setting_sources=["user", "project"],
    skills="all",
)

有关 settingSources/setting_sources 的更多详情，请参阅 TypeScript SDK 参考 或 Python SDK 参考。
检查工作目录：SDK 从 cwd 选项中的 .claude/skills/ 以及直到仓库根目录的每个父目录加载 Skills。确保 cwd 指向包含 .claude/skills/ 的目录或其下方目录，且在同一仓库内：
Python
TypeScript
# Ensure your cwd points to the directory containing .claude/skills/
options = ClaudeAgentOptions(
    cwd="/path/to/project",  # .claude/skills/ here or in a parent directory
    setting_sources=["user", "project"],  # Loads skills from these sources
    skills="all",
)

有关完整模式，请参阅上面的”在 SDK 中使用 Skills”部分。
验证文件系统位置：
# Check project Skills
ls .claude/skills/*/SKILL.md

# Check personal Skills
ls ~/.claude/skills/*/SKILL.md

​
Skill 未被使用
检查 skills 选项：如果传递了 skills 列表，确认 Skill 的名称已包含。传递 [] 会禁用所有 Skills。
检查描述：确保它具体且包含相关关键字。有关编写有效描述的指导，请参阅 Agent Skills 最佳实践。
​
其他故障排除
有关一般 Skills 故障排除（YAML 语法、调试等），请参阅 Claude Code Skills 故障排除部分。
​
相关文档
​
Skills 指南
Claude Code 中的 Agent Skills：包含创建、示例和故障排除的完整 Skills 指南
Agent Skills 概述：概念概述、优势和架构
Agent Skills 最佳实践：有效 Skills 的编写指南
Agent Skills 食谱：示例 Skills 和模板
​
SDK 资源
SDK 中的子代理：具有编程选项的类似文件系统代理
SDK 中的 Slash Commands：用户调用的命令
SDK 概述：常规 SDK 概念
TypeScript SDK 参考：完整 API 文档
Python SDK 参考：完整 API 文档

此页面对您有帮助吗？

是
否
SDK 中的 slash commands
SDK 中的 Plugins
⌘I

---

# SDK 中的 Plugins

> 章节: 自定义行为 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/plugins

---

自定义行为
SDK 中的 Plugins

通过 Agent SDK 加载自定义 plugins，使用命令、agents、skills 和 hooks 扩展 Claude Code

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

Plugins 允许你使用可在项目间共享的自定义功能来扩展 Claude Code。通过 Agent SDK，你可以以编程方式从本地目录加载 plugins，以便向 agent 会话添加自定义 slash commands、agents、skills、hooks 和 MCP servers。
​
什么是 plugins？
Plugins 是 Claude Code 扩展的包，可以包括：
Skills：Claude 自主使用的模型调用功能（也可以使用 /skill-name 调用）
Agents：用于特定任务的专门子 agents
Hooks：响应工具使用和其他事件的事件处理程序
MCP servers：通过 Model Context Protocol 的外部工具集成
commands/ 目录是旧版格式。对于新 plugins，请使用 skills/。Claude Code 继续支持两种格式以实现向后兼容性。
有关 plugin 结构和如何创建 plugins 的完整信息，请参阅 Plugins。
​
加载 plugins
通过在选项配置中提供本地文件系统路径来加载 plugins。type 字段必须是 "local"，这是 SDK 接受的唯一值。要使用通过 marketplace 或远程存储库分发的 plugin，请先下载它并提供本地目录路径。SDK 支持从不同位置加载多个 plugins。
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Hello",
  options: {
    plugins: [
      { type: "local", path: "./my-plugin" },
      { type: "local", path: "/absolute/path/to/another-plugin" }
    ]
  }
})) {
  // Plugin commands, agents, and other features are now available
}

​
路径规范
Plugin 路径可以是：
相对路径：相对于你的当前工作目录解析（例如，"./plugins/my-plugin"）
绝对路径：完整文件系统路径（例如，"/home/user/plugins/my-plugin"）
路径应指向 plugin 的根目录（包含 .claude-plugin/plugin.json 的目录）。
​
验证 plugin 安装
当 plugins 成功加载时，它们会出现在系统初始化消息中。你可以验证你的 plugins 是否可用：
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Hello",
  options: {
    plugins: [{ type: "local", path: "./my-plugin" }]
  }
})) {
  if (message.type === "system" && message.subtype === "init") {
    // 检查已加载的 plugins
    console.log("Plugins:", message.plugins);
    // 示例: [{ name: "my-plugin", path: "./my-plugin" }]

    // 检查来自 plugins 的可用命令
    console.log("Commands:", message.slash_commands);
    // 示例: ["/help", "/compact", "my-plugin:custom-command"]
  }
}

​
使用 plugin skills
来自 plugins 的 skills 会自动使用 plugin 名称进行命名空间划分，以避免冲突。当作为 slash commands 调用时，格式为 plugin-name:skill-name。
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

// Load a plugin with a custom /greet skill
for await (const message of query({
  prompt: "/my-plugin:greet", // Use plugin skill with namespace
  options: {
    plugins: [{ type: "local", path: "./my-plugin" }]
  }
})) {
  // Claude executes the custom greeting skill from the plugin
  if (message.type === "assistant") {
    console.log(message.message.content);
  }
}

如果你通过 CLI 安装了 plugin（例如，/plugin install my-plugin@marketplace），你仍然可以通过提供其安装路径在 SDK 中使用它。检查 ~/.claude/plugins/ 以查找 CLI 安装的 plugins。
​
完整示例
这是一个演示 plugin 加载和使用的完整示例：
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";
import * as path from "path";

async function runWithPlugin() {
  const pluginPath = path.join(__dirname, "plugins", "my-plugin");

  console.log("Loading plugin from:", pluginPath);

  for await (const message of query({
    prompt: "What custom commands do you have available?",
    options: {
      plugins: [{ type: "local", path: pluginPath }],
      maxTurns: 3
    }
  })) {
    if (message.type === "system" && message.subtype === "init") {
      console.log("Loaded plugins:", message.plugins);
      console.log("Available commands:", message.slash_commands);
    }

    if (message.type === "assistant") {
      console.log("Assistant:", message.message.content);
    }
  }
}

runWithPlugin().catch(console.error);

​
Plugin 结构参考
Plugin 目录必须包含 .claude-plugin/plugin.json 清单文件。它可以选择性地包括：
my-plugin/
├── .claude-plugin/
│   └── plugin.json          # Required: plugin manifest
├── skills/                   # Agent Skills (invoked autonomously or via /skill-name)
│   └── my-skill/
│       └── SKILL.md
├── commands/                 # Legacy: use skills/ instead
│   └── custom-cmd.md
├── agents/                   # Custom agents
│   └── specialist.md
├── hooks/                    # Event handlers
│   └── hooks.json
└── .mcp.json                # MCP server definitions

有关创建 plugins 的详细信息，请参阅：
Plugins - 完整的 plugin 开发指南
Plugins reference - 技术规范和架构
​
常见用例
​
开发和测试
在开发期间加载 plugins，无需全局安装它们：
plugins: [{ type: "local", path: "./dev-plugins/my-plugin" }];

​
项目特定的扩展
在你的项目存储库中包含 plugins，以实现团队范围的一致性：
plugins: [{ type: "local", path: "./project-plugins/team-workflows" }];

​
多个 plugin 源
组合来自不同位置的 plugins：
plugins: [
  { type: "local", path: "./local-plugin" },
  { type: "local", path: "~/.claude/custom-plugins/shared-plugin" }
];

​
故障排除
​
Plugin 未加载
如果你的 plugin 未出现在初始化消息中：
检查路径：确保路径指向 plugin 根目录（包含 .claude-plugin/）
验证 plugin.json：确保你的清单文件具有有效的 JSON 语法
检查文件权限：确保 plugin 目录可读
​
Skills 未出现
如果 plugin skills 不起作用：
使用命名空间：作为 slash commands 调用时，plugin skills 需要 plugin-name:skill-name 格式
检查初始化消息：验证 skill 是否以正确的命名空间出现在 slash_commands 中
验证 skill 文件：确保每个 skill 在 skills/ 下的自己的子目录中都有一个 SKILL.md 文件（例如，skills/my-skill/SKILL.md）
​
路径解析问题
如果相对路径不起作用：
检查工作目录：相对路径从你的当前工作目录解析
使用绝对路径：为了可靠性，考虑使用绝对路径
规范化路径：使用路径实用程序正确构造路径
​
另请参阅
Plugins - 完整的 plugin 开发指南
Plugins reference - 技术规范
Slash Commands - 在 SDK 中使用 slash commands
Subagents - 使用专门的 agents
Skills - 使用 Agent Skills

此页面对您有帮助吗？

是
否
SDK 中的 Agent Skills
配置权限
⌘I

---

# 配置权限

> 章节: 控制和可观测性 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/permissions

---

控制和可观测性
配置权限

使用权限模式、hooks 和声明式允许/拒绝规则来控制您的代理如何使用工具。

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

Claude Agent SDK 提供权限控制来管理 Claude 如何使用工具。使用权限模式和规则来定义自动允许的内容，以及使用 canUseTool 回调 在运行时处理其他所有情况。
本页面涵盖权限模式和规则。要构建交互式批准流程，其中用户在运行时批准或拒绝工具请求，请参阅 处理批准和用户输入。
​
权限如何被评估
当 Claude 请求一个工具时，SDK 按以下顺序检查权限：
1

Hooks

首先运行 hooks。一个 hook 可以直接拒绝调用或将其传递下去。返回 allow 的 hook 不会跳过下面的拒绝和询问规则；无论 hook 结果如何，这些规则都会被评估。
2

拒绝规则

检查 deny 规则（来自 disallowed_tools 和 settings.json）。如果拒绝规则匹配，工具被阻止，即使在 bypassPermissions 模式下也是如此。裸名称拒绝规则（如 Bash）在此评估开始之前将工具从 Claude 的上下文中移除，因此只有作用域规则（如 Bash(rm *)）在此步骤中被检查。
3

权限模式

应用活跃的 权限模式。bypassPermissions 批准到达此步骤的所有内容。acceptEdits 批准文件操作。其他模式会继续进行。
4

允许规则

检查 allow 规则（来自 allowed_tools 和 settings.json）。如果规则匹配，工具被批准。
5

canUseTool 回调

如果上述任何步骤都未解决，调用您的 canUseTool 回调 以获得决定。在 dontAsk 模式下，此步骤被跳过，工具被拒绝。
本页面重点关注 允许和拒绝规则 以及 权限模式。对于其他步骤：
Hooks： 运行自定义代码以允许、拒绝或修改工具请求。请参阅 使用 hooks 控制执行。
canUseTool 回调： 在运行时提示用户批准。请参阅 处理批准和用户输入。
​
允许和拒绝规则
allowed_tools 和 disallowed_tools（TypeScript：allowedTools / disallowedTools）向上面评估流程中的允许和拒绝规则列表添加条目。允许规则仅影响批准：未在 allowed_tools 中列出的工具仍然可供 Claude 使用，并继续进行权限模式。拒绝规则的行为取决于它们是命名工具还是在工具内范围化模式。
选项	效果
allowed_tools=["Read", "Grep"]	Read 和 Grep 被自动批准。此处未列出的工具仍然存在并继续进行权限模式和 canUseTool。
disallowed_tools=["Bash"]	Bash 工具定义从请求中移除。Claude 看不到该工具，无法尝试它。
disallowed_tools=["Bash(rm *)"]	Bash 保持可用。与 rm * 匹配的调用在每个权限模式中都被拒绝，包括 bypassPermissions。其他 Bash 调用继续进行权限模式。
对于锁定的代理，将 allowedTools 与 permissionMode: "dontAsk" 配对。列出的工具被批准；其他任何内容都被直接拒绝，而不是提示：
const options = {
  allowedTools: ["Read", "Glob", "Grep"],
  permissionMode: "dontAsk"
};

allowed_tools 不约束 bypassPermissions。 allowed_tools 仅预批准您列出的工具。未列出的工具不与任何允许规则匹配，并继续进行权限模式，其中 bypassPermissions 批准它们。设置 allowed_tools=["Read"] 与 permission_mode="bypassPermissions" 一起仍然批准每个工具，包括 Bash、Write 和 Edit。如果您需要 bypassPermissions 但想要阻止特定工具，请使用 disallowed_tools。
您也可以在 .claude/settings.json 中声明式地配置允许、拒绝和询问规则。当启用 project 设置源时，这些规则被读取，默认 query() 选项就是这样。如果您显式设置 setting_sources（TypeScript：settingSources），请包含 "project" 以使其应用。请参阅 权限设置 了解规则语法。
​
权限模式
权限模式提供对 Claude 如何使用工具的全局控制。您可以在调用 query() 时设置权限模式，或在流式会话期间动态更改它。
​
可用模式
SDK 支持这些权限模式：
模式	描述	工具行为
default	标准权限行为	无自动批准；不匹配的工具触发您的 canUseTool 回调
dontAsk	拒绝而不是提示	任何未被 allowed_tools 或规则预批准的内容都被拒绝；canUseTool 永远不会被调用
acceptEdits	自动接受文件编辑	文件编辑和 文件系统操作（mkdir、rm、mv 等）被自动批准
bypassPermissions	绕过所有权限检查	所有工具运行而无需权限提示（谨慎使用）
plan	规划模式	只读工具运行；Claude 分析和规划而不编辑您的源文件
auto（仅 TypeScript）	模型分类批准	模型分类器批准或拒绝每个工具调用。请参阅 Auto 模式 了解可用性
子代理继承： 当父代理使用 bypassPermissions、acceptEdits 或 auto 时，所有子代理继承该模式，并且不能按子代理覆盖。子代理可能有不同的系统提示和行为约束较少，比您的主代理，所以继承 bypassPermissions 授予它们完整的、自主的系统访问权限，无需任何批准提示。
​
设置权限模式
您可以在启动查询时设置权限模式一次，或在会话活跃时动态更改它。
在查询时
在流式传输期间
在创建查询时传递 permission_mode（Python）或 permissionMode（TypeScript）。此模式应用于整个会话，除非动态更改。
Python
TypeScript
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def main():
    async for message in query(
        prompt="Help me refactor this code",
        options=ClaudeAgentOptions(
            permission_mode="default",  # 在此处设置模式
        ),
    ):
        if hasattr(message, "result"):
            print(message.result)


asyncio.run(main())

​
模式详情
​
接受编辑模式（acceptEdits）
自动批准文件操作，以便 Claude 可以编辑代码而无需提示。其他工具（如不是文件系统操作的 Bash 命令）仍然需要正常权限。
自动批准的操作：
文件编辑（Edit、Write 工具）
文件系统命令：mkdir、touch、rm、rmdir、mv、cp、sed
两者都仅适用于工作目录或 additionalDirectories 内的路径。该范围外的路径和对受保护路径的写入仍然会提示。
使用时机： 您信任 Claude 的编辑并希望更快的迭代，例如在原型设计期间或在隔离目录中工作时。
​
不询问模式（dontAsk）
将任何权限提示转换为拒绝。由 allowed_tools、settings.json 允许规则或作为 hook 运行的工具正常运行。其他所有内容都被拒绝，无需调用 canUseTool。
使用时机： 您想要为无头代理提供固定的、明确的工具表面，并且更喜欢硬拒绝而不是默默依赖 canUseTool 不存在。
​
绕过权限模式（bypassPermissions）
自动批准所有工具使用而无需提示。Hooks 仍然执行，如果需要可以阻止操作。
谨慎使用。Claude 在此模式下具有完整的系统访问权限。仅在您信任所有可能操作的受控环境中使用。
allowed_tools 不约束此模式。每个工具都被批准，而不仅仅是您列出的工具。拒绝规则（disallowed_tools）、显式 ask 规则和 hooks 在模式检查之前被评估，仍然可以阻止工具。
​
规划模式（plan）
将 Claude 限制为只读工具。Claude 可以读取文件并运行只读 shell 命令来探索代码库，但不编辑您的源文件。Claude 可能使用 AskUserQuestion 在最终确定计划之前澄清需求。请参阅 处理批准和用户输入 以处理这些提示。
使用时机： 您想要 Claude 提议更改而不执行它们，例如在代码审查期间或当您需要在进行更改之前批准更改时。
​
相关资源
对于权限评估流程中的其他步骤：
处理批准和用户输入：交互式批准提示和澄清问题
Hooks 指南：在代理生命周期中的关键点运行自定义代码
权限规则：settings.json 中的声明式允许/拒绝规则

此页面对您有帮助吗？

是
否
SDK 中的 Plugins
使用 hooks 拦截和控制代理行为
⌘I

---

# 使用 hooks 拦截和控制代理行为

> 章节: 控制和可观测性 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/hooks

---

控制和可观测性
使用 hooks 拦截和控制代理行为

在代理执行的关键点使用 hooks 拦截和自定义代理行为

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

Hooks 是回调函数，用于响应代理事件（如工具被调用、会话启动或执行停止）运行您的代码。使用 hooks，您可以：
阻止危险操作在执行前进行，如破坏性 shell 命令或未授权的文件访问
记录和审计每个工具调用，用于合规性、调试或分析
转换输入和输出以清理数据、注入凭证或重定向文件路径
要求人工批准敏感操作，如数据库写入或 API 调用
跟踪会话生命周期以管理状态、清理资源或发送通知
本指南涵盖 hooks 的工作原理、如何配置它们，并提供常见模式的示例，如阻止工具、修改输入和转发通知。
​
Hooks 如何工作
1

事件触发

代理执行期间发生某事，SDK 触发事件：工具即将被调用（PreToolUse）、工具返回结果（PostToolUse）、子代理启动或停止、代理空闲或执行完成。请参阅完整事件列表。
2

SDK 收集已注册的 hooks

SDK 检查为该事件类型注册的 hooks。这包括您在 options.hooks 中传递的回调 hooks 和来自设置文件的 shell 命令 hooks，当相应的 settingSources 或 setting_sources 条目启用时（默认 query() 选项就是这样）。
3

匹配器过滤哪些 hooks 运行

如果 hook 有 matcher 模式（如 "Write|Edit"），SDK 会针对事件的目标（例如工具名称）测试它。没有匹配器的 hooks 对该类型的每个事件都运行。
4

回调函数执行

每个匹配的 hook 的回调函数接收有关正在发生的事情的输入：工具名称、其参数、会话 ID 和其他事件特定的详细信息。
5

您的回调返回决定

执行任何操作（日志记录、API 调用、验证）后，您的回调返回一个输出对象，告诉代理该做什么：允许操作、阻止它、修改输入或将上下文注入到对话中。
以下示例将这些步骤组合在一起。它注册一个 PreToolUse hook（步骤 1），带有 "Write|Edit" 匹配器（步骤 3），因此回调仅对文件写入工具触发。触发时，回调接收工具的输入（步骤 4），检查文件路径是否针对 .env 文件，并返回 permissionDecision: "deny" 以阻止操作（步骤 5）：
Python
TypeScript
import asyncio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeSDKClient,
    ClaudeAgentOptions,
    HookMatcher,
    ResultMessage,
)


# 定义一个接收工具调用详细信息的 hook 回调
async def protect_env_files(input_data, tool_use_id, context):
    # 从工具的输入参数中提取文件路径
    file_path = input_data["tool_input"].get("file_path", "")
    file_name = file_path.split("/")[-1]

    # 如果针对 .env 文件，阻止操作
    if file_name == ".env":
        return {
            "hookSpecificOutput": {
                "hookEventName": input_data["hook_event_name"],
                "permissionDecision": "deny",
                "permissionDecisionReason": "Cannot modify .env files",
            }
        }

    # 返回空对象以允许操作
    return {}


async def main():
    options = ClaudeAgentOptions(
        hooks={
            # 为 PreToolUse 事件注册 hook
            # 匹配器仅过滤 Write 和 Edit 工具调用
            "PreToolUse": [HookMatcher(matcher="Write|Edit", hooks=[protect_env_files])]
        }
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("Update the database configuration")
        async for message in client.receive_response():
            # 过滤助手和结果消息
            if isinstance(message, (AssistantMessage, ResultMessage)):
                print(message)


asyncio.run(main())

​
可用的 hooks
SDK 为代理执行的不同阶段提供 hooks。某些 hooks 在两个 SDK 中都可用，而其他 hooks 仅在 TypeScript 中可用。
Hook 事件	Python SDK	TypeScript SDK	触发条件	示例用例
PreToolUse	是	是	工具调用请求（可以阻止或修改）	阻止危险的 shell 命令
PostToolUse	是	是	工具执行结果	将所有文件更改记录到审计跟踪
PostToolUseFailure	是	是	工具执行失败	处理或记录工具错误
PostToolBatch	否	是	一整批工具调用解决，每批一次，在下一个模型调用之前	为整个批次注入约定
UserPromptSubmit	是	是	用户提示提交	将额外上下文注入到提示中
Stop	是	是	代理执行停止	在退出前保存会话状态
SubagentStart	是	是	子代理初始化	跟踪并行任务生成
SubagentStop	是	是	子代理完成	聚合来自并行任务的结果
PreCompact	是	是	对话压缩请求	在总结前存档完整记录
PermissionRequest	是	是	权限对话将显示	自定义权限处理
SessionStart	否	是	会话初始化	初始化日志记录和遥测
SessionEnd	否	是	会话终止	清理临时资源
Notification	是	是	代理状态消息	将代理状态更新发送到 Slack 或 PagerDuty
Setup	否	是	会话设置/维护	运行初始化任务
TeammateIdle	否	是	队友变为空闲	重新分配工作或通知
TaskCompleted	否	是	后台任务完成	聚合来自并行任务的结果
ConfigChange	否	是	配置文件更改	动态重新加载设置
WorktreeCreate	否	是	Git worktree 创建	跟踪隔离的工作区
WorktreeRemove	否	是	Git worktree 移除	清理工作区资源
​
配置 hooks
要配置 hook，请在您的代理选项的 hooks 字段中传递它（Python 中的 ClaudeAgentOptions，TypeScript 中的 options 对象）：
Python
TypeScript
options = ClaudeAgentOptions(
    hooks={"PreToolUse": [HookMatcher(matcher="Bash", hooks=[my_callback])]}
)

async with ClaudeSDKClient(options=options) as client:
    await client.query("Your prompt")
    async for message in client.receive_response():
        print(message)

hooks 选项是一个字典（Python）或对象（TypeScript），其中：
键是 hook 事件名称（例如 'PreToolUse'、'PostToolUse'、'Stop'）
值是匹配器数组，每个包含可选的过滤模式和您的回调函数
​
匹配器
使用匹配器来过滤您的回调何时触发。matcher 字段是一个正则表达式字符串，根据 hook 事件类型匹配不同的值。例如，基于工具的 hooks 匹配工具名称，而 Notification hooks 匹配通知类型。请参阅 Claude Code hooks 参考以获取每个事件类型的匹配器值的完整列表。
选项	类型	默认值	描述
matcher	string	undefined	针对事件的过滤字段匹配的正则表达式模式。对于工具 hooks，这是工具名称。内置工具包括 Bash、Read、Write、Edit、Glob、Grep、WebFetch、Agent 等（请参阅工具输入类型以获取完整列表）。MCP 工具使用模式 mcp__<server>__<action>。
hooks	HookCallback[]	-	必需。当模式匹配时执行的回调函数数组
timeout	number	60	超时时间（秒）
尽可能使用 matcher 模式来针对特定工具。带有 'Bash' 的匹配器仅对 Bash 命令运行，而省略模式会为事件的每次出现运行您的回调。请注意，对于基于工具的 hooks，匹配器仅按工具名称过滤，而不是按文件路径或其他参数。要按文件路径过滤，请在回调内检查 tool_input.file_path。
发现工具名称： 请参阅工具输入类型以获取内置工具名称的完整列表，或添加没有匹配器的 hook 来记录您的会话进行的所有工具调用。
MCP 工具命名： MCP 工具始终以 mcp__ 开头，后跟服务器名称和操作：mcp__<server>__<action>。例如，如果您配置一个名为 playwright 的服务器，其工具将被命名为 mcp__playwright__browser_screenshot、mcp__playwright__browser_click 等。服务器名称来自您在 mcpServers 配置中使用的键。
​
回调函数
​
输入
每个 hook 回调接收三个参数：
输入数据： 一个包含事件详细信息的类型化对象。每个 hook 类型都有自己的输入形状（例如，PreToolUseHookInput 包括 tool_name 和 tool_input，而 NotificationHookInput 包括 message）。请参阅 TypeScript 和 Python SDK 参考中的完整类型定义。
所有 hook 输入共享 session_id、cwd 和 hook_event_name。
当 hook 在子代理内触发时，agent_id 和 agent_type 被填充。在 TypeScript 中，这些在基础 hook 输入上，对所有 hook 类型都可用。在 Python 中，它们仅在 PreToolUse、PostToolUse 和 PostToolUseFailure 上。
工具使用 ID（str | None / string | undefined）：关联同一工具调用的 PreToolUse 和 PostToolUse 事件。
上下文： 在 TypeScript 中，包含用于取消的 signal 属性（AbortSignal）。在 Python 中，此参数保留供将来使用。
​
输出
您的回调返回一个具有两类字段的对象：
顶级字段在每个事件上的工作方式相同：systemMessage 向用户显示消息，continue（Python 中的 continue_）确定代理在此 hook 后是否继续运行。
hookSpecificOutput 控制当前操作。内部的字段取决于 hook 事件类型。对于 PreToolUse hooks，这是您设置 permissionDecision（"allow"、"deny"、"ask" 或 "defer"）、permissionDecisionReason 和 updatedInput 的地方。返回 "defer" 结束查询，以便您可以稍后恢复它。对于 PostToolUse hooks，您可以设置 additionalContext 以将信息附加到工具结果，或设置 updatedToolOutput 以在 Claude 看到之前完全替换工具的输出。
返回 {} 以允许操作而不进行更改。SDK 回调 hooks 使用与 Claude Code shell 命令 hooks 相同的 JSON 输出格式，其中记录了每个字段和事件特定的选项。对于 SDK 类型定义，请参阅 TypeScript 和 Python SDK 参考。
当多个 hooks 或权限规则适用时，deny 优先于 defer，defer 优先于 ask，ask 优先于 allow。如果任何 hook 返回 deny，操作将被阻止，无论其他 hooks 如何。
​
异步输出
默认情况下，代理在您的 hook 返回前等待。如果您的 hook 执行副作用（日志记录、发送 webhook）并且不需要影响代理的行为，您可以改为返回异步输出。这告诉代理立即继续，而不等待 hook 完成：
Python
TypeScript
async def async_hook(input_data, tool_use_id, context):
    # 启动后台任务，然后立即返回
    asyncio.create_task(send_to_logging_service(input_data))
    return {"async_": True, "asyncTimeout": 30000}

字段	类型	描述
async	true	表示异步模式。代理继续而不等待。在 Python 中，使用 async_ 以避免保留关键字。
asyncTimeout	number	后台操作的可选超时时间（毫秒）
异步输出无法阻止、修改或将上下文注入到操作中，因为代理已经继续。仅将它们用于日志记录、指标或通知等副作用。
​
示例
​
修改工具输入
此示例拦截 Write 工具调用并重写 file_path 参数以添加 /sandbox 前缀，将所有文件写入重定向到沙箱目录。回调返回带有修改路径的 updatedInput 和 permissionDecision: 'allow' 以自动批准重写的操作：
Python
TypeScript
async def redirect_to_sandbox(input_data, tool_use_id, context):
    if input_data["hook_event_name"] != "PreToolUse":
        return {}

    if input_data["tool_name"] == "Write":
        original_path = input_data["tool_input"].get("file_path", "")
        return {
            "hookSpecificOutput": {
                "hookEventName": input_data["hook_event_name"],
                "permissionDecision": "allow",
                "updatedInput": {
                    **input_data["tool_input"],
                    "file_path": f"/sandbox{original_path}",
                },
            }
        }
    return {}

使用 updatedInput 时，您还必须包括 permissionDecision: 'allow' 以自动批准修改的输入，或 permissionDecision: 'ask' 以将其显示给用户。使用 'defer' 时，updatedInput 会被忽略。始终返回新对象而不是改变原始 tool_input。
​
添加上下文并阻止工具
此示例阻止写入 /etc 目录的操作，并向模型和用户解释原因：
permissionDecision: 'deny' 停止工具调用。
permissionDecisionReason 告诉模型原因，以便它避免重试。
systemMessage 向用户显示发生了什么。
Python
TypeScript
async def block_etc_writes(input_data, tool_use_id, context):
    file_path = input_data["tool_input"].get("file_path", "")

    if file_path.startswith("/etc"):
        return {
            # 顶级字段：显示给用户的消息
            "systemMessage": "Remember: system directories like /etc are protected.",
            # hookSpecificOutput：阻止操作
            "hookSpecificOutput": {
                "hookEventName": input_data["hook_event_name"],
                "permissionDecision": "deny",
                "permissionDecisionReason": "Writing to /etc is not allowed",
            },
        }
    return {}

​
自动批准特定工具
默认情况下，代理可能在使用某些工具前提示权限。此示例通过返回 permissionDecision: 'allow' 自动批准只读文件系统工具（Read、Glob、Grep），让它们无需用户确认即可运行，同时让所有其他工具受到正常权限检查：
Python
TypeScript
async def auto_approve_read_only(input_data, tool_use_id, context):
    if input_data["hook_event_name"] != "PreToolUse":
        return {}

    read_only_tools = ["Read", "Glob", "Grep"]
    if input_data["tool_name"] in read_only_tools:
        return {
            "hookSpecificOutput": {
                "hookEventName": input_data["hook_event_name"],
                "permissionDecision": "allow",
                "permissionDecisionReason": "Read-only tool auto-approved",
            }
        }
    return {}

​
注册多个 hooks
当事件触发时，所有匹配的 hooks 并行运行。对于权限决策，最严格的结果获胜：单个 deny 会阻止工具调用，无论其他 hooks 返回什么。由于完成顺序是不确定的，请编写每个 hook 以独立行动，而不是依赖另一个 hook 已运行。
下面的示例为每个工具调用注册三个独立检查：
Python
TypeScript
options = ClaudeAgentOptions(
    hooks={
        "PreToolUse": [
            HookMatcher(hooks=[authorization_check]),
            HookMatcher(hooks=[input_validator]),
            HookMatcher(hooks=[audit_logger]),
        ]
    }
)

​
使用正则表达式匹配器过滤
使用正则表达式模式匹配多个工具。此示例注册三个具有不同范围的匹配器：第一个仅对文件修改工具触发 file_security_hook，第二个对任何 MCP 工具（名称以 mcp__ 开头的工具）触发 mcp_audit_hook，第三个对每个工具调用（无论名称如何）触发 global_logger：
Python
TypeScript
options = ClaudeAgentOptions(
    hooks={
        "PreToolUse": [
            # 匹配文件修改工具
            HookMatcher(matcher="Write|Edit|Delete", hooks=[file_security_hook]),
            # 匹配所有 MCP 工具
            HookMatcher(matcher="^mcp__", hooks=[mcp_audit_hook]),
            # 匹配所有内容（无匹配器）
            HookMatcher(hooks=[global_logger]),
        ]
    }
)

​
跟踪子代理活动
使用 SubagentStop hooks 监控子代理何时完成其工作。请参阅 TypeScript 和 Python SDK 参考中的完整输入类型。此示例在每次子代理完成时记录摘要：
Python
TypeScript
async def subagent_tracker(input_data, tool_use_id, context):
    # 子代理完成时记录子代理详细信息
    print(f"[SUBAGENT] Completed: {input_data['agent_id']}")
    print(f"  Transcript: {input_data['agent_transcript_path']}")
    print(f"  Tool use ID: {tool_use_id}")
    print(f"  Stop hook active: {input_data.get('stop_hook_active')}")
    return {}


options = ClaudeAgentOptions(
    hooks={"SubagentStop": [HookMatcher(hooks=[subagent_tracker])]}
)

​
从 hooks 发出 HTTP 请求
Hooks 可以执行异步操作，如 HTTP 请求。在您的 hook 内捕获错误，而不是让它们传播，因为未处理的异常可能会中断代理。
此示例在每个工具完成后发送 webhook，记录哪个工具运行以及何时运行。hook 捕获错误，以便失败的 webhook 不会中断代理：
Python
TypeScript
import asyncio
import json
import urllib.request
from datetime import datetime


def _send_webhook(tool_name):
    """同步辅助函数，将工具使用数据 POST 到外部 webhook。"""
    data = json.dumps(
        {
            "tool": tool_name,
            "timestamp": datetime.now().isoformat(),
        }
    ).encode()
    req = urllib.request.Request(
        "https://api.example.com/webhook",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req)


async def webhook_notifier(input_data, tool_use_id, context):
    # 仅在工具完成后触发（PostToolUse），而不是之前
    if input_data["hook_event_name"] != "PostToolUse":
        return {}

    try:
        # 在线程中运行阻塞 HTTP 调用以避免阻塞事件循环
        await asyncio.to_thread(_send_webhook, input_data["tool_name"])
    except Exception as e:
        # 记录错误但不抛出。失败的 webhook 不应停止代理
        print(f"Webhook request failed: {e}")

    return {}

​
将通知转发到 Slack
使用 Notification hooks 从代理接收系统通知并将其转发到外部服务。通知针对特定事件类型触发：permission_prompt（Claude 需要权限）、idle_prompt（Claude 等待输入）、auth_success（身份验证完成）、elicitation_dialog（Claude 提示用户）、elicitation_response（用户回答了引导）和 elicitation_complete（引导已关闭）。每个通知包括一个带有人类可读描述的 message 字段，以及可选的 title。
此示例将每个通知转发到 Slack 频道。它需要一个 Slack 传入 webhook URL，您可以通过将应用添加到您的 Slack 工作区并启用传入 webhooks 来创建：
Python
TypeScript
import asyncio
import json
import urllib.request

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, HookMatcher


def _send_slack_notification(message):
    """同步辅助函数，通过传入 webhook 向 Slack 发送消息。"""
    data = json.dumps({"text": f"Agent status: {message}"}).encode()
    req = urllib.request.Request(
        "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req)


async def notification_handler(input_data, tool_use_id, context):
    try:
        # 在线程中运行阻塞 HTTP 调用以避免阻塞事件循环
        await asyncio.to_thread(_send_slack_notification, input_data.get("message", ""))
    except Exception as e:
        print(f"Failed to send notification: {e}")

    # 返回空对象。通知 hooks 不修改代理行为
    return {}


async def main():
    options = ClaudeAgentOptions(
        hooks={
            # 为通知事件注册 hook（不需要匹配器）
            "Notification": [HookMatcher(hooks=[notification_handler])],
        },
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("Analyze this codebase")
        async for message in client.receive_response():
            print(message)


asyncio.run(main())

​
修复常见问题
​
Hook 未触发
验证 hook 事件名称正确且区分大小写（PreToolUse，而不是 preToolUse）
检查您的匹配器模式是否与工具名称完全匹配
确保 hook 在 options.hooks 中的正确事件类型下
对于非工具 hooks，如 Stop 和 SubagentStop，匹配器匹配不同的字段（请参阅匹配器模式）
当代理达到 max_turns 限制时，hooks 可能不会触发，因为会话在 hooks 可以执行前结束
​
匹配器未按预期过滤
匹配器仅匹配工具名称，而不是文件路径或其他参数。要按文件路径过滤，请在您的 hook 内检查 tool_input.file_path：
const myHook: HookCallback = async (input, toolUseID, { signal }) => {
  const preInput = input as PreToolUseHookInput;
  const toolInput = preInput.tool_input as Record<string, unknown>;
  const filePath = toolInput?.file_path as string;
  if (!filePath?.endsWith(".md")) return {}; // 跳过非 markdown 文件
  // 处理 markdown 文件...
  return {};
};

​
Hook 超时
增加 HookMatcher 配置中的 timeout 值
在 TypeScript 中使用第三个回调参数中的 AbortSignal 来优雅地处理取消
​
工具意外被阻止
检查所有 PreToolUse hooks 是否返回 permissionDecision: 'deny'
向您的 hooks 添加日志记录以查看它们返回的 permissionDecisionReason
验证匹配器模式不会太宽泛（空匹配器匹配所有工具）
​
修改的输入未应用
确保 updatedInput 在 hookSpecificOutput 内，而不是在顶级：
return {
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "allow",
    updatedInput: { command: "new command" }
  }
};

您还必须返回 permissionDecision: 'allow' 或 'ask' 以使输入修改生效
在 hookSpecificOutput 中包括 hookEventName 以识别输出针对的 hook 类型
​
Python 中不可用会话 hooks
SessionStart 和 SessionEnd 可以在 TypeScript 中注册为 SDK 回调 hooks，但在 Python SDK 中不可用（HookEvent 省略了它们）。在 Python 中，它们仅作为shell 命令 hooks 在设置文件中定义（例如 .claude/settings.json）。要从您的 SDK 应用程序加载 shell 命令 hooks，请使用 setting_sources 或 settingSources 包括适当的设置源：
Python
TypeScript
options = ClaudeAgentOptions(
    setting_sources=["project"],  # 加载 .claude/settings.json 包括 hooks
)

要改为运行初始化逻辑作为 Python SDK 回调，请使用 client.receive_response() 的第一条消息作为您的触发器。
​
子代理权限提示倍增
生成多个子代理时，每个子代理可能会单独请求权限。子代理不会自动继承父代理权限。要避免重复提示，请使用 PreToolUse hooks 自动批准特定工具，或配置适用于子代理会话的权限规则。
​
子代理的递归 hook 循环
生成子代理的 UserPromptSubmit hook 如果这些子代理触发相同的 hook，可能会创建无限循环。要防止这种情况：
在生成子代理前检查 hook 输入中的子代理指示符
使用共享变量或会话状态来跟踪您是否已在子代理内
将 hooks 范围限制为仅对顶级代理会话运行
​
systemMessage 未出现在输出中
systemMessage 字段向用户显示消息，而不是模型。默认情况下，SDK 不会在消息流中显示 hook 输出，因此除非您设置 includeHookEvents（Python 中为 include_hook_events），否则消息可能不会出现。要改为将上下文传递给模型，请返回 additionalContext。
如果您需要可靠地将 hook 决定呈现给您的应用程序，请单独记录它们或使用专用输出通道。
​
相关资源
Claude Code hooks 参考：完整的 JSON 输入/输出架构、事件文档和匹配器模式
Claude Code hooks 指南：shell 命令 hook 示例和演练
TypeScript SDK 参考：hook 类型、输入/输出定义和配置选项
Python SDK 参考：hook 类型、输入/输出定义和配置选项
权限：控制您的代理可以做什么
自定义工具：构建工具以扩展代理功能

此页面对您有帮助吗？

是
否
配置权限
File checkpointing
⌘I

---

# File checkpointing

> 章节: 控制和可观测性 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/file-checkpointing

---

Securely deploying AI agents

> 注意: 此页面暂无中文翻译，以下为英文原版内容。

Security is critical when deploying AI agents that can execute code, access files, and interact with external systems. This guide covers best practices for securely deploying agents built with the Claude Agent SDK.

## Principle of Least Privilege

Always run agents with the minimum permissions needed:

- **File system access**: Restrict the working directory to only what the agent needs
- **Network access**: Use firewalls or network policies to limit outbound connections
- **Tool restrictions**: Only enable the specific tools your agent requires

```python
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Grep", "Glob"],  # Read-only tools
    permission_mode="default",
    working_dir="/path/to/specific/project",  # Restrict scope
)
```

## Sandboxing

### Containerization

Run agents inside Docker containers or Kubernetes pods to isolate them from the host system:

```dockerfile
FROM node:20-slim
RUN npm install @anthropic-ai/claude-agent-sdk
COPY agent.js /app/
WORKDIR /app
USER node  # Non-root user
CMD ["node", "agent.js"]
```

### Filesystem Isolation

- Mount only necessary directories as read-only when possible
- Use tmpfs for temporary files that shouldn't persist
- Never mount the host filesystem root (/)

```bash
docker run   -v $(pwd)/project:/app/project:ro \  # Read-only project files
  -v $(pwd)/output:/app/output \        # Write-only output directory
  --tmpfs /tmp   my-agent
```

## API Key Management

Never hardcode API keys in your agent code:

```python
# Good: Use environment variables
import os
api_key = os.environ["ANTHROPIC_API_KEY"]

# Good: Use secret management services
# AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault, etc.
```

## Network Security

- Use HTTPS/TLS for all external connections
- Configure firewalls to allow only necessary outbound ports (443, 22 if git needed)
- Consider using a proxy for web access to inspect and filter traffic

## Input Validation

Validate and sanitize any user-provided input before passing it to the agent:

```python
def sanitize_user_input(user_message: str) -> str:
    # Remove control characters
    cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', user_message)
    # Truncate to reasonable length
    return cleaned[:10000]
```

## Audit Logging

Enable logging to track agent actions:

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('/var/log/agent/audit.log')]
)
```

## Rate Limiting

Implement rate limiting to prevent abuse:

```python
from functools import wraps
import time

def rate_limit(max_per_minute: int):
    calls = []
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            calls[:] = [c for c in calls if c > now - 60]
            if len(calls) >= max_per_minute:
                raise Exception("Rate limit exceeded")
            calls.append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

## Regular Updates

Keep the SDK and its dependencies up to date:

```bash
npm update @anthropic-ai/claude-agent-sdk  # TypeScript
pip install --upgrade claude-agent-sdk      # Python
```

Review the SDK changelog regularly for security-related updates and patches.

---

# 跟踪成本和使用情况

> 章节: 控制和可观测性 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/cost-tracking

---

控制和可观测性
跟踪成本和使用情况

了解如何跟踪令牌使用情况、估计成本，以及使用 Claude Agent SDK 配置提示缓存。

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

Claude Agent SDK 为与 Claude 的每次交互提供详细的令牌使用信息。本指南说明如何正确跟踪使用情况和理解成本报告，特别是在处理并行工具使用和多步骤对话时。
有关完整的 API 文档，请参阅 TypeScript SDK 参考 和 Python SDK 参考。
total_cost_usd 和 costUSD 字段是客户端估计值，不是权威的计费数据。SDK 从构建时捆绑的价格表在本地计算它们，因此当以下情况发生时，它们可能与您实际被计费的金额不同：
定价发生变化
已安装的 SDK 版本无法识别某个模型
应用了客户端无法建模的计费规则
使用这些字段进行开发洞察和大致预算编制。对于权威计费，请使用 使用情况和成本 API 或 Claude 控制台 中的使用情况页面。不要从这些字段向最终用户计费或触发财务决策。
​
理解令牌使用情况
TypeScript 和 Python SDK 使用不同的字段名称公开相同的使用数据：
TypeScript 在每个助手消息上提供每步令牌细分（message.message.id、message.message.usage），通过结果消息上的 modelUsage 提供每个模型的成本，以及结果消息上的累积总计。
Python 在每个助手消息上提供每步令牌细分（message.usage、message.message_id），通过结果消息上的 model_usage 提供每个模型的成本，以及结果消息上的累积总计（total_cost_usd 和 usage 字典）。
两个 SDK 使用相同的底层成本模型并公开相同的粒度。区别在于字段命名和每步使用情况的嵌套位置。
成本跟踪取决于理解 SDK 如何确定使用数据的范围：
query() 调用： SDK 的 query() 函数的一次调用。单个调用可能涉及多个步骤（Claude 响应、使用工具、获取结果、再次响应）。每个调用在末尾产生一条 result 消息。
步骤： query() 调用中的单个请求/响应周期。每个步骤产生带有令牌使用情况的助手消息。
会话： 由会话 ID 链接的一系列 query() 调用（使用 resume 选项）。会话中的每个 query() 调用独立报告其自己的成本。
下图显示了单个 query() 调用的消息流，在每个步骤报告令牌使用情况，末尾显示累积估计：
1

每个步骤产生助手消息

当 Claude 响应时，它发送一条或多条助手消息。在 TypeScript 中，每条助手消息包含一个嵌套的 BetaMessage（通过 message.message 访问），具有 id 和一个 usage 对象，其中包含令牌计数（input_tokens、output_tokens）。在 Python 中，AssistantMessage 数据类通过 message.usage 和 message.message_id 直接公开相同的数据。当 Claude 在一个回合中使用多个工具时，该回合中的所有消息共享相同的 ID，因此按 ID 去重以避免重复计数。
2

结果消息提供累积估计

当 query() 调用完成时，SDK 发出一条结果消息，其中包含 total_cost_usd 和累积 usage。这在 TypeScript（SDKResultMessage）和 Python（ResultMessage）中都可用。如果您进行多个 query() 调用（例如，在多轮会话中），每个结果仅反映该单个调用的成本。如果您只需要估计的总计，可以忽略每步使用情况并读取此单个值。
​
获取查询的总成本
结果消息（TypeScript、Python）标记 query() 调用的代理循环的结束。它包括 total_cost_usd，即该调用中所有步骤的累积估计成本。这适用于成功和错误结果。如果您使用会话进行多个 query() 调用，每个结果仅反映该单个调用的成本。
以下示例遍历 query() 调用的消息流，并在 result 消息到达时打印总成本：
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({ prompt: "Summarize this project" })) {
  if (message.type === "result") {
    console.log(`Total cost: $${message.total_cost_usd}`);
  }
}

​
跟踪每步和每个模型的使用情况
本部分中的示例使用 TypeScript 字段名称。在 Python 中，等效字段是 AssistantMessage.usage 和 AssistantMessage.message_id 用于每步使用情况，以及 ResultMessage.model_usage 用于每个模型的细分。
​
跟踪每步使用情况
每条助手消息包含一个嵌套的 BetaMessage（通过 message.message 访问），具有 id 和 usage 对象，其中包含令牌计数。当 Claude 并行使用工具时，多条消息共享相同的 id 和相同的使用数据。跟踪您已经计数的 ID，并跳过重复项以避免膨胀的总计。
并行工具调用产生多条助手消息，其嵌套的 BetaMessage 共享相同的 id 和相同的使用情况。始终按 ID 去重以获得准确的每步令牌计数。
以下示例累积所有步骤中的输入和输出令牌，仅计数每个唯一消息 ID 一次：
import { query } from "@anthropic-ai/claude-agent-sdk";

const seenIds = new Set<string>();
let totalInputTokens = 0;
let totalOutputTokens = 0;

for await (const message of query({ prompt: "Summarize this project" })) {
  if (message.type === "assistant") {
    const msgId = message.message.id;

    // Parallel tool calls share the same ID, only count once
    if (!seenIds.has(msgId)) {
      seenIds.add(msgId);
      totalInputTokens += message.message.usage.input_tokens;
      totalOutputTokens += message.message.usage.output_tokens;
    }
  }
}

console.log(`Steps: ${seenIds.size}`);
console.log(`Input tokens: ${totalInputTokens}`);
console.log(`Output tokens: ${totalOutputTokens}`);

​
按模型细分使用情况
结果消息包括 modelUsage，这是一个模型名称到每个模型令牌计数和成本的映射。当您运行多个模型（例如，为子代理使用 Haiku，为主代理使用 Opus）并想查看令牌的去向时，这很有用。
以下示例运行查询并打印所使用的每个模型的成本和令牌细分：
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({ prompt: "Summarize this project" })) {
  if (message.type !== "result") continue;

  for (const [modelName, usage] of Object.entries(message.modelUsage)) {
    console.log(`${modelName}: $${usage.costUSD.toFixed(4)}`);
    console.log(`  Input tokens: ${usage.inputTokens}`);
    console.log(`  Output tokens: ${usage.outputTokens}`);
    console.log(`  Cache read: ${usage.cacheReadInputTokens}`);
    console.log(`  Cache creation: ${usage.cacheCreationInputTokens}`);
  }
}

​
累积多个调用的成本
每个 query() 调用返回其自己的 total_cost_usd。SDK 不提供会话级别的总计，因此如果您的应用程序进行多个 query() 调用（例如，在多轮会话中或跨不同用户），请自己累积总计。
以下示例按顺序运行两个 query() 调用，将每个调用的 total_cost_usd 添加到运行总计，并打印每个调用和合并的成本：
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

// Track cumulative cost across multiple query() calls
let totalSpend = 0;

const prompts = [
  "Read the files in src/ and summarize the architecture",
  "List all exported functions in src/auth.ts"
];

for (const prompt of prompts) {
  for await (const message of query({ prompt })) {
    if (message.type === "result") {
      totalSpend += message.total_cost_usd;
      console.log(`This call: $${message.total_cost_usd}`);
    }
  }
}

console.log(`Total spend: $${totalSpend.toFixed(4)}`);

​
处理错误、缓存和令牌差异
为了准确的成本跟踪，需要考虑失败的对话、缓存令牌定价和偶发的报告不一致。
​
解决输出令牌差异
在极少数情况下，您可能会观察到具有相同 ID 的消息的 output_tokens 值不同。当这种情况发生时：
使用最高值： 一组中的最终消息通常包含准确的总计。
优先使用结果消息： 结果消息中的 total_cost_usd 反映 SDK 在所有步骤中的累积估计，因此比自己求和每步值更可靠。它仍然是一个估计值，可能与您的实际账单不同。
报告不一致： 在 Claude Code GitHub 存储库 提交问题。
​
跟踪失败对话的成本
成功和错误结果消息都包括 usage 和 total_cost_usd。如果对话在中途失败，您仍然消耗了到失败点为止的令牌。无论其 subtype 如何，始终从结果消息读取成本数据。
​
跟踪缓存令牌
Agent SDK 自动使用 提示缓存 来减少重复内容的成本。您不需要自己配置缓存。使用对象包括两个额外的字段用于缓存跟踪：
cache_creation_input_tokens：用于创建新缓存条目的令牌（按比标准输入令牌更高的速率计费）。
cache_read_input_tokens：从现有缓存条目读取的令牌（按降低的速率计费）。
将这些与 input_tokens 分开跟踪以了解缓存节省。在 TypeScript 中，这些字段在 Usage 对象上进行类型化。在 Python 中，它们作为 ResultMessage.usage 字典中的键出现（例如，message.usage.get("cache_read_input_tokens", 0)）。
​
将提示缓存 TTL 扩展到一小时
当您使用 API 密钥进行身份验证或在 Amazon Bedrock、Google Cloud Vertex AI 或 Microsoft Foundry 上运行时，SDK 写入的缓存条目默认使用 5 分钟 TTL。如果您的工作负载针对相同的系统提示和上下文运行许多短会话，且会话之间的间隔超过 5 分钟，缓存会在会话之间过期，每个新会话都会支付完整的输入价格。
要请求缓存写入的 1 小时 TTL，请设置 ENABLE_PROMPT_CACHING_1H 环境变量。您可以在 shell 或容器环境中导出它，或通过 options.env 传递它。
以下示例为在 Bedrock 上运行的代理启用 1 小时 TTL：
Python
TypeScript
options = ClaudeAgentOptions(
    env={
        "CLAUDE_CODE_USE_BEDROCK": "1",
        "ENABLE_PROMPT_CACHING_1H": "1",
    },
)

具有 1 小时 TTL 的缓存写入按比 5 分钟写入更高的速率计费，因此启用此功能会用更高的写入成本换取更多的缓存读取。有关详细信息，请参阅 提示缓存定价。Claude 订阅用户已自动获得 1 小时 TTL，不需要设置此变量。
​
相关文档
TypeScript SDK 参考 - 完整的 API 文档
SDK 概述 - SDK 入门
SDK 权限 - 管理工具权限

此页面对您有帮助吗？

是
否
File checkpointing
Observability
⌘I

---

# Observability

> 章节: 控制和可观测性 | 来源: https://code.claude.com/docs/en/agent-sdk/observability
> 注意: 此页面暂无中文翻译，以下为英文原版内容。

---

The Claude Agent SDK supports OpenTelemetry tracing for monitoring agent performance, debugging issues, and understanding agent behavior in production.

## Enabling OpenTelemetry

Set the environment variable to enable tracing: `CLAUDE_CODE_ENABLE_OTEL=1`

Or configure it programmatically:

The SDK emits spans for each agent turn (prompt to response), tool calls (Bash, Read, Write, Edit, etc.), sub-agent invocations, MCP tool calls, and hook executions. Each span includes attributes like model name, token usage, tool name, and duration.

## Exporting Traces

Traces can be exported to any OpenTelemetry-compatible backend including Jaeger, Honeycomb, Datadog, and Grafana Cloud. Configure the OTLP endpoint and headers as needed for your observability platform.

## Example: Local Debugging with Jaeger

```bash
docker run -d --name jaeger -p 16686:16686 -p 4317:4317 jaegertracing/all-in-one:latest
CLAUDE_CODE_ENABLE_OTEL=1 OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 python my_agent.py
# View traces at http://localhost:16686
```

Traces help you understand where your agent spends time, identify slow tool calls, and debug complex multi-turn interactions.

---

# 待办事项列表

> 章节: 控制和可观测性 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/todo-tracking

---

控制和可观测性
待办事项列表

使用 Claude Agent SDK 跟踪和显示待办事项，实现有组织的任务管理

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

待办事项跟踪提供了一种结构化的方式来管理任务并向用户显示进度。Claude Agent SDK 包含内置的待办事项功能，可帮助组织复杂的工作流程并让用户了解任务进度。
截至 TypeScript Agent SDK 0.3.142 和 Claude Code v2.1.142，会话使用结构化的 Task 工具 TaskCreate、TaskUpdate、TaskGet 和 TaskList，而不是 TodoWrite。请参阅迁移到 Task 工具了解监控代码如何变化。本页面上的示例设置 CLAUDE_CODE_ENABLE_TASKS=0 以继续为尚未迁移的会话显示 TodoWrite。
​
待办事项生命周期
待办事项遵循可预测的生命周期：
创建为 pending 状态，当任务被识别时
激活为 in_progress 状态，当工作开始时
完成当任务成功完成时
移除当组中的所有任务都完成时
​
何时使用待办事项
SDK 会自动为以下情况创建待办事项：
复杂的多步骤任务需要 3 个或更多不同的操作
用户提供的任务列表当提到多个项目时
非平凡的操作受益于进度跟踪
明确的请求当用户要求组织待办事项时
​
示例
​
监控待办事项变化
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Optimize my React app performance and track progress with todos",
  // Re-enable TodoWrite, which this example monitors. Without it, the SDK uses
  // Task tools instead and these tool_use blocks never appear.
  options: { maxTurns: 15, env: { ...process.env, CLAUDE_CODE_ENABLE_TASKS: "0" } }
})) {
  // Todo updates are reflected in the message stream
  if (message.type === "assistant") {
    for (const block of message.message.content) {
      if (block.type === "tool_use" && block.name === "TodoWrite") {
        const todos = block.input.todos;

        console.log("Todo Status Update:");
        todos.forEach((todo, index) => {
          const status =
            todo.status === "completed" ? "✅" : todo.status === "in_progress" ? "🔧" : "❌";
          console.log(`${index + 1}. ${status} ${todo.content}`);
        });
      }
    }
  }
}

​
实时进度显示
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

class TodoTracker {
  private todos: any[] = [];

  displayProgress() {
    if (this.todos.length === 0) return;

    const completed = this.todos.filter((t) => t.status === "completed").length;
    const inProgress = this.todos.filter((t) => t.status === "in_progress").length;
    const total = this.todos.length;

    console.log(`\nProgress: ${completed}/${total} completed`);
    console.log(`Currently working on: ${inProgress} task(s)\n`);

    this.todos.forEach((todo, index) => {
      const icon =
        todo.status === "completed" ? "✅" : todo.status === "in_progress" ? "🔧" : "❌";
      const text = todo.status === "in_progress" ? todo.activeForm : todo.content;
      console.log(`${index + 1}. ${icon} ${text}`);
    });
  }

  async trackQuery(prompt: string) {
    for await (const message of query({
      prompt,
      // Re-enable TodoWrite, which this tracker watches for.
      options: { maxTurns: 20, env: { ...process.env, CLAUDE_CODE_ENABLE_TASKS: "0" } }
    })) {
      if (message.type === "assistant") {
        for (const block of message.message.content) {
          if (block.type === "tool_use" && block.name === "TodoWrite") {
            this.todos = block.input.todos;
            this.displayProgress();
          }
        }
      }
    }
  }
}

// Usage
const tracker = new TodoTracker();
await tracker.trackQuery("Build a complete authentication system with todos");

​
迁移到 Task 工具
Task 工具将单个 TodoWrite 调用分为 TaskCreate（用于每个新项目）和 TaskUpdate（用于每个状态更改），TaskList 和 TaskGet 可供模型读取当前列表。您的监控代码仍然检查助手流中的 tool_use 块，但维护一个由任务 ID 键入的映射，而不是在每次调用时替换整个列表。Task 工具是 TypeScript Agent SDK 0.3.142 和 Claude Code v2.1.142 的默认工具，因此不需要更改 options.env。
使用 TodoWrite	使用 Task 工具
一个工具调用重写完整的 todos 数组	TaskCreate 添加一个项目，TaskUpdate 按 taskId 修补一个项目
匹配 block.name === "TodoWrite"	匹配 block.name === "TaskCreate" 或 "TaskUpdate"
项目形状：{ content, status, activeForm }	TaskCreate 输入：{ subject, description, activeForm?, metadata? }。TaskUpdate 输入：{ taskId, status?, subject?, description?, activeForm?, addBlocks?, addBlockedBy?, owner?, metadata? }。status 是 "pending"、"in_progress" 或 "completed"；设置 status: "deleted" 以删除
直接渲染 block.input.todos	跨调用累积项目，或从 TaskList 工具结果读取快照
分配的任务 ID 不在 TaskCreate 输入中。它在匹配的 tool_result 中返回为 { task: { id, subject } }，因此从结果块捕获它以键入您的映射。以下示例显示了对监控待办事项变化循环的最小更改。要渲染完整列表，请在流中监视 TaskList 工具结果或将 TaskCreate 结果和 TaskUpdate 输入累积到映射中：
TypeScript
Python
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Optimize my React app performance",
})) {
  if (message.type !== "assistant") continue;
  for (const block of message.message.content) {
    if (block.type !== "tool_use") continue;
    if (block.name === "TaskCreate") {
      const input = block.input as { subject: string };
      console.log(`+ ${input.subject}`);
    } else if (block.name === "TaskUpdate") {
      const input = block.input as { taskId: string; status?: string };
      if (input.status) console.log(`  ${input.taskId} -> ${input.status}`);
    }
  }
}

​
相关文档
TypeScript SDK 参考
Python SDK 参考
流式模式与单一模式
自定义工具

此页面对您有帮助吗？

是
否
Observability
托管 Agent SDK
⌘I

---

# 托管 Agent SDK

> 章节: 部署 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/hosting

---

部署
托管 Agent SDK

在生产环境中部署和托管 Claude Agent SDK

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

Claude Agent SDK 与传统的无状态 LLM API 不同，它维护对话状态并在持久环境中执行命令。本指南涵盖了在生产环境中部署基于 SDK 的代理的架构、托管考虑因素和最佳实践。
有关超越基本 sandboxing 的安全加固（包括网络控制、凭证管理和隔离选项），请参阅 Secure Deployment。
​
托管要求
​
基于容器的 Sandboxing
为了安全性和隔离，SDK 应在沙箱容器环境中运行。这提供了进程隔离、资源限制、网络控制和临时文件系统。
SDK 还支持 programmatic sandbox configuration 用于命令执行。
​
系统要求
每个 SDK 实例需要：
运行时依赖
Python 3.10+ 用于 Python SDK，或 Node.js 18+ 用于 TypeScript SDK
两个 SDK 包都为主机平台捆绑了本地 Claude Code 二进制文件，因此不需要为生成的 CLI 单独安装 Claude Code 或 Node.js
资源分配
推荐：1GiB RAM、5GiB 磁盘和 1 个 CPU（根据您的任务需要调整）
网络访问
出站 HTTPS 到 api.anthropic.com
可选：访问 MCP 服务器或外部工具
​
理解 SDK 架构
与无状态 API 调用不同，Claude Agent SDK 作为 长运行进程 运行，该进程：
在持久 shell 环境中执行命令
在工作目录中管理文件操作
处理工具执行，包含来自先前交互的上下文
​
Sandbox 提供商选项
几个提供商专门提供用于 AI 代码执行的安全容器环境：
Modal Sandbox - demo implementation
Cloudflare Sandboxes
Daytona
E2B
Fly Machines
Vercel Sandbox
有关自托管选项（Docker、gVisor、Firecracker）和详细的隔离配置，请参阅 Isolation Technologies。
​
生产部署模式
​
模式 1：临时会话
为每个用户任务创建一个新容器，然后在完成时销毁它。
最适合一次性任务，用户可能在任务完成时仍与 AI 交互，但一旦完成，容器就会被销毁。
示例：
Bug 调查和修复：使用相关上下文调试和解决特定问题
发票处理：从收据/发票中提取和结构化数据用于会计系统
翻译任务：在语言之间翻译文档或内容批次
图像/视频处理：对媒体文件应用转换、优化或提取元数据
​
模式 2：长运行会话
为长运行任务维护持久容器实例。通常在容器内根据需求运行 多个 Claude Agent 进程。
最适合主动代理，这些代理在没有用户输入的情况下采取行动，提供内容的代理或处理大量消息的代理。
示例：
电子邮件代理：监控传入电子邮件并根据内容自主分类、响应或采取行动
网站构建器：为每个用户托管自定义网站，具有通过容器端口提供的实时编辑功能
高频聊天机器人：处理来自 Slack 等平台的连续消息流，其中需要快速响应时间
​
模式 3：混合会话
临时容器，使用历史和状态进行补充，可能来自数据库或 SDK 的会话恢复功能。
最适合与用户进行间歇性交互的容器，启动工作并在工作完成时关闭，但可以继续。
示例：
个人项目管理器：帮助管理进行中的项目，进行间歇性检查，维护任务、决策和进度的上下文
深度研究：进行多小时的研究任务，保存发现并在用户返回时恢复调查
客户支持代理：处理跨越多个交互的支持票证，加载票证历史和客户上下文
​
模式 4：单个容器
在一个全局容器中运行多个 Claude Agent SDK 进程。
最适合必须紧密协作的代理。这可能是最不受欢迎的模式，因为您必须防止代理相互覆盖。
示例：
模拟：在模拟中相互交互的代理，例如视频游戏。
​
常见问题
​
我如何与我的 sandboxes 通信？
在容器中托管时，暴露端口以与您的 SDK 实例通信。您的应用程序可以为外部客户端暴露 HTTP/WebSocket 端点，而 SDK 在容器内部运行。
​
托管容器的成本是多少？
提供代理的主要成本是令牌；容器根据您配置的内容而异，但最低成本大约是每小时运行 5 美分。
​
我应该何时关闭空闲容器与保持它们温暖？
这可能取决于提供商，不同的 sandbox 提供商将让您为空闲超时设置不同的条件，之后 sandbox 可能会关闭。 您需要根据您认为用户响应可能的频率来调整此超时。
​
我应该多久更新一次 Claude Code CLI？
Claude Code CLI 使用 semver 进行版本控制，因此任何破坏性更改都将被版本化。
​
我如何监控容器健康和代理性能？
由于容器只是服务器，您用于后端的相同日志记录基础设施将适用于容器。
​
代理会话在超时前可以运行多长时间？
代理会话不会超时，但考虑设置 ‘maxTurns’ 属性以防止 Claude 陷入循环。
​
后续步骤
Secure Deployment - 网络控制、凭证管理和隔离加固
TypeScript SDK - Sandbox Settings - 以编程方式配置 sandbox
Sessions Guide - 了解会话管理
Permissions - 配置工具权限
Cost Tracking - 监控 API 使用情况
MCP Integration - 使用自定义工具扩展

此页面对您有帮助吗？

是
否
待办事项列表
Secure deployment
⌘I

---

# Secure deployment

> 章节: 部署 | 来源: https://code.claude.com/docs/en/agent-sdk/secure-deployment
> 注意: 此页面暂无中文翻译，以下为英文原版内容。

---

Security is critical when deploying AI agents that can execute code, access files, and interact with external systems. This guide covers best practices for securely deploying agents built with the Claude Agent SDK.

## Principle of Least Privilege

Always run agents with the minimum permissions needed. Restrict file system access to only what the agent needs, use firewalls or network policies to limit outbound connections, and only enable the specific tools your agent requires.

## Sandboxing

Run agents inside Docker containers or Kubernetes pods to isolate them from the host system. Use non-root users, mount only necessary directories (read-only when possible), use tmpfs for temporary files, and never mount the host filesystem root.

## API Key Management

Never hardcode API keys in your agent code. Use environment variables, secret management services (AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault), or your platform's built-in secrets mechanism.

## Network Security

Use HTTPS/TLS for all external connections. Configure firewalls to allow only necessary outbound ports. Consider using a proxy for web access to inspect and filter traffic.

## Input Validation

Validate and sanitize any user-provided input before passing it to the agent. Remove control characters and truncate to reasonable lengths.

## Audit Logging

Enable logging to track agent actions for security auditing and incident response.

## Rate Limiting

Implement rate limiting to prevent abuse of your agent endpoints.

## Regular Updates

Keep the SDK and its dependencies up to date. Review the SDK changelog regularly for security-related updates and patches.

---


# TypeScript SDK

> 章节: SDK 参考 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/typescript

---

SDK 参考
Agent SDK 参考 - TypeScript

TypeScript Agent SDK 的完整 API 参考，包括所有函数、类型和接口。

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

​
安装
npm install @anthropic-ai/claude-agent-sdk

SDK 为您的平台捆绑了一个本地 Claude Code 二进制文件，作为可选依赖项，例如 @anthropic-ai/claude-agent-sdk-darwin-arm64。您无需单独安装 Claude Code。如果您的包管理器跳过可选依赖项，SDK 会抛出 Native CLI binary for <platform> not found；改为将 pathToClaudeCodeExecutable 设置为单独安装的 claude 二进制文件。
​
函数
​
query()
与 Claude Code 交互的主要函数。创建一个异步生成器，在消息到达时流式传输消息。
function query({
  prompt,
  options
}: {
  prompt: string | AsyncIterable<SDKUserMessage>;
  options?: Options;
}): Query;

​
参数
参数	类型	描述
prompt	string | AsyncIterable<SDKUserMessage>	输入提示，可以是字符串或异步可迭代对象（用于流式模式）
options	Options	可选配置对象（请参阅下面的 Options 类型）
​
返回值
返回一个 Query 对象，该对象扩展 AsyncGenerator<SDKMessage, void>，并具有其他方法。
​
startup()
通过生成 CLI 子进程并在提示可用之前完成初始化握手来预热 CLI 子进程。返回的 WarmQuery 句柄稍后接受提示并将其写入已准备好的进程，因此第一个 query() 调用解析时无需支付子进程生成和初始化成本。
function startup(params?: {
  options?: Options;
  initializeTimeoutMs?: number;
}): Promise<WarmQuery>;

​
参数
参数	类型	描述
options	Options	可选配置对象。与 query() 的 options 参数相同
initializeTimeoutMs	number	等待子进程初始化的最长时间（毫秒）。默认为 60000。如果初始化未在规定时间内完成，promise 将以超时错误拒绝
​
返回值
返回一个 Promise<WarmQuery>，在子进程生成并完成其初始化握手后解析。
​
示例
早期调用 startup()，例如在应用程序启动时，然后在提示准备好后在返回的句柄上调用 .query()。这会将子进程生成和初始化移出关键路径。
import { startup } from "@anthropic-ai/claude-agent-sdk";

// 提前支付启动成本
const warm = await startup({ options: { maxTurns: 3 } });

// 稍后，当提示准备好时，这是立即的
for await (const message of warm.query("What files are here?")) {
  console.log(message);
}

​
tool()
为与 SDK MCP 服务器一起使用创建类型安全的 MCP 工具定义。
function tool<Schema extends AnyZodRawShape>(
  name: string,
  description: string,
  inputSchema: Schema,
  handler: (args: InferShape<Schema>, extra: unknown) => Promise<CallToolResult>,
  extras?: { annotations?: ToolAnnotations }
): SdkMcpToolDefinition<Schema>;

​
参数
参数	类型	描述
name	string	工具的名称
description	string	工具功能的描述
inputSchema	Schema extends AnyZodRawShape	定义工具输入参数的 Zod 架构（支持 Zod 3 和 Zod 4）
handler	(args, extra) => Promise<CallToolResult>	执行工具逻辑的异步函数
extras	{ annotations?: ToolAnnotations }	可选的 MCP 工具注释，为客户端提供行为提示
​
ToolAnnotations
从 @modelcontextprotocol/sdk/types.js 重新导出。所有字段都是可选提示；客户端不应依赖它们做出安全决策。
字段	类型	默认值	描述
title	string	undefined	工具的人类可读标题
readOnlyHint	boolean	false	如果为 true，工具不会修改其环境
destructiveHint	boolean	true	如果为 true，工具可能执行破坏性更新（仅在 readOnlyHint 为 false 时有意义）
idempotentHint	boolean	false	如果为 true，使用相同参数的重复调用没有额外效果（仅在 readOnlyHint 为 false 时有意义）
openWorldHint	boolean	true	如果为 true，工具与外部实体交互（例如，网络搜索）。如果为 false，工具的域是封闭的（例如，内存工具）
import { tool } from "@anthropic-ai/claude-agent-sdk";
import { z } from "zod";

const searchTool = tool(
  "search",
  "Search the web",
  { query: z.string() },
  async ({ query }) => {
    return { content: [{ type: "text", text: `Results for: ${query}` }] };
  },
  { annotations: { readOnlyHint: true, openWorldHint: true } }
);

​
createSdkMcpServer()
创建在与应用程序相同的进程中运行的 MCP 服务器实例。
function createSdkMcpServer(options: {
  name: string;
  version?: string;
  tools?: Array<SdkMcpToolDefinition<any>>;
}): McpSdkServerConfigWithInstance;

​
参数
参数	类型	描述
options.name	string	MCP 服务器的名称
options.version	string	可选版本字符串
options.tools	Array<SdkMcpToolDefinition>	使用 tool() 创建的工具定义数组
​
listSessions()
发现并列出具有轻量级元数据的过去会话。按项目目录筛选或列出所有项目中的会话。
function listSessions(options?: ListSessionsOptions): Promise<SDKSessionInfo[]>;

​
参数
参数	类型	默认值	描述
options.dir	string	undefined	列出会话的目录。省略时，返回所有项目中的会话
options.limit	number	undefined	要返回的最大会话数
options.includeWorktrees	boolean	true	当 dir 在 git 存储库内时，包括来自所有 worktree 路径的会话
​
返回类型：SDKSessionInfo
属性	类型	描述
sessionId	string	唯一会话标识符 (UUID)
summary	string	显示标题：自定义标题、自动生成的摘要或第一个提示
lastModified	number	上次修改时间（自纪元以来的毫秒数）
fileSize	number | undefined	会话文件大小（字节）。仅对本地 JSONL 存储进行填充
customTitle	string | undefined	用户设置的会话标题（通过 /rename）
firstPrompt	string | undefined	会话中的第一个有意义的用户提示
gitBranch	string | undefined	会话结束时的 git 分支
cwd	string | undefined	会话的工作目录
tag	string | undefined	用户设置的会话标签（请参阅 tagSession()）
createdAt	number | undefined	创建时间（自纪元以来的毫秒数），来自第一个条目的时间戳
​
示例
打印项目的 10 个最近会话。结果按 lastModified 降序排序，因此第一项是最新的。省略 dir 以搜索所有项目。
import { listSessions } from "@anthropic-ai/claude-agent-sdk";

const sessions = await listSessions({ dir: "/path/to/project", limit: 10 });

for (const session of sessions) {
  console.log(`${session.summary} (${session.sessionId})`);
}

​
getSessionMessages()
从过去的会话记录中读取用户和助手消息。
function getSessionMessages(
  sessionId: string,
  options?: GetSessionMessagesOptions
): Promise<SessionMessage[]>;

​
参数
参数	类型	默认值	描述
sessionId	string	必需	要读取的会话 UUID（请参阅 listSessions()）
options.dir	string	undefined	查找会话的项目目录。省略时，搜索所有项目
options.limit	number	undefined	要返回的最大消息数
options.offset	number	undefined	从开始跳过的消息数
​
返回类型：SessionMessage
属性	类型	描述
type	"user" | "assistant"	消息角色
uuid	string	唯一消息标识符
session_id	string	此消息所属的会话
message	unknown	来自记录的原始消息有效负载
parent_tool_use_id	string | null	对于子代理消息，生成 Agent 工具调用的 tool_use_id。对于主会话消息和较旧的会话为 null
​
示例
import { listSessions, getSessionMessages } from "@anthropic-ai/claude-agent-sdk";

const [latest] = await listSessions({ dir: "/path/to/project", limit: 1 });

if (latest) {
  const messages = await getSessionMessages(latest.sessionId, {
    dir: "/path/to/project",
    limit: 20
  });

  for (const msg of messages) {
    console.log(`[${msg.type}] ${msg.uuid}`);
  }
}

​
getSessionInfo()
按 ID 读取单个会话的元数据，无需扫描完整项目目录。
function getSessionInfo(
  sessionId: string,
  options?: GetSessionInfoOptions
): Promise<SDKSessionInfo | undefined>;

​
参数
参数	类型	默认值	描述
sessionId	string	必需	要查找的会话 UUID
options.dir	string	undefined	项目目录路径。省略时，搜索所有项目目录
返回 SDKSessionInfo，如果找不到会话，则返回 undefined。
​
renameSession()
通过附加自定义标题条目来重命名会话。重复调用是安全的；最新的标题获胜。
function renameSession(
  sessionId: string,
  title: string,
  options?: SessionMutationOptions
): Promise<void>;

​
参数
参数	类型	默认值	描述
sessionId	string	必需	要重命名的会话 UUID
title	string	必需	新标题。修剪空格后必须非空
options.dir	string	undefined	项目目录路径。省略时，搜索所有项目目录
​
tagSession()
标记会话。传递 null 以清除标签。重复调用是安全的；最新的标签获胜。
function tagSession(
  sessionId: string,
  tag: string | null,
  options?: SessionMutationOptions
): Promise<void>;

​
参数
参数	类型	默认值	描述
sessionId	string	必需	要标记的会话 UUID
tag	string | null	必需	标签字符串，或 null 以清除
options.dir	string	undefined	项目目录路径。省略时，搜索所有项目目录
​
resolveSettings()
使用与 CLI 相同的合并引擎为给定目录解析有效的 Claude Code 设置，无需生成 Claude CLI。在调用 query() 之前使用它来检查 query() 调用将看到的配置。
此函数处于 alpha 阶段，其 API 在稳定之前可能会更改。它读取 MDM 源，包括 macOS plist 和 Windows HKLM/HKCU，以与 CLI 启动保持一致，但不执行管理员配置的 policyHelper 子进程。permissions.defaultMode 字段从所有层级（包括项目设置）按原样返回。CLI 在遵守升级权限模式之前应用的信任过滤器不被应用。
function resolveSettings(
  options?: ResolveSettingsOptions
): Promise<ResolvedSettings>;

​
参数
resolveSettings() 接受单个选项对象。所有字段都是可选的。
参数	类型	默认值	描述
options.cwd	string	process.cwd()	用于解析项目和本地设置的相对目录
options.settingSources	SettingSource[]	所有源	要加载的文件系统源。传递 [] 以跳过用户、项目和本地设置。托管策略设置在所有情况下都会加载
options.managedSettings	Settings	undefined	由嵌入主机提供的限制性策略层设置。当存在管理员部署的托管层时被删除；当 parentSettingsBehavior 为 "merge" 时在该层下合并。非限制性密钥（如 model）会被静默删除，以便此选项可以加强托管策略但不能放松它
options.serverManagedSettings	Settings	undefined	来自 /api/claude_code/settings 的服务器托管设置有效负载。非限制性密钥不经过滤地通过
​
返回类型：ResolvedSettings
resolveSettings() 返回一个对象，描述合并的设置和为每个密钥提供的源。
属性	类型	描述
effective	Settings	在按优先级顺序应用所有启用的源后合并的设置
provenance	Partial<Record<keyof Settings, ProvenanceEntry>>	对于 effective 中的每个顶级密钥，哪个源提供了该值
sources	Array<{ source, settings, path?, policyOrigin? }>	每个源的原始设置，按从最低到最高优先级排序
​
示例
下面的示例为项目目录解析设置，并打印控制清理周期的源。
import { resolveSettings } from "@anthropic-ai/claude-agent-sdk";

const { effective, provenance } = await resolveSettings({
  cwd: "/path/to/project",
  settingSources: ["user", "project", "local"],
});

console.log(`Cleanup period: ${effective.cleanupPeriodDays} days`);
console.log(`Set by: ${provenance.cleanupPeriodDays?.source}`);

​
类型
​
Options
query() 函数的配置对象。
属性	类型	默认值	描述
abortController	AbortController	new AbortController()	用于取消操作的控制器
additionalDirectories	string[]	[]	Claude 可以访问的其他目录
agent	string	undefined	主线程的代理名称。代理必须在 agents 选项或设置中定义
agents	Record<string, [AgentDefinition](#agentdefinition)>	undefined	以编程方式定义子代理
agentProgressSummaries	boolean	false	当为 true 时，为子代理生成单行进度摘要，并通过 summary 字段在 task_progress 事件上转发它们。适用于前台和后台子代理
allowDangerouslySkipPermissions	boolean	false	启用绕过权限。使用 permissionMode: 'bypassPermissions' 时需要
allowedTools	string[]	[]	无需提示即可自动批准的工具。这不会将 Claude 限制为仅这些工具；未列出的工具会通过 permissionMode 和 canUseTool 进行处理。使用 disallowedTools 阻止工具。请参阅权限
betas	SdkBeta[]	[]	启用测试功能
canUseTool	CanUseTool	undefined	工具使用的自定义权限函数
continue	boolean	false	继续最近的对话
cwd	string	process.cwd()	当前工作目录
debug	boolean	false	为 Claude Code 进程启用调试模式
debugFile	string	undefined	将调试日志写入特定文件路径。隐式启用调试模式
disallowedTools	string[]	[]	要拒绝的工具。裸名称如 "Bash" 会从 Claude 的上下文中移除该工具。作用域规则如 "Bash(rm *)" 会保留该工具可用，并在每个权限模式（包括 bypassPermissions）中拒绝匹配的调用。请参阅权限
effort	'low' | 'medium' | 'high' | 'xhigh' | 'max'	'high'	控制 Claude 在其响应中投入的努力程度。与自适应思考一起工作以指导思考深度
enableFileCheckpointing	boolean	false	启用文件更改跟踪以进行回滚。请参阅文件 checkpointing
env	Record<string, string | undefined>	process.env	环境变量。请参阅环境变量了解底层 CLI 读取的变量，以及处理缓慢或停滞的 API 响应了解与超时相关的变量。设置 CLAUDE_AGENT_SDK_CLIENT_APP 以在 User-Agent 标头中标识您的应用
executable	'bun' | 'deno' | 'node'	自动检测	要使用的 JavaScript 运行时
executableArgs	string[]	[]	传递给可执行文件的参数
extraArgs	Record<string, string | null>	{}	其他参数
fallbackModel	string	undefined	主模型失败时使用的模型
forkSession	boolean	false	使用 resume 恢复时，分叉到新会话 ID 而不是继续原始会话
forwardSubagentText	boolean	false	转发子代理文本和思考块作为助手和用户消息，并设置 parent_tool_use_id，以便消费者可以呈现嵌套记录。默认情况下，仅从子代理发出 tool_use 和 tool_result 块
hooks	Partial<Record<HookEvent, HookCallbackMatcher[]>>	{}	事件的 Hook 回调
includeHookEvents	boolean	false	在消息流中包括 hook 生命周期事件，作为 SDKHookStartedMessage、SDKHookProgressMessage 和 SDKHookResponseMessage
includePartialMessages	boolean	false	包括部分消息事件
loadTimeoutMs	number	60000	Alpha. 每个 sessionStore.load() 和 sessionStore.listSubkeys() 调用在恢复物化期间的超时时间（以毫秒为单位）。如果适配器未在此窗口内解决，查询将失败而不是挂起。未设置 sessionStore 时忽略
managedSettings	Settings	undefined	由生成的父进程提供的策略层设置。当机器上已存在 IT 控制的托管设置层时删除，除非该管理员选择使用 parentSettingsBehavior: 'merge'。无论如何都会过滤为仅限制性键
maxBudgetUsd	number	undefined	当客户端成本估计达到此 USD 值时停止查询。与 total_cost_usd 的相同估计进行比较；请参阅跟踪成本和使用情况了解准确性注意事项
maxThinkingTokens	number	undefined	已弃用： 改用 thinking。思考过程的最大令牌数
maxTurns	number	undefined	最大代理轮次（工具使用往返）
mcpServers	Record<string, [McpServerConfig](#mcpserverconfig)>	{}	MCP 服务器配置
model	string	CLI 的默认值	要使用的 Claude 模型
onElicitation	(request: ElicitationRequest, options: { signal: AbortSignal }) => Promise<ElicitationResult>	undefined	用于处理 MCP 引出请求的回调。当 MCP 服务器请求用户输入且没有 hook 首先处理它时调用。未提供时，未处理的引出请求会自动被拒绝
outputFormat	{ type: 'json_schema', schema: JSONSchema }	undefined	为代理结果定义输出格式。请参阅结构化输出了解详情
outputStyle	string	undefined	不是 Options 字段。改为在内联 settings 对象或设置文件中设置 outputStyle。请参阅激活输出样式
pathToClaudeCodeExecutable	string	从捆绑的本地二进制文件自动解析	Claude Code 可执行文件的路径。仅在安装期间跳过可选依赖项或您的平台不在支持的集合中时需要
permissionMode	PermissionMode	'default'	会话的权限模式
permissionPromptToolName	string	undefined	权限提示的 MCP 工具名称
persistSession	boolean	true	当为 false 时，禁用会话持久化到磁盘。会话之后无法恢复
planModeInstructions	string	undefined	Plan Mode 的自定义工作流说明。当 permissionMode 为 'plan' 时，此字符串替换默认 Plan Mode 工作流正文。CLI 仍然使用只读强制前导和 ExitPlanMode 协议页脚包装它
plugins	SdkPluginConfig[]	[]	从本地路径加载自定义 plugins。请参阅Plugins了解详情
promptSuggestions	boolean	false	启用提示建议。在每个轮次后发出 prompt_suggestion 消息，包含预测的下一个用户提示
resume	string	undefined	要恢复的会话 ID
resumeSessionAt	string	undefined	在特定消息 UUID 处恢复会话
sandbox	SandboxSettings	undefined	以编程方式配置 sandbox 行为。请参阅Sandbox 设置了解详情
sessionId	string	自动生成	为会话使用特定的 UUID 而不是自动生成一个
sessionStore	SessionStore	undefined	将会话记录镜像到外部后端，以便任何主机都可以恢复它们。请参阅将会话持久化到外部存储
sessionStoreFlush	'batched' | 'eager'	'batched'	Alpha. sessionStore 的刷新模式。未设置 sessionStore 时忽略
settings	string | Settings	undefined	内联设置对象或设置文件的路径。填充优先级顺序中的标志设置层。使用 applyFlagSettings() 在运行时更改
settingSources	SettingSource[]	CLI 默认值（所有源）	控制加载哪些文件系统设置。传递 [] 以禁用用户、项目和本地设置。无论如何都会加载托管策略设置。请参阅使用 Claude Code 功能
skills	string[] | 'all'	undefined	会话可用的 skills。传递 'all' 以启用每个发现的 skill，或传递 skill 名称列表。设置后，SDK 会自动启用 Skill 工具，无需在 allowedTools 中列出。请参阅Skills
spawnClaudeCodeProcess	(options: SpawnOptions) => SpawnedProcess	undefined	用于生成 Claude Code 进程的自定义函数。用于在 VM、容器或远程环境中运行 Claude Code
stderr	(data: string) => void	undefined	stderr 输出的回调
strictMcpConfig	boolean	false	仅使用在 mcpServers 中传递的服务器，并忽略项目 .mcp.json、用户设置和 plugin 提供的 MCP 服务器
systemPrompt	string | { type: 'preset'; preset: 'claude_code'; append?: string; excludeDynamicSections?: boolean }	undefined（最小提示）	系统提示配置。传递字符串以获取自定义提示，或 { type: 'preset', preset: 'claude_code' } 以使用 Claude Code 的系统提示。使用预设对象形式时，添加 append 以使用其他说明扩展它，并设置 excludeDynamicSections: true 以将每个会话上下文移到第一条用户消息中，以便更好地跨机器重用提示缓存
taskBudget	{ total: number }	undefined	Alpha. API 端任务预算（以令牌为单位）。设置后，模型会被告知其剩余令牌预算，以便它可以调整工具使用速度并在达到限制前完成
thinking	ThinkingConfig	支持的模型为 { type: 'adaptive' }	控制 Claude 的思考/推理行为。请参阅 ThinkingConfig 了解选项
title	string	undefined	会话的显示标题。通过 resume 或 continue 恢复时，恢复的会话的持久化标题优先；使用 renameSession() 重新标题现有会话
toolAliases	Record<string, string>	undefined	将内置工具名称映射到 MCP 工具名称，以便 Claude 调用您的 MCP 实现而不是内置工具。例如，{ Bash: 'mcp__workspace__bash' }
toolConfig	ToolConfig	undefined	内置工具行为的配置。请参阅 ToolConfig 了解详情
tools	string[] | { type: 'preset'; preset: 'claude_code' }	undefined	工具配置。传递工具名称数组或使用预设获取 Claude Code 的默认工具
​
处理缓慢或停滞的 API 响应
CLI 子进程读取多个环境变量，这些变量控制 API 超时和停滞检测。通过 env 选项传递它们：
const result = query({
  prompt: "Analyze this code",
  options: {
    env: {
      ...process.env,
      API_TIMEOUT_MS: "120000",
      CLAUDE_CODE_MAX_RETRIES: "2",
      CLAUDE_ASYNC_AGENT_STALL_TIMEOUT_MS: "120000",
    },
  },
});

API_TIMEOUT_MS：Anthropic 客户端上的每个请求超时，以毫秒为单位。默认 600000。适用于主循环和所有子代理。
CLAUDE_CODE_MAX_RETRIES：最大 API 重试次数。默认 10。每次重试都有自己的 API_TIMEOUT_MS 窗口，因此最坏情况下的实际时间大约是 API_TIMEOUT_MS × (CLAUDE_CODE_MAX_RETRIES + 1) 加上退避。
CLAUDE_ASYNC_AGENT_STALL_TIMEOUT_MS：使用 run_in_background 启动的子代理的停滞监视程序。默认 600000。在每个流事件上重置；在停滞时中止子代理，将任务标记为失败，并将错误与任何部分结果一起呈现给父级。不适用于同步子代理。
CLAUDE_ENABLE_STREAM_WATCHDOG=1 与 CLAUDE_STREAM_IDLE_TIMEOUT_MS：当标头已到达但响应正文停止流式传输时中止请求。默认关闭。CLAUDE_STREAM_IDLE_TIMEOUT_MS 默认为 300000 并被限制为该最小值。中止的请求通过正常重试路径进行。
​
Query 对象
由 query() 函数返回的接口。
interface Query extends AsyncGenerator<SDKMessage, void> {
  interrupt(): Promise<void>;
  rewindFiles(
    userMessageId: string,
    options?: { dryRun?: boolean }
  ): Promise<RewindFilesResult>;
  setPermissionMode(mode: PermissionMode): Promise<void>;
  setModel(model?: string): Promise<void>;
  setMaxThinkingTokens(maxThinkingTokens: number | null): Promise<void>;
  applyFlagSettings(settings: { [K in keyof Settings]?: Settings[K] | null }): Promise<void>;
  initializationResult(): Promise<SDKControlInitializeResponse>;
  supportedCommands(): Promise<SlashCommand[]>;
  supportedModels(): Promise<ModelInfo[]>;
  supportedAgents(): Promise<AgentInfo[]>;
  mcpServerStatus(): Promise<McpServerStatus[]>;
  accountInfo(): Promise<AccountInfo>;
  reconnectMcpServer(serverName: string): Promise<void>;
  toggleMcpServer(serverName: string, enabled: boolean): Promise<void>;
  setMcpServers(servers: Record<string, McpServerConfig>): Promise<McpSetServersResult>;
  streamInput(stream: AsyncIterable<SDKUserMessage>): Promise<void>;
  stopTask(taskId: string): Promise<void>;
  close(): void;
}

​
方法
方法	描述
interrupt()	中断查询（仅在流式输入模式下可用）
rewindFiles(userMessageId, options?)	将文件恢复到指定用户消息时的状态。传递 { dryRun: true } 以预览更改。需要 enableFileCheckpointing: true。请参阅文件 checkpointing
setPermissionMode()	更改权限模式（仅在流式输入模式下可用）
setModel()	更改模型（仅在流式输入模式下可用）
setMaxThinkingTokens()	已弃用： 改用 thinking 选项。更改最大思考令牌数
applyFlagSettings(settings)	在运行时将设置合并到会话的标志设置层中（仅在流式输入模式下可用）。请参阅 applyFlagSettings()
initializationResult()	返回完整的初始化结果，包括支持的命令、模型、帐户信息和输出样式配置
supportedCommands()	返回可用的 slash commands
supportedModels()	返回具有显示信息的可用模型
supportedAgents()	返回可用的子代理作为 AgentInfo[]
mcpServerStatus()	返回连接的 MCP 服务器的状态
accountInfo()	返回帐户信息
reconnectMcpServer(serverName)	按名称重新连接 MCP 服务器
toggleMcpServer(serverName, enabled)	按名称启用或禁用 MCP 服务器
setMcpServers(servers)	动态替换此会话的 MCP 服务器集。返回有关添加、删除的服务器和任何错误的信息
streamInput(stream)	将输入消息流式传输到查询以进行多轮对话
stopTask(taskId)	按 ID 停止运行的后台任务
close()	关闭查询并终止底层进程。强制结束查询并清理所有资源
​
applyFlagSettings()
在运行的会话上更改任何设置而无需重新启动查询。当没有专用设置器的设置需要在会话中期更改时使用它，例如在代理读取不受信任的输入后收紧 permissions。setModel() 和 setPermissionMode() 是这两个键的专用设置器；applyFlagSettings() 是接受任何设置键子集的通用形式，在此处传递 model 的行为与 setModel() 相同。
这些值被写入标志设置层，这是内联 query() 的 settings 选项在启动时填充的同一层。标志设置位于设置优先级顺序的顶部附近：它们覆盖用户、项目和本地设置，只有托管策略设置可以覆盖它们。这与优先级部分称为编程选项的层相同。
连续调用浅合并顶级键。第二次调用 { permissions: {...} } 会替换先前调用中的整个 permissions 对象，而不是深度合并到其中。要从标志层清除键并回退到较低优先级源，请为该键传递 null。传递 undefined 无效，因为 JSON 序列化会将其删除。
仅在流式输入模式下可用，与 setModel() 和 setPermissionMode() 的约束相同。
下面的示例在会话中期切换活动模型，然后清除覆盖，以便模型回退到用户或项目设置指定的任何内容。
const q = query({ prompt: messageStream });

// 覆盖会话其余部分的模型
await q.applyFlagSettings({ model: "claude-opus-4-6" });

// 稍后：清除覆盖并回退到较低优先级设置
await q.applyFlagSettings({ model: null });

applyFlagSettings() 仅适用于 TypeScript。Python SDK 不公开等效方法。
​
WarmQuery
由 startup() 返回的句柄。子进程已生成并初始化，因此在此句柄上调用 query() 会直接将提示写入准备好的进程，无需启动延迟。
interface WarmQuery extends AsyncDisposable {
  query(prompt: string | AsyncIterable<SDKUserMessage>): Query;
  close(): void;
}

​
方法
方法	描述
query(prompt)	向预热的子进程发送提示并返回 Query。每个 WarmQuery 只能调用一次
close()	关闭子进程而不发送提示。使用此方法丢弃不再需要的预热查询
WarmQuery 实现 AsyncDisposable，因此可以与 await using 一起使用以进行自动清理。
​
SDKControlInitializeResponse
initializationResult() 的返回类型。包含会话初始化数据。
type SDKControlInitializeResponse = {
  commands: SlashCommand[];
  agents: AgentInfo[];
  output_style: string;
  available_output_styles: string[];
  models: ModelInfo[];
  account: AccountInfo;
  fast_mode_state?: "off" | "cooldown" | "on";
};

​
AgentDefinition
以编程方式定义的子代理的配置。
type AgentDefinition = {
  description: string;
  tools?: string[];
  disallowedTools?: string[];
  prompt: string;
  model?: string;
  mcpServers?: AgentMcpServerSpec[];
  skills?: string[];
  initialPrompt?: string;
  maxTurns?: number;
  background?: boolean;
  memory?: "user" | "project" | "local";
  effort?: "low" | "medium" | "high" | "xhigh" | "max" | number;
  permissionMode?: PermissionMode;
  criticalSystemReminder_EXPERIMENTAL?: string;
};

字段	必需	描述
description	是	何时使用此代理的自然语言描述
tools	否	允许的工具名称数组。如果省略，继承父级的所有工具。要将 Skills 预加载到代理的上下文中，请使用 skills 字段而不是在此处列出 'Skill'
disallowedTools	否	要为此代理明确禁止的工具名称数组
prompt	是	代理的系统提示
model	否	此代理的模型覆盖。接受别名，如 'sonnet'、'opus'、'haiku'、'inherit'，或完整的模型 ID。如果省略或 'inherit'，使用主模型
mcpServers	否	此代理的 MCP 服务器规范
skills	否	要预加载到代理上下文中的 skill 名称数组
initialPrompt	否	当此代理作为主线程代理运行时，自动提交为第一个用户轮次
maxTurns	否	停止前的最大代理轮次数（API 往返）
background	否	调用时将此代理作为非阻塞后台任务运行
memory	否	此代理的内存源：'user'、'project' 或 'local'
effort	否	此代理的推理努力级别。接受命名级别或整数
permissionMode	否	此代理内工具执行的权限模式。请参阅 PermissionMode
criticalSystemReminder_EXPERIMENTAL	否	实验性：添加到系统提示的关键提醒
​
AgentMcpServerSpec
指定子代理可用的 MCP 服务器。可以是服务器名称（字符串，引用父级 mcpServers 配置中的服务器）或内联服务器配置记录，将服务器名称映射到配置。
type AgentMcpServerSpec = string | Record<string, McpServerConfigForProcessTransport>;

其中 McpServerConfigForProcessTransport 是 McpStdioServerConfig | McpSSEServerConfig | McpHttpServerConfig | McpSdkServerConfig。
​
SettingSource
控制 SDK 从哪些基于文件系统的配置源加载设置。
type SettingSource = "user" | "project" | "local";

值	描述	位置
'user'	全局用户设置	~/.claude/settings.json
'project'	共享项目设置（版本控制）	.claude/settings.json
'local'	本地项目设置（gitignored）	.claude/settings.local.json
​
默认行为
当 settingSources 被省略或 undefined 时，query() 加载与 Claude Code CLI 相同的文件系统设置：用户、项目和本地。在所有情况下都会加载托管策略设置。请参阅settingSources 不控制的内容了解无论此选项如何都会读取的输入，以及如何禁用它们。
​
为什么使用 settingSources
禁用文件系统设置：
// 不从磁盘加载用户、项目或本地设置
const result = query({
  prompt: "Analyze this code",
  options: { settingSources: [] }
});

显式加载所有文件系统设置：
const result = query({
  prompt: "Analyze this code",
  options: {
    settingSources: ["user", "project", "local"] // 加载所有设置
  }
});

仅加载特定设置源：
// 仅加载项目设置，忽略用户和本地
const result = query({
  prompt: "Run CI checks",
  options: {
    settingSources: ["project"] // 仅 .claude/settings.json
  }
});

测试和 CI 环境：
// 通过排除本地设置确保 CI 中的一致行为
const result = query({
  prompt: "Run tests",
  options: {
    settingSources: ["project"], // 仅团队共享设置
    permissionMode: "bypassPermissions"
  }
});

仅 SDK 应用程序：
// 以编程方式定义所有内容。
// 传递 [] 以选择退出文件系统设置源。
const result = query({
  prompt: "Review this PR",
  options: {
    settingSources: [],
    agents: {
      /* ... */
    },
    mcpServers: {
      /* ... */
    },
    allowedTools: ["Read", "Grep", "Glob"]
  }
});

加载 CLAUDE.md 项目说明：
// 加载项目设置以包括 CLAUDE.md 文件
const result = query({
  prompt: "Add a new feature following project conventions",
  options: {
    systemPrompt: {
      type: "preset",
      preset: "claude_code" // 使用 Claude Code 的系统提示
    },
    settingSources: ["project"], // 从项目目录加载 CLAUDE.md
    allowedTools: ["Read", "Write", "Edit"]
  }
});

​
设置优先级
加载多个源时，设置按此优先级合并（从高到低）：
本地设置（.claude/settings.local.json）
项目设置（.claude/settings.json）
用户设置（~/.claude/settings.json）
编程选项（如 agents、allowedTools 和 settings）覆盖用户、项目和本地文件系统设置。托管策略设置优先于编程选项。
​
PermissionMode
type PermissionMode =
  | "default" // 标准权限行为
  | "acceptEdits" // 自动接受文件编辑
  | "bypassPermissions" // 绕过所有权限检查
  | "plan" // Plan Mode - 仅读取工具
  | "dontAsk" // 不提示权限，如果未预先批准则拒绝
  | "auto"; // 使用模型分类器批准或拒绝每个工具调用

​
CanUseTool
用于控制工具使用的自定义权限函数类型。
type CanUseTool = (
  toolName: string,
  input: Record<string, unknown>,
  options: {
    signal: AbortSignal;
    suggestions?: PermissionUpdate[];
    blockedPath?: string;
    decisionReason?: string;
    toolUseID: string;
    agentID?: string;
  }
) => Promise<PermissionResult>;

选项	类型	描述
signal	AbortSignal	如果应中止操作，则发出信号
suggestions	PermissionUpdate[]	建议的权限更新，以便用户不会再次被提示此工具。Bash 提示包括一个建议，其中包含 localSettings 目标，因此在 updatedPermissions 中返回它会将规则写入 .claude/settings.local.json 并在会话中持久化。
blockedPath	string	触发权限请求的文件路径（如果适用）
decisionReason	string	解释为什么触发此权限请求
toolUseID	string	此特定工具调用在助手消息中的唯一标识符
agentID	string	如果在子代理中运行，子代理的 ID
​
PermissionResult
权限检查的结果。
type PermissionResult =
  | {
      behavior: "allow";
      updatedInput?: Record<string, unknown>;
      updatedPermissions?: PermissionUpdate[];
      toolUseID?: string;
    }
  | {
      behavior: "deny";
      message: string;
      interrupt?: boolean;
      toolUseID?: string;
    };

​
ToolConfig
内置工具行为的配置。
type ToolConfig = {
  askUserQuestion?: {
    previewFormat?: "markdown" | "html";
  };
};

字段	类型	描述
askUserQuestion.previewFormat	'markdown' | 'html'	选择加入 AskUserQuestion 选项上的 preview 字段并设置其内容格式。未设置时，Claude 不发出预览
​
McpServerConfig
MCP 服务器的配置。
type McpServerConfig =
  | McpStdioServerConfig
  | McpSSEServerConfig
  | McpHttpServerConfig
  | McpSdkServerConfigWithInstance;

​
McpStdioServerConfig
type McpStdioServerConfig = {
  type?: "stdio";
  command: string;
  args?: string[];
  env?: Record<string, string>;
};

​
McpSSEServerConfig
type McpSSEServerConfig = {
  type: "sse";
  url: string;
  headers?: Record<string, string>;
};

​
McpHttpServerConfig
type McpHttpServerConfig = {
  type: "http";
  url: string;
  headers?: Record<string, string>;
};

​
McpSdkServerConfigWithInstance
type McpSdkServerConfigWithInstance = {
  type: "sdk";
  name: string;
  instance: McpServer;
};

​
McpClaudeAIProxyServerConfig
type McpClaudeAIProxyServerConfig = {
  type: "claudeai-proxy";
  url: string;
  id: string;
};

​
SdkPluginConfig
SDK 中加载 plugins 的配置。
type SdkPluginConfig = {
  type: "local";
  path: string;
};

字段	类型	描述
type	'local'	必须为 'local'（目前仅支持本地 plugins）
path	string	插件目录的绝对或相对路径
示例：
plugins: [
  { type: "local", path: "./my-plugin" },
  { type: "local", path: "/absolute/path/to/plugin" }
];

有关创建和使用 plugins 的完整信息，请参阅Plugins。
​
消息类型
​
SDKMessage
查询返回的所有可能消息的联合类型。
type SDKMessage =
  | SDKAssistantMessage
  | SDKUserMessage
  | SDKUserMessageReplay
  | SDKResultMessage
  | SDKSystemMessage
  | SDKPartialAssistantMessage
  | SDKCompactBoundaryMessage
  | SDKStatusMessage
  | SDKLocalCommandOutputMessage
  | SDKHookStartedMessage
  | SDKHookProgressMessage
  | SDKHookResponseMessage
  | SDKPluginInstallMessage
  | SDKToolProgressMessage
  | SDKAuthStatusMessage
  | SDKTaskNotificationMessage
  | SDKTaskStartedMessage
  | SDKTaskProgressMessage
  | SDKTaskUpdatedMessage
  | SDKSessionStateChangedMessage
  | SDKNotificationMessage
  | SDKFilesPersistedEvent
  | SDKToolUseSummaryMessage
  | SDKMemoryRecallMessage
  | SDKRateLimitEvent
  | SDKElicitationCompleteMessage
  | SDKPermissionDeniedMessage
  | SDKPromptSuggestionMessage
  | SDKAPIRetryMessage
  | SDKMirrorErrorMessage;

​
SDKAssistantMessage
助手响应消息。
type SDKAssistantMessage = {
  type: "assistant";
  uuid: UUID;
  session_id: string;
  message: BetaMessage; // 来自 Anthropic SDK
  parent_tool_use_id: string | null;
  error?: SDKAssistantMessageError;
};

message 字段是来自 Anthropic SDK 的 BetaMessage。它包括 id、content、model、stop_reason 和 usage 等字段。
SDKAssistantMessageError 是以下之一：'authentication_failed'、'oauth_org_not_allowed'、'billing_error'、'rate_limit'、'invalid_request'、'model_not_found'、'server_error'、'max_output_tokens' 或 'unknown'。'model_not_found' 表示所选模型不存在或对您的账户或部署不可用。
​
SDKUserMessage
用户输入消息。
type SDKUserMessage = {
  type: "user";
  uuid?: UUID;
  session_id?: string;
  message: MessageParam; // 来自 Anthropic SDK
  parent_tool_use_id: string | null;
  isSynthetic?: boolean;
  shouldQuery?: boolean;
  tool_use_result?: unknown;
  origin?: SDKMessageOrigin;
};

将 shouldQuery 设置为 false 以将消息附加到记录中而不触发助手轮次。消息被保留并合并到下一个触发轮次的用户消息中。使用此方法注入上下文，例如您在带外运行的命令的输出，而无需在其上花费模型调用。
​
SDKUserMessageReplay
具有必需 UUID 的重放用户消息。
type SDKUserMessageReplay = {
  type: "user";
  uuid: UUID;
  session_id: string;
  message: MessageParam;
  parent_tool_use_id: string | null;
  isSynthetic?: boolean;
  tool_use_result?: unknown;
  origin?: SDKMessageOrigin;
  isReplay: true;
};

​
SDKResultMessage
最终结果消息。
type SDKResultMessage =
  | {
      type: "result";
      subtype: "success";
      uuid: UUID;
      session_id: string;
      duration_ms: number;
      duration_api_ms: number;
      is_error: boolean;
      api_error_status?: number | null;
      num_turns: number;
      result: string;
      stop_reason: string | null;
      ttft_ms?: number;
      total_cost_usd: number;
      usage: NonNullableUsage;
      modelUsage: { [modelName: string]: ModelUsage };
      permission_denials: SDKPermissionDenial[];
      structured_output?: unknown;
      deferred_tool_use?: { id: string; name: string; input: Record<string, unknown> };
      terminal_reason?: TerminalReason;
      fast_mode_state?: FastModeState;
      origin?: SDKMessageOrigin;
    }
  | {
      type: "result";
      subtype:
        | "error_max_turns"
        | "error_during_execution"
        | "error_max_budget_usd"
        | "error_max_structured_output_retries";
      uuid: UUID;
      session_id: string;
      duration_ms: number;
      duration_api_ms: number;
      is_error: boolean;
      num_turns: number;
      stop_reason: string | null;
      total_cost_usd: number;
      usage: NonNullableUsage;
      modelUsage: { [modelName: string]: ModelUsage };
      permission_denials: SDKPermissionDenial[];
      errors: string[];
      terminal_reason?: TerminalReason;
      fast_mode_state?: FastModeState;
      origin?: SDKMessageOrigin;
    };

结果上的多个字段除了 subtype 之外还提供诊断详情：
api_error_status：终止对话的 API 错误的 HTTP 状态码。当轮次在没有 API 错误的情况下结束时，该字段不存在或为 null。
ttft_ms：首个令牌的时间（毫秒）。仅在成功分支上显示。
terminal_reason：循环结束的原因。为 "completed"、"max_turns"、"tool_deferred"、"aborted_streaming"、"aborted_tools"、"hook_stopped"、"stop_hook_prevented"、"blocking_limit"、"rapid_refill_breaker"、"prompt_too_long"、"image_error" 或 "model_error" 之一。
fast_mode_state：为 "on"、"off" 或 "cooldown" 之一。
origin 字段转发触发此结果的用户消息的 SDKMessageOrigin。当后台任务完成且 SDK 注入合成后续轮次时，生成的 SDKResultMessage 携带 origin: { kind: "task-notification" }。检查此字段以区分回答您的提示的结果与为后台任务后续操作发出的结果，以便您可以路由或抑制后者。对于在任何用户轮次之前发出的结果（例如启动错误），该字段不存在。
当 PreToolUse hook 返回 permissionDecision: "defer" 时，结果具有 stop_reason: "tool_deferred" 和 deferred_tool_use 携带待处理工具的 id、name 和 input。读取此字段以在您自己的 UI 中显示请求，然后使用相同的 session_id 恢复以继续。有关完整的往返过程，请参阅稍后延迟工具调用。
​
SDKSystemMessage
系统初始化消息。
type SDKSystemMessage = {
  type: "system";
  subtype: "init";
  uuid: UUID;
  session_id: string;
  agents?: string[];
  apiKeySource: ApiKeySource;
  betas?: string[];
  claude_code_version: string;
  cwd: string;
  tools: string[];
  mcp_servers: {
    name: string;
    status: string;
  }[];
  model: string;
  permissionMode: PermissionMode;
  slash_commands: string[];
  output_style: string;
  skills: string[];
  plugins: { name: string; path: string }[];
};

​
SDKPartialAssistantMessage
流式部分消息（仅当 includePartialMessages 为 true 时）。
type SDKPartialAssistantMessage = {
  type: "stream_event";
  event: BetaRawMessageStreamEvent; // 来自 Anthropic SDK
  parent_tool_use_id: string | null;
  uuid: UUID;
  session_id: string;
};

​
SDKCompactBoundaryMessage
指示对话压缩边界的消息。
type SDKCompactBoundaryMessage = {
  type: "system";
  subtype: "compact_boundary";
  uuid: UUID;
  session_id: string;
  compact_metadata: {
    trigger: "manual" | "auto";
    pre_tokens: number;
  };
};

​
SDKPluginInstallMessage
插件安装进度事件。当设置 CLAUDE_CODE_SYNC_PLUGIN_INSTALL 时发出，以便您的 Agent SDK 应用程序可以在第一个轮次之前跟踪市场插件安装。started 和 completed 状态括起整体安装。installed 和 failed 状态报告单个市场并包括 name。
type SDKPluginInstallMessage = {
  type: "system";
  subtype: "plugin_install";
  status: "started" | "installed" | "failed" | "completed";
  name?: string;
  error?: string;
  uuid: UUID;
  session_id: string;
};

​
SDKPermissionDeniedMessage
当权限系统自动拒绝工具调用而不显示交互式提示时发出的流事件。使用它在发生时在您的 UI 中呈现拒绝，而不仅仅观察随后的 is_error 工具结果。交互式询问路径通过 canUseTool 回调单独到达您的应用程序。由 PreToolUse hook 发出的拒绝不会通过此事件报告。
此事件需要 Claude Code v2.1.136 或更高版本。
type SDKPermissionDeniedMessage = {
  type: "system";
  subtype: "permission_denied";
  tool_name: string;
  tool_use_id: string;
  agent_id?: string;
  decision_reason_type?: string;
  decision_reason?: string;
  message: string;
  uuid: UUID;
  session_id: string;
};

字段	类型	描述
tool_name	string	被拒绝的工具的名称
tool_use_id	string	此拒绝回答的 tool_use 块的 ID
agent_id	string	当拒绝的调用源自子代理内部时的子代理 ID。镜像 can_use_tool 上的字段以进行主机端路由
decision_reason_type	string	决定组件的鉴别器，例如 "rule"、"mode"、"classifier" 或 "asyncAgent"
decision_reason	string	来自决定组件的人类可读原因（如果可用）
message	string	在 tool_result 中返回给模型的拒绝消息
​
SDKPermissionDenial
有关被拒绝的工具使用的信息。
type SDKPermissionDenial = {
  tool_name: string;
  tool_use_id: string;
  tool_input: Record<string, unknown>;
};

​
SDKMessageOrigin
用户角色消息的来源。这在 SDKUserMessage 上显示为 origin，并转发到相应的 SDKResultMessage，以便您可以判断给定轮次的触发因素。
type SDKMessageOrigin =
  | { kind: "human" }
  | { kind: "channel"; server: string }
  | { kind: "peer"; from: string; name?: string }
  | { kind: "task-notification" }
  | { kind: "coordinator" };

kind	含义
human	来自最终用户的直接输入。在用户消息上，缺少的 origin 也表示人工输入。
channel	消息到达频道。server 是源 MCP 服务器名称。
peer	来自另一个代理会话的消息，通过 SendMessage。from 是发送者地址；name 是发送者的显示名称（如果可用）。
task-notification	后台任务完成后注入的合成轮次。请参阅 SDKTaskNotificationMessage。
coordinator	来自代理团队中的团队协调员的消息。
​
Hook 类型
有关使用 hooks 的综合指南，包括示例和常见模式，请参阅 Hooks 指南。
​
HookEvent
可用的 hook 事件。
type HookEvent =
  | "PreToolUse"
  | "PostToolUse"
  | "PostToolUseFailure"
  | "PostToolBatch"
  | "Notification"
  | "UserPromptSubmit"
  | "SessionStart"
  | "SessionEnd"
  | "Stop"
  | "SubagentStart"
  | "SubagentStop"
  | "PreCompact"
  | "PermissionRequest"
  | "Setup"
  | "TeammateIdle"
  | "TaskCompleted"
  | "ConfigChange"
  | "WorktreeCreate"
  | "WorktreeRemove";

​
HookCallback
Hook 回调函数类型。
type HookCallback = (
  input: HookInput, // 所有 hook 输入类型的联合
  toolUseID: string | undefined,
  options: { signal: AbortSignal }
) => Promise<HookJSONOutput>;

​
HookCallbackMatcher
带有可选匹配器的 Hook 配置。
interface HookCallbackMatcher {
  matcher?: string;
  hooks: HookCallback[];
  timeout?: number; // 此匹配器中所有 hooks 的超时时间（秒）
}

​
HookInput
所有 hook 输入类型的联合类型。
type HookInput =
  | PreToolUseHookInput
  | PostToolUseHookInput
  | PostToolUseFailureHookInput
  | PostToolBatchHookInput
  | NotificationHookInput
  | UserPromptSubmitHookInput
  | SessionStartHookInput
  | SessionEndHookInput
  | StopHookInput
  | SubagentStartHookInput
  | SubagentStopHookInput
  | PreCompactHookInput
  | PermissionRequestHookInput
  | SetupHookInput
  | TeammateIdleHookInput
  | TaskCompletedHookInput
  | ConfigChangeHookInput
  | WorktreeCreateHookInput
  | WorktreeRemoveHookInput;

​
BaseHookInput
所有 hook 输入类型扩展的基本接口。
type BaseHookInput = {
  session_id: string;
  transcript_path: string;
  cwd: string;
  permission_mode?: string;
  effort?: { level: string };
  agent_id?: string;
  agent_type?: string;
};

​
PreToolUseHookInput
type PreToolUseHookInput = BaseHookInput & {
  hook_event_name: "PreToolUse";
  tool_name: string;
  tool_input: unknown;
  tool_use_id: string;
};

​
PostToolUseHookInput
type PostToolUseHookInput = BaseHookInput & {
  hook_event_name: "PostToolUse";
  tool_name: string;
  tool_input: unknown;
  tool_response: unknown;
  tool_use_id: string;
  duration_ms?: number;
};

​
PostToolUseFailureHookInput
type PostToolUseFailureHookInput = BaseHookInput & {
  hook_event_name: "PostToolUseFailure";
  tool_name: string;
  tool_input: unknown;
  tool_use_id: string;
  error: string;
  is_interrupt?: boolean;
  duration_ms?: number;
};

​
PostToolBatchHookInput
在批处理中的每个工具调用都已解决后触发一次，在下一个模型请求之前。tool_response 携带序列化的 tool_result 内容，模型会看到该内容；其形状与 PostToolUseHookInput 的结构化 Output 对象不同。
type PostToolBatchHookInput = BaseHookInput & {
  hook_event_name: "PostToolBatch";
  tool_calls: PostToolBatchToolCall[];
};

type PostToolBatchToolCall = {
  tool_name: string;
  tool_input: unknown;
  tool_use_id: string;
  tool_response?: unknown;
};

​
NotificationHookInput
type NotificationHookInput = BaseHookInput & {
  hook_event_name: "Notification";
  message: string;
  title?: string;
  notification_type: string;
};

​
UserPromptSubmitHookInput
type UserPromptSubmitHookInput = BaseHookInput & {
  hook_event_name: "UserPromptSubmit";
  prompt: string;
};

​
SessionStartHookInput
type SessionStartHookInput = BaseHookInput & {
  hook_event_name: "SessionStart";
  source: "startup" | "resume" | "clear" | "compact";
  agent_type?: string;
  model?: string;
};

​
SessionEndHookInput
type SessionEndHookInput = BaseHookInput & {
  hook_event_name: "SessionEnd";
  reason: ExitReason; // EXIT_REASONS 数组中的字符串
};

​
StopHookInput
type StopHookInput = BaseHookInput & {
  hook_event_name: "Stop";
  stop_hook_active: boolean;
  last_assistant_message?: string;
};

​
SubagentStartHookInput
type SubagentStartHookInput = BaseHookInput & {
  hook_event_name: "SubagentStart";
  agent_id: string;
  agent_type: string;
};

​
SubagentStopHookInput
type SubagentStopHookInput = BaseHookInput & {
  hook_event_name: "SubagentStop";
  stop_hook_active: boolean;
  agent_id: string;
  agent_transcript_path: string;
  agent_type: string;
  last_assistant_message?: string;
};

​
PreCompactHookInput
type PreCompactHookInput = BaseHookInput & {
  hook_event_name: "PreCompact";
  trigger: "manual" | "auto";
  custom_instructions: string | null;
};

​
PermissionRequestHookInput
type PermissionRequestHookInput = BaseHookInput & {
  hook_event_name: "PermissionRequest";
  tool_name: string;
  tool_input: unknown;
  permission_suggestions?: PermissionUpdate[];
};

​
SetupHookInput
type SetupHookInput = BaseHookInput & {
  hook_event_name: "Setup";
  trigger: "init" | "maintenance";
};

​
TeammateIdleHookInput
type TeammateIdleHookInput = BaseHookInput & {
  hook_event_name: "TeammateIdle";
  teammate_name: string;
  team_name: string;
};

​
TaskCompletedHookInput
type TaskCompletedHookInput = BaseHookInput & {
  hook_event_name: "TaskCompleted";
  task_id: string;
  task_subject: string;
  task_description?: string;
  teammate_name?: string;
  team_name?: string;
};

​
ConfigChangeHookInput
type ConfigChangeHookInput = BaseHookInput & {
  hook_event_name: "ConfigChange";
  source:
    | "user_settings"
    | "project_settings"
    | "local_settings"
    | "policy_settings"
    | "skills";
  file_path?: string;
};

​
WorktreeCreateHookInput
type WorktreeCreateHookInput = BaseHookInput & {
  hook_event_name: "WorktreeCreate";
  name: string;
};

​
WorktreeRemoveHookInput
type WorktreeRemoveHookInput = BaseHookInput & {
  hook_event_name: "WorktreeRemove";
  worktree_path: string;
};

​
HookJSONOutput
Hook 返回值。
type HookJSONOutput = AsyncHookJSONOutput | SyncHookJSONOutput;

​
AsyncHookJSONOutput
type AsyncHookJSONOutput = {
  async: true;
  asyncTimeout?: number;
};

​
SyncHookJSONOutput
type SyncHookJSONOutput = {
  continue?: boolean;
  suppressOutput?: boolean;
  stopReason?: string;
  decision?: "approve" | "block";
  systemMessage?: string;
  reason?: string;
  hookSpecificOutput?:
    | {
        hookEventName: "PreToolUse";
        permissionDecision?: "allow" | "deny" | "ask" | "defer";
        permissionDecisionReason?: string;
        updatedInput?: Record<string, unknown>;
        additionalContext?: string;
      }
    | {
        hookEventName: "UserPromptSubmit";
        additionalContext?: string;
      }
    | {
        hookEventName: "SessionStart";
        additionalContext?: string;
      }
    | {
        hookEventName: "Setup";
        additionalContext?: string;
      }
    | {
        hookEventName: "SubagentStart";
        additionalContext?: string;
      }
    | {
        hookEventName: "PostToolUse";
        additionalContext?: string;
        updatedToolOutput?: unknown;
        /** @deprecated 使用 `updatedToolOutput`，它适用于所有工具。 */
        updatedMCPToolOutput?: unknown;
      }
    | {
        hookEventName: "PostToolUseFailure";
        additionalContext?: string;
      }
    | {
        hookEventName: "PostToolBatch";
        additionalContext?: string;
      }
    | {
        hookEventName: "Notification";
        additionalContext?: string;
      }
    | {
        hookEventName: "PermissionRequest";
        decision:
          | {
              behavior: "allow";
              updatedInput?: Record<string, unknown>;
              updatedPermissions?: PermissionUpdate[];
            }
          | {
              behavior: "deny";
              message?: string;
              interrupt?: boolean;
            };
      };
};

​
工具输入类型
所有内置 Claude Code 工具的输入架构文档。这些类型从 @anthropic-ai/claude-agent-sdk 导出，可用于类型安全的工具交互。
​
ToolInputSchemas
所有工具输入类型的联合，从 @anthropic-ai/claude-agent-sdk 导出。
type ToolInputSchemas =
  | AgentInput
  | AskUserQuestionInput
  | BashInput
  | TaskOutputInput
  | EnterWorktreeInput
  | ExitPlanModeInput
  | FileEditInput
  | FileReadInput
  | FileWriteInput
  | GlobInput
  | GrepInput
  | ListMcpResourcesInput
  | McpInput
  | MonitorInput
  | NotebookEditInput
  | ReadMcpResourceInput
  | SubscribeMcpResourceInput
  | SubscribePollingInput
  | TaskCreateInput
  | TaskGetInput
  | TaskListInput
  | TaskStopInput
  | TaskUpdateInput
  | TodoWriteInput
  | UnsubscribeMcpResourceInput
  | UnsubscribePollingInput
  | WebFetchInput
  | WebSearchInput;

​
Agent
工具名称： Agent（之前为 Task，仍然接受作为别名）
type AgentInput = {
  description: string;
  prompt: string;
  subagent_type: string;
  model?: "sonnet" | "opus" | "haiku";
  resume?: string;
  run_in_background?: boolean;
  max_turns?: number;
  name?: string;
  team_name?: string;
  mode?: "acceptEdits" | "bypassPermissions" | "default" | "dontAsk" | "plan";
  isolation?: "worktree";
};

启动新代理以自主处理复杂的多步骤任务。
​
AskUserQuestion
工具名称： AskUserQuestion
type AskUserQuestionInput = {
  questions: Array<{
    question: string;
    header: string;
    options: Array<{ label: string; description: string; preview?: string }>;
    multiSelect: boolean;
  }>;
};

在执行期间向用户提出澄清问题。请参阅处理批准和用户输入了解使用详情。
​
Bash
工具名称： Bash
type BashInput = {
  command: string;
  timeout?: number;
  description?: string;
  run_in_background?: boolean;
  dangerouslyDisableSandbox?: boolean;
};

在持久 shell 会话中执行 bash 命令，支持可选超时和后台执行。
​
Monitor
工具名称： Monitor
type MonitorInput = {
  command: string;
  description: string;
  timeout_ms?: number;
  persistent?: boolean;
};

运行后台脚本并将每个 stdout 行作为事件传递给 Claude，以便它可以做出反应而无需轮询。为会话长度的监视（如日志尾部）设置 persistent: true。Monitor 遵循与 Bash 相同的权限规则。请参阅 Monitor 工具参考了解行为和提供商可用性。
​
TaskOutput
工具名称： TaskOutput
type TaskOutputInput = {
  task_id: string;
  block: boolean;
  timeout: number;
};

从运行中或已完成的后台任务检索输出。
​
Edit
工具名称： Edit
type FileEditInput = {
  file_path: string;
  old_string: string;
  new_string: string;
  replace_all?: boolean;
};

在文件中执行精确字符串替换。
​
Read
工具名称： Read
type FileReadInput = {
  file_path: string;
  offset?: number;
  limit?: number;
  pages?: string;
};

从本地文件系统读取文件，包括文本、图像、PDF 和 Jupyter 笔记本。对 PDF 页面范围使用 pages（例如，"1-5"）。
​
Write
工具名称： Write
type FileWriteInput = {
  file_path: string;
  content: string;
};

将文件写入本地文件系统，如果存在则覆盖。
​
Glob
工具名称： Glob
type GlobInput = {
  pattern: string;
  path?: string;
};

快速文件模式匹配，适用于任何代码库大小。
​
Grep
工具名称： Grep
type GrepInput = {
  pattern: string;
  path?: string;
  glob?: string;
  type?: string;
  output_mode?: "content" | "files_with_matches" | "count";
  "-i"?: boolean;
  "-n"?: boolean;
  "-B"?: number;
  "-A"?: number;
  "-C"?: number;
  context?: number;
  head_limit?: number;
  offset?: number;
  multiline?: boolean;
};

基于 ripgrep 的强大搜索工具，支持正则表达式。
​
TaskStop
工具名称： TaskStop
type TaskStopInput = {
  task_id?: string;
  shell_id?: string; // 已弃用：使用 task_id
};

按 ID 停止运行的后台任务或 shell。
​
NotebookEdit
工具名称： NotebookEdit
type NotebookEditInput = {
  notebook_path: string;
  cell_id?: string;
  new_source: string;
  cell_type?: "code" | "markdown";
  edit_mode?: "replace" | "insert" | "delete";
};

编辑 Jupyter 笔记本文件中的单元格。
​
WebFetch
工具名称： WebFetch
type WebFetchInput = {
  url: string;
  prompt: string;
};

从 URL 获取内容并使用 AI 模型处理它。
​
WebSearch
工具名称： WebSearch
type WebSearchInput = {
  query: string;
  allowed_domains?: string[];
  blocked_domains?: string[];
};

搜索网络并返回格式化的结果。
​
TodoWrite
工具名称： TodoWrite
type TodoWriteInput = {
  todos: Array<{
    content: string;
    status: "pending" | "in_progress" | "completed";
    activeForm: string;
  }>;
};

创建和管理结构化任务列表以跟踪进度。
自 TypeScript Agent SDK 0.3.142 起，TodoWrite 默认被禁用。改用 TaskCreate、TaskGet、TaskUpdate 和 TaskList。请参阅迁移到 Task 工具以更新您的监视代码，或设置 CLAUDE_CODE_ENABLE_TASKS=0 以恢复为 TodoWrite。
​
TaskCreate
工具名称： TaskCreate
type TaskCreateInput = {
  subject: string;
  description: string;
  activeForm?: string;
  metadata?: Record<string, unknown>;
};

创建单个任务并返回其分配的 ID。
​
TaskUpdate
工具名称： TaskUpdate
type TaskUpdateInput = {
  taskId: string;
  status?: "pending" | "in_progress" | "completed" | "deleted";
  subject?: string;
  description?: string;
  activeForm?: string;
  addBlocks?: string[];
  addBlockedBy?: string[];
  owner?: string;
  metadata?: Record<string, unknown>;
};

按 ID 修补一个任务。将 status 设置为 "deleted" 以删除它。
​
TaskGet
工具名称： TaskGet
type TaskGetInput = {
  taskId: string;
};

返回一个任务的完整详情，或在找不到 ID 时返回 null。
​
TaskList
工具名称： TaskList
type TaskListInput = {};

返回当前列表中所有任务的快照。
​
ExitPlanMode
工具名称： ExitPlanMode
type ExitPlanModeInput = {
  allowedPrompts?: Array<{
    tool: "Bash";
    prompt: string;
  }>;
};

退出规划模式。可选地指定实现计划所需的基于提示的权限。
​
ListMcpResources
工具名称： ListMcpResources
type ListMcpResourcesInput = {
  server?: string;
};

列出来自连接服务器的可用 MCP 资源。
​
ReadMcpResource
工具名称： ReadMcpResource
type ReadMcpResourceInput = {
  server: string;
  uri: string;
};

从服务器读取特定的 MCP 资源。
​
EnterWorktree
工具名称： EnterWorktree
type EnterWorktreeInput = {
  name?: string;
  path?: string;
};

创建并进入临时 git worktree 以进行隔离工作。传递 path 以切换到当前存储库的现有 worktree 而不是创建新的。name 和 path 互斥。
​
工具输出类型
所有内置 Claude Code 工具的输出架构文档。这些类型从 @anthropic-ai/claude-agent-sdk 导出，代表每个工具返回的实际响应数据。
​
ToolOutputSchemas
所有工具输出类型的联合。
type ToolOutputSchemas =
  | AgentOutput
  | AskUserQuestionOutput
  | BashOutput
  | EnterWorktreeOutput
  | ExitPlanModeOutput
  | FileEditOutput
  | FileReadOutput
  | FileWriteOutput
  | GlobOutput
  | GrepOutput
  | ListMcpResourcesOutput
  | MonitorOutput
  | NotebookEditOutput
  | ReadMcpResourceOutput
  | TaskCreateOutput
  | TaskGetOutput
  | TaskListOutput
  | TaskStopOutput
  | TaskUpdateOutput
  | TodoWriteOutput
  | WebFetchOutput
  | WebSearchOutput;

​
Agent
工具名称： Agent（之前为 Task，仍然接受作为别名）
type AgentOutput =
  | {
      status: "completed";
      agentId: string;
      content: Array<{ type: "text"; text: string }>;
      totalToolUseCount: number;
      totalDurationMs: number;
      totalTokens: number;
      usage: {
        input_tokens: number;
        output_tokens: number;
        cache_creation_input_tokens: number | null;
        cache_read_input_tokens: number | null;
        server_tool_use: {
          web_search_requests: number;
          web_fetch_requests: number;
        } | null;
        service_tier: ("standard" | "priority" | "batch") | null;
        cache_creation: {
          ephemeral_1h_input_tokens: number;
          ephemeral_5m_input_tokens: number;
        } | null;
      };
      prompt: string;
    }
  | {
      status: "async_launched";
      agentId: string;
      description: string;
      prompt: string;
      outputFile: string;
      canReadOutputFile?: boolean;
    }
  | {
      status: "sub_agent_entered";
      description: string;
      message: string;
    };

返回来自子代理的结果。在 status 字段上进行区分："completed" 表示已完成的任务，"async_launched" 表示后台任务，"sub_agent_entered" 表示交互式子代理。
​
AskUserQuestion
工具名称： AskUserQuestion
type AskUserQuestionOutput = {
  questions: Array<{
    question: string;
    header: string;
    options: Array<{ label: string; description: string; preview?: string }>;
    multiSelect: boolean;
  }>;
  answers: Record<string, string>;
};

返回提出的问题和用户的答案。
​
Bash
工具名称： Bash
type BashOutput = {
  stdout: string;
  stderr: string;
  rawOutputPath?: string;
  interrupted: boolean;
  isImage?: boolean;
  backgroundTaskId?: string;
  backgroundedByUser?: boolean;
  dangerouslyDisableSandbox?: boolean;
  returnCodeInterpretation?: string;
  structuredContent?: unknown[];
  persistedOutputPath?: string;
  persistedOutputSize?: number;
};

返回命令输出，stdout/stderr 分开。后台命令包括 backgroundTaskId。
​
Monitor
工具名称： Monitor
type MonitorOutput = {
  taskId: string;
  timeoutMs: number;
  persistent?: boolean;
};

返回运行监视器的后台任务 ID。使用此 ID 与 TaskStop 一起提前取消监视。
​
Edit
工具名称： Edit
type FileEditOutput = {
  filePath: string;
  oldString: string;
  newString: string;
  originalFile: string;
  structuredPatch: Array<{
    oldStart: number;
    oldLines: number;
    newStart: number;
    newLines: number;
    lines: string[];
  }>;
  userModified: boolean;
  replaceAll: boolean;
  gitDiff?: {
    filename: string;
    status: "modified" | "added";
    additions: number;
    deletions: number;
    changes: number;
    patch: string;
  };
};

返回编辑操作的结构化差异。
​
Read
工具名称： Read
type FileReadOutput =
  | {
      type: "text";
      file: {
        filePath: string;
        content: string;
        numLines: number;
        startLine: number;
        totalLines: number;
      };
    }
  | {
      type: "image";
      file: {
        base64: string;
        type: "image/jpeg" | "image/png" | "image/gif" | "image/webp";
        originalSize: number;
        dimensions?: {
          originalWidth?: number;
          originalHeight?: number;
          displayWidth?: number;
          displayHeight?: number;
        };
      };
    }
  | {
      type: "notebook";
      file: {
        filePath: string;
        cells: unknown[];
      };
    }
  | {
      type: "pdf";
      file: {
        filePath: string;
        base64: string;
        originalSize: number;
      };
    }
  | {
      type: "parts";
      file: {
        filePath: string;
        originalSize: number;
        count: number;
        outputDir: string;
      };
    };

返回适合文件类型的格式的文件内容。在 type 字段上进行区分。
​
Write
工具名称： Write
type FileWriteOutput = {
  type: "create" | "update";
  filePath: string;
  content: string;
  structuredPatch: Array<{
    oldStart: number;
    oldLines: number;
    newStart: number;
    newLines: number;
    lines: string[];
  }>;
  originalFile: string | null;
  gitDiff?: {
    filename: string;
    status: "modified" | "added";
    additions: number;
    deletions: number;
    changes: number;
    patch: string;
  };
};

返回写入结果，包含结构化差异信息。
​
Glob
工具名称： Glob
type GlobOutput = {
  durationMs: number;
  numFiles: number;
  filenames: string[];
  truncated: boolean;
};

返回与 glob 模式匹配的文件路径，按修改时间排序。
​
Grep
工具名称： Grep
type GrepOutput = {
  mode?: "content" | "files_with_matches" | "count";
  numFiles: number;
  filenames: string[];
  content?: string;
  numLines?: number;
  numMatches?: number;
  appliedLimit?: number;
  appliedOffset?: number;
};

返回搜索结果。形状因 mode 而异：文件列表、带匹配的内容或匹配计数。
​
TaskStop
工具名称： TaskStop
type TaskStopOutput = {
  message: string;
  task_id: string;
  task_type: string;
  command?: string;
};

停止后台任务后返回确认。
​
NotebookEdit
工具名称： NotebookEdit
type NotebookEditOutput = {
  new_source: string;
  cell_id?: string;
  cell_type: "code" | "markdown";
  language: string;
  edit_mode: string;
  error?: string;
  notebook_path: string;
  original_file: string;
  updated_file: string;
};

返回笔记本编辑的结果，包含原始和更新的文件内容。
​
WebFetch
工具名称： WebFetch
type WebFetchOutput = {
  bytes: number;
  code: number;
  codeText: string;
  result: string;
  durationMs: number;
  url: string;
};

返回获取的内容，包含 HTTP 状态和元数据。
​
WebSearch
工具名称： WebSearch
type WebSearchOutput = {
  query: string;
  results: Array<
    | {
        tool_use_id: string;
        content: Array<{ title: string; url: string }>;
      }
    | string
  >;
  durationSeconds: number;
};

返回来自网络的搜索结果。
​
TodoWrite
工具名称： TodoWrite
type TodoWriteOutput = {
  oldTodos: Array<{
    content: string;
    status: "pending" | "in_progress" | "completed";
    activeForm: string;
  }>;
  newTodos: Array<{
    content: string;
    status: "pending" | "in_progress" | "completed";
    activeForm: string;
  }>;
};

返回之前和更新的任务列表。
自 TypeScript Agent SDK 0.3.142 起，TodoWrite 默认被禁用。改用 TaskCreate、TaskGet、TaskUpdate 和 TaskList。请参阅迁移到 Task 工具更新您的监视代码，或设置 CLAUDE_CODE_ENABLE_TASKS=0 以恢复为 TodoWrite。
​
TaskCreate
工具名称： TaskCreate
type TaskCreateOutput = {
  task: {
    id: string;
    subject: string;
  };
};

返回创建的任务及其分配的 ID。
​
TaskUpdate
工具名称： TaskUpdate
type TaskUpdateOutput = {
  success: boolean;
  taskId: string;
  updatedFields: string[];
  error?: string;
  statusChange?: {
    from: string;
    to: string;
  };
};

返回更新结果，包括哪些字段已更改。
​
TaskGet
工具名称： TaskGet
type TaskGetOutput = {
  task: {
    id: string;
    subject: string;
    description: string;
    status: "pending" | "in_progress" | "completed";
    blocks: string[];
    blockedBy: string[];
  } | null;
};

返回完整的任务记录，或在找不到 ID 时返回 null。
​
TaskList
工具名称： TaskList
type TaskListOutput = {
  tasks: Array<{
    id: string;
    subject: string;
    status: "pending" | "in_progress" | "completed";
    owner?: string;
    blockedBy: string[];
  }>;
};

返回当前列表中所有任务的快照。
​
ExitPlanMode
工具名称： ExitPlanMode
type ExitPlanModeOutput = {
  plan: string | null;
  isAgent: boolean;
  filePath?: string;
  hasTaskTool?: boolean;
  awaitingLeaderApproval?: boolean;
  requestId?: string;
};

返回退出规划模式后的计划状态。
​
ListMcpResources
工具名称： ListMcpResources
type ListMcpResourcesOutput = Array<{
  uri: string;
  name: string;
  mimeType?: string;
  description?: string;
  server: string;
}>;

返回可用 MCP 资源的数组。
​
ReadMcpResource
工具名称： ReadMcpResource
type ReadMcpResourceOutput = {
  contents: Array<{
    uri: string;
    mimeType?: string;
    text?: string;
  }>;
};

返回请求的 MCP 资源的内容。
​
EnterWorktree
工具名称： EnterWorktree
type EnterWorktreeOutput = {
  worktreePath: string;
  worktreeBranch?: string;
  message: string;
};

返回有关 git worktree 的信息。
​
权限类型
​
PermissionUpdate
用于更新权限的操作。
type PermissionUpdate =
  | {
      type: "addRules";
      rules: PermissionRuleValue[];
      behavior: PermissionBehavior;
      destination: PermissionUpdateDestination;
    }
  | {
      type: "replaceRules";
      rules: PermissionRuleValue[];
      behavior: PermissionBehavior;
      destination: PermissionUpdateDestination;
    }
  | {
      type: "removeRules";
      rules: PermissionRuleValue[];
      behavior: PermissionBehavior;
      destination: PermissionUpdateDestination;
    }
  | {
      type: "setMode";
      mode: PermissionMode;
      destination: PermissionUpdateDestination;
    }
  | {
      type: "addDirectories";
      directories: string[];
      destination: PermissionUpdateDestination;
    }
  | {
      type: "removeDirectories";
      directories: string[];
      destination: PermissionUpdateDestination;
    };

​
PermissionBehavior
type PermissionBehavior = "allow" | "deny" | "ask";

​
PermissionUpdateDestination
type PermissionUpdateDestination =
  | "userSettings" // 全局用户设置
  | "projectSettings" // 每个目录的项目设置
  | "localSettings" // Gitignored 本地设置
  | "session" // 仅当前会话
  | "cliArg"; // CLI 参数

​
PermissionRuleValue
type PermissionRuleValue = {
  toolName: string;
  ruleContent?: string;
};

​
其他类型
​
ApiKeySource
type ApiKeySource = "user" | "project" | "org" | "temporary" | "oauth";

​
SdkBeta
可通过 betas 选项启用的可用测试功能。请参阅 Beta 标头了解更多信息。
type SdkBeta = "context-1m-2025-08-07";

context-1m-2025-08-07 beta 自 2026 年 4 月 30 日起已停用。使用 Claude Sonnet 4.5 或 Sonnet 4 传递此值无效，超过标准 200k 令牌上下文窗口的请求返回错误。要使用 1M 令牌上下文窗口，请迁移到 Claude Sonnet 4.6、Claude Opus 4.6 或 Claude Opus 4.7，它们以标准定价包括 1M 上下文，无需 beta 标头。
​
SlashCommand
有关可用 slash command 的信息。
type SlashCommand = {
  name: string;
  description: string;
  argumentHint: string;
  aliases?: string[];
};

​
ModelInfo
有关可用模型的信息。
type ModelInfo = {
  value: string;
  displayName: string;
  description: string;
  supportsEffort?: boolean;
  supportedEffortLevels?: ("low" | "medium" | "high" | "xhigh" | "max")[];
  supportsAdaptiveThinking?: boolean;
  supportsFastMode?: boolean;
};

​
AgentInfo
有关可通过 Agent 工具调用的可用子代理的信息。
type AgentInfo = {
  name: string;
  description: string;
  model?: string;
};

字段	类型	描述
name	string	代理类型标识符（例如，"Explore"、"general-purpose"）
description	string	何时使用此代理的描述
model	string | undefined	此代理使用的模型别名。如果省略，继承父级的模型
​
McpServerStatus
连接的 MCP 服务器的状态。
type McpServerStatus = {
  name: string;
  status: "connected" | "failed" | "needs-auth" | "pending" | "disabled";
  serverInfo?: {
    name: string;
    version: string;
  };
  error?: string;
  config?: McpServerStatusConfig;
  scope?: string;
  tools?: {
    name: string;
    description?: string;
    annotations?: {
      readOnly?: boolean;
      destructive?: boolean;
      openWorld?: boolean;
    };
  }[];
};

​
McpServerStatusConfig
由 mcpServerStatus() 报告的 MCP 服务器的配置。这是所有 MCP 服务器传输类型的联合。
type McpServerStatusConfig =
  | McpStdioServerConfig
  | McpSSEServerConfig
  | McpHttpServerConfig
  | McpSdkServerConfig
  | McpClaudeAIProxyServerConfig;

请参阅 McpServerConfig了解每种传输类型的详情。
​
AccountInfo
经过身份验证的用户的帐户信息。
type AccountInfo = {
  email?: string;
  organization?: string;
  subscriptionType?: string;
  tokenSource?: string;
  apiKeySource?: string;
};

​
ModelUsage
结果消息中返回的每个模型使用统计。costUSD 值是客户端估计。请参阅跟踪成本和使用情况了解计费注意事项。
type ModelUsage = {
  inputTokens: number;
  outputTokens: number;
  cacheReadInputTokens: number;
  cacheCreationInputTokens: number;
  webSearchRequests: number;
  costUSD: number;
  contextWindow: number;
  maxOutputTokens: number;
};

​
ConfigScope
type ConfigScope = "local" | "user" | "project";

​
NonNullableUsage
Usage 的版本，所有可空字段都变为非可空。
type NonNullableUsage = {
  [K in keyof Usage]: NonNullable<Usage[K]>;
};

​
Usage
令牌使用统计。这是来自 @anthropic-ai/sdk 的 BetaUsage 类型。
type Usage = {
  input_tokens: number;
  output_tokens: number;
  cache_creation_input_tokens: number | null;
  cache_read_input_tokens: number | null;
  cache_creation: {
    ephemeral_5m_input_tokens: number;
    ephemeral_1h_input_tokens: number;
  } | null;
  server_tool_use: BetaServerToolUsage | null;
  service_tier: "standard" | "priority" | "batch" | null;
  speed: "standard" | "fast" | null;
  inference_geo: string | null;
  iterations: BetaIterationsUsage | null;
};

BetaServerToolUsage 和 BetaIterationsUsage 在 @anthropic-ai/sdk 中定义。
​
CallToolResult
MCP 工具结果类型（来自 @modelcontextprotocol/sdk/types.js）。structuredContent 是一个 JSON 对象，可以与 content 一起返回，包括图像块。请参阅返回结构化数据。
type CallToolResult = {
  content: Array<{
    type: "text" | "image" | "resource";
    // 其他字段因类型而异
  }>;
  structuredContent?: Record<string, unknown>;
  isError?: boolean;
};

​
ThinkingConfig
控制 Claude 的思考/推理行为。优先于已弃用的 maxThinkingTokens。
type ThinkingDisplay = "summarized" | "omitted";

type ThinkingConfig =
  | { type: "adaptive"; display?: ThinkingDisplay } // 模型确定何时以及多少推理（Opus 4.6+）
  | { type: "enabled"; budgetTokens?: number; display?: ThinkingDisplay } // 固定思考令牌预算
  | { type: "disabled" }; // 无扩展思考

可选的 display 字段控制思考文本是否以 "summarized" 或 "omitted" 形式返回。在 Claude Opus 4.7 及更高版本上，API 默认值为 "omitted"，因此设置 "summarized" 以在 thinking 块中接收思考内容。
​
SpawnedProcess
自定义进程生成的接口（与 spawnClaudeCodeProcess 选项一起使用）。ChildProcess 已满足此接口。
interface SpawnedProcess {
  stdin: Writable;
  stdout: Readable;
  readonly killed: boolean;
  readonly exitCode: number | null;
  kill(signal: NodeJS.Signals): boolean;
  on(
    event: "exit",
    listener: (code: number | null, signal: NodeJS.Signals | null) => void
  ): void;
  on(event: "error", listener: (error: Error) => void): void;
  once(
    event: "exit",
    listener: (code: number | null, signal: NodeJS.Signals | null) => void
  ): void;
  once(event: "error", listener: (error: Error) => void): void;
  off(
    event: "exit",
    listener: (code: number | null, signal: NodeJS.Signals | null) => void
  ): void;
  off(event: "error", listener: (error: Error) => void): void;
}

​
SpawnOptions
传递给自定义生成函数的选项。
interface SpawnOptions {
  command: string;
  args: string[];
  cwd?: string;
  env: Record<string, string | undefined>;
  signal: AbortSignal;
}

​
McpSetServersResult
setMcpServers() 操作的结果。
type McpSetServersResult = {
  added: string[];
  removed: string[];
  errors: Record<string, string>;
};

​
RewindFilesResult
rewindFiles() 操作的结果。
type RewindFilesResult = {
  canRewind: boolean;
  error?: string;
  filesChanged?: string[];
  insertions?: number;
  deletions?: number;
};

​
SDKStatusMessage
状态更新消息（例如，压缩）。
type SDKStatusMessage = {
  type: "system";
  subtype: "status";
  status: "compacting" | null;
  permissionMode?: PermissionMode;
  uuid: UUID;
  session_id: string;
};

​
SDKTaskNotificationMessage
后台任务完成、失败或停止时的通知。后台任务包括 run_in_background Bash 命令、Monitor 监视和后台子代理。
type SDKTaskNotificationMessage = {
  type: "system";
  subtype: "task_notification";
  task_id: string;
  tool_use_id?: string;
  status: "completed" | "failed" | "stopped";
  output_file: string;
  summary: string;
  usage?: {
    total_tokens: number;
    tool_uses: number;
    duration_ms: number;
  };
  uuid: UUID;
  session_id: string;
};

​
SDKToolUseSummaryMessage
对话中工具使用的摘要。
type SDKToolUseSummaryMessage = {
  type: "tool_use_summary";
  summary: string;
  preceding_tool_use_ids: string[];
  uuid: UUID;
  session_id: string;
};

​
SDKHookStartedMessage
当 hook 开始执行时发出。
type SDKHookStartedMessage = {
  type: "system";
  subtype: "hook_started";
  hook_id: string;
  hook_name: string;
  hook_event: string;
  uuid: UUID;
  session_id: string;
};

​
SDKHookProgressMessage
在 hook 运行时发出，包含 stdout/stderr 输出。
type SDKHookProgressMessage = {
  type: "system";
  subtype: "hook_progress";
  hook_id: string;
  hook_name: string;
  hook_event: string;
  stdout: string;
  stderr: string;
  output: string;
  uuid: UUID;
  session_id: string;
};

​
SDKHookResponseMessage
当 hook 完成执行时发出。
type SDKHookResponseMessage = {
  type: "system";
  subtype: "hook_response";
  hook_id: string;
  hook_name: string;
  hook_event: string;
  output: string;
  stdout: string;
  stderr: string;
  exit_code?: number;
  outcome: "success" | "error" | "cancelled";
  uuid: UUID;
  session_id: string;
};

​
SDKToolProgressMessage
在工具执行时定期发出，以指示进度。
type SDKToolProgressMessage = {
  type: "tool_progress";
  tool_use_id: string;
  tool_name: string;
  parent_tool_use_id: string | null;
  elapsed_time_seconds: number;
  task_id?: string;
  uuid: UUID;
  session_id: string;
};

​
SDKAuthStatusMessage
在身份验证流程中发出。
type SDKAuthStatusMessage = {
  type: "auth_status";
  isAuthenticating: boolean;
  output: string[];
  error?: string;
  uuid: UUID;
  session_id: string;
};

​
SDKTaskStartedMessage
当后台任务开始时发出。task_type 字段对于后台 Bash 命令和 Monitor 监视为 "local_bash"，对于子代理为 "local_agent"，或 "remote_agent"。
type SDKTaskStartedMessage = {
  type: "system";
  subtype: "task_started";
  task_id: string;
  tool_use_id?: string;
  description: string;
  task_type?: string;
  uuid: UUID;
  session_id: string;
};

​
SDKTaskProgressMessage
在子代理或后台任务运行时定期发出。仅当启用 agentProgressSummaries 时，summary 字段才会被填充。
type SDKTaskProgressMessage = {
  type: "system";
  subtype: "task_progress";
  task_id: string;
  tool_use_id?: string;
  description: string;
  subagent_type?: string;
  usage: {
    total_tokens: number;
    tool_uses: number;
    duration_ms: number;
  };
  last_tool_name?: string;
  summary?: string;
  uuid: UUID;
  session_id: string;
};

​
SDKTaskUpdatedMessage
当后台任务的状态发生变化时发出，例如当它从 running 转换为 completed 时。将 patch 合并到按 task_id 键入的本地任务映射中。end_time 字段是 Unix 纪元时间戳（以毫秒为单位），可与 Date.now() 比较。
type SDKTaskUpdatedMessage = {
  type: "system";
  subtype: "task_updated";
  task_id: string;
  patch: {
    status?: "pending" | "running" | "completed" | "failed" | "killed";
    description?: string;
    end_time?: number;
    total_paused_ms?: number;
    error?: string;
    is_backgrounded?: boolean;
  };
  uuid: UUID;
  session_id: string;
};

​
SDKFilesPersistedEvent
当文件检查点持久化到磁盘时发出。
type SDKFilesPersistedEvent = {
  type: "system";
  subtype: "files_persisted";
  files: { filename: string; file_id: string }[];
  failed: { filename: string; error: string }[];
  processed_at: string;
  uuid: UUID;
  session_id: string;
};

​
SDKRateLimitEvent
当会话遇到速率限制时发出。
type SDKRateLimitEvent = {
  type: "rate_limit_event";
  rate_limit_info: {
    status: "allowed" | "allowed_warning" | "rejected";
    resetsAt?: number;
    utilization?: number;
  };
  uuid: UUID;
  session_id: string;
};

​
SDKLocalCommandOutputMessage
来自本地 slash command 的输出（例如，/voice 或 /usage）。在记录中显示为助手样式的文本。
type SDKLocalCommandOutputMessage = {
  type: "system";
  subtype: "local_command_output";
  content: string;
  uuid: UUID;
  session_id: string;
};

​
SDKPromptSuggestionMessage
当启用 promptSuggestions 时在每个轮次后发出。包含预测的下一个用户提示。
type SDKPromptSuggestionMessage = {
  type: "prompt_suggestion";
  suggestion: string;
  uuid: UUID;
  session_id: string;
};

​
AbortError
用于中止操作的自定义错误类。
class AbortError extends Error {}

​
沙箱配置
​
SandboxSettings
沙箱行为的配置。使用此选项以编程方式启用命令沙箱和配置网络限制。
type SandboxSettings = {
  enabled?: boolean;
  autoAllowBashIfSandboxed?: boolean;
  excludedCommands?: string[];
  allowUnsandboxedCommands?: boolean;
  network?: SandboxNetworkConfig;
  filesystem?: SandboxFilesystemConfig;
  ignoreViolations?: Record<string, string[]>;
  enableWeakerNestedSandbox?: boolean;
  ripgrep?: { command: string; args?: string[] };
};

属性	类型	默认值	描述
enabled	boolean	false	为命令执行启用沙箱模式
autoAllowBashIfSandboxed	boolean	true	启用沙箱时自动批准 bash 命令
excludedCommands	string[]	[]	始终绕过沙箱限制的命令（例如，['docker']）。这些自动运行在沙箱外，无需模型参与
allowUnsandboxedCommands	boolean	true	允许模型请求在沙箱外运行命令。当为 true 时，模型可以在工具输入中设置 dangerouslyDisableSandbox，这会回退到权限系统
network	SandboxNetworkConfig	undefined	网络特定的沙箱配置
filesystem	SandboxFilesystemConfig	undefined	用于读/写限制的文件系统特定沙箱配置
ignoreViolations	Record<string, string[]>	undefined	违规类别到要忽略的模式的映射（例如，{ file: ['/tmp/*'], network: ['localhost'] }）
enableWeakerNestedSandbox	boolean	false	为兼容性启用较弱的嵌套沙箱
ripgrep	{ command: string; args?: string[] }	undefined	沙箱环境中的自定义 ripgrep 二进制配置
​
示例用法
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Build and test my project",
  options: {
    sandbox: {
      enabled: true,
      autoAllowBashIfSandboxed: true,
      network: {
        allowLocalBinding: true
      }
    }
  }
})) {
  if ("result" in message) console.log(message.result);
}

Unix socket 安全性： allowUnixSockets 选项可以授予对强大系统服务的访问权限。例如，允许 /var/run/docker.sock 实际上通过 Docker API 授予对主机系统的完全访问权限，绕过沙箱隔离。仅允许严格必要的 Unix sockets 并了解每个的安全含义。
​
SandboxNetworkConfig
沙箱模式的网络特定配置。
type SandboxNetworkConfig = {
  allowedDomains?: string[];
  deniedDomains?: string[];
  allowManagedDomainsOnly?: boolean;
  allowLocalBinding?: boolean;
  allowUnixSockets?: string[];
  allowAllUnixSockets?: boolean;
  httpProxyPort?: number;
  socksProxyPort?: number;
};

属性	类型	默认值	描述
allowedDomains	string[]	[]	沙箱进程可以访问的域名
deniedDomains	string[]	[]	沙箱进程无法访问的域名。优先于 allowedDomains
allowManagedDomainsOnly	boolean	false	仅限管理设置。在管理设置中设置时，仅遵守来自管理设置的 allowedDomains 条目，来自用户、项目或本地设置的条目被忽略。通过 SDK 选项设置时无效
allowLocalBinding	boolean	false	允许进程绑定到本地端口（例如，用于开发服务器）
allowUnixSockets	string[]	[]	进程可以访问的 Unix socket 路径（例如，Docker socket）
allowAllUnixSockets	boolean	false	允许访问所有 Unix sockets
httpProxyPort	number	undefined	网络请求的 HTTP 代理端口
socksProxyPort	number	undefined	网络请求的 SOCKS 代理端口
内置沙箱代理基于请求的主机名强制执行 allowedDomains，不会终止或检查 TLS 流量，因此域前置等技术可能会绕过它。有关详细信息，请参阅沙箱安全限制，以及安全部署以配置 TLS 终止代理。
​
SandboxFilesystemConfig
沙箱模式的文件系统特定配置。
type SandboxFilesystemConfig = {
  allowWrite?: string[];
  denyWrite?: string[];
  denyRead?: string[];
};

属性	类型	默认值	描述
allowWrite	string[]	[]	允许写入访问的文件路径模式
denyWrite	string[]	[]	拒绝写入访问的文件路径模式
denyRead	string[]	[]	拒绝读取访问的文件路径模式
​
沙箱外命令的权限回退
启用 allowUnsandboxedCommands 时，模型可以通过在工具输入中设置 dangerouslyDisableSandbox: true 来请求在沙箱外运行命令。这些请求回退到现有权限系统，意味着您的 canUseTool 处理程序被调用，允许您实现自定义授权逻辑。
excludedCommands vs allowUnsandboxedCommands：
excludedCommands：始终自动绕过沙箱的命令的静态列表（例如，['docker']）。模型对此无法控制。
allowUnsandboxedCommands：让模型在运行时通过在工具输入中设置 dangerouslyDisableSandbox: true 来决定是否请求沙箱外执行。
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Deploy my application",
  options: {
    sandbox: {
      enabled: true,
      allowUnsandboxedCommands: true // 模型可以请求沙箱外执行
    },
    permissionMode: "default",
    canUseTool: async (tool, input) => {
      // 检查模型是否请求绕过沙箱
      if (tool === "Bash" && input.dangerouslyDisableSandbox) {
        // 模型请求在沙箱外运行此命令
        console.log(`Unsandboxed command requested: ${input.command}`);

        if (isCommandAuthorized(input.command)) {
          return { behavior: "allow" as const, updatedInput: input };
        }
        return {
          behavior: "deny" as const,
          message: "Command not authorized for unsandboxed execution"
        };
      }
      return { behavior: "allow" as const, updatedInput: input };
    }
  }
})) {
  if ("result" in message) console.log(message.result);
}

此模式使您能够：
审计模型请求： 记录模型何时请求沙箱外执行
实现允许列表： 仅允许特定命令在沙箱外运行
添加批准工作流： 需要对特权操作进行明确授权
使用 dangerouslyDisableSandbox: true 运行的命令具有完整的系统访问权限。确保您的 canUseTool 处理程序仔细验证这些请求。
如果 permissionMode 设置为 bypassPermissions 且 allowUnsandboxedCommands 启用，模型可以自主执行沙箱外的命令，无需任何批准提示。此组合实际上允许模型以静默方式逃离沙箱隔离。
​
另请参阅
SDK 概述 - 常规 SDK 概念
Python SDK 参考 - Python SDK 文档
CLI 参考 - 命令行界面
常见工作流 - 分步指南

此页面对您有帮助吗？

是
否
Secure deployment
TypeScript V2（已移除）
⌘I

---

# TypeScript V2（已移除）

> 章节: SDK 参考 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/typescript-v2-preview

---

SDK 参考
TypeScript SDK V2 session API（已移除）

已移除的 V2 TypeScript Agent SDK session API 参考，具有用于多轮对话的基于会话的 send/stream 模式。

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

V2 session API 不再受支持。TypeScript Agent SDK 0.3.142 移除了 unstable_v2_createSession、unstable_v2_resumeSession、unstable_v2_prompt 以及 SDKSession 和 SDKSessionOptions 类型。
要迁移，请使用 query() API 和它接受的 session 选项。为多轮对话传递 AsyncIterable<SDKUserMessage>，或使用 options.resume 继续已保存的会话。如果您在 Agent SDK 0.2.x 或更早版本上维护代码，此页面保留供参考。
V2 是一个实验性的 session API，消除了对异步生成器和 yield 协调的需求。与其在各轮之间管理生成器状态，每一轮都是一个单独的 send()/stream() 周期。API 表面简化为三个概念：
createSession() / resumeSession()：启动或继续对话
session.send()：发送消息
session.stream()：获取响应
​
安装
Agent SDK 0.2.x 是包含 V2 interface 的最后一个版本。包版本从 0.2.x 直接跳到 0.3.142，因此上面的移除版本和下面的安装固定版本描述的是同一个边界。要安装最后一个 V2 兼容版本，请固定主版本号和次版本号：
npm install @anthropic-ai/claude-agent-sdk@0.2

SDK 为您的平台捆绑了一个本地 Claude Code 二进制文件作为可选依赖项，因此您无需单独安装 Claude Code。
​
快速开始
​
单次提示
对于不需要维护会话的简单单轮查询，使用 unstable_v2_prompt()。此示例发送一个数学问题并记录答案：
import { unstable_v2_prompt } from "@anthropic-ai/claude-agent-sdk";

const result = await unstable_v2_prompt("What is 2 + 2?", {
  model: "claude-opus-4-7"
});
if (result.subtype === "success") {
  console.log(result.result);
}

​
基本会话
对于超出单个提示的交互，创建一个会话。V2 将发送和流式传输分为不同的步骤：
send() 分派您的消息
stream() 流式传输响应
这种明确的分离使得在轮次之间添加逻辑变得更容易（例如在发送后续消息之前处理响应）。
下面的示例创建一个会话，向 Claude 发送”Hello!”，并打印文本响应。它使用 await using（TypeScript 5.2+）在块退出时自动关闭会话。您也可以手动调用 session.close()。
import { unstable_v2_createSession } from "@anthropic-ai/claude-agent-sdk";

await using session = unstable_v2_createSession({
  model: "claude-opus-4-7"
});

await session.send("Hello!");
for await (const msg of session.stream()) {
  // Filter for assistant messages to get human-readable output
  if (msg.type === "assistant") {
    const text = msg.message.content
      .filter((block) => block.type === "text")
      .map((block) => block.text)
      .join("");
    console.log(text);
  }
}

​
多轮对话
会话在多个交换中保持上下文。要继续对话，请在同一会话上再次调用 send()。Claude 会记住之前的轮次。
此示例提出一个数学问题，然后提出一个引用前一个答案的后续问题：
import { unstable_v2_createSession } from "@anthropic-ai/claude-agent-sdk";

await using session = unstable_v2_createSession({
  model: "claude-opus-4-7"
});

// Turn 1
await session.send("What is 5 + 3?");
for await (const msg of session.stream()) {
  // Filter for assistant messages to get human-readable output
  if (msg.type === "assistant") {
    const text = msg.message.content
      .filter((block) => block.type === "text")
      .map((block) => block.text)
      .join("");
    console.log(text);
  }
}

// Turn 2
await session.send("Multiply that by 2");
for await (const msg of session.stream()) {
  if (msg.type === "assistant") {
    const text = msg.message.content
      .filter((block) => block.type === "text")
      .map((block) => block.text)
      .join("");
    console.log(text);
  }
}

​
会话恢复
如果您有来自之前交互的会话 ID，您可以稍后恢复它。这对于长时间运行的工作流或当您需要在应用程序重新启动时保持对话时很有用。
此示例创建一个会话，存储其 ID，关闭它，然后恢复对话：
import {
  unstable_v2_createSession,
  unstable_v2_resumeSession,
  type SDKMessage
} from "@anthropic-ai/claude-agent-sdk";

// Helper to extract text from assistant messages
function getAssistantText(msg: SDKMessage): string | null {
  if (msg.type !== "assistant") return null;
  return msg.message.content
    .filter((block) => block.type === "text")
    .map((block) => block.text)
    .join("");
}

// Create initial session and have a conversation
const session = unstable_v2_createSession({
  model: "claude-opus-4-7"
});

await session.send("Remember this number: 42");

// Get the session ID from any received message
let sessionId: string | undefined;
for await (const msg of session.stream()) {
  sessionId = msg.session_id;
  const text = getAssistantText(msg);
  if (text) console.log("Initial response:", text);
}

console.log("Session ID:", sessionId);
session.close();

// Later: resume the session using the stored ID
await using resumedSession = unstable_v2_resumeSession(sessionId!, {
  model: "claude-opus-4-7"
});

await resumedSession.send("What number did I ask you to remember?");
for await (const msg of resumedSession.stream()) {
  const text = getAssistantText(msg);
  if (text) console.log("Resumed response:", text);
}

​
清理
会话可以手动关闭或使用 await using（TypeScript 5.2+ 功能用于自动资源清理）自动关闭。如果您使用的是较旧的 TypeScript 版本或遇到兼容性问题，请改用手动清理。
自动清理（TypeScript 5.2+）：
import { unstable_v2_createSession } from "@anthropic-ai/claude-agent-sdk";

await using session = unstable_v2_createSession({
  model: "claude-opus-4-7"
});
// Session closes automatically when the block exits

手动清理：
import { unstable_v2_createSession } from "@anthropic-ai/claude-agent-sdk";

const session = unstable_v2_createSession({
  model: "claude-opus-4-7"
});
// ... use the session ...
session.close();

​
API 参考
​
unstable_v2_createSession()
为多轮对话创建新会话。
function unstable_v2_createSession(options: {
  model: string;
  // Additional options supported
}): SDKSession;

​
unstable_v2_resumeSession()
按 ID 恢复现有会话。
function unstable_v2_resumeSession(
  sessionId: string,
  options: {
    model: string;
    // Additional options supported
  }
): SDKSession;

​
unstable_v2_prompt()
用于单轮查询的单次便利函数。
function unstable_v2_prompt(
  prompt: string,
  options: {
    model: string;
    // Additional options supported
  }
): Promise<SDKResultMessage>;

​
SDKSession interface
interface SDKSession {
  readonly sessionId: string;
  send(message: string | SDKUserMessage): Promise<void>;
  stream(): AsyncGenerator<SDKMessage, void>;
  close(): void;
}

​
功能可用性
V2 session API 不支持所有 V1 功能。以下功能需要使用 V1 SDK：
会话分叉（forkSession 选项）
某些高级流式输入模式
​
另请参阅
TypeScript SDK 参考（V1） - 完整的 V1 SDK 文档
SDK 概述 - 常规 SDK 概念
GitHub 上的 V2 示例 - 工作代码示例

此页面对您有帮助吗？

是
否
TypeScript SDK
Python SDK
⌘I

---

# Python SDK

> 章节: SDK 参考 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/python

---

SDK 参考
Agent SDK 参考 - Python

Python Agent SDK 的完整 API 参考，包括所有函数、类型和类。

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

​
安装
pip install claude-agent-sdk

​
在 query() 和 ClaudeSDKClient 之间选择
Python SDK 提供了两种与 Claude Code 交互的方式：
​
快速比较
功能	query()	ClaudeSDKClient
会话	默认创建新会话	重用同一会话
对话	单次交换	同一上下文中的多次交换
连接	自动管理	手动控制
流式输入	✅ 支持	✅ 支持
中断	❌ 不支持	✅ 支持
hooks	✅ 支持	✅ 支持
自定义工具	✅ 支持	✅ 支持
继续聊天	通过 continue_conversation 或 resume 手动进行	✅ 自动
用例	一次性任务	持续对话
​
何时使用 query()（一次性任务）
最适合：
不需要对话历史的一次性问题
不需要来自之前交换的上下文的独立任务
简单的自动化脚本
当你想每次都重新开始时
​
何时使用 ClaudeSDKClient（持续对话）
最适合：
继续对话 - 当你需要 Claude 记住上下文时
后续问题 - 基于之前的响应进行构建
交互式应用程序 - 聊天界面、REPL
响应驱动的逻辑 - 当下一步操作取决于 Claude 的响应时
会话控制 - 显式管理对话生命周期
​
函数
​
query()
为每次与 Claude Code 的交互创建一个新会话。默认情况下返回一个异步迭代器，当消息到达时产生消息。每次调用 query() 都会重新开始，不记得之前的交互，除非你传递 continue_conversation=True 或在 ClaudeAgentOptions 中传递 resume。参见 Sessions。
async def query(
    *,
    prompt: str | AsyncIterable[dict[str, Any]],
    options: ClaudeAgentOptions | None = None,
    transport: Transport | None = None
) -> AsyncIterator[Message]

​
参数
参数	类型	描述
prompt	str | AsyncIterable[dict]	输入提示，可以是字符串或用于流式模式的异步可迭代对象
options	ClaudeAgentOptions | None	可选配置对象（如果为 None，默认为 ClaudeAgentOptions()）
transport	Transport | None	用于与 CLI 进程通信的可选自定义传输
​
返回
返回一个 AsyncIterator[Message]，从对话中产生消息。
​
示例 - 带选项
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def main():
    options = ClaudeAgentOptions(
        system_prompt="You are an expert Python developer",
        permission_mode="acceptEdits",
        cwd="/home/user/project",
    )

    async for message in query(prompt="Create a Python web server", options=options):
        print(message)


asyncio.run(main())

​
tool()
用于定义具有类型安全的 MCP 工具的装饰器。
def tool(
    name: str,
    description: str,
    input_schema: type | dict[str, Any],
    annotations: ToolAnnotations | None = None
) -> Callable[[Callable[[Any], Awaitable[dict[str, Any]]]], SdkMcpTool[Any]]

​
参数
参数	类型	描述
name	str	工具的唯一标识符
description	str	工具功能的人类可读描述
input_schema	type | dict[str, Any]	定义工具输入参数的模式（见下文）
annotations	ToolAnnotations | None	可选的 MCP 工具注解，为客户端提供行为提示
​
输入模式选项
简单类型映射（推荐）：
{"text": str, "count": int, "enabled": bool}

JSON Schema 格式（用于复杂验证）：
{
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "count": {"type": "integer", "minimum": 0},
    },
    "required": ["text"],
}

​
返回
一个装饰器函数，包装工具实现并返回一个 SdkMcpTool 实例。
​
示例
from claude_agent_sdk import tool
from typing import Any


@tool("greet", "Greet a user", {"name": str})
async def greet(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": f"Hello, {args['name']}!"}]}

​
ToolAnnotations
从 mcp.types 重新导出（也可以从 claude_agent_sdk 导入为 from claude_agent_sdk import ToolAnnotations）。所有字段都是可选的提示；客户端不应依赖它们做出安全决策。
字段	类型	默认值	描述
title	str | None	None	工具的人类可读标题
readOnlyHint	bool | None	False	如果为 True，工具不修改其环境
destructiveHint	bool | None	True	如果为 True，工具可能执行破坏性更新（仅当 readOnlyHint 为 False 时有意义）
idempotentHint	bool | None	False	如果为 True，使用相同参数的重复调用没有额外效果（仅当 readOnlyHint 为 False 时有意义）
openWorldHint	bool | None	True	如果为 True，工具与外部实体交互（例如网络搜索）。如果为 False，工具的域是封闭的（例如内存工具）
from claude_agent_sdk import tool, ToolAnnotations
from typing import Any


@tool(
    "search",
    "Search the web",
    {"query": str},
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def search(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": f"Results for: {args['query']}"}]}

​
create_sdk_mcp_server()
创建在 Python 应用程序中运行的进程内 MCP 服务器。
def create_sdk_mcp_server(
    name: str,
    version: str = "1.0.0",
    tools: list[SdkMcpTool[Any]] | None = None
) -> McpSdkServerConfig

​
参数
参数	类型	默认值	描述
name	str	-	服务器的唯一标识符
version	str	"1.0.0"	服务器版本字符串
tools	list[SdkMcpTool[Any]] | None	None	使用 @tool 装饰器创建的工具函数列表
​
返回
返回一个 McpSdkServerConfig 对象，可以传递给 ClaudeAgentOptions.mcp_servers。
​
示例
from claude_agent_sdk import tool, create_sdk_mcp_server


@tool("add", "Add two numbers", {"a": float, "b": float})
async def add(args):
    return {"content": [{"type": "text", "text": f"Sum: {args['a'] + args['b']}"}]}


@tool("multiply", "Multiply two numbers", {"a": float, "b": float})
async def multiply(args):
    return {"content": [{"type": "text", "text": f"Product: {args['a'] * args['b']}"}]}


calculator = create_sdk_mcp_server(
    name="calculator",
    version="2.0.0",
    tools=[add, multiply],  # Pass decorated functions
)

# Use with Claude
options = ClaudeAgentOptions(
    mcp_servers={"calc": calculator},
    allowed_tools=["mcp__calc__add", "mcp__calc__multiply"],
)

​
list_sessions()
列出带有元数据的过去会话。按项目目录过滤或列出所有项目中的会话。同步；立即返回。
def list_sessions(
    directory: str | None = None,
    limit: int | None = None,
    include_worktrees: bool = True
) -> list[SDKSessionInfo]

​
参数
参数	类型	默认值	描述
directory	str | None	None	列出会话的目录。省略时，返回所有项目中的会话
limit	int | None	None	返回的最大会话数
include_worktrees	bool	True	当 directory 在 git 仓库内时，包括所有 worktrees 路径中的会话
​
返回类型：SDKSessionInfo
属性	类型	描述
session_id	str	唯一会话标识符
summary	str	显示标题：自定义标题、自动生成的摘要或第一个提示
last_modified	int	上次修改时间（自纪元以来的毫秒数）
file_size	int | None	会话文件大小（字节）（远程存储后端为 None）
custom_title	str | None	用户设置的会话标题
first_prompt	str | None	会话中的第一个有意义的用户提示
git_branch	str | None	会话结束时的 Git 分支
cwd	str | None	会话的工作目录
tag	str | None	用户设置的会话标签（见 tag_session()）
created_at	int | None	会话创建时间（自纪元以来的毫秒数）
​
示例
打印项目的 10 个最近会话。结果按 last_modified 降序排序，所以第一项是最新的。省略 directory 以搜索所有项目。
from claude_agent_sdk import list_sessions

for session in list_sessions(directory="/path/to/project", limit=10):
    print(f"{session.summary} ({session.session_id})")

​
get_session_messages()
从过去的会话中检索消息。同步；立即返回。
def get_session_messages(
    session_id: str,
    directory: str | None = None,
    limit: int | None = None,
    offset: int = 0
) -> list[SessionMessage]

​
参数
参数	类型	默认值	描述
session_id	str	必需	要检索消息的会话 ID
directory	str | None	None	要查看的项目目录。省略时，搜索所有项目
limit	int | None	None	返回的最大消息数
offset	int	0	从开始跳过的消息数
​
返回类型：SessionMessage
属性	类型	描述
type	Literal["user", "assistant"]	消息角色
uuid	str	唯一消息标识符
session_id	str	会话标识符
message	Any	原始消息内容
parent_tool_use_id	None	保留供将来使用
​
示例
from claude_agent_sdk import list_sessions, get_session_messages

sessions = list_sessions(limit=1)
if sessions:
    messages = get_session_messages(sessions[0].session_id)
    for msg in messages:
        print(f"[{msg.type}] {msg.uuid}")

​
get_session_info()
按 ID 读取单个会话的元数据，无需扫描完整项目目录。同步；立即返回。
def get_session_info(
    session_id: str,
    directory: str | None = None,
) -> SDKSessionInfo | None

​
参数
参数	类型	默认值	描述
session_id	str	必需	要查找的会话的 UUID
directory	str | None	None	项目目录路径。省略时，搜索所有项目目录
返回 SDKSessionInfo，如果找不到会话则返回 None。
​
示例
查找单个会话的元数据，无需扫描项目目录。当你已经从之前的运行中获得会话 ID 时很有用。
from claude_agent_sdk import get_session_info

info = get_session_info("550e8400-e29b-41d4-a716-446655440000")
if info:
    print(f"{info.summary} (branch: {info.git_branch}, tag: {info.tag})")

​
rename_session()
通过追加自定义标题条目来重命名会话。重复调用是安全的；最新的标题获胜。同步。
def rename_session(
    session_id: str,
    title: str,
    directory: str | None = None,
) -> None

​
参数
参数	类型	默认值	描述
session_id	str	必需	要重命名的会话的 UUID
title	str	必需	新标题。去除空格后必须非空
directory	str | None	None	项目目录路径。省略时，搜索所有项目目录
如果 session_id 不是有效的 UUID 或 title 为空，则抛出 ValueError；如果找不到会话，则抛出 FileNotFoundError。
​
示例
重命名最近的会话，使其更容易找到。新标题在后续读取时出现在 SDKSessionInfo.custom_title 中。
from claude_agent_sdk import list_sessions, rename_session

sessions = list_sessions(directory="/path/to/project", limit=1)
if sessions:
    rename_session(sessions[0].session_id, "Refactor auth module")

​
tag_session()
标记会话。传递 None 以清除标签。重复调用是安全的；最新的标签获胜。同步。
def tag_session(
    session_id: str,
    tag: str | None,
    directory: str | None = None,
) -> None

​
参数
参数	类型	默认值	描述
session_id	str	必需	要标记的会话的 UUID
tag	str | None	必需	标签字符串，或 None 以清除。存储前进行 Unicode 清理
directory	str | None	None	项目目录路径。省略时，搜索所有项目目录
如果 session_id 不是有效的 UUID 或 tag 在清理后为空，则抛出 ValueError；如果找不到会话，则抛出 FileNotFoundError。
​
示例
标记会话，然后在稍后的读取中按该标签过滤。传递 None 以清除现有标签。
from claude_agent_sdk import list_sessions, tag_session

# Tag a session
tag_session("550e8400-e29b-41d4-a716-446655440000", "needs-review")

# Later: find all sessions with that tag
for session in list_sessions(directory="/path/to/project"):
    if session.tag == "needs-review":
        print(session.summary)

​
类
​
ClaudeSDKClient
在多次交换中维持对话会话。 这是 TypeScript SDK 的 query() 函数内部工作方式的 Python 等价物 - 它创建一个可以继续对话的客户端对象。
​
关键特性
会话连续性：在多个 query() 调用中维持对话上下文
同一对话：会话保留之前的消息
中断支持：可以在任务中途停止执行
显式生命周期：你控制会话何时开始和结束
响应驱动的流程：可以对响应做出反应并发送后续消息
自定义工具和 hooks：支持自定义工具（使用 @tool 装饰器创建）和 hooks
class ClaudeSDKClient:
    def __init__(self, options: ClaudeAgentOptions | None = None, transport: Transport | None = None)
    async def connect(self, prompt: str | AsyncIterable[dict] | None = None) -> None
    async def query(self, prompt: str | AsyncIterable[dict], session_id: str = "default") -> None
    async def receive_messages(self) -> AsyncIterator[Message]
    async def receive_response(self) -> AsyncIterator[Message]
    async def interrupt(self) -> None
    async def set_permission_mode(self, mode: str) -> None
    async def set_model(self, model: str | None = None) -> None
    async def rewind_files(self, user_message_id: str) -> None
    async def get_mcp_status(self) -> McpStatusResponse
    async def reconnect_mcp_server(self, server_name: str) -> None
    async def toggle_mcp_server(self, server_name: str, enabled: bool) -> None
    async def stop_task(self, task_id: str) -> None
    async def get_server_info(self) -> dict[str, Any] | None
    async def disconnect(self) -> None

​
方法
方法	描述
__init__(options)	使用可选配置初始化客户端
connect(prompt)	连接到 Claude，可选初始提示或消息流
query(prompt, session_id)	以流式模式发送新请求
receive_messages()	以异步迭代器形式接收来自 Claude 的所有消息
receive_response()	接收消息直到并包括 ResultMessage
interrupt()	发送中断信号（仅在流式模式下工作）
set_permission_mode(mode)	更改当前会话的权限模式
set_model(model)	更改当前会话的模型。传递 None 以重置为默认值
rewind_files(user_message_id)	将文件恢复到指定用户消息时的状态。需要 enable_file_checkpointing=True。见 文件检查点
get_mcp_status()	获取所有配置的 MCP 服务器的状态。返回 McpStatusResponse
reconnect_mcp_server(server_name)	重试连接到失败或断开连接的 MCP 服务器
toggle_mcp_server(server_name, enabled)	在会话中启用或禁用 MCP 服务器。禁用会移除其工具
stop_task(task_id)	停止运行的后台任务。一个状态为 "stopped" 的 TaskNotificationMessage 随后在消息流中出现
get_server_info()	获取服务器信息，包括会话 ID 和功能
disconnect()	从 Claude 断开连接
​
上下文管理器支持
客户端可以用作异步上下文管理器以自动管理连接：
async with ClaudeSDKClient() as client:
    await client.query("Hello Claude")
    async for message in client.receive_response():
        print(message)

重要： 迭代消息时，避免使用 break 提前退出，因为这可能导致 asyncio 清理问题。相反，让迭代自然完成或使用标志来跟踪何时找到了你需要的内容。
​
示例 - 继续对话
import asyncio
from claude_agent_sdk import ClaudeSDKClient, AssistantMessage, TextBlock, ResultMessage


async def main():
    async with ClaudeSDKClient() as client:
        # First question
        await client.query("What's the capital of France?")

        # Process response
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"Claude: {block.text}")

        # Follow-up question - the session retains the previous context
        await client.query("What's the population of that city?")

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"Claude: {block.text}")

        # Another follow-up - still in the same conversation
        await client.query("What are some famous landmarks there?")

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"Claude: {block.text}")


asyncio.run(main())

​
示例 - 使用 ClaudeSDKClient 进行流式输入
import asyncio
from claude_agent_sdk import ClaudeSDKClient


async def message_stream():
    """Generate messages dynamically."""
    yield {
        "type": "user",
        "message": {"role": "user", "content": "Analyze the following data:"},
    }
    await asyncio.sleep(0.5)
    yield {
        "type": "user",
        "message": {"role": "user", "content": "Temperature: 25°C, Humidity: 60%"},
    }
    await asyncio.sleep(0.5)
    yield {
        "type": "user",
        "message": {"role": "user", "content": "What patterns do you see?"},
    }


async def main():
    async with ClaudeSDKClient() as client:
        # Stream input to Claude
        await client.query(message_stream())

        # Process response
        async for message in client.receive_response():
            print(message)

        # Follow-up in same session
        await client.query("Should we be concerned about these readings?")

        async for message in client.receive_response():
            print(message)


asyncio.run(main())

​
示例 - 使用中断
import asyncio
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, ResultMessage


async def interruptible_task():
    options = ClaudeAgentOptions(allowed_tools=["Bash"], permission_mode="acceptEdits")

    async with ClaudeSDKClient(options=options) as client:
        # Start a long-running task
        await client.query("Count from 1 to 100 slowly, using the bash sleep command")

        # Let it run for a bit
        await asyncio.sleep(2)

        # Interrupt the task
        await client.interrupt()
        print("Task interrupted!")

        # Drain the interrupted task's messages (including its ResultMessage)
        async for message in client.receive_response():
            if isinstance(message, ResultMessage):
                print(f"Interrupted task finished with subtype={message.subtype!r}")
                # subtype is "error_during_execution" for interrupted tasks

        # Send a new command
        await client.query("Just say hello instead")

        # Now receive the new response
        async for message in client.receive_response():
            if isinstance(message, ResultMessage) and message.subtype == "success":
                print(f"New result: {message.result}")


asyncio.run(interruptible_task())

中断后的缓冲行为： interrupt() 发送停止信号但不清除消息缓冲区。被中断任务已产生的消息，包括其 ResultMessage（带 subtype="error_during_execution"），保留在流中。你必须在读取新查询的响应之前用 receive_response() 清空它们。如果在 interrupt() 之后立即发送新查询并仅调用一次 receive_response()，你将收到被中断任务的消息，而不是新查询的响应。
​
示例 - 高级权限控制
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk.types import (
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)


async def custom_permission_handler(
    tool_name: str, input_data: dict, context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    """Custom logic for tool permissions."""

    # Block writes to system directories
    if tool_name == "Write" and input_data.get("file_path", "").startswith("/system/"):
        return PermissionResultDeny(
            message="System directory write not allowed", interrupt=True
        )

    # Redirect sensitive file operations
    if tool_name in ["Write", "Edit"] and "config" in input_data.get("file_path", ""):
        safe_path = f"./sandbox/{input_data['file_path']}"
        return PermissionResultAllow(
            updated_input={**input_data, "file_path": safe_path}
        )

    # Allow everything else
    return PermissionResultAllow(updated_input=input_data)


async def main():
    options = ClaudeAgentOptions(
        can_use_tool=custom_permission_handler, allowed_tools=["Read", "Write", "Edit"]
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("Update the system config file")

        async for message in client.receive_response():
            # Will use sandbox path instead
            print(message)


asyncio.run(main())

​
类型
@dataclass vs TypedDict： 此 SDK 使用两种类型。用 @dataclass 装饰的类（如 ResultMessage、AgentDefinition、TextBlock）在运行时是对象实例，支持属性访问：msg.result。用 TypedDict 定义的类（如 ThinkingConfigEnabled、McpStdioServerConfig、SyncHookJSONOutput）在运行时是普通字典，需要键访问：config["budget_tokens"]，而不是 config.budget_tokens。ClassName(field=value) 调用语法对两者都有效，但只有数据类产生具有属性的对象。
​
SdkMcpTool
使用 @tool 装饰器创建的 SDK MCP 工具的定义。
@dataclass
class SdkMcpTool(Generic[T]):
    name: str
    description: str
    input_schema: type[T] | dict[str, Any]
    handler: Callable[[T], Awaitable[dict[str, Any]]]
    annotations: ToolAnnotations | None = None

属性	类型	描述
name	str	工具的唯一标识符
description	str	人类可读的描述
input_schema	type[T] | dict[str, Any]	输入验证的模式
handler	Callable[[T], Awaitable[dict[str, Any]]]	处理工具执行的异步函数
annotations	ToolAnnotations | None	可选的 MCP 工具注解（例如 readOnlyHint、destructiveHint、openWorldHint）。来自 mcp.types
​
Transport
自定义传输实现的抽象基类。使用此类通过自定义通道与 Claude 进程通信（例如，远程连接而不是本地子进程）。
这是一个低级内部 API。接口可能在未来版本中更改。自定义实现必须更新以匹配任何接口更改。
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any


class Transport(ABC):
    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def write(self, data: str) -> None: ...

    @abstractmethod
    def read_messages(self) -> AsyncIterator[dict[str, Any]]: ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    def is_ready(self) -> bool: ...

    @abstractmethod
    async def end_input(self) -> None: ...

方法	描述
connect()	连接传输并准备通信
write(data)	将原始数据（JSON + 换行符）写入传输
read_messages()	异步迭代器，产生解析的 JSON 消息
close()	关闭连接并清理资源
is_ready()	如果传输可以发送和接收，返回 True
end_input()	关闭输入流（例如，为子进程传输关闭 stdin）
导入：from claude_agent_sdk import Transport
​
ClaudeAgentOptions
Claude Code 查询的配置数据类。
@dataclass
class ClaudeAgentOptions:
    tools: list[str] | ToolsPreset | None = None
    allowed_tools: list[str] = field(default_factory=list)
    system_prompt: str | SystemPromptPreset | None = None
    mcp_servers: dict[str, McpServerConfig] | str | Path = field(default_factory=dict)
    strict_mcp_config: bool = False
    permission_mode: PermissionMode | None = None
    continue_conversation: bool = False
    resume: str | None = None
    max_turns: int | None = None
    max_budget_usd: float | None = None
    disallowed_tools: list[str] = field(default_factory=list)
    model: str | None = None
    fallback_model: str | None = None
    betas: list[SdkBeta] = field(default_factory=list)
    output_format: dict[str, Any] | None = None
    permission_prompt_tool_name: str | None = None
    cwd: str | Path | None = None
    cli_path: str | Path | None = None
    settings: str | None = None
    add_dirs: list[str | Path] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    extra_args: dict[str, str | None] = field(default_factory=dict)
    max_buffer_size: int | None = None
    debug_stderr: Any = sys.stderr  # Deprecated
    stderr: Callable[[str], None] | None = None
    can_use_tool: CanUseTool | None = None
    hooks: dict[HookEvent, list[HookMatcher]] | None = None
    user: str | None = None
    include_partial_messages: bool = False
    include_hook_events: bool = False
    fork_session: bool = False
    agents: dict[str, AgentDefinition] | None = None
    setting_sources: list[SettingSource] | None = None
    sandbox: SandboxSettings | None = None
    plugins: list[SdkPluginConfig] = field(default_factory=list)
    max_thinking_tokens: int | None = None  # Deprecated: use thinking instead
    thinking: ThinkingConfig | None = None
    effort: EffortLevel | None = None
    enable_file_checkpointing: bool = False
    session_store: SessionStore | None = None
    session_store_flush: SessionStoreFlushMode = "batched"

属性	类型	默认值	描述
tools	list[str] | ToolsPreset | None	None	工具配置。使用 {"type": "preset", "preset": "claude_code"} 获取 Claude Code 的默认工具
allowed_tools	list[str]	[]	无需提示即可自动批准的工具。这不会限制 Claude 仅使用这些工具；未列出的工具会通过 permission_mode 和 can_use_tool 处理。使用 disallowed_tools 阻止工具。见 权限
system_prompt	str | SystemPromptPreset | None	None	系统提示配置。传递字符串以获取自定义提示，或使用 {"type": "preset", "preset": "claude_code"} 获取 Claude Code 的系统提示。添加 "append" 以扩展预设
mcp_servers	dict[str, McpServerConfig] | str | Path	{}	MCP 服务器配置或配置文件路径
strict_mcp_config	bool	False	当为 True 时，仅使用在 mcp_servers 中传递的服务器，忽略项目 .mcp.json、用户设置和插件提供的 MCP 服务器。映射到 CLI --strict-mcp-config 标志
permission_mode	PermissionMode | None	None	工具使用的权限模式
continue_conversation	bool	False	继续最近的对话
resume	str | None	None	要恢复的会话 ID
max_turns	int | None	None	最大代理轮次（工具使用往返）
max_budget_usd	float | None	None	当客户端成本估计达到此 USD 值时停止查询。与 total_cost_usd 的相同估计进行比较；见 跟踪成本和使用 了解准确性注意事项
disallowed_tools	list[str]	[]	要拒绝的工具。裸名称如 "Bash" 从 Claude 的上下文中移除工具。作用域规则如 "Bash(rm *)" 保持工具可用，并在每个权限模式（包括 bypassPermissions）中拒绝匹配的调用。见 权限
enable_file_checkpointing	bool	False	启用文件更改跟踪以进行回滚。见 文件检查点
model	str | None	None	要使用的 Claude 模型
fallback_model	str | None	None	主模型失败时使用的备用模型
betas	list[SdkBeta]	[]	要启用的测试功能。见 SdkBeta 了解可用选项
output_format	dict[str, Any] | None	None	结构化响应的输出格式（例如 {"type": "json_schema", "schema": {...}}）。见 结构化输出 了解详情
permission_prompt_tool_name	str | None	None	权限提示的 MCP 工具名称
cwd	str | Path | None	None	当前工作目录
cli_path	str | Path | None	None	Claude Code CLI 可执行文件的自定义路径
settings	str | None	None	设置文件的路径
add_dirs	list[str | Path]	[]	Claude 可以访问的其他目录
env	dict[str, str]	{}	环境变量合并到继承的进程环境之上。见 环境变量 了解底层 CLI 读取的变量，以及 处理缓慢或停滞的 API 响应 了解超时相关变量
extra_args	dict[str, str | None]	{}	直接传递给 CLI 的其他 CLI 参数
max_buffer_size	int | None	None	缓冲 CLI stdout 时的最大字节数
debug_stderr	Any	sys.stderr	已弃用 - 用于调试输出的类文件对象。改用 stderr 回调
stderr	Callable[[str], None] | None	None	CLI 中 stderr 输出的回调函数
can_use_tool	CanUseTool | None	None	工具权限回调函数。见 权限类型 了解详情
hooks	dict[HookEvent, list[HookMatcher]] | None	None	用于拦截事件的 hooks 配置
user	str | None	None	用户标识符
include_partial_messages	bool	False	包括部分消息流式事件。启用时，会产生 StreamEvent 消息
include_hook_events	bool	False	在消息流中包括 hooks 生命周期事件作为 HookEventMessage 对象
fork_session	bool	False	使用 resume 恢复时，分叉到新会话 ID 而不是继续原始会话
agents	dict[str, AgentDefinition] | None	None	以编程方式定义的子代理
plugins	list[SdkPluginConfig]	[]	从本地路径加载自定义插件。见 Plugins 了解详情
sandbox	SandboxSettings | None	None	以编程方式配置沙箱行为。见 沙箱设置 了解详情
setting_sources	list[SettingSource] | None	None（CLI 默认值：所有源）	控制加载哪些文件系统设置。传递 [] 以禁用用户、项目和本地设置。无论如何都会加载托管策略设置。见 使用 Claude Code 功能
skills	list[str] | Literal["all"] | None	None	会话可用的技能。传递 "all" 以启用每个发现的技能，或传递技能名称列表。设置时，SDK 会自动启用 Skill 工具，无需在 allowed_tools 中列出。见 Skills
max_thinking_tokens	int | None	None	已弃用 - 思考块的最大令牌数。改用 thinking
thinking	ThinkingConfig | None	None	控制扩展思考行为。优先于 max_thinking_tokens
effort	EffortLevel | None	None	思考深度的努力级别
session_store	SessionStore | None	None	将会话记录镜像到外部后端，以便任何主机都可以恢复它们。见 将会话持久化到外部存储
session_store_flush	Literal["batched", "eager"]	"batched"	何时将镜像的记录条目刷新到 session_store。"batched" 每轮刷新一次或当缓冲区填满时；"eager" 在每帧后触发后台刷新。当 session_store 为 None 时忽略
​
处理缓慢或停滞的 API 响应
CLI 子进程读取多个环境变量，这些变量控制 API 超时和停滞检测。通过 ClaudeAgentOptions.env 传递它们：
options = ClaudeAgentOptions(
    env={
        "API_TIMEOUT_MS": "120000",
        "CLAUDE_CODE_MAX_RETRIES": "2",
        "CLAUDE_ASYNC_AGENT_STALL_TIMEOUT_MS": "120000",
    },
)

API_TIMEOUT_MS：Anthropic 客户端上的每个请求超时，以毫秒为单位。默认 600000。适用于主循环和所有子代理。
CLAUDE_CODE_MAX_RETRIES：最大 API 重试次数。默认 10。每次重试都有自己的 API_TIMEOUT_MS 窗口，因此最坏情况下的实际时间大约是 API_TIMEOUT_MS × (CLAUDE_CODE_MAX_RETRIES + 1) 加上退避。
CLAUDE_ASYNC_AGENT_STALL_TIMEOUT_MS：使用 run_in_background 启动的子代理的停滞监视器。默认 600000。在每个流事件时重置；停滞时中止子代理，将任务标记为失败，并将错误与任何部分结果一起呈现给父代理。不适用于同步子代理。
CLAUDE_ENABLE_STREAM_WATCHDOG=1 与 CLAUDE_STREAM_IDLE_TIMEOUT_MS：当标头已到达但响应体停止流式传输时中止请求。默认关闭。CLAUDE_STREAM_IDLE_TIMEOUT_MS 默认为 300000 并被限制为该最小值。中止的请求通过正常重试路径进行。
​
OutputFormat
结构化输出验证的配置。将其作为 dict 传递给 ClaudeAgentOptions 上的 output_format 字段：
# Expected dict shape for output_format
{
    "type": "json_schema",
    "schema": {...},  # Your JSON Schema definition
}

字段	必需	描述
type	是	必须是 "json_schema" 用于 JSON Schema 验证
schema	是	用于输出验证的 JSON Schema 定义
​
SystemPromptPreset
使用 Claude Code 的预设系统提示和可选添加的配置。
class SystemPromptPreset(TypedDict):
    type: Literal["preset"]
    preset: Literal["claude_code"]
    append: NotRequired[str]
    exclude_dynamic_sections: NotRequired[bool]

字段	必需	描述
type	是	必须是 "preset" 以使用预设系统提示
preset	是	必须是 "claude_code" 以使用 Claude Code 的系统提示
append	否	要追加到预设系统提示的其他说明
exclude_dynamic_sections	否	将每个会话的上下文（如工作目录、git 状态和内存路径）从系统提示移到第一条用户消息。改进跨用户和机器的提示缓存重用。见 修改系统提示
​
SettingSource
控制 SDK 从哪些基于文件系统的配置源加载设置。
SettingSource = Literal["user", "project", "local"]

值	描述	位置
"user"	全局用户设置	~/.claude/settings.json
"project"	共享项目设置（版本控制）	.claude/settings.json
"local"	本地项目设置（gitignored）	.claude/settings.local.json
​
默认行为
当 setting_sources 被省略或为 None 时，query() 加载与 Claude Code CLI 相同的文件系统设置：用户、项目和本地。无论如何都会加载托管策略设置。见 settingSources 不控制什么 了解无论此选项如何都会读取的输入，以及如何禁用它们。
​
为什么使用 setting_sources
禁用文件系统设置：
# Do not load user, project, or local settings from disk
from claude_agent_sdk import query, ClaudeAgentOptions

async for message in query(
    prompt="Analyze this code",
    options=ClaudeAgentOptions(
        setting_sources=[]
    ),
):
    print(message)

在 Python SDK 0.1.59 及更早版本中，空列表的处理方式与省略选项相同，因此 setting_sources=[] 不会禁用文件系统设置。如果你需要空列表生效，请升级到较新版本。TypeScript SDK 不受影响。
显式加载所有文件系统设置：
from claude_agent_sdk import query, ClaudeAgentOptions

async for message in query(
    prompt="Analyze this code",
    options=ClaudeAgentOptions(
        setting_sources=["user", "project", "local"]
    ),
):
    print(message)

仅加载特定设置源：
# Load only project settings, ignore user and local
async for message in query(
    prompt="Run CI checks",
    options=ClaudeAgentOptions(
        setting_sources=["project"]  # Only .claude/settings.json
    ),
):
    print(message)

测试和 CI 环境：
# Ensure consistent behavior in CI by excluding local settings
async for message in query(
    prompt="Run tests",
    options=ClaudeAgentOptions(
        setting_sources=["project"],  # Only team-shared settings
        permission_mode="bypassPermissions",
    ),
):
    print(message)

仅 SDK 应用程序：
# Define everything programmatically.
# Pass [] to opt out of filesystem setting sources.
async for message in query(
    prompt="Review this PR",
    options=ClaudeAgentOptions(
        setting_sources=[],
        agents={...},
        mcp_servers={...},
        allowed_tools=["Read", "Grep", "Glob"],
    ),
):
    print(message)

加载 CLAUDE.md 项目说明：
# Load project settings to include CLAUDE.md files
async for message in query(
    prompt="Add a new feature following project conventions",
    options=ClaudeAgentOptions(
        system_prompt={
            "type": "preset",
            "preset": "claude_code",  # Use Claude Code's system prompt
        },
        setting_sources=["project"],  # Loads CLAUDE.md from project
        allowed_tools=["Read", "Write", "Edit"],
    ),
):
    print(message)

​
设置优先级
加载多个源时，设置按此优先级合并（从高到低）：
本地设置（.claude/settings.local.json）
项目设置（.claude/settings.json）
用户设置（~/.claude/settings.json）
编程选项（如 agents 和 allowed_tools）覆盖用户、项目和本地文件系统设置。托管策略设置优先于编程选项。
​
AgentDefinition
以编程方式定义的子代理的配置。
@dataclass
class AgentDefinition:
    description: str
    prompt: str
    tools: list[str] | None = None
    disallowedTools: list[str] | None = None
    model: str | None = None
    skills: list[str] | None = None
    memory: Literal["user", "project", "local"] | None = None
    mcpServers: list[str | dict[str, Any]] | None = None
    initialPrompt: str | None = None
    maxTurns: int | None = None
    background: bool | None = None
    effort: EffortLevel | int | None = None
    permissionMode: PermissionMode | None = None

字段	必需	描述
description	是	何时使用此代理的自然语言描述
prompt	是	代理的系统提示
tools	否	允许的工具名称数组。如果省略，继承所有工具
disallowedTools	否	要从代理的工具集中移除的工具名称数组
model	否	此代理的模型覆盖。接受别名如 "sonnet"、"opus"、"haiku" 或 "inherit"，或完整模型 ID。如果省略，使用主模型
skills	否	此代理可用的技能名称列表
memory	否	此代理的内存源："user"、"project" 或 "local"
mcpServers	否	此代理可用的 MCP 服务器。每个条目是服务器名称或内联 {name: config} 字典
initialPrompt	否	当此代理作为主线程代理运行时自动提交为第一个用户轮次
maxTurns	否	代理停止前的最大代理轮次数
background	否	调用时将此代理作为非阻塞后台任务运行
effort	否	此代理的推理努力级别。接受命名级别或整数。见 EffortLevel
permissionMode	否	此代理内工具执行的权限模式。见 PermissionMode
AgentDefinition 字段名称使用 camelCase，如 disallowedTools、permissionMode 和 maxTurns。这些名称直接映射到与 TypeScript SDK 共享的线路格式。这与 ClaudeAgentOptions 不同，后者对等效的顶级字段（如 disallowed_tools 和 permission_mode）使用 Python snake_case。因为 AgentDefinition 是数据类，传递 snake_case 关键字在构造时会引发 TypeError。
​
PermissionMode
用于控制工具执行的权限模式。
PermissionMode = Literal[
    "default",  # Standard permission behavior
    "acceptEdits",  # Auto-accept file edits
    "plan",  # Planning mode - read-only tools only
    "dontAsk",  # Deny anything not pre-approved instead of prompting
    "bypassPermissions",  # Bypass all permission checks (use with caution)
]

​
EffortLevel
用于指导思考深度的努力级别。
EffortLevel = Literal[
    "low",  # Minimal thinking, fastest responses
    "medium",  # Moderate thinking
    "high",  # Deep reasoning
    "xhigh",  # Extended reasoning (Opus 4.7 only; falls back to "high" on other models)
    "max",  # Maximum effort
]

​
CanUseTool
工具权限回调函数的类型别名。
CanUseTool = Callable[
    [str, dict[str, Any], ToolPermissionContext], Awaitable[PermissionResult]
]

回调接收：
tool_name：被调用的工具的名称
input_data：工具的输入参数
context：带有附加信息的 ToolPermissionContext
返回 PermissionResult（PermissionResultAllow 或 PermissionResultDeny）。
​
ToolPermissionContext
传递给工具权限回调的上下文信息。
@dataclass
class ToolPermissionContext:
    signal: Any | None = None  # Future: abort signal support
    suggestions: list[PermissionUpdate] = field(default_factory=list)
    blocked_path: str | None = None
    decision_reason: str | None = None
    title: str | None = None
    display_name: str | None = None
    description: str | None = None

字段	类型	描述
signal	Any | None	保留供将来中止信号支持
suggestions	list[PermissionUpdate]	来自 CLI 的权限更新建议。Bash 提示包括带有 localSettings 目标的建议，因此在 updated_permissions 中返回它会将规则写入 .claude/settings.local.json 并在会话间持久化。
blocked_path	str | None	触发权限请求的文件路径（如适用）。例如，当 Bash 命令尝试访问允许目录外的路径时
decision_reason	str | None	触发此权限请求的原因。从 PreToolUse hooks 的 permissionDecisionReason 转发，当 hooks 返回 "ask" 时
title	str | None	完整权限提示句子，如 Claude wants to read foo.txt。存在时用作主要提示文本
display_name	str | None	工具操作的短名词短语，如 Read file，适合按钮标签
description	str | None	权限 UI 的人类可读副标题
​
PermissionResult
权限回调结果的联合类型。
PermissionResult = PermissionResultAllow | PermissionResultDeny

​
PermissionResultAllow
指示应允许工具调用的结果。
@dataclass
class PermissionResultAllow:
    behavior: Literal["allow"] = "allow"
    updated_input: dict[str, Any] | None = None
    updated_permissions: list[PermissionUpdate] | None = None

字段	类型	默认值	描述
behavior	Literal["allow"]	"allow"	必须是 “allow”
updated_input	dict[str, Any] | None	None	要使用的修改后的输入而不是原始输入
updated_permissions	list[PermissionUpdate] | None	None	要应用的权限更新
​
PermissionResultDeny
指示应拒绝工具调用的结果。
@dataclass
class PermissionResultDeny:
    behavior: Literal["deny"] = "deny"
    message: str = ""
    interrupt: bool = False

字段	类型	默认值	描述
behavior	Literal["deny"]	"deny"	必须是 “deny”
message	str	""	解释为什么拒绝工具的消息
interrupt	bool	False	是否中断当前执行
​
PermissionUpdate
用于以编程方式更新权限的配置。
@dataclass
class PermissionUpdate:
    type: Literal[
        "addRules",
        "replaceRules",
        "removeRules",
        "setMode",
        "addDirectories",
        "removeDirectories",
    ]
    rules: list[PermissionRuleValue] | None = None
    behavior: Literal["allow", "deny", "ask"] | None = None
    mode: PermissionMode | None = None
    directories: list[str] | None = None
    destination: (
        Literal["userSettings", "projectSettings", "localSettings", "session"] | None
    ) = None

字段	类型	描述
type	Literal[...]	权限更新操作的类型
rules	list[PermissionRuleValue] | None	用于添加/替换/移除操作的规则
behavior	Literal["allow", "deny", "ask"] | None	基于规则的操作的行为
mode	PermissionMode | None	setMode 操作的模式
directories	list[str] | None	用于添加/移除目录操作的目录
destination	Literal[...] | None	应用权限更新的位置
​
PermissionRuleValue
要在权限更新中添加、替换或移除的规则。
@dataclass
class PermissionRuleValue:
    tool_name: str
    rule_content: str | None = None

​
ToolsPreset
使用 Claude Code 的默认工具集的预设工具配置。
class ToolsPreset(TypedDict):
    type: Literal["preset"]
    preset: Literal["claude_code"]

​
ThinkingConfig
控制扩展思考行为。三种配置的联合：
ThinkingDisplay = Literal["summarized", "omitted"]


class ThinkingConfigAdaptive(TypedDict):
    type: Literal["adaptive"]
    display: NotRequired[ThinkingDisplay]


class ThinkingConfigEnabled(TypedDict):
    type: Literal["enabled"]
    budget_tokens: int
    display: NotRequired[ThinkingDisplay]


class ThinkingConfigDisabled(TypedDict):
    type: Literal["disabled"]


ThinkingConfig = ThinkingConfigAdaptive | ThinkingConfigEnabled | ThinkingConfigDisabled

变体	字段	描述
adaptive	type, display	Claude 自适应决定何时思考
enabled	type, budget_tokens, display	启用具有特定令牌预算的思考
disabled	type	禁用思考
可选的 display 字段控制思考文本是否返回为 "summarized" 或 "omitted"。在 Claude Opus 4.7 及更高版本上，API 默认值为 "omitted"，因此设置 "summarized" 以在 ThinkingBlock 输出中接收思考内容。
因为这些是 TypedDict 类，它们在运行时是普通字典。要么将它们构造为字典字面量，要么调用类作为构造函数；两者都产生 dict。使用 config["budget_tokens"] 访问字段，而不是 config.budget_tokens：
from claude_agent_sdk import ClaudeAgentOptions, ThinkingConfigEnabled

# Option 1: dict literal (recommended, no import needed)
options = ClaudeAgentOptions(thinking={"type": "enabled", "budget_tokens": 20000})

# Option 2: constructor-style (returns a plain dict)
config = ThinkingConfigEnabled(type="enabled", budget_tokens=20000)
print(config["budget_tokens"])  # 20000
# config.budget_tokens would raise AttributeError

​
SdkBeta
SDK 测试功能的字面类型。
SdkBeta = Literal["context-1m-2025-08-07"]

与 ClaudeAgentOptions 中的 betas 字段一起使用以启用测试功能。
context-1m-2025-08-07 测试版自 2026 年 4 月 30 日起已停用。使用 Claude Sonnet 4.5 或 Sonnet 4 传递此标头无效，超过标准 200k 令牌上下文窗口的请求返回错误。要使用 1M 令牌上下文窗口，请迁移到 Claude Sonnet 4.6、Claude Opus 4.6 或 Claude Opus 4.7，它们以标准定价包括 1M 上下文，无需测试版标头。
​
McpSdkServerConfig
使用 create_sdk_mcp_server() 创建的 SDK MCP 服务器的配置。
class McpSdkServerConfig(TypedDict):
    type: Literal["sdk"]
    name: str
    instance: Any  # MCP Server instance

​
McpServerConfig
MCP 服务器配置的联合类型。
McpServerConfig = (
    McpStdioServerConfig | McpSSEServerConfig | McpHttpServerConfig | McpSdkServerConfig
)

​
McpStdioServerConfig
class McpStdioServerConfig(TypedDict):
    type: NotRequired[Literal["stdio"]]  # Optional for backwards compatibility
    command: str
    args: NotRequired[list[str]]
    env: NotRequired[dict[str, str]]

​
McpSSEServerConfig
class McpSSEServerConfig(TypedDict):
    type: Literal["sse"]
    url: str
    headers: NotRequired[dict[str, str]]

​
McpHttpServerConfig
class McpHttpServerConfig(TypedDict):
    type: Literal["http"]
    url: str
    headers: NotRequired[dict[str, str]]

​
McpServerStatusConfig
由 get_mcp_status() 报告的 MCP 服务器的配置。这是所有 McpServerConfig 传输变体加上用于通过 claude.ai 代理的服务器的仅输出 claudeai-proxy 变体的联合。
McpServerStatusConfig = (
    McpStdioServerConfig
    | McpSSEServerConfig
    | McpHttpServerConfig
    | McpSdkServerConfigStatus
    | McpClaudeAIProxyServerConfig
)

McpSdkServerConfigStatus 是 McpSdkServerConfig 的可序列化形式，仅包含 type（"sdk"）和 name（str）字段；进程内 instance 被省略。McpClaudeAIProxyServerConfig 具有 type（"claudeai-proxy"）、url（str）和 id（str）字段。
​
McpStatusResponse
来自 ClaudeSDKClient.get_mcp_status() 的响应。在 mcpServers 键下包装服务器状态列表。
class McpStatusResponse(TypedDict):
    mcpServers: list[McpServerStatus]

​
McpServerStatus
连接的 MCP 服务器的状态，包含在 McpStatusResponse 中。
class McpServerStatus(TypedDict):
    name: str
    status: McpServerConnectionStatus  # "connected" | "failed" | "needs-auth" | "pending" | "disabled"
    serverInfo: NotRequired[McpServerInfo]
    error: NotRequired[str]
    config: NotRequired[McpServerStatusConfig]
    scope: NotRequired[str]
    tools: NotRequired[list[McpToolInfo]]

字段	类型	描述
name	str	服务器名称
status	str	"connected"、"failed"、"needs-auth"、"pending" 或 "disabled" 之一
serverInfo	dict（可选）	服务器名称和版本（{"name": str, "version": str}）
error	str（可选）	服务器连接失败时的错误消息
config	McpServerStatusConfig（可选）	服务器配置。与 McpServerConfig 形状相同（stdio、SSE、HTTP 或 SDK），加上通过 claude.ai 连接的服务器的 claudeai-proxy 变体
scope	str（可选）	配置范围
tools	list（可选）	此服务器提供的工具，每个都有 name、description 和 annotations 字段
​
SdkPluginConfig
SDK 中加载插件的配置。
class SdkPluginConfig(TypedDict):
    type: Literal["local"]
    path: str

字段	类型	描述
type	Literal["local"]	必须是 "local"（目前仅支持本地插件）
path	str	插件目录的绝对或相对路径
示例：
plugins = [
    {"type": "local", "path": "./my-plugin"},
    {"type": "local", "path": "/absolute/path/to/plugin"},
]

有关创建和使用插件的完整信息，见 Plugins。
​
消息类型
​
Message
所有可能消息的联合类型。
Message = (
    UserMessage
    | AssistantMessage
    | SystemMessage
    | ResultMessage
    | StreamEvent
    | RateLimitEvent
)

​
UserMessage
用户输入消息。
@dataclass
class UserMessage:
    content: str | list[ContentBlock]
    uuid: str | None = None
    parent_tool_use_id: str | None = None
    tool_use_result: dict[str, Any] | None = None

字段	类型	描述
content	str | list[ContentBlock]	消息内容为文本或内容块
uuid	str | None	唯一消息标识符
parent_tool_use_id	str | None	如果此消息是工具结果响应，则为工具使用 ID
tool_use_result	dict[str, Any] | None	工具结果数据（如果适用）
​
AssistantMessage
带有内容块的助手响应消息。
@dataclass
class AssistantMessage:
    content: list[ContentBlock]
    model: str
    parent_tool_use_id: str | None = None
    error: AssistantMessageError | None = None
    usage: dict[str, Any] | None = None
    message_id: str | None = None

字段	类型	描述
content	list[ContentBlock]	响应中的内容块列表
model	str	生成响应的模型
parent_tool_use_id	str | None	如果这是嵌套响应，则为工具使用 ID
error	AssistantMessageError | None	如果响应遇到错误，则为错误类型
usage	dict[str, Any] | None	每条消息的令牌使用情况（与 ResultMessage.usage 相同的键）
message_id	str | None	API 消息 ID。来自一个轮次的多条消息共享相同的 ID
​
AssistantMessageError
助手消息的可能错误类型。
AssistantMessageError = Literal[
    "authentication_failed",
    "billing_error",
    "rate_limit",
    "invalid_request",
    "server_error",
    "max_output_tokens",
    "unknown",
]

​
SystemMessage
带有元数据的系统消息。
@dataclass
class SystemMessage:
    subtype: str
    data: dict[str, Any]

​
ResultMessage
带有成本和使用信息的最终结果消息。
@dataclass
class ResultMessage:
    subtype: str
    duration_ms: int
    duration_api_ms: int
    is_error: bool
    num_turns: int
    session_id: str
    stop_reason: str | None = None
    total_cost_usd: float | None = None
    usage: dict[str, Any] | None = None
    result: str | None = None
    structured_output: Any = None
    model_usage: dict[str, Any] | None = None
    permission_denials: list[Any] | None = None
    deferred_tool_use: DeferredToolUse | None = None
    errors: list[str] | None = None
    api_error_status: int | None = None
    uuid: str | None = None

usage 字典在存在时包含以下键：
键	类型	描述
input_tokens	int	消耗的总输入令牌。
output_tokens	int	生成的总输出令牌。
cache_creation_input_tokens	int	用于创建新缓存条目的令牌。
cache_read_input_tokens	int	从现有缓存条目读取的令牌。
model_usage 字典将模型名称映射到每个模型的使用情况。内部字典键使用 camelCase，因为该值从底层 CLI 进程未修改地传递，匹配 TypeScript ModelUsage 类型：
键	类型	描述
inputTokens	int	此模型的输入令牌。
outputTokens	int	此模型的输出令牌。
cacheReadInputTokens	int	此模型的缓存读取令牌。
cacheCreationInputTokens	int	此模型的缓存创建令牌。
webSearchRequests	int	此模型进行的网络搜索请求。
costUSD	float	此模型的估计成本（美元），客户端计算。见 跟踪成本和使用 了解计费注意事项。
contextWindow	int	此模型的上下文窗口大小。
maxOutputTokens	int	此模型的最大输出令牌限制。
​
StreamEvent
流式事件，用于流式传输期间的部分消息更新。仅在 ClaudeAgentOptions 中 include_partial_messages=True 时接收。通过 from claude_agent_sdk.types import StreamEvent 导入。
@dataclass
class StreamEvent:
    uuid: str
    session_id: str
    event: dict[str, Any]  # The raw Claude API stream event
    parent_tool_use_id: str | None = None

字段	类型	描述
uuid	str	此事件的唯一标识符
session_id	str	会话标识符
event	dict[str, Any]	原始 Claude API 流事件数据
parent_tool_use_id	str | None	如果此事件来自子代理，则为父工具使用 ID
​
RateLimitEvent
当速率限制状态更改时发出（例如，从 "allowed" 到 "allowed_warning"）。使用此来在用户达到硬限制之前警告他们，或在状态为 "rejected" 时退避。
@dataclass
class RateLimitEvent:
    rate_limit_info: RateLimitInfo
    uuid: str
    session_id: str

字段	类型	描述
rate_limit_info	RateLimitInfo	当前速率限制状态
uuid	str	唯一事件标识符
session_id	str	会话标识符
​
RateLimitInfo
由 RateLimitEvent 携带的速率限制状态。
RateLimitStatus = Literal["allowed", "allowed_warning", "rejected"]
RateLimitType = Literal[
    "five_hour", "seven_day", "seven_day_opus", "seven_day_sonnet", "overage"
]


@dataclass
class RateLimitInfo:
    status: RateLimitStatus
    resets_at: int | None = None
    rate_limit_type: RateLimitType | None = None
    utilization: float | None = None
    overage_status: RateLimitStatus | None = None
    overage_resets_at: int | None = None
    overage_disabled_reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

字段	类型	描述
status	RateLimitStatus	当前状态。"allowed_warning" 表示接近限制；"rejected" 表示达到限制
resets_at	int | None	速率限制窗口重置的 Unix 时间戳
rate_limit_type	RateLimitType | None	哪个速率限制窗口适用
utilization	float | None	消耗的速率限制的分数（0.0 到 1.0）
overage_status	RateLimitStatus | None	按需付费超额使用的状态（如果适用）
overage_resets_at	int | None	超额窗口重置的 Unix 时间戳
overage_disabled_reason	str | None	为什么超额不可用，如果状态为 "rejected"
raw	dict[str, Any]	来自 CLI 的完整原始字典，包括上面未建模的字段
​
TaskStartedMessage
当后台任务启动时发出。后台任务是在主轮次之外跟踪的任何内容：后台 Bash 命令、Monitor 监视、通过 Agent 工具生成的子代理或远程代理。task_type 字段告诉你是哪一个。此命名与 Task 到 Agent 工具重命名无关。
@dataclass
class TaskStartedMessage(SystemMessage):
    task_id: str
    description: str
    uuid: str
    session_id: str
    tool_use_id: str | None = None
    task_type: str | None = None

字段	类型	描述
task_id	str	任务的唯一标识符
description	str	任务的描述
uuid	str	唯一消息标识符
session_id	str	会话标识符
tool_use_id	str | None	关联的工具使用 ID
task_type	str | None	哪种后台任务："local_bash" 用于后台 Bash 和 Monitor 监视，"local_agent" 或 "remote_agent"
​
TaskUsage
后台任务的令牌和计时数据。
class TaskUsage(TypedDict):
    total_tokens: int
    tool_uses: int
    duration_ms: int

​
TaskProgressMessage
定期为运行的后台任务发出进度更新。
@dataclass
class TaskProgressMessage(SystemMessage):
    task_id: str
    description: str
    usage: TaskUsage
    uuid: str
    session_id: str
    tool_use_id: str | None = None
    last_tool_name: str | None = None

字段	类型	描述
task_id	str	任务的唯一标识符
description	str	当前状态描述
usage	TaskUsage	此任务迄今为止的令牌使用情况
uuid	str	唯一消息标识符
session_id	str	会话标识符
tool_use_id	str | None	关联的工具使用 ID
last_tool_name	str | None	任务使用的最后一个工具的名称
​
TaskNotificationMessage
当后台任务完成、失败或停止时发出。后台任务包括 run_in_background Bash 命令、Monitor 监视和后台子代理。
@dataclass
class TaskNotificationMessage(SystemMessage):
    task_id: str
    status: TaskNotificationStatus  # "completed" | "failed" | "stopped"
    output_file: str
    summary: str
    uuid: str
    session_id: str
    tool_use_id: str | None = None
    usage: TaskUsage | None = None

字段	类型	描述
task_id	str	任务的唯一标识符
status	TaskNotificationStatus	"completed"、"failed" 或 "stopped" 之一
output_file	str	任务输出文件的路径
summary	str	任务结果的摘要
uuid	str	唯一消息标识符
session_id	str	会话标识符
tool_use_id	str | None	关联的工具使用 ID
usage	TaskUsage | None	任务的最终令牌使用情况
​
内容块类型
​
ContentBlock
所有内容块的联合类型。
ContentBlock = TextBlock | ThinkingBlock | ToolUseBlock | ToolResultBlock

​
TextBlock
文本内容块。
@dataclass
class TextBlock:
    text: str

​
ThinkingBlock
思考内容块（用于具有思考能力的模型）。
@dataclass
class ThinkingBlock:
    thinking: str
    signature: str

​
ToolUseBlock
工具使用请求块。
@dataclass
class ToolUseBlock:
    id: str
    name: str
    input: dict[str, Any]

​
ToolResultBlock
工具执行结果块。
@dataclass
class ToolResultBlock:
    tool_use_id: str
    content: str | list[dict[str, Any]] | None = None
    is_error: bool | None = None

​
错误类型
​
ClaudeSDKError
所有 SDK 错误的基础异常类。
class ClaudeSDKError(Exception):
    """Base error for Claude SDK."""

​
CLINotFoundError
当 Claude Code CLI 未安装或找不到时引发。
class CLINotFoundError(CLIConnectionError):
    def __init__(
        self, message: str = "Claude Code not found", cli_path: str | None = None
    ):
        """
        Args:
            message: Error message (default: "Claude Code not found")
            cli_path: Optional path to the CLI that was not found
        """

​
CLIConnectionError
当连接到 Claude Code 失败时引发。
class CLIConnectionError(ClaudeSDKError):
    """Failed to connect to Claude Code."""

​
ProcessError
当 Claude Code 进程失败时引发。
class ProcessError(ClaudeSDKError):
    def __init__(
        self, message: str, exit_code: int | None = None, stderr: str | None = None
    ):
        self.exit_code = exit_code
        self.stderr = stderr

​
CLIJSONDecodeError
当 JSON 解析失败时引发。
class CLIJSONDecodeError(ClaudeSDKError):
    def __init__(self, line: str, original_error: Exception):
        """
        Args:
            line: The line that failed to parse
            original_error: The original JSON decode exception
        """
        self.line = line
        self.original_error = original_error

​
Hook 类型
有关使用 hooks 的综合指南，包括示例和常见模式，见 Hooks 指南。
​
HookEvent
支持的 hook 事件类型。
HookEvent = Literal[
    "PreToolUse",  # Called before tool execution
    "PostToolUse",  # Called after tool execution
    "PostToolUseFailure",  # Called when a tool execution fails
    "UserPromptSubmit",  # Called when user submits a prompt
    "Stop",  # Called when stopping execution
    "SubagentStop",  # Called when a subagent stops
    "PreCompact",  # Called before message compaction
    "Notification",  # Called for notification events
    "SubagentStart",  # Called when a subagent starts
    "PermissionRequest",  # Called when a permission decision is needed
]

TypeScript SDK 支持 Python 中尚未提供的其他 hook 事件：SessionStart、SessionEnd、Setup、TeammateIdle、TaskCompleted、ConfigChange、WorktreeCreate、WorktreeRemove 和 PostToolBatch。
​
HookCallback
hook 回调函数的类型定义。
HookCallback = Callable[[HookInput, str | None, HookContext], Awaitable[HookJSONOutput]]

参数：
input：强类型 hook 输入，具有基于 hook_event_name 的判别联合（见 HookInput）
tool_use_id：可选工具使用标识符（用于工具相关的 hooks）
context：带有附加信息的 hook 上下文
返回可能包含以下内容的 HookJSONOutput：
decision："block" 以阻止操作
systemMessage：显示给用户的警告消息
hookSpecificOutput：hook 特定的输出数据
​
HookContext
传递给 hook 回调的上下文信息。
class HookContext(TypedDict):
    signal: Any | None  # Future: abort signal support

​
HookMatcher
用于将 hooks 匹配到特定事件或工具的配置。
@dataclass
class HookMatcher:
    matcher: str | None = (
        None  # Tool name or pattern to match (e.g., "Bash", "Write|Edit")
    )
    hooks: list[HookCallback] = field(
        default_factory=list
    )  # List of callbacks to execute
    timeout: float | None = (
        None  # Timeout in seconds for all hooks in this matcher (default: 60)
    )

​
HookInput
所有 hook 输入类型的联合类型。实际类型取决于 hook_event_name 字段。
HookInput = (
    PreToolUseHookInput
    | PostToolUseHookInput
    | PostToolUseFailureHookInput
    | UserPromptSubmitHookInput
    | StopHookInput
    | SubagentStopHookInput
    | PreCompactHookInput
    | NotificationHookInput
    | SubagentStartHookInput
    | PermissionRequestHookInput
)

​
BaseHookInput
所有 hook 输入类型中存在的基础字段。
class BaseHookInput(TypedDict):
    session_id: str
    transcript_path: str
    cwd: str
    permission_mode: NotRequired[str]

字段	类型	描述
session_id	str	当前会话标识符
transcript_path	str	会话记录文件的路径
cwd	str	当前工作目录
permission_mode	str（可选）	当前权限模式
​
PreToolUseHookInput
PreToolUse hook 事件的输入数据。
class PreToolUseHookInput(BaseHookInput):
    hook_event_name: Literal["PreToolUse"]
    tool_name: str
    tool_input: dict[str, Any]
    tool_use_id: str
    agent_id: NotRequired[str]
    agent_type: NotRequired[str]

字段	类型	描述
hook_event_name	Literal["PreToolUse"]	始终为 “PreToolUse”
tool_name	str	即将执行的工具的名称
tool_input	dict[str, Any]	工具的输入参数
tool_use_id	str	此工具使用的唯一标识符
agent_id	str（可选）	子代理标识符，当 hook 在子代理内触发时存在
agent_type	str（可选）	子代理类型，当 hook 在子代理内触发时存在
​
PostToolUseHookInput
PostToolUse hook 事件的输入数据。
class PostToolUseHookInput(BaseHookInput):
    hook_event_name: Literal["PostToolUse"]
    tool_name: str
    tool_input: dict[str, Any]
    tool_response: Any
    tool_use_id: str
    agent_id: NotRequired[str]
    agent_type: NotRequired[str]

字段	类型	描述
hook_event_name	Literal["PostToolUse"]	始终为 “PostToolUse”
tool_name	str	已执行的工具的名称
tool_input	dict[str, Any]	使用的输入参数
tool_response	Any	工具执行的响应
tool_use_id	str	此工具使用的唯一标识符
agent_id	str（可选）	子代理标识符，当 hook 在子代理内触发时存在
agent_type	str（可选）	子代理类型，当 hook 在子代理内触发时存在
​
PostToolUseFailureHookInput
PostToolUseFailure hook 事件的输入数据。当工具执行失败时调用。
class PostToolUseFailureHookInput(BaseHookInput):
    hook_event_name: Literal["PostToolUseFailure"]
    tool_name: str
    tool_input: dict[str, Any]
    tool_use_id: str
    error: str
    is_interrupt: NotRequired[bool]
    agent_id: NotRequired[str]
    agent_type: NotRequired[str]

字段	类型	描述
hook_event_name	Literal["PostToolUseFailure"]	始终为 “PostToolUseFailure”
tool_name	str	失败的工具的名称
tool_input	dict[str, Any]	使用的输入参数
tool_use_id	str	此工具使用的唯一标识符
error	str	失败执行的错误消息
is_interrupt	bool（可选）	失败是否由中断引起
agent_id	str（可选）	子代理标识符，当 hook 在子代理内触发时存在
agent_type	str（可选）	子代理类型，当 hook 在子代理内触发时存在
​
UserPromptSubmitHookInput
UserPromptSubmit hook 事件的输入数据。
class UserPromptSubmitHookInput(BaseHookInput):
    hook_event_name: Literal["UserPromptSubmit"]
    prompt: str

字段	类型	描述
hook_event_name	Literal["UserPromptSubmit"]	始终为 “UserPromptSubmit”
prompt	str	用户提交的提示
​
StopHookInput
Stop hook 事件的输入数据。
class StopHookInput(BaseHookInput):
    hook_event_name: Literal["Stop"]
    stop_hook_active: bool

字段	类型	描述
hook_event_name	Literal["Stop"]	始终为 “Stop”
stop_hook_active	bool	stop hook 是否活跃
​
SubagentStopHookInput
SubagentStop hook 事件的输入数据。
class SubagentStopHookInput(BaseHookInput):
    hook_event_name: Literal["SubagentStop"]
    stop_hook_active: bool
    agent_id: str
    agent_transcript_path: str
    agent_type: str

字段	类型	描述
hook_event_name	Literal["SubagentStop"]	始终为 “SubagentStop”
stop_hook_active	bool	stop hook 是否活跃
agent_id	str	子代理的唯一标识符
agent_transcript_path	str	子代理的记录文件路径
agent_type	str	子代理的类型
​
PreCompactHookInput
PreCompact hook 事件的输入数据。
class PreCompactHookInput(BaseHookInput):
    hook_event_name: Literal["PreCompact"]
    trigger: Literal["manual", "auto"]
    custom_instructions: str | None

字段	类型	描述
hook_event_name	Literal["PreCompact"]	始终为 “PreCompact”
trigger	Literal["manual", "auto"]	什么触发了压缩
custom_instructions	str | None	压缩的自定义说明
​
NotificationHookInput
Notification hook 事件的输入数据。
class NotificationHookInput(BaseHookInput):
    hook_event_name: Literal["Notification"]
    message: str
    title: NotRequired[str]
    notification_type: str

字段	类型	描述
hook_event_name	Literal["Notification"]	始终为 “Notification”
message	str	通知消息内容
title	str（可选）	通知标题
notification_type	str	通知类型
​
SubagentStartHookInput
SubagentStart hook 事件的输入数据。
class SubagentStartHookInput(BaseHookInput):
    hook_event_name: Literal["SubagentStart"]
    agent_id: str
    agent_type: str

字段	类型	描述
hook_event_name	Literal["SubagentStart"]	始终为 “SubagentStart”
agent_id	str	子代理的唯一标识符
agent_type	str	子代理的类型
​
PermissionRequestHookInput
PermissionRequest hook 事件的输入数据。允许 hooks 以编程方式处理权限决策。
class PermissionRequestHookInput(BaseHookInput):
    hook_event_name: Literal["PermissionRequest"]
    tool_name: str
    tool_input: dict[str, Any]
    permission_suggestions: NotRequired[list[Any]]

字段	类型	描述
hook_event_name	Literal["PermissionRequest"]	始终为 “PermissionRequest”
tool_name	str	请求权限的工具的名称
tool_input	dict[str, Any]	工具的输入参数
permission_suggestions	list[Any]（可选）	来自 CLI 的建议权限更新
​
HookJSONOutput
hook 回调返回值的联合类型。
HookJSONOutput = AsyncHookJSONOutput | SyncHookJSONOutput

​
SyncHookJSONOutput
具有控制和决策字段的同步 hook 输出。
class SyncHookJSONOutput(TypedDict):
    # Control fields
    continue_: NotRequired[bool]  # Whether to proceed (default: True)
    suppressOutput: NotRequired[bool]  # Hide stdout from transcript
    stopReason: NotRequired[str]  # Message when continue is False

    # Decision fields
    decision: NotRequired[Literal["block"]]
    systemMessage: NotRequired[str]  # Warning message for user
    reason: NotRequired[str]  # Feedback for Claude

    # Hook-specific output
    hookSpecificOutput: NotRequired[HookSpecificOutput]

在 Python 代码中使用 continue_（带下划线）。发送到 CLI 时会自动转换为 continue。
​
HookSpecificOutput
包含 hook 事件名称和事件特定字段的 TypedDict。形状取决于 hookEventName 值。有关每个 hook 事件的可用字段的完整详情，见 使用 hooks 控制执行。
事件特定输出类型的判别联合。hookEventName 字段确定哪些字段有效。
class PreToolUseHookSpecificOutput(TypedDict):
    hookEventName: Literal["PreToolUse"]
    permissionDecision: NotRequired[Literal["allow", "deny", "ask", "defer"]]
    permissionDecisionReason: NotRequired[str]
    updatedInput: NotRequired[dict[str, Any]]
    additionalContext: NotRequired[str]


class PostToolUseHookSpecificOutput(TypedDict):
    hookEventName: Literal["PostToolUse"]
    additionalContext: NotRequired[str]
    updatedToolOutput: NotRequired[Any]
    updatedMCPToolOutput: NotRequired[Any]  # Deprecated: use updatedToolOutput, which works for all tools


class PostToolUseFailureHookSpecificOutput(TypedDict):
    hookEventName: Literal["PostToolUseFailure"]
    additionalContext: NotRequired[str]


class UserPromptSubmitHookSpecificOutput(TypedDict):
    hookEventName: Literal["UserPromptSubmit"]
    additionalContext: NotRequired[str]


class NotificationHookSpecificOutput(TypedDict):
    hookEventName: Literal["Notification"]
    additionalContext: NotRequired[str]


class SubagentStartHookSpecificOutput(TypedDict):
    hookEventName: Literal["SubagentStart"]
    additionalContext: NotRequired[str]


class PermissionRequestHookSpecificOutput(TypedDict):
    hookEventName: Literal["PermissionRequest"]
    decision: dict[str, Any]


HookSpecificOutput = (
    PreToolUseHookSpecificOutput
    | PostToolUseHookSpecificOutput
    | PostToolUseFailureHookSpecificOutput
    | UserPromptSubmitHookSpecificOutput
    | NotificationHookSpecificOutput
    | SubagentStartHookSpecificOutput
    | PermissionRequestHookSpecificOutput
)

​
AsyncHookJSONOutput
延迟 hook 执行的异步 hook 输出。
class AsyncHookJSONOutput(TypedDict):
    async_: Literal[True]  # Set to True to defer execution
    asyncTimeout: NotRequired[int]  # Timeout in milliseconds

在 Python 代码中使用 async_（带下划线）。发送到 CLI 时会自动转换为 async。
​
Hook 使用示例
此示例注册两个 hooks：一个阻止危险的 bash 命令（如 rm -rf /），另一个记录所有工具使用以进行审计。安全 hook 仅在 Bash 命令上运行（通过 matcher），而日志 hook 在所有工具上运行。
from claude_agent_sdk import query, ClaudeAgentOptions, HookMatcher, HookContext
from typing import Any


async def validate_bash_command(
    input_data: dict[str, Any], tool_use_id: str | None, context: HookContext
) -> dict[str, Any]:
    """Validate and potentially block dangerous bash commands."""
    if input_data["tool_name"] == "Bash":
        command = input_data["tool_input"].get("command", "")
        if "rm -rf /" in command:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "Dangerous command blocked",
                }
            }
    return {}


async def log_tool_use(
    input_data: dict[str, Any], tool_use_id: str | None, context: HookContext
) -> dict[str, Any]:
    """Log all tool usage for auditing."""
    print(f"Tool used: {input_data.get('tool_name')}")
    return {}


options = ClaudeAgentOptions(
    hooks={
        "PreToolUse": [
            HookMatcher(
                matcher="Bash", hooks=[validate_bash_command], timeout=120
            ),  # 2 min for validation
            HookMatcher(
                hooks=[log_tool_use]
            ),  # Applies to all tools (default 60s timeout)
        ],
        "PostToolUse": [HookMatcher(hooks=[log_tool_use])],
    }
)

async for message in query(prompt="Analyze this codebase", options=options):
    print(message)

​
工具输入/输出类型
所有内置 Claude Code 工具的输入/输出模式文档。虽然 Python SDK 不将这些导出为类型，但它们代表消息中工具输入和输出的结构。
​
Agent
工具名称： Agent（之前为 Task，仍然接受作为别名）
输入：
{
    "description": str,  # 任务的简短描述（3-5 个单词）
    "prompt": str,  # 代理要执行的任务
    "subagent_type": str,  # 要使用的专门代理的类型
}

输出：
{
    "result": str,  # 来自子代理的最终结果
    "usage": dict | None,  # 令牌使用统计
    "total_cost_usd": float | None,  # 以美元计的估计总成本
    "duration_ms": int | None,  # 执行持续时间（毫秒）
}

​
AskUserQuestion
工具名称： AskUserQuestion
在执行期间向用户提出澄清问题。见 处理批准和用户输入 了解使用详情。
输入：
{
    "questions": [  # 要向用户提出的问题（1-4 个问题）
        {
            "question": str,  # 要向用户提出的完整问题
            "header": str,  # 显示为芯片/标签的非常简短的标签（最多 12 个字符）
            "options": [  # 可用的选择（2-4 个选项）
                {
                    "label": str,  # 此选项的显示文本（1-5 个单词）
                    "description": str,  # 此选项含义的说明
                }
            ],
            "multiSelect": bool,  # 设置为 true 以允许多个选择
        }
    ],
    "answers": dict[str, str | list[str]] | None,
    # 由权限系统填充的用户答案。多选
    # 答案可能是标签列表或逗号连接的字符串
}

输出：
{
    "questions": [  # 被提出的问题
        {
            "question": str,
            "header": str,
            "options": [{"label": str, "description": str}],
            "multiSelect": bool,
        }
    ],
    "answers": dict[str, str],  # 将问题文本映射到答案字符串
    # 多选答案以逗号分隔
}

​
Bash
工具名称： Bash
输入：
{
    "command": str,  # 要执行的命令
    "timeout": int | None,  # 可选的超时时间（毫秒）（最大 600000）
    "description": str | None,  # 清晰、简洁的描述（5-10 个单词）
    "run_in_background": bool | None,  # 设置为 true 以在后台运行
}

输出：
{
    "output": str,  # 合并的 stdout 和 stderr 输出
    "exitCode": int,  # 命令的退出代码
    "killed": bool | None,  # 命令是否因超时而被杀死
    "shellId": str | None,  # 后台进程的 Shell ID
}

​
Monitor
工具名称： Monitor
运行后台脚本并将每个 stdout 行作为事件传递给 Claude，以便它可以做出反应而无需轮询。Monitor 遵循与 Bash 相同的权限规则。见 Monitor 工具参考 了解行为和提供商可用性。
输入：
{
    "command": str,  # Shell 脚本；每个 stdout 行是一个事件，退出结束监视
    "description": str,  # 在通知中显示的简短描述
    "timeout_ms": int | None,  # 在此截止时间后杀死（默认 300000，最大 3600000）
    "persistent": bool | None,  # 在会话的生命周期内运行；使用 TaskStop 停止
}

输出：
{
    "taskId": str,  # 后台监视任务的 ID
    "timeoutMs": int,  # 超时截止时间（毫秒）（持久时为 0）
    "persistent": bool | None,  # 当运行到 TaskStop 或会话结束时为 True
}

​
Edit
工具名称： Edit
输入：
{
    "file_path": str,  # 要修改的文件的绝对路径
    "old_string": str,  # 要替换的文本
    "new_string": str,  # 替换为的文本
    "replace_all": bool | None,  # 替换所有出现（默认 False）
}

输出：
{
    "message": str,  # 确认消息
    "replacements": int,  # 进行的替换次数
    "file_path": str,  # 被编辑的文件路径
}

​
Read
工具名称： Read
输入：
{
    "file_path": str,  # 要读取的文件的绝对路径
    "offset": int | None,  # 开始读取的行号
    "limit": int | None,  # 要读取的行数
}

输出（文本文件）：
{
    "content": str,  # 带行号的文件内容
    "total_lines": int,  # 文件中的总行数
    "lines_returned": int,  # 实际返回的行数
}

输出（图像）：
{
    "image": str,  # Base64 编码的图像数据
    "mime_type": str,  # 图像 MIME 类型
    "file_size": int,  # 文件大小（字节）
}

​
Write
工具名称： Write
输入：
{
    "file_path": str,  # 要写入的文件的绝对路径
    "content": str,  # 要写入文件的内容
}

输出：
{
    "message": str,  # 成功消息
    "bytes_written": int,  # 写入的字节数
    "file_path": str,  # 被写入的文件路径
}

​
Glob
工具名称： Glob
输入：
{
    "pattern": str,  # 用于匹配文件的 glob 模式
    "path": str | None,  # 要搜索的目录（默认为 cwd）
}

输出：
{
    "matches": list[str],  # 匹配的文件路径数组
    "count": int,  # 找到的匹配数
    "search_path": str,  # 使用的搜索目录
}

​
Grep
工具名称： Grep
输入：
{
    "pattern": str,  # 正则表达式模式
    "path": str | None,  # 要搜索的文件或目录
    "glob": str | None,  # 用于过滤文件的 glob 模式
    "type": str | None,  # 要搜索的文件类型
    "output_mode": str | None,  # "content"、"files_with_matches" 或 "count"
    "-i": bool | None,  # 不区分大小写的搜索
    "-n": bool | None,  # 显示行号
    "-B": int | None,  # 每个匹配前显示的行数
    "-A": int | None,  # 每个匹配后显示的行数
    "-C": int | None,  # 每个匹配前后显示的行数
    "head_limit": int | None,  # 将输出限制为前 N 行/条目
    "multiline": bool | None,  # 启用多行模式
}

输出（content 模式）：
{
    "matches": [
        {
            "file": str,
            "line_number": int | None,
            "line": str,
            "before_context": list[str] | None,
            "after_context": list[str] | None,
        }
    ],
    "total_matches": int,
}

输出（files_with_matches 模式）：
{
    "files": list[str],  # 包含匹配的文件
    "count": int,  # 包含匹配的文件数
}

​
NotebookEdit
工具名称： NotebookEdit
输入：
{
    "notebook_path": str,  # Jupyter 笔记本的绝对路径
    "cell_id": str | None,  # 要编辑的单元格的 ID
    "new_source": str,  # 单元格的新源代码
    "cell_type": "code" | "markdown" | None,  # 单元格的类型
    "edit_mode": "replace" | "insert" | "delete" | None,  # 编辑操作类型
}

输出：
{
    "message": str,  # 成功消息
    "edit_type": "replaced" | "inserted" | "deleted",  # 执行的编辑类型
    "cell_id": str | None,  # 受影响的单元格 ID
    "total_cells": int,  # 编辑后笔记本中的总单元格数
}

​
WebFetch
工具名称： WebFetch
输入：
{
    "url": str,  # 要从中获取内容的 URL
    "prompt": str,  # 在获取的内容上运行的提示
}

输出：
{
    "bytes": int,  # 获取的内容大小（字节）
    "code": int,  # HTTP 响应代码
    "codeText": str,  # HTTP 响应代码文本
    "result": str,  # 通过将提示应用于内容得到的处理结果
    "durationMs": int,  # 获取和处理内容的时间（毫秒）
    "url": str,  # 被获取的 URL
}

​
WebSearch
工具名称： WebSearch
输入：
{
    "query": str,  # 要使用的搜索查询
    "allowed_domains": list[str] | None,  # 仅包含来自这些域的结果
    "blocked_domains": list[str] | None,  # 永远不包含来自这些域的结果
}

输出：
{
    "query": str,  # 搜索查询
    "results": list[str | {"tool_use_id": str, "content": list[{"title": str, "url": str}]}],
    "durationSeconds": float,  # 搜索持续时间（秒）
}

​
TodoWrite
工具名称： TodoWrite
自 Claude Code v2.1.142 起，TodoWrite 默认被禁用。改用 TaskCreate、TaskGet、TaskUpdate 和 TaskList。见 迁移到 Task 工具 更新您的监视代码，或设置 CLAUDE_CODE_ENABLE_TASKS=0 以恢复到 TodoWrite。
输入：
{
    "todos": [
        {
            "content": str,  # 任务描述
            "status": "pending" | "in_progress" | "completed",  # 任务状态
            "activeForm": str,  # 描述的活跃形式
        }
    ]
}

输出：
{
    "message": str,  # 成功消息
    "stats": {"total": int, "pending": int, "in_progress": int, "completed": int},
}

​
TaskCreate
工具名称： TaskCreate
输入：
{
    "subject": str,  # 简短的任务标题
    "description": str,  # 详细的任务正文
    "activeForm": str | None,  # 进行中时显示的现在时标签
    "metadata": dict | None,  # 任意调用者元数据
}

输出：
{
    "task": {"id": str, "subject": str},  # 创建的任务及其分配的 ID
}

​
TaskUpdate
工具名称： TaskUpdate
输入：
{
    "taskId": str,  # 要修补的任务的 ID
    "status": Literal["pending", "in_progress", "completed", "deleted"] | None,
    "subject": str | None,
    "description": str | None,
    "activeForm": str | None,
    "addBlocks": list[str] | None,  # 此任务现在阻止的任务 ID
    "addBlockedBy": list[str] | None,  # 现在阻止此任务的任务 ID
    "owner": str | None,
    "metadata": dict | None,
}

输出：
{
    "success": bool,
    "taskId": str,
    "updatedFields": list[str],  # 更改的字段名称
    "error": str | None,
    "statusChange": {"from": str, "to": str} | None,
}

​
TaskGet
工具名称： TaskGet
输入：
{
    "taskId": str,  # 要读取的任务的 ID
}

输出：
{
    "task": {
        "id": str,
        "subject": str,
        "description": str,
        "status": Literal["pending", "in_progress", "completed"],
        "blocks": list[str],
        "blockedBy": list[str],
    } | None,  # 当 ID 未找到时为 None
}

​
TaskList
工具名称： TaskList
输入：
{}

输出：
{
    "tasks": [
        {
            "id": str,
            "subject": str,
            "status": Literal["pending", "in_progress", "completed"],
            "owner": str | None,
            "blockedBy": list[str],
        }
    ],
}

​
BashOutput
工具名称： BashOutput
输入：
{
    "bash_id": str,  # 后台 shell 的 ID
    "filter": str | None,  # 用于过滤输出行的可选正则表达式
}

输出：
{
    "output": str,  # 自上次检查以来的新输出
    "status": "running" | "completed" | "failed",  # 当前 shell 状态
    "exitCode": int | None,  # 完成时的退出代码
}

​
KillBash
工具名称： KillBash
输入：
{
    "shell_id": str  # 要杀死的后台 shell 的 ID
}

输出：
{
    "message": str,  # 成功消息
    "shell_id": str,  # 被杀死的 shell 的 ID
}

​
ExitPlanMode
工具名称： ExitPlanMode
输入：
{
    "plan": str  # 用户要运行以获得批准的计划
}

输出：
{
    "message": str,  # 确认消息
    "approved": bool | None,  # 用户是否批准了计划
}

​
ListMcpResources
工具名称： ListMcpResources
输入：
{
    "server": str | None  # 可选的服务器名称以按其过滤资源
}

输出：
{
    "resources": [
        {
            "uri": str,
            "name": str,
            "description": str | None,
            "mimeType": str | None,
            "server": str,
        }
    ],
    "total": int,
}

​
ReadMcpResource
工具名称： ReadMcpResource
输入：
{
    "server": str,  # MCP 服务器名称
    "uri": str,  # 要读取的资源 URI
}

输出：
{
    "contents": [
        {"uri": str, "mimeType": str | None, "text": str | None, "blob": str | None}
    ],
    "server": str,
}

​
ClaudeSDKClient 的高级功能
​
构建持续对话界面
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
)
import asyncio


class ConversationSession:
    """Maintains a single conversation session with Claude."""

    def __init__(self, options: ClaudeAgentOptions | None = None):
        self.client = ClaudeSDKClient(options)
        self.turn_count = 0

    async def start(self):
        await self.client.connect()
        print("Starting conversation session. Claude will remember context.")
        print(
            "Commands: 'exit' to quit, 'interrupt' to stop current task, 'new' for new session"
        )

        while True:
            user_input = input(f"\n[Turn {self.turn_count + 1}] You: ")

            if user_input.lower() == "exit":
                break
            elif user_input.lower() == "interrupt":
                await self.client.interrupt()
                print("Task interrupted!")
                continue
            elif user_input.lower() == "new":
                # Disconnect and reconnect for a fresh session
                await self.client.disconnect()
                await self.client.connect()
                self.turn_count = 0
                print("Started new conversation session (previous context cleared)")
                continue

            # Send message - the session retains all previous messages
            await self.client.query(user_input)
            self.turn_count += 1

            # Process response
            print(f"[Turn {self.turn_count}] Claude: ", end="")
            async for message in self.client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            print(block.text, end="")
            print()  # New line after response

        await self.client.disconnect()
        print(f"Conversation ended after {self.turn_count} turns.")


async def main():
    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Bash"], permission_mode="acceptEdits"
    )
    session = ConversationSession(options)
    await session.start()


# Example conversation:
# Turn 1 - You: "Create a file called hello.py"
# Turn 1 - Claude: "I'll create a hello.py file for you..."
# Turn 2 - You: "What's in that file?"
# Turn 2 - Claude: "The hello.py file I just created contains..." (remembers!)
# Turn 3 -You: "Add a main function to it"
# Turn 3 - Claude: "I'll add a main function to hello.py..." (knows which file!)

asyncio.run(main())

​
使用 Hooks 进行行为修改
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    HookMatcher,
    HookContext,
)
import asyncio
from typing import Any


async def pre_tool_logger(
    input_data: dict[str, Any], tool_use_id: str | None, context: HookContext
) -> dict[str, Any]:
    """Log all tool usage before execution."""
    tool_name = input_data.get("tool_name", "unknown")
    print(f"[PRE-TOOL] About to use: {tool_name}")

    # You can modify or block the tool execution here
    if tool_name == "Bash" and "rm -rf" in str(input_data.get("tool_input", {})):
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Dangerous command blocked",
            }
        }
    return {}


async def post_tool_logger(
    input_data: dict[str, Any], tool_use_id: str | None, context: HookContext
) -> dict[str, Any]:
    """Log results after tool execution."""
    tool_name = input_data.get("tool_name", "unknown")
    print(f"[POST-TOOL] Completed: {tool_name}")
    return {}


async def user_prompt_modifier(
    input_data: dict[str, Any], tool_use_id: str | None, context: HookContext
) -> dict[str, Any]:
    """Add context to user prompts."""
    original_prompt = input_data.get("prompt", "")

    # Add a timestamp as additional context for Claude to see
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": f"[Submitted at {timestamp}] Original prompt: {original_prompt}",
        }
    }


async def main():
    options = ClaudeAgentOptions(
        hooks={
            "PreToolUse": [
                HookMatcher(hooks=[pre_tool_logger]),
                HookMatcher(matcher="Bash", hooks=[pre_tool_logger]),
            ],
            "PostToolUse": [HookMatcher(hooks=[post_tool_logger])],
            "UserPromptSubmit": [HookMatcher(hooks=[user_prompt_modifier])],
        },
        allowed_tools=["Read", "Write", "Bash"],
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("List files in current directory")

        async for message in client.receive_response():
            # Hooks will automatically log tool usage
            pass


asyncio.run(main())

​
实时进度监控
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ToolUseBlock,
    ToolResultBlock,
    TextBlock,
)
import asyncio


async def monitor_progress():
    options = ClaudeAgentOptions(
        allowed_tools=["Write", "Bash"], permission_mode="acceptEdits"
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("Create 5 Python files with different sorting algorithms")

        # Monitor progress in real-time
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, ToolUseBlock):
                        if block.name == "Write":
                            file_path = block.input.get("file_path", "")
                            print(f"Creating: {file_path}")
                    elif isinstance(block, ToolResultBlock):
                        print("Completed tool execution")
                    elif isinstance(block, TextBlock):
                        print(f"Claude says: {block.text[:100]}...")

        print("Task completed!")


asyncio.run(monitor_progress())

​
示例用法
​
基本文件操作（使用 query）
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ToolUseBlock
import asyncio


async def create_project():
    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Bash"],
        permission_mode="acceptEdits",
        cwd="/home/user/project",
    )

    async for message in query(
        prompt="Create a Python project structure with setup.py", options=options
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    print(f"Using tool: {block.name}")


asyncio.run(create_project())

​
错误处理
from claude_agent_sdk import query, CLINotFoundError, ProcessError, CLIJSONDecodeError

try:
    async for message in query(prompt="Hello"):
        print(message)
except CLINotFoundError:
    print(
        "Claude Code CLI not found. Try reinstalling: pip install --force-reinstall claude-agent-sdk"
    )
except ProcessError as e:
    print(f"Process failed with exit code: {e.exit_code}")
except CLIJSONDecodeError as e:
    print(f"Failed to parse response: {e}")

​
使用客户端的流式模式
from claude_agent_sdk import ClaudeSDKClient
import asyncio


async def interactive_session():
    async with ClaudeSDKClient() as client:
        # Send initial message
        await client.query("What's the weather like?")

        # Process responses
        async for msg in client.receive_response():
            print(msg)

        # Send follow-up
        await client.query("Tell me more about that")

        # Process follow-up response
        async for msg in client.receive_response():
            print(msg)


asyncio.run(interactive_session())

​
使用 ClaudeSDKClient 的自定义工具
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    tool,
    create_sdk_mcp_server,
    AssistantMessage,
    TextBlock,
)
import asyncio
from typing import Any


# Define custom tools with @tool decorator
@tool("calculate", "Perform mathematical calculations", {"expression": str})
async def calculate(args: dict[str, Any]) -> dict[str, Any]:
    try:
        result = eval(args["expression"], {"__builtins__": {}})
        return {"content": [{"type": "text", "text": f"Result: {result}"}]}
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
            "is_error": True,
        }


@tool("get_time", "Get current time", {})
async def get_time(args: dict[str, Any]) -> dict[str, Any]:
    from datetime import datetime

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {"content": [{"type": "text", "text": f"Current time: {current_time}"}]}


async def main():
    # Create SDK MCP server with custom tools
    my_server = create_sdk_mcp_server(
        name="utilities", version="1.0.0", tools=[calculate, get_time]
    )

    # Configure options with the server
    options = ClaudeAgentOptions(
        mcp_servers={"utils": my_server},
        allowed_tools=["mcp__utils__calculate", "mcp__utils__get_time"],
    )

    # Use ClaudeSDKClient for interactive tool usage
    async with ClaudeSDKClient(options=options) as client:
        await client.query("What's 123 * 456?")

        # Process calculation response
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"Calculation: {block.text}")

        # Follow up with time query
        await client.query("What time is it now?")

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"Time: {block.text}")


asyncio.run(main())

​
沙箱配置
​
SandboxSettings
沙箱行为的配置。使用此来启用命令沙箱和以编程方式配置网络限制。
class SandboxSettings(TypedDict, total=False):
    enabled: bool
    autoAllowBashIfSandboxed: bool
    excludedCommands: list[str]
    allowUnsandboxedCommands: bool
    network: SandboxNetworkConfig
    ignoreViolations: SandboxIgnoreViolations
    enableWeakerNestedSandbox: bool

属性	类型	默认值	描述
enabled	bool	False	为命令执行启用沙箱模式
autoAllowBashIfSandboxed	bool	True	启用沙箱时自动批准 bash 命令
excludedCommands	list[str]	[]	始终绕过沙箱限制的命令（例如 ["docker"]）。这些自动运行沙箱外，无需模型参与
allowUnsandboxedCommands	bool	True	允许模型请求在沙箱外运行命令。当为 True 时，模型可以在工具输入中设置 dangerouslyDisableSandbox，这会回退到 权限系统
network	SandboxNetworkConfig	None	网络特定的沙箱配置
ignoreViolations	SandboxIgnoreViolations	None	配置要忽略的沙箱违规
enableWeakerNestedSandbox	bool	False	启用较弱的嵌套沙箱以实现兼容性
​
示例用法
from claude_agent_sdk import query, ClaudeAgentOptions, SandboxSettings

sandbox_settings: SandboxSettings = {
    "enabled": True,
    "autoAllowBashIfSandboxed": True,
    "network": {"allowLocalBinding": True},
}

async for message in query(
    prompt="Build and test my project",
    options=ClaudeAgentOptions(sandbox=sandbox_settings),
):
    print(message)

Unix socket 安全性：allowUnixSockets 选项可以授予对强大系统服务的访问权限。例如，允许 /var/run/docker.sock 实际上通过 Docker API 授予完整的主机系统访问权限，绕过沙箱隔离。仅允许严格必要的 Unix sockets，并理解每个的安全含义。
​
SandboxNetworkConfig
沙箱模式的网络特定配置。
class SandboxNetworkConfig(TypedDict, total=False):
    allowedDomains: list[str]
    deniedDomains: list[str]
    allowManagedDomainsOnly: bool
    allowUnixSockets: list[str]
    allowAllUnixSockets: bool
    allowLocalBinding: bool
    allowMachLookup: list[str]
    httpProxyPort: int
    socksProxyPort: int

属性	类型	默认值	描述
allowedDomains	list[str]	[]	沙箱化进程可以访问的域名
deniedDomains	list[str]	[]	沙箱化进程无法访问的域名。优先于 allowedDomains
allowManagedDomainsOnly	bool	False	仅限托管设置：在托管设置中设置时，忽略来自非托管设置源的 allowedDomains。通过 SDK 选项设置时无效
allowUnixSockets	list[str]	[]	进程可以访问的 Unix socket 路径（例如 Docker socket）
allowAllUnixSockets	bool	False	允许访问所有 Unix sockets
allowLocalBinding	bool	False	允许进程绑定到本地端口（例如开发服务器）
allowMachLookup	list[str]	[]	仅限 macOS：允许的 XPC/Mach 服务名称。支持尾部通配符
httpProxyPort	int	None	网络请求的 HTTP 代理端口
socksProxyPort	int	None	网络请求的 SOCKS 代理端口
内置沙箱代理基于请求的主机名强制执行网络允许列表，不会终止或检查 TLS 流量，因此 域名前置 等技术可能会绕过它。有关详细信息，请参阅 沙箱安全限制，以及 安全部署 以配置 TLS 终止代理。
​
SandboxIgnoreViolations
用于忽略特定沙箱违规的配置。
class SandboxIgnoreViolations(TypedDict, total=False):
    file: list[str]
    network: list[str]

属性	类型	默认值	描述
file	list[str]	[]	要忽略违规的文件路径模式
network	list[str]	[]	要忽略违规的网络模式
​
沙箱外命令的权限回退
当 allowUnsandboxedCommands 启用时，模型可以通过在工具输入中设置 dangerouslyDisableSandbox: True 来请求在沙箱外运行命令。这些请求回退到现有权限系统，意味着你的 can_use_tool 处理程序将被调用，允许你实现自定义授权逻辑。
excludedCommands vs allowUnsandboxedCommands：
excludedCommands：始终自动绕过沙箱的命令的静态列表（例如 ["docker"]）。模型对此无控制权。
allowUnsandboxedCommands：让模型在运行时通过在工具输入中设置 dangerouslyDisableSandbox: True 来决定是否请求沙箱外执行。
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    HookMatcher,
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)


async def can_use_tool(
    tool: str, input: dict, context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    # Check if the model is requesting to bypass the sandbox
    if tool == "Bash" and input.get("dangerouslyDisableSandbox"):
        # The model is requesting to run this command outside the sandbox
        print(f"Unsandboxed command requested: {input.get('command')}")

        if is_command_authorized(input.get("command")):
            return PermissionResultAllow()
        return PermissionResultDeny(
            message="Command not authorized for unsandboxed execution"
        )
    return PermissionResultAllow()


# Required: dummy hook keeps the stream open for can_use_tool
async def dummy_hook(input_data, tool_use_id, context):
    return {"continue_": True}


async def prompt_stream():
    yield {
        "type": "user",
        "message": {"role": "user", "content": "Deploy my application"},
    }


async def main():
    async for message in query(
        prompt=prompt_stream(),
        options=ClaudeAgentOptions(
            sandbox={
                "enabled": True,
                "allowUnsandboxedCommands": True,  # Model can request unsandboxed execution
            },
            permission_mode="default",
            can_use_tool=can_use_tool,
            hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[dummy_hook])]},
        ),
    ):
        print(message)

此模式使你能够：
审计模型请求：记录模型何时请求沙箱外执行
实现允许列表：仅允许特定命令在沙箱外运行
添加批准工作流：需要显式授权以进行特权操作
使用 dangerouslyDisableSandbox: True 运行的命令具有完整的系统访问权限。确保你的 can_use_tool 处理程序仔细验证这些请求。
如果 permission_mode 设置为 bypassPermissions 且 allow_unsandboxed_commands 启用，模型可以自主执行沙箱外的命令，无需任何批准提示。此组合实际上允许模型无声地逃离沙箱隔离。
​
另见
SDK 概述 - 一般 SDK 概念
TypeScript SDK 参考 - TypeScript SDK 文档
CLI 参考 - 命令行界面
常见工作流 - 分步指南

此页面对您有帮助吗？

是
否
TypeScript V2（已移除）
迁移指南
⌘I

---

# 迁移指南

> 章节: SDK 参考 | 来源: https://code.claude.com/docs/zh-CN/agent-sdk/migration-guide

---

SDK 参考
迁移到 Claude Agent SDK

将 Claude Code TypeScript 和 Python SDK 迁移到 Claude Agent SDK 的指南

复制页面
Documentation Index

Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt

Use this file to discover all available pages before exploring further.

​
概述
Claude Code SDK 已重命名为 Claude Agent SDK，其文档已重新组织。这一变化反映了该 SDK 在构建超越编码任务的 AI 代理方面的更广泛功能。
​
变更内容
方面	旧版本	新版本
包名称 (TS/JS)	@anthropic-ai/claude-code	@anthropic-ai/claude-agent-sdk
Python 包	claude-code-sdk	claude-agent-sdk
文档位置	Claude Code 文档	API 指南 → Agent SDK 部分
文档变更： Agent SDK 文档已从 Claude Code 文档移至 API 指南下的专门 Agent SDK 部分。Claude Code 文档现在专注于 CLI 工具和自动化功能。
​
迁移步骤
​
对于 TypeScript/JavaScript 项目
1. 卸载旧包：
npm uninstall @anthropic-ai/claude-code

2. 安装新包：
npm install @anthropic-ai/claude-agent-sdk

3. 更新导入：
将所有导入从 @anthropic-ai/claude-code 更改为 @anthropic-ai/claude-agent-sdk：
// 之前
import { query, tool, createSdkMcpServer } from "@anthropic-ai/claude-code";

// 之后
import { query, tool, createSdkMcpServer } from "@anthropic-ai/claude-agent-sdk";

4. 更新 package.json 依赖项：
如果您在 package.json 中列出了该包，请更新它：
之前：
{
  "dependencies": {
    "@anthropic-ai/claude-code": "^0.0.42"
  }
}

之后：
{
  "dependencies": {
    "@anthropic-ai/claude-agent-sdk": "^0.2.0"
  }
}

就这样！无需进行其他代码更改。
​
对于 Python 项目
1. 卸载旧包：
pip uninstall claude-code-sdk

2. 安装新包：
pip install claude-agent-sdk

3. 更新导入：
将所有导入从 claude_code_sdk 更改为 claude_agent_sdk：
# 之前
from claude_code_sdk import query, ClaudeCodeOptions

# 之后
from claude_agent_sdk import query, ClaudeAgentOptions

4. 更新类型名称：
将 ClaudeCodeOptions 更改为 ClaudeAgentOptions：
# 之前
from claude_code_sdk import query, ClaudeCodeOptions

options = ClaudeCodeOptions(model="claude-opus-4-7")

# 之后
from claude_agent_sdk import query, ClaudeAgentOptions

options = ClaudeAgentOptions(model="claude-opus-4-7")

5. 查看 破坏性变更
进行完成迁移所需的任何代码更改。
​
破坏性变更
为了改进隔离和显式配置，Claude Agent SDK v0.1.0 为从 Claude Code SDK 迁移的用户引入了破坏性变更。在迁移前请仔细查看本部分。
​
Python：ClaudeCodeOptions 重命名为 ClaudeAgentOptions
变更内容： Python SDK 类型 ClaudeCodeOptions 已重命名为 ClaudeAgentOptions。
迁移：
# 之前 (claude-code-sdk)
from claude_code_sdk import query, ClaudeCodeOptions

options = ClaudeCodeOptions(model="claude-opus-4-7", permission_mode="acceptEdits")

# 之后 (claude-agent-sdk)
from claude_agent_sdk import query, ClaudeAgentOptions

options = ClaudeAgentOptions(model="claude-opus-4-7", permission_mode="acceptEdits")

为什么变更： 类型名称现在与”Claude Agent SDK”品牌相匹配，并在 SDK 的命名约定中提供一致性。
​
系统提示不再是默认值
变更内容： SDK 不再默认使用 Claude Code 的系统提示。
迁移：
TypeScript
Python
// 之前 (v0.0.x) - 默认使用 Claude Code 的系统提示
const result = query({ prompt: "Hello" });

// 之后 (v0.1.0) - 默认使用最小系统提示
// 要获得旧行为，请显式请求 Claude Code 的预设：
const result = query({
  prompt: "Hello",
  options: {
    systemPrompt: { type: "preset", preset: "claude_code" }
  }
});

// 或使用自定义系统提示：
const result = query({
  prompt: "Hello",
  options: {
    systemPrompt: "You are a helpful coding assistant"
  }
});

为什么变更： 为 SDK 应用程序提供更好的控制和隔离。您现在可以构建具有自定义行为的代理，而无需继承 Claude Code 的 CLI 焦点指令。
​
设置源默认值
此默认值在 v0.1.0 中曾短暂更改，然后被还原，因此无需迁移操作。
当前行为： 在 query() 上省略 settingSources 会加载用户、项目和本地文件系统设置，与 CLI 匹配。这包括 ~/.claude/settings.json、.claude/settings.json、.claude/settings.local.json、CLAUDE.md 文件和自定义命令。
要从文件系统设置中隔离运行，请传递空数组：
TypeScript
Python
const result = query({
  prompt: "Hello",
  options: {
    settingSources: [] // 未加载文件系统设置
  }
});

// 或仅加载特定源：
const result = query({
  prompt: "Hello",
  options: {
    settingSources: ["project"] // 仅项目设置
  }
});

隔离对于 CI/CD 管道、已部署的应用程序、测试环境和多租户系统特别重要，其中本地自定义不应泄露。
SDK v0.1.0 曾短暂默认为不加载任何设置；这在后续版本中被还原。Python SDK 0.1.59 及更早版本将空列表视为与省略选项相同，因此在依赖 setting_sources=[] 之前请升级。有关即使 settingSources 为 [] 时仍会读取的输入，请参阅 settingSources 不控制的内容。
​
为什么重命名？
Claude Code SDK 最初是为编码任务设计的，但它已发展成为构建所有类型 AI 代理的强大框架。新名称”Claude Agent SDK”更好地反映了其功能：
构建业务代理（法律助手、财务顾问、客户支持）
创建专门的编码代理（SRE 机器人、安全审查员、代码审查代理）
为任何领域开发自定义代理，具有工具使用、MCP 集成等功能
​
获取帮助
如果您在迁移过程中遇到任何问题：
对于 TypeScript/JavaScript：
检查所有导入是否已更新为使用 @anthropic-ai/claude-agent-sdk
验证您的 package.json 具有新的包名称
运行 npm install 以确保依赖项已更新
对于 Python：
检查所有导入是否已更新为使用 claude_agent_sdk
验证您的 requirements.txt 或 pyproject.toml 具有新的包名称
运行 pip install claude-agent-sdk 以确保包已安装
​
后续步骤
探索 Agent SDK 概述 以了解可用功能
查看 TypeScript SDK 参考 以获取详细的 API 文档
查看 Python SDK 参考 以获取 Python 特定文档
了解 自定义工具 和 MCP 集成

此页面对您有帮助吗？

是
否
Python SDK
⌘I

---

