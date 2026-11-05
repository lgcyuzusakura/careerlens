# CareerLens v1 接口契约

状态：四层已实现；结构 Schema 见 `contracts/analysis-v1.schema.json` 和 `contracts/analysis-input-v1.schema.json`，使用 `node scripts/export-contract.mjs` 重新生成。Schema 之外仍校验 NFKC/trim 后码点长度及证据语义。此文档中的 JSON 全为合成数据，不来自用户简历。

## 1. 通用约定

- Content-Type: application/json；字段 camelCase；禁止未知字段。
- 文本长度按 Unicode code point 计；请求 UTF-8 body 上限 160 KiB，原始与 NFKC 清洗后都检查。
- 所有业务接口信封只有 `code`、`msg`、`data` 三个顶层字段；字段校验信息放 `data.errors`，禁止堆栈和请求正文。
- 成功 HTTP 200，code=OK；一般错误 data=null，校验错误 data={errors:[...]}；UUID traceId 只通过 `X-Trace-Id` 响应头提供，前端与 Postman 从 header 读取。
- 本机调试端口：前端 3000、Java 8080、Node BFF 8081、Python 8082；均绑定 127.0.0.1。浏览器仍只访问前端同源 /api，直接端口为 Postman/curl 服务调试用途。
- 下游响应还应设置 512 KiB body 上限，超过为协议错误，不无限读取。
- 日期只能返回原文有依据的值；无法识别返回 null，不推断具体年份或工作时长。

## 2. 浏览器与 BFF

### POST /api/v1/analyses

```json
{
  "resumeText": "项目经历\n使用 Java 和 Spring Boot 实现合成课程管理 API。",
  "jdText": "必须掌握 Java、Spring Boot；Docker 经验优先。",
  "options": {
    "useExternalModel": false
  }
}
```

| 字段 | 限制 |
| --- | --- |
| resumeText | string，清理后的非空白文本，20–20000 code points |
| jdText | string，清理后的非空白文本，10–12000 code points |
| options | 只允许 useExternalModel；未提供时默认 false |
| options.useExternalModel | boolean；只允许用户明确启用，不接受字符串 true |

拒绝 null、数组代替对象、数值转字符串、未知字段、前端给的 key、model、providerUrl、score 和不受控超时参数。入参对象通过 schema 后重新构造 DTO，不用 spread 原始 body。

成功响应形状：

```json
{
  "code": "OK",
  "msg": "分析完成",
  "data": {
    "contractVersion": "analysis-v1",
    "ruleVersion": "skill-coverage-v1",
    "skillDictionaryVersion": "skills-v1",
    "mode": "rules",
    "warnings": [{
      "code": "RULES_MODE",
      "msg": "本次使用规则提取，请核对复杂语义。"
    }],
    "structuredResume": {
      "headline": null,
      "education": [],
      "experience": [],
      "projects": [{
        "title": "课程管理 API",
        "summary": "使用 Java 和 Spring Boot 实现合成课程管理 API。",
        "evidenceIds": ["R2"]
      }],
      "skills": [{
        "skillId": "java",
        "displayName": "Java",
        "rawMentions": ["Java"],
        "evidenceIds": ["R2"]
      }, {
        "skillId": "spring-boot",
        "displayName": "Spring Boot",
        "rawMentions": ["Spring Boot"],
        "evidenceIds": ["R2"]
      }],
      "unmappedSkills": [],
      "issues": [{
        "code": "NO_EDUCATION_EVIDENCE",
        "msg": "材料中未发现教育背景。",
        "evidenceIds": []
      }]
    },
    "requirements": [{
      "skillId": "java", "displayName": "Java", "priority": "required", "weight": 3, "evidenceIds": ["J1"]
    }, {
      "skillId": "spring-boot", "displayName": "Spring Boot", "priority": "required", "weight": 3, "evidenceIds": ["J1"]
    }, {
      "skillId": "docker", "displayName": "Docker", "priority": "preferred", "weight": 1, "evidenceIds": ["J1"]
    }],
    "matches": [{
      "skillId": "java", "displayName": "Java", "resumeEvidenceIds": ["R2"], "jdEvidenceIds": ["J1"]
    }, {
      "skillId": "spring-boot", "displayName": "Spring Boot", "resumeEvidenceIds": ["R2"], "jdEvidenceIds": ["J1"]
    }],
    "gaps": [{
      "skillId": "docker", "displayName": "Docker", "priority": "preferred",
      "reason": "简历中未发现 Docker 证据。",
      "suggestion": "如有容器实践，请补充真实项目中的用途和验证方法。",
      "jdEvidenceIds": ["J1"]
    }],
    "score": {
      "value": 86,
      "matchedWeight": 6,
      "totalWeight": 7,
      "reason": "WEIGHTED_SKILL_COVERAGE"
    },
    "evidence": [{
      "id": "R1", "source": "resume", "line": 1, "text": "项目经历"
    }, {
      "id": "R2", "source": "resume", "line": 2, "text": "使用 Java 和 Spring Boot 实现合成课程管理 API。"
    }, {
      "id": "J1", "source": "jd", "line": 1, "text": "必须掌握 Java、Spring Boot；Docker 经验优先。"
    }]
  }
}
```

