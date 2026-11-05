# CareerLens 交付记录

更新时间：2026-11-05，Asia/Shanghai。当前进入 v0.1 实现阶段；用户要求先 README，再 Vue -> Node -> Java -> Python，最后 Docker/测试/CI。所有“计划”项均不代表已通过验证。

## 22:34 最新验证（覆盖下方早期准备状态）

- 四层实现与应用 CI/CD workflow 已提交，分支 `feature/careerlens-v0.1`，main 未合并。
- `npm test`：Vue 3、BFF 8 项通过；`pytest`：17 项通过；Java 前一增量 8 项通过，共 36 项。新增真实 HTTP 超时、超大响应、模型协议与伪造证据反例。
- [首轮应用 CI](https://github.com/lgcyuzusakura/careerlens/actions/runs/42044875793) 实际失败：Java JAR 复制路径错误。日志确认 Maven 单测与打包已成功，现修正 Dockerfile 后重跑。
- `docker compose config -q` 已通过；国内 nginx 镜像已拉取，其余基础镜像仍下载，尚未声称本机四容器运行成功。
- 本机 Windows JDK 的 NIO loopback 异常影响宿主 Tomcat 启动，Linux Docker CI 的 Maven 测试不受该异常影响。
- 外部模型仅有受控协议测试，未配置真实付费模型；人工审核与回滚仍待完成。

## v0.1 本轮进度

- 已从文档分支新建 `feature/careerlens-v0.1`，未合并 main；先更新 README 的范围、运行契约和人工门禁。
- 前端、Node、Java、Python 按用户顺序实现；各阶段实际测试结果将在此追加。
- 最终交付可运行 v0.1 供用户测试，保持 Draft PR；用户未明确批准前不合并。
- 用户补充剩余两小时，要求优先代码、后更新 README。当前四层源码按指定顺序已写入。
- 实际本机验证：`npm run build` 成功；前端 3、BFF 5、Java 8、Python 8 项测试通过。
- Docker 国内基础镜像正在首次拉取；Compose 配置和全链路尚待验证，不把宿主测试算成 Docker 成功。

## 1. 启动与环境

当前没有 `compose.yaml` 或应用代码，不能运行项目。后续计划的统一启动命令为：

```sh
docker compose up -d --build
```

命令需在四个服务和 Compose 实现后实际验证。以 Docker 为主要构建/运行环境，宿主机不用安装 JDK、Python 或 Maven。国内基础镜像和依赖源通过构建参数配置，实际可拉取并锁定 digest 后记录；当前尚未拉取验证。

| 服务 | 本机地址 | 用途 |
| --- | --- | --- |
| Vue 前端 | http://localhost:3000 | 用户入口，/api 同源转发 BFF |
| Java | http://localhost:8080 | 领域 REST 调试 |
| Node BFF | http://localhost:8081 | BFF REST 调试 |
| Python | http://localhost:8082 | 提取 REST 调试 |

四个宿主端口均计划绑定 127.0.0.1，浏览器业务只调用 BFF。接口格式固定 `{ code, msg, data }`，traceId 为 `X-Trace-Id` header。可先导入 [Postman 集合](postman/CareerLens.postman_collection.json) 审阅请求；应用尚未实现，尚不能实际请求这些服务。

| 环境项 | 用途 | 当前状态 |
| --- | --- | --- |
| `LLM_MODE` | `auto` / `required` / `rules`，默认 auto | 设计中 |
| `OPENAI_API_KEY` | 仅 Python 从环境读取，不填入文档 | 尚未接入 |
| `OPENAI_BASE_URL` | 运维指定、校验过的模型网关 | 尚未接入 |
| `OPENAI_MODEL` | 运维明确配置支持结构化输出的模型 | 尚未接入 |
| `RELEASE_TAG` | 四个服务一致的 Git SHA 镜像标识 | 尚未发布 |

计划默认以合成材料演示；不自动读取用户本地的原始简历。正式考试计时尚未声明开始。

## 2. 实际验证与测试状态

| 检查 | 实际结果 |
| --- | --- |
| 本地题目阅读 | 已读取 `test/README.md`，确认 Vue/Node/Java/Python 与 GitHub Actions 要求 |
| 工作区和 Git | 根为 `D:/test-main`；初始为无提交、无 remote 的空仓库 |
| 资料包边界 | 只读取 ZIP 元数据：20 PDF + 1 TXT，未提取正文 |
| `Get-Command npx,...` | npx、git、gh、docker、java、mvn、node、python 可找到 |
| Node/npm/Java/Maven/Python 版本 | 24.18.0 / 11.16.0 / 21.0.12 / 3.9.4 / 3.11.9 |
| `docker version --format '{{.Server.Version}}'` | 返回 29.9.2；没有据此宣称应用 Docker 构建成功 |
| `gh auth status` / `gh api user` | 设备授权已完成，确认账号 lgcyuzusakura；不保存认证值 |
| `gh repo create ... --private` / `gh repo view ...` | 私有仓库已创建，见第 7 节 |
| `git push -u origin main` | 前两次网络断连；随后 HTTP/1.1 重试成功，main 已推送 |
| 公开参考读取 | devprep-ai ADR、简历文档、compose、CI；Resume Matcher/OpenResume README 与许可证元数据已读取 |
| `python scripts/check_docs.py` | 已通过：10 Markdown、5 JSON 样例、10 Postman 请求；代码块、相对链接、端口变量、默认外传关闭与隐私启发式检查 |
| `git diff --cached --check` | 已通过，无 whitespace error |
| 文档只读 review | 按 code-review skill 检查本轮完整 diff；No findings. 不代表不存在实现风险 |
| 本项目应用单元/契约/E2E | 未执行，尚无应用代码 |
| `docker compose config -q` / 构建 / 启动 | 未执行，尚无 Compose 配置 |
| 真实模型请求 | 未执行，尚无运行时配置 |
| 远端文档 CI | 9dbd265 的 push 与 PR 两次 run 均 success，见第 7 节；不代表应用测试通过 |
| main 分支保护 API | 实际 PUT 返回 403，当前套餐不支持私有仓库分支保护；保留私有，不宣称平台强制门禁已生效 |
| 回滚演练 | 未执行，无可用版本镜像 |

后续每个增量在此补充命令、结果、commit SHA、CI run、release digest；失败也保留。

## 3. 部署与回滚

设计：四个服务各构建一个镜像，发布标签使用完整 Git SHA 并记录 digest。测试阶段可以本地构建，正式 release 不使用可变 `latest`。

发布前门禁：全部单测与契约/集成测试、Docker 构建、合成材料四层 smoke、浏览器回归、只读 review、远端必需检查绿色，以及用户本人明确人工审核通过。人工审核前不能合并 main，不能把 AI 审查或绿色 CI 当作人工批准。公开环境还须完成鉴权和 HTTPS；MVP 默认只绑定本机。

发布清单应包含：Git SHA、四个镜像 digest、规则版本、契约版本、构建 run 链接和前一可用清单。保留当前与前一可用镜像；不运行会清除它们的 prune 命令。

回滚设计：使用上一完整清单运行 `docker compose --env-file <previous-release-env> up -d --no-build --wait`，然后检查四服务健康并用固定合成材料复验。运行时 `.env` 与模型密钥独立于 release 清单，不提交 Git。此命令目前只是设计，清单与脚本尚未生成。

MVP 采用无持久化分析，不涉及数据库迁移；配置和契约仍需兼容校验。初版发布前至少本地完成 A -> B -> A 回切并记录结果；首次交付还必须保留一次可用基线镜像。

## 4. 架构取舍

- 四层分离来自题目强约束。BFF 集中处理页面契约与边界，Java 保留业务规则所有权，Python 隔离模型协议与不确定输出。
- 模型只提取有证据的信息；Java 按版本化权重计算分数，避免同一技能集合因模型措辞变化得到不同分数。
- 使用轻量 OpenAI-compatible HTTP adapter；MVP 不引入 Agent、向量数据库、复杂 LangChain 链或历史数据库。接口保持可替换，后续需要多步工具时再引入框架。
- 不持久化原始简历，不默认 localStorage。刷新后材料丢失是明确取舍；JSON 导出必须由用户主动操作。
- 无 key 可运行规则模式，但 UI 必须标出 `rules` / `degraded`；不能把规则结果称为已完成真实 LLM 验证。
- GitHub 为本次目标；Gitea skill 的硬编码平台不能覆盖用户和 README。Gitee 回退须另行核验其 CI 产品，不声称支持 GitHub Actions。

详细说明见 [开发总纲](docs/DEVELOPMENT.md) 和 [接口契约](docs/API_CONTRACT.md)。

## 5. 已知缺口与优先级

| 优先级 | 缺口 | 完成条件 |
| --- | --- | --- |
| P0 | 应用、测试、Docker、CI 尚未实现 | 按开发总纲落实并提供实际验证 |
| P1 | 应用与文档均未获用户人工审核 | 文档已推送并开 Draft PR #1；应用完成并全绿后提交人工审核，批准前不合并 |
| P1 | 私有仓库 main 无平台强制保护 | GitHub 返回套餐限制；按项目流程禁止自动合并，后续具备套餐/组织能力再启用平台门禁，不改为公开 |
| P1 | 无真实模型调用证据 | 安全配置运行时 key 后记录脱敏请求结果与模式 |
| P1 | 无镜像基线或回滚演练 | 两个可用版本、release 清单与回切记录 |
| P1 | MVP 计划无用户认证 | 仅绑定本机；公网部署前实现认证、TLS、限流 |
| P2 | 不做 PDF/OCR 导入与简历历史 | 粘贴文本满足题目最小闭环；后续独立规划 |
| P2 | 规则提取不能完整理解复杂语义和否定 | 标注降级、添加反例回归，不承诺招聘预测 |
| P2 | 未做压测、跨浏览器和真实简历精度评测 | 后续用经授权的脱敏评测集执行 |

## 6. 15 分钟演示路径

1. 3 分钟：解释业务、四层边界、确定性分数与无持久化取舍。
2. 5 分钟：打开工作台，用合成简历 + JD 完成真实 HTTP 链；展示证据定位、缺口和同一 traceId，再演示非法输入、模型降级与服务超时。
3. 4 分钟：展示增量 git 历史、feature PR、绿色 CI、Docker healthcheck 与上一个版本回切。
4. 3 分钟：解释分数不是录用概率，说明实际验证范围、模型模式、尚未做的鉴权与解析能力。

后续提供 `scripts/demo.sh` 与 PowerShell 等价入口。目前没有脚本，不将其记为完成。

## 7. 仓库、分支和 CI 事实

- 远端：[lgcyuzusakura/careerlens](https://github.com/lgcyuzusakura/careerlens)，已通过 CLI/API 确认私有。origin 已配置。
- 初始仓库为 master unborn。现已建立 main 隐私基线 a954c7f 并推送；当前文档开发分支为 `feature/careerlens-plan`。这不构成正式考试计时开始。
- 实现分支后续为 `feature/careerlens-mvp`；小增量提交，PR -> 单测/集成测试/CI -> 用户本人明确审核通过 -> 才能合并。
- 文档分支已提交并推送 9dbd265：[Draft PR #1](https://github.com/lgcyuzusakura/careerlens/pull/1)，保持 OPEN / Draft，未合并。main 仍是 a954c7f 隐私基线。
- 文档检查 `.github/workflows/docs.yml` 执行 `python3 scripts/check_docs.py`；9dbd265 的 [push run](https://github.com/lgcyuzusakura/careerlens/actions/runs/42037841838) 和 [PR run](https://github.com/lgcyuzusakura/careerlens/actions/runs/42037952724) 均 success。只验证文档；后续文档状态更新会再次触发，以 PR 最新 commit 检查为准。
- 应用 CI 计划路径 `.github/workflows/ci.yml`、CD 路径 `.github/workflows/release.yml` 尚未生成，应用单测/集成/Docker 均未执行。
- 文档 CI runner 为 `ubuntu-24.04`；checkout v4 的 SHA 由公开 API 核验并固定为 `11d5960a326750d5838078e36cf38b85af677262`，权限仅 `contents: read`，checkout 不保留凭据。应用 CI 也将采用固定 SHA；release job 单独授予 `packages: write`，不让 PR 使用发布凭据。
- 文档检查名 `Documentation checks`。实际尝试为 main 配置必需检查与 PR 门禁，GitHub 返回 HTTP 403：需升级套餐或公开仓库。保持私有，没有生效的分支保护；人工审核要求由项目约束和 Draft PR 状态执行，不声称已有平台级强制审批。
- 镜像 registry 权限、release 与 digest 尚未验证；没有删除任何已有 Docker 镜像。
- 首次认证未完成已解决；Git HTTPS 前两次断连，HTTP/1.1 重试已推送 main，不需要切换 Gitee。

## 8. 本轮变更与门禁

- 建立隐私忽略规则、持续工作约束与文档入口。
- 准备详细开发、API、前端设计和公开参考文档。
- 按用户新要求补充国内源策略、固定四端口、code/msg/data 信封、Postman 契约集合，以及“用户本人审核通过才能合并”门禁。
- AI_LOG 改为按日期直接复制双方对话，敏感值脱敏并附文件变更；文档静态检查、Git 历史与认证状态在本轮完成时更新。
- 本轮文档检查与只读 review 已完成，feature 已推送，Draft PR 已创建；文档 CI 有实际绿色 run。原始题目/简历资料与授权码未提交。
- [ ] 应用单测与契约测试
- [ ] Compose 配置、构建、健康检查
- [ ] 浏览器真实链路和移动端截图
- [ ] 只读代码 review 与修复闭环
- [ ] PR 必需检查绿色
- [ ] 用户本人明确人工审核通过
- [ ] 镜像上一版本保留与实际回滚
