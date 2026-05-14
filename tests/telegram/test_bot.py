"""Tests for telegram_bot.bot message handling."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import telegram_bot.bot as bot_module

ALLOWED_USER_ID = 12345
SESSION_ID = "telegram_main"
BOT_USER_ID = "telegram_bot_user"


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.warm_session = AsyncMock()
    agent.invoke = AsyncMock(return_value="Hello from agent!")
    agent.clear_history = AsyncMock()
    return agent


@pytest.fixture
def mock_update():
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = ALLOWED_USER_ID
    update.effective_chat = MagicMock()
    update.effective_chat.id = 99999
    update.message = MagicMock()
    update.message.text = "Hello bot!"
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    context = MagicMock()
    context.bot = MagicMock()
    context.bot.send_chat_action = AsyncMock()
    return context


@pytest.fixture(autouse=True)
def setup_bot(mock_agent):
    """Inject mock agent and settings into the bot module."""
    mock_settings = MagicMock()
    mock_settings.TELEGRAM_ALLOWED_USER_ID = ALLOWED_USER_ID
    mock_settings.TELEGRAM_SESSION_ID = SESSION_ID
    mock_settings.TELEGRAM_BOT_USER_ID = BOT_USER_ID

    original_agent = bot_module.agent
    bot_module.agent = mock_agent
    with patch.object(bot_module, "settings", mock_settings):
        yield
    bot_module.agent = original_agent


@pytest.mark.asyncio
async def test_unauthorized_user_ignored(mock_update, mock_context, mock_agent):
    mock_update.effective_user.id = 99999  # Not the allowed user
    await bot_module.handle_message(mock_update, mock_context)
    mock_agent.invoke.assert_not_called()
    mock_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_message_invokes_agent(mock_update, mock_context, mock_agent):
    await bot_module.handle_message(mock_update, mock_context)
    mock_agent.invoke.assert_called_once_with(
        "Hello bot!",
        SESSION_ID,
        user_id=BOT_USER_ID,
    )
    mock_update.message.reply_text.assert_called_once_with("Hello from agent!")


@pytest.mark.asyncio
async def test_warm_session_not_called(mock_update, mock_context, mock_agent):
    """InMemoryStore needs no warming; warm_session should not be called."""
    await bot_module.handle_message(mock_update, mock_context)
    mock_agent.warm_session.assert_not_called()


@pytest.mark.asyncio
async def test_agent_error_replies_gracefully(mock_update, mock_context, mock_agent):
    mock_agent.invoke.side_effect = RuntimeError("LLM crashed")
    await bot_module.handle_message(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once_with(
        "Sorry, something went wrong. Please try again."
    )


@pytest.mark.asyncio
async def test_clear_command_clears_history(mock_update, mock_context, mock_agent):
    await bot_module.clear_command(mock_update, mock_context)
    mock_agent.clear_history.assert_called_once_with(
        session_id=SESSION_ID,
        user_id=BOT_USER_ID,
    )
    mock_update.message.reply_text.assert_called_once_with("Chat history cleared.")


@pytest.mark.asyncio
async def test_clear_command_unauthorized_ignored(
    mock_update, mock_context, mock_agent
):
    mock_update.effective_user.id = 99999  # Not the allowed user
    await bot_module.clear_command(mock_update, mock_context)
    mock_agent.clear_history.assert_not_called()
    mock_update.message.reply_text.assert_not_called()
