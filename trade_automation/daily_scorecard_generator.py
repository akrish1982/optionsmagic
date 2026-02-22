"""
Daily Scorecard Generator - End-of-day P&L and performance report
Runs at 4:00 PM ET weekdays (after market close at 4:00 PM)
Posts scorecard to Twitter/X, LinkedIn, Instagram
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from decimal import Decimal
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from trade_automation.config import Settings
from trade_automation.supabase_client import get_supabase_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/daily_scorecard_generator.log"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


class DailyScorecardGenerator:
    """Generate daily trading scorecard with P&L and performance metrics"""

    def __init__(self, settings: Settings, supabase):
        self.settings = settings
        self.supabase = supabase
        self.output_dir = Path("/tmp")

    async def generate_scorecard(self, date: Optional[datetime] = None) -> Dict:
        """
        Generate complete daily scorecard with P&L and metrics

        Args:
            date: Date to generate scorecard for (default: today)

        Returns:
        {
            "text": "Formatted scorecard text",
            "image_path": "/tmp/daily_scorecard_[date].png",
            "metrics": {...},
            "timestamp": "2026-02-24T16:00:00Z"
        }
        """

        if date is None:
            date = datetime.now()

        try:
            logger.info(f"Generating daily scorecard for {date.date()}...")

            # 1. Fetch today's closed trades
            today_trades = await self._fetch_today_trades(date)
            logger.info(f"Found {len(today_trades)} closed trades")

            # 2. Calculate metrics
            metrics = self._calculate_metrics(today_trades, date)
            logger.info(f"Metrics: {len(today_trades)} trades, {metrics['win_rate']:.1f}% win rate, "
                       f"P&L ${metrics['total_pnl']:+.2f}")

            # 3. Fetch period performance (week, month)
            period_metrics = await self._fetch_period_metrics(date)

            # 4. Fetch open positions
            open_positions = await self._fetch_open_positions()
            logger.info(f"Open positions: {len(open_positions)}, "
                       f"Unrealized P&L ${metrics['unrealized_pnl']:+.2f}")

            # 5. Format scorecard text
            scorecard_text = self._format_scorecard(metrics, period_metrics, open_positions)

            # 6. Generate image card
            image_path = await self._generate_image(metrics)
            logger.info(f"Generated image: {image_path}")

            result = {
                "text": scorecard_text,
                "image_path": image_path,
                "metrics": metrics,
                "period_metrics": period_metrics,
                "trades_today": len(today_trades),
                "open_positions": len(open_positions),
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.info("Daily scorecard generated successfully")
            return result

        except Exception as e:
            logger.error(f"Failed to generate scorecard: {e}", exc_info=True)
            raise

    async def _fetch_today_trades(self, date: datetime) -> List[Dict]:
        """Fetch all closed trades for a given day"""

        try:
            start_of_day = datetime.combine(date.date(), datetime.min.time()).isoformat()
            end_of_day = (date.replace(hour=23, minute=59, second=59)).isoformat()

            response = self.supabase.table("trade_history").select("*").gte(
                "closed_at", start_of_day
            ).lte(
                "closed_at", end_of_day
            ).eq(
                "status", "CLOSED"
            ).execute()

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Failed to fetch today's trades: {e}")
            return []

    async def _fetch_open_positions(self) -> List[Dict]:
        """Fetch all currently open positions"""

        try:
            response = self.supabase.table("positions").select("*").eq(
                "status", "OPEN"
            ).execute()

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Failed to fetch open positions: {e}")
            return []

    def _calculate_metrics(self, trades: List[Dict], date: datetime) -> Dict:
        """Calculate performance metrics from trades"""

        if not trades:
            return {
                "trades_today": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "avg_pnl": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
                "unrealized_pnl": 0.0,
            }

        pnl_values = [float(t.get("pnl_realized", 0)) for t in trades]
        wins = sum(1 for pnl in pnl_values if pnl > 0)
        losses = len(pnl_values) - wins
        total_pnl = sum(pnl_values)
        avg_pnl = total_pnl / len(trades) if trades else 0

        return {
            "trades_today": len(trades),
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / len(trades) * 100) if trades else 0.0,
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(avg_pnl, 2),
            "largest_win": round(max(pnl_values), 2) if pnl_values else 0.0,
            "largest_loss": round(min(pnl_values), 2) if pnl_values else 0.0,
            "unrealized_pnl": 0.0,  # Will be calculated from open positions
        }

    async def _fetch_period_metrics(self, date: datetime) -> Dict:
        """Fetch performance metrics for week and month"""

        try:
            # Week to date (Monday-Today)
            start_of_week = date - timedelta(days=date.weekday())
            week_data = self.supabase.table("trade_history").select("*").gte(
                "closed_at", start_of_week.isoformat()
            ).lte(
                "closed_at", date.isoformat()
            ).eq(
                "status", "CLOSED"
            ).execute()

            # Month to date
            start_of_month = date.replace(day=1)
            month_data = self.supabase.table("trade_history").select("*").gte(
                "closed_at", start_of_month.isoformat()
            ).lte(
                "closed_at", date.isoformat()
            ).eq(
                "status", "CLOSED"
            ).execute()

            week_trades = week_data.data if week_data.data else []
            month_trades = month_data.data if month_data.data else []

            week_pnl = sum(float(t.get("pnl_realized", 0)) for t in week_trades)
            month_pnl = sum(float(t.get("pnl_realized", 0)) for t in month_trades)

            return {
                "week_trades": len(week_trades),
                "week_pnl": round(week_pnl, 2),
                "month_trades": len(month_trades),
                "month_pnl": round(month_pnl, 2),
            }

        except Exception as e:
            logger.error(f"Failed to fetch period metrics: {e}")
            return {
                "week_trades": 0,
                "week_pnl": 0.0,
                "month_trades": 0,
                "month_pnl": 0.0,
            }

    def _format_scorecard(self, metrics: Dict, period: Dict, positions: List[Dict]) -> str:
        """Format scorecard as text"""

        date = datetime.now().strftime("%B %d, %Y")

        # Determine emoji based on P&L
        pnl_emoji = "📈" if metrics["total_pnl"] > 0 else "📉" if metrics["total_pnl"] < 0 else "➡️"

        scorecard = f"""{pnl_emoji} OptionsMagic Daily Scorecard - {date}

