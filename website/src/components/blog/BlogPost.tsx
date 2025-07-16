import React, { useEffect, useState } from 'react';
import { format } from 'date-fns';
import { Badge } from '@/components/ui/badge.tsx';

interface Post {
    title: string;
    content: string;
    created_at: string;
    tags?: string[];
}

interface BlogPostProps {
    slug: string;
}

const BlogPost: React.FC<BlogPostProps> = ({ slug }) => {
    const [post, setPost] = useState<Post | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchPost = async () => {
            try {
                const response = await fetch(`https://openguard.lol/api/blog/posts/slug/${slug}`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                setPost(data);
            } catch (e: any) {
                setError(e.message);
            } finally {
                setLoading(false);
            }
        };

        fetchPost();
    }, [slug]);

    if (loading) {
        return <p>Loading blog post...</p>;
    }

    if (error) {
        return <p className="text-red-500">Error loading blog post: {error}</p>;
    }

    if (!post) {
        return <p>Blog post not found.</p>;
    }

    return (
        <article className="prose dark:prose-invert max-w-none">
            <h1 className="mb-2">{post.title}</h1>
            <div className="mb-4 flex items-center gap-4 text-sm text-muted-foreground">
                <span>{format(new Date(post.created_at), 'MMMM d, yyyy')}</span>
                {post.tags && post.tags.length > 0 && post.tags.map((tag: string) => (
                    <Badge variant="secondary" key={tag}>{tag}</Badge>
                ))}
            </div>
            <div className="mt-8" dangerouslySetInnerHTML={{ __html: post.content }} />
        </article>
    );
};

export default BlogPost;