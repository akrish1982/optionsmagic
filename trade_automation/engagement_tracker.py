#!/usr/bin/env python3
"""
Engagement Tracker
Monitors social media post performance (impressions, likes, retweets, etc.)
Generates daily engagement reports for OptionsMagic launch

Usage:
  from engagement_tracker import EngagementTracker
  tracker = EngagementTracker(db)
  
  # Track posts
  tracker.log_post(platform="twitter", post_id="...", content="...")
  
  # Get daily report
  report = tracker.get_daily_report(date="2026-03-08")
  print(report)
"""

from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional
import json


@dataclass
class Post:
    """Represents a social media post"""
    post_id: str
    platform: str  # twitter, linkedin, instagram, tiktok
    content: str
    posted_at: datetime
    post_type: str  # morning_brief, daily_scorecard
    trade_count: int = 0
    trades_pnl: float = 0.0
    
    # Metrics (updated later)
    impressions: int = 0
    clicks: int = 0
    likes: int = 0
    shares: int = 0
    comments: int = 0
    engagement_rate: float = 0.0
    reach: int = 0
    
    def calculate_engagement_rate(self):
        """Calculate engagement as % of impressions"""
        total_engagement = self.likes + self.shares + self.comments + self.clicks
        if self.impressions > 0:
            self.engagement_rate = (total_engagement / self.impressions) * 100
        return self.engagement_rate
    
    def to_dict(self):
        """Convert to dictionary for database"""
        return {
            "post_id": self.post_id,
            "platform": self.platform,
            "content": self.content[:500],  # Truncate for storage
            "posted_at": self.posted_at.isoformat(),
            "post_type": self.post_type,
            "trade_count": self.trade_count,
            "trades_pnl": self.trades_pnl,
            "impressions": self.impressions,
            "clicks": self.clicks,
            "likes": self.likes,
            "shares": self.shares,
            "comments": self.comments,
            "engagement_rate": self.calculate_engagement_rate(),
            "reach": self.reach,
        }


