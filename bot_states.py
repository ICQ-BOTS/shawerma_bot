import state
import bot_db
from button_menu import ButtonsMenuBuilder, ButtonCallbackHandler

import logging
import os
import random
import utils
import aiohttp
import base64
import json

log = logging.getLogger(__name__)
ENCODING = "utf-8"

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))

# --------------------------------root state--------------------------------

RETURN_TO_ROOT_BUTTON_ACTION = "return_to_root"
CANCEL_BUTTON_ACTION = "cancel"


async def default_root_return_handler(bot, user, event, args):
    global root_state
    return state.callback_enter_state(
        root_state, bot, user, event, {"end_session": True}
    )


async def standart_buttons_callback_handler(bot, user, event, args):
    return await user.current_state.buttons_callback_handler.handle_event(
        bot, user, event, user.current_state
    )


ROOT_ADMINS_EDIT_BUTTON_ACTION = "root:admins_edit"
ROOT_GET_STATISTICS_BUTTON_ACTION = "root:get_statistics"
ROOT_GET_FAST_STATISTICS_BUTTON_ACTION = "root:get_fast_statistics"


async def on_root_enter(bot, user, event, args):
    bmb = ButtonsMenuBuilder()

    if user.permissions == 2:
        bmb.add_action_button("Статистика", ROOT_GET_STATISTICS_BUTTON_ACTION)
        bmb.next_row()
        bmb.add_action_button(
            "Быстрая статистика", ROOT_GET_FAST_STATISTICS_BUTTON_ACTION
        )

    await state.show_message(
        bot=bot,
        user=user,
        text="Привет! Отправь мне свое фото и я вставлю твое лицо в шаурму 🌯",
        buttons=bmb.get_to_send(),
    )

    return state.callback_wait_for_input(bot, user, False)


async def face_photo_loaded(bot, user, event, args):
    face_file = utils.get_attachment_from_event(event, required_type="image")
    if face_file is None:
        return state.callback_enter_state(root_state, bot, user, event)
    user.state_params["face_file"] = face_file

    return state.callback_enter_state(shawarma_load_state, bot, user, event)


async def get_statistics(bot, user, event, args):
    if user.permissions == 0:
        return state.callback_enter_state(root_state, bot, user, event)

    workbook = bot_db.get_statistics()
    file = f"{SCRIPT_PATH}/statistics/statistics.xlsx"
    workbook.save(file)

    bmb = ButtonsMenuBuilder()
    bmb.add_action_button("Спасибо!", RETURN_TO_ROOT_BUTTON_ACTION)
    await state.show_message(
        bot=bot,
        user=user,
        text="Статистика:",
        buttons=bmb.get_to_send(),
        file=open(file, "rb"),
    )
    if os.path.exists(file):
        os.remove(file)

    return state.callback_wait_for_input(bot, user, False)


async def get_fast_statistics(bot, user, event, args):
    if user.permissions == 0:
        return state.callback_enter_state(root_state, bot, user, event)
    return state.callback_enter_state(fast_statistics, bot, user, event)


# --------------------------------root state--------------------------------

# -----------------------------Shawarma load state------------------------

SHAWARMA_LOAD_RANDOM_SHAWARMA = "shawarma_load_state:random_shawarma"


async def on_shawarma_load_enter(bot, user, event, args):
    print("on_shawarma_load_enter")
    bmb = ButtonsMenuBuilder()
    bmb.add_action_button("Рандомная шаурма", SHAWARMA_LOAD_RANDOM_SHAWARMA)

    await state.show_message(
        bot=bot,
        user=user,
        text="Отправь фото шаурмы или нажми на кнопку, чтоб получить случайный результат 😉",
        buttons=bmb.get_to_send(),
    )

    return state.callback_wait_for_input(bot, user, False)


