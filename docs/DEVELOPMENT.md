# CareerLens 开发总纲

状态：原始架构设计与实施计划，四层首版已经实现。日期：2026-11-05，Asia/Shanghai。实际运行证据以 DELIVERY.md 为准，以下目录树为设计目标。

实现对照：Vue 与 BFF 为 JavaScript + 运行时校验，未采用原计划 TypeScript，以缩短限时实现；真实入口分别为 `apps/web/src/App.vue`、`apps/bff/src/app.js`、`services/domain-api/src/main/java/com/careerlens/ApiController.java`、`services/ai-service/app/main.py`。Java `ScorePolicy` 拥有评分，Python `provider.py` 隔离外部 HTTP，`config/skills.v1.json` 共享词典。请求/输出结构 Schema 位于 `contracts/`；真实跨层兼容由 `scripts/smoke.py` 验证，尚未做到所有语言分别加载同一反例 fixture。

本文件根据本地 `test/README.md` 与用户本轮要求编写，先交付设计，再按可验证增量实现。用户原始资料目录只读保留在本地，公开参考只借鉴方法、不复制代码。

## 1. 需求、验收和范围

### 1.1 业务目标

学生粘贴简历文本与开发岗位 JD，点击“分析匹配”，得到清洗后的结构化简历、归一化技能、岗位要求、可定位的命中证据、未发现证据的要求和可解释分数。结果帮助补充材料与安排学习，不用于自动淘汰候选人，不等于录用概率。

### 1.2 MVP 必须完成

| 能力 | 验收标准 |
| --- | --- |
| 文本输入 | 简历与 JD 都必填；支持中英文、换行、全角字符；实时字数与明确错误 |
| 文本清洗 | 统一换行、Unicode NFKC、清除不允许的控制字符、压缩重复空白；保留项目和段落证据 |
| 结构化简历 | 教育、经历、项目、技能、信息完整性问题；没有证据的字段为空，不补造学校或任职时间 |
| 技能归一 | JS/JavaScript、Vue.js/Vue、SpringBoot/Spring Boot 等映射到受控技能 ID，保留原始表达与出处 |
| 岗位匹配 | JD 要求去重、优先级分类，输出命中和缺口；每个命中必须引用简历证据 |
| 可解释分数 | Java 根据版本化权重计算 0–100 分；展示分子、分母和规则版本；无法评分时为 null |
| 模型接入 | Python 调 OpenAI-compatible HTTP API；输出通过 schema 和证据校验，失败明确降级 |
| 真实请求链 | 浏览器 -> BFF -> Spring Boot -> Python；LLM 模式额外经过外置网关；同一 traceId 串起日志 |
| 工程交付 | 各层测试、Compose 健康检查、CI、PR、增量提交、实际回滚记录和逐轮会话日志 |

### 1.3 本次不扩展

不做注册登录、简历历史数据库、PDF/OCR 上传、招聘网站爬虫、多岗位批处理、自动投递、面试 Agent、向量检索或付费系统。PDF 题目材料由使用者在本地取文本，MVP 只接收粘贴文本。公网开放前补鉴权、HTTPS 和滥用控制。

## 2. 约束解释与仓库策略

- 本地题目明确 GitHub Actions；本轮用户明确 GitHub，网络故障时可考虑 Gitee。因此以 GitHub 为实现目标，不把 Gitee 与自建 Gitea 混为一谈。
- 用户已授权新建仓库、feature 开发、提交与推送和 PR。用户最新明确要求单测、测试、CI 和本人审核全部通过才能合并，因此保持 PR 等待用户明确批准，不自动合并，不把 AI review 替代人工审核。
- 正式“开始计时”尚未宣布。本轮仅记录实际文档准备时间，不伪造三小时成绩或历史提交。
- 仓库 `lgcyuzusakura/careerlens` 已创建并确认私有。创建前已核对认证账号及同名仓库是否存在，没有覆盖已有项目。
- 初始根目录已有 `.git` 但无提交，真实项目根为 `D:/test-main`。现已建立 main 基线并在 feature 分支编写文档；保留 `test/`，不在其中另建嵌套 Git。

## 3. 系统架构与职责

