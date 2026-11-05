package com.careerlens;

import org.springframework.stereotype.Service;
import java.util.*;
import static com.careerlens.Models.*;

@Service
public class ScorePolicy {
    public int weight(String priority) {
        return switch (priority) { case "required" -> 3; case "unspecified" -> 2; case "preferred" -> 1; default -> throw new ServiceFailure(502, "UPSTREAM_FAILURE"); };
    }
    private void check(boolean valid) { if (!valid) throw new ServiceFailure(502, "UPSTREAM_FAILURE"); }
    public Analysis analyze(Extraction source) {
        try {
            check("analysis-v1".equals(source.contractVersion()) && "skills-v1".equals(source.skillDictionaryVersion()));
            check(Set.of("rules", "llm", "degraded").contains(source.mode()));
            check(source.warnings() != null && source.warnings().size() <= 20);
            check(!source.mode().equals("degraded") || !source.warnings().isEmpty());
            var resume = source.structuredResume();
            check(resume != null && resume.skills().size() <= 100 && source.requirements().size() <= 100 && source.evidence().size() <= 500);
            var evidence = new HashMap<String,Evidence>();
            for (var item : source.evidence()) {
                check(item.id() != null && item.text() != null && item.text().length() <= 40000 && Set.of("resume", "jd").contains(item.source()));
                check(evidence.put(item.id(), item) == null);
            }
            var skills = new LinkedHashMap<String,Skill>();
            for (var skill : resume.skills()) {
                check(SkillDictionary.NAMES.containsKey(skill.skillId()) && SkillDictionary.NAMES.get(skill.skillId()).equals(skill.displayName()));
                check(skill.skillId() != null && skill.displayName() != null && skill.evidenceIds() != null && !skill.evidenceIds().isEmpty());
                for (String id : skill.evidenceIds()) check(evidence.containsKey(id) && evidence.get(id).source().equals("resume"));
                skills.merge(skill.skillId(), skill, (a,b) -> new Skill(a.skillId(), a.displayName(), a.rawMentions(), java.util.stream.Stream.concat(a.evidenceIds().stream(), b.evidenceIds().stream()).distinct().toList()));
            }
            var requirements = new LinkedHashMap<String,Requirement>();
            for (var req : source.requirements()) {
                check(SkillDictionary.NAMES.containsKey(req.skillId()) && SkillDictionary.NAMES.get(req.skillId()).equals(req.displayName()));
                check(req.skillId() != null && req.displayName() != null && req.evidenceIds() != null && !req.evidenceIds().isEmpty());
                for (String id : req.evidenceIds()) check(evidence.containsKey(id) && evidence.get(id).source().equals("jd"));
                weight(req.priority());
                requirements.merge(req.skillId(), req, (a,b) -> weight(a.priority()) >= weight(b.priority()) ? a : b);
            }
            var weighted = new ArrayList<WeightedRequirement>(); var matches = new ArrayList<Match>(); var gaps = new ArrayList<Gap>();
            int total = 0, matched = 0;
            for (var req : requirements.values()) {
                int weight = weight(req.priority()); total += weight;
                weighted.add(new WeightedRequirement(req.skillId(), req.displayName(), req.priority(), weight, req.evidenceIds()));
                if (skills.containsKey(req.skillId())) {
                    matched += weight; matches.add(new Match(req.skillId(), req.displayName(), skills.get(req.skillId()).evidenceIds(), req.evidenceIds()));
                } else gaps.add(new Gap(req.skillId(), req.displayName(), req.priority(), "简历中未发现 " + req.displayName() + " 证据。", "如有相关实践，请补充真实项目中的用途、个人贡献和验证方法。", req.evidenceIds()));
            }
            Integer value = total == 0 ? null : (100 * matched * 2 + total) / (total * 2);
            return new Analysis("analysis-v1", "skill-coverage-v1", "skills-v1", source.mode(), source.warnings(), resume, weighted, matches, gaps,
                new Score(value, matched, total, total == 0 ? "NO_RECOGNIZED_REQUIREMENTS" : "WEIGHTED_SKILL_COVERAGE"), source.evidence());
        } catch (ServiceFailure e) { throw e; }
        catch (RuntimeException e) { throw new ServiceFailure(502, "UPSTREAM_FAILURE"); }
    }
}
