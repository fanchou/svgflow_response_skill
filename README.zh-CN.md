# SVGFlow Response Infographic Skill

SVGFlow 是一个 Codex Skill，用来把“助手已经生成的回答”转换成紧凑、有效、可预览的 SVG 或 HTML 信息图。

它适合作为回答后的可视化后处理步骤：不直接根据用户原始 prompt 作图，而是读取助手回答，提取适合视觉化的结构，构建 DSL，选择布局，渲染 SVG 或 HTML，校验产物，并在有明确信号时修复一次。

## 什么时候使用

当回答适合变成视觉产物时使用这个 Skill：

- 工作流、决策、重试和错误路径
- 技术管线、系统执行流和数据流
- 架构图、分层系统和模块关系
- 知识地图、原则网格和结构化解释
- 产品、业务、客服、可靠性或运营类信息图
- 需要步骤控制的交互式 walkthrough

不适合用于纯聊天回答、很短的事实回答，或需要凭空补充大量外部信息的视觉内容。

## 安装

安装器本身不绑定某个 agent：它只是把运行时 Skill 文件夹复制到任何“基于目录发现 Skills”的 agent skills 目录。唯一要求是安装后的 Skill 文件夹必须把 `SKILL.md` 放在根目录。

直接用 `npx` 从 GitHub 安装：

```bash
npx github:fanchou/svgflow_response_skill --skills-dir <agent-skills-dir>
```

发布到 npm 后，也可以这样安装：

```bash
npx svgflow-response-skill --skills-dir <agent-skills-dir>
```

如果安装给 Codex，通常可以省略 `--skills-dir`。安装器会默认使用 `$CODEX_HOME/skills`，然后回退到 `~/.codex/skills`：

```bash
npx github:fanchou/svgflow_response_skill
```

如果安装给其他 agent，请显式传入那个 agent 的 skills 目录：

```bash
npx github:fanchou/svgflow_response_skill --skills-dir /path/to/agent/skills
```

安装后的结构是：

```text
<agent-skills-dir>/
  svgflow-response/
    SKILL.md
    agents/openai.yaml
    locales/
    prompts/
    schemas/
    templates/
    validators/
```

安装器只复制运行时需要的 Skill 文件，不会复制测试、changelog、发布 fixture 等仓库维护文件。

如果已经 clone 了仓库，可以运行本地 Node 安装器：

```bash
node scripts/install-skill.mjs --source /path/to/svgflow_response_skill --skills-dir <agent-skills-dir>
```

也保留了 Python 安装器，方便偏好 Python 的环境：

```bash
python scripts/install_skill.py --source /path/to/svgflow_response_skill --skills-dir /path/to/agent/skills
```

手动安装也可以：把仓库根目录、或打包好的 runtime 文件夹，复制或软链接到 `<agent-skills-dir>/svgflow-response`。关键是 `SKILL.md` 必须直接位于这个文件夹内。

安装后重启对应 agent 或开启一个新会话，让它重新发现 Skill metadata。

## 在 Codex 里怎么用

启用后，可以让 Codex 把已有回答可视化为 SVGFlow 信息图、SVG、HTML 预览、架构图、工作流或 walkthrough。

关键输入是“要被可视化的助手回答”。这个 Skill 不应该凭空补充缺失的业务逻辑，也不应该重新回答原始问题。

## 会产出什么

| 输出模式 | 适合场景 |
|---|---|
| `preview_svg` | 可独立预览的 SVG，包含内嵌样式 |
| `raw_svg` | 嵌入已有应用，由宿主 CSS 提供样式 |
| `html_preview` | 完整 HTML 预览，包含内嵌 SVG 和交互控件 |
| `component_ready` | 适合前端组件集成的 class-based SVG |

默认模式是 `preview_svg`。`raw_svg` 和 `component_ready` 会保留 `class="svgflow"`、`data-svgflow-id`、节点颜色 class 和 marker id，方便宿主应用继续样式化或检查输出。

## 支持的视觉家族

新工作应优先使用 `diagramType: "infographic"`，只有在 fixture、渲染器或明确请求需要时才使用专门家族。