样例用于说明响应结构，数值取自已跑通的合成材料请求；仍不是对任意输入的承诺。实际 project title 若没有原文可定位依据，应设 null；不能由 UI 示例反推解析承诺。

### 结果不变量

- `mode` 只能为 llm / rules / degraded；有降级时 warning 必须非空。
- 技能、要求、命中、缺口最多各 100 项；教育、工作、项目最多各 20 项；warning 和 issue 最多各 20 项。
- 显示名最长 80、标题最长 200、摘要最长 1000、建议最长 500 code points；证据行最多 500 行且不超过清洗后输入上限。
- evidence 按清洗后非空行编号，每份材料最多 250 个非空行（合计 500），每行最多 20000 code points；过多行拒绝为 422，不能静默截断造成丢证据。
- 每个 evidenceId 必须存在且 source 正确。matches 的 resumeEvidenceIds 非空，不能引用 JD 来证明简历技能。
- matches 与 gaps 互斥，按 skillId 去重，其并集等于可识别 requirements；未知技能只列到 unmappedSkills 和 warning。
- 所有 `weight` 由 Java ScorePolicy 回填，不接受 Python/LLM 任意权重。
- score.value 是 0–100 整数或 null；分母 0 时 value=null、matchedWeight=0、reason=NO_RECOGNIZED_REQUIREMENTS。
- 分数 denominator 和 numerator 可由 requirements 与 matches 重算，契约测试必须检查。

### GET /api/v1/job-templates

由 BFF 调 Java `GET /api/v1/job-templates` 编排，返回至少两份明确标识的合成模板，不抓取第三方招聘正文。

```json
{
  "code": "OK",
  "msg": "OK",
  "data": {
    "items": [{
      "id": "java-campus",
      "title": "Java 校招开发（合成示例）",
      "jdText": "熟悉 Java、Spring Boot 和 SQL，Docker 经验优先。"
    }]
  }
}
```

前端主动选择模板才填 JD，不覆盖已编辑文本而无提示。模板可用性不影响自定义 JD 分析；模板读取失败保留手动输入。

## 3. BFF -> Java

`POST /api/v1/matches` 使用与 BFF 请求相同的三字段 DTO，以及 `X-Trace-Id` 请求头。Java 重新校验未知字段、code point 长度和 options，不仅依赖 BFF 的验证结果。

Java controller 只做协议转换，MatchService 调 ExtractionClient 后做词典版本验证、要求去重、SkillMatch 和 ScorePolicy。响应就是最终 AnalysisResult 的统一信封。模型配置、密钥、prompt 不进入 DTO。

职责测试：若 Python 提取集合固定，Java 分数必须固定；Java 不接受调用方提供的 score/weights；不向浏览器返回 Python 原始响应或异常堆栈。

## 4. Java -> Python

`POST /internal/v1/extractions`：

```json
{
  "resumeText": "项目经历\n使用 Java 和 Spring Boot 实现合成课程管理 API。",
  "jdText": "必须掌握 Java、Spring Boot；Docker 经验优先。",
  "options": { "useExternalModel": false },
  "contractVersion": "analysis-v1",
  "skillDictionaryVersion": "skills-v1"
}
```

响应 data 为 `ExtractionResult`：

| 字段 | 定义 |
| --- | --- |
| contractVersion / skillDictionaryVersion | 必须与请求和本地支持版本相同，不支持返回 422 |
| mode / warnings | 实际提取路径与安全原因，不含 provider 原始错误正文 |
| structuredResume | 同最终响应的结构化信息与证据 |
| requirements | skillId、displayName、priority、evidenceIds；不返回 weight |
| evidence | 经脱敏与清洗后的行 ID、source、line、text |

Python 不返回最终 matches、gaps、score，Java 统一计算。Python 负责技能与来源合法性，Java 再检查 ID/引用/版本和输入规模，防协议漂移。

## 5. Python -> 外部 LLM

