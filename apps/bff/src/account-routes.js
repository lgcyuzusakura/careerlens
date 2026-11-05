import { z } from 'zod'

const user = z.object({ id: z.string().uuid(), username: z.string().max(40), role: z.enum(['USER','ADMIN']), credits: z.number().int().nonnegative(), createdAt: z.string().max(40) }).strict()
const order = z.object({ id: z.string().uuid(), userId: z.string().uuid(), username: z.string().max(40).optional(), amountCents: z.number().int().min(100), credits: z.number().int().nonnegative(), commissionBps: z.number().int().min(0).max(10000), feeCents: z.number().int().nonnegative(), status: z.enum(['PENDING','SIMULATED_PAID']), createdAt: z.string().max(40), paidAt: z.string().max(40).nullable() }).strict()
const settings = z.object({ commissionBps: z.number().int().min(0).max(10000), creditsPerYuan: z.literal(10), analysisCost: z.literal(1), paymentMode: z.literal('SIMULATED') }).strict()
const credentials = z.object({ username: z.string().regex(/^[a-zA-Z0-9_]{3,32}$/), password: z.string().min(10).refine(s => Buffer.byteLength(s) <= 72) }).strict()
const account = z.object({ user, recharges: z.array(order).max(200), analyses: z.array(z.object({ id: z.string().uuid(), status: z.enum(['RESERVED','SUCCEEDED','FAILED']), createdAt: z.string().max(40) }).strict()).max(20) }).strict()
export const documentSchema = z.object({ text: z.string().refine(s=>Array.from(s).length<=20000), filename: z.string().max(160), format: z.enum(['txt','md','pdf','docx']), charCount: z.number().int().min(1).max(20000), warnings: z.array(z.string()).max(10) }).strict()

export function registerAccountRoutes(app,forward) {
  function route(method,url,input,output) {
    app.route({method,url,handler:(req,reply)=>{
      if (!['/api/v1/auth/login','/api/v1/auth/register'].includes(url) && !/^Bearer [A-Za-z0-9._-]{1,4090}$/.test(req.headers.authorization || '')) return reply.code(401).send({code:'AUTH_REQUIRED',msg:'请登录后继续。',data:null})
      const body=input?.safeParse(req.body)
      if (body && !body.success) return reply.code(400).send({code:'INVALID_INPUT',msg:'请检查字段类型、范围和必填内容。',data:null})
      const path=req.routeOptions.url.replace(':id',encodeURIComponent(req.params.id || ''))
      return forward(path,req,reply,body?.data,output,method)
    }})
  }
  const auth=z.object({token:z.string().max(4096),expiresAt:z.string().max(40),user}).strict()
  for(const path of ['login','register']) route('POST',`/api/v1/auth/${path}`,credentials,auth)
  for(const path of ['/api/v1/account','/api/v1/auth/me']) route('GET',path,null,account)
  route('POST','/api/v1/recharges',z.object({amountCents:z.number().int().min(100).max(1000000).multipleOf(100),idempotencyKey:z.string().uuid()}).strict(),order)
  route('POST','/api/v1/recharges/:id/simulate-confirm',z.object({}).strict(),order)
  route('GET','/api/v1/admin/overview',null,z.object({users:z.number().int().nonnegative(),availableCredits:z.number().int().nonnegative(),successfulAnalyses:z.number().int().nonnegative(),simulatedRevenueCents:z.number().int().nonnegative(),simulatedFeeCents:z.number().int().nonnegative()}).strict())
  route('GET','/api/v1/admin/users',null,z.object({items:z.array(user).max(200)}).strict())
  route('GET','/api/v1/admin/recharges',null,z.object({items:z.array(order).max(200)}).strict())
  route('GET','/api/v1/admin/settings',null,settings)
  route('PUT','/api/v1/admin/settings',z.object({commissionBps:z.number().int().min(0).max(10000)}).strict(),settings)
  route('POST','/api/v1/admin/users/:id/quota',z.object({delta:z.number().int().min(-1000000).max(1000000).refine(x=>x!==0),reason:z.string().trim().min(1).max(200)}).strict(),user)
}
