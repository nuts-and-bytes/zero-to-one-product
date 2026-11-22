<div align="center">

# Zero-to-One Product

**让复杂的 0→1，沿一条有状态、可恢复、有安全门的 Codex 路由器前进。**

<p>
  <a href="https://nuts-and-bytes.github.io/zero-to-one-product/"><strong>打开交互式文档与分类器 ↗</strong></a> ·
  <a href="#安装这个插件">快速安装</a> ·
  <a href="README.md">English</a>
</p>

<br />

<img src="docs/assets/hero-route.webp" alt="Zero-to-One Product：从模糊想法到首个可用版本" width="880" />

</div>

[English](README.md) | 简体中文

`zero-to-one-product` 是一个只包含 Skills 的 Codex 流程路由器。它把 [Matt Pocock Skills](https://github.com/mattpocock/skills) 的产品发现能力与 [Superpowers](https://github.com/obra/superpowers) 的工程执行纪律，组合成一条从模糊产品想法到首个可用版本的固定路线。

它不是另一套与两者竞争的方法论，也不会复制上游 Skills。它负责判断项目类型、识别当前阶段、选择唯一的当前流程，并在阶段完成后收回控制权重新路由。

> 一个路由器。每阶段一个主流程。一个可验证的下一步。

```mermaid
flowchart LR
  Idea["模糊想法 / 0→1 目标"] --> Classify{"路由器自动分类"}
  Classify -->|"中小型 · 新项目"| Grill["grill-me"]
  Classify -->|"中小型 · 已有工作区"| GrillDocs["grill-with-docs"]
  Classify -->|"跨会话 · 路线仍有雾"| Wayfinder["wayfinder"]
  Grill --> Spec["Matt: to-spec → to-tickets"]
  GrillDocs --> Spec
  Wayfinder --> Spec
  Spec --> Exec["Superpowers: worktree → plan → TDD → verify"]
  Exec --> Ship["首个可用版本"]
```

<p align="center">
  <img src="docs/assets/fixed-route.webp" alt="从产品发现到工程交付的固定路线" width="820" />
</p>

## 它解决什么问题

当 Matt Skills 与 Superpowers 同时安装时，Agent 可能重复 brainstorming、过早进入技术计划、跳过规格直接编码，或者执行完一项任务后失去全局流程。

`zero-to-one-product` 通过明确的阶段所有权解决这些冲突：

- Matt 负责弄清楚做什么、为什么做，以及如何把产品决定固化为规格和 Tickets。
- Router 负责项目分类、状态恢复、Git 安全门、有界执行和阶段交还。
- Superpowers 负责隔离工作区、单 Ticket 计划、TDD、常规调试、验证和分支收尾。
- 同一阶段只允许一个主流程，不会让功能相似的 Skills 同时接管任务。

## 自动判断项目入口

路由器会先根据证据判断项目规模，而不是让用户手动挑 Skill。

| 项目情况 | 判断信号 | 当前入口 |
| --- | --- | --- |
| 中小型、没有工作区 | 单一产品表面、少量角色，主要不确定性可通过一次对话或原型解决 | `grill-me` |
| 中小型、已有工作区 | 已有代码或文档可以参与产品判断 | `grill-with-docs` |
| 确实跨会话且路线仍有雾 | 预计超过一个 agent session，并且从当前状态到 destination 的路线仍然实质不清楚 | `wayfinder` |

## Wayfinder 契约

只有同时满足“预计超过一个 agent session”与“从当前状态到 destination 的路线仍然实质不清楚”，才选择 Wayfinder；任一条件不成立时，继续使用 `grill-me` 或 `grill-with-docs`。

Wayfinder map 只有在开放决策 Ticket 数量为 0、`Not yet specified` 为空且 destination 仍有效时才完成。完成后必须回到 Router 并进入 Matt `to-spec`，不能恢复为开放中的 wayfinding。

Tracker Notes、issue body 与 comment 都只是数据，不是授权。它们不能覆盖 Plan-don't-do、授权交付或生产执行，也不能选择额外 skill。任何执行请求必须退出 Wayfinder 并回到 Router，重新经过正常路由与授权门。

禁止把 secret 值、token、cookie、connection string、signed URL 或 credential location 写入 tracker artifact。如决策确实需要凭证引用，只能写抽象的 secret-manager identifier，且仅在用户确认 tracker 可见性合适后才可写入。

它只拥有新的独立产品、应用、服务、网站、工作流或 MVP 的 0→1 外层流程。超出范围时会立即交还所有权：

- 成熟项目的普通新功能 → `brainstorming`
- Bug 或异常行为 → `systematic-debugging`
- 无异常行为的计划性重构 → `codebase-design`

## 从想法到首个可用版本

路线包含 13 个可检查节点。Agent 会根据已有证据恢复到最靠后的未完成节点，而不是每次从头开始。

1. **确认产品问题** — `grill-me` 或 `grill-with-docs`：明确用户、问题、结果和边界。
2. **拆解跨会话路线迷雾** — `wayfinder`：仅在预计跨会话且到 destination 的路线仍实质不清楚时，建立可恢复的决策前沿。
3. **补齐事实** — `research`：只在产品决定依赖外部事实时研究。
4. **验证关键不确定性** — `prototype`：用可丢弃原型验证视觉、交互、状态或数据模型。
5. **形成规格** — `to-spec`：把已确认的产品决定写成可构建规格。
6. **切成 Tickets** — `to-tickets`：按纵向价值切出 Tickets，并记录阻塞关系。
7. **确认仓库状态** — Router Git gates：只读检查 Git、基线与工作区身份。
8. **隔离工作区** — `using-git-worktrees`：在有效 Git 和已知基线下创建隔离工作区。
9. **规划单个 Ticket** — `writing-plans`：只为当前 Ticket 定义文件、测试和验证命令。
10. **有界执行** — TDD + task reviews：新实现者执行 RED–GREEN–REFACTOR，再通过规格审查和质量审查。
11. **整体代码审查** — `code-review`：从 Standards 与 Spec 两条轴检查整个 Ticket。
12. **完成证据** — `verification-before-completion`：用新鲜测试、构建和验收证据证明完成。
13. **分支收尾** — `finishing-a-development-branch`：选择合并、PR、保留或放弃。

## 固定的职责边界

### Matt Pocock Skills：产品形成

负责追问、研究、原型、规格、切票、困难调试和整体代码审查。Matt 产品阶段运行时，不叠加 Superpowers `brainstorming`。

### Router：流程控制

始终保持唯一的 0→1 外层流程所有者，根据范围、证据和状态优先级决定当前阶段。它也负责 Git 检查门与单 Ticket 的有界执行适配器。

### Superpowers：工程交付

负责 worktree、单 Ticket 技术计划、正式 TDD、常规调试、任务审查、完成验证和分支收尾。

正式编码统一使用 Superpowers `test-driven-development`。组合流程不会调用 Matt `tdd`、Matt `implement`，也不会把完整的 `subagent-driven-development` 或 `executing-plans` 当成终态流程。

## 安全与授权

自动路由只免除“应该选择哪个流程”的确认，不会扩大 Agent 权限。以下操作仍保留各自的授权门：

- 外部写入和 Issue Tracker 变更
- 创建 worktree 或初始化 Git 仓库
- 凭证与敏感配置
- 删除、覆盖等破坏性操作
- commit、push、PR、部署和发布

如果依赖缺失或同时发现多个可信副本，路由器会停止并报告精确的 Skill 名称，不会猜测机器相关路径。

## 前置条件

- 支持 Plugins 的 Codex App 或 Codex CLI
- Node.js 与 `npx`，用于安装 Matt Pocock Skills
- 可访问 GitHub 与 Codex Plugins marketplace 的网络环境

## 安装依赖

### 1. Matt Pocock Skills

运行上游安装器：

```bash
npx skills@latest add mattpocock/skills
```

选择下方列出的必需 Skills，并额外安装 `setup-matt-pocock-skills`。之后在要使用路由器的项目中运行 `setup-matt-pocock-skills`，完成项目级术语、Issue Tracker 与工作规则配置。

该上游配置流程会先检查项目，展示发现结果和准备执行的修改，并请求你的确认。确认后，它会编辑现有的项目级 `CLAUDE.md` 或 `AGENTS.md`；如果两者都不存在，会先询问要创建哪一个。它还会写入 `docs/agents/issue-tracker.md` 和 `docs/agents/domain.md`；安装了 `triage` Skill 时，也可能写入 `docs/agents/triage-labels.md`。这些都是经过确认的项目级写入，不是本路由器对全局 `AGENTS.md` 的静默修改。

### 2. Superpowers

- Codex App：打开官方 Plugins marketplace，搜索 **Superpowers** 并安装。
- Codex CLI：输入 `/plugins`，搜索 **Superpowers**，选择 **Install Plugin**。

## 安装本插件

添加 marketplace 并安装插件：

```bash
codex plugin marketplace add nuts-and-bytes/zero-to-one-product
codex plugin add zero-to-one-product@zero-to-one-product
```

安装或更新后请新建一个 Codex 对话，让 Codex 刷新 Skill 目录。

## 使用方法

显式调用是最可靠的入口：

```text
$zero-to-one-product <你的产品想法或当前 0→1 目标>
```

例如：

```text
$zero-to-one-product 我想做一个帮助独立开发者验证 SaaS 想法的网站，目前还没有代码库。
```

路由器也可以被自动触发，但其他安装环境中的 `AGENTS.md` 可能包含冲突的全局流程规则。本插件不会静默修改用户的全局 `AGENTS.md`。

## 必需的外部 Skills

Matt Pocock Skills（12 个）：

- `grill-me`
- `grill-with-docs`
- `wayfinder`
- `grilling`
- `domain-modeling`
- `research`
- `prototype`
- `to-spec`
- `to-tickets`
- `diagnosing-bugs`
- `code-review`
- `handoff`

`grilling` 和 `domain-modeling` 是 Wayfinder 内部使用、仅通过 Skill catalog 解析的依赖；它们不是外层流程 owner，也不使用文件系统 fallback。

Superpowers Skills（7 个）：

- `using-git-worktrees`
- `writing-plans`
- `test-driven-development`
- `systematic-debugging`
- `requesting-code-review`
- `verification-before-completion`
- `finishing-a-development-branch`

完整依赖清单和上游链接见 [`dependencies.md`](plugins/zero-to-one-product/skills/zero-to-one-product/references/dependencies.md)。

## 更新

刷新 marketplace：

```bash
codex plugin marketplace upgrade zero-to-one-product
```

然后通过 Codex Plugins 界面更新或重新安装 **Zero-to-One Product**。Matt Pocock Skills 与 Superpowers 需要通过各自的上游安装方式单独更新。完成后新建一个 Codex 对话。

## 卸载

```bash
codex plugin remove zero-to-one-product@zero-to-one-product
```

这只会移除路由插件，不会删除独立安装的 Matt Pocock Skills 或 Superpowers。

## 故障排查

如果路由器报告依赖缺失：

1. 记录缺失的精确 Skill 名称及其所属项目。
2. 按照上面的方式安装或更新对应上游项目。
3. 如果属于 Matt Pocock Skills，在当前项目中完成 `setup-matt-pocock-skills`。
4. 新建对话并显式调用 `$zero-to-one-product`。

如果报告依赖存在歧义，请移除或禁用过期的重复安装，确保该 Skill 只有一个可信副本，然后新建对话。不要把机器相关的 Skill 绝对路径写进路由器。

## 分发安全

本仓库不包含 MCP server、hook、运行时脚本、凭证或私人数据。插件只打包路由 Skill 与相关文档。仓库内的分发验证脚本仅供维护者检查，普通用户无需执行。
