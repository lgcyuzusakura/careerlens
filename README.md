# CareerLens v0.1

面向高校学生的简历与岗位分析工作台：输入简历文本和 JD，输出结构化简历、技能归一结果、命中证据、待补充证据及可解释的匹配分数。

**v0.1 四层代码已实现，Docker 已在本机启动。测试与远端 CI 证据见 [DELIVERY.md](DELIVERY.md)。当前保留 feature 分支，人工验收前不合并。**

构建和运行以 Docker 为主，国内镜像源需可配置并锁定版本。固定端口：前端 3000、Java 8080、Node BFF 8081、Python 8082。业务接口统一 `{ code, msg, data }`。单测、集成测试、CI 和用户本人审核均通过后才允许合并 main。

## 强制请求链

```text
Vue 3 -> Node.js BFF -> Java / Spring Boot -> Python -> LLM
```

浏览器只调用 BFF；Java 持有领域契约与评分规则；Python 负责文本处理、技能提取及模型适配。LLM 不可用时保留规则提取能力，并明确展示降级状态。

## v0.1 范围

- 粘贴简历与 JD，或主动载入明确标记的虚构示例；选择合成岗位模板后仍可修改。
- 清洗文本、归一技能、结构化教育/经历/项目，并展示有原文依据的命中与待补充项。
- Java 按 required=3、unspecified=2、preferred=1 计算技能覆盖分；不是录用概率，无可识别要求时不评分。
- 支持规则模式与 OpenAI-compatible 外部模型；外部发送默认关闭，失败明确降级，不冒充模型成功。
- 支持取消、输入修改后的陈旧结果提示、错误恢复、证据定位、JSON 导出和移动端。
- 无账号、数据库、历史记录或 PDF/OCR；材料只在当前页面与请求生命周期内处理。

## Docker 启动

默认使用已锁定 digest 的国内基础镜像：

```sh
docker compose up -d --build --wait
```

| 服务 | 地址 | 用途 |
| --- | --- | --- |
| Vue 前端 | http://localhost:3000 | 主要测试入口，同源 /api 调 BFF |
| Java | http://localhost:8080 | 领域 REST 与 Actuator 健康探针 |
| Node BFF | http://localhost:8081 | 参数校验、编排、时限、统一错误 |
| Python | http://localhost:8082 | 清洗、归一、外部模型提取 |

所有宿主端口绑定 127.0.0.1。JDK、Maven、Node 与 Python 在 Docker 中构建运行，不要求宿主安装这些 SDK。基础镜像和 npm/Maven/PyPI 使用可配置的国内源，保留 TLS 校验、锁文件和固定镜像标识，不删除上一可用镜像。

无 key 时默认规则路径可用。接入真实模型只在本机 `.env` 设置 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`，再在页面明确启用外部模型；密钥仅传给 Python 服务。不要在浏览器、Postman 集合、Git 或日志中放 key。

如 Node OCI 镜像下载停滞，可在 Docker 内构建同版应急基础镜像（仅 linux/amd64，归档 hash 已与 nodejs.org 核对）：

```powershell
docker build -f docker/node-base.Dockerfile -t careerlens-node:24.11.0-local .
$env:NODE_IMAGE = 'careerlens-node:24.11.0-local'
docker compose up -d --build --force-recreate --wait
```

本机已经在被忽略的 `.env` 配置上述 Node 应急镜像，没有模型 key。更改模型配置或回滚时整链 `--force-recreate`，避免代理缓存旧容器地址。

## 测试、部署和回滚

Docker build 内执行前端/BFF、Java JUnit、Python pytest。宿主开发验证和运行后验收入口：

```sh
npm ci
npm test
mvn -B -s services/domain-api/settings.xml -f services/domain-api/pom.xml test
python -m pip install -r services/ai-service/requirements.lock
python -m pytest services/ai-service/tests -q
python scripts/smoke.py
python -m pip install playwright==1.56.0
python -m playwright install chromium
python tests/e2e/browser.py
```

CI 实际构建并启动四个容器，再测试浏览器和 OpenAI-compatible 合成网关；网关测试不能证明真实付费模型质量。

部署使用同一 Git SHA 的四镜像清单，保留上一可用清单与镜像，回滚四层一起回切。精确命令、实际测试数、CI run 和回滚演练结果持续记录在 DELIVERY.md，未运行的检查明确标记。

```sh
python scripts/release.py --snapshot v0.1-baseline
python scripts/release.py --deploy output/releases/v0.1-baseline.json
```

快照先检查四容器健康并执行 smoke，保存内容 ID 和保留标签；部署使用清单中四个精确镜像 ID，无构建、无 prune。CD 仅在 main 的 CI 绿色后向 GHCR 发布 SHA 标签，当前尚未发布。

## 开发与合并门禁

当前实现分支为 `feature/careerlens-v0.1`，继承尚未合并的文档分支内容；不先合并文档到 main。按“README -> Vue -> Node -> Java -> Python -> Docker/测试/CI”的顺序做可验证提交。

提交前执行隐私检查；AI_LOG.md 逐轮复制双方对话并脱敏，DELIVERY.md 记录实际结果。v0.1 完成后提供可运行地址和 Draft PR 供用户测试。**单测、集成/E2E、Docker、CI 和用户本人明确人工审核全部通过前，禁止合并 main。** GitHub 当前套餐不支持私有库平台分支保护，此限制不豁免人工门禁。

## 文档

- [开发总纲](docs/DEVELOPMENT.md)：需求、架构、代码编排、契约、算法、异常、测试和实施顺序。
- [接口契约](docs/API_CONTRACT.md)：跨层字段、证据、返回值和错误约定。
- [前端设计](docs/FRONTEND_DESIGN.md)：工作台交互、设计 token、响应式与状态。
- [参考调研](docs/REFERENCES.md)：已读取的公开参考、借鉴范围与许可证边界。
- [Postman 调试说明](docs/POSTMAN.md)：导入集合、四个端口和合成请求；应用实现后执行。
- [交付说明](DELIVERY.md)：实际执行记录、启动、部署、回滚、缺口和演示路径。
- [会话记录](AI_LOG.md)：按日期复制双方对话原文，敏感值脱敏，并附每轮文件变更。
- [变更记录](CHANGELOG.md)：按可验证增量记录改动。

## 隐私

本地 `test/` 包含题目与原始资料，不进入 Git 和镜像构建上下文。测试仅使用合成样例；密钥通过 Python 运行时环境变量注入，不出现在前端、仓库或日志中。

## 仓库与验证

私有仓库：[lgcyuzusakura/careerlens](https://github.com/lgcyuzusakura/careerlens)。分支推送、PR 和 CI 状态以 [DELIVERY.md](DELIVERY.md) 的事实记录为准。GitHub 网络不可用时再评估用户指定的 Gitee；认证缺失与网络故障分别处理。

正式三小时考试计时尚未声明开始，不将文档准备冒充计时内开发记录。
