export async function api(path, { body, signal } = {}) {
  const response = await fetch(path, { method: body ? 'POST' : 'GET', headers: body ? { 'Content-Type': 'application/json' } : {}, body: body ? JSON.stringify(body) : undefined, signal })
  const traceId = response.headers.get('X-Trace-Id') || ''
  let payload
  try { payload = await response.json() } catch { throw Object.assign(new Error('服务返回了无效响应，请稍后重试。'), { traceId }) }
  if (!response.ok || payload.code !== 'OK') throw Object.assign(new Error(payload.msg || '分析暂不可用，请稍后重试。'), { traceId, fields: payload.data?.errors })
  return { data: payload.data, traceId }
}
export const countCharacters = value => Array.from(value).length
export function validate(resume, jd) {
  const errors = {}
  for (const [key, value, min, max] of [['resumeText', resume, 20, 20000], ['jdText', jd, 10, 12000]]) {
    const size = countCharacters(value.normalize('NFKC').trim())
    if (size < min || size > max) errors[key] = `请输入 ${min}–${max} 个字符。`
  }
  return errors
}
