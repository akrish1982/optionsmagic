"""
Twitter/X Poster - Post briefs and scorecards to Twitter/X
Uses Twitter API v2 (requires: TWITTER_API_KEY, TWITTER_API_SECRET, etc.)
"""

import asyncio
import logging
from typing import Dict, Optional
from pathlib import Path

try:
    import tweepy
except ImportError:
    tweepy = None

from trade_automation.config import Settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/twitter_poster.log"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


class TwitterPoster:
    """Post to Twitter/X with images"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = None
        self.auth = None
        
        if not tweepy:
            logger.warning("tweepy not installed. Install with: poetry add tweepy")
            return
        
        # Initialize Twitter API v2 client
        try:
            self.client = tweepy.Client(
                bearer_token=settings.twitter_bearer_token,
                consumer_key=settings.twitter_api_key,
                consumer_secret=settings.twitter_api_secret,
                access_token=settings.twitter_access_token,
                access_token_secret=settings.twitter_access_token_secret,
            )
            logger.info("✅ Twitter API v2 client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter client: {e}")
            self.client = None

    async def post_brief(self, brief_text: str, image_path: Optional[str] = None) -> Dict:
        """
        Post morning brief to Twitter/X

        Args:
            brief_text: Formatted brief text
            image_path: Optional path to image file

        Returns:
            {
                "ok": True/False,
                "tweet_id": "...",
                "error": "..." (if failed)
            }
        """

        if not self.client:
            logger.error("Twitter client not initialized")
            return {"ok": False, "error": "Client not initialized"}

        try:
            # Upload media if image provided
            media_id = None
            if image_path and Path(image_path).exists():
                try:
                    # Use v1.1 API for media upload (v2 doesn't support yet)
                    # For now, we'll just post text (v2 media support coming)
                    logger.info(f"Image path provided: {image_path}")
                    # TODO: Implement media upload when tweepy v2 media support available
                except Exception as e:
                    logger.warning(f"Failed to upload image: {e}")

            # Post tweet
            response = self.client.create_tweet(
                text=brief_text,
                # TODO: Add media_ids=[media_id] when v2 media upload available
            )

            if response and response.data:
                tweet_id = response.data["id"]
                logger.info(f"✅ Posted to Twitter: {tweet_id}")
                return {"ok": True, "tweet_id": tweet_id}
            else:
                logger.error("No response from Twitter API")
                return {"ok": False, "error": "No response from API"}

        except Exception as e:
            logger.error(f"Failed to post brief: {e}")
            return {"ok": False, "error": str(e)}

    async def post_scorecard(self, scorecard_text: str, image_path: Optional[str] = None) -> Dict:
        """
        Post daily scorecard to Twitter/X

        Args:
            scorecard_text: Formatted scorecard text
            image_path: Optional path to scorecard image

        Returns:
            {"ok": True/False, "tweet_id": "...", "error": "..."}
        """

        return await self.post_brief(scorecard_text, image_path)

    async def post_with_fallback(self, text: str, image_path: Optional[str] = None) -> Dict:
        """
        Post to Twitter with fallback error handling

        If Twitter API fails, log error and continue (don't break pipeline)
        """

        try:
            result = await self.post_brief(text, image_path)
            return result
        except Exception as e:
            logger.error(f"Fatal error posting to Twitter: {e}")
            # Return error but don't raise (let other platforms post)
            return {"ok": False, "error": str(e), "platform": "twitter"}


class TwitterPosterDryRun:
    """Dry-run version that logs instead of posting"""

    def __init__(self, settings: Settings):
        self.settings = settings
        logger.info("✅ Twitter Poster (DRY_RUN mode)")

    async def post_brief(self, brief_text: str, image_path: Optional[str] = None) -> Dict:
        """Log brief instead of posting"""
        logger.info(f"[DRY_RUN] Would post to Twitter:\n{brief_text}")
        if image_path:
            logger.info(f"[DRY_RUN] With image: {image_path}")
        return {"ok": True, "dry_run": True}

    async def post_scorecard(self, scorecard_text: str, image_path: Optional[str] = None) -> Dict:
        """Log scorecard instead of posting"""
        logger.info(f"[DRY_RUN] Would post to Twitter:\n{scorecard_text}")
        if image_path:
            logger.info(f"[DRY_RUN] With image: {image_path}")
        return {"ok": True, "dry_run": True}

    async def post_with_fallback(self, text: str, image_path: Optional[str] = None) -> Dict:
        """Log with fallback"""
        return await self.post_brief(text, image_path)


def get_twitter_poster(settings: Settings) -> TwitterPoster:
    """Factory: return real or dry-run poster based on config"""
    if settings.twitter_api_key and settings.twitter_api_secret:
        return TwitterPoster(settings)
    else:
        logger.warning("Twitter credentials not configured. Using DRY_RUN mode.")
        return TwitterPosterDryRun(settings)


async def main():
    """Test Twitter posting"""
    settings = Settings()
    poster = get_twitter_poster(settings)

    test_brief = """📊 OptionsMagic Morning Brief - Feb 24, 2026

SPY: $580.25 | VIX: 16.5
ES: +0.3% | NQ: +0.5%

🎯 Top Opportunities:
1. SPY - CSP @ 580 | $150 credit
2. QQQ - VPC @ 380 | $200 credit  
3. IWM - CSP @ 190 | $125 credit

⚠️ Hypothetical. Not financial advice.
#OptionsMagic #OptionsTrading"""

    result = await poster.post_brief(test_brief)
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
