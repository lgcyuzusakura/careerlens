from typing import Literal
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Options(StrictModel):
    useExternalModel: bool = False


class ExtractionInput(StrictModel):
    resumeText: str = Field(min_length=20, max_length=20000)
    jdText: str = Field(min_length=10, max_length=12000)
    options: Options = Field(default_factory=Options)
    contractVersion: Literal["analysis-v1"]
    skillDictionaryVersion: Literal["skills-v1"]

    @field_validator("resumeText", "jdText")
    @classmethod
    def normalized_bounds(cls, value, info):
        size = len(unicodedata.normalize("NFKC", value).strip())
        minimum, maximum = (20, 20000) if info.field_name == "resumeText" else (10, 12000)
        if not minimum <= size <= maximum or any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise ValueError("Invalid normalized length or encoding")
        return value


class Notice(StrictModel):
    code: str = Field(max_length=80)
    msg: str = Field(max_length=500)
    evidenceIds: list[str] = Field(default_factory=list, max_length=20)


class Entry(StrictModel):
    title: str | None = Field(default=None, max_length=200)
    summary: str = Field(max_length=1000)
    evidenceIds: list[str] = Field(min_length=1, max_length=20)


class Skill(StrictModel):
    skillId: str = Field(max_length=80)
    displayName: str = Field(max_length=80)
    rawMentions: list[str] = Field(max_length=20)
    evidenceIds: list[str] = Field(min_length=1, max_length=100)


class Resume(StrictModel):
    headline: str | None = Field(default=None, max_length=200)
    education: list[Entry] = Field(default_factory=list, max_length=20)
    experience: list[Entry] = Field(default_factory=list, max_length=20)
    projects: list[Entry] = Field(default_factory=list, max_length=20)
    skills: list[Skill] = Field(default_factory=list, max_length=100)
    unmappedSkills: list[str] = Field(default_factory=list, max_length=100)
    issues: list[Notice] = Field(default_factory=list, max_length=20)


class Requirement(StrictModel):
    skillId: str = Field(max_length=80)
    displayName: str = Field(max_length=80)
    priority: Literal["required", "unspecified", "preferred"]
    evidenceIds: list[str] = Field(min_length=1, max_length=100)


class Evidence(StrictModel):
    id: str = Field(max_length=8)
    source: Literal["resume", "jd"]
    line: int = Field(ge=1, le=500)
    text: str = Field(min_length=1, max_length=20000)


class ModelOutput(StrictModel):
    structuredResume: Resume
    requirements: list[Requirement] = Field(max_length=100)


class Extraction(ModelOutput):
    contractVersion: Literal["analysis-v1"] = "analysis-v1"
    skillDictionaryVersion: Literal["skills-v1"] = "skills-v1"
    mode: Literal["rules", "llm", "degraded"]
    warnings: list[Notice] = Field(max_length=20)
    evidence: list[Evidence] = Field(max_length=500)
