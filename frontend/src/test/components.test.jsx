/**
 * Basic component tests - simple rendering without complex context
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

// Simple test components
const SimpleButton = ({ children, onClick, disabled = false }) => (
  <button onClick={onClick} disabled={disabled}>
    {children}
  </button>
);

const SimpleCard = ({ title, content }) => (
  <div className="card">
    <h3>{title}</h3>
    <p>{content}</p>
  </div>
);

const SimpleList = ({ items }) => (
  <ul>
    {items.map((item, index) => (
      <li key={index}>{item}</li>
    ))}
  </ul>
);

describe('Simple Component Tests', () => {
  it('should render a simple button', () => {
    render(<SimpleButton>Click me</SimpleButton>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('should render a disabled button', () => {
    render(<SimpleButton disabled>Disabled</SimpleButton>);
    const button = screen.getByText('Disabled');
    expect(button).toBeInTheDocument();
    expect(button).toBeDisabled();
  });

  it('should render a simple card', () => {
    render(<SimpleCard title="Test Card" content="This is test content" />);
    expect(screen.getByText('Test Card')).toBeInTheDocument();
    expect(screen.getByText('This is test content')).toBeInTheDocument();
  });

  it('should render a list of items', () => {
    const items = ['Item 1', 'Item 2', 'Item 3'];
    render(<SimpleList items={items} />);
    
    items.forEach(item => {
      expect(screen.getByText(item)).toBeInTheDocument();
    });
  });

  it('should render an empty list', () => {
    render(<SimpleList items={[]} />);
    const list = screen.getByRole('list');
    expect(list).toBeInTheDocument();
    expect(list.children).toHaveLength(0);
  });
});

describe('Component Props Tests', () => {
  it('should handle different button states', () => {
    const { rerender } = render(<SimpleButton>Initial</SimpleButton>);
    expect(screen.getByText('Initial')).toBeInTheDocument();

    rerender(<SimpleButton disabled>Updated</SimpleButton>);
    expect(screen.getByText('Updated')).toBeDisabled();
  });

  it('should handle dynamic content', () => {
    const { rerender } = render(<SimpleCard title="First" content="Content 1" />);
    expect(screen.getByText('First')).toBeInTheDocument();
    expect(screen.getByText('Content 1')).toBeInTheDocument();

    rerender(<SimpleCard title="Second" content="Content 2" />);
    expect(screen.getByText('Second')).toBeInTheDocument();
    expect(screen.getByText('Content 2')).toBeInTheDocument();
  });
});