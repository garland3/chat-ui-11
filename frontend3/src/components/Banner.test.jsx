import { describe, it, expect, beforeAll, afterAll, vi } from 'vitest'
import { render } from '@testing-library/react'
import Banner from './Banner'

describe('Banner', () => {
  beforeAll(() => {
    // Mock fetch to avoid "Failed to parse URL from /api/banners" error
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ messages: ['Test banner message'] }),
      })
    );
  });

  afterAll(() => {
    global.fetch.mockClear();
    delete global.fetch;
  });

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