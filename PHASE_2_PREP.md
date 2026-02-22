# Phase 2 Preparation Guide - Morning Brief & Daily Scorecard Generators

**Target Launch:** March 8, 2026  
**Preparation Start:** February 22, 2026 (This Weekend)  
**Status:** Design Phase - Ready to Code After SIM Validation (Feb 24-28)

---

## 📊 Phase 2 Overview

### What Gets Built
1. **Morning Brief Generator** (runs 9:00 AM ET, weekdays)
   - Fetches market data + top 3 trading opportunities
   - Generates formatted brief + image card
   - Posts to Twitter/X, LinkedIn, Instagram

2. **Daily Scorecard Generator** (runs 4:00 PM ET, weekdays)
   - Fetches closed trades from database
   - Calculates P&L, win rate, metrics
   - Generates visual P&L card
   - Posts to social media

### Success Metrics
- **60+ social posts** (2 per day × 30 days)
- **500+ follower growth** (via consistent, quality posts)
- **Live performance tracking** (real-time P&L visible)

---

## 🎯 Architecture

```
┌─────────────────────────────────────────────────┐
│ SIM TESTING WEEK (Feb 24-28)                     │
│ Generate sample trade data for Phase 2            │
│ - Open 2-3 positions per day                      │
│ - Close some at profit target, some at stop loss  │
│ - Collect 5 days of realistic P&L data           │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│ PHASE 2 PREP (Mar 1-7)                           │
│ - Build Morning Brief Generator                   │
│ - Build Daily Scorecard Generator               │
│ - Setup Pillow image templates                   │
│ - Verify social media credentials                │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│ PHASE 2 LAUNCH (Mar 8+)                          │
│ - Run 9 AM: Morning Brief (proposal + market)   │
│ - Run 4 PM: Daily Scorecard (P&L + stats)       │
│ - Post to 4 platforms (Twitter/LinkedIn/IG/TikTok)
│ - Repeat daily weekdays                          │
└─────────────────────────────────────────────────┘
```

---

## 💻 Component 1: Morning Brief Generator

### File: `trade_automation/morning_brief_generator.py`

**Runs:** Daily at 9:00 AM ET (before market open at 9:30)

**Input:**
```python
{
  "market_data": {
    "spy_open": 580.25,
    "vix_level": 16.5,
    "overnight_futures": {
      "es_change_percent": 0.3,
      "nq_change_percent": 0.5
    }
  },
  "economic_events": [
    {"time": "10:00 AM", "event": "Initial Jobless Claims", "impact": "Medium"}
  ],
  "top_opportunities": [
    {
      "ticker": "SPY",
      "strategy": "CSP",
      "strike": 580,
      "delta": 0.16,
      "credit": 150,
      "expiry": "2026-03-07"
    },
    # ... 2 more
  ]
}
```

**Output:**
```
📊 OptionsMagic Morning Brief - Feb 24, 2026

Market Open: SPY $580.25, VIX 16.5
Overnight Movement: ES +0.3%, NQ +0.5%

📅 Economic Events:
  • 10:00 AM - Initial Jobless Claims (Medium Impact)

🎯 Today's Top Opportunities:
  1. $SPY - CSP @ 580 | Delta 0.16 | Credit $150
  2. $QQQ - VPC @ 380 | Width $5 | Credit $200
  3. $IWM - CSP @ 190 | Delta 0.18 | Credit $125

⚠️ Hypothetical performance. Not financial advice.
#OptionsMagic #OptionsTrading

[Attached: morning_brief_image.png with visual card]
```

**Database Queries:**
```python
# 1. Fetch top 3 opportunities from database
opportunities = supabase.table("options_opportunities")\
  .select("ticker,strategy_type,strike,delta,net_credit,expiry_date")\
  .order("net_credit", desc=True)\
  .limit(3)\
  .execute()

# 2. Fetch economic calendar (integrate with external API or store locally)
# Options:
#   - Alpha Vantage API (free tier available)
#   - Yahoo Finance (basic economic calendar)
#   - Manual CSV import for key events

# 3. Fetch market data (SPY, VIX, futures)
#   - yfinance: spy_data = yf.download("SPY", period="1d")
#   - VIX from yfinance: vix_data = yf.download("^VIX", period="1d")
#   - ES futures: es_data = yf.download("ES=F", period="1d")
```

