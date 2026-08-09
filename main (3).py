"""
🐆 الفهد — نقطة الدخول الرئيسية
"""
import asyncio
import logging
import sys

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from config.settings import settings
from security.vault import init_vault
from core.engine import engine

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء البوت"""
    user_id = update.effective_user.id
    username = update.effective_user.username or ""
    full_name = update.effective_user.full_name or ""

    try:
        user = await engine.get_or_create_user(
            user_id, username=username, full_name=full_name
        )

        tier_name = {
            "free": "🆓 مجاني",
            "silver": "🥈 فضي",
            "gold": "🥇 ذهبي",
            "diamond": "💎 ماسي",
            "admin": "👑 مدير"
        }.get(user.tier, "🆓 مجاني")

        msg = (
            f"🐆 *أهلاً بك في الفهد!*

"
            f"وكيلك الذكي للتداول
"
            f"باقتك: {tier_name}

"
            f"📋 *الأوامر:*
"
            f"• /wallet — محفظتك
"
            f"• /execute — صفقة فورية
"
            f"• /vtrades — صفقاتك
"
            f"• /live — ربط منصة
"
            f"• /upgrade — الباقات
"
            f"• /help — المساعدة"
        )
    except Exception as e:
        logger.error(f"Start error: {e}")
        msg = (
            f"🐆 *أهلاً بك في الفهد!*

"
            f"وكيلك الذكي للتداول

"
            f"📋 *الأوامر:*
"
            f"• /wallet — محفظتك
"
            f"• /execute — صفقة فورية
"
            f"• /vtrades — صفقاتك
"
            f"• /live — ربط منصة
"
            f"• /upgrade — الباقات
"
            f"• /help — المساعدة"
        )

    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """المساعدة"""
    msg = (
        "🐆 *الفهد — دليل الاستخدام*

"
        "📊 *التداول:*
"
        "`/execute BTC buy 500` — شراء
"
        "`/execute ETH sell 300` — بيع

"
        "💼 *المحفظة:*
"
        "`/wallet` — الرصيد
"
        "`/vtrades` — الصفقات

"
        "⚙️ *الإعدادات:*
"
        "`/live connect okx KEY SECRET`
"
        "`/live off` — فصل المنصة

"
        "💎 *الباقات:*
"
        "`/upgrade` — عرض الباقات"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض المحفظة"""
    user_id = update.effective_user.id
    try:
        summary = await engine.get_portfolio_summary(user_id)

        if "error" in summary:
            await update.message.reply_text("❌ خطأ في جلب البيانات")
            return

        msg = (
            f"💼 *محفظتك — الفهد*
"
            f"━━━━━━━━━━━━━━━━━━
"
            f"💵 رصيد: ${summary['balance']:,.2f}
"
            f"📊 مستثمر: ${summary['invested']:,.2f}
"
            f"💰 إجمالي: ${summary['total_value']:,.2f}
"
            f"📈 صافي الربح: ${summary['total_pnl']:+,.2f}
"
            f"🎯 مراكز: {summary['open_positions']}
"
            f"💎 باقة: {summary['tier']}"
        )

        if summary.get('risk_alerts'):
            msg += "

