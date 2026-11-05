import { mkdirSync, writeFileSync } from 'node:fs'
import { z } from 'zod'
import { inputSchema } from '../apps/bff/src/app.js'
import { analysisSchema } from '../apps/bff/src/response-schema.js'

// Normalized Unicode bounds remain runtime refinements in addition to this structural schema.
mkdirSync('contracts', { recursive: true })
for (const [name, schema] of [['analysis-v1', analysisSchema], ['analysis-input-v1', inputSchema]]) {
  const contract = z.toJSONSchema(schema, { unrepresentable: 'any', io: name === 'analysis-input-v1' ? 'input' : 'output' })
  if (name === 'analysis-input-v1') {
    Object.assign(contract.properties.resumeText, { minLength: 20, maxLength: 20000 })
    Object.assign(contract.properties.jdText, { minLength: 10, maxLength: 12000 })
  }
  writeFileSync(`contracts/${name}.schema.json`, JSON.stringify(contract, null, 2) + '\n')
}
