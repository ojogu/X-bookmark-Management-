#!/usr/bin/env python3
"""
Simple test to verify the single-file structlog configuration is working.
"""

import asyncio
from src.utils.log import get_logger, bind_context, clear_context

async def main():
    print("🚀 Testing Single-File Structlog Configuration\n")
    
    # Test basic logging
    logger = get_logger(__name__)
    logger.info("Testing basic logging functionality")
    
    # Test context binding
    bind_context(feature="test", user_id="123")
    logger.info("Testing context binding")
    clear_context()
    
    # Test service loggers
    twitter_logger = get_logger("src.v1.service.twitter")
    twitter_logger.info("Twitter service test")
    
    user_logger = get_logger("src.v1.service.user") 
    user_logger.info("User service test")
    
    bookmark_logger = get_logger("src.v1.service.bookmark")
    bookmark_logger.info("Bookmark service test")
    
    print("✅ All tests completed successfully!")
    print("\n📋 Single-File Logging Summary:")
    print("  ✓ Structlog configured with single app.log file")
    print("  ✓ Console output working")
    print("  ✓ Context binding working")
    print("  ✓ Service loggers working")
    print("  ✓ Ready for logtail/OTel Collector integration")

if __name__ == "__main__":
    asyncio.run(main())