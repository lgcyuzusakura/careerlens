import { z } from 'zod'
const id = z.string().min(1).max(80)
const ids = z.array(z.string().min(1).max(8)).max(100)
const notice = z.object({ code: id, msg: z.string().max(500), evidenceIds: z.array(z.string()).max(20).optional() }).strict()
const entry = z.object({ title: z.string().max(200).nullable(), summary: z.string().max(1000), evidenceIds: ids.min(1) }).strict()
const skill = z.object({ skillId: id, displayName: z.string().max(80), rawMentions: z.array(z.string()).max(20), evidenceIds: ids.min(1) }).strict()
const priority = z.enum(['required', 'unspecified', 'preferred'])
export const analysisSchema = z.object({
  contractVersion: z.literal('analysis-v1'), ruleVersion: z.literal('skill-coverage-v1'), skillDictionaryVersion: z.literal('skills-v1'),
  mode: z.enum(['rules', 'llm', 'degraded']), warnings: z.array(notice).max(20),
  structuredResume: z.object({ headline: z.string().max(200).nullable(), education: z.array(entry).max(20), experience: z.array(entry).max(20), projects: z.array(entry).max(20), skills: z.array(skill).max(100), unmappedSkills: z.array(z.string()).max(100), issues: z.array(notice).max(20) }).strict(),
  requirements: z.array(z.object({ skillId: id, displayName: z.string().max(80), priority, weight: z.number().int().min(1).max(3), evidenceIds: ids.min(1) }).strict()).max(100),
  matches: z.array(z.object({ skillId: id, displayName: z.string().max(80), resumeEvidenceIds: ids.min(1), jdEvidenceIds: ids.min(1) }).strict()).max(100),
  gaps: z.array(z.object({ skillId: id, displayName: z.string().max(80), priority, reason: z.string().max(500), suggestion: z.string().max(500), jdEvidenceIds: ids.min(1) }).strict()).max(100),
  score: z.object({ value: z.number().int().min(0).max(100).nullable(), matchedWeight: z.number().int().min(0).max(300), totalWeight: z.number().int().min(0).max(300), reason: z.enum(['WEIGHTED_SKILL_COVERAGE', 'NO_RECOGNIZED_REQUIREMENTS']) }).strict(),
  evidence: z.array(z.object({ id: z.string().max(8), source: z.enum(['resume', 'jd']), line: z.number().int().min(1).max(500), text: z.string().min(1).max(20000) }).strict()).max(500)
}).strict()
export const templatesSchema = z.object({ items: z.array(z.object({ id, title: z.string().max(200), jdText: z.string().max(12000) }).strict()).max(20) }).strict()
