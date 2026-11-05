import { test } from 'node:test'
import assert from 'node:assert/strict'
import { buildApp } from '../src/app.js'
process.env.NODE_ENV = 'test'
const body = { resumeText: 'a'.repeat(20), jdText: 'Java Spring Boot SQL', options: { useExternalModel: false } }
async function withApp(options, fn) { const app = buildApp(options); try { await fn(app) } finally { await app.close() } }
test('rejects whitespace, unknown fields and wrong types before calling domain', () => withApp({ call: () => { throw new Error('Must not call') } }, async app => {
  for (const payload of [{ ...body, resumeText: ' ' }, { ...body, extra: true }, { ...body, options: { useExternalModel: 'true' } }]) {
    const r = await app.inject({ method: 'POST', url: '/api/v1/analyses', payload }); assert.equal(r.statusCode, 400); assert.match(r.headers['x-trace-id'], /^[a-f0-9-]{36}$/)
  }
}))
test('rejects invalid successful downstream data', () => withApp({ call: async () => ({ status: 200, payload: { code: 'OK', msg: 'ok', data: {} } }) }, async app => {
  assert.equal((await app.inject({ method: 'POST', url: '/api/v1/analyses', payload: body })).statusCode, 502)
}))
test('maps timeout without leaking downstream details', () => withApp({ call: async () => { throw Object.assign(new Error('private internal secret'), { name: 'TimeoutError' }) } }, async app => {
  const r = await app.inject({ method: 'POST', url: '/api/v1/analyses', payload: body }); assert.equal(r.statusCode, 504); assert.ok(!r.body.includes('private'))
}))
test('forwards validated white-listed input and trace', () => withApp({ call: async (path, options) => { assert.equal(path, '/api/v1/job-templates'); assert.match(options.traceId, /^[a-f0-9-]{36}$/); return { status: 200, payload: { code: 'OK', msg: 'OK', data: { items: [] } } } } }, async app => {
  const r = await app.inject('/api/v1/job-templates'); assert.equal(r.statusCode, 200); assert.deepEqual(Object.keys(r.json()).sort(), ['code', 'data', 'msg'])
}))
test('limits repeated requests', () => withApp({ rateLimit: 1, call: async () => ({ status: 200, payload: { code: 'OK', msg: 'OK', data: { items: [] } } }) }, async app => {
  await app.inject('/api/v1/job-templates'); const r = await app.inject('/api/v1/job-templates'); assert.equal(r.statusCode, 429)
}))
