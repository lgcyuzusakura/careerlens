# 请求链演示手册（同一 trace / 15 分钟答辩配套）

配套 [15 分钟答辩稿](演讲稿.md) 与 `scripts/demo_chain.py`。日期：2026-11-05。所有材料均为合成、明确虚构，见 [JD_TEST_SAMPLE.md](JD_TEST_SAMPLE.md)。

## 1. 链路与端口

| 层 | 地址 | 入口 | 职责 | 是否产生分数 |
| --- | --- | --- | --- | --- |
| Vue 3 / Nginx | http://localhost:3000 | `/api/v1/analyses` 同源转发 | 展示、证据定位、导出 | 否 |
| Node BFF | http://localhost:8081 | `/api/v1/analyses` | 白名单、校验、编排、超时、错误映射 | 否（透传 Java 结果） |
| Java / Spring Boot | http://localhost:8080 | `/api/v1/matches` | 领域 DTO、规则版本、SkillMatch、ScorePolicy | **是** |
| Python / FastAPI | http://localhost:8082 | `/internal/v1/extractions` | 清洗、归一、提取、模型输出验证、降级 | 否 |
| LLM | 仅 Python 运行时配置 | OpenAI-compatible chat | 可选，需页面显式启用 | 否 |

浏览器业务只访问 3000 的同源 `/api`；8080/8081/8082 是绑定 127.0.0.1 的调试端口，用于 Postman / curl 与逐层讲解。

## 2. 一键演示（推荐）

```sh
python scripts/demo_chain.py
```

脚本六个步骤：

1. 四层健康探针（200）。
2. 从浏览器入口发一次真实分析，打印 `code`、信封、`mode`、命中、缺口、分数、证据条数与缺口措辞。
3. 用响应头里的 `X-Trace-Id` 检索 `docker compose logs`，打印 bff / domain-api / ai-service 三行同 trace 日志。
4. 用同一个 trace 直连 8081 / 8080 / 8082，打印每层的 `code`、响应 trace、是否有 `score`、requirements 数量。
5. 400 / 413 / 空要求 / 降级四个边界。
6. 生成 `output/demo/chain-*.json`（只有状态码、trace、计数，不含材料正文），最后打印 `PASS` 或 `FAIL`。

常用变体：

```sh
python scripts/demo_chain.py --no-logs                              # 无 docker CLI 时
python scripts/demo_chain.py --jd-file tests/fixtures/jd-synthetic.txt  # 招聘风格长 JD
python scripts/demo_chain.py --trace 0b3d5f70-9c2e-4a61-8d47-6e1f2a3b4c5d
```

默认命令**不发送外部模型请求**（`useExternalModel=false`）。只有确认运行时未配置真实模型 key 时，才用 `--include-degradation` 演示降级；脚本会打印警告，并在 `mode=llm` 时明确提示材料已发往真实网关。所有 PASS 结论都由脚本断言支撑；`--no-logs` 会把「同一 trace 日志」标记为「已跳过」，不会假装通过。报告只写状态码、trace、计数与服务名，不落盘日志正文。

注意：`--trace` 只是**客户端携带**的值。BFF 按安全设计丢弃它并生成新 UUID，屏幕上的「链路 trace」以第 2 步打印值为准；Java / Python 直连时复用该生成值。

## 3. trace 机制（讲稿要点）

- BFF `onRequest` 用 `randomUUID()` 生成 trace，写进 `X-Trace-Id` 响应头，并在调用 Java 时作为请求头传入。
- Java `TraceFilter` 只接受合法 UUID v4；非法或缺失则自行生成，并把同一 trace 传给 Python。
- Python 中间件同样校验 UUID v4，回显到响应头；`/internal/` 请求只记录 service / traceId / status / durationMs。
- 日志不含请求正文、简历、JD 或模型响应。
- 因此：一次浏览器请求能在三个后端服务日志里找到**同一个 trace**；客户端伪造的 trace 不会进入日志。

一次实测输出（合成材料，trace 每次不同）：

