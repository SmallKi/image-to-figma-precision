# 图标：同画风、清晰与真实透明

图标默认按 [transparent-generation.md](transparent-generation.md) 逐枚重绘，按 [acceptance.md](acceptance.md) 的约 8–9 分目标验收。画风必须与整张参考和同组素材一致；不要求细纹理、轮廓和源 RGB 完全相同。

## 默认检查

1. **目标尺寸**：原参考与候选并排看。主体、方向与关键部件对应，描边清楚、主要色块可辨；不改变主题的细节差异可接受。目标尺寸正常即停止，不因高清母版放大有轻微差异重绘。
2. **画风**：逐枚核对色板、描边语言、材质、光照和细节密度；不能以更清晰为由接受明显风格漂移。
3. **布局**：等比放入约定框，校准主体视觉中心，不挤压标签或越出允许范围。按 [layout.md](layout.md) 检查；有意装饰出界单独记录。
4. **Alpha**：保存母版、哈希、实际尺寸、目标框及节点 ID，运行 `scripts/audit-alpha.py icon.png --out alpha-report.json`。RGB、全不透明、空图不能作为透明成品；有 Alpha 还须目视核对是否夹带背景。
5. **换底**：查看真实 UI 底色及白、黑、洋红底，确认主体与高光完整，无明显矩形残底、孔洞错误或彩边。允许 Alpha 250–255 的实体和自然抗锯齿，不为严格 255 比例低而硬化 Alpha。

参考裁片只是来源证据，不能当交付前景。图标与标签、数字徽章、共用 UI 底板独立。先按 [asset-assembly.md](asset-assembly.md) 跨图比较：书的纸张、奖杯自身底座等主体部件保留，反复出现的金框/台基不能仅凭“固有”一词并入前景；需要背板单独隐藏证据。绘画素材的细节不拆成手画矢量，简单可见图形同样生图。

## 按需深化

只在目标尺寸存在可见缺陷、复杂细枝/孔洞、导出采样异常或用户要求严格保留时增加深度检查，不为普通图标强制建立合同和多轮测试。

- `render-cutout-proof.py icon.png --out proof.png --zoom 1` 可生成母版白、黑、洋红、青色和 Alpha 证据。目标尺寸图可按需要 2×/4× 放大，注明倍率；Figma 4× 导出不证明母版新增细节。
- `audit-cutout.py candidate.png contract.json --out semantic-report.json` 可审计 `keep/holes/outside`、覆盖率和合法部件。坐标按实际候选登记，不能为了通过移动锚点；阈值按对象语义选择。仅在明确严格源像素要求时传 `--source` 并使用 `sourceRgbIntegrity`。
- Figma 实际采样疑似异常时，在临时 FRAME 中测试底色并导出主组件；复杂遮挡抽查隐藏/移动，检查原位置残影和底板。无需对全组无问题图标逐个重复全部状态。

脚本不自动证明画风和相似程度。只在极端放大/增强 Alpha 诊断中可见且不影响实际尺寸的零星差异可记备注；目标尺寸下明显缺部件、残底或透底仍应修复。严格诊断失败不能改写为通过，但未启用的像素约束不阻塞默认视觉验收。

## 返修与停止

优先修画风漂移、排版/溢出、主体误读，再修明显模糊和透明问题。风格统一、主体约 8–9 分像、使用尺寸清楚且换底正常，即停止并继续同组；不耗尽重试预算追逐满分。

失败时按生成协议进行针对性修改和预算停止。真实 Alpha 仍是透明素材的必要条件，不把画在 PNG 中的透明示意底当真透明。用户明确要求已生成图去底时可按编辑流程处理；不因普通去底候选少量色值变化自动启用源 RGB 精确保留。

## 接入现有构建脚本

保留 `requiresTransparency: true`，通过后用 `transparentAsset`，不将原始 `crop` 当透明前景。state.assets 关联实际 imageHash、sha256、alphaReport、visualReview；有合同才保存 semanticContract/semanticReport。

现有 visualReview 字段继续兼容：`status="pass"`、`backgrounds=["white","black","magenta"]`、`evidenceFiles`，以及 `smoothEdges/noMatte/highlightsPreserved/holesCorrect`。这些视觉布尔项按目标尺寸和本页标准判断，不要求所有放大像素完美；补充 `targetSizeReadable/styleMatched/semanticMatched/layoutAccurate/noUnintendedOverflow`。证据须真实存在并查看，不伪造报告或节点 ID。
