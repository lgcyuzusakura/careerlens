package com.careerlens;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import java.util.List;

public final class Models {
    private Models() {}
    public record Envelope<T>(String code, String msg, T data) {
        public static <T> Envelope<T> ok(T data) { return new Envelope<>("OK", "分析完成", data); }
    }
    public record Options(@NotNull Boolean useExternalModel) {}
    public record Input(@NotNull String resumeText, @NotNull String jdText, @Valid Options options) {}
    public record ExtractionInput(String resumeText, String jdText, Options options, String contractVersion, String skillDictionaryVersion) {}
    public record Notice(String code, String msg, List<String> evidenceIds) {}
    public record Entry(String title, String summary, List<String> evidenceIds) {}
    public record Skill(String skillId, String displayName, List<String> rawMentions, List<String> evidenceIds) {}
    public record Resume(String headline, List<Entry> education, List<Entry> experience, List<Entry> projects,
                         List<Skill> skills, List<String> unmappedSkills, List<Notice> issues) {}
    public record Requirement(String skillId, String displayName, String priority, List<String> evidenceIds) {}
    public record WeightedRequirement(String skillId, String displayName, String priority, int weight, List<String> evidenceIds) {}
    public record Evidence(String id, String source, int line, String text) {}
    public record Extraction(String contractVersion, String skillDictionaryVersion, String mode, List<Notice> warnings,
                             Resume structuredResume, List<Requirement> requirements, List<Evidence> evidence) {}
    public record Match(String skillId, String displayName, List<String> resumeEvidenceIds, List<String> jdEvidenceIds) {}
    public record Gap(String skillId, String displayName, String priority, String reason, String suggestion, List<String> jdEvidenceIds) {}
    public record Score(Integer value, int matchedWeight, int totalWeight, String reason) {}
    public record Analysis(String contractVersion, String ruleVersion, String skillDictionaryVersion, String mode,
                           List<Notice> warnings, Resume structuredResume, List<WeightedRequirement> requirements,
                           List<Match> matches, List<Gap> gaps, Score score, List<Evidence> evidence) {}
    public record Job(String id, String title, String jdText) {}
}