**Image Generation (Pillow):**
```python
from PIL import Image, ImageDraw, ImageFont

def generate_morning_brief_image(opportunities, market_data):
    """Create branded morning brief card"""
    
    # Image settings
    width, height = 1200, 675
    bg_color = (15, 23, 42)  # Dark blue-gray
    accent_color = (34, 197, 94)  # Green
    text_color = (255, 255, 255)  # White
    
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Add title
    title = "OptionsMagic Morning Brief"
    draw.text((40, 30), title, fill=accent_color, font=bold_font)
    
    # Add market data
    market_text = f"SPY ${market_data['spy_open']} | VIX {market_data['vix_level']}"
    draw.text((40, 100), market_text, fill=text_color, font=regular_font)
    
    # Add top 3 opportunities
    for i, opp in enumerate(opportunities):
        y_pos = 170 + (i * 120)
        opp_text = f"{opp['ticker']} - {opp['strategy']} @ ${opp['strike']} | ${opp['credit']}"
        draw.text((40, y_pos), opp_text, fill=accent_color, font=bold_font)
    
    # Add disclaimer
    disclaimer = "⚠️ Hypothetical performance. Not financial advice."
    draw.text((40, height - 60), disclaimer, fill=(255, 100, 100), font=small_font)
    
    # Save
    img.save("/tmp/morning_brief.png")
    return "/tmp/morning_brief.png"
```

**Integration with Cron:**
```bash
# Add to crontab (Mon-Fri 9:00 AM ET)
0 9 * * 1-5 cd /workspace && poetry run python -m trade_automation.morning_brief_generator
```

---

## 📈 Component 2: Daily Scorecard Generator

### File: `trade_automation/daily_scorecard_generator.py`

**Runs:** Daily at 4:00 PM ET (after market close)

**Input (from database):**
```python
# Query closed trades for today
today_trades = supabase.table("trade_history")\
  .select("*")\
  .gte("closed_at", today_start)\
  .lte("closed_at", today_end)\
  .execute()

# Calculate metrics
metrics = {
  "trades_today": len(today_trades),
  "wins": sum(1 for t in today_trades if t['pnl_realized'] > 0),
  "losses": len(today_trades) - sum(1 for t in today_trades if t['pnl_realized'] > 0),
  "total_pnl": sum(t['pnl_realized'] for t in today_trades),
  "avg_pnl": sum(t['pnl_realized'] for t in today_trades) / len(today_trades),
  "win_rate": (wins / total) * 100
}
```

**Output:**
```
📈 OptionsMagic Daily Scorecard - Feb 24, 2026

Today's Results:
  Trades: 3
  Wins: 2 | Losses: 1
  Win Rate: 66.7%

💰 P&L Summary:
  Realized P&L: +$425.00
  Unrealized P&L: +$180.00
  Total: +$605.00

📊 Open Positions: 2

📈 This Week: +$1,890 (4 trades, 75% win rate)
📅 This Month: +$2,340 (12 trades, 72% win rate)

⚠️ Hypothetical performance. Not financial advice.
#OptionsMagic #OptionsTrading

[Attached: scorecard_image.png with P&L card]
```

**Image Generation (Pillow):**
```python
def generate_scorecard_image(metrics, pnl_data):
    """Create daily P&L visual card"""
    
    img = Image.new("RGB", (1200, 675), (15, 23, 42))
    draw = ImageDraw.Draw(img)
    
    # Title
    draw.text((40, 30), "Daily Trading Scorecard", fill=(34, 197, 94), font=bold_font)
    
    # P&L box (green if positive, red if negative)
    pnl_color = (34, 197, 94) if metrics['total_pnl'] > 0 else (239, 68, 68)
    pnl_text = f"${metrics['total_pnl']:+.2f}"
    draw.text((40, 100), pnl_text, fill=pnl_color, font=huge_font)
    
    # Metrics grid
    draw.text((40, 200), f"Trades: {metrics['trades_today']}", fill=(255,255,255), font=regular_font)
    draw.text((40, 250), f"Win Rate: {metrics['win_rate']:.1f}%", fill=(255,255,255), font=regular_font)
    draw.text((40, 300), f"Avg P&L: ${metrics['avg_pnl']:+.2f}", fill=(255,255,255), font=regular_font)
    
    # Mini chart (optional)
    # Draw cumulative P&L chart for the week
    
    img.save("/tmp/daily_scorecard.png")
    return "/tmp/daily_scorecard.png"
```

