# SVGFlow Response Infographic Skill

这是一个用于将“助手回答”转换为紧凑 SVG 或 HTML 信息图的 Skill 包。

## 定位

这是一个 Response-to-Infographic 后处理 Skill。它不直接根据用户原始 prompt 作图，而是读取助手已经生成的解释型回答，尽可能构建通用 infographic DSL，规划布局，渲染有效的 SVG 或 HTML，并在输出前进行校验和一次修复。

## 通用模型

新工作应优先使用 `diagramType: "infographic"`，只有在兼容旧 fixture 或特定渲染器确实需要时，才使用专门的旧图形家族。

通用 DSL 将内容语义和视觉形状分离：

- `content.nodes`：实体、动作、容器、决策、指标、注释和输出
- `content.groups`：容器、层级、区域、章节和泳道
- `content.edges`：流程、控制、数据、依赖和反馈关系
- `content.labels`：标注和说明
- `content.legends`：色调和符号说明
- `content.steps`：可选的 walkthrough 状态
- `interactions`：点击、分步、高亮、切换和 prompt 动作
- `layout.intent`：`linear`、`layered`、`loop`、`matrix`、`hub_spoke`、`timeline`、`swimlane`、`comparison`、`hierarchy`、`dashboard` 或 `freeform`

模板选择定义在 `templates/infographic-templates.json` 中。模板是 v2 预设，不是新的 schema 家族。

## 兼容和专用图形家族

旧图形家族主要用于兼容场景，对应的 v2 映射定义在 `schemas/legacy-to-infographic-map.json`。

| family | DSL `diagramType` | 输出 |
|---|---|---|
| Universal infographic | `infographic` | 大多数 SVG 或 HTML 信息图的首选 v2 结构 |
| Flowchart | `flowchart` | 紧凑的 SVG 流程、分支、重试或错误流 |
| Knowledge map | `knowledge_map` | 带章节和原则网格的官方风格交互式 SVG |
| Architecture map | `architecture_map` | 带嵌套区域和标签的分层 SVG 信息架构 |
| Interactive walkthrough | `interactive_walkthrough` | 带步骤控制、进度点和 CSS 动画的 HTML 预览 |
| System loop | `system_loop` | 带参与者、信号、守卫和次级路径的紧凑反馈环 SVG |
| Module grid | `module_grid` | 带模块、徽章、语义色调、图标和 CTA 的 HTML 卡片网格 |
| Agentic pipeline | `agentic_pipeline` | 扇出/汇入的 agent 工作流，包含 worker、知识源、综合器、输出和重规划环 |
| Phased pipeline | `phased_pipeline` | 长纵向生命周期管线，包含阶段容器、本地流程、旁注和图例 |

## 常用命令

发布前运行完整检查：

```bash
python3 scripts/validate_svg.py --release-check .
```

运行生产管线 fixture：

```bash
python3 scripts/run_pipeline_fixture.py --root . --case production_freeform_growth
python3 scripts/run_pipeline_fixture.py --root . --case production_unknown_experiment_priority
python3 scripts/run_pipeline_fixture.py --root . --case production_walkthrough_html
```

生产管线 fixture 会同时校验 DSL 和 SVG/HTML 产物。SVG 用例会检查视觉质量、可读性、文本适配、转义安全和交互可访问性；HTML 用例会检查生产 HTML 合约、渲染区域和转义安全。

调试包结构：

```bash
python3 scripts/validate_svg.py --package .
```

检查常见质量门：

```bash
python3 scripts/validate_svg.py --coverage .
python3 scripts/validate_svg.py --i18n .
python3 scripts/validate_svg.py --text-fit .
python3 scripts/validate_svg.py --escaping-safety .
python3 scripts/validate_svg.py --interaction-accessibility .
python3 scripts/validate_svg.py --production-svg-contract .
python3 scripts/validate_svg.py --production-html-contract .
python3 scripts/validate_svg.py --render-surface .
```

当本机有 Chrome 或 Chromium 时，可以运行浏览器渲染指标检查：

```bash
node scripts/check_browser_render_metrics.mjs --root . --cases tests/browser_render_metric_cases.json
```

## 输出模式

| mode | 说明 |
|---|---|
| `preview_svg` | 可单独预览的 SVG，包含内嵌样式 |
| `raw_svg` | 不包含样式，依赖宿主 CSS |
| `html_preview` | 完整 HTML 文档，内嵌 SVG |
| `component_ready` | 适合前端组件集成的 class-based SVG |

`raw_svg` 和 `component_ready` 会保留 `class="svgflow"`、`data-svgflow-id`、节点颜色 class 和 marker id。宿主 CSS 可从 `templates/host_css.template.css` 开始。

## 国际化约定

Skill 会保留源回答中的标签语言。DSL metadata 包含 `meta.locale` 和 `meta.textDirection`；渲染后的 flowchart SVG 包含匹配的 `xml:lang`、`lang` 和 `dir` 属性。官方风格交互示例也会保留用户语言中的可见标签和 prompt。

中文文本应限制在 `README.zh-CN.md` 以及专用 i18n fixture 中，例如 `locales/signals.json`、`examples/chinese_*` 和用于验证语言保留能力的官方风格中文示例。其他文件应避免不必要的中文。
