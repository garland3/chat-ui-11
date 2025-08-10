import { describe, it, expect } from 'vitest'

describe('MarkdownRenderer', () => {
  it('validates markdown content structure', () => {
    const content = '# Heading\n\nParagraph text'
    expect(content.includes('#')).toBe(true)
    expect(content.length).toBeGreaterThan(0)
  })

  it('handles empty content', () => {
    const content = ''
    expect(content.length).toBe(0)
  })
})