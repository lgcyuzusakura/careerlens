package com.careerlens;

import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;
import java.util.*;
import static com.careerlens.Models.*;

@RestController
@RequestMapping("/api/v1")
public class ApiController {
    private final ExtractionClient client; private final ScorePolicy policy; private final Accounts accounts;
    public ApiController(ExtractionClient client, ScorePolicy policy, Accounts accounts) { this.client = client; this.policy = policy; this.accounts=accounts; }
    @PostMapping("/matches")
    public Envelope<Analysis> match(@Valid @RequestBody Input input, @RequestAttribute("traceId") String trace, @RequestAttribute("actor") Accounts.Actor actor) {
        validateText(input.resumeText(), 20, 20000); validateText(input.jdText(), 10, 12000);
        return Envelope.ok(accounts.analysis(actor,trace,() -> policy.analyze(client.extract(input, trace))));
    }
    static void validateText(String text, int min, int max) {
        var normalized = java.text.Normalizer.normalize(text, java.text.Normalizer.Form.NFKC).strip();
        int size = normalized.codePointCount(0, normalized.length());
        if (size < min || size > max || text.codePointCount(0,text.length()) > max) throw new ServiceFailure(400, "INVALID_INPUT");
    }
    @GetMapping("/job-templates")
    public Envelope<Map<String,List<Job>>> templates() {
        return Envelope.ok(Map.of("items", List.of(
            new Job("java-campus", "Java 校招开发（合成示例）", "必须熟悉 Java、Spring Boot 和 SQL。掌握 Redis 和 Git，Docker 经验优先。"),
            new Job("frontend-campus", "前端校招开发（合成示例）", "掌握 JavaScript、TypeScript、Vue 3 和 CSS，熟悉 Git，Docker 经验优先。"),
            new Job("python-api", "Python 服务开发（合成示例）", "必须熟悉 Python、SQL 和 REST API。掌握 Linux 和 Docker，Redis 经验优先。"),
            new Job("fullstack", "全栈开发（合成示例）", "必须熟悉 JavaScript、Vue 和 Node.js。了解 Java、Spring Boot、SQL 与 Git，Docker 经验优先。"),
            new Job("cloud", "云平台开发（合成示例）", "必须熟悉 Linux、Docker 和 Kubernetes。掌握 Python、Git，Java 与 SQL 经验优先。"),
            new Job("quality", "测试开发（合成示例）", "必须熟悉 Java、JUnit、SQL 和 REST API。掌握 Git 与 Linux，Docker 经验优先。"))));
    }
}
