import { test } from 'node:test'
import assert from 'node:assert/strict'
import { buildApp } from '../src/app.js'

process.env.NODE_ENV = 'test'
const auth = { authorization: 'Bearer synthetic.jwt.fixture' }
const id = '741d5c5e-d388-42a6-a610-df5cd74be839'
const date = '2026-11-05T12:00:00Z'
const user = { id, username: 'synthetic', role: 'USER', credits: 10, createdAt: date }
const settings = { commissionBps: 1000, creditsPerYuan: 10, analysisCost: 1, paymentMode: 'SIMULATED' }
const ok = data => ({ status: 200, payload: { code: 'OK', msg: 'ok', data } })
async function usingApp(call, work) { const app = buildApp({ call }); try { await work(app) } finally { await app.close() } }

function multipart({ filename = 'synthetic.md', content = Buffer.from('# Synthetic Java resume'), target = 'resume', fieldFirst = true } = {}) {
  const boundary = 'careerlens-synthetic-upload-boundary'
  const field = `--${boundary}\r\nContent-Disposition: form-data; name="target"\r\n\r\n${target}\r\n`
  const file = Buffer.concat([Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="file"; filename="${filename}"\r\nContent-Type: application/octet-stream\r\n\r\n`), content, Buffer.from('\r\n')])
  return { headers: { ...auth, 'content-type': `multipart/form-data; boundary=${boundary}` }, payload: Buffer.concat(fieldFirst ? [Buffer.from(field), file, Buffer.from(`--${boundary}--\r\n`)] : [file, Buffer.from(field), Buffer.from(`--${boundary}--\r\n`)]) }
}

test('auth rejects role injection, invalid names and BCrypt truncation before forwarding', () => usingApp(() => { throw new Error('must not forward') }, async app => {
  for (const payload of [
    { username: 'synthetic', password: 'synthetic-password', role: 'ADMIN' },
    { username: 'bad name', password: 'synthetic-password' },
    { username: 'synthetic', password: '密'.repeat(25) },
    { username: 'synthetic', password: 'short' }
  ]) assert.equal((await app.inject({ method: 'POST', url: '/api/v1/auth/register', payload })).statusCode, 400)
}))

test('valid login forwards only credential fields and validates session response', () => usingApp(async (path, options) => {
  assert.equal(path, '/api/v1/auth/login')
  assert.deepEqual(options.body, { username: 'synthetic', password: 'synthetic-password' })
  assert.equal(options.method, 'POST')
  return ok({ token: 'synthetic.jwt.fixture', expiresAt: date, user })
}, async app => {
  const response = await app.inject({ method: 'POST', url: '/api/v1/auth/login', payload: { username: 'synthetic', password: 'synthetic-password' } })
  assert.equal(response.statusCode, 200)
  assert.equal(response.json().data.user.credits, 10)
  assert.equal(response.headers['cache-control'], 'no-store')
}))

test('account rejects anonymous calls and forwards bearer token for authenticated calls', () => usingApp(async (path, options) => {
  assert.equal(path, '/api/v1/account'); assert.equal(options.token, auth.authorization)
  return ok({ user, recharges: [], analyses: [] })
}, async app => {
  const denied = await app.inject('/api/v1/account'); assert.equal(denied.statusCode, 401)
  const response = await app.inject({ url: '/api/v1/account', headers: auth }); assert.equal(response.statusCode, 200)
  assert.match(response.headers['x-trace-id'], /^[a-f0-9-]{36}$/)
}))

test('backend secrets in otherwise valid user response are rejected', () => usingApp(async () => ok({ user: { ...user, passwordHash: 'synthetic-sensitive-canary' }, recharges: [], analyses: [] }), async app => {
  const response = await app.inject({ url: '/api/v1/account', headers: auth })
  assert.equal(response.statusCode, 502); assert.ok(!response.body.includes('synthetic-sensitive-canary'))
}))

test('maps auth quota and ownership failures without leaking internal messages', async () => {
  for (const status of [401, 402, 403, 409]) await usingApp(async () => ({ status, payload: { code: 'PRIVATE', msg: 'synthetic-internal-canary', data: null } }), async app => {
    const response = await app.inject({ url: '/api/v1/account', headers: auth })
    assert.equal(response.statusCode, status); assert.ok(!response.body.includes('synthetic-internal-canary'))
    assert.deepEqual(Object.keys(response.json()).sort(), ['code', 'data', 'msg'])
  })
})

test('recharge requires integer cents, allowed range, idempotency key and no client price overrides', () => usingApp(() => { throw new Error('must not forward') }, async app => {
  for (const payload of [
    { amountCents: 99, idempotencyKey: id }, { amountCents: 100.5, idempotencyKey: id },
    { amountCents: 1000001, idempotencyKey: id }, { amountCents: 1000, idempotencyKey: 'invalid' },
    { amountCents: 1000, idempotencyKey: id, credits: 1000000 }
  ]) assert.equal((await app.inject({ method: 'POST', url: '/api/v1/recharges', headers: auth, payload })).statusCode, 400)
}))

test('commission settings preserve PUT and reject values outside basis-point range', () => usingApp(async (path, options) => {
  assert.equal(path, '/api/v1/admin/settings'); assert.equal(options.method, 'PUT'); assert.equal(options.body.commissionBps, 1250)
  return ok({ ...settings, commissionBps: 1250 })
}, async app => {
  for (const value of [-1, 10001, 2.5, '1000']) assert.equal((await app.inject({ method: 'PUT', url: '/api/v1/admin/settings', headers: auth, payload: { commissionBps: value } })).statusCode, 400)
  assert.equal((await app.inject({ method: 'PUT', url: '/api/v1/admin/settings', headers: auth, payload: { commissionBps: 1250 } })).statusCode, 200)
}))

test('uploads forward bytes as base64 with target in either multipart order', async () => {
  for (const fieldFirst of [true, false]) await usingApp(async (path, options) => {
    assert.equal(path, '/api/v1/documents/text'); assert.equal(options.token, auth.authorization)
    assert.deepEqual(options.body, { filename: 'synthetic.md', contentBase64: Buffer.from('# Synthetic Java resume').toString('base64'), target: 'resume' })
    return ok({ text: '# Synthetic Java resume', filename: 'synthetic.md', format: 'md', charCount: 23, warnings: [] })
  }, async app => {
    const response = await app.inject({ method: 'POST', url: '/api/v1/documents/text', ...multipart({ fieldFirst }) })
    assert.equal(response.statusCode, 200); assert.equal(response.json().data.format, 'md')
  })
})

test('upload rejects missing login unsupported extension and invalid target', () => usingApp(() => { throw new Error('must not forward') }, async app => {
  const request = multipart(); delete request.headers.authorization
  assert.equal((await app.inject({ method: 'POST', url: '/api/v1/documents/text', ...request })).statusCode, 401)
  for (const options of [{ filename: 'synthetic.exe' }, { target: 'other' }])
    assert.equal((await app.inject({ method: 'POST', url: '/api/v1/documents/text', ...multipart(options) })).statusCode, 400)
}))

test('upload over 2 MiB fails with JSON envelope before domain call', () => usingApp(() => { throw new Error('must not forward') }, async app => {
  const response = await app.inject({ method: 'POST', url: '/api/v1/documents/text', ...multipart({ content: Buffer.alloc(2097153, 'a') }) })
  assert.equal(response.statusCode, 413); assert.equal(response.json().data, null)
}))