```text
浏览器 Vue 3 (宿主 3000)
    | 同源 /api/*，无密钥
    v
前端静态服务 / 开发 Vite proxy
    | /api/*
    v
Node BFF (8081)
    | schema + trace + timeout + error mapping
    v
Spring Boot domain-api (8080)
    | DTO + 领域编排 + 确定性评分
    v
Python ai-service (8082)
    | clean + normalize + validate + bounded fallback
    v
运维配置的 OpenAI-compatible LLM
```

| 层 | 负责 | 明确边界 |
| --- | --- | --- |
| Vue 3 + TypeScript | 输入、字数、防重复提交、状态、证据展示、JSON 导出 | 只能调用 BFF，不包含模型 key，不请求内部端口 |
| Node + TypeScript BFF | 权威校验、白名单、traceId、页面接口编排、连接与总时限、错误映射 | 不评分、不做技能业务规则、不直连数据库、不透传原始 body |
| Java 21 + Spring Boot | Bean Validation、岗位模板、领域服务、契约版本、去重和评分 | 不依赖浏览器 cookie，不拼 prompt，不把模型分数当事实 |
| Python + FastAPI/Pydantic | 清洗、脱敏、受控词典、LLM adapter、模型输出与证据验证、规则降级 | 不拥有业务主库，不向浏览器暴露，不决定最终评分 |
| LLM provider | 从输入识别语义与结构，返回受限 JSON | 无工具调用或写权限，不得创造经历、技能或指标 |

MVP 无主数据库。岗位模板是 Java 内置、版本化的合成内容；自定义 JD 不持久化。处理结果只保留在浏览器当前页面内存和请求生命周期中。

## 4. 技术选型与版本控制

| 模块 | 计划选型 | 理由与固定策略 |
| --- | --- | --- |
| 前端 | Vue 3、TypeScript、Vite、Lucide Vue | 组合式组件，小型工作台无需复杂状态框架；提交精确版本与 npm lockfile |
| BFF | Node 24 LTS 范围、Fastify、Zod、带连接时限的 HTTP client | 测试可注入下游 transport；完整锁文件；日志关闭请求正文 |
| Java | Java 21、Spring Boot、Validation、Actuator、JUnit/MockMvc | 显式 DTO 与服务层；Maven 固定依赖及 Wrapper 发行版本 |
| Python | Python 3.11、FastAPI、Pydantic、HTTPX、pytest | 与现有环境一致；HTTP adapter 足以支持一次结构化提取；锁定直接与传递依赖 |
| 浏览器验收 | Playwright CLI + Python Playwright | CLI 先侦察，再用 Python 脚本做可重复断言，满足两项用户 skill |
| 部署 | 四个 Dockerfile + Docker Compose | 与请求层逐一对应；镜像、基础镜像和 release 可追溯 |
| CI/CD | GitHub Actions + GHCR（待核验私有包权限） | PR 无发布权限；合并后发布；本机部署由 release 清单控制 |

此表不是已验证的版本锁。实施时核验所选稳定版本的兼容性，写入 package-lock、pom、Python lock 和基础镜像 digest，不使用浮动 `latest`。不为一个 HTTP 提取步骤引入 LangChain；如果后续需要多步检索/工具编排，再通过 adapter 接入。

## 5. 代码编排

以下为 v0.1 已落地的目录结构（本段最初写于设计阶段，当时文件尚未建立；现已按此结构实现）：

