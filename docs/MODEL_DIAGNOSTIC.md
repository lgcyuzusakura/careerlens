# 模型超时诊断与流式验证

日期：2026-11-05，Asia/Shanghai。仅使用明确虚构的简历与 JD。凭据、模型返回正文和用户材料不进入本记录。

## 已复现的问题

- Docker 的 Python、Java、BFF 日志记录了约 9.3–10 秒的分析请求，HTTP 状态为 200；这是允许规则降级后的业务成功状态，不能据此判定模型成功。
- 对前端同源 `/api/v1/analyses` 发起合成材料请求，实际返回 `code=OK`、`mode=degraded`、`warnings[].code=LLM_TIMEOUT`，耗时 9366 ms。追踪号：`de0031a5-c85c-4a8b-9de0-edac13446abf`。
- 当时运行容器中的 key、base URL 和 model 均已配置；仅检查是否存在，没有打印值。旧镜像仅支持 Chat 协议，读取超时 9 秒、总预算 10 秒。
- 在同一 Python 容器中，最小 Chat 请求实际 200，耗时 4628 ms；最小 Responses 请求也实际 200，耗时 7591 ms。因此不能把这次故障归因于无效 key、服务完全不可达或中转站完全不支持 Chat。
- 将完整提取探测限定在独立进程内、临时允许 45 秒预算，实际 8162 ms 完成并通过 schema 和证据校验。不同调用耗时有波动，原 9 秒读取预算缺少余量。

## 已实现的修改

- Python 模型请求发送 `stream: true` 与 `Accept: text/event-stream`。Chat Completions 和 Responses 都通过固定版本 `httpx-sse==0.4.3` 解析 SSE。
- 同一个 HTTP 连接持续接收小块响应，不为每个分块重新发送简历或创建模型请求。这样不会因为分块重复计费，也不会丢失完整材料上下文。
- Chat 必须收到 `finish_reason=stop` 与 `[DONE]`；Responses 必须收到 `response.completed`。断流、截断、过滤、错误事件或不一致的最终文本都不作为成功结果。
- SSE 传输数据最多 1 MiB、4096 个事件；聚合文本最多 256 KiB。UTF-8 由 HTTP/SSE 库增量解码，支持网络分块恰好截断中文字符。
- 兼容忽略 `stream=true`、仍返回完整 JSON 的中转站；此兼容路径有同样的输出限制。
- 聚合后继续执行 Pydantic schema 与原文证据校验，再交给 Java 评分。浏览器的分析接口仍使用 `{code,msg,data}`，前端一次显示最终已校验结果，不展示未验证的模型片段。
- 当前 Python 模型总预算 30 秒、读取预算 29 秒；BFF、Java、Fastify、Nginx 和浏览器的超时均长于 Python 模型预算，防止上层提前中断。流式不会消除首包等待，也不保证每次模型调用都低于总预算；超时继续明确降级或在 required 模式返回错误。

## 实际验证

| 检查 | 结果 |
| --- | --- |
| Python 宿主测试，流式修改前 | 68 项通过 |
| Python Docker 构建内测试，流式修改前 | 68 项通过 |
| 新增真实 TCP SSE 集成测试 | Chat、Responses 各 1 项，2 项通过 |
| 最新 Python 宿主与 Docker 构建内测试 | 70 项通过 |
| Java `mvn -B -s settings.xml test` | 27 项通过；覆盖注册、JWT、越权、充值幂等、并发扣费、失败退款、抽成快照 |
| `npm test` | 前端 6 项、BFF 19 项通过 |
| 真实中转站 SSE，独立 Docker 容器 | `protocol=responses`、HTTP 200、`isSSE=true`；1233 字节聚合文本、3 个技能、8614 ms，schema 和证据校验通过 |

真实中转站结果与受控模型替身测试分别记录，不把 HTTP 200、规则降级或替身结果当作真实 LLM 成功。上述真实调用使用运行时凭据，可能产生中转站费用；没有保存请求或响应正文。

本轮临时验证镜像为 `careerlens-ai:streaming-validation-20261105`，用于测试，不作为正式 Git SHA release。四层发布、远端最新 CI、浏览器验收和跨版本回滚需按完整交付门禁另行核验，不能由单个 Python 容器的成功代替。

## 复查命令

```powershell
docker compose logs --no-color --tail 60 ai-service domain-api bff
python tests/diagnostics/model_probe.py --style chat
python tests/diagnostics/model_probe.py --style responses
python tests/diagnostics/model_probe.py --style chat --full-extraction
.\.venv\Scripts\python -m pytest -q services/ai-service/tests
```

`model_probe.py` 只打印配置存在性、状态、耗时和错误分类，不打印 key、URL、模型正文或材料。`--full-extraction` 使用当前运行容器的提取器和协议，仅在该独立探测进程临时放宽预算，不修改部署配置；未重建容器时，它测到的仍可能是旧版本。
