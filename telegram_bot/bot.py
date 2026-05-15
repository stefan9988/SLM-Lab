"""Telegram bot that routes messages to the general agent."""

import asyncio
import logging

import telegramify_markdown
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from AI.agents.initialize_agent import init_agent
from AI.prompts.general_agent_prompt import build_general_agent_prompt
from AI.tools import get_telegram_agent_enabled_tools
from BE.config import init_config, settings as be_settings
from BE.session_store import InMemoryStore

from .config import settings

logger = logging.getLogger(__name__)

agent = None


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages, routing them to the agent."""
    user = update.effective_user
    if user is None or user.id != settings.TELEGRAM_ALLOWED_USER_ID:
        logger.warning(
            "Rejected message from unauthorized user: %s",
            user.id if user else "unknown",
        )
        return

    text = update.message.text
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )

    try:
        response = await agent.invoke(
            text,
            settings.TELEGRAM_SESSION_ID,
            user_id=settings.TELEGRAM_BOT_USER_ID,
        )
        await update.message.reply_text(
            telegramify_markdown.markdownify(response),
            parse_mode="MarkdownV2",
        )
    except Exception:
        logger.error("Agent invocation failed", exc_info=True)
        await update.message.reply_text(
            "Sorry, something went wrong. Please try again."
        )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /clear command — wipes the conversation history."""
    user = update.effective_user
    if user is None or user.id != settings.TELEGRAM_ALLOWED_USER_ID:
        logger.warning("Unauthorized /clear attempt from user %s", user and user.id)
        return
    await agent.clear_history(
        session_id=settings.TELEGRAM_SESSION_ID,
        user_id=settings.TELEGRAM_BOT_USER_ID,
    )
    logger.info("Chat history cleared for session %s", settings.TELEGRAM_SESSION_ID)
    await update.message.reply_text("Chat history cleared.")


def main() -> None:
    """Initialize the agent and start the bot."""
    init_config()

    global agent
    agent = init_agent(
        system_prompt=build_general_agent_prompt(),
        tools=get_telegram_agent_enabled_tools(be_settings),
        maintain_history=True,
        provider=settings.TELEGRAM_AGENT_LLM_PROVIDER
        or be_settings.GENERAL_AGENT_LLM_PROVIDER
        or None,
        model_name=settings.TELEGRAM_AGENT_MODEL_NAME
        or be_settings.GENERAL_AGENT_MODEL_NAME
        or None,
        agent_name="telegram_general_agent",
        session_store=InMemoryStore(),
    )

    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Starting Telegram bot (long polling)...")
    app.run_polling()
