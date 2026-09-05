# 透明图标生成协议

## 能力与调用

GPT Image 的透明背景是输出参数，不只是提示词。调用层若暴露图像输出选项，必须显式设置：

```json
{
  "background": "transparent",
  "output_format": "png"
}
```

也可使用支持 Alpha 的 WebP；不能使用 JPEG。是否支持透明输出以当前接口 schema 与实际文件为准。权威说明：[OpenAI Image generation — Customize Image Output](https://developers.openai.com/api/docs/guides/image-generation#customize-image-output)。

调用前先检查当前工具 schema：

1. 工具暴露 `background` 时，传 `transparent`；暴露 `output_format` 时传 `png`。
2. 工具只暴露 `prompt` 和参考图时，在提示中明确真实 RGBA，但把它视为无保证的请求。
3. 不得声称“提示词写了透明，所以结果透明”。保存后立即读取 PNG mode、Alpha 唯一级数、透明/半透明/不透明像素数。
4. 若结果为 RGB、Alpha 全 255、棋盘格被烘焙、主体大部分半透明，从原始参考重新生成一次；不要继续编辑失败图。
5. 若需要切换到直接 API/CLI 以显式传参，遵守运行环境的授权和密钥流程，不能偷偷换模型或接口。

同一任务、同一调用接口已连续两次输出 RGB/烘焙棋盘格时，记录该次能力探测失败并停止这条透明提示重试路线，不为后续每个图标重复两次。这不证明所有接口或模型均不支持透明，只说明当前调用未满足 Alpha 合同。转用任务已允许且可验证的独立抠图流程；若需要新的 API/模型授权，保存失败样本后明确说明，不能把棋盘格图当作透明素材交付。

## 先隔离参考与边缘颜色

按 [edge-cleanup.md](edge-cleanup.md) 准备单个对象的局部参考，明确哪些颜色来自主体、哪些来自旧底板/相邻元素。原图混色边带是待修区域，不能要求模型原样保留其 RGB；可靠实体内区仍保持原样。只修边缘时使用该文档的局部模板；用户允许整体重绘时才使用下面的生成模板。

透明提示中禁止“如果不能透明就白底/绿底”之类替代条款。纯色底候选是独立流程，不能与真 RGBA 请求混写；尤其不能用白底去隔离带白色高光的物体，再全局按白色挖空。

## 为目标尺寸生成

重生图不要求逐像素复制低分辨率原图。先记录目标显示尺寸，再按该尺寸约束生成：

- 明确写出“最终缩小到 W×H px 使用”。
- 颜色风格：主色、暗部、轮廓色、高光色分别描述。
- 轮廓风格：粗细、圆角、对称性和剪影比例；小尺寸简化仅限用户允许重绘时，原图中的合法细枝不可因去边缘污染而删除。
- 结构：列出必须存在的主体、手把、徽记、叶片等；孔洞逐项列出。
- 小尺寸可读性：先检查目标尺寸可读性；只有用户允许设计简化时才减少高频纹理或调整孔洞，精确还原保持原结构。
- 不透明主体：实体内部 Alpha=255；仅外轮廓和孔洞内沿的窄带用部分 Alpha 抗锯齿；约 1–2 px 指最终显示尺寸，工作分辨率按比例换算。
- 透明区域：画布外部和真实孔洞 Alpha=0；禁止棋盘格、底板、光晕、投影和文字。

推荐模板：

```text
Use case: isolated-asset-redraw (only when redraw is authorized)
Asset type: game UI icon, final display size <W×H px>
Input images: Image 1 supplies subject and palette; Image 2 supplies outline/rendering style (if present)
Primary request: redraw one isolated <subject>; preserve silhouette, proportions, orientation, palette and original outline thickness; simplify details only if authorized
Composition: centered, transparent safety margin, front/side orientation as reference
Color palette: <main>, <shadow>, <outline>, <highlight>
Must keep: <semantic parts and light highlights>
Must be transparent: canvas outside; <named holes/gaps>
Reference contamination: <sampled old matte/neighbor colors> belong to the background, not the subject palette.
Edge RGB: reconstruct the narrow mixed-color boundary from adjacent foreground material/outline colors, including hole rims; do not copy old matte spill, bake a white/black fringe, shrink the silhouette or thicken the outline.
Alpha contract: subject interior Alpha=255; a narrow antialias band on outer and hole contours may be partial (about 1–2 px at final display size, scaled at working resolution); outside and named holes Alpha=0
Avoid: checkerboard, opaque background, halo, cast shadow, text, extra decoration, microtexture that disappears at target size
Output: true RGBA PNG with transparent background
```

## 自动验收与重试

生成后先运行 `audit-alpha.py`，再为素材建立 `audit-cutout.py` 合同。至少包含：

- `alphaCoverage.min/max`：主体面积范围。
- `alphaCoverage.minOpaqueFractionOfForeground`：普通实体图标建议从 0.8 起校准，拒绝整体半透明。
- `keep`：高光、浅色纸面、皮肤等必须不透明。
- `holes/outside`：真实孔洞与画布外部必须透明。
- `expectedEnclosedHoles`：孔洞数量。
- `componentPolicy`：主体与合法分离零件数量。
- `edgePolicy`：Alpha 层级、突跳、孤立点、尖刺、针孔和已知底色。

第一轮失败时只改一个原因：RGB/棋盘格失败就加强输出与 Alpha 合同；主体半透明就明确实体 Alpha=255；小尺寸糊成一团先检查生成分辨率和预乘缩放；仅在允许设计简化时调整纹理与孔洞；风格漂移就补颜色/轮廓参考。边缘杂色失败时转到 edge-cleanup.md，区分 Alpha 错误与 RGB 混色，不能只追加“更透明”。透明和边缘颜色均通过后才以预乘 Alpha 缩放到目标尺寸并执行 Figma 4×、白黑洋红青色、默认/移动/隐藏回归。

常规后处理限于裁切、配准和预乘 Alpha 缩放（缩放会改变采样，并非无损）。不得用轮廓拟合、腐蚀、膨胀或颜色键修补来掩盖生成缺陷；这类操作必须作为独立候选方法记录，不能算“生成阶段已解决”。
