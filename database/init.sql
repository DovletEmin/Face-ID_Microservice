-- ============================================
-- Face ID Database Initialization
-- ============================================

-- Enable pgvector extension for face embeddings
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Face enrollments table (stores 3D face data)
CREATE TABLE IF NOT EXISTS face_enrollments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    embedding vector(512) NOT NULL,
    depth_signature JSONB NOT NULL DEFAULT '{}',
    quality_score FLOAT NOT NULL DEFAULT 0.0,
    is_primary BOOLEAN DEFAULT FALSE,
    enrolled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Authentication logs
CREATE TABLE IF NOT EXISTS auth_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    success BOOLEAN NOT NULL,
    confidence FLOAT,
    depth_verified BOOLEAN DEFAULT FALSE,
    anti_spoof_score FLOAT,
    ip_address INET,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_face_enrollments_user_id ON face_enrollments(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_logs_user_id ON auth_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_logs_created_at ON auth_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- HNSW index for fast vector similarity search
CREATE INDEX IF NOT EXISTS idx_face_embedding_hnsw 
    ON face_enrollments 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
