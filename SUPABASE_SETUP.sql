-- ============================================
-- SUPABASE SETUP FOR VECTOR EMBEDDINGS
-- ============================================
-- Run these SQL commands in your Supabase SQL Editor
-- Go to: https://supabase.com/dashboard → Your Project → SQL Editor → New Query

-- Step 1: Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Step 2: Create embeddings table (if not exists)
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    chunk_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Step 3: Create indexes for performance
CREATE INDEX IF NOT EXISTS embeddings_embedding_idx 
ON embeddings USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS embeddings_item_id_idx ON embeddings(item_id);

CREATE INDEX IF NOT EXISTS embeddings_user_id_idx ON embeddings(user_id);

CREATE INDEX IF NOT EXISTS embeddings_user_item_idx ON embeddings(user_id, item_id);

-- Step 4: Create the match_embeddings RPC function
CREATE OR REPLACE FUNCTION match_embeddings (
    query_embedding vector(384),
    match_user_id UUID,
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    item_id UUID,
    chunk_id TEXT,
    chunk_index INT,
    content TEXT,
    similarity FLOAT,
    item_title TEXT,
    item_url TEXT,
    item_folders TEXT[],
    item_tags TEXT[]
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.item_id,
        e.chunk_id,
        e.chunk_index,
        e.content,
        ROUND((1 - (e.embedding <=> query_embedding))::numeric, 4)::float AS similarity,
        i.title AS item_title,
        i.url AS item_url,
        i.folders AS item_folders,
        i.tags AS item_tags
    FROM embeddings e
    JOIN items i ON e.item_id = i.id
    WHERE e.user_id = match_user_id
    AND 1 - (e.embedding <=> query_embedding) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Step 5: Enable RLS (Row Level Security) on embeddings table
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view their own embeddings" ON embeddings;
DROP POLICY IF EXISTS "Users can insert their own embeddings" ON embeddings;
DROP POLICY IF EXISTS "Users can delete their own embeddings" ON embeddings;

-- Create policy so users can only see their own embeddings
CREATE POLICY "Users can view their own embeddings"
    ON embeddings
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own embeddings"
    ON embeddings
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own embeddings"
    ON embeddings
    FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================
-- TROUBLESHOOTING
-- ============================================
-- If the function still doesn't work, check:
-- 1. Is pgvector extension enabled? Run: SELECT extname FROM pg_extension WHERE extname = 'vector';
-- 2. Does embeddings table exist? Run: SELECT * FROM embeddings LIMIT 1;
-- 3. Test the function manually: SELECT * FROM match_embeddings(ARRAY[...]::vector, 'user-id-here', 0.7, 5);

-- To verify embeddings are stored:
-- SELECT COUNT(*) FROM embeddings WHERE user_id = 'your-user-id';

-- To check items and their embeddings:
-- SELECT i.id, i.title, COUNT(e.id) as embedding_count 
-- FROM items i
-- LEFT JOIN embeddings e ON i.id = e.item_id
-- GROUP BY i.id, i.title;