⚠️ *تنبيهات:*
" + "
".join(summary['risk_alerts'])
    except Exception as e:
        logger.error(f"Wallet error: {e}")
        msg = "❌ خطأ في جلب البيانات — جرب لاحقاً"

    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنفيذ صفقة"""
    user_id = update.effective_user.id
    args = context.args or []

    if len(args) < 3:
        await update.message.reply_text(
            "⚡ *الاستخدام:*
"
            "`/execute BTC buy 500`
"
            "`/execute ETH sell 300`

"
            "_buy = شراء | sell = بيع_",
            parse_mode="Markdown"
        )
        return

    symbol = args[0].upper()
    direction = args[1].lower()

    if direction not in ("buy", "sell", "شراء", "بيع"):
        await update.message.reply_text("❌ الاتجاه: buy أو sell")
        return

    if direction in ("شراء",):
        direction = "buy"
    elif direction in ("بيع",):
        direction = "sell"

    try:
        amount = float(args[2])
    except ValueError:
        await update.message.reply_text("❌ المبلغ غير صحيح")
        return

    if amount < 1 or amount > 1000000:
        await update.message.reply_text("❌ المبلغ يجب أن يكون بين $1 و $1,000,000")
        return

    msg = await update.message.reply_text(f"🔍 جاري تقييم {symbol}...")

    try:
        result = await engine.execute_virtual(user_id, symbol, direction, amount)

        if result.get("ok"):
            risk = result.get("risk", {})
            resp = (
                f"✅ *تم التنفيذ!*

"
                f"🪙 {symbol} | {'🟢 شراء' if direction=='buy' else '🔴 بيع'}
"
                f"💰 الحجم: ${amount:,.2f}
"
            )
            if risk:
                resp += (
                    f"🛑 وقف الخسارة: {risk.get('sl_pct', 5)}%
"
                    f"🎯 هدف الربح: {risk.get('tp_pct', 10)}%
"
                    f"📊 R/R: 1:{risk.get('rr_ratio', 2)}
"
                )
            resp += "
🎮 *وضع افتراضي*"
        else:
            resp = result.get("msg", "❌ فشل التنفيذ")

        await msg.edit_text(resp, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Execute error: {e}")
        await msg.edit_text(f"❌ خطأ: {str(e)[:100]}")


async def cmd_vtrades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الصفقات الافتراضية"""
    user_id = update.effective_user.id
    try:
        user = await engine.get_user(user_id)

        if not user or not user.virtual_wallet:
            await update.message.reply_text("❌ ما عندك محفظة")
            return

        from core.virtual_wallet import VirtualWallet
        wallet = VirtualWallet(user.virtual_wallet.to_dict() if hasattr(user.virtual_wallet, 'to_dict') else {})

        if not wallet.positions:
            await update.message.reply_text(
                "📋 *ما عندك صفقات مفتوحة*

"
                "افتح صفقة: `/execute BTC buy 500`",
                parse_mode="Markdown"
            )
            return

        lines = ["📋 *صفقاتك المفتوحة*", "━━━━━━━━━━━━━━━━━━", ""]

        for sym, pos in wallet.positions.items():
            coin = sym.replace("USDT", "")
            from core.data_layer import data_layer
            price_data = await data_layer.get_price(coin)
            current = price_data.get("price", pos["avg_price"]) if price_data else pos["avg_price"]

            pnl = (current - pos["avg_price"]) * pos["quantity"]
            pnl_pct = (pnl / max(pos["cost"], 1)) * 100
            sign = "+" if pnl >= 0 else ""
            emoji = "🟢" if pnl >= 0 else "🔴"

            lines.append(
                f"{emoji} *{sym}*
"
                f"• دخول: ${pos['avg_price']:,.4f}
"
                f"• الحالي: ${current:,.4f}
"
                f"• PnL: {sign}${pnl:,.2f} ({sign}{pnl_pct:.1f}%)
"
                f"• TP: ${pos.get('take_profit', 0):,.4f} | SL: ${pos.get('stop_loss', 0):,.4f}
"
            )

        lines.append(f"
💵 الرصيد: ${wallet.balance:,.2f}")

        await update.message.reply_text("
".join(lines), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Vtrades error: {e}")
        await update.message.reply_text("❌ خطأ في جلب الصفقات")


async def cmd_live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ربط/فصل المنصة"""
    user_id = update.effective_user.id
    args = context.args or []
    action = args[0].lower() if args else "status"

    if action == "status":
        if engine.has_live_trading(user_id):
            from core.exchange import exchange_manager
            conn = exchange_manager.get_user_exchange(user_id)
            ex_name = conn.get("exchange_id", "unknown").upper() if conn else "Unknown"
            await update.message.reply_text(f"🏦 *متصل بـ {ex_name}* ✅")
        else:
            await update.message.reply_text(
                "🎮 *وضع افتراضي*

"
                "للربط: `/live connect okx KEY SECRET`"
            )
        return

    if action == "off":
        engine.disconnect_exchange(user_id)
        await update.message.reply_text("✅ تم الفصل — وضع افتراضي 🎮")
        return

    if action == "connect":
        if len(args) < 4:
            await update.message.reply_text(
                "⚠️ *الاستخدام:*
"
                "`/live connect okx KEY SECRET [PASSPHRASE]`"
            )
            return

        ex_name = args[1].lower()
        api_key = args[2]
        api_secret = args[3]
        passphrase = args[4] if len(args) > 4 else ""

        msg = await update.message.reply_text(f"⏳ جاري الاتصال بـ {ex_name.upper()}...")

        try:
            success = await engine.connect_exchange(
                user_id, ex_name, api_key, api_secret, passphrase
            )
            if success:
                await msg.edit_text(
                    f"✅ *تم الربط بـ {ex_name.upper()}* 🏦

"
                    f"الآن يمكنك التداول الحقيقي!"
                )
            else:
                await msg.edit_text("❌ *فشل الاتصال* — تحقق من API Keys")
        except Exception as e:
            logger.error(f"Live connect error: {e}")
            await msg.edit_text("❌ خطأ في الاتصال")
        return

    await update.message.reply_text("⚠️ استخدم: /live status | connect | off")


async def cmd_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الباقات"""
    msg = (
        "💎 *باقات الفهد*
"
        "━━━━━━━━━━━━━━━━━━

"
        "🆓 *مجاني — $0*
"
        "• 30 عملة | 3 صفقات/يوم
"
        "• 15% تعرض max

"
        "🥈 *فضي — $19/شهر*
"
        "• 100 عملة | 5 صفقات/يوم
"
        "• 25% تعرض max

"
        "🥇 *ذهبي — $49/شهر*
"
        "• 150 عملة + أصول المنصة
"
        "• 35% تعرض max

"
        "💎 *ماسي — $199/شهر*
"
        "• 300 عملة + جميع الأصول
"
        "• 10 يومي / 5 أسبوعي / 10 شهري

"
        "📩 للاشتراك: تواصل مع @admin"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة الباقات (للمدير)"""
    user_id = update.effective_user.id

    if not settings.is_moderator(user_id):
        await update.message.reply_text("🔒 للمدير فقط")
        return

    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text("⚠️ `/premium add USER_ID tier`")
        return

    action = args[0].lower()
    try:
        target_id = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ user_id غير صحيح")
        return

    from core.database import db
    if action == "add" and len(args) >= 3:
        tier = args[2].lower()
        if tier not in ("free", "silver", "gold", "diamond", "admin"):
            await update.message.reply_text("❌ باقة غير صالحة")
            return

        await db.update_user_tier(target_id, tier, user_id)
        tier_name = {"free": "مجاني", "silver": "فضي", "gold": "ذهبي", 
                     "diamond": "ماسي", "admin": "مدير"}.get(tier, tier)
        await update.message.reply_text(f"✅ تم ترقية `{target_id}` إلى {tier_name}")

    elif action == "remove":
        await db.update_user_tier(target_id, "free", user_id)
        await update.message.reply_text(f"✅ تم إعادة `{target_id}` للمجاني")

    else:
        await update.message.reply_text("⚠️ استخدم: add | remove")


async def cmd_risk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حالة المخاطر"""
    user_id = update.effective_user.id
    try:
        summary = await engine.get_portfolio_summary(user_id)

        drawdown = abs(summary.get('total_pnl', 0)) / max(summary.get('total_value', 1), 1) * 100

        msg = (
            f"⚖️ *حالة المخاطر*
"
            f"━━━━━━━━━━━━━━━━━━
"
            f"📉 Drawdown: {drawdown:.1f}%
"
            f"📊 مراكز: {summary.get('open_positions', 0)}
"
            f"💎 باقة: {summary.get('tier', 'مجاني')}
"
        )

        if summary.get('is_healthy'):
            msg += "
✅ *المحفظة صحية*"
        else:
            msg += "
⚠️ *هناك تنبيهات*"
    except Exception as e:
        logger.error(f"Risk error: {e}")
        msg = "❌ خطأ في جلب البيانات"

    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_killswitch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kill Switch"""
    await update.message.reply_text(
        "🛑 *Kill Switch*

"
        "للإيقاف: `/killswitch trigger`
"
        "للإعادة: `/killswitch reset`"
    )


async def cmd_autotrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التداول الآلي"""
    args = context.args or []
    action = args[0].lower() if args else "status"

    if action in ("on", "تشغيل"):
        await update.message.reply_text(
            "🤖 *التداول الآلي مُفعَّل*

"
            "سأرسل لك إشارات للموافقة عليها."
        )
    elif action in ("off", "إيقاف"):
        await update.message.reply_text("⏹️ *التداول الآلي مُوقَّف*")
    else:
        await update.message.reply_text(
            "🤖 *التداول الآلي*
"
            "الحالة: ❌ موقف
"
            "للتفعيل: `/autotrade on`"
        )


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة المدير"""
    user_id = update.effective_user.id

    if not settings.is_moderator(user_id):
        await update.message.reply_text("🔒 للمدير فقط")
        return

    await update.message.reply_text(
        "👑 *لوحة المدير*

"
        "`/premium add USER_ID tier`
"
        "`/broadcast رسالة`"
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأزرار"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "goto_vtrades":
        await query.message.reply_text("استخدم /vtrades لعرض الصفقات")
    elif data == "report":
        await query.message.reply_text("📊 التقارير قريباً!")


async def post_init(app: Application):
    """تهيئة المحرك قبل بدء البوت"""
    logger.info("🐆 تهيئة الفهد...")
    try:
        init_vault(settings.MASTER_KEY)
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
