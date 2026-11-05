# CareerLens 公开参考调研

调研日期：2026-11-05。以下内容来自实际读取的公开 README、项目文档和 GitHub API；不是对这些项目完整源码或安全性的背书。只学习设计方法，不拷贝代码、界面资产或私人数据。

## 1. 用户指定的 devprep-ai

- [项目与 README](https://github.com/lgcyuzusakura/devprep-ai)
- [Spring Boot 与模型边界 ADR](https://github.com/lgcyuzusakura/devprep-ai/blob/main/docs/architecture/adr-0001-backend.md)
- [简历编辑与 JD 定向分析](https://github.com/lgcyuzusakura/devprep-ai/blob/main/docs/resume-editing.md)
- [Compose](https://github.com/lgcyuzusakura/devprep-ai/blob/main/compose.yaml)
- [CI](https://github.com/lgcyuzusakura/devprep-ai/blob/main/.github/workflows/ci.yml)

已读取上述正文。可借鉴：业务层隔离模型 adapter、模型输出不直接改变确定性业务结果、简历诊断引用原文、合成样例、不把模型网关测试和真实模型运行混为一谈、实际运行记录与未验证范围分开。

本项目差异：该项目文档描述 React + Spring Boot 主体及独立执行器，本题强制 Vue -> Node BFF -> Spring Boot -> Python，因此不复制其应用拓扑、浏览器框架、数据库或 Docker socket 方案。本项目不需要代码执行器，也不挂载 Docker socket 到应用容器。

其测试数量和运行记录只属于该参考项目，不计入 CareerLens。没有读取完整源码，因此不声称复用其内部实现或已经审查其安全性。

## 2. Resume Matcher

- [项目](https://github.com/srbhr/Resume-Matcher)
- [README](https://github.com/srbhr/Resume-Matcher/blob/main/README.md)
- [许可证](https://github.com/srbhr/Resume-Matcher/blob/main/LICENSE)

通过公开 API 读取 README 和仓库元数据，许可证元数据为 Apache-2.0。README 描述简历与 JD 对照、缺失关键词/技能提示、模型选择，以及由代码而非 LLM 执行 ATS 评分的设计。

可借鉴：先对齐岗位要求与真实经历，再给可解释改进；保留原简历事实；将提取和数值评分分开。CareerLens 不复制其 ATS 权重、React/Next.js 前端、导出模板或大规模功能。

没有对其评分算法逐行阅读和精度复现，不能把 README 宣称当本项目验证。本项目使用独立的版本化技能覆盖规则，不宣称与 ATS 或招聘结果等价。

## 3. OpenResume

- [项目](https://github.com/xitanggg/open-resume)
- [README](https://github.com/xitanggg/open-resume/blob/main/README.md)
- [许可证](https://github.com/xitanggg/open-resume/blob/main/LICENSE)

通过公开 API 读取 README 和仓库元数据，许可证元数据为 AGPL-3.0。README 描述简历编辑、PDF 解析和本地浏览器处理的隐私方向。

只借鉴“解析结果可检查”和“主动控制材料”的产品原则，不复用代码、模板或资产，避免把它的许可证或前端技术栈带入本项目。CareerLens 会在用户启用时向外部模型发送尽力脱敏文本，因此不能照搬该项目“数据完全不离开浏览器”的隐私描述。

## 4. 本次落实到设计的决定

| 参考点 | CareerLens 决策 | 验收位置 |
| --- | --- | --- |
| 来源证据优先 | 行 ID、片段引用、归一化技能与原始表达并存 | 契约和证据测试 |
| 稳定数值规则 | Java ScorePolicy，required/unspecified/preferred 加权 | Java 单测与 UI 评分说明 |
| 不虚构简历事实 | 不存在的实体丢弃、语义不足提示，不自动补经历 | Python 输出验证与反例 |
| 隐私清楚可见 | 原始材料本地保留、模型显式开关、日志不记正文 | 忽略规则、UI、密钥扫描 |
| 可重复运行 | 四服务 Compose、合成样例、模型替身、真实 HTTP | CI 和 E2E |
| 文档可审计 | 每轮 AI_LOG/DELIVERY、渐进提交、回滚清单 | Git 历史和交付门禁 |

## 5. 调研的限制

未下载用户真实简历，未向外部项目或模型发送材料，未导入参考项目依赖。raw GitHub 某次请求出现等待，已终止并改用带超时的 Contents API，随后关键文档读取成功。当前没有理由把该事件判定为 GitHub 全面不可达。

后续若确需复制第三方代码或资产，必须先读取对应版本许可证、保留声明并记录来源；本轮无此类复制。
