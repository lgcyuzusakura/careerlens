package com.careerlens;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.*;

final class SkillDictionary {
    private SkillDictionary() {}
    static final Map<String,String> NAMES = load();
    private static Map<String,String> load() {
        try (var stream = SkillDictionary.class.getResourceAsStream("/skills.v1.json")) {
            var root = new ObjectMapper().readTree(stream);
            if (!"skills-v1".equals(root.path("version").asText())) throw new IllegalStateException("Dictionary version mismatch");
            var names = new HashMap<String,String>();
            for (var item : root.path("skills")) names.put(item.path("id").asText(), item.path("name").asText());
            return Map.copyOf(names);
        } catch (Exception e) { throw new IllegalStateException("Skill dictionary unavailable",e); }
    }
}
