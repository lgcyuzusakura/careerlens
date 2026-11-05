# CareerLens

面向高校学生的简历与岗位分析工作台：输入简历文本和 JD，输出结构化简历、技能归一结果、命中证据、待补充证据及可解释的匹配分数。

**当前阶段：开发文档与实施计划。应用、应用测试、Docker 镜像和应用 CI 尚未实现，不可启动；已提供独立的文档检查 workflow。**

构建和运行以 Docker 为主，国内镜像源需可配置并锁定版本。固定端口：前端 3000、Java 8080、Node BFF 8081、Python 8082。业务接口统一 `{ code, msg, data }`。单测、集成测试、CI 和用户本人审核均通过后才允许合并 main。

## 强制请求链

```text
Vue 3 -> Node.js BFF -> Java / Spring Boot -> Python -> LLM
```

浏览器只调用 BFF；Java 持有领域契约与评分规则；Python 负责文本处理、技能提取及模型适配。LLM 不可用时保留规则提取能力，并明确展示降级状态。

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
