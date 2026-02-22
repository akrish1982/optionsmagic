"""
Morning Brief Generator - Daily market analysis + top trading opportunities
Runs at 9:00 AM ET weekdays (before market open at 9:30)
Posts generated brief to Twitter/X, LinkedIn, Instagram
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from decimal import Decimal
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import yfinance as yf

from trade_automation.config import Settings
from trade_automation.supabase_client import get_supabase_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/morning_brief_generator.log"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


class MorningBriefGenerator:
    """Generate daily morning trading brief with market data and opportunities"""

    def __init__(self, settings: Settings, supabase):
        self.settings = settings
        self.supabase = supabase
        self.output_dir = Path("/tmp")

    async def generate_brief(self) -> Dict:
        """
        Generate complete morning brief with market data and opportunities

        Returns:
        {
            "text": "Formatted brief text",
            "image_path": "/tmp/morning_brief_[date].png",
            "market_data": {...},
            "opportunities": [...],
            "timestamp": "2026-02-24T09:00:00Z"
        }
        """

        try:
            logger.info("Generating morning brief...")

            # 1. Fetch market data
            market_data = await self._fetch_market_data()
            logger.info(f"Market data: SPY ${market_data['spy_open']}, VIX {market_data['vix_level']}")

            # 2. Fetch economic events (placeholder for external API)
            economic_events = await self._fetch_economic_events()
            logger.info(f"Found {len(economic_events)} economic events")

            # 3. Fetch top 3 trading opportunities
            opportunities = await self._fetch_top_opportunities()
            logger.info(f"Found {len(opportunities)} trading opportunities")

            # 4. Format brief text
            brief_text = self._format_brief(market_data, economic_events, opportunities)

            # 5. Generate image card
            image_path = await self._generate_image(market_data, opportunities)
            logger.info(f"Generated image: {image_path}")

            result = {
                "text": brief_text,
                "image_path": image_path,
                "market_data": market_data,
                "opportunities": opportunities,
                "economic_events": economic_events,
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.info("Morning brief generated successfully")
            return result

        except Exception as e:
            logger.error(f"Failed to generate morning brief: {e}", exc_info=True)
            raise

    async def _fetch_market_data(self) -> Dict:
        """Fetch SPY, VIX, and overnight futures data"""

        try:
            # Fetch SPY data
            spy = yf.download("SPY", period="1d", progress=False)
            spy_open = float(spy['Open'].iloc[-1])

            # Fetch VIX data
            vix = yf.download("^VIX", period="1d", progress=False)
            vix_level = float(vix['Close'].iloc[-1])

            # Fetch overnight futures (ES, NQ)
            es = yf.download("ES=F", period="1d", progress=False)
            nq = yf.download("NQ=F", period="1d", progress=False)

            es_change = ((es['Close'].iloc[-1] - es['Open'].iloc[-1]) / es['Open'].iloc[-1]) * 100
            nq_change = ((nq['Close'].iloc[-1] - nq['Open'].iloc[-1]) / nq['Open'].iloc[-1]) * 100

            return {
                "spy_open": round(spy_open, 2),
                "vix_level": round(vix_level, 2),
                "es_change_percent": round(float(es_change), 2),
                "nq_change_percent": round(float(nq_change), 2),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to fetch market data: {e}")
            # Return placeholder data
            return {
                "spy_open": 0.0,
                "vix_level": 0.0,
                "es_change_percent": 0.0,
                "nq_change_percent": 0.0,
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def _fetch_economic_events(self) -> List[Dict]:
        """
        Fetch today's economic calendar events

        TODO: Integrate with external API:
        - Alpha Vantage (free tier: 5 calls/min)
        - Yahoo Finance economic calendar
        - Or maintain local CSV of key events
        """

        # Placeholder: return empty list for now
        # Will be implemented with external API
        return []

    async def _fetch_top_opportunities(self) -> List[Dict]:
        """Fetch top 3 trading opportunities from database"""

        try:
            response = self.supabase.table("options_opportunities").select(
                "ticker,strategy_type,strike_price,delta,net_credit,expiry_date,collateral_required"
            ).order("net_credit", desc=True).limit(3).execute()

            opportunities = []
            for opp in response.data:
                opportunities.append({
                    "ticker": opp.get("ticker"),
                    "strategy": opp.get("strategy_type"),
                    "strike": float(opp.get("strike_price", 0)),
                    "delta": float(opp.get("delta", 0)),
                    "credit": float(opp.get("net_credit", 0)),
                    "collateral": float(opp.get("collateral_required", 0)),
                    "expiry": opp.get("expiry_date"),
                })

            return opportunities

        except Exception as e:
            logger.error(f"Failed to fetch opportunities: {e}")
            return []

    def _format_brief(self, market_data: Dict, events: List[Dict], opportunities: List[Dict]) -> str:
        """Format morning brief as text"""

        date = datetime.now().strftime("%B %d, %Y")

        brief = f"""📊 OptionsMagic Morning Brief - {date}