运行时只读取 `OPENAI_API_KEY`、`OPENAI_BASE_URL` 和 `OPENAI_MODEL`，使用配置中明确支持的 OpenAI-compatible chat JSON 协议。base URL 必须由服务运维设置，不接受前端提供。不自动选择未验证的模型或探测账户列表。

发送：系统提取规则、受控技能 ID/别名、标记为不可信数据的脱敏简历/JD 行。限制输出 token，不启用工具；schema 中无 score。原始 provider response 不透传；Pydantic/schema 和本地证据验证失败走模式表。

CI 的受控模型服务器至少提供：合法 JSON、伪造证据、额外字段、429、延迟、截断 JSON、过大响应。CI 无真实 key。真实 provider 通过运行时私密配置单独 smoke，记录 traceId、状态和耗时，不保存正文与 Authorization。

## 6. 统一错误表

| HTTP | code | 触发 | UI 行为 |
| --- | --- | --- | --- |
| 400 | INVALID_INPUT | 空白、长度、未知字段、非法 options | 定位字段并保留输入 |
| 404 | NOT_FOUND | 岗位模板等资源不存在 | 提示改用手动 JD |
| 413 | PAYLOAD_TOO_LARGE | UTF-8 body 超上限 | 显示长度限制 |
| 415 | UNSUPPORTED_MEDIA_TYPE | 非 JSON | 安全提示，前端开发错误可排查 |
| 422 | UNANALYZABLE_INPUT | 清洗后无有效文本、行数过多或不支持的契约 | 提示调整材料 |
| 429 | RATE_LIMITED | 有界并发/请求速率达到限制 | 保留输入，显示稍后重试 |
| 502 | UPSTREAM_FAILURE | 连接失败、5xx、错误 schema、过大响应 | 安全提示 + traceId，可主动重试 |
| 503 | SERVICE_UNAVAILABLE | 未 ready、required 模型配置/服务不可用 | 保留材料，说明稍后重试 |
| 504 | UPSTREAM_TIMEOUT | 完整调用 deadline 到期 | 保留材料，允许主动重试 |

provider 429 在 auto 模式可变成 200 degraded + LLM_RATE_LIMITED；required 则映射服务依赖不可用，不把 provider 私密响应转发。内部返回 400/422 时需校验错误 code 后保留语义，未知正文统一遮蔽。

```json
{
  "code": "INVALID_INPUT",
  "msg": "请检查输入内容。",
  "data": {
    "errors": [{ "field": "resumeText", "msg": "简历至少需要 20 个字符。" }]
  }
}
```

data.errors 只允许安全字段名和 msg，不回显被拒绝的输入值。遇到恶意 traceId 不能原样写 header 或日志。HTTP 状态与 code 同时表达结果，不把失败统一包装成 HTTP 200。

## 7. 健康与版本

- BFF/Python：`GET /healthz` liveness、`GET /readyz` readiness。
- Java：Actuator liveness/readiness health endpoint；只暴露必要信息，不暴露 env/configprops。
- 静态前端：本地健康 path，检查静态服务可响应。
- readiness 不对每次探测调用外部模型。required 模式 key 缺失时 not ready；auto/rules 无 key 可以 ready。
- 本机开发按用户要求发布四个 127.0.0.1 调试端口，公网部署 profile 关闭内部端口。业务接口统一信封；原生 Actuator 管理健康接口保留标准 `{status:...}`，与业务响应区分。

## 8. 契约验收

共享 fixture 至少包含：完整命中、部分命中、0 命中、0 要求、重复技能、优先级冲突、否定、未知技能、中英文/emoji、非法字段、证据伪造、降级、下游超时。

各语言用自己的类型和校验器实现，但同一 fixture 必须得到一致判定。schema 变化先决定兼容性；破坏性字段变更需新版本，不让发布四层任意混搭。

## 9. REST 调试与 Postman

导入 `postman/CareerLens.postman_collection.json`，变量为 `webBaseUrl=http://localhost:3000`、`bffBaseUrl=http://localhost:8081`、`javaBaseUrl=http://localhost:8080`、`pythonBaseUrl=http://localhost:8082`。具体操作见 [Postman 说明](POSTMAN.md)。

集合覆盖浏览器入口分析、直连 BFF 分析、Java 匹配、Python 提取、非法参数、岗位模板和健康探针。请求仅使用合成数据，options.useExternalModel=false；应用已实现，`scripts/smoke.py` 与 `scripts/demo_chain.py` 已用等价请求在线跑通四层链路。Postman/Newman 的独立 Collection run 仍未执行，不声称该工具已验证。
