# 按参考风格重新生成透明图标

这是所有美术图形的默认制作流程，包含图标、背板、帽子剪影、小菱形、按钮、标签和装饰。先按 [asset-assembly.md](asset-assembly.md) 拆共用零件、语义组和摆放角度，再用描述和参考图片生成独立素材。背景若应不透明则使用不透明输出，其余独立素材按下文透明流程。默认以目标尺寸下约 8–9 分视觉相似验收；透明通过不能代替画风、关系和拆分检查。

## 1. 看图并写出可执行描述

实际查看原图和单个图标的局部参考。局部要包含完整主体、细枝和分离部件；整图用于画风与使用场景，局部用于主体结构。可使用已有裁片；需要裁切时按当前环境允许的图像工具处理，裁片仅作参考。不要把最近邻放大的像素块、失败抠图或差异热图当作画风参考。

先整理整套图标共用的风格描述，例如：

- 造型与视角：圆润或硬朗，正面或轻俯视，夸张比例及主要剪影。
- 色板：主体、暗部、描边、高光分别是什么颜色；不把 UI 底板色或混色边缘当主体色。
- 描边：颜色、视觉粗细、端点与转角、是否有内描线。
- 材质与光照：平涂、手绘或立体质感，光从哪来，高光形状与阴影软硬。
- 细节密度：最终尺寸下应保留的大色块、材质层次和关键识别部件。

随后逐素材口述“画什么”：主体、各部件数量与相对关系、固有姿态、必须保留的浅色高光/细枝、真正透明的孔洞、排除的共用底板与文字。单独生成背板时反过来排除物体。整体倾斜的按钮/标签要求正对画布、长轴水平、摆放角度 0°，原角度由 Figma 父容器恢复。只写“高清、精致、同风格”不够。看不清的功能含义记为未知，保留可见外形线索，不擅自赋予新含义。

## 2. 准备图片与母版规格

每次提交的输入角色写进提示词：

- 原图或整体风格图：提供画风、色板、光照，不导入其他对象或布局。
- 当前图标局部：提供主体结构、关键比例和方向；不复制低清像素、压缩块和底色污染。
- 已通过的同组图标（如有）：只辅助统一渲染语言，不把它的主体画进当前图标。

文字不能代替图片附件。使用当前工具实际支持的参考图参数；本地图片先查看，全部有路径时可用支持的路径列表，含会话图片时依工具规则选择覆盖必要输入的最小范围，不混用互斥参数。若无法把必要参考传给工具，保留描述并说明缺少输入，不把纯文生图声称为参考图重绘。

记录最终主体尺寸 W×H 与原 UI 中的固定布局框，另请求工具支持的高分辨率母版。按主体宽高比选最接近的可用画幅；横向按钮不要默认方形画布。普通小图标可把约 1024 px 画布、主体主要尺寸约为目标的 4 倍或以上作为起点。按钮/标签明确要求“单个大主体、紧凑构图、不留展示海报式空白”，安全边距按 asset-assembly.md 设定；不能只有大画布而主体很小。工具未暴露尺寸参数时只在提示中请求，并检查实际输出，不能声称已强制指定。

保存母版实际尺寸、renderBounds/bodyBounds、四边空隙和长短轴占比。不要把插值放大的原图当高清参考或高清母版。按 asset-assembly.md 去除已确认全透明外边或补偿完整母版偏移，Figma 以实际主体适配目标框；禁止把大空白母版直接 FIT 进按钮框，再按图片节点中心排字。保留母版，避免先缩成小图后反复放大。需要单独导出目标尺寸文件时，从母版一次缩小并验证 Alpha 采样。像素画按其明确像素风格处理。

## 3. 实际生成

默认使用当前内置图像工具；环境提供 imagegen 技能时遵循其调用规则。以当前 schema 为准，不编造模型、尺寸、seed、保存路径或透明输出参数；当前内置工具暴露 `background` 时显式设为 `"transparent"`，保存实际参数。工具暴露透明背景与 PNG 输出选项且当前模型支持时显式设置；只支持提示词时请求真实透明 RGBA，结果仍以实际文件为准。不得擅自改用收费 API/CLI 或换模型。