💰 Today's Results
Trades: {metrics['trades_today']} ({metrics['wins']} W / {metrics['losses']} L)
Win Rate: {metrics['win_rate']:.1f}%
P&L: ${metrics['total_pnl']:+,.2f}
Avg Per Trade: ${metrics['avg_pnl']:+,.2f}
"""

        if metrics["trades_today"] > 0:
            scorecard += f"Best Trade: ${metrics['largest_win']:+,.2f}\n"
            scorecard += f"Worst Trade: ${metrics['largest_loss']:+,.2f}\n"

        scorecard += f"""
📊 Position Summary
Open Positions: {len(positions)}
Unrealized P&L: ${metrics['unrealized_pnl']:+,.2f}

📈 Period Performance
Week to Date: {period['week_trades']} trades, ${period['week_pnl']:+,.2f}
Month to Date: {period['month_trades']} trades, ${period['month_pnl']:+,.2f}

⚠️ Hypothetical performance. Not financial advice.
#OptionsMagic #OptionsTrading
"""

        return scorecard

    async def _generate_image(self, metrics: Dict) -> str:
        """Generate branded P&L visual card"""

        try:
            # Image dimensions
            width, height = 1200, 675
            bg_color = (15, 23, 42)  # Dark blue-gray
            text_color = (255, 255, 255)  # White

            # Choose color based on P&L
            if metrics["total_pnl"] > 0:
                accent_color = (34, 197, 94)  # Green
                pnl_color = (34, 197, 94)
            elif metrics["total_pnl"] < 0:
                accent_color = (239, 68, 68)  # Red
                pnl_color = (239, 68, 68)
            else:
                accent_color = (156, 163, 175)  # Gray
                pnl_color = (156, 163, 175)

            img = Image.new("RGB", (width, height), bg_color)
            draw = ImageDraw.Draw(img)

            # Try to load fonts
            try:
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
                huge_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 96)
                header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
                body_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
            except:
                title_font = header_font = huge_font = body_font = small_font = ImageFont.load_default()

            # Title
            draw.text((40, 30), "Daily Trading Scorecard", fill=accent_color, font=title_font)

            # Main P&L (large)
            pnl_text = f"${metrics['total_pnl']:+,.0f}"
            draw.text((40, 120), pnl_text, fill=pnl_color, font=huge_font)

            # Metrics
            y_pos = 280
            draw.text((40, y_pos), f"Trades: {metrics['trades_today']}", fill=text_color, font=body_font)
            y_pos += 50
            draw.text((40, y_pos), f"Win Rate: {metrics['win_rate']:.1f}%", fill=text_color, font=body_font)
            y_pos += 50
            draw.text((40, y_pos), f"Avg P&L: ${metrics['avg_pnl']:+,.2f}", fill=text_color, font=body_font)

            # Disclaimer
            disclaimer = "⚠️ Hypothetical performance. Not financial advice."
            draw.text((40, height - 60), disclaimer, fill=(255, 100, 100), font=small_font)

            # Save image
            date_str = datetime.now().strftime("%Y-%m-%d")
            image_path = self.output_dir / f"daily_scorecard_{date_str}.png"
            img.save(str(image_path))

            return str(image_path)

        except Exception as e:
            logger.error(f"Failed to generate image: {e}", exc_info=True)
            raise


async def main():
    """Run daily scorecard generator standalone"""
    settings = Settings()
    supabase = get_supabase_client(settings)

    generator = DailyScorecardGenerator(settings, supabase)
    scorecard = await generator.generate_scorecard()

    logger.info("Daily scorecard:")
    logger.info(scorecard["text"])
    logger.info(f"Image saved to: {scorecard['image_path']}")


if __name__ == "__main__":
    asyncio.run(main())
