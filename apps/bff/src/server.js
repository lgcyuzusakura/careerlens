import { buildApp } from './app.js'
const app = buildApp()
await app.listen({ port: Number(process.env.PORT || 8081), host: '0.0.0.0' })
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, async () => { await app.close(); process.exit(0) })
