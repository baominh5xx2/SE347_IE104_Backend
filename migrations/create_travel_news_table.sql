-- ============================================
-- Travel News URLs Table Migration
-- Execute this in Supabase SQL Editor
-- ============================================

-- Travel News / Guides URLs Table
CREATE TABLE IF NOT EXISTS travel_news_urls (
    news_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    url VARCHAR(2048) NOT NULL UNIQUE,
    snippet TEXT,
    date DATE,
    last_updated DATE,
    source_type VARCHAR(50) DEFAULT 'news', -- news | guide
    destination VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for travel_news_urls
CREATE INDEX IF NOT EXISTS idx_travel_news_url ON travel_news_urls(url);
CREATE INDEX IF NOT EXISTS idx_travel_news_date ON travel_news_urls(date DESC);
CREATE INDEX IF NOT EXISTS idx_travel_news_source_type ON travel_news_urls(source_type);

-- Add comment for documentation
COMMENT ON TABLE travel_news_urls IS 'Stores travel news and guide URLs collected from Perplexity Search API';
COMMENT ON COLUMN travel_news_urls.source_type IS 'Type of source: news (tin tức) or guide (cẩm nang)';
