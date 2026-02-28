-- Social Posts Table
-- Tracks all social media posts and their engagement metrics

CREATE TABLE IF NOT EXISTS social_posts (
  post_id TEXT PRIMARY KEY,
  platform TEXT NOT NULL,  -- twitter, linkedin, instagram, tiktok
  content TEXT,            -- Post content (truncated)
  posted_at TIMESTAMP NOT NULL,
  post_type TEXT NOT NULL, -- morning_brief, daily_scorecard
  
  -- Trading info
  trade_count INT DEFAULT 0,
  trades_pnl DECIMAL(10, 2) DEFAULT 0,
  
  -- Engagement metrics
  impressions INT DEFAULT 0,
  clicks INT DEFAULT 0,
  likes INT DEFAULT 0,
  shares INT DEFAULT 0,
  comments INT DEFAULT 0,
  engagement_rate DECIMAL(5, 2) DEFAULT 0,  -- Percentage
  reach INT DEFAULT 0,
  
  -- System fields
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  CONSTRAINT platform_valid CHECK (platform IN ('twitter', 'linkedin', 'instagram', 'tiktok')),
  CONSTRAINT post_type_valid CHECK (post_type IN ('morning_brief', 'daily_scorecard'))
);

-- Indexes for common queries
CREATE INDEX idx_social_posts_date ON social_posts(posted_at DESC);
CREATE INDEX idx_social_posts_platform ON social_posts(platform);
CREATE INDEX idx_social_posts_type ON social_posts(post_type);
CREATE INDEX idx_social_posts_impressions ON social_posts(impressions DESC);

-- View: Daily engagement summary
CREATE OR REPLACE VIEW v_daily_engagement AS
SELECT 
  DATE(posted_at) as date,
  COUNT(*) as posts,
  platform,
  post_type,
  SUM(impressions) as total_impressions,
  SUM(likes + shares + comments + clicks) as total_engagement,
  ROUND(CAST(SUM(likes + shares + comments + clicks) AS DECIMAL) / 
        NULLIF(SUM(impressions), 0) * 100, 2) as engagement_rate,
  SUM(trade_count) as trades,
  SUM(trades_pnl) as total_pnl
FROM social_posts
GROUP BY DATE(posted_at), platform, post_type
ORDER BY date DESC, platform;

-- View: Platform performance
CREATE OR REPLACE VIEW v_platform_performance AS
SELECT 
  platform,
  COUNT(*) as posts,
  SUM(impressions) as total_impressions,
  ROUND(AVG(impressions), 0) as avg_impressions,
  SUM(likes + shares + comments + clicks) as total_engagement,
  ROUND(CAST(SUM(likes + shares + comments + clicks) AS DECIMAL) / 
        NULLIF(SUM(impressions), 0) * 100, 2) as engagement_rate,
  SUM(trade_count) as trades,
  SUM(trades_pnl) as total_pnl
FROM social_posts
GROUP BY platform
ORDER BY total_impressions DESC;

-- View: Content type performance
CREATE OR REPLACE VIEW v_content_performance AS
SELECT 
  post_type,
  COUNT(*) as posts,
  SUM(impressions) as total_impressions,
  ROUND(AVG(impressions), 0) as avg_impressions,
  SUM(likes + shares + comments + clicks) as total_engagement,
  ROUND(CAST(SUM(likes + shares + comments + clicks) AS DECIMAL) / 
        NULLIF(SUM(impressions), 0) * 100, 2) as engagement_rate,
  SUM(trade_count) as trades,
  SUM(trades_pnl) as total_pnl
FROM social_posts
GROUP BY post_type
ORDER BY total_impressions DESC;