```text
careerlens/
  AGENTS.md / README.md / AI_LOG.md / DELIVERY.md / CHANGELOG.md
  docs/
    DEVELOPMENT.md / API_CONTRACT.md / FRONTEND_DESIGN.md / REFERENCES.md
  contracts/
    analysis-v1.schema.json         # 语言无关请求/响应 JSON Schema
    fixtures/                     # 合成跨层请求、期望响应、非法 payload
  config/
    skills.v1.json                # 受控 ID、显示名、别名、边界；镜像只读复制
  apps/
    web/
      src/api/analysis.ts          # 只调用 /api
      src/components/             # 输入、要求列表、证据、状态
      src/composables/             # 请求、取消、陈旧结果检测
      src/styles/tokens.css
      src/App.vue
      tests/
    bff/
      src/app.ts                  # 可注入 client 的应用工厂
      src/config.ts
      src/routes/analysis.ts
      src/schemas/analysis.ts
      src/clients/domain.ts
      src/errors.ts / trace.ts
      test/
  services/
    domain-api/
      src/main/java/.../
        api/                      # controller、DTO、异常 advice
        application/              # MatchService、岗位模板编排
        domain/                   # ScorePolicy、版本、要求去重
        infrastructure/           # 有限时 HTTP client、配置
      src/test/java/.../
      pom.xml / mvnw / mvnw.cmd
    ai-service/
      app/main.py / models.py / config.py
      app/cleaning.py / normalization.py / evidence.py
      app/providers/openai_compatible.py
      app/extraction.py / fallback.py
      tests/
      requirements.in / requirements.lock
  tests/e2e/                      # Python Playwright，只有合成数据
  scripts/
    verify.* / smoke.* / demo.*
    release.* / rollback.*
    scan-secrets.*
  deploy/
    compose.release.yaml
    releases/                     # 不含 key 的发布清单模板和保留策略
  .github/workflows/
    ci.yml / release.yml
  compose.yaml / .env.example / .gitignore / .dockerignore
```

共享 schema 是兼容边界，不跨语言共享运行时代码。每个服务独立构建。前端和 BFF 可用根 npm workspaces；Java/Python 使用自身工具链，统一通过根验证脚本编排。

## 6. 请求编排与协议

1. Vue `GET /api/v1/job-templates` 获取 Java 管理的合成岗位模板；前端选择模板后可编辑 JD。
2. 用户提交 `POST /api/v1/analyses`，包含 `resumeText`、`jdText`、`options.useExternalModel`。
3. BFF 拒绝未知字段、非法类型、空白和超长文本，建立 traceId，重新构造白名单 DTO。
4. BFF 调 Java `POST /api/v1/matches`；Java 二次校验并调用 Python `POST /internal/v1/extractions`。
5. Python 清洗并脱敏；按配置与用户选项选择 rules / llm；模型失败可以 rules 降级，但返回具体 warning。
6. Python 仅返回经校验的结构、归一技能、带出处的 JD 要求与处理模式；Java 去重、做集合匹配并计算分数。
7. Java 返回带 `ruleVersion` 的结果；BFF 验证响应结构后输出统一信封；Vue 展示证据、分数解释和状态。

跨层业务信封统一为 `{ code, msg, data }`，只保留这三个顶层字段；traceId 放 `X-Trace-Id` 响应头。所有字段用 camelCase；成功 `code=OK`，一般错误 `data=null`，字段校验错误 `data.errors` 返回安全字段信息。字段限制、JSON 样例及错误表见 [API 契约](API_CONTRACT.md)。

下游返回 200 但 JSON 不符合契约也必须视为 502；不能返回半截成功结果。未知模板为 404；无可识别技能为有效分析但分数 null，不是假 100 分。

## 7. 清洗、归一与证据

### 7.1 清洗顺序

1. 在 BFF、Java、Python 分别校验输入，不默认信任上游。
2. 统一 CRLF/CR 为 LF；应用 NFKC；去除 NUL、BOM、零宽混淆和其他不允许的控制字符。
3. 折叠同一行多空格，压缩连续空行；保留有效行，不把整份简历压成一行。
4. 检测常见邮箱、电话和证件号并遮盖，之后才构造发往外部模型的文本。此脱敏是尽力而为，不能承诺消除全部身份信息。
5. 为清洗后非空行分配稳定的 `R1...` 和 `J1...` 证据 ID。引用以行 ID 和原文片段定位，不使用跨语言可能不一致的字符 offset。

不把恶意 HTML 当 DOM；输出在 Vue 中用文本插值，不使用未经处理的 `v-html`。prompt injection 视为普通材料，不能覆盖系统提取规则。

### 7.2 技能词典

维护 `config/skills.v1.json`：稳定 `skillId`、显示名、别名和匹配边界。Python 读取用于规范化，Java 只认合法 ID。CI 校验两者词典版本相同。

- 明确区分 Java / JavaScript、C / C++ / C#、Vue 2 / Vue 3；版本要求无法确认时不能暗算完全匹配。
- 英文 token 使用边界匹配，中文别名使用明确词条；重复、大小写与全角不扩大命中次数。
- 一般描述如“参与 Java 项目”可形成技能提及，但不自动等价“精通 Java”。MVP 评分只覆盖技能出现，不对熟练度和年限加权。
- “未使用过 Redis”等明确否定不构成正向证据；复杂否定、反讽和跨句推理进入评测缺口，界面说明不确定性。
- 未知技能保留为 `unmappedSkills`，不强行映射最近词，不直接进入分数。

