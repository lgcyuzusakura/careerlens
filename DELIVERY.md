# CareerLens 交付记录

## 2026-11-05 23:50 测试与模型流式补充

本节补充账号/上传测试及模型诊断，具体复现、命令和限制见 [模型诊断](docs/MODEL_DIAGNOSTIC.md)。Python 请求已启用 `stream=true`，逐块接收 SSE，最终仍经 schema/证据验证后交 Java 评分；前端继续展示一次完整的已校验结果。

- 已验证：`npm test` 前端 6、BFF 19 项通过；Java `mvn -B -s settings.xml test` 27 项通过；Python 首轮 68 项通过，新增真实 TCP Chat/Responses SSE 集成 2 项通过。Docker Python 测试构建首轮 68 项通过。
- 已验证的真实模型：独立 Docker 容器使用当前中转站 Responses SSE 返回 200，8614 ms，最终结构和证据校验通过；该结果与受控替身测试区分记录。
- 旧运行容器失败：HTTP 200 实为 `mode=degraded`、`LLM_TIMEOUT`，约 9366 ms；旧模型预算为读取 9 秒、总 10 秒，配置均存在。最新源码模型总预算为 30 秒，外层预算逐层放宽；仍需重建完整运行环境才生效。
- 启动/部署：沿用 `docker compose up -d --build --force-recreate --wait`；本轮流式专用测试镜像只证明 Python 构建与模型调用，不替代四层健康检查、真实前端链路、远端最新 CI 或人工审批。
- 回滚：沿用完整四镜像 release 清单与数据卷保护，不删除旧镜像，不把本轮临时镜像当 SHA 发布清单；本轮未进行跨版本回滚演练。
- 架构取舍：只把 Python 到中转站改成流式；Java 继续拥有评分，BFF 不访问数据库，模型 key 只在 Python 运行时；终端用户不接收未校验模型片段。
- 已知限制：首包和总时限仍可能超时；真实调用耗时有波动；前端不是逐字生成效果。当前验证不等于最新分支远端 CI 全绿，不改变人工审核后才能合并的要求。

## 最新交付增量：v0.2（2026-11-05 23:53）

用户最新要求优先保证运行与基础功能，未完成项如实列出。本节优先于下方 v0.1 历史状态。v0.1 合并明确依据用户原话“我测试完了，这版可以推主分支了如果单测ci什么的都没问题的话”，对应 CI 全绿；该批准不延伸到 v0.2。

### 启动与部署

```powershell
python scripts/configure_runtime.py --codex
$env:RELEASE_TAG='v0.2-dev'
docker compose config -q
docker compose up -d --build --force-recreate --wait --wait-timeout 120
```

前端 http://localhost:3000，Java 8080、BFF 8081、Python 8082。本机 .env 已生成随机 JWT、管理员及数据库凭据，并按用户授权从当前 Codex 配置导入中转站；未将值写入 Git、日志或浏览器。管理员名默认 admin，密码只在本机被忽略的 .env 中查看；普通用户从页面注册，默认 10 次。模型仍需在工作台主动勾选“使用外部模型”。

### 实现、测试与验证状态

- 已实现：注册/登录、HS256 JWT、BCrypt、用户/管理员权限、余额与消费记录、模拟充值、后台用户/充值/统计、分成比例和额度调整、MD/TXT/PDF/DOCX 导入、三个简历示例和六个岗位模板。
- 已执行：`docker compose config -q` 通过；`npm test` 中 Vue 6 项和 BFF 对应新增测试通过；`npm run build --workspace @careerlens/web` 通过；Python 最新 70 项通过。
- Java 账户安全/并发/幂等测试通过；完整测试曾因岗位模板从 2 增为 6 的旧断言失败，已更新断言，待本轮重跑结果。
- Docker 新版构建进行中：Vue/BFF/Python 镜像已完成，Java 仍下载新增 Maven 依赖。尚不声称四层新版已运行；旧版四个健康镜像仍保留。
- v0.1 main CI 已通过：https://github.com/lgcyuzusakura/careerlens/actions/runs/42053405971；镜像发布已通过：https://github.com/lgcyuzusakura/careerlens/actions/runs/42054682893。
- v0.2 远端 CI、完整浏览器/接口验收、真实中转调用尚未完成；只允许保留 feature 分支，禁止合并新版。

