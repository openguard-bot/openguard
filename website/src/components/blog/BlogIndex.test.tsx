import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import BlogIndex from './BlogIndex'

const posts = [
  { slug: 'a', title: 'A', excerpt: 'a' },
  { slug: 'b', title: 'B', excerpt: 'b' },
]

global.fetch = vi.fn(() =>
  Promise.resolve({ ok: true, json: () => Promise.resolve({ posts }) })
) as any


describe('BlogIndex', () => {
  it('renders posts from API', async () => {
    render(<BlogIndex />)
    await waitFor(() => {
      expect(screen.getByText('A')).toBeInTheDocument()
      expect(screen.getByText('B')).toBeInTheDocument()
    })
  })
})
