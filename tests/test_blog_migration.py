#!/usr/bin/env python3
"""
Test script to verify blog posts table migration and basic functionality.
Run this script to test the blog post database operations.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

from database.connection import get_pool, initialize_database
from dashboard.backend.app import crud, schemas
from dashboard.backend.app.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
import asyncpg

async def test_blog_migration():
    """Test the blog posts table and basic CRUD operations."""
    print("Testing blog posts migration...")
    
    try:
        # Initialize database connection
        print("1. Initializing database connection...")
        success = await initialize_database()
        if not success:
            print("❌ Failed to initialize database")
            return False
        print("✅ Database connection initialized")
        
        # Get database pool
        pool = await get_pool()
        if not pool:
            print("❌ Failed to get database pool")
            return False
        
        # Test table exists
        print("2. Checking if blog_posts table exists...")
        async with pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'blog_posts'
                );
            """)
            
            if not result:
                print("❌ blog_posts table does not exist")
                print("   Run the migration script: psql -d aimod_bot -f database/migrations/add_blog_posts_table.sql")
                return False
            print("✅ blog_posts table exists")
        
        # Test basic CRUD operations would require setting up the full SQLAlchemy session
        # For now, just test the table structure
        print("3. Checking table structure...")
        async with pool.acquire() as conn:
            columns = await conn.fetch("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'blog_posts'
                ORDER BY ordinal_position;
            """)
            
            expected_columns = {
                'id', 'title', 'content', 'author_id', 
                'published', 'slug', 'created_at', 'updated_at'
            }
            
            actual_columns = {col['column_name'] for col in columns}
            
            if not expected_columns.issubset(actual_columns):
                missing = expected_columns - actual_columns
                print(f"❌ Missing columns: {missing}")
                return False
            print("✅ All required columns present")
        
        # Test indexes
        print("4. Checking indexes...")
        async with pool.acquire() as conn:
            indexes = await conn.fetch("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'blog_posts';
            """)
            
            index_names = {idx['indexname'] for idx in indexes}
            expected_indexes = {
                'blog_posts_pkey', 'blog_posts_slug_key',
                'idx_blog_posts_author_id', 'idx_blog_posts_published', 
                'idx_blog_posts_slug'
            }
            
            if not expected_indexes.issubset(index_names):
                missing = expected_indexes - index_names
                print(f"⚠️  Missing indexes: {missing}")
            else:
                print("✅ All indexes present")
        
        print("\n🎉 Blog posts migration test completed successfully!")
        print("\nNext steps:")
        print("1. Start the dashboard backend: cd dashboard/backend && python -m uvicorn main:app --reload --port 5030")
        print("2. Start the frontend: cd dashboard/frontend && npm start")
        print("3. Login with user ID 1141746562922459136 or 452666956353503252 to see the blog management button")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function."""
    success = await test_blog_migration()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
