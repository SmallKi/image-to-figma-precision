# 构建计划与批处理

`prepare-batch.py plan.json state.json --count 8 --out next-batch.js`

`plan.json` 是父节点在前的元素数组。每项必须有 `key`、`parent`、`type`、`box:[x,y,width,height]`，box 是源图全局坐标。`type` 支持 FRAME、COMPONENT、RECTANGLE、VECTOR、TEXT。COMPONENT 在草稿阶段创建 FRAME，内容完成后按由内到外的顺序转换并放置实例。

可选字段：

- `color`、`stroke`：六位十六进制颜色；`sw` 为描边宽度。
- `radius`：圆角；`shadow`：阴影纵向偏移。
- `gradient`：按顺序排列的颜色数组，用于纵向线性渐变。
- `crop:[x,y,w,h]`：源图矩形取样。只用于允许保留矩形背景的无文字区域，不提供透明保证。
- `requiresTransparency:true`：图标前景必设。原始 crop 会被拒绝；以 `transparentAsset` 引用已验收素材，字段与验证流程见 [transparent-icons.md](transparent-icons.md)。自定义矢量遮罩构建另行执行并验收。
- `path`：VECTOR 的局部坐标路径。
- TEXT 必需 `text,family,style,size`，可选 `align,outline,outlineWidth`。box 决定固定文字框；字距和富文本范围按实际任务扩展。

`state.json` 必须有 `pageId,sourceHash,sourceWidth,sourceHeight`。`nodes` 是 `{key:nodeId}`，至少有 `root`；`colors` 是 `{hex:variableId}`，可为空。sourceHash 来自成功上传，不是源文件的 SHA-256。所有 ID 必须来自实际工具返回。

执行生成代码前确认当前后端、正确目标文件、至多 10 个节点、字体名称真实可用。每次成功返回后合并 mapping，并保存 createdNodeIds/mutatedNodeIds。发生错误不推进 offset；发生超时先只读查重。进入新调用时不要假定前次 page context 仍有效。

转组件时先将已完成 FRAME 移到主组件区，再 `createComponentFromNode`，在原父级和原位置添加其实例；不能把新主组件放回另一主组件内。处理父组件前，确认内部子组件均是实例。重新扫描当前屏幕更新所有后代 ID。

使用 [componentize-one.js](../scripts/componentize-one.js) 每次转换一个已完成容器。输入 config 包含 pageId、rootId、shelfId、sourceId、key，以及清单全部组件的 componentKeys、清单全部节点的 stableKeys。stableKeys 不包含重复图标实例内部的通用名称（例如 Vector）；这些名称不能作为全局节点身份。shelf 是交付屏幕之外单独创建的普通 FRAME，layoutMode=NONE，不允许放在交付根节点内部。按清单父子关系从最内层选择；脚本拒绝跳过尚未转换的子组件，也拒绝在现有 INSTANCE 内部创建主组件。

转换后保存 mainComponentId/instanceId、所有返回 ID、textProperties；用返回的整屏 mapping 更新 state.nodes 以及 manifest 所有 nodeId。被转换的后代 ID 可能全部变化，不能只替换父 ID。主组件设置原生 TEXT 属性，嵌套实例内的文字由该实例自身主组件管理。每次必须做截图和编辑性验证；本地语法或模型测试不代替 Figma API 实测。
