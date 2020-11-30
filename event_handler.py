import state

# Точка входа пользователя


async def handle_session_start(bot, event, user):
    await state.start_session(bot, user, event)
