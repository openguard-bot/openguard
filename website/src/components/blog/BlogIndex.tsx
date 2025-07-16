import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card.tsx';

interface Post {
    slug: string;
    title: string;
    excerpt: string;
}

const BlogIndex: React.FC = () => {
    const [posts, setPosts] = useState<Post[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchPosts = async () => {
            try {
                const response = await fetch('https://openguard.lol/api/blog/posts?published_only=true');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                setPosts(data.posts);
            } catch (e: any) {
                setError(e.message);
            } finally {
                setLoading(false);
            }
        };

        fetchPosts();
    }, []);

    if (loading) {
        return <p>Loading blog posts...</p>;
    }

    if (error) {
        return <p className="text-red-500">Error loading blog posts: {error}</p>;
    }

    return (
        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
            {posts.map((post) => (
                <a href={`/blog/${post.slug}`} key={post.slug}>
                    <Card>
                        <CardHeader>
                            <CardTitle>{post.title}</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <p>{post.excerpt}</p>
                        </CardContent>
                    </Card>
                </a>
            ))}
        </div>
    );
};

export default BlogIndex;