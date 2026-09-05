# Image to Figma Precision

将截图或图片设计稿还原为 Figma 中可编辑、可分层的设计，适合游戏 UI、移动端界面和含复杂插画的设计稿。

这是一个供 AI 助手使用的 **skill 与辅助脚本集合**。它提供拆解、构建、透明素材处理和验收流程；实际写入 Figma 需要另外连接具有写入能力的 Figma 工具。

## 能做什么

- 将按钮、卡片、资源项、导航等拆成独立组件，重复结构使用实例。
- 将可见文字重建为原生可编辑 TEXT，校准字体、尺寸、位置和字距。
- 分离背景、图标、装饰和文字，检查图标真实透明度、孔洞、高光和残留底色。
- 对遮挡区域进行局部推断补全，并通过组件移动、隐藏测试检查底板与残影。
- 比较原图与 Figma 的同尺寸 1× 导出，输出全图和局部误差、叠加图、差异图。
- 保存节点 ID、素材哈希和迭代状态，支持中断后恢复。

复杂插画可以保留为独立位图。像素误差通过不代表文字、组件结构与可编辑性同时通过，也不等于“100% 相似”。

## 仓库结构

```text
.
├── README.md
└── image-to-figma-precision/
    ├── SKILL.md                 # 助手入口与工作流程
    ├── requirements.txt         # 本地 Python 脚本依赖
    ├── references/              # 分层、后端、透明素材、计划与验收规范
    └── scripts/                 # 构建模板、结构审计、像素与透明度检查
```

只需保留整个 `image-to-figma-precision/` 文件夹即可分发 skill。开发过程中的原图、生成素材、任务状态、日志、模型和本机 MCP 安装目录不属于发布内容。

## 安装

### 1. 获取并安装 skill

```bash
git clone https://github.com/SmallKi/image-to-figma-precision.git
cd image-to-figma-precision
```

将仓库内的 `image-to-figma-precision/` 文件夹复制到助手的 skill 目录，保留内部目录结构。Codex 可使用 `$CODEX_HOME/skills/`，未设置 `CODEX_HOME` 时使用用户目录下的 `.codex/skills/`。安装后在新会话中确认能找到 `$image-to-figma-precision`。

### 2. 安装 Python 依赖

建议使用独立虚拟环境。以下命令在仓库根目录执行：

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\python.exe -m pip install -r image-to-figma-precision/requirements.txt
# macOS / Linux
.venv/bin/python -m pip install -r image-to-figma-precision/requirements.txt
```

下文的 `python` 指向已安装依赖的解释器。脚本依赖 NumPy 和 Pillow；无需安装图像生成模型即可运行像素比较和离线检查。

### 3. 连接 Figma 写入工具

可使用已配置的 Figma 写入工具，或 Southleft 的 Figma Console MCP 本地后端。后者需要 Node.js、Figma 桌面端和 Desktop Bridge 插件。本项目参考的是 `figma-console-mcp@1.40.0`，连接、导出及恢复说明见 [本地后端指南](image-to-figma-precision/references/local-console.md)。

安装 skill 本身不会安装 MCP，也不会自动获取 Figma 文件权限。助手应先确认目标文件和真实插件往返，再开始构建。

## 使用示例

在支持该 skill 的助手会话中提供源图片和目标 Figma 文件链接：

```text
使用 $image-to-figma-precision 将这张设计稿还原到指定 Figma 文件的新页面。
保留原图布局与文案，文字可编辑，按钮、图标和卡片独立组件化。
先完成拆解清单，再分批构建，最后输出像素比较、结构审计和剩余差异。
```

典型流程：

1. 记录源图尺寸与哈希，确认目标文件、字体和可调用的写入工具。
2. 建立分层清单与构建计划，保存 `manifest.json`、`state.json`、`iterations.json`。
3. 准备并验收独立素材，分批写入，及时保存工具返回的节点 ID。
4. 导出同尺寸整屏图和透明组件图，分别检查像素、结构与可编辑性。
5. 依据证据迭代，交付 Figma 链接、截图、报告及未解决问题。

图像编辑、遮挡补全和素材重生需要当前环境另有可用的图像工具；本仓库不包含这类模型或服务。

## 脚本说明

| 脚本 | 用途 |
| --- | --- |
| `compare.py` | 比较同尺寸源图与导出图，生成指标、叠加图和差异图 |
| `audit-alpha.py` | 检查原始 Alpha、尺寸、边界与透明覆盖情况 |
| `audit-cutout.py` | 按 JSON 合同验证保留区、透明区、孔洞、轮廓和源 RGB |
| `render-cutout-proof.py` | 生成白、黑、洋红、青色背景及 Alpha、边缘证据图 |
| `extract-chroma-cutout.py` | 使用已知纯色底与独立 Alpha 修复边缘混色 |
| `test-edge-cleanup.py` | 运行无需 Figma 或模型的合成素材回归检查 |
| `prepare-batch.py` | 将审核后的计划和节点状态转换为有限批量的 JS |
| `apply-batch.js` | 批量创建基础节点的 Figma Plugin API 模板 |
| `componentize-one.js` | 将一个已完成容器转换为主组件并替换为实例 |
| `audit-figma.js` | 审计 Figma 根节点下的组件、文字与图像结构 |

Python 命令示例：

```bash
python image-to-figma-precision/scripts/compare.py reference.png candidate.png --regions manifest.json --out outputs/iteration-01
python image-to-figma-precision/scripts/audit-alpha.py icon.png --out outputs/icon-alpha.json
python image-to-figma-precision/scripts/render-cutout-proof.py icon.png --out outputs/icon-proof.png
python image-to-figma-precision/scripts/audit-cutout.py icon.png contract.json --out outputs/icon-cutout.json
python image-to-figma-precision/scripts/prepare-batch.py plan.json state.json --count 8 --out next-batch.js
```

执行报告命令前，先创建需要的输出父目录。`compare.py` 可省略 `--regions`；传入的 JSON 使用 `{"regions":[{"key":"title","box":[0,0,100,40]}]}` 格式，坐标必须落在源图内。比较器将透明图合成到白底后比较 RGB，透明质量需另用 Alpha 与抠图审计判断。比较器会输出 `pixel_gate_pass`，调用成功或退出码为 0 本身不表示该门禁通过。

批处理数据格式见 [构建计划](image-to-figma-precision/references/plan-format.md)。`sourceHash` 是 Figma 上传图像返回的哈希，`pageId` 与节点 ID 必须来自真实工具返回。JS 文件运行于 Figma Plugin API 环境，不能当作普通 Node.js 程序直接写入画布；`prepare-batch.py` 仅生成代码，执行后还需合并返回的 mapping 才能继续下一批。

## 验证

```bash
python image-to-figma-precision/scripts/test-edge-cleanup.py --out outputs/edge-cleanup
```

该回归使用自动生成的测试图验证边缘去污染、高光、孔洞与细杆保留，无需私人素材。它只验证离线图像处理行为；在线组件构建仍应按 [验收规范](image-to-figma-precision/references/acceptance.md) 实测。

## 进一步阅读

- [Skill 完整流程](image-to-figma-precision/SKILL.md)
- [分层重建](image-to-figma-precision/references/reconstruction.md)
- [透明图标验收](image-to-figma-precision/references/transparent-icons.md)
- [边缘去污染](image-to-figma-precision/references/edge-cleanup.md)
- [透明素材生成](image-to-figma-precision/references/transparent-generation.md)
- [Figma Console MCP 上游项目](https://github.com/southleft/figma-console-mcp)