### 回滚

保留 v0.1 四个 `keep-v0.1-baseline` 镜像及 `output/releases/v0.1-baseline.json`；不删除任何镜像或卷。四层必须按同一清单一起回切。v0.2 新增 H2 卷 `careerlens_domain-data`，旧版不会读取该卷；回切后账户功能暂不可用，但再次启动 v0.2 可读取原数据。不要 `docker compose down -v`。新旧版验证脚本不同，旧版 smoke 必须设 `LEGACY_SMOKE=true`。本节不把历史 v0.1 回滚演练当作 v0.2 演练结果。

### 架构取舍与缺口

Java 拥有账户数据库、订单状态、额度与评分；BFF 只做参数校验、请求编排、超时和契约校验；Python 独占模型凭据及文件解析。使用 H2 持久卷适应本地单实例演示，分析正文/原始文件不入库。文件在独立受限进程解析，5 秒终止，PDF 不做 OCR。JWT 有效期 1 小时，标签页 sessionStorage 保存，退出本地清除。

模拟充值不接支付渠道、不发生资金流；金额用整数分，确认幂等，分成以订单创建时比例快照，不能当真实财务系统。生产尚缺支付签名/对账、找回密码/刷新或撤销令牌、账号限额与反滥用、多实例数据库迁移、备份恢复演练、管理员操作审计页面和分页。当前最多返回 200 用户/后台订单、50 个人订单和 20 次分析。


更新时间：2026-11-05 23:35，Asia/Shanghai。**本文件第 0 节是当前唯一有效状态**；第 9 节及更早段落是当时的历史记录，含「尚无代码」「CI 未生成」「回滚未执行」等已过时的断言，只用于追溯过程与保留失败记录，不代表现在。
状态口径：**设计**（写在文档里）/ **已实现**（代码已提交）/ **已验证**（本轮或远端实际跑过）/ **未验证**（不能说通过）。

## 0. 本轮运行事实（23:13–23:35 实际执行）

本轮任务：准备 15 分钟答辩与请求链演示；查找公开开发岗位 JD 测试稿；检查已提交可运行代码、测试、Docker/Compose 与 CI/CD 配置；把实际验证过的启动、测试、部署/回滚、架构取舍和已知缺口写入本文件；最后做独立只读审查并回答「是否有问题」。

### 0.1 适用范围与并发注意

- 验证对象是**已提交的 v0.1**：feature 分支 `629f778`、main 合并提交 `30158f4`。远端 feature、PR、main 三个应用 CI run 均绿色（见 0.5）。
- 本轮工作期间，同一工作区有**另一个并发会话**在做 v0.2（账号/导入）开发：`AGENTS.md`、`apps/bff`、`services/*` 等出现大量未提交改动，并新建了 `feature/careerlens-accounts-import` 分支。本轮的单测、smoke、浏览器验收在 v0.2 源码改动落盘前后分别执行，结论只对已提交 v0.1 与当时运行的 v0.1 镜像成立；**未暂存、未提交任何 v0.2 代码**。
- 本机 `.env`（Git 忽略）只含 `NODE_IMAGE` 应急镜像选择，无模型 key；默认 Compose 仍是固定 digest 的国内镜像。本机运行镜像是应急 Node 基础层构建的 v0.1 镜像，不声称与默认 digest 基础层逐字节一致。

### 0.2 启动与环境（已验证）

| 项 | 实际结果 |
| --- | --- |
| `docker version --format '{{.Server.Version}}'` | 29.9.2；Docker Desktop 运行中 |
| `docker compose config -q` | 通过 |
| `docker compose ps` | 四服务 `careerlens-{web,bff,java,ai}:v0.1-dev` 全部 `healthy` |
| 端口绑定 | 3000 / 8080 / 8081 / 8082 均在 `127.0.0.1`；浏览器业务只走 3000 同源 `/api` |
| 健康探针 | 3000 `/` 200；8081 `/healthz` 200；8080 `/actuator/health/readiness` 200；8082 `/healthz` 200（由 `scripts/demo_chain.py` 逐项实测） |
| 启动命令 | `docker compose up -d --no-build --wait --wait-timeout 120`（本轮回切时实际执行并成功） |

