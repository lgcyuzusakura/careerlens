import { test } from 'node:test'
import assert from 'node:assert/strict'
import { analysisSchema } from '../src/response-schema.js'

test('response text lengths use Unicode code points across schema boundaries', () => {
  const schema = analysisSchema.shape.evidence.element.shape.text
  assert.equal(schema.safeParse('😀'.repeat(20000)).success, true)
  assert.equal(schema.safeParse('😀'.repeat(20001)).success, false)
  const entry = analysisSchema.shape.structuredResume.shape.projects.element
  assert.equal(entry.shape.summary.safeParse('😀'.repeat(1000)).success, true)
  assert.equal(entry.shape.summary.safeParse('😀'.repeat(1001)).success, false)
})
