import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import WelcomeScreen from './WelcomeScreen'

describe('WelcomeScreen', () => {
  it('renders component', () => {
    const { container } = render(<WelcomeScreen />)
    expect(container.firstChild).toBeTruthy()
  })

  it('shows loading state initially', () => {
    render(<WelcomeScreen />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })
})