**Integration with Cron:**
```bash
# Add to crontab (Mon-Fri 4:00 PM ET)
0 16 * * 1-5 cd /workspace && poetry run python -m trade_automation.daily_scorecard_generator
```

---

## 🔄 Social Media Publishing Integration

### Twitter/X Integration

**File:** `trade_automation/twitter_publisher.py`

```python
import tweepy

def post_to_twitter(brief_or_scorecard, image_path):
    """Post to Twitter/X with image"""
    
    auth = tweepy.OAuthHandler(API_KEY, API_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth)
    
    # Upload image
    media = api.media_upload(image_path)
    
    # Post tweet with image
    api.update_status(
        status=brief_or_scorecard,
        media_ids=[media.media_id]
    )
```

**Integration:**
- Post Morning Brief at 9:30 AM ET (after brief generation at 9:00)
- Post Daily Scorecard at 4:30 PM ET (after scorecard generation at 4:00)

### LinkedIn Integration

**Option 1: Browser Automation (Simpler)**
```python
from selenium import webdriver

def post_to_linkedin(text, image_path):
    """Post to LinkedIn using browser automation"""
    driver = webdriver.Chrome()
    driver.get("https://www.linkedin.com")
    # Login and post
```

**Option 2: LinkedIn API (Requires OAuth)**
- Requires company page access
- More reliable long-term

### Instagram & TikTok

**Option 1: Manual Alerts to Zoe**
- Generate image card
- Send message to Zoe via Telegram
- Zoe posts manually

**Option 2: Meta Business API (Future)**
- Instagram via Meta Business API
- TikTok has limited API access

---

## 📋 Database Schema Extensions

### View: `v_morning_brief_data`
```sql
CREATE VIEW v_morning_brief_data AS
SELECT
  ticker,
  strategy_type,
  strike_price,
  delta,
  net_credit,
  expiry_date,
  days_to_expiry,
  collateral_required
FROM options_opportunities
WHERE
  status = 'ready'
  AND net_credit > 50  -- Minimum credit threshold
ORDER BY net_credit DESC
LIMIT 3;
```

### View: `v_daily_performance`
```sql
CREATE VIEW v_daily_performance AS
SELECT
  DATE(closed_at) as trade_date,
  COUNT(*) as trades_count,
  SUM(CASE WHEN pnl_realized > 0 THEN 1 ELSE 0 END) as wins,
  SUM(CASE WHEN pnl_realized <= 0 THEN 1 ELSE 0 END) as losses,
  ROUND(100.0 * SUM(CASE WHEN pnl_realized > 0 THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate,
  ROUND(SUM(pnl_realized), 2) as total_pnl,
  ROUND(AVG(pnl_realized), 2) as avg_pnl
FROM trade_history
WHERE status IN ('CLOSED', 'EXPIRED')
GROUP BY DATE(closed_at)
ORDER BY DATE(closed_at) DESC;
```

---

## 🛠️ Technology Stack

### Libraries Needed
```toml
[tool.poetry.dependencies]
pillow = "^10.0.0"  # Image generation
tweepy = "^4.14.0"  # Twitter API
linkedin-api = "^2.0.0"  # LinkedIn (optional)
selenium = "^4.10.0"  # Browser automation (optional)
yfinance = "^0.2.30"  # Market data (already have)
```

### External APIs
- **Twitter/X API v2** - Zoe to provide credentials
- **LinkedIn API** - Zoe to provide company page access
- **Alpha Vantage** - Economic calendar (free tier: 5 calls/min)
- **Yahoo Finance** - Market data (free, via yfinance)

---

## 📅 Implementation Timeline

### Week of Feb 24-28 (SIM Testing)
- [ ] Generate 5+ days of realistic trade data
- [ ] Collect sample P&L data
- [ ] Test database queries for brief/scorecard

### Week of Mar 1-7 (Phase 2 Prep)
- [ ] Build Morning Brief Generator (3 days)
- [ ] Build Daily Scorecard Generator (2 days)
- [ ] Design Pillow image templates (2 days)
- [ ] Get social media API credentials from Zoe
- [ ] Test posting to all 4 platforms (1 day)

