import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'node:http'
import { domainCall } from '../src/app.js'

async function server(handler, check) {
  const http = createServer(handler)
  await new Promise(resolve => http.listen(0, '127.0.0.1', resolve))
  try { await check(`http://127.0.0.1:${http.address().port}`) }
  finally { http.closeAllConnections(); await new Promise(resolve => http.close(resolve)) }
}

test('real HTTP transport propagates trace and whitelist body', () => server((req, res) => {
  assert.equal(req.headers['x-trace-id'], 'synthetic-trace')
  let body = ''; req.on('data', chunk => body += chunk)
  req.on('end', () => { assert.deepEqual(JSON.parse(body), { value: 1 }); res.end('{"code":"OK"}') })
}, async baseUrl => {
  const response = await domainCall('/test', { baseUrl, traceId: 'synthetic-trace', body: { value: 1 } })
  assert.equal(response.status, 200); assert.equal(response.payload.code, 'OK')
}))

test('real HTTP transport cancels a stalled upstream', () => server(() => {}, async baseUrl => {
  await assert.rejects(domainCall('/test', { baseUrl, traceId: 'synthetic-trace', timeoutMs: 50 }), error => error.name === 'TimeoutError' || /TIMEOUT/.test(error.code || ''))
}))

test('real HTTP transport rejects oversized and invalid JSON responses', async () => {
  for (const body of ['x'.repeat(524289), 'not-json']) await server((req, res) => res.end(body), async baseUrl => {
    await assert.rejects(domainCall('/test', { baseUrl, traceId: 'synthetic-trace' }))
  })
})