### 7.3 模型输出约束

模型返回固定 JSON，不接受评分字段。Pydantic 禁止额外字段并限制数组长度、字符串长度和枚举。每段引用必须存在于指定清洗后输入行；每个技能 ID 必须在受控词典，技能证据必须含该技能的合法别名。无法证明的实体丢弃并警告；关键结构整体不可用时降级。

原文引用只证明来源，不能证明经历真实，也不能完全验证语言模型的语义判断。MVP 不宣称解决简历真实性核验。

## 8. 可解释评分

评分在 Java `ScorePolicy`，规则版本暂定 `skill-coverage-v1`。输入只来自已验证的归一技能与 JD 要求；LLM 不决定数值。

JD 要求按 `skillId` 去重；同一技能多次出现保留最严格且有文本依据的优先级。权重为 required=3、unspecified=2、preferred=1。只有 JD 明确“必须/熟悉/掌握”时记 required，明确“优先/加分”时 preferred，其余为 unspecified。不根据技能流行度自行补要求。

```text
totalWeight   = sum(weight(requirement))
matchedWeight = sum(weight(requirement) for evidenced skill matches)
score         = roundHalfUp(100 * matchedWeight / totalWeight)
```

- 范围为 0–100；Java 用整数算术或 BigDecimal 的 HALF_UP，避免语言浮点差异。
- 无可识别要求：`score.value=null`、权重为 0、`score.reason=NO_RECOGNIZED_REQUIREMENTS`。
- 无命中且分母大于 0：0 分，完整命中为 100 分；同一技能只计一次。
- 示例：Java(required,3)、Spring Boot(required,3)、Docker(preferred,1)；简历命中前两项，则 6/7 -> 86 分。
- 前端同步展示“已匹配权重 6 / 总权重 7”，文案为“技能覆盖分”，明确不衡量年限、学历、软技能或录用概率。
- 缺口写“简历中未发现 Docker 证据”，建议补充真实实践，不建议凭空添加技能。

## 9. 时限、限流与降级

### 9.1 递减预算

| 边界 | 连接超时 | 整个调用 deadline | 备注 |
| --- | --- | --- | --- |
| 浏览器 -> BFF | 由浏览器处理 | 25s | 可取消，避免重复提交；反向代理 24s |
| BFF -> Java | 1.5s | 20s | 包含响应体读取，校验后立即中止过大响应 |
| Java -> Python | 1s | 16s | 连接、读及完整调用预算；不依赖无限 socket wait |
| Python -> LLM | 1s | 10s | 覆盖 pool/connect/write/read/完整生成；最多一次调用 |
| Python 本地处理 | 不适用 | 预留 2s | 有输入与数组上限，不做阻塞重试 |

超时值是设计预算，必须测试并留出逐层编码和传输余量。Python 使用真正的 async client；Java 使用配置了连接与响应时限的 client。仅 socket read timeout 不等于整个调用 deadline，两者都要覆盖。

分析 POST 虽无持久化但会产生外部费用，默认不自动重试；浏览器提供主动重试。岗位模板 GET 可在总预算内最多重试 1 次，仅网络错误或 502/503，带小幅抖动，不重试 4xx。不要把 429 自动重试成费用放大。

### 9.2 模式

| 配置/结果 | 返回行为 |
| --- | --- |
| `LLM_MODE=rules` | 全链路真实 HTTP，Python 规则提取；mode=rules，显示限制 |
| auto + 未同意外部模型 | 规则提取；不发送外部请求 |
| auto + 同意 + key 已配置 | 尝试一次模型提取；成功 mode=llm |
| auto + 缺 key/超时/429/无效 JSON/证据失败 | 有限规则降级；mode=degraded；warning 只含安全原因码 |
| required + 未同意 | 400，解释必须允许外部模型或切换 rules，不隐式外传 |
| required + 配置缺失/模型失败 | 503 或 504；不冒充 llm 成功 |
| Java/Python 整层不可达 | BFF 502/503/504；不在浏览器生成假结果 |

