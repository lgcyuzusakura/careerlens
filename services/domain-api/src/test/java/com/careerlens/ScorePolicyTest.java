package com.careerlens;

import org.junit.jupiter.api.Test;
import java.util.List;
import static com.careerlens.Models.*;
import static org.junit.jupiter.api.Assertions.*;

class ScorePolicyTest {
    private final ScorePolicy policy = new ScorePolicy();
    Extraction source(List<Requirement> requirements) {
        return new Extraction("analysis-v1","skills-v1","rules",List.of(),new Resume(null,List.of(),List.of(),List.of(),
            List.of(new Skill("java","Java",List.of("Java"),List.of("R1")),new Skill("spring-boot","Spring Boot",List.of("Spring Boot"),List.of("R1"))),List.of(),List.of()),requirements,
            List.of(new Evidence("R1","resume",1,"Java Spring Boot"),new Evidence("J1","jd",1,"Java Spring Boot Docker")));
    }
    @Test void weightedCoverageAndDuplicateRules() {
        var data = policy.analyze(source(List.of(new Requirement("java","Java","required",List.of("J1")),new Requirement("spring-boot","Spring Boot","required",List.of("J1")),new Requirement("docker","Docker","preferred",List.of("J1")),new Requirement("java","Java","preferred",List.of("J1")))));
        assertEquals(86,data.score().value()); assertEquals(7,data.score().totalWeight()); assertEquals(2,data.matches().size()); assertEquals(1,data.gaps().size());
    }
    @Test void noRequirementsIsNotPerfectMatch() { assertNull(policy.analyze(source(List.of())).score().value()); }
    @Test void noMatchesIsZero() { assertEquals(0,policy.analyze(source(List.of(new Requirement("docker","Docker","required",List.of("J1"))))).score().value()); }
    @Test void rejectsFabricatedEvidence() { assertThrows(ServiceFailure.class,() -> policy.analyze(source(List.of(new Requirement("docker","Docker","required",List.of("R1")))))); }
    @Test void unicodeLengthAndWhitespace() { assertDoesNotThrow(() -> ApiController.validateText("😀".repeat(20),20,20)); assertThrows(ServiceFailure.class,() -> ApiController.validateText(" ".repeat(30),20,20000)); }
}
