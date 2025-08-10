import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import Banner from './Banner'

describe('Banner', () => {
  it('renders component', () => {
    const { container } = render(<Banner />)
    expect(container).toBeTruthy()
  })

  it('accepts banner prop', () => {
    const mockBanner = {
      id: 1,
      message: 'Test banner message',
      type: 'info'
    }
    const { container } = render(<Banner banner={mockBanner} />)
    expect(container).toBeTruthy()
  })
})