class EngagementTracker:
    """Tracks and reports on social media engagement"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.posts: List[Post] = []
        self._load_existing_posts()
    
    def _load_existing_posts(self):
        """Load existing posts from database"""
        try:
            result = self.db.table("social_posts").select("*").execute()
            if result.data:
                for row in result.data:
                    post = Post(
                        post_id=row.get("post_id"),
                        platform=row.get("platform"),
                        content=row.get("content", ""),
                        posted_at=datetime.fromisoformat(row.get("posted_at")),
                        post_type=row.get("post_type"),
                        trade_count=row.get("trade_count", 0),
                        trades_pnl=row.get("trades_pnl", 0.0),
                        impressions=row.get("impressions", 0),
                        clicks=row.get("clicks", 0),
                        likes=row.get("likes", 0),
                        shares=row.get("shares", 0),
                        comments=row.get("comments", 0),
                        engagement_rate=row.get("engagement_rate", 0.0),
                        reach=row.get("reach", 0),
                    )
                    self.posts.append(post)
        except Exception as e:
            print(f"⚠️ Could not load existing posts: {e}")
    
    def log_post(self, platform: str, post_id: str, content: str, 
                 post_type: str, trade_count: int = 0, trades_pnl: float = 0.0):
        """Log a new social media post"""
        
        post = Post(
            post_id=post_id,
            platform=platform,
            content=content,
            posted_at=datetime.now(),
            post_type=post_type,
            trade_count=trade_count,
            trades_pnl=trades_pnl,
        )
        
        self.posts.append(post)
        
        # Save to database
        try:
            self.db.table("social_posts").insert(post.to_dict()).execute()
            print(f"✅ Logged {platform} post: {post_id}")
        except Exception as e:
            print(f"❌ Error logging post: {e}")
        
        return post
    
    def update_post_metrics(self, post_id: str, impressions: int = 0, 
                           clicks: int = 0, likes: int = 0, shares: int = 0, 
                           comments: int = 0, reach: int = 0):
        """Update metrics for a post"""
        
        # Find post in memory
        post = next((p for p in self.posts if p.post_id == post_id), None)
        if not post:
            print(f"❌ Post {post_id} not found")
            return None
        
        # Update metrics
        if impressions > 0:
            post.impressions = impressions
        if clicks > 0:
            post.clicks = clicks
        if likes > 0:
            post.likes = likes
        if shares > 0:
            post.shares = shares
        if comments > 0:
            post.comments = comments
        if reach > 0:
            post.reach = reach
        
        # Calculate engagement rate
        post.calculate_engagement_rate()
        
        # Update database
        try:
            self.db.table("social_posts").update(post.to_dict()).eq("post_id", post_id).execute()
            print(f"✅ Updated metrics for {post_id}")
        except Exception as e:
            print(f"❌ Error updating metrics: {e}")
        
        return post
    
    def get_daily_report(self, date: Optional[str] = None) -> Dict:
        """Get engagement report for a specific date"""
        
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Parse date
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            print(f"❌ Invalid date format: {date}")
            return {}
        
        # Filter posts from this date
        daily_posts = [p for p in self.posts 
                       if p.posted_at.strftime("%Y-%m-%d") == date]
        
        if not daily_posts:
            return {
                "date": date,
                "total_posts": 0,
                "total_impressions": 0,
                "total_engagement": 0,
                "avg_engagement_rate": 0.0,
                "total_trades": 0,
                "total_pnl": 0.0,
                "posts_by_platform": {},
                "posts_by_type": {},
            }
        
        # Calculate aggregates
        total_impressions = sum(p.impressions for p in daily_posts)
        total_engagement = sum(p.likes + p.shares + p.comments + p.clicks 
                              for p in daily_posts)
        avg_engagement_rate = sum(p.engagement_rate for p in daily_posts) / len(daily_posts)
        total_trades = sum(p.trade_count for p in daily_posts)
        total_pnl = sum(p.trades_pnl for p in daily_posts)
        
        # By platform
        platforms = {}
        for post in daily_posts:
            if post.platform not in platforms:
                platforms[post.platform] = {
                    "posts": 0,
                    "impressions": 0,
                    "engagement": 0,
                    "avg_engagement_rate": 0.0,
                }
            platforms[post.platform]["posts"] += 1
            platforms[post.platform]["impressions"] += post.impressions
            platforms[post.platform]["engagement"] += (post.likes + post.shares + 
                                                       post.comments + post.clicks)
        
        # Calculate platform engagement rates
        for platform, data in platforms.items():
            if data["impressions"] > 0:
                data["avg_engagement_rate"] = (data["engagement"] / data["impressions"]) * 100
        
        # By type
        types = {}
        for post in daily_posts:
            if post.post_type not in types:
                types[post.post_type] = {
                    "posts": 0,
                    "impressions": 0,
                    "engagement": 0,
                    "avg_engagement_rate": 0.0,
                }
            types[post.post_type]["posts"] += 1
            types[post.post_type]["impressions"] += post.impressions
            types[post.post_type]["engagement"] += (post.likes + post.shares + 
                                                    post.comments + post.clicks)
        
        # Calculate type engagement rates
        for ptype, data in types.items():
            if data["impressions"] > 0:
                data["avg_engagement_rate"] = (data["engagement"] / data["impressions"]) * 100
        
        return {
            "date": date,
            "total_posts": len(daily_posts),
            "total_impressions": total_impressions,
            "total_engagement": total_engagement,
            "avg_engagement_rate": round(avg_engagement_rate, 2),
            "total_trades": total_trades,
            "total_pnl": total_pnl,
            "posts_by_platform": platforms,
            "posts_by_type": types,
            "posts": [
                {
                    "post_id": p.post_id,
                    "platform": p.platform,
                    "posted_at": p.posted_at.strftime("%H:%M"),
                    "impressions": p.impressions,
                    "engagement": p.likes + p.shares + p.comments + p.clicks,
                    "engagement_rate": round(p.engagement_rate, 2),
                }
                for p in daily_posts
            ]
        }
    
    def get_weekly_report(self, start_date: Optional[str] = None) -> Dict:
        """Get engagement report for past 7 days"""
        
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")
        
        # Get 7 days of data
        reports = []
        total_posts = 0
        total_impressions = 0
        total_engagement = 0
        total_trades = 0
        total_pnl = 0.0
        
        for i in range(7):
            date = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=i)).strftime("%Y-%m-%d")
            report = self.get_daily_report(date)
            
            if report.get("total_posts", 0) > 0:
                reports.append(report)
                total_posts += report["total_posts"]
                total_impressions += report["total_impressions"]
                total_engagement += report["total_engagement"]
                total_trades += report["total_trades"]
                total_pnl += report["total_pnl"]
        
        avg_engagement_rate = (total_engagement / total_impressions * 100) if total_impressions > 0 else 0
        
        return {
            "period": f"{start_date} to {(datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=6)).strftime('%Y-%m-%d')}",
            "days_active": len(reports),
            "total_posts": total_posts,
            "avg_posts_per_day": round(total_posts / 7, 1) if reports else 0,
            "total_impressions": total_impressions,
            "total_engagement": total_engagement,
            "avg_engagement_rate": round(avg_engagement_rate, 2),
            "total_trades": total_trades,
            "total_pnl": total_pnl,
            "avg_pnl_per_day": round(total_pnl / len(reports), 2) if reports else 0,
            "daily_reports": reports,
        }
    
    def format_daily_report(self, report: Dict) -> str:
        """Format daily report as readable text"""
        
        if report.get("total_posts") == 0:
            return f"📊 No posts on {report.get('date')}"
        
        text = f"""
