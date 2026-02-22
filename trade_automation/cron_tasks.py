"""
Cron Task Orchestrators - Scheduled tasks for morning brief and daily scorecard
These run via cron and coordinate all components

Scheduled:
- 9:00 AM ET: Morning brief generator
- 4:00 PM ET: Daily scorecard generator
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict

from trade_automation.config import Settings
from trade_automation.supabase_client import get_supabase_client
from trade_automation.morning_brief_generator import MorningBriefGenerator
from trade_automation.daily_scorecard_generator import DailyScorecardGenerator
from trade_automation.social_media_orchestrator import SocialMediaOrchestrator, Platform

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/cron_tasks.log"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


class MorningBriefCronTask:
    """
    9:00 AM ET - Generate and post morning brief
    
    Flow:
    1. Fetch market data + opportunities
    2. Generate formatted brief + image
    3. Post to Twitter, LinkedIn, Instagram
    4. Log results
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.supabase = get_supabase_client(settings)
        self.brief_generator = MorningBriefGenerator(settings, self.supabase)
        self.orchestrator = SocialMediaOrchestrator(settings)

    async def run(self) -> Dict:
        """Execute morning brief task"""

        task_start = datetime.utcnow()
        logger.info(f"=== MORNING BRIEF CRON TASK START ({task_start}) ===")

        try:
            # 1. Generate brief
            logger.info("Step 1: Generating morning brief...")
            brief_data = await self.brief_generator.generate_brief()
            logger.info(f"✅ Brief generated: {len(brief_data['text'])} chars, image: {brief_data['image_path']}")

            # 2. Post to social media
            logger.info("Step 2: Posting to social media...")
            post_result = await self.orchestrator.post_brief(
                brief_text=brief_data["text"],
                image_path=brief_data["image_path"],
                platforms=[Platform.TWITTER, Platform.LINKEDIN, Platform.INSTAGRAM],
            )
            logger.info(f"✅ Social posting result: {post_result['summary']}")

            # 3. Log results
            duration = (datetime.utcnow() - task_start).total_seconds()
            result = {
                "success": post_result["success"],
                "duration_seconds": duration,
                "brief_data": {
                    "market_data": brief_data.get("market_data"),
                    "opportunities_count": len(brief_data.get("opportunities", [])),
                },
                "social_result": post_result,
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.info(f"=== MORNING BRIEF CRON TASK COMPLETE ({duration}s) ===")
            return result

        except Exception as e:
            logger.error(f"Failed to run morning brief task: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
        finally:
            self.orchestrator.cleanup()


class DailyScorecardCronTask:
    """
    4:00 PM ET - Generate and post daily scorecard
    
    Flow:
    1. Fetch today's closed trades
    2. Calculate performance metrics
    3. Generate formatted scorecard + image
    4. Post to Twitter, LinkedIn, Instagram, TikTok
    5. Log results
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.supabase = get_supabase_client(settings)
        self.scorecard_generator = DailyScorecardGenerator(settings, self.supabase)
        self.orchestrator = SocialMediaOrchestrator(settings)

    async def run(self) -> Dict:
        """Execute daily scorecard task"""

        task_start = datetime.utcnow()
        logger.info(f"=== DAILY SCORECARD CRON TASK START ({task_start}) ===")

        try:
            # 1. Generate scorecard
            logger.info("Step 1: Generating daily scorecard...")
            scorecard_data = await self.scorecard_generator.generate_scorecard()
            logger.info(f"✅ Scorecard generated: {len(scorecard_data['text'])} chars, image: {scorecard_data['image_path']}")

            # 2. Post to social media
            logger.info("Step 2: Posting to social media...")
            post_result = await self.orchestrator.post_scorecard(
                scorecard_text=scorecard_data["text"],
                image_path=scorecard_data["image_path"],
                platforms=[Platform.TWITTER, Platform.LINKEDIN, Platform.INSTAGRAM, Platform.TIKTOK],
            )
            logger.info(f"✅ Social posting result: {post_result['summary']}")

            # 3. Log results
            duration = (datetime.utcnow() - task_start).total_seconds()
            result = {
                "success": post_result["success"],
                "duration_seconds": duration,
                "metrics": scorecard_data.get("metrics"),
                "trades_today": scorecard_data.get("trades_today"),
                "open_positions": scorecard_data.get("open_positions"),
                "social_result": post_result,
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.info(f"=== DAILY SCORECARD CRON TASK COMPLETE ({duration}s) ===")
            return result

        except Exception as e:
            logger.error(f"Failed to run daily scorecard task: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
        finally:
            self.orchestrator.cleanup()


async def run_morning_brief():
    """CLI entry point for morning brief cron job"""
    settings = Settings()
    task = MorningBriefCronTask(settings)
    result = await task.run()
    
    # Exit with status code
    import sys
    sys.exit(0 if result.get("success") else 1)


async def run_daily_scorecard():
    """CLI entry point for daily scorecard cron job"""
    settings = Settings()
    task = DailyScorecardCronTask(settings)
    result = await task.run()
    
    # Exit with status code
    import sys
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "brief":
        asyncio.run(run_morning_brief())
    elif len(sys.argv) > 1 and sys.argv[1] == "scorecard":
        asyncio.run(run_daily_scorecard())
    else:
        print("Usage: python -m trade_automation.cron_tasks [brief|scorecard]")
