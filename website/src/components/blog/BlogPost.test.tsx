import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import BlogPost from './BlogPost'

const post = {
  title: 'Hello',
  content: '<p>content</p>',
  created_at: '2020-01-01T00:00:00Z',
}

global.fetch = vi.fn(() =>
  Promise.resolve({ ok: true, json: () => Promise.resolve(post) })
) as any


describe('BlogPost', () => {
  it('renders post', async () => {
    render(<BlogPost slug="hello" />)
    await waitFor(() => {
      expect(screen.getByText('Hello')).toBeInTheDocument()
      expect(screen.getByText('content')).toBeInTheDocument()
    })
  })
})
