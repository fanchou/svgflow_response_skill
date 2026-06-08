# SVGFlow Response Skill

这是一个用于将“助手回答”转换为紧凑 SVG 流程图的 Skill 包。

## 定位

它不是直接读取用户原始 prompt 画图，而是读取助手已经生成的解释型回答，从中提取流程结构，构建 Flow DSL，规划布局，渲染 SVG，并在输出前进行校验和修复。

## 常用命令

发布或修改前运行：

```bash
python3 scripts/validate_svg.py --package .
```

检查流程元素覆盖度：

```bash
python3 scripts/validate_svg.py --coverage .
```

检查国际化覆盖：

```bash
python3 scripts/validate_svg.py --i18n .
```

## 输出模式

| mode | 说明 |
|---|---|
| `preview_svg` | 可单独预览的 SVG，包含样式 |
| `raw_svg` | 不包含样式，依赖宿主 CSS |
| `html_preview` | 完整 HTML，内嵌 SVG |
| `component_ready` | 适合前端组件集成的 class-based SVG |

## 国际化约定

主包默认使用英文说明。除这个中文 README 外，其他文件不应出现不必要的中文。流程节点、连线标签、标题和描述应保留输入回答的主要语言，并通过 `meta.locale` 和 `meta.textDirection` 标记语言与方向。
