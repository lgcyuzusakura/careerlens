# 变更记录

所有日期使用 Asia/Shanghai。只记录实际完成的变更；规划见开发文档。

## 2026-11-05 模型流式与边界测试

- 模型请求启用 SSE，小块接收 Chat/Responses 响应，完成事件、传输/文本上限、断流及证据校验均受控；保留 JSON 网关兼容路径。
- 新增账号/权限/额度/模拟充值、上传解析与流式协议测试，并提供真实 TCP SSE 测试网关。
- 实际复现旧容器 `LLM_TIMEOUT`，诊断和真实 Docker SSE 验证见 [模型诊断](docs/MODEL_DIAGNOSTIC.md)。真实中转站成功与合成替身验证分别记录。

## 2026-11-05 · 文档准备

- 阅读本地 CareerLens 题目并核对强制技术栈、业务闭环和 GitHub Actions 要求。
- 新增隐私忽略规则，原始题目、简历材料、授权信息与密钥不进入 Git 或 Docker context。
- 建立 `AGENTS.md`、`AI_LOG.md`、`DELIVERY.md` 与项目文档入口。
- 设计四层边界、证据契约、确定性评分、模型降级、测试门禁与镜像回滚。
- 按用户后续要求，将 AI_LOG 改为带日期与角色的对话原文，敏感授权值脱敏，附本轮文件变更。
- 按用户最新要求固定 3000/8080/8081/8082 端口，Docker 为主要构建环境，补充国内镜像/依赖源策略与 code/msg/data 信封，准备 Postman 调试集合。
- 合并门禁增加用户本人明确人工审核，测试与 CI 绿色不能代替人工批准。
- 新增文档阶段静态检查脚本与 GitHub Actions workflow；不将文档检查当应用单测或 Docker 结果。
- 私有仓库与 Draft PR #1 已创建；9dbd265 的 push/PR 文档 CI 实际通过。
- main 保护设置被 GitHub 以套餐限制返回 403；保留私有，不宣称平台门禁已配置，不合并 PR。
- 本阶段未实现应用，不宣称应用测试、应用 CI 或回滚已通过。

## 2026-11-05 · v0.1 答辩准备与交付核验（23:13–23:35）

- 新增 15 分钟答辩逐字稿 `docs/DEFENSE_15MIN.md`、请求链演示手册 `docs/DEMO_REQUEST_CHAIN.md`、同一 trace 演示脚本 `scripts/demo_chain.py`、合成 JD 夹具 `tests/fixtures/jd-synthetic.txt` 与公开来源记录 `docs/JD_TEST_SAMPLE.md`（记录来源 URL、访问日期 2026-11-05 与脱敏说明）。
- 实际验证并记录：四容器健康、`docker compose config -q`、44 项单测、四层 smoke、浏览器验收（首次缺 Chromium 失败，安装后通过）、同一 trace 跨三层日志与逐层直连、清单回滚部署与回切。
- 核验远端：feature / PR / main 三个应用 CI run 与 CD run `42054682893` 均成功；发现 PR #2 已于 23:17 合并 main，与「用户本人人工审核通过前不合并」门禁冲突，待用户确认。
- 重建 `DELIVERY.md` 当前状态并保留历史失败记录；`docs/API_CONTRACT.md`、`docs/POSTMAN.md`、`docs/DEVELOPMENT.md` 标注设计阶段旧措辞；`README.md` 补充文档入口。
- 明确未验证：跨版本 A → B → A 回滚、真实付费 LLM 调用、GHCR digest 独立核验、用户本人人工审核。
- 备注：同一工作区存在并发 v0.2（账号/导入）未提交改动；本轮未暂存、未提交这些文件，验证只针对已提交 v0.1。
