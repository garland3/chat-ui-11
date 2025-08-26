import { describe, it, expect } from 'vitest'

function toSelectedToolMap(selectedToolsSet) {
  return Array.from(selectedToolsSet).reduce((acc, fqn) => {
    const idx = fqn.indexOf('_')
    if (idx > 0) {
      const server = fqn.slice(0, idx)
      const tool = fqn.slice(idx + 1)
      if (!acc[server]) acc[server] = []
      acc[server].push(tool)
    }
    return acc
  }, {})
}

describe('toSelectedToolMap', () => {
  it('converts set of fqns to server->tools map', () => {
    const set = new Set(['calculator_evaluate', 'filesystem_list', 'filesystem_read'])
    const map = toSelectedToolMap(set)
    expect(map).toEqual({
      calculator: ['evaluate'],
      filesystem: ['list', 'read']
    })
  })

  it('ignores malformed keys without underscore', () => {
    const set = new Set(['badkey', 'calculator_eval'])
    const map = toSelectedToolMap(set)
    expect(map).toEqual({ calculator: ['eval'] })
  })
})
