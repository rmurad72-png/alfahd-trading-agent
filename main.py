"""
🐆 الفهد — نقطة الدخول الرئيسية
"""
import asyncio
import logging
import sys
from datetime import datetime, timezone  # ← هنا (قبل الـ import المفتوح)

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from config.settings import settings
from security.vault import init_vault
from core.engine import engine
from handlers import (
    cmd_start, cmd_help, cmd_wallet, cmd_execute,
    cmd_vtrades, cmd_live, cmd_upgrade, cmd_premium,
    cmd_risk, cmd_killswitch, cmd_autotrade, cmd_admin,
    handle_callback, error_handler
)

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


async def post_init(app: Application):
    """تهيئة المحرك قبل بدء البوت"""
    logger.info("🐆 تهيئة الفهد...")
    try:
        init_vault(settings.MASTER_KEY, settings.VAULT_SALT)
        await engine.init()
        logger.info("✅ الفهد جاهز!")
    except Exception as e:
        logger.error(f"Init error: {e}")
        logger.warning("⚠️ البوت يعمل بدون قاعدة بيانات — بعض الميزات قد لا تعمل")


def main():
    """الدالة الرئيسية"""
    application = (
        Application.builder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Error Handler (Bitget Skill: error recovery)
    application.add_error_handler(error_handler)

    # Commands
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("wallet", cmd_wallet))
    application.add_handler(CommandHandler("execute", cmd_execute))
    application.add_handler(CommandHandler("vtrades", cmd_vtrades))
    application.add_handler(CommandHandler("live", cmd_live))
    application.add_handler(CommandHandler("upgrade", cmd_upgrade))
    application.add_handler(CommandHandler("premium", cmd_premium))
    application.add_handler(CommandHandler("risk", cmd_risk))
    application.add_handler(CommandHandler("killswitch", cmd_killswitch))
    application.add_handler(CommandHandler("autotrade", cmd_autotrade))
    application.add_handler(CommandHandler("admin", cmd_admin))
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Run
    logger.info("🐆 الفهد يعمل الآن!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
