# Postman 与 REST 调试

状态：接口设计配套集合已提供，应用尚未实现，当前无法在线执行请求。集合不是已通过的接口测试报告。

## 1. 导入

Postman 选择 Import，导入 [CareerLens.postman_collection.json](../postman/CareerLens.postman_collection.json)。无需导入真实环境或凭据，所有变量默认指向 localhost：

| Collection variable | 默认值 | 用途 |
| --- | --- | --- |
| webBaseUrl | http://localhost:3000 | 浏览器同源入口，全链路分析 |
| javaBaseUrl | http://localhost:8080 | Java 领域 REST |
| bffBaseUrl | http://localhost:8081 | Node BFF REST |
| pythonBaseUrl | http://localhost:8082 | Python 提取 REST |

接口和字段详见 [API 契约](API_CONTRACT.md)。Docker 实现后启动四个服务并检查健康，再运行集合。所有宿主端口仅绑定 127.0.0.1，不为调试而对外开放。

## 2. 请求顺序

1. 执行健康分组，确认 Node、Java 和 Python 返回 HTTP 200；Java 原生 Actuator 是管理探针，响应为原生 status 结构。
2. 执行前端入口的模板 GET 和合成简历分析 POST，验证真实 BFF -> Java -> Python HTTP 链。
3. 执行空白简历与未知字段用例，期望 HTTP 400，检查错误信封和字段定位。
4. 分别直调 BFF、Java 和 Python，核对分层 DTO；Python 只返回提取，不返回最终业务评分。
5. 读取响应头 X-Trace-Id，在 Compose 日志中查找相同 ID。不要在日志输出请求正文、Authorization 或模型响应原文。

业务响应必须只有 `{ code, msg, data }` 三个顶层字段，成功 code=OK，失败使用对应错误码与真实 HTTP 状态。集合测试检查 status、信封和 trace header；健康探针只检查 HTTP 状态，不把管理协议误当业务接口。

## 3. 规则模式与外部模型

集合请求均为虚构示例，useExternalModel=false，不含 API key、模型 URL、provider 或个人简历。默认 auto/rules 环境下这些请求应在无 key 时完成规则分析。required 环境要求明确同意外部模型，因此不能照搬默认规则集合的成功断言。

真实模型 smoke 单独进行：用户在本机运行时配置 Python 环境变量，明确开启外部模型选项；不要把 key 加入 Collection、Environment、截图或 Git。验证结果必须注明实际 mode，不能拿规则结果当真实模型成功。

## 4. PowerShell 调试示例

以下命令仅在实现并启动 Docker 服务后执行，目前没有执行：

```powershell
$analysisPayload = @{
    resumeText = "项目经历：使用 Java 和 Spring Boot 实现合成课程管理 API，并编写单元测试。"
    jdText = "必须掌握 Java、Spring Boot，Docker 经验优先。"
    options = @{ useExternalModel = $false }
} | ConvertTo-Json -Depth 4
$analysisResponse = Invoke-WebRequest `
    -Uri 'http://localhost:8081/api/v1/analyses' `
    -Method Post `
    -ContentType 'application/json; charset=utf-8' `
    -Body ([Text.Encoding]::UTF8.GetBytes($analysisPayload))
$analysisResponse.Headers['X-Trace-Id']
$analysisResponse.Content
```

直接调 Java 使用 http://localhost:8080/api/v1/matches；Python 使用 http://localhost:8082/internal/v1/extractions 且需要契约和词典版本字段，优先用已提供的集合避免手写错误。

## 5. 验收记录

当前只提供合法 JSON 集合与设计请求，尚无应用响应，尚未执行 Postman/Newman。实现后补记录执行时间、版本 SHA、请求数/通过数和失败原因；不能提交包含真实材料的 Collection run 导出。
