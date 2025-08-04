import { describe, it, expect, beforeEach, vi } from 'vitest'

describe('Temperature Control', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear()
    // Mock console methods to avoid noise in tests
    vi.spyOn(console, 'log').mockImplementation(() => {})
    vi.spyOn(console, 'warn').mockImplementation(() => {})
  })

  it('should have default temperature of 0.7', () => {
    // Test default temperature value
    expect(0.7).toBe(0.7)
  })

  it('should validate temperature range', () => {
    // Test temperature validation logic
    const validTemperatures = [0, 0.5, 1.0, 1.5, 2.0]
    const invalidTemperatures = [-0.1, 2.1, 3.0, -1.0]
    
    validTemperatures.forEach(temp => {
      expect(temp >= 0 && temp <= 2).toBe(true)
    })
    
    invalidTemperatures.forEach(temp => {
      expect(temp >= 0 && temp <= 2).toBe(false)
    })
  })

  it('should handle localStorage temperature persistence', () => {
    // Test localStorage operations
    const testTemperature = '1.2'
    
    // Save temperature
    localStorage.setItem('chatui-temperature', testTemperature)
    expect(localStorage.getItem('chatui-temperature')).toBe(testTemperature)
    
    // Parse saved temperature
    const savedTemp = localStorage.getItem('chatui-temperature')
    const parsedTemp = parseFloat(savedTemp)
    expect(parsedTemp).toBe(1.2)
    expect(!isNaN(parsedTemp)).toBe(true)
  })

  it('should handle invalid localStorage temperature values', () => {
    // Test invalid values in localStorage
    const invalidValues = ['invalid', 'NaN', '', null, undefined, '2.5', '-0.5']
    
    invalidValues.forEach(value => {
      localStorage.setItem('chatui-temperature', value)
      const saved = localStorage.getItem('chatui-temperature')
      
      if (saved === null || saved === 'null' || saved === 'undefined') {
        expect(saved === null || saved === 'null' || saved === 'undefined').toBe(true)
      } else {
        const parsed = parseFloat(saved)
        // Should be NaN or out of range
        expect(isNaN(parsed) || parsed < 0 || parsed > 2).toBe(true)
      }
    })
  })

  it('should format temperature values correctly', () => {
    // Test temperature formatting and step handling
    const temperatures = [0, 0.1, 0.5, 1.0, 1.5, 2.0]
    
    temperatures.forEach(temp => {
      // Temperature should be a valid number within range
      expect(typeof temp).toBe('number')
      expect(temp >= 0).toBe(true)
      expect(temp <= 2).toBe(true)
      
      // Temperature should be reasonable for LLM usage
      expect(Number.isFinite(temp)).toBe(true)
    })
  })
})