📊 Engagement Report - {report.get('date')}
{'=' * 50}

📈 Overall Performance:
  Total Posts: {report.get('total_posts')}
  Total Impressions: {report.get('total_impressions'):,}
  Total Engagement: {report.get('total_engagement'):,}
  Avg Engagement Rate: {report.get('avg_engagement_rate')}%

💰 Trading Performance:
  Trades Posted: {report.get('total_trades')}
  Total P&L: ${report.get('total_pnl'):+,.2f}

📱 By Platform:
"""
        
        for platform, data in report.get("posts_by_platform", {}).items():
            text += f"""
  {platform.upper()}:
    Posts: {data['posts']}
    Impressions: {data['impressions']:,}
    Engagement Rate: {data['avg_engagement_rate']:.2f}%
"""
        
        text += f"""
🎯 By Content Type:
"""
        
        for ptype, data in report.get("posts_by_type", {}).items():
            text += f"""
  {ptype}:
    Posts: {data['posts']}
    Impressions: {data['impressions']:,}
    Engagement Rate: {data['avg_engagement_rate']:.2f}%
"""
        
        return text
    
    def format_weekly_report(self, report: Dict) -> str:
        """Format weekly report as readable text"""
        
        text = f"""
📈 Weekly Engagement Report
{'=' * 50}
Period: {report.get('period')}

📊 Summary:
  Days Active: {report.get('days_active')}
  Total Posts: {report.get('total_posts')}
  Avg Posts/Day: {report.get('avg_posts_per_day')}
  
📈 Metrics:
  Total Impressions: {report.get('total_impressions'):,}
  Total Engagement: {report.get('total_engagement'):,}
  Avg Engagement Rate: {report.get('avg_engagement_rate')}%
  
💰 Trading:
  Total Trades Posted: {report.get('total_trades')}
  Weekly P&L: ${report.get('total_pnl'):+,.2f}
  Avg P&L/Day: ${report.get('avg_pnl_per_day'):+,.2f}

📋 Daily Breakdown:
"""
        
        for daily in report.get("daily_reports", []):
            text += f"\n  {daily['date']}: {daily['total_posts']} posts, {daily['total_impressions']:,} impressions"
        
        return text


# Example usage
if __name__ == "__main__":
    print("""
    Engagement Tracker - Usage Example
    
    from trade_automation.engagement_tracker import EngagementTracker
    from trade_automation.config import Settings
    from trade_automation.supabase_client import get_supabase_client
    
    settings = Settings()
    db = get_supabase_client(settings)
    tracker = EngagementTracker(db)
    
    # Log a post
    post = tracker.log_post(
        platform="twitter",
        post_id="1234567890",
        content="Morning brief...",
        post_type="morning_brief",
        trade_count=3,
        trades_pnl=125.50
    )
    
    # Update metrics after a few hours
    tracker.update_post_metrics(
        post_id="1234567890",
        impressions=5000,
        clicks=150,
        likes=500,
        shares=100,
        comments=50
    )
    
    # Get daily report
    report = tracker.get_daily_report("2026-03-08")
    print(tracker.format_daily_report(report))
    
    # Get weekly report
    week_report = tracker.get_weekly_report("2026-03-08")
    print(tracker.format_weekly_report(week_report))
    """)
