import Fastify from 'fastify'
import { z } from 'zod'
import { randomUUID } from 'node:crypto'
import { Agent, request } from 'undici'

const text = (min, max) => z.string().refine(s => {
  const n = Array.from(s.normalize('NFKC').trim()).length
  return n >= min && n <= max && Array.from(s).length <= max
}, `长度须为 ${min}–${max} 个字符。`)
export const inputSchema = z.object({
  resumeText: text(20, 20000), jdText: text(10, 12000),
  options: z.object({ useExternalModel: z.boolean().default(false) }).strict().default({ useExternalModel: false })
}).strict()
const dispatcher = new Agent({ connect: { timeout: 1500 } })
const messages = { 400: '请检查输入内容。', 404: '请求的资源不存在。', 413: '材料过大，请缩短文本。', 415: '请求必须使用 JSON。', 422: '材料无法分析，请调整文本。', 429: '请求过于频繁，请稍后重试。', 502: '分析服务暂不可用，请稍后重试。', 503: '分析服务尚未就绪。', 504: '分析超时，材料已保留。' }
const codes = { 400: 'INVALID_INPUT', 404: 'NOT_FOUND', 413: 'PAYLOAD_TOO_LARGE', 415: 'UNSUPPORTED_MEDIA_TYPE', 422: 'UNANALYZABLE_INPUT', 429: 'RATE_LIMITED', 502: 'UPSTREAM_FAILURE', 503: 'SERVICE_UNAVAILABLE', 504: 'UPSTREAM_TIMEOUT' }

export async function domainCall(path, { body, traceId, baseUrl, timeoutMs = 20000 }) {
  const response = await request(new URL(path, baseUrl), {
    method: body ? 'POST' : 'GET',
    headers: { 'content-type': 'application/json', 'x-trace-id': traceId },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(timeoutMs), headersTimeout: timeoutMs, bodyTimeout: timeoutMs,
    maxRedirections: 0, dispatcher
  })
  const chunks = []; let length = 0
  for await (const chunk of response.body) {
    length += chunk.length
    if (length > 524288) { response.body.destroy(); throw new Error('Invalid upstream size') }
    chunks.push(chunk)
  }
  return { status: response.statusCode, payload: JSON.parse(Buffer.concat(chunks).toString('utf8')) }
}

function validAnalysis(data) {
  return data && data.contractVersion === 'analysis-v1' && ['llm', 'rules', 'degraded'].includes(data.mode)
    && ['requirements', 'matches', 'gaps', 'evidence', 'warnings'].every(k => Array.isArray(data[k]) && data[k].length <= 500)
    && data.score && (data.score.value === null || Number.isInteger(data.score.value) && data.score.value >= 0 && data.score.value <= 100)
    && data.structuredResume && ['education', 'experience', 'projects', 'skills', 'issues'].every(k => Array.isArray(data.structuredResume[k]))
}

export function buildApp({ call = domainCall, domainUrl = process.env.DOMAIN_URL || 'http://domain-api:8080', timeoutMs = 20000, rateLimit = 30 } = {}) {
  const app = Fastify({ bodyLimit: 163840, logger: false, requestTimeout: 23000 })
  const buckets = new Map()
  app.addHook('onRequest', async (req, reply) => {
    req.traceId = randomUUID(); req.started = Date.now()
    reply.header('X-Trace-Id', req.traceId).header('Cache-Control', 'no-store').header('X-Content-Type-Options', 'nosniff')
    if (req.url.startsWith('/api')) {
      const now = Date.now(); const key = req.ip
      const bucket = buckets.get(key)
      if (!bucket || now - bucket.at >= 60000) buckets.set(key, { at: now, count: 1 })
      else if (++bucket.count > rateLimit) return reply.header('Retry-After', '60').code(429).send({ code: codes[429], msg: messages[429], data: null })
      if (buckets.size > 10000) for (const [ip, item] of buckets) if (now - item.at >= 60000) buckets.delete(ip)
    }
  })
  app.addHook('onResponse', async (req, reply) => {
    if (process.env.NODE_ENV !== 'test') console.log(JSON.stringify({ service: 'bff', traceId: req.traceId, path: req.routeOptions.url || 'unknown', status: reply.statusCode, durationMs: Date.now() - req.started }))
  })
  app.setErrorHandler((error, req, reply) => {
    const status = [400, 413, 415, 429].includes(error.statusCode) ? error.statusCode : 502
    reply.code(status).send({ code: codes[status], msg: messages[status], data: null })
  })
  app.setNotFoundHandler((req, reply) => reply.code(404).send({ code: codes[404], msg: messages[404], data: null }))
  app.get('/healthz', async () => ({ status: 'UP' }))
  async function forward(path, req, reply, body, kind) {
    try {
      const response = await call(path, { body, traceId: req.traceId, baseUrl: domainUrl, timeoutMs })
      const payload = response.payload
      if (response.status !== 200) {
        const status = [400, 404, 422, 429, 503, 504].includes(response.status) ? response.status : 502
        return reply.code(status).send({ code: codes[status], msg: messages[status], data: null })
      }
      if (!payload || payload.code !== 'OK' || typeof payload.msg !== 'string' || (kind === 'analysis' ? !validAnalysis(payload.data) : !Array.isArray(payload.data?.items))) throw new Error('Invalid upstream contract')
      return { code: 'OK', msg: payload.msg, data: payload.data }
    } catch (error) {
      const status = ['TimeoutError', 'AbortError'].includes(error.name) || /TIMEOUT/.test(error.code || '') ? 504 : 502
      return reply.code(status).send({ code: codes[status], msg: messages[status], data: null })
    }
  }
  app.get('/readyz', async (req, reply) => {
    try { const r = await call('/actuator/health/readiness', { traceId: req.traceId, baseUrl: domainUrl, timeoutMs: 1500 }); if (r.status !== 200) throw new Error(); return { status: 'UP' } }
    catch { return reply.code(503).send({ status: 'DOWN' }) }
  })
  app.get('/api/v1/job-templates', (req, reply) => forward('/api/v1/job-templates', req, reply, undefined, 'templates'))
  app.post('/api/v1/analyses', (req, reply) => {
    const parsed = inputSchema.safeParse(req.body)
    if (!parsed.success) return reply.code(400).send({ code: codes[400], msg: messages[400], data: { errors: parsed.error.issues.map(x => ({ field: String(x.path[0] || 'body'), msg: x.code === 'unrecognized_keys' ? '包含不支持的字段。' : '字段类型或长度不符合要求。' })) } })
    const { resumeText, jdText, options } = parsed.data
    return forward('/api/v1/matches', req, reply, { resumeText, jdText, options }, 'analysis')
  })
  return app
}
