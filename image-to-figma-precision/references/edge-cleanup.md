# 边缘去污染：轮廓与颜色分开求解

出现原图底板色、邻接装饰色、白边或黑边时，先读本页。透明 Alpha、平滑轮廓、干净 RGB 是三项独立条件；有半透明像素不代表无杂色。

## 识别污染来源

保存配准后的原始局部、候选、实际显示尺寸与背景采样位置。检查外轮廓和每个孔洞内沿，不能只看图标最外圈。

| 证据 | 判断与下一步 |
| --- | --- |
| 边缘出现相邻文字、线条、底板色 | 前景范围选大或原图混色被复制。标明这些区域不是对象，重新分割/局部重建边缘 |
| Alpha 已合理，换底仍有原底色环 | 边缘 RGB 被原底色污染。已知底色且有独立 Alpha 时反混色；背景复杂时局部重建前景色 |
| 边缘在不同底色上均异常发暗 | 检查是否把预乘 RGB 当 straight RGB 写入 PNG，或对干净 RGBA 再次反混色 |
| 高分辨率干净，缩小才出现彩点 | 检查缩放是否在预乘 Alpha 上进行，以及透明像素的隐藏 RGB；只在最终阶段缩放一次 |

Alpha=255 的边缘也可能带原背景颜色，例如颜色键把混色像素提前饱和成不透明。不能只审计半透明像素，也不能只查“接近原底色”的像素：金色与青色混合后可能两者都不像。已知底色距离只是线索，逐段换底目视仍是必要门禁。

## 输入准备

1. 每次只传一个对象的原始局部，保留细枝、合法分离零件及少量背景取样带。记录裁片到原图的变换。上下文图另标为定位参考；箭头、标注、选框放在单独参考中，不烧进编辑目标。
2. 写明 `属于前景`、`属于背景/邻接物`、`不确定的混色边带`。从实体内区取主体色/描边色，从对象外侧取旧底色，不能把边缘混色当目标色板。背景存在渐变或邻接多色时分别记录，不能取四角平均代替整个边缘背景。
3. 选择“局部边缘修复”或“允许重绘整个图标”；默认前者。保持可靠内区像素，允许修复受污染边带，不要求逐像素复制原图混色边。不得通过全局收缩、增粗描边、模糊或降低主体 Alpha 隐藏污染。
4. 透明请求中不写“无法透明就白底/绿底”。纯色底是单独记录的后备候选，需使用不同提示词并完成抠图。失败候选用于诊断，下一次编辑仍以原始局部为目标。

低分辨率素材优先使用原始尺寸局部作为生成参考。用于审计的 8× 最近邻放大图会突出方块，模型可能把它当像素画风复制；不要将它作为平滑插画的默认编辑目标。需要放大以便识别时，明确它只是结构参考，并保留原始裁片对照。平滑原轮廓与保留可靠内区纹理分别约束，不能把检查用放大图的像素块当成应保留纹理。

## 局部边缘修复模板

填完尖括号里的清单；不要只追加“更干净、更精准”。

```text
Edit one isolated <subject> from Image 1. Final use: <W x H> px;
working canvas: <dimensions>, subject bounds: <box>, orientation: <direction>.
Image 1 is the source design. <Image 2, if supplied, is context only; copy no pixels or objects from it.>
Keep the registered silhouette, proportions, internal texture, lighting and original outline thickness.
Preserve these solid parts and highlights: <explicit list, including thin/detached parts>.
Remove these background/neighbor elements: <old panel color, nearby text, baseline, ornament>.
Transparent holes: <each real hole and gap; say none for a solid subject>.

The reference's boundary pixels already contain mixed-in <sampled old background colors>.
They are contamination, not the object's palette or an intentional rim light.
Repair that narrow uncertain boundary, including the inner rims of holes.
Preserve reliable opaque interior pixels; do not copy contaminated edge RGB unchanged.
Use the adjacent object's own <outline/material colors> for the repaired edge RGB.
Encode edge coverage with alpha, not by blending RGB toward white, black or the old background.
Remove attached color spill and detached background scraps while retaining <legitimate detached parts>.
Do not shrink the silhouette, thicken the outline, blur the edge, remove pale highlights,
add a new border, or make the solid subject translucent to hide the contamination.

Output one true RGBA PNG: solid interior alpha 255; exterior and named holes alpha 0;
a narrow smooth partial-alpha band follows the contour at the working resolution.
No colored matte, checkerboard, mockup, glow, new cast shadow, labels or comparison sheet.
The same edge must remain clean on white, black, magenta, cyan and the target UI background.
```

