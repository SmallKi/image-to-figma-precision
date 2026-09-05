# Figma Console MCP 本地后端

适用于 Southleft 的 `figma-console-mcp`，通过 Figma Desktop Bridge 插件连接。工具可用性以当前会话暴露的 MCP 工具或其真实 tools/list 为准，不假设安装配置后当前会话已自动加载。

## 连接与目标

1. `figma_get_status({probe:true})` 验证真实往返；仅 TCP 端口监听不能证明 Figma 插件已连接。
2. 查询当前连接文件，匹配用户指定 fileKey。`figma_execute` 本地模式可显式传入 fileKey；每次写入都明确目标，防止用户切换文件后操作错误文档。
3. 程序安装成功、握手成功、插件连接、目标文档可写是四个不同状态，分别记录。尚需导入插件时给出固定 manifest 路径和桌面菜单步骤。

## 执行与错误恢复

- 使用 `figma_execute({code,timeout,fileKey})` 运行原生 Plugin API。参考版本 1.40.0 的单次 timeout 上限为 30000 ms；读取实际 schema 后再调用。省略官方专用 skillNames/description 参数。
- 原生 Figma 不提供官方工具环境的 `node.screenshot()`、`node.query()`、`node.set()` 等扩展；使用标准 Plugin API，不原样复制这些辅助方法。
- 操作文本先加载每个实际 family/style，等待完成后修改。修改 INSTANCE 内容优先通过组件属性；不要依赖直接写实例后代文字，当前后端提示这种操作可能静默失败。
- **本地执行不能假定事务回滚。** 某行异常或工具超时前，前面的节点可能已经创建。先只读查询已记录 ID 和本任务确定的稳定 key，再恢复账本；不得直接重发整批。清理只处理已核实属于本次操作的明确 ID。
- 检查返回的 `resultAnalysis.warning`、错误字段和实际读回值；成功调用本身不证明设计改变。
- `componentize-one.js` 等本地脚本是原生 API 模板，仍需实际执行后验证，不把离线模型测试当作在线验证。

## 图像与精度

- 原始素材通过本地工具支持的图像导入或 `figma.createImage(Uint8Array)` 进入文件。工具的路径/字节格式以实时 schema 为准。
- `figma_capture_screenshot` 适合预览，但参考版本会把长边限制在 1568 px；原图超过限制时，不能拿该默认预览直接做 1:1 像素验收。升级后以工具实际输出为准。
- 最终比较应从目标根节点直接 `exportAsync({format:'PNG',constraint:{type:'SCALE',value:1}})` 导出，并通过工具支持的结果传输方式保存全部字节。检查实际 PNG 尺寸与 manifest 记录的源图宽高一致，拒绝缩小预览冒充 1× 导出。大数据传输需要分块时验证分块顺序、总长度和文件头，保存导出节点 ID 与哈希。
- 本地桥接的读写和原生导出不消耗官方 MCP 工具配额；REST 查询工具仍可能需要 Token 并受 Figma API 限制。遇到 Token 错误先确认是否误用了 REST 路径，不为了截图要求用户付费。

### 导出任务与超时

本项目实测 `exportAsync` 放在长时间等待的 execute 请求里会间歇超时；可在插件 `globalThis` 中创建带唯一任务 key 的临时记录，调用 exportAsync 的 then/catch 更新 status 和 base64，首个 execute 立即返回。后续 execute 读取同一任务：running 继续观察、complete 取回 PNG、error 记录原因。任务存在时不要重复启动；只有明确 missing 才重新导出。导出期间不要改变目标节点。该方式已在目标文档完成 941×1672 原尺寸导出，不依赖 REST Token。

这是插件运行时的临时任务，不把大段 base64 写入 Figma 文档 pluginData。保存 PNG 并验证尺寸/哈希后删除运行时任务记录。插件重开可能丢失记录；进度账本仍以本地文件和实际文档为准。

独立图标轮廓通过检查后，可以将 Figma 1× 透明导出重新作为小 PNG 填充回主组件，保持尺寸和 Alpha，不再反复渲染整张源图裁片。保留原轮廓供编辑，并比较回填前后导出，避免重复叠加抗锯齿遮罩。

## 独立安装

本 skill 不包含 MCP 程序或本机安装状态。已有可用连接时直接验证状态，无需重复安装。

以本项目参考版本为例，在支持 STDIO 的 MCP 客户端中配置启动命令 `npx`，参数为 `["-y", "figma-console-mcp@1.40.0"]`。确保客户端能找到 Node.js 和 npx；完整环境要求和平台配置参见 [上游说明](https://github.com/southleft/figma-console-mcp)。

服务启动后，在 Figma 桌面端选择 **Plugins → Development → Import plugin from manifest…**，导入用户主目录下 `.figma-console-mcp/plugin/manifest.json`，再运行 **Figma Desktop Bridge** 并保持窗口打开。该稳定插件目录由服务创建；找不到文件时先检查服务启动日志。通过 `figma_get_status({probe:true})` 验证目标文档的真实往返。

工具清单与参数以当前服务的 `tools/list` 为准。升级服务后核查配套插件，必要时重新导入 manifest。不要把本机绝对路径、文件 key、Token 或历史运行状态写入可分发的 skill。

# 重连导致导出任务丢失时

如果每次启动服务后，插件的临时任务句柄都消失，检查 Figma 开发插件菜单中的 Hot reload plugin，以及所用服务是否在启动时重写插件文件。确认两者同时存在时，可暂时关闭热重载并重开已安装插件，再用一次实际导出验证。关闭热重载后修改插件代码需要手动重开。不要把导出请求成功或 `running` 状态记录为图片已生成。

本地服务可能占用固定端口区间。先检查状态和实际端口，避免连续启动新实例挤掉旧连接；不要批量结束其他任务的进程。若使用 CLI 恢复同一已授权 MCP，应尽量在一个连接内串行执行、逐调用保存结果，并在结束后只关闭自己启动的子进程。