### Week of Mar 8+ (Phase 2 Launch)
- [ ] Enable cron jobs (9 AM + 4 PM)
- [ ] Monitor first week of postings
- [ ] Fix any formatting/timing issues
- [ ] Scale to all 4 platforms

---

## 🔍 Testing Checklist

### Before Going Live (Mar 8)

- [ ] **Morning Brief Tests**
  - [ ] Correctly fetches top 3 opportunities
  - [ ] Market data correct (SPY, VIX, futures)
  - [ ] Image generates without errors
  - [ ] Twitter post succeeds
  - [ ] LinkedIn post succeeds
  - [ ] Instagram post succeeds

- [ ] **Daily Scorecard Tests**
  - [ ] Correctly counts trades for today
  - [ ] P&L calculations accurate
  - [ ] Win rate calculation correct
  - [ ] Image displays P&L correctly
  - [ ] Color changes based on profit/loss
  - [ ] Posts to all platforms

- [ ] **Database Tests**
  - [ ] Views return correct data
  - [ ] No NULL values in results
  - [ ] Performance is fast (<1 sec)

- [ ] **Schedule Tests**
  - [ ] Cron jobs run at correct times
  - [ ] No duplicate posts
  - [ ] Handles weekends/holidays correctly

---

## 📝 Success Criteria

### By March 21 (End of Phase 2)
- [ ] 20+ social posts published (2/day × 10 days)
- [ ] 100+ combined followers across platforms
- [ ] 0 broken posts (100% success rate)
- [ ] <2% engagement rate baseline established
- [ ] Ready for Phase 3 (API integrations)

### By April 30 (End of SIM Testing)
- [ ] 60+ social posts published
- [ ] 500+ follower growth
- [ ] >3% engagement rate
- [ ] Live performance data accessible to followers
- [ ] Ready for LIVE trading announcement

---

## 🚀 Next Steps (This Weekend)

### For You (Max) - Sunday Morning Tasks
1. [ ] Review this document
2. [ ] Create skeleton files for generators
3. [ ] Set up Pillow template files
4. [ ] Make database view queries

### For Ananth - Before Mar 8
1. [ ] Provide Twitter/X API credentials to Zoe
2. [ ] Provide LinkedIn credentials to Zoe
3. [ ] Approve image template designs
4. [ ] Approve disclaimer language

### For Zoe - Before Mar 1
1. [ ] Provide social media API credentials
2. [ ] Design image templates (branded cards)
3. [ ] Review posting schedule (9:30 AM + 4:30 PM)

---

## 💡 Design Notes

### Branding
- **Colors:** Dark blue (#0f172a), Green (#22c55e), White (#ffffff)
- **Font:** Use system fonts (Helvetica, Arial for cross-platform)
- **Logo:** OptionsMagic logo in corner of each card
- **Watermark:** Always include "Hypothetical performance. Not financial advice."

### Tone
- Professional but approachable
- Data-driven (show numbers, not hype)
- Transparent about performance
- Educate followers on strategies being used

### Disclaimers
- Every post must include: "Hypothetical performance. Not financial advice."
- Link to detailed risk disclosure on website (Spider will build)
- Consider adding: "Not a recommendation to trade" on each post

---

## 📞 Dependencies

### Blocking Items (Need Before Mar 8)
1. ✅ Phase 1 code complete (DONE)
2. ✅ Database schema ready (DONE)
3. ⏳ SIM testing data collected (Feb 24-28)
4. ⏳ Social media API credentials (Zoe to provide)
5. ⏳ Image template designs (Zoe to design)

### Non-Blocking (Can Iterate)
1. Twitter API integration (built, tested)
2. LinkedIn posting (can be manual initially)
3. Instagram/TikTok (can post manually via Zoe)

---

## 🎬 Ready to Build

Once SIM testing confirms that trades are executing correctly, Phase 2 is straightforward:
1. Pull data from database (queries ready)
2. Format text (templates above)
3. Generate images (Pillow)
4. Post to social (APIs ready)

All components are small, testable, and can be built independently.

---

**Next Review:** After SIM validation (Feb 28)  
**Status:** Ready to code Mar 1-7  
**Launch:** Mar 8, 2026