这是生成目标，不是工具能力保证。实际文件没有 Alpha 时按透明生成协议切换方法。色带仍污染但形状正确时只修色；几何也错时回到分割，不能继续在错误 Alpha 上反混色。

## 可测量的纯色底反混色

仅用于已知纯色底的合成 RGB，且 Alpha 来自同坐标的独立分割/高分辨率遮罩。`C = αF + (1−α)B` 中 C 是旧背景上看到的混色，交付 PNG 的 RGB 应是 F。脚本在输入 RGB 编码下求解；如果源混合发生在线性光空间、带压缩/调色，或背景不是常量，不适用这个简单模型。不要对已干净 RGBA 再做一次反混色。

```bash
python scripts/extract-chroma-cutout.py matte.png candidate.png --alpha-mask reviewed-alpha.png --background-rgb 24,96,112 --border 4 --report candidate.json
```

- `reviewed-alpha.png` 是与 RGB 同尺寸的 8 位灰度 Alpha，不是对象截图或亮度图。必须有经过配准确认的抗锯齿覆盖率；二值遮罩不能解开混色。保留细枝、孔洞、高光的语义合同仍适用。
- `--border` 必须落在真正的空背景带；脚本检查其颜色一致性。背景带不一致、物体触边、烘焙棋盘格或多色背景时换方法，不能提高容差把失败压过去。外边一致也不证明对象周边及孔洞内背景一致，仍需人工确认。
- 默认保持原画布，不自动裁切。确需裁切时显式 `--trim`；目标适配用 `--target-size WxH --target-box x,y,w,h`，从报告记录 sourceCrop 和目标变换后重新配准。
- `--allow-heuristic-alpha` 才启用旧颜色距离方案，它只是候选。`--high` 不是物理 Alpha：某个 α=0.5 的像素可能已被判成 α=1，旧底色因此留在 RGB。高光/前景与底色近似时，不采用此路线。
- 报告记录 Alpha/不透明 RGB 是否改变、反推越界比例、低 Alpha 像素数及输入哈希；越界或低 Alpha 集中区需复核，不能把裁到 0..255 当成功。α 很小时量化噪声被放大，没有可靠信息就局部重建，不强称恢复原像素。

这个脚本是可选的程序化候选流程，只有当前任务允许这类处理时使用；默认图像编辑工具仍按当前环境要求选择。脚本输出始终为 `candidate-needs-visual-review`。

## 修复后验收

先在少量代表性素材上验证：带浅色高光的实体、带内孔的图标、细枝/细描边。依次审计候选原生尺寸、最终 1× 显示尺寸、Figma 原生 4× 导出；证据图可用 `render-cutout-proof.py`，不得把本地放大说成 Figma 导出。

白/黑/洋红/青色与实际 UI 底色逐段检查外沿和孔沿，既看部分 Alpha，也看贴着它的实体边沿。半透明带通常在最终 1× 占约 1–2 px；高分辨率工作图按比例理解，不能强制其也只占 1–2 px。透明边距、孔洞透底、内区高光、描边粗细、碎片与原图配准全部通过后才写入。

不要用 `sourceRgbIntegrity` 要求受污染边带仍逐像素等于源图；该项约束可靠不透明内区，边带改变单独记录并目视复核。如果旧 Alpha=255 边缘已污染，先修 Alpha 或局部重建，不能直接禁用源 RGB 验收。原图合成层只能覆盖确认干净的内区：根据实际污染宽度和缩放滤波范围选择保护带，不能默认内缩 1 px 就安全，也不能为了保留源色把旧污染覆盖回来。

保留失败样本与修改前后证据。连续两次同类失败换方法；提示词通过与脚本通过都不能替代最终组件换底验收。