带参考图直出透明素材时，提示词开头先明确输出的**表示方式**，再描述 Alpha 细节：

```text
Generate the asset itself, not a picture or preview of an asset.
<Describe only the wanted subject and explicitly exclude neighboring reference content.>
The transparent-output setting is already enabled. Leave the exterior absent/transparent.
Do not paint, simulate, or illustrate transparency; do not create a checkerboard, white/colored field, canvas, card, mockup, or surrounding shadow.
Tight asset framing: the subject occupies <measured target coverage> while fully visible with a narrow safety edge. One object only.
```

该结构在一次同工具小样中跨按钮与帽子 6/6 得到真实 RGBA；同次测试中，仅写“透明背景”或大段 `ALPHA CONTRACT` 都只有 1/2。它是当前观察到的优先模板，不是模型保证：仍须逐文件检查真实 Alpha，不能因提示词相同跳过门禁。避免把 Alpha 技术说明堆在主体身份之前；“RGBA、角点 Alpha=0”可作为后续合同补充，但不能替代“生成资产本身、不要画透明预览”的表示约束。若模型/工具配置变化，重新抽样，不把本次比例当永久能力声明。

一次生成一个图标，不生成含多个小图标的图集或整页界面再裁切。先以一个代表图标校准共用风格，检查通过即继续同组；用户已授权图标重绘时不为常规美术校准追加确认。每个后续图标都沿用同一风格描述，附自己的主体参考与专属部件要求。达到约 8–9 分、画风一致且目标尺寸正常就继续，不为细纹理或轻微轮廓偏差反复校准。

填写下面的模板，保存实际提交内容到任务目录的 `icons/<key>/generation-prompt.txt`；删去不适用条目，不能提交未填占位词。

```text
Use case: stylized-concept
Asset type: one independently generated <foreground icon / empty shared backplate / decoration / button skin>
Primary request: draw a new, crisp <subject> using both the written art direction and the attached references.
Representation: generate the asset itself, not a picture or preview of an asset. The transparent-output setting is already enabled; leave the exterior absent/transparent and never paint a checkerboard, field, canvas, card, mockup, or surrounding shadow.
Reconstruct the illustration at high resolution; do not extract, trace screenshot pixels, upscale, or sharpen the low-resolution crop.
Input images:
- Image 1: overall style reference only: <specific palette, outline, material and light observations>.
- Image 2: subject reference: <parts, silhouette proportions, orientation, distinctive features>.
- Image 3, if present: approved companion icon for rendering consistency only; do not copy its subject.
Final use: <W×H px> in the existing UI. Keep semantic identity, major proportions, intrinsic pose and visual weight; aim for a close 8–9/10 visual match while matching the art style exactly.
Orientation: <canonical pose>. For a tilted UI plate, generate a front-facing master with horizontal long axis and zero overall placement rotation; preserve designed chamfers/curved edges. Figma will rotate the complete component, including its editable text, by <placement angle> later. Do not bake that placement tilt into the asset.
Working composition: <requested supported dimensions closest to subject aspect ratio>; one large fully visible subject, tight framing, approximately <measured/planned long-axis coverage> of the canvas long axis, only <small safe margins> around the artwork. Preserve the subject aspect ratio. No oversized empty presentation canvas; do not stretch the artwork to fill an incompatible canvas.
For an empty button/label plate: preserve a clear continuous inner text-bearing region <relative position and proportions from reference>, with balanced visual padding; no text or placeholder lettering. Keep heavy bevels, curled corners and decoration out of that intended region.
Art direction: <shape language>; <main/shadow/outline/highlight colors>; <outline weight and corners>; <material>; <light direction and shading style>.
Must depict: <specific parts and their relationships, highlights, thin or detached details>.
Must be transparent: exterior; <named true holes, or none inside a solid object>.
Readability: clean intentional contours and clear major color shapes at final size; redraw indistinct non-semantic texture as restrained material detail, without deleting identifying parts.
Alpha: solid-looking interior and highlights; near-opacity such as 250–255 is acceptable; natural antialiasing at outer and hole contours; exterior and true holes Alpha=0.
Keep intrinsic illustrated outlines and material shading. This asset includes only <owned parts>. Exclude <shared backplate/frame or foreground objects, according to the asset role>, labels and numbers. Do not reinterpret a repeated UI frame as an intrinsic pedestal.
Avoid: screenshot blur, compression blocks, copied matte colors, fuzzy contours, sharpening halos, opaque backdrop, extra objects, text, watermark, icon sheet, full UI.
Output: one genuinely transparent RGBA PNG.
```