async def send_shawarma(bot, user, face_image_file, shawarma_image_file):
    result_number = random.randint(0, 1023)
    message_id = await state.show_message(
        bot=bot,
        user=user,
        text="Подождите, результат загружается...",
        stay_in_chat=True,
    )

    # Prepare face image (set None or download)
    face_image = None
    if not face_image_file is None:
        async with aiohttp.ClientSession() as session:
            file_info = await bot.get_file_info(face_image_file[1])
            image_url = file_info.get("url", None)
            if not image_url is None:
                async with session.get(image_url) as resp:
                    face_image_bytes = await resp.read()
                    face_image = base64.b64encode(face_image_bytes).decode(ENCODING)
            await session.close()
    shawarma_image = None
    if not shawarma_image_file is None:
        async with aiohttp.ClientSession() as session:
            file_info = await bot.get_file_info(shawarma_image_file[1])
            image_url = file_info.get("url", None)
            if not image_url is None:
                async with session.get(image_url) as resp:
                    shawarma_image_bytes = await resp.read()
                    shawarma_image = base64.b64encode(shawarma_image_bytes).decode(
                        ENCODING
                    )
            await session.close()

    # Create session
    bot_db.add_user_picture_gen(user.id)

    async with aiohttp.ClientSession() as session:
        bmb = ButtonsMenuBuilder()
        bmb.add_action_button("Попробовать снова", "return_to_root")
        request_data = {
            "bot_info": [bot.token, bot.name],
            "callback_message_id": message_id,
            "callback_chat_id": user.id,
            "callback_addition": {"buttons": bmb.get_to_send()},
            "watermark": "shawarma_bot",
            "face_image": face_image,
        }

        if shawarma_image is None:
            request_data["shawarma_generator"] = [result_number, False, False]
        else:
            request_data["shawarma_image"] = shawarma_image

        async with await session.post(
            f"http://{PUT_FACES_IP}:{PUT_FACES_PORT}/shawarma_put",
            data=json.dumps(request_data),
        ) as response:
            response_dict = await response.text()
        await session.close()


async def on_random_shawarma_clicked(bot, user, event, args):
    await send_shawarma(bot, user, user.state_params["face_file"], None)
    return None


async def shawarma_photo_loaded(bot, user, event, args):
    shawarma_file = utils.get_attachment_from_event(event, required_type="image")
    if shawarma_file is None:
        return state.callback_enter_state(root_state, bot, user, event)

    await send_shawarma(bot, user, user.state_params["face_file"], shawarma_file)
    return None


# -----------------------------Shawarma load state------------------------

# ----------------------------Fast statistics state-----------------------


async def on_fast_statistics_enter(bot, user, event, args):

    bmb = ButtonsMenuBuilder()

    common, users_count = bot_db.get_fast_statistics()

    message_text = "Статстика генераций:"

    bmb.add_action_button("Спасибо!", CANCEL_BUTTON_ACTION)

    message_text += "\n\nВсего генераций: %d" % (common)
    message_text += "\nВсего пользователей: %d" % (users_count)
    await state.show_message(
        bot=bot, user=user, text=message_text, buttons=bmb.get_to_send()
    )
    return state.callback_wait_for_input(bot, user, False, args)


# ----------------------------Fast statistics state-----------------------


def init(put_faces_ip, put_faces_port, db_host, db_port):
    global PUT_FACES_IP, PUT_FACES_PORT, root_state, fast_statistics, shawarma_load_state
    PUT_FACES_IP = put_faces_ip
    PUT_FACES_PORT = put_faces_port
    bot_db.connect(db_host, db_port)

    # root state
    root_state = state.State("root", on_root_enter, standart_buttons_callback_handler)
    root_state.buttons_callback_handler = ButtonCallbackHandler()
    root_state.buttons_callback_handler.add_action(
        ROOT_GET_STATISTICS_BUTTON_ACTION, get_statistics
    )
    root_state.buttons_callback_handler.add_action(
        ROOT_GET_FAST_STATISTICS_BUTTON_ACTION, get_fast_statistics
    )

    root_state.buttons_callback_handler.add_action(
        RETURN_TO_ROOT_BUTTON_ACTION, default_root_return_handler
    )
    root_state.buttons_callback_handler.set_not_button_action(face_photo_loaded)

    # Shawarma load state

    shawarma_load_state = state.State(
        "Shawarma load", on_shawarma_load_enter, standart_buttons_callback_handler
    )
    shawarma_load_state.buttons_callback_handler = ButtonCallbackHandler()
    shawarma_load_state.buttons_callback_handler.add_action(
        SHAWARMA_LOAD_RANDOM_SHAWARMA, on_random_shawarma_clicked
    )
    shawarma_load_state.buttons_callback_handler.set_not_button_action(
        shawarma_photo_loaded
    )

    # Fast statistics

    fast_statistics = state.State(
        "Fast statistics", on_fast_statistics_enter, standart_buttons_callback_handler
    )
    fast_statistics.buttons_callback_handler = ButtonCallbackHandler()
    fast_statistics.buttons_callback_handler.add_action(
        CANCEL_BUTTON_ACTION, default_root_return_handler
    )

    state.set_root_state(root_state)
