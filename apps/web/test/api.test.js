import { describe, it, expect } from 'vitest'
import { validate, countCharacters } from '../src/api.js'
describe('form boundaries', () => {
  it('counts Unicode code points', () => expect(countCharacters('中😀')).toBe(2))
  it('rejects blank and oversized material', () => {
    expect(Object.keys(validate(' ', ' '))).toHaveLength(2)
    expect(validate('a'.repeat(20001), 'Java '.repeat(4))).toHaveProperty('resumeText')
  })
  it('accepts legitimate material at the minimum', () => expect(validate('a'.repeat(20), 'b'.repeat(10))).toEqual({}))
})
