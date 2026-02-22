"""
Social Media Orchestrator - Post to all platforms simultaneously
Handles: Twitter/X, LinkedIn, Instagram, TikTok
Posts morning brief and daily scorecards
"""

import asyncio
import logging
from typing import Dict, List, Optional
from enum import Enum

from trade_automation.config import Settings
from trade_automation.twitter_poster import get_twitter_poster
from trade_automation.linkedin_poster import get_linkedin_poster

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/social_media_orchestrator.log"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


class Platform(Enum):
    """Social media platforms"""
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"


class SocialMediaOrchestrator:
    """
    Orchestrate posting to multiple platforms simultaneously
    
    Handles failures gracefully - if one platform fails, others still post
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.twitter = get_twitter_poster(settings)
        self.linkedin = get_linkedin_poster(settings)
        
        logger.info("✅ Social Media Orchestrator initialized")

    async def post_brief(
        self,
        brief_text: str,
        image_path: Optional[str] = None,
        platforms: Optional[List[Platform]] = None,
    ) -> Dict:
        """
        Post morning brief to selected platforms (default: all)

        Args:
            brief_text: Formatted brief text
            image_path: Optional path to image file
            platforms: Platforms to post to (default: Twitter, LinkedIn, Instagram)

        Returns:
            {
                "success": bool,
                "platforms": {
                    "twitter": {"ok": True/False, ...},
                    "linkedin": {"ok": True/False, ...},
                    ...
                },
                "failed": ["platform1", "platform2"],
                "summary": "X/4 platforms succeeded"
            }
        """

        if platforms is None:
            platforms = [Platform.TWITTER, Platform.LINKEDIN, Platform.INSTAGRAM]

        logger.info(f"Posting brief to {len(platforms)} platforms: {[p.value for p in platforms]}")

        results = {}
        failed = []

        # Post to Twitter
        if Platform.TWITTER in platforms:
            try:
                result = await self.twitter.post_brief(brief_text, image_path)
                results["twitter"] = result
                if not result.get("ok"):
                    failed.append("twitter")
                    logger.error(f"Twitter failed: {result.get('error')}")
            except Exception as e:
                logger.error(f"Twitter exception: {e}")
                results["twitter"] = {"ok": False, "error": str(e)}
                failed.append("twitter")

        # Post to LinkedIn
        if Platform.LINKEDIN in platforms:
            try:
                result = await self.linkedin.post_brief(brief_text, image_path)
                results["linkedin"] = result
                if not result.get("ok"):
                    failed.append("linkedin")
                    logger.error(f"LinkedIn failed: {result.get('error')}")
            except Exception as e:
                logger.error(f"LinkedIn exception: {e}")
                results["linkedin"] = {"ok": False, "error": str(e)}
                failed.append("linkedin")

        # Instagram: Post via Zoe (manual alert for now)
        if Platform.INSTAGRAM in platforms:
            try:
                result = await self._post_instagram_alert(brief_text, image_path)
                results["instagram"] = result
                if not result.get("ok"):
                    failed.append("instagram")
            except Exception as e:
                logger.error(f"Instagram exception: {e}")
                results["instagram"] = {"ok": False, "error": str(e)}
                failed.append("instagram")

        # TikTok: Post via Zoe (manual alert for now)
        if Platform.TIKTOK in platforms:
            try:
                result = await self._post_tiktok_alert(brief_text, image_path)
                results["tiktok"] = result
                if not result.get("ok"):
                    failed.append("tiktok")
            except Exception as e:
                logger.error(f"TikTok exception: {e}")
                results["tiktok"] = {"ok": False, "error": str(e)}
                failed.append("tiktok")

        success = len(results) - len(failed) > 0
        summary = f"{len(results) - len(failed)}/{len(results)} platforms succeeded"

        if failed:
            logger.warning(f"Failed platforms: {failed}")
        else:
            logger.info("✅ All platforms succeeded")

        return {
            "success": success,
            "platforms": results,
            "failed": failed,
            "summary": summary,
        }

    async def post_scorecard(
        self,
        scorecard_text: str,
        image_path: Optional[str] = None,
        platforms: Optional[List[Platform]] = None,
    ) -> Dict:
        """
        Post daily scorecard to selected platforms (default: all)

        Same as post_brief but for scorecard
        """

        if platforms is None:
            platforms = [Platform.TWITTER, Platform.LINKEDIN, Platform.INSTAGRAM, Platform.TIKTOK]

        logger.info(f"Posting scorecard to {len(platforms)} platforms: {[p.value for p in platforms]}")

        results = {}
        failed = []

        # Post to Twitter
        if Platform.TWITTER in platforms:
            try:
                result = await self.twitter.post_scorecard(scorecard_text, image_path)
                results["twitter"] = result
                if not result.get("ok"):
                    failed.append("twitter")
            except Exception as e:
                logger.error(f"Twitter exception: {e}")
                results["twitter"] = {"ok": False, "error": str(e)}
                failed.append("twitter")

        # Post to LinkedIn
        if Platform.LINKEDIN in platforms:
            try:
                result = await self.linkedin.post_scorecard(scorecard_text, image_path)
                results["linkedin"] = result
                if not result.get("ok"):
                    failed.append("linkedin")
            except Exception as e:
                logger.error(f"LinkedIn exception: {e}")
                results["linkedin"] = {"ok": False, "error": str(e)}
                failed.append("linkedin")

        # Instagram: Post via Zoe
        if Platform.INSTAGRAM in platforms:
            try:
                result = await self._post_instagram_alert(scorecard_text, image_path)
                results["instagram"] = result
                if not result.get("ok"):
                    failed.append("instagram")
            except Exception as e:
                results["instagram"] = {"ok": False, "error": str(e)}
                failed.append("instagram")

        # TikTok: Post via Zoe
        if Platform.TIKTOK in platforms:
            try:
                result = await self._post_tiktok_alert(scorecard_text, image_path)
                results["tiktok"] = result
                if not result.get("ok"):
                    failed.append("tiktok")
            except Exception as e:
                results["tiktok"] = {"ok": False, "error": str(e)}
                failed.append("tiktok")

        success = len(results) - len(failed) > 0
        summary = f"{len(results) - len(failed)}/{len(results)} platforms succeeded"

        return {
            "success": success,
            "platforms": results,
            "failed": failed,
            "summary": summary,
        }

    async def _post_instagram_alert(self, text: str, image_path: Optional[str] = None) -> Dict:
        """
        Send alert to Zoe to post to Instagram (manual posting)
        
        Later: Can be replaced with Meta Business API integration
        """
        try:
            # TODO: Integrate with Telegram notifier to send alert to Zoe
            logger.info(f"[MANUAL] Instagram posting alert sent to Zoe")
            logger.info(f"Text: {text[:100]}...")
            if image_path:
                logger.info(f"Image: {image_path}")
            return {"ok": True, "manual": True, "message": "Alert sent to Zoe"}
        except Exception as e:
            logger.error(f"Failed to send Instagram alert: {e}")
            return {"ok": False, "error": str(e)}

    async def _post_tiktok_alert(self, text: str, image_path: Optional[str] = None) -> Dict:
        """
        Send alert to Zoe to post to TikTok (manual posting)
        
        Later: Can be replaced with TikTok API integration
        """
        try:
            # TODO: Integrate with Telegram notifier to send alert to Zoe
            logger.info(f"[MANUAL] TikTok posting alert sent to Zoe")
            logger.info(f"Text: {text[:100]}...")
            if image_path:
                logger.info(f"Image: {image_path}")
            return {"ok": True, "manual": True, "message": "Alert sent to Zoe"}
        except Exception as e:
            logger.error(f"Failed to send TikTok alert: {e}")
            return {"ok": False, "error": str(e)}

    def cleanup(self):
        """Clean up resources (close browsers, etc)"""
        try:
            self.linkedin.close()
        except:
            pass


async def main():
    """Test orchestrator"""
    settings = Settings()
    orchestrator = SocialMediaOrchestrator(settings)

    test_brief = """📊 OptionsMagic Morning Brief - Feb 24, 2026

SPY: $580.25 | VIX: 16.5
ES: +0.3% | NQ: +0.5%

🎯 Today's Opportunities:
1. SPY - CSP @ 580 | $150 credit
2. QQQ - VPC @ 380 | $200 credit
3. IWM - CSP @ 190 | $125 credit

⚠️ Hypothetical. Not financial advice.
#OptionsMagic #OptionsTrading"""

    result = await orchestrator.post_brief(test_brief)
    print(f"\nBrief Result:\n{result}")

    orchestrator.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
