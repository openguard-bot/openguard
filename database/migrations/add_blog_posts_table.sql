-- Migration to add blog_posts table
-- Run this script to add blog post functionality to existing databases

-- Create blog posts table
CREATE TABLE IF NOT EXISTS blog_posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    author_id BIGINT NOT NULL,
    published BOOLEAN DEFAULT false,
    slug VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_blog_posts_author_id ON blog_posts(author_id);
CREATE INDEX IF NOT EXISTS idx_blog_posts_published ON blog_posts(published);
CREATE INDEX IF NOT EXISTS idx_blog_posts_slug ON blog_posts(slug);

-- Create trigger for updated_at column
CREATE TRIGGER update_blog_posts_updated_at 
    BEFORE UPDATE ON blog_posts 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions (replace 'aimod_user' with your actual database user if different)
-- ALTER TABLE blog_posts OWNER TO aimod_user;
-- ALTER SEQUENCE blog_posts_id_seq OWNER TO aimod_user;

COMMENT ON TABLE blog_posts IS 'Blog posts for the website';
COMMENT ON COLUMN blog_posts.slug IS 'URL-friendly identifier for the blog post';
COMMENT ON COLUMN blog_posts.published IS 'Whether the blog post is published and visible to the public';