Python 设置并发信号量与有界等待；无法入队返回 429 与 Retry-After。BFF 设 body 限制与单进程请求速率上限；不信任任意 X-Forwarded-For。MVP 仅本机部署，不以此替代完整多租户配额。

## 10. 错误与可观察性

统一映射：400 输入、404 资源、413 请求过大、415 非 JSON、422 有效 JSON 但不可分析、429 限流、502 错误响应/连接失败、503 未就绪/必需模型不可用、504 下游 deadline。

每个请求在 BFF 产生 UUID traceId。只接受语法正确且长度有上限的来路标识作为关联值，默认重新生成 canonical traceId；内部用 `X-Trace-Id` 透传，最终前端也从该响应头读取。同一个 traceId 贯穿各层；直接调试内部接口时缺少有效 trace header 则由该入口生成。每层日志仅含 traceId、service、path、status、durationMs、mode 和安全错误码，禁止输入、prompt、Authorization、模型正文、内部堆栈回浏览器。

前端成功响应也写不含正文的 traceId 诊断记录。Vue 展示 traceId 的复制操作以便排查，不用 URL query 存材料。

## 11. 前端设计与状态

设计方向为“证据工作台”：直接进入两个文本输入与分析结果，面向反复编辑和核对的学生。记忆点是每条命中都能跳回简历行证据，分数旁有透明分子分母。使用文档指定的颜色、字体、间距和响应式规则，避免营销首屏和重复卡片。

状态机：idle -> validating -> submitting -> success / error；用户编辑后标记 stale。取消返回 idle，旧请求即使晚到也不能覆盖新请求。示例是明确标识的虚构数据，由用户主动载入。

结果包含模式提示、技能覆盖分、命中列表、缺口列表、结构化简历和导出；移动端先输入后结果、证据展开。完整 token、线框、键盘与空态见 [前端设计](FRONTEND_DESIGN.md)。

## 12. 安全与隐私

- 原始 ZIP、PDF、脱敏 TXT、原题联系人和一次性授权码均不发布；`.gitignore` 与 `.dockerignore` 同时保护。
- key 仅 Python 读取环境；BFF/Java 不持有；Compose 通过单服务 environment 注入，不把整个 env_file 传给所有服务。
- `.env.example` 仅变量名与空值；禁止 `VITE_*KEY`、前端模型 URL、自选代理 URL和请求日志正文。
- 外部模型选项默认关闭，用户明确启用后才发送尽力脱敏文本，并可见“脱敏可能不完整”的说明；不声称所有数据都在本地。
- 不自动写 localStorage、服务器日志或磁盘；清空操作清掉当前结果和输入，导出 JSON 需用户主动触发。
- 只允许服务配置的下游地址；模型 URL 从运维环境读取并校验 scheme/host，拒绝浏览器传入以避免 SSRF。
- GitHub 认证在用户本机交互，不接收 token；Git 作者使用用户给出的公开账号和 noreply 身份，避免私人邮箱进入历史。
- 推送前扫描完整 staged diff；后续 CI 检查合成 fixture、依赖锁与 secret pattern，命中需人工辨别示例变量名和真实值，不输出秘密内容。

## 13. Docker 与网络

四个多阶段 Dockerfile。Node 构建使用 npm ci；Java Maven 构建后只带 JRE 与 Jar；Python 仅安装锁定运行依赖。非 root 用户运行，健康检查使用容器中实际存在的工具，设置 restart 与适当内存上限。

主要构建和验证路径使用 Docker，不依赖宿主机预装 JDK、Maven、Python。国内源采用构建参数：JDK/JRE、Maven、Node、Python、静态服务分别指定镜像，候选使用 `m.daocloud.io/docker.io/library/*`，实际 manifest 可拉取且 digest 核验后才能落锁。源不可达时明确失败或由运行配置切换，不静默引入不同镜像版本。npm/Maven/PyPI 源也配置为受控参数，TLS 校验保持开启；首次依赖锁生成和镜像拉取都记录实际来源。本段为 21:xx 的源策略设计记录；后续基础镜像已实际拉取并在 `compose.yaml` 中锁定 manifest digest，Node OCI 下载停滞时另有应急构建入口 `docker/node-base.Dockerfile`。实际拉取、构建与验证状态以 `DELIVERY.md` 第 0 节为准，不把设计段落当成当前状态。