本机四个容器在多轮验证中始终保持健康；回滚演练中曾整链 `--force-recreate` 两次，均恢复健康。JDK / Maven / Node / Python 的构建在 Docker 镜像内完成，宿主工具链只用于补充单测。

### 0.3 测试与实际结果（已验证）

| 检查 | 命令 | 结果 | 时间 |
| --- | --- | --- | --- |
| 前端单测 | `npm run test --workspace @careerlens/web` | 3 passed（vitest） | 23:25 |
| BFF 单测 | `npm run test --workspace @careerlens/bff` | 9 passed（node:test） | 23:20 |
| Java 单测 | `mvn -B -q -s services/domain-api/settings.xml -f services/domain-api/pom.xml test` | 15 passed（ApiTest 5 / ExtractionClientTest 5 / ScorePolicyTest 5） | 23:22 |
| Python 单测 | `.venv/Scripts/python.exe -m pytest services/ai-service/tests -q` | 17 passed | 23:20 |
| 合计 | — | **44 项通过** | — |
| 契约/集成 smoke | `python scripts/smoke.py` | PASS：86/100、命中 Java/Spring Boot、缺口 Docker、直连三层 REST、400、413、15000 emoji 边界、空要求 null 分数、external=`degraded` | 23:21 / 23:31 / 23:32 各一次 |
| 浏览器验收 | `.venv/Scripts/python.exe tests/e2e/browser.py` | **首次失败**：缺 Chromium headless shell 二进制；安装 `playwright install chromium` 后重跑 **PASS**（真实分析、证据高亮、结构化页签、陈旧提示、导出、超时恢复、取消、1440/390/320px） | 23:22 失败 / 23:26 通过 |
| 答辩演示脚本（含固定 trace / 降级） | `python scripts/demo_chain.py --trace ... --include-degradation` | **PASS**：四层健康、一次真实链路、同一 trace 的 bff/domain-api/ai-service 三行日志、逐层直连评分归属、400/413/null/degraded | 23:28 |
| 演示脚本只读审查后加固 | 默认、`--include-degradation`、`--no-logs`、`--web http://example.com` 四种 | **PASS**：日志命中三服务、BFF/Java 有 score 且 Python 无 score、错误 code 比对、空要求响应均改为断言；`--no-logs` 明确标记跳过；非 localhost 地址被拒绝；响应读取有 1 MiB 上限、连接异常不崩溃 | 23:46 |
| 合成 JD 长文本演示 | `python scripts/demo_chain.py --jd-file tests/fixtures/jd-synthetic.txt --no-logs` | **PASS**：10 项要求、8 项缺口、分数 24（6/25）；日志断言按参数标记为跳过 | 23:47 |
| 文档静态检查 | `python scripts/check_docs.py` | PASS：13 Markdown、6 JSON 示例、10 Postman 请求；隐私边界与密钥启发式扫描通过 | 23:36 |

说明：浏览器验收的失败与修复都如实保留，不把「安装后通过」写成「一次通过」。CI 中的浏览器验收使用同一脚本，但 runner 独立安装 Chromium，属于远端验证，不等同于本机结果。

### 0.4 部署与回滚（本轮实际演练，含明确限制）

- **已实现**：`scripts/release.py --snapshot` 校验四容器健康、保存四个精确 image ID、打 `keep-<name>` 保留标签并跑 smoke；`--deploy` 校验清单 schema / 契约版本 / 词典 hash，用四个精确 image ID 生成 override，整链 `--no-build --force-recreate --wait`，再跑 smoke。不删除任何镜像，不执行 prune。
- **已存在清单**：`output/releases/v0.1-baseline.json`（gitSha `30158f4`，`workingTreeDirty: true`，`contractVersion: analysis-v1`，`dictionarySha256: b4d8ae1c…`），四个 `keep-v0.1-baseline` 标签仍在。
- **本轮实际执行**：
  1. `python scripts/release.py --deploy output/releases/v0.1-baseline.json` → 四容器重建为清单中的精确 image ID（web `34f705d2…`、bff `1f74f32f…`、java `dd0e0020…`、ai `5efa5a7a…`），全部 `healthy`，脚本内置 smoke PASS。
  2. `docker compose up -d --no-build --force-recreate --wait --wait-timeout 120` → 回切默认 `v0.1-dev` 标签，四服务再次 `healthy`，`python scripts/smoke.py` 再次 PASS。
  3. 生成 `output/releases/compose-release.json` override（Git 忽略）。
