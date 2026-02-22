"""
LinkedIn Poster - Post briefs and scorecards to LinkedIn
Uses LinkedIn API or browser automation (Selenium)
Currently uses browser automation for reliability
"""

import asyncio
import logging
from typing import Dict, Optional
from pathlib import Path

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    webdriver = None

from trade_automation.config import Settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/linkedin_poster.log"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


class LinkedInPoster:
    """Post to LinkedIn using browser automation"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.driver = None
        
        if not webdriver:
            logger.warning("Selenium not installed. Install with: poetry add selenium")
            return

        # Don't initialize browser until actually posting
        # This avoids keeping browser open between posts
        logger.info("✅ LinkedIn Poster initialized (browser automation)")

    def _get_driver(self):
        """Lazy-load browser driver"""
        if self.driver is None:
            try:
                # Use Chrome driver
                options = webdriver.ChromeOptions()
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                # Don't set headless for first-time auth
                self.driver = webdriver.Chrome(options=options)
                logger.info("✅ Chrome driver initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Chrome driver: {e}")
                return None
        return self.driver

    async def post_brief(self, brief_text: str, image_path: Optional[str] = None) -> Dict:
        """
        Post morning brief to LinkedIn (company page)

        Note: Requires manual login first or saved session
        
        Args:
            brief_text: Formatted brief text
            image_path: Optional path to image file

        Returns:
            {"ok": True/False, "error": "..." (if failed)}
        """

        driver = self._get_driver()
        if not driver:
            return {"ok": False, "error": "Browser driver not initialized"}

        try:
            logger.info("Opening LinkedIn...")
            driver.get("https://www.linkedin.com")

            # Check if logged in (wait for feed to load)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "feed"))
            )
            logger.info("✅ Logged into LinkedIn")

            # Find "Start a post" button
            start_post_btn = driver.find_element(By.XPATH, "//button[contains(.,'Start a post')]")
            start_post_btn.click()

            # Wait for text area to appear
            text_area = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "ql-editor"))
            )

            # Type message
            text_area.send_keys(brief_text)
            logger.info("✅ Typed message")

            # Upload image if provided
            if image_path and Path(image_path).exists():
                try:
                    # Find media upload button
                    media_btn = driver.find_element(By.XPATH, "//button[@aria-label='Add media']")
                    media_btn.click()

                    # Find file input and upload
                    file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                    file_input.send_keys(str(Path(image_path).absolute()))
                    logger.info("✅ Uploaded image")
                except Exception as e:
                    logger.warning(f"Failed to upload image: {e}")

            # Click Post button
            post_btn = driver.find_element(By.XPATH, "//button[contains(.,'Post')]")
            post_btn.click()

            # Wait for confirmation
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located((By.CLASS_NAME, "artdeco-modal"))
            )
            logger.info("✅ Posted to LinkedIn")
            return {"ok": True}

        except Exception as e:
            logger.error(f"Failed to post to LinkedIn: {e}")
            return {"ok": False, "error": str(e)}

    async def post_scorecard(self, scorecard_text: str, image_path: Optional[str] = None) -> Dict:
        """Post daily scorecard to LinkedIn"""
        return await self.post_brief(scorecard_text, image_path)

    async def post_with_fallback(self, text: str, image_path: Optional[str] = None) -> Dict:
        """Post with fallback error handling"""
        try:
            result = await self.post_brief(text, image_path)
            return result
        except Exception as e:
            logger.error(f"Fatal error posting to LinkedIn: {e}")
            return {"ok": False, "error": str(e), "platform": "linkedin"}

    def close(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None


class LinkedInPosterDryRun:
    """Dry-run version that logs instead of posting"""

    def __init__(self, settings: Settings):
        self.settings = settings
        logger.info("✅ LinkedIn Poster (DRY_RUN mode)")

    async def post_brief(self, brief_text: str, image_path: Optional[str] = None) -> Dict:
        """Log brief instead of posting"""
        logger.info(f"[DRY_RUN] Would post to LinkedIn:\n{brief_text}")
        if image_path:
            logger.info(f"[DRY_RUN] With image: {image_path}")
        return {"ok": True, "dry_run": True}

    async def post_scorecard(self, scorecard_text: str, image_path: Optional[str] = None) -> Dict:
        """Log scorecard instead of posting"""
        logger.info(f"[DRY_RUN] Would post to LinkedIn:\n{scorecard_text}")
        if image_path:
            logger.info(f"[DRY_RUN] With image: {image_path}")
        return {"ok": True, "dry_run": True}

    async def post_with_fallback(self, text: str, image_path: Optional[str] = None) -> Dict:
        """Log with fallback"""
        return await self.post_brief(text, image_path)

    def close(self):
        """No-op for dry-run"""
        pass


def get_linkedin_poster(settings: Settings) -> LinkedInPoster:
    """Factory: return real or dry-run poster based on config"""
    # For now, always use dry-run unless explicitly enabled
    # Can be switched to real posting when credentials are configured
    logger.warning("LinkedIn posting uses browser automation. Using DRY_RUN mode for now.")
    return LinkedInPosterDryRun(settings)


async def main():
    """Test LinkedIn posting"""
    settings = Settings()
    poster = get_linkedin_poster(settings)

    test_brief = """📊 OptionsMagic Morning Brief - Feb 24, 2026

SPY: $580.25 | VIX: 16.5

🎯 Today's Top Trading Opportunities:
1. SPY - Credit Secured Put @ 580
2. QQQ - Vertical Put Credit @ 380  
3. IWM - Credit Secured Put @ 190

⚠️ Hypothetical performance. Not financial advice.

#OptionsMagic #OptionsTrading #StockMarket"""

    result = await poster.post_brief(test_brief)
    print(f"Result: {result}")
    
    poster.close()


if __name__ == "__main__":
    asyncio.run(main())