🎯 Market Open
SPY: ${market_data['spy_open']} | VIX: {market_data['vix_level']}
ES: {market_data['es_change_percent']:+.2f}% | NQ: {market_data['nq_change_percent']:+.2f}%
"""

        if events:
            brief += "\n📅 Economic Events Today:\n"
            for evt in events:
                brief += f"  • {evt.get('time')} - {evt.get('name')} ({evt.get('impact')})\n"

        if opportunities:
            brief += "\n🎯 Today's Top Opportunities:\n"
            for i, opp in enumerate(opportunities, 1):
                brief += f"  {i}. ${opp['ticker']} - {opp['strategy']} @ ${opp['strike']}\n"
                brief += f"     Delta: {opp['delta']:.2f} | Credit: ${opp['credit']:.2f}\n"

        brief += "\n⚠️ Hypothetical performance. Not financial advice.\n"
        brief += "#OptionsMagic #OptionsTrading #StockMarket"

        return brief

    async def _generate_image(self, market_data: Dict, opportunities: List[Dict]) -> str:
        """Generate branded image card for morning brief"""

        try:
            # Image dimensions
            width, height = 1200, 675
            bg_color = (15, 23, 42)  # Dark blue-gray
            accent_color = (34, 197, 94)  # Green
            text_color = (255, 255, 255)  # White

            img = Image.new("RGB", (width, height), bg_color)
            draw = ImageDraw.Draw(img)

            # Try to load fonts, fall back to default
            try:
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
                header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
                body_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
            except:
                title_font = header_font = body_font = small_font = ImageFont.load_default()

            # Title
            draw.text((40, 30), "OptionsMagic Morning Brief", fill=accent_color, font=title_font)

            # Market data
            market_text = f"SPY ${market_data['spy_open']} | VIX {market_data['vix_level']}"
            draw.text((40, 100), market_text, fill=text_color, font=header_font)

            # Futures
            futures_text = f"ES {market_data['es_change_percent']:+.2f}% | NQ {market_data['nq_change_percent']:+.2f}%"
            draw.text((40, 150), futures_text, fill=text_color, font=body_font)

            # Opportunities
            y_pos = 230
            for i, opp in enumerate(opportunities):
                opp_header = f"{i + 1}. ${opp['ticker']} - {opp['strategy']} @ ${opp['strike']}"
                draw.text((40, y_pos), opp_header, fill=accent_color, font=body_font)

                opp_details = f"Delta: {opp['delta']:.2f} | Credit: ${opp['credit']:.2f}"
                draw.text((60, y_pos + 40), opp_details, fill=text_color, font=small_font)

                y_pos += 100

            # Disclaimer
            disclaimer = "⚠️ Hypothetical performance. Not financial advice."
            draw.text((40, height - 60), disclaimer, fill=(255, 100, 100), font=small_font)

            # Save image
            date_str = datetime.now().strftime("%Y-%m-%d")
            image_path = self.output_dir / f"morning_brief_{date_str}.png"
            img.save(str(image_path))

            return str(image_path)

        except Exception as e:
            logger.error(f"Failed to generate image: {e}", exc_info=True)
            raise


async def main():
    """Run morning brief generator standalone"""
    settings = Settings()
    supabase = get_supabase_client(settings)

    generator = MorningBriefGenerator(settings, supabase)
    brief = await generator.generate_brief()

    logger.info("Morning brief:")
    logger.info(brief["text"])
    logger.info(f"Image saved to: {brief['image_path']}")


if __name__ == "__main__":
    asyncio.run(main())