```text
[2/6]  HTTP 200  code=OK  envelope=True
       链路 trace = 1d744bf0-e1ae-450a-b6b6-1c3e43c9ae8e
       mode=rules  score=86 matched=6/7
       matches=['java', 'spring-boot']  gaps=['docker']
[3/6]  ai-service-1  | {"service": "ai-service", "traceId": "1d744bf0-...", "status": 200, ...}
       domain-api-1  | {"service":"domain-api","traceId":"1d744bf0-...", "status":200, ...}
       bff-1         | {"service":"bff","traceId":"1d744bf0-...", "status":200, ...}
[4/6]  BFF 8081 → score 有；Java 8080 → score 有；Python 8082 → score 无
```

## 4. curl 等价命令（脚本不可用时）

请求体（合成数据）：

```json
{
  "resumeText": "项目经历\n使用 Java 和 Spring Boot 实现合成课程管理 API，并编写单元测试。",
  "jdText": "必须掌握 Java、Spring Boot；Docker 经验优先。",
  "options": { "useExternalModel": false }
}
```

```sh
curl -i -X POST http://localhost:3000/api/v1/analyses \
  -H 'Content-Type: application/json' \
  -d '{"resumeText":"项目经历\n使用 Java 和 Spring Boot 实现合成课程管理 API，并编写单元测试。","jdText":"必须掌握 Java、Spring Boot；Docker 经验优先。","options":{"useExternalModel":false}}'
```

从响应头复制 `X-Trace-Id`，再逐层直连（把 `TRACE` 换成该值）：

```sh
TRACE=<复制的 UUID>
curl -s -o /dev/null -w '%{http_code}\n' -H "X-Trace-Id: $TRACE" \
  -H 'Content-Type: application/json' \
  -d '{"resumeText":"项目经历\n使用 Java 和 Spring Boot 实现合成课程管理 API，并编写单元测试。","jdText":"必须掌握 Java、Spring Boot；Docker 经验优先。","options":{"useExternalModel":false}}' \
  http://localhost:8080/api/v1/matches

curl -s -o /dev/null -w '%{http_code}\n' -H "X-Trace-Id: $TRACE" \
  -H 'Content-Type: application/json' \
  -d '{"resumeText":"项目经历\n使用 Java 和 Spring Boot 实现合成课程管理 API，并编写单元测试。","jdText":"必须掌握 Java、Spring Boot；Docker 经验优先。","options":{"useExternalModel":false},"contractVersion":"analysis-v1","skillDictionaryVersion":"skills-v1"}' \
  http://localhost:8082/internal/v1/extractions

docker compose logs --since 15m --no-color | grep "$TRACE"
```

更完整的十组调试请求见 [POSTMAN.md](POSTMAN.md) 和 `postman/CareerLens.postman_collection.json`。

## 5. 边界演示与预期

| 动作 | 预期 HTTP | 预期 code | 讲法 |
| --- | --- | --- | --- |
| 空白简历 / 未知字段 | 400 | `INVALID_INPUT` | BFF 先拦，不打扰下游；`data.errors` 只给安全字段名 |
| 170 KB 文本 | 413 | `PAYLOAD_TOO_LARGE` | Nginx 也返回统一 JSON 信封，不返回 HTML |
| 15000 个 emoji + Java | 200 | `OK` | 补充 Unicode 边界回归：曾因 Java JSON escape 膨胀触发 Python 413，已修 |
| JD 无技能词 | 200 | `OK`，`score.value=null` | 分母 0 不硬给 0 分，理由 `NO_RECOGNIZED_REQUIREMENTS` |
| `useExternalModel=true` 且无 key（需 `--include-degradation`） | 200 | `OK`，`mode=degraded` | 警告码随失败原因变化（`LLM_NOT_CONFIGURED` / `LLM_TIMEOUT` 等），不冒充模型成功；默认演示不发此请求 |

## 6. 演示后收尾

- `output/demo/` 与 `output/playwright/` 均在 `.gitignore` 内，不提交、不进镜像上下文。
- 报告不含材料正文；截图只含合成示例。
- 若现场改过 URL / key / `.env`，恢复后整链 `--force-recreate`，避免上游缓存旧容器地址。
- 演示结论以 [DELIVERY.md](../DELIVERY.md) 当轮记录为准；未跑过的检查一律说「未验证」。