| Family | DSL `diagramType` | 用途 |
|---|---|---|
| Universal infographic | `infographic` | 大多数通用 SVG 或 HTML 信息图 |
| Flowchart | `flowchart` | 流程、分支、重试或错误流 |
| Knowledge map | `knowledge_map` | 带章节的知识地图和原则网格 |
| Architecture map | `architecture_map` | 带区域、标签和关系的分层系统 |
| Interactive walkthrough | `interactive_walkthrough` | 带步骤、进度和动画的 HTML 预览 |
| System loop | `system_loop` | 带参与者、信号、守卫和支路的反馈环 |
| Module grid | `module_grid` | 带徽章、语义色调、图标和动作的 HTML 模块卡片 |
| Agentic pipeline | `agentic_pipeline` | 带综合和重规划的扇出/汇入 agent 工作流 |
| Phased pipeline | `phased_pipeline` | 带阶段、旁注和图例的长生命周期管线 |

## 工作方式

这个 Skill 会把内容语义和视觉布局分开处理：

1. 解析助手回答。
2. 构建选定 DSL，优先使用通用 infographic DSL。
3. 选择布局意图，例如 `linear`、`layered`、`loop`、`matrix`、`hub_spoke`、`timeline`、`swimlane`、`comparison`、`hierarchy`、`dashboard` 或 `freeform`。
4. 基于模板渲染 SVG 或 HTML。
5. 校验可读性、文本适配、转义安全、可访问性和生产合约。
6. 当校验给出明确修复信号时修复一次。

模板选择定义在 `templates/infographic-templates.json`。旧家族到 v2 的映射定义在 `schemas/legacy-to-infographic-map.json`。

## 项目结构

这个仓库是开发包。真正安装到 Codex 的运行时 Skill，是 `scripts/install_skill.py` 复制的子集。

| 路径 | 用途 |
|---|---|
| `SKILL.md` | Codex Skill 运行时说明 |
| `agents/openai.yaml` | Skill 列表和 chip 使用的 UI metadata |
| `skill.json` | 这个仓库的包 metadata |
| `schemas/` | DSL 和布局 schema |
| `prompts/` | 解析、DSL 构建、布局、渲染和修复 prompt |
| `templates/` | SVG、HTML、宿主 CSS 和信息图模板预设 |
| `validators/` | 校验清单和修复规则 |
| `scripts/install-skill.mjs` | 兼容 npx 的安装器 |
| `scripts/install_skill.py` | 用于本地/source 安装的 Python 安装器 |
| `examples/` | 开发 fixture，运行时不必安装 |
| `tests/` | 正向和负向 fixture 用例 |
| `docs/production-checklist.md` | 维护者发布检查清单 |

## 维护者检查

大多数使用者不需要运行这些命令。它们主要给修改 schema、prompt、模板、示例或校验器的贡献者使用。

运行发布检查：

```bash
python3 scripts/validate_svg.py --release-check .
```

运行代表性生产 fixture：

```bash
python3 scripts/run_pipeline_fixture.py --root . --case production_freeform_growth
python3 scripts/run_pipeline_fixture.py --root . --case production_unknown_experiment_priority
python3 scripts/run_pipeline_fixture.py --root . --case production_walkthrough_html
```

开发时运行重点检查：

```bash
python3 scripts/validate_svg.py --package .
python3 scripts/validate_svg.py --coverage .
python3 scripts/validate_svg.py --i18n .
python3 scripts/validate_svg.py --text-fit .
python3 scripts/validate_svg.py --escaping-safety .
python3 scripts/validate_svg.py --interaction-accessibility .
python3 scripts/validate_svg.py --production-svg-contract .
python3 scripts/validate_svg.py --production-html-contract .
python3 scripts/validate_svg.py --render-surface .
```

如果本机有 Chrome 或 Chromium，可以运行浏览器渲染指标检查：

```bash
node scripts/check_browser_render_metrics.mjs --root . --cases tests/browser_render_metric_cases.json
```

## 国际化约定

Skill 会保留源回答中的标签语言。DSL metadata 包含 `meta.locale` 和 `meta.textDirection`；渲染后的 flowchart SVG 包含匹配的 `xml:lang`、`lang` 和 `dir` 属性。

中文文本应限制在 `README.zh-CN.md` 以及专用 i18n fixture 中，例如 `locales/signals.json`、`examples/chinese_*` 和用于验证语言保留能力的官方风格中文示例。
