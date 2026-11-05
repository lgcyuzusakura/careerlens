import { describe, it, expect, vi, afterEach } from 'vitest'
import { validate, countCharacters, api, setSession, sessionToken } from '../src/api.js'

afterEach(()=>{setSession('');vi.unstubAllGlobals()})
it('adds bearer and PUT while preserving JSON envelope',async()=>{
  setSession('synthetic-token')
  const fetch=vi.fn(async()=>new Response(JSON.stringify({code:'OK',msg:'ok',data:{saved:true}}),{headers:{'X-Trace-Id':'synthetic-trace'}}));vi.stubGlobal('fetch',fetch)
  const response=await api('/api/v1/admin/settings',{method:'PUT',body:{commissionBps:1250}})
  expect(fetch.mock.calls[0][1].headers.Authorization).toBe('Bearer synthetic-token');expect(fetch.mock.calls[0][1].method).toBe('PUT');expect(response.traceId).toBe('synthetic-trace')
})
it('uploads FormData without overriding multipart boundary',async()=>{
  const fetch=vi.fn(async()=>new Response(JSON.stringify({code:'OK',msg:'ok',data:{text:'synthetic'}})));vi.stubGlobal('fetch',fetch)
  const body=new FormData();body.append('target','resume');await api('/api/v1/documents/text',{body})
  expect(fetch.mock.calls[0][1].headers['Content-Type']).toBeUndefined();expect(fetch.mock.calls[0][1].body).toBe(body)
})
it('expires session on protected 401 but preserves it on login failure',async()=>{
  setSession('synthetic-token');vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify({code:'AUTH_REQUIRED',msg:'请登录',data:null}),{status:401})))
  await expect(api('/api/v1/auth/login',{body:{}})).rejects.toThrow('请登录');expect(sessionToken()).toBe('synthetic-token')
  await expect(api('/api/v1/account')).rejects.toThrow('请登录');expect(sessionToken()).toBe('')
})
describe('form boundaries', () => {
  it('counts Unicode code points', () => expect(countCharacters('中😀')).toBe(2))
  it('rejects blank and oversized material', () => {
    expect(Object.keys(validate(' ', ' '))).toHaveLength(2)
    expect(validate('a'.repeat(20001), 'Java '.repeat(4))).toHaveProperty('resumeText')
  })
  it('accepts legitimate material at the minimum', () => expect(validate('a'.repeat(20), 'b'.repeat(10))).toEqual({}))
})
