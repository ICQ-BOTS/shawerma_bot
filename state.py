import json
from mailru_im_async_bot.event import EventType

import utils as utils
import logging
import bot_db
import traceback
import sys

log = logging.getLogger(__name__)

# Добавочная информация в объекте user:
# user.last_message_id - последнее сообщение, отправленное пользователю

CALLBACK_WAIT_INPUT = 0
CALLBACK_ENTER_STATE = 1
CALLBACK_END_SESSION = 2


class State:
    def __init__(self, name, on_enter_handler, on_event_handler):
        self.on_enter_handler = on_enter_handler
        self.on_event_handler = on_event_handler
        self.name = name
        pass

    async def enter_state(self, bot, user, event, args={}):
        user.current_state = self
        if self.on_enter_handler:
            return await self.on_enter_handler(bot, user, event, args)

    async def on_event(self, bot, user, event, args={}):
        if self.on_event_handler:
            return await self.on_event_handler(bot, user, event, args)

    async def wait_for_input(
        self,
        bot,
        user,
        is_text_input,
        forward_args={},
        call_on_event=True,
        private_input=True,
    ):
        if is_text_input:
            user.last_message_id = None
        while True:
            response_event = await user.wait_response()
            if not private_input:
                break

            if utils.is_one_user_dialog_event(response_event):
                break

        if call_on_event:
            result = await self.on_event(bot, user, response_event, forward_args)
            return result
        else:
            return response_event

    async def wait_for_text_input_loop(self, bot, user, message=None):
        while True:
            if message:
                await show_message(bot, user, force_new_message=True, text=message)

            response_event = await self.wait_for_input(
                bot, user, True, {}, call_on_event=False
            )

            response_text = utils.get_text_from_event(response_event)
            if response_text:
                return response_text

    async def wait_for_multiple_data_input_loop(
        self, bot, user, message, required_type=None
    ):
        while True:
            await show_message(bot, user, force_new_message=True, text=message)
            response_event = await self.wait_for_input(
                bot, user, True, {}, call_on_event=False
            )

            response_cortage = utils.get_attachment_from_event(
                response_event, required_type=required_type
            )
            if response_cortage:
                return (response_cortage[0], response_cortage[1])

            response_text = utils.get_text_from_event(response_event)
            # text
            if response_text:
                return (response_text, None)

    def __str__(self):
        return "State: %s" % (self.name)


async def send_query_response(bot, event):
    if not event:
        return False

    if utils.is_button_click(event):
        if "queryId" in event.data:
            await bot.answer_callback_query(event.data["queryId"])
            return True
    return False


async def send_file(bot, user, file, text=None, buttons=None):
    return await bot.send_file(
        chat_id=user.id, file=file, caption=text, inline_keyboard_markup=buttons
    )


async def show_message(
    bot,
    user,
    force_new_message=False,
    text=None,
    buttons=None,
    stay_in_chat=False,
    message_image=None,
    file=None,
):
    log.info(f"show message: {user.last_message_id}")
    if message_image:
        if text:
            text += " " + utils.get_reference_to_file(message_image)
        else:
            text = utils.get_reference_to_file(message_image)

    if file:
        user.last_message_id = None
        stay_in_chat = True
        response = await send_file(
            bot=bot, user=user, file=file, text=text, buttons=buttons
        )
        message_id = response.get("msgId", None)
    elif force_new_message or (not user.last_message_id):
        response = await bot.send_text(
            chat_id=user.id, text=text, inline_keyboard_markup=buttons
        )
        message_id = response.get("msgId", None)
        user.last_message_id = message_id
    else:
        response = await bot.edit_text(
            chat_id=user.id,
            msg_id=user.last_message_id,
            text=text,
            inline_keyboard_markup=buttons,
        )
        message_id = user.last_message_id

    if stay_in_chat:
        user.last_message_id = None

    return message_id


def clear_last_message(user):
    user.last_message_id = None


def set_root_state(new_root_state):
    global root_state
    root_state = new_root_state


# Выпрямление действий пользователя (для исключения рекурсии)

# session start and end
def callback_wait_for_input(bot, user, is_text_input, forward_args={}):
    #                0            1    2         3            4
    return (CALLBACK_WAIT_INPUT, bot, user, is_text_input, forward_args)


def callback_enter_state(new_state, bot, user, event=None, forward_args={}):
    #                0              1        2    3      4           5
    return (CALLBACK_ENTER_STATE, new_state, bot, user, event, forward_args)


def callback_end_session(user):
    return None


async def handle_callback_action(ca):
    global root_state
    try:
        action = ca[0]
        if action == CALLBACK_WAIT_INPUT:
            if ca[2].current_state == root_state:
                return None
            print("wait for input...")
            result = await ca[2].current_state.wait_for_input(
                ca[1], ca[2], ca[3], ca[4]
            )
            return result
        elif action == CALLBACK_ENTER_STATE:
            result = await ca[1].enter_state(ca[2], ca[3], ca[4], ca[5])
            await send_query_response(ca[2], ca[4])
            return result
    except:
        log.info("Exception!")
        log.info(f"Unexpected error: {sys.exc_info()[0]}")
        traceback.print_exc()


async def end_session(user):
    log.info(f"End session for {user}")
    pass


async def start_session(bot, user, event):

    if not utils.is_one_user_dialog_event(event):
        return

    log.info(f"Start session for {user}")

    global root_state
    user.last_message_id = None
    bot_db.init_user_info(user)

    if utils.is_text_message(event) or utils.is_button_click(
        event
    ):  # Если первое действие пользователя - нажатие на кнопку
        if utils.is_button_click(event):
            user.last_message_id = event.data["message"]["msgId"]
        user.current_state = root_state
        current_action = await root_state.on_event(bot, user, event)
        await send_query_response(bot, event)

    else:
        current_action = await root_state.enter_state(bot, user, event)

    await send_query_response(bot, event)

    while current_action:
        current_action = await handle_callback_action(current_action)
        # print("State ", current_action)

    await end_session(user)