## 4. 审核与针对性重绘

按 [transparent-icons.md](transparent-icons.md) 检查候选母版、最终尺寸与 Figma 实际导出：

1. 先看目标尺寸下主体和关键部件是否可读，描边是否清晰，整套画风是否一致，并确认图标与标签无溢出或遮挡。约 8–9 分像即可，轻微轮廓、纹理和色值差异不阻塞；缩小后糊成一团或明显换画风仍失败。
2. 再检查 Alpha、浅色高光、真实孔洞和换底残边。轻微接近不透明与正常抗锯齿不需要硬化；RGB 文件、假棋盘格、实体明显透底都失败。
3. 最后按实际主体放回固定布局框，检查大小、视觉中心、标签关系、真实底板与移动/隐藏状态。按钮额外检查四边空隙是否进入了布局、文字是否位于实际可用区且字高协调。另查母版长轴是否摆正、前景是否夹带共用背板、装饰是否属于约定语义组。按 asset-assembly.md 的代表项测试后才扩展全组。保持原文案和独立层，不以更换图标为由调整整个界面。

问题与修改一一对应：风格漂移就修正具体色板/描边/材质描述；图标糊就检查母版主体尺寸和缩放链，并在原参考上重新生成清晰线条与色块；缺部件/错孔洞就明确部件关系；假透明就重申真实 Alpha 输出。失败图片只作诊断，不当下一次的主参考。不通过旧截图内区覆盖、腐蚀、颜色键、反复模糊/锐化来掩盖问题。

默认每个图标 1 次生成 + 最多 2 次针对性重绘，通过即停止；用户的次数或费用限制优先。同一工具配置连续两次输出 RGB/烘焙棋盘格时暂停该配置的整组透明生成，不逐图重试同一失败。记录已完成与待处理项，保留最优候选；不自动转抠图、换 API 或无限重试。用户明确另选源像素保留流程时才使用 [edge-cleanup.md](edge-cleanup.md)。

若会话中用户已授权“先生成独立高清候选，再用 AI 编辑去底”，沿用该授权执行这条独立路线，无需重新索要同一许可：以已查看的新生成候选为编辑输入，显式请求真实透明，保留主体与细节，输出重新走 Alpha 和目标尺寸审核。这不是截取原图像素或颜色键抠图，不能与失败的直接透明生成混算为成功；记录各阶段实际调用。未授权时不把该路线作为无限重试借口。

## 5. 保存生成来源

在 manifest 元素记录 `assetMethod: ai-reference-redraw`（源像素模式为 `source-preserve`），并保存原参考路径/哈希、图片角色、共用风格描述、逐图标实际提示词、目标布局框、母版尺寸/主体范围、缩放与对位变换、实际工具信息与透明参数、尝试次数、输出哈希及审核证据。未知模型型号不填写猜测值。

这是来源元数据，不改变现有构建脚本的接口。最终素材仍通过 `transparentAsset`、真实 Alpha 报告与 visualReview 进入构建，见 [plan-format.md](plan-format.md)。重绘应标明 AI 生成，不能称为找回原始素材。像素差异完整保留，验收范围见 [acceptance.md](acceptance.md)。