- **结论与限制（重要）**：这验证了**同一份 release 清单驱动四层协同切换**的机制（A → 清单部署 → 回切），但两版镜像内容 ID 相同，来自同一次构建，**没有跨代码版本的差异**，因此**不等于**题目要求的完整 A → B → A 跨版本回切。跨版本回滚仍标记 **未验证**；完成条件是用真实不同的两个 Git SHA 镜像各跑一次 smoke 并保留回切记录。
- 另：基线快照记录 `workingTreeDirty: true`，说明快照时工作区不干净；正式发布清单应在干净工作树/明确 SHA 上生成。
- 本机运行镜像与最新提交的一致性证据：长 Unicode 回归（15000 emoji）在 smoke 中通过，远端 CI 从 `629f778` 构建四镜像成功；本轮**没有重新执行 `docker compose build`**，所以不声称「运行镜像与源码逐字节一致」。

### 0.5 远端 CI/CD、分支与合并（只读核验）

| run | 类型 | 结论 | 说明 |
| --- | --- | --- | --- |
| [42051190947](https://github.com/lgcyuzusakura/careerlens/actions/runs/42051190947) | feature push `629f778` | success | 四镜像构建、单测、真实 HTTP、浏览器、合成模型网关 |
| [42051203482](https://github.com/lgcyuzusakura/careerlens/actions/runs/42051203482) | PR #2 | success | 同上；`Planning Docs` 同轮亦 success |
| [42053405971](https://github.com/lgcyuzusakura/careerlens/actions/runs/42053405971) | main push `30158f4` | success（23:24 完成） | 合并后的全量 CI，7m24s |
| [42054682893](https://github.com/lgcyuzusakura/careerlens/actions/runs/42054682893) | `Release images` CD | success（23:24 触发，4m14s） | `workflow_run` 触发；`Build verified revision and publish immutable tags` 步骤成功，包含四个 `docker push` |

- **CD 已触发且步骤成功**，推翻了此前「GHCR 发布未执行」的旧记录；但当前本机凭据缺 `read:packages` scope，GitHub Packages API 返回 403，**无法独立列出 GHCR 版本或核验 digest**，因此不把「digest 已核验」记为通过。
- **合并门禁问题（P0，需用户确认）**：PR #2 于 2026-11-05 15:17:06Z（本机 23:17）由账号 `lgcyuzusakura` 合并，`isDraft=false`、`reviewDecision` 为空、`reviews=[]`、评论为空；`main` 已是 `30158f4`。而 23:03 的交付记录仍写「用户人工验收仍未批准 / 保持 feature/Draft，不合并 main」，`AGENTS.md` 要求「用户本人明确表示人工审核通过后才合并」。**如果这次合并不是用户本人在 GitHub 上手动批准，就违反了人工门禁，并且连带触发了 CD 发布**。本轮不擅自 revert、不强推、不重写历史；请用户确认后再决定是否用新提交回退。
- main 平台分支保护仍是 403（套餐限制，历史事实），没有生效的平台强制门禁；人工审核不能由 AI review 或绿色 CI 代替。

### 0.6 架构取舍（已实现，理由保留）

- 四层分离来自题目强约束：BFF 只做字段白名单、参数校验、编排、超时与统一错误映射，不做评分、不连数据库；Java 持有领域 DTO、规则版本与 `ScorePolicy`；Python 负责清洗、归一、模型输出验证和提取降级；模型只由 Python 调用。
- 确定性优先：权重由 Java 回填，Python/LLM 不返回 weight/score；同一提取集合必得同一分数。分母为 0 时 `score.value=null`，不硬给 0 分。
- BFF 生成 `X-Trace-Id` 并逐层传递，Java/Python 只接受合法 UUID v4，防伪造日志注入；日志只含 service / traceId / status / 耗时，不含材料正文。
- 请求 UTF-8 上限 160 KiB、长度按 Unicode code point；Nginx 413 返回统一 JSON 信封；下游响应 512 KiB 上限。
- 无账号、无数据库、无持久化、不默认 localStorage；刷新丢材料是明确隐私取舍，JSON 导出由用户主动触发。
- 无 key 可跑规则模式，但 UI 明确标 `rules` / `degraded`；模型 URL 只由运维环境变量配置，浏览器与前端不能给。
- 回滚四层共用一份清单，不单独回切一层；`contractVersion` / `skillDictionaryVersion` 防止四层混搭发布。
- 未引入 Agent、向量库、ORM 迁移、PDF/OCR 与付费系统；公网开放前必须补认证、TLS、限流。

详见 [开发总纲](docs/DEVELOPMENT.md)、[接口契约](docs/API_CONTRACT.md)、[答辩稿](docs/DEFENSE_15MIN.md)。

### 0.7 15 分钟答辩与请求链演示（本轮新增，已验证）

| 交付物 | 内容 | 状态 |
| --- | --- | --- |
| `docs/DEFENSE_15MIN.md` | 逐字稿、时间分配、预设问答、合规红线、兜底话术 | 已实现，按 0.3 的事实核对后可直接照讲 |
| `docs/DEMO_REQUEST_CHAIN.md` | 一键演示步骤、同一 trace 机制、curl 等价命令、边界预期表 | 已实现 |
| `scripts/demo_chain.py` | 六步真实 HTTP 演示；同一 trace 日志三服务命中、BFF/Java 有 score 且 Python 无 score、错误 code、空要求均为断言；默认不外发外部模型；`--no-logs` 明确标记跳过；地址限 localhost；报告只含状态码/trace/计数/服务名 | **已验证 PASS**（默认 / 含降级 / 跳过日志 / 拒绝远程地址 四种路径） |
| `tests/fixtures/jd-synthetic.txt` | 明确虚构的合成长 JD，供 `--jd-file` 使用 | 已验证 |
| `docs/JD_TEST_SAMPLE.md` | 公开招聘来源、URL、访问日期 2026-11-05、脱敏摘录、合成改写稿、隐私边界 | 已实现；页面正文需登录，技术条款取自公开检索索引 |
| `output/playwright/*.png`、`output/demo/*.json` | 本机截图与演示报告 | 已生成，Git 忽略，不提交 |

演示链路实测：`POST http://localhost:3000/api/v1/analyses` → BFF 生成 trace → Java → Python；`docker compose logs` 中 bff / domain-api / ai-service 三行 trace 完全一致；直连 8080 与 8082 复用同一 trace，Python 响应无 `score`、Java 响应有 `score`。

### 0.8 已知缺口与问题（当前优先级）

| 优先级 | 缺口 | 状态 / 完成条件 |
| --- | --- | --- |
| P0 | **人工审核门禁与 main 已合并的事实冲突** | 需用户本人确认 23:17 的合并是否为其手动批准；若否，按流程用新提交处理，不重写历史 |
| P0 | 跨版本 A → B → A 回滚未演练 | 本轮只验证同内容镜像的清单切换机制；需两个不同 Git SHA 的四镜像各跑 smoke 并记录 |
| P0 | 真实付费 LLM 调用未验证 | 仅 CI 合成网关 + 本机 `degraded`；需运行时私密配置后单独记录 trace/状态/耗时，不保存正文与凭据 |
| P0 | **`release.yml` 在 main CI 绿色后自动发布，没有人工审批** | 独立只读审查发现：`workflow_run` 只校验 conclusion / event / head_branch 与 `head_sha`，PR #2 合并后已自动向 GHCR 推送四镜像（run `42054682893`），推送不可撤回。需补人工批准 / 环境门禁或调整触发条件；**绿色 CI 不能代替人工批准** |
| P0 | **Java 未把 evidence 文本与原始简历交叉核对** | 审查发现 `ScorePolicy` / `ApiController` 只校验 evidence ID 存在与 `source` 正确、skillId 在词典内，未把 `evidence.text` / `rawMentions` / `line` 与 `resumeText` / `jdText` 比对；被替换的 Python 可用词典内技能 + 任意简历行构造命中。与契约文档声称的「Java 再检查引用」存在实现漂移，需补纵深校验与回归测试 |
| P1 | 413 / 415 / 405 错误映射被压缩 | BFF 与 `ExtractionClient` 把下游 413/415/500/502 压成 502 且丢弃 `data.errors`；Python 未产出 415；Java 405 透传到 BFF 变 502。与错误表不一致 |
| P1 | Java 直连 8080 缺请求体字节上限 | 直连调试端口绕过 nginx 160k 与 BFF 163840 限制；需补入口限制 |
| P1 | 独立只读审查结论已纳入 | 本轮完成一次独立只读审查（暂存 diff、四层调用点、缺失测试、交付配置）；上面两项 P0 与 413/415 项来自审查。本轮只修新增脚本/文档，**未改动并发会话正在编辑的已提交代码** |
| P1 | GHCR 发布已发生但 digest 未独立核验 | CD run 42054682893 成功；需 `read:packages` 权限或 Docker manifest 校验后记录 digest |
| P1 | 基线快照 `workingTreeDirty: true` | 正式 release 清单应在干净工作树、明确 SHA 上生成 |
| P1 | 本机未重新执行 `docker compose build` | 运行镜像的一致性证据来自 smoke 回归与远端 CI 构建，不声称与源码逐字节一致 |
| P1 | 私有库 main 无平台强制保护 | GitHub 403 套餐限制；靠项目流程与人工门禁，不声称平台生效 |
| P1 | 公网部署前无认证 / TLS / 限流 | 当前仅绑定 127.0.0.1；公网前必须补齐 |
| P1 | 并发会话在同一工作区改 v0.2 源码 | 本轮未暂存其改动；双方同时改 `DELIVERY.md`/`AI_LOG.md` 有冲突风险，需人工协调 |
| P1 | 演示脚本与回滚脚本未纳入 CI | `ci.yml` 覆盖构建/单测/HTTP/浏览器/合成网关；`demo_chain.py`、`release.py --deploy` 仅本机验证 |
| P2 | `docs/API_CONTRACT.md`、`docs/POSTMAN.md`、`docs/DEVELOPMENT.md` 含「应用尚未实现」等历史措辞 | 本轮已加状态标注，见 0.9；全文逐句清理留待后续 |
| P2 | 规则提取不理解复杂语义与否定 | 标注降级、保留反例回归，不承诺招聘预测 |
| P2 | 无 PDF/OCR、简历历史、压测、跨浏览器与真实简历精度评测 | 仅 headless Chromium 1440/390/320px；后续用经授权脱敏评测集执行 |

### 0.9 本轮文件变更与验证状态

- 新增：`docs/DEFENSE_15MIN.md`、`docs/DEMO_REQUEST_CHAIN.md`、`docs/JD_TEST_SAMPLE.md`、`scripts/demo_chain.py`、`tests/fixtures/jd-synthetic.txt`。
- 更新：`DELIVERY.md`（本文件，重建当前状态）、`AI_LOG.md`（追加本轮对话原文与文件变更）、`CHANGELOG.md`、`README.md`（新增文档入口）、`docs/API_CONTRACT.md` / `docs/POSTMAN.md` / `docs/DEVELOPMENT.md`（把「应用尚未实现」类历史措辞标注为设计阶段记录）。
- 生成（Git 忽略，不提交）：`output/demo/chain-*.json`、`output/releases/compose-release.json`、`output/playwright/*.png`。
- 独立只读审查：修复阶段结束后单独执行，覆盖暂存 diff、四层调用点、缺失测试与交付配置；发现的问题按严重程度列入 0.8，本轮只修本轮新增的脚本与文档。审查阶段未修改任何文件。
- 门禁清单（本轮真实状态）：单测 44 ✅ / 契约与集成 smoke ✅ / Docker 配置与健康 ✅ / 浏览器验收 ✅（安装 Chromium 后）/ 文档静态检查 ✅ / 远端 feature+PR+main CI ✅ / CD run ✅ / 同一 trace 演示 ✅ / 清单回滚机制 ✅ / **跨版本回滚 ❌ 未验证** / **真实付费 LLM ❌ 未验证** / **GHCR digest ❌ 未独立核验** / **用户本人人工审核 ❓ 待确认** / **自动发布人工门禁 ❌ 缺失**。
- `python scripts/check_docs.py` 只检查 Git 跟踪的文件；已在显式暂存本轮文件后执行并通过（23:36），提交前再看一次完整 staged diff 与敏感信息。

---

## 9. 历史记录（保留当时断言与失败，已被第 0 节覆盖）

> 以下段落写于 21:00–23:03，包含「尚无应用代码」「应用 CI 尚未生成」「回滚清单尚未生成」等**当时的真实状态**。保留它们是为了追溯过程与失败闭环，**不得用作当前状态**。当前状态一律看第 0 节。

- 21:xx 文档阶段：根为 `D:/test-main` 的空仓库；建立 `AGENTS.md`、`AI_LOG.md`、`DELIVERY.md` 与文档入口；私有仓库 `lgcyuzusakura/careerlens` 已创建，main 隐私基线 `a954c7f`；Draft PR #1 保持 OPEN；文档 CI push run `42037841838`、PR run `42037952724` 均 success。配置 main 分支保护的 API 返回 403（套餐限制），保留私有，不声称平台门禁生效。
- 22:34 首轮应用 CI：run `42044875793` 实际失败，原因是 Java Dockerfile 的 JAR 复制路径与 Maven 输出目录不一致；修正后重跑。当时 `docker compose config -q` 已通过，但四容器尚未启动成功，本机 Windows JDK 的 NIO loopback 异常影响宿主 Tomcat。
- 22:43 第二轮：四镜像构建、规则 smoke 与浏览器通过；切换模型网关后首条规则请求 502，原因是 Compose 只重建 Python、上游缓存旧连接/DNS，改为整链 `--force-recreate`。新增 `scripts/release.py`、契约 Schema 与浏览器错误/取消回归；当时回滚仍待执行。
- 22:51 只读审查：发现并修复 BFF 输出长度按 UTF-16 计数（长 emoji 被误拒）与 Nginx 413 返回 HTML（破坏统一信封）；补回归，43 项单测通过。
- 23:03 Node OCI 下载停滞：新增 `docker/node-base.Dockerfile`，用国内归档源安装 Node 24.11.0 并核对官方 SHA-256；四容器健康。随后 Unicode smoke 在 run `42049145654`（及 `42049137284`）揭示 Java JSON escape 字节膨胀触发 Python 413，已修复；早期绿色 run `42048288344` 属于 `f055147`，不把早期绿色当成最新状态。
- 23:03 时的已知缺口原文要点：`DELIVERY.md` 仍残留「当前没有 `compose.yaml` 或应用代码」「应用 CI 计划路径尚未生成」「回滚演练未执行」「后续提供 `scripts/demo.sh`，目前没有脚本」等。这些在本轮（23:13–23:35）已由第 0 节和新增脚本取代；`scripts/demo.sh` 那个计划最终以跨平台的 `scripts/demo_chain.py` 实现，并非 shell 脚本。
- 历史演示路径（保留）：3 分钟业务与四层边界、5 分钟真实 HTTP 链与证据定位、4 分钟增量提交/CI/Docker/回切、3 分钟分数含义与未做事项。现已被 `docs/DEFENSE_15MIN.md` 的逐字稿细化。
- 历史取舍（保留）：GitHub 为目标平台，Gitee 仅在 GitHub 网络不可用时评估；Gitea 与 Gitee 是不同平台，不移用 `.gitea/workflows/`；「正式三小时考试计时」尚未声明开始，不伪造计时或达标记录，本轮为文档准备与验证时间。