Compose 网络上使用 `bff:8081`、`domain-api:8080`、`ai-service:8082` 服务名；不使用 localhost 指向其他容器。按用户要求发布四个本机调试端口，绑定 127.0.0.1；前端 /api 代理到 BFF，浏览器业务仍只能同源访问 BFF，内部端口用于 Postman/curl 调试。对外部署 profile 应关闭内部宿主端口。

| 服务 | 宿主:容器 | 用途 |
| --- | --- | --- |
| web | 127.0.0.1:3000:3000 | 前端与同源 /api 入口 |
| domain-api | 127.0.0.1:8080:8080 | Java REST 调试 |
| bff | 127.0.0.1:8081:8081 | Node REST 调试 |
| ai-service | 127.0.0.1:8082:8082 | Python REST 调试 |

提供 [Postman 说明](POSTMAN.md) 与 `postman/CareerLens.postman_collection.json`。集合只用合成数据和 localhost 默认地址，不包含 token、key 或模型 URL；统一信封、HTTP 状态和 trace header 可直接断言。业务使用资源名路径和 POST JSON，健康探针不触发模型调用。

启动依赖为 web -> bff -> domain-api -> ai-service，逐层 `depends_on: condition: service_healthy`。liveness 只检查进程，readiness 检查必要配置和内部依赖，避免依赖环；rules/auto 无 key 可 ready，required 无 key 不 ready。外部模型不放在每次健康探测中，避免费用和外网抖动。

开发和发布分开：开发 Compose 支持 build；发布清单固定镜像 digest，启动不得隐式重建。保留上一个可用四镜像组合与配置；禁止自动删除旧镜像。

## 14. 测试计划与边界矩阵

| 层 | 工具 | 必测场景 |
| --- | --- | --- |
| Vue | Vitest + Vue Test Utils | 空输入、字数、提交/取消、错误、降级、旧结果失效、分数 null、JSON 导出 |
| BFF | Node test/Vitest + app.inject | strict schema、未知字段、超长 body、非 JSON、trace、下游 4xx/5xx、连接/完整超时、响应 schema |
| Java | JUnit + MockMvc + mock HTTP | DTO、重复技能、权重、0/100/null、rounding、Python 超时/无效 JSON、规则版本和模板 |
| Python | pytest + async HTTP mocks | NFKC、换行、控制字符、别名边界、否定、伪造证据、注入、缺 key、429、超时、无效/过大输出 |
| 跨层契约 | 共享 JSON fixture | 所有语言接受合法 schema、拒绝相同非法字段、camelCase 与版本一致 |
| Compose | smoke 脚本 | 健康检查、端口隔离、真实 Vue/BFF/Java/Python 结果、trace、错误恢复 |
| 浏览器 | Playwright CLI 侦察 + Python 断言 | 真正输入并提交，校验命中/缺口/分数/模式，400、取消、移动端、键盘、无控制台异常 |
| release | 发布/回滚脚本 | A 与 B 镜像均可启动，B -> A 回切后健康与固定用例结果正确 |

必须包含：纯空白、零宽字符、emoji/中文、UTF-16 surrogate 边界、长度恰好上限/超 1、HTML/script、超多数组项、JavaScript 不误命中 Java、C++ 不误命中 C、重复 JD、不识别技能、模型声称不存在的经历、没有外部同意不发模型请求、客户端断开后不再触发重试。

计数长度统一按 Unicode code point。BFF 用 Array.from/迭代，Java 用 codePointCount 而不是 @Size 直接数 UTF-16，Python 用 len；原始请求限制另按 UTF-8 bytes。规范化前后都检查，避免 NFKC 扩展绕过上限。

测试替身只替换外部模型，不替换四层 HTTP。CI 无付费 key，通过 rules 和受控模型服务器验证成功/失败；真实 provider 验证单独执行并记录，不与模拟混用。

## 15. CI/CD 和分支门禁

### 15.1 GitHub Actions

`ci.yml` 在 push 与 pull_request 触发，合并前需要：

