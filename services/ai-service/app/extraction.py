import json
import re
import unicodedata
from pathlib import Path

from .models import Entry, Evidence, Extraction, ModelOutput, Notice, Requirement, Resume, Skill


ROOT = Path(__file__).resolve().parents[3]
DICTIONARY = json.loads((ROOT / "config/skills.v1.json").read_text(encoding="utf-8"))
SKILLS = {item["id"]: item for item in DICTIONARY["skills"]}
PATTERNS = {
    key: [re.compile(r"(?<![A-Za-z0-9_])" + re.escape(alias) + r"(?![A-Za-z0-9_+#])", re.I) for alias in item["aliases"]]
    for key, item in SKILLS.items()
}


class Unanalyzable(ValueError):
    pass


def clean(value: str) -> list[str]:
    text = unicodedata.normalize("NFKC", value.replace("\r\n", "\n").replace("\r", "\n"))
    text = "".join(char for char in text if char in "\n\t" or unicodedata.category(char) not in {"Cc", "Cf", "Cs"})
    text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[邮箱已隐藏]", text)
    text = re.sub(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)", "[电话已隐藏]", text)
    text = re.sub(r"(?<!\w)\d{17}[0-9Xx](?!\w)", "[证件号已隐藏]", text)
    lines = [re.sub(r"[\t ]+", " ", line).strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    if not lines or len(lines) > 250:
        raise Unanalyzable("请提供有效文本，单份材料最多 250 个非空行。")
    return lines


def make_evidence(resume: str, jd: str) -> list[Evidence]:
    return [Evidence(id=f"{prefix}{index}", source=source, line=index, text=line)
            for value, prefix, source in [(resume, "R", "resume"), (jd, "J", "jd")]
            for index, line in enumerate(clean(value), 1)]


def mentions(skill_id: str, text: str):
    # Specific versions are retained; a generic Vue requirement also accepts a versioned mention.
    matches = [match for pattern in PATTERNS[skill_id] for match in pattern.finditer(text)]
    positive = []
    for match in matches:
        preceding = text[max(0, match.start()-24):match.start()]
        clause = re.split(r"[。;；,，\n]", preceding)[-1]
        if re.search(r"(?:未|没有|不)(?:曾|实际)?(?:使用|接触|掌握|熟悉|了解|学习)(?:过)?\s*$|(?:no experience (?:with|in)|never used|not familiar with)\s*$", clause, re.I):
            continue
        positive.append(match)
    return positive


def priority_for(text: str, match) -> str:
    start = max(text.rfind(separator, 0, match.start()) for separator in "。;；\n") + 1
    ends = [text.find(separator, match.end()) for separator in "。;；\n"]
    end = min((value for value in ends if value >= 0), default=len(text))
    clause = text[start:end]
    if re.search(r"优先|加分|preferred|nice.to.have", clause, re.I):
        return "preferred"
    if re.search(r"必须|熟悉|掌握|必备|required|must", clause, re.I):
        return "required"
    return "unspecified"


def rules(evidence: list[Evidence], mode="rules", warning=None) -> Extraction:
    resume = Resume()
    requirements = []
    for skill_id, item in SKILLS.items():
        resume_hits = [(line, mentions(skill_id, line.text)) for line in evidence if line.source == "resume"]
        resume_hits = [(line, matches) for line, matches in resume_hits if matches]
        if resume_hits:
            raw = list(dict.fromkeys(match.group() for _, matches in resume_hits for match in matches))[:20]
            resume.skills.append(Skill(skillId=skill_id, displayName=item["name"], rawMentions=raw, evidenceIds=[line.id for line, _ in resume_hits][:100]))
        jd_hits = [(line, match) for line in evidence if line.source == "jd" for match in mentions(skill_id, line.text)]
        if skill_id == "vue":
            jd_hits = [(line, match) for line, match in jd_hits if not mentions("vue2", line.text) and not mentions("vue3", line.text)]
        if jd_hits:
            weights = {"required": 3, "unspecified": 2, "preferred": 1}
            priority = max((priority_for(line.text, match) for line, match in jd_hits), key=weights.get)
            requirements.append(Requirement(skillId=skill_id, displayName=item["name"], priority=priority, evidenceIds=list(dict.fromkeys(line.id for line, _ in jd_hits))[:100]))
    section = None
    headings = {"education": r"教育背景|教育经历|education", "experience": r"工作经历|实习经历|职业经历|experience", "projects": r"项目经历|项目经验|projects?"}
    for line in (line for line in evidence if line.source == "resume"):
        found = next((key for key, pattern in headings.items() if re.fullmatch(r"[#\s]*" + "(?:" + pattern + r")[：:\s]*", line.text, re.I)), None)
        if found:
            section = found
            continue
        if re.fullmatch(r"[#\s]*(?:技能|专业技能|技术栈|skills?)[：:\s]*", line.text, re.I):
            section = None
            continue
        if section and len(getattr(resume, section)) < 20:
            # Preserve exact text; do not manufacture titles or rewrite accomplishments.
            getattr(resume, section).append(Entry(title=None, summary=line.text[:1000], evidenceIds=[line.id]))
    for key, msg in [("education", "材料中未识别到教育背景。"), ("projects", "材料中未识别到项目经历。")]:
        if not getattr(resume, key):
            resume.issues.append(Notice(code=f"NO_{key.upper()}_EVIDENCE", msg=msg))
    warnings = [Notice(code=warning or "RULES_MODE", msg="模型暂不可用，已使用规则提取。" if mode == "degraded" else "本次使用规则提取，复杂语义请核对原文。")]
    return Extraction(mode=mode, warnings=warnings, evidence=evidence, structuredResume=resume, requirements=requirements)


def validate_model(output: ModelOutput, evidence: list[Evidence]) -> ModelOutput:
    lookup = {line.id: line for line in evidence}

    def valid_ids(ids, source):
        if not ids or any(key not in lookup or lookup[key].source != source for key in ids):
            raise ValueError("Unsupported evidence reference")
        return [lookup[key] for key in ids]

    for item in output.structuredResume.skills:
        lines = valid_ids(item.evidenceIds, "resume")
        if item.skillId not in SKILLS or any(not mentions(item.skillId, line.text) for line in lines):
            raise ValueError("Unsupported skill evidence")
        item.displayName = SKILLS[item.skillId]["name"]
        if any(not any(raw in line.text for line in lines) for raw in item.rawMentions):
            raise ValueError("Unsupported raw mention")
    for item in output.requirements:
        lines = valid_ids(item.evidenceIds, "jd")
        if item.skillId not in SKILLS or any(not mentions(item.skillId, line.text) for line in lines):
            raise ValueError("Unsupported requirement evidence")
        item.displayName = SKILLS[item.skillId]["name"]
    for key in ("education", "experience", "projects"):
        for item in getattr(output.structuredResume, key):
            lines = valid_ids(item.evidenceIds, "resume")
            content = "\n".join(line.text for line in lines)
            if item.summary not in content or item.title is not None and item.title not in content:
                raise ValueError("Unsupported generated statement")
    if output.structuredResume.headline is not None and not any(output.structuredResume.headline in line.text for line in evidence if line.source == "resume"):
        raise ValueError("Unsupported headline")
    # Unknown skills and issue prose are regenerated locally, never accepted as new facts.
    output.structuredResume.unmappedSkills = []
    output.structuredResume.issues = []
    return output