1. secrets 与隐私扫描、锁文件和文档链接检查。
2. 前端/BFF lint、typecheck、单测与前端构建。
3. Maven verify；Python 测试与静态检查。
4. 契约 fixture 跨语言校验。
5. `docker compose config -q`、四镜像构建、启动 --wait、健康与全链路 smoke。
6. headless Chromium E2E、桌面/手机截图、失败日志工件；工件仅用合成材料。
7. 无论成功失败停止测试容器；不在开发机执行镜像清理。

Actions 固定完整 commit SHA；checkout 不持久化凭据；PR 权限最小，不使用 pull_request_target 执行不可信代码，不传生产 secrets。主分支保护要求稳定的检查名称；账号权限或套餐不支持时如实记录限制，不称已保护。

### 15.2 发布

release workflow 仅在 `main` 的目标 commit 已通过全部必需检查后构建/推送 SHA 镜像，生成四镜像 digest 清单。推荐使用 workflow_run 监听 CI 并再次核对 branch、SHA 和 conclusion；发布代码必须 checkout 被验证的精确 SHA，不以分支当前头代替。

GHCR 的短期 GITHUB_TOKEN 只在发布 job 授予 packages:write。远端服务器地址和凭据目前没有提供，因此不假设已具备生产部署；先完成本机 release 与回滚验证。后续配置环境级 secrets 后再启用远端部署。

### 15.3 过程提交

目标是可审计的小增量，不凑固定数量。建议依次提交基础隐私边界、开发设计、共享契约、Python 清洗、模型 adapter、Java 评分、BFF 边界、Vue 输入、证据结果、测试、Compose、CI/release、回滚与交付记录。每次提交描述实际验证，测试未跑时不写 passed。

至少准备一次完整 `feature/* -> main` PR；代码 review 是只读阶段，所有明确缺陷在修复阶段处理。单测、集成测试、Docker/浏览器验收与远端 CI 全绿后，将精确 commit SHA、结果和 PR 提交用户人工审核；只有用户本人明确批准该版本，才允许合并。批准后如有新变更，重新验证并重新获得对新版本的审核，不复用过期批准。认证、远端检查、用户未批准或套餐限制阻塞时保留 feature，不绕开门禁。

## 16. 实施顺序与三小时建议

文档准备不等于正式计时。用户明确开始后，可按下表压缩实现；外部认证或镜像网络等待如实记录，不能承诺未实际达成的时限。

| 阶段 | 建议预算 | 退出条件 |
| --- | --- | --- |
| 契约与骨架 | 15 min | schema、词典、合成样例、四服务健康入口 |
| Python + Java | 40 min | 清洗/归一/外部模型 adapter、评分与边界测试 |
| BFF + 真实链路 | 20 min | 校验、时限、错误映射和跨层测试 |
| Vue 工作台 | 35 min | 输入、结果、证据、降级、手机和键盘状态 |
| Docker + CI | 30 min | 镜像构建、健康检查、规则与模型替身 E2E |
| review + 回滚 + PR | 25 min | 缺陷修复、回切、绿色 run、提交用户人工审核；未批准则保留 PR |
| 缓冲 | 15 min | 处理真实失败，不压缩最终验证来追求功能量 |

每阶段同步 AI_LOG、DELIVERY 和 CHANGELOG。AI_LOG 按用户最新要求直接复制双方对话原文，标明日期、角色和本轮文件变更；密钥、验证码和真实个人材料替换为 `[已脱敏]`，不能用摘要替代对话。若时间紧，优先保住真实四层闭环、证据、测试、Docker 与诚实记录；不增加题目以外功能。

## 17. 完成定义

- 同一输入在受控模式下可重复得到可解释结果，所有命中可定位。
- 模型不可用、输入不合法与服务超时都有可执行的界面提示。
- 浏览器业务只经过 BFF，内部调试端口仅本机可达，密钥和原始材料不进入 Git/镜像/日志。
- 单测、契约、真实 HTTP E2E、Docker、远端 CI 和回滚实际完成并有记录。
- feature PR 单测、集成测试、CI 和用户本人审核通过后才能合并；未获人工批准则保持待审，旧可用镜像保留。
- 文档中每条验证都能对应实际命令或 run；AI_LOG 和 DELIVERY 覆盖每轮。

任何一项尚未完成，交付说明保留明确缺口，不把开发计划写成完成报告。
