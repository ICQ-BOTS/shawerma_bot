from mailru_im_async_bot.event import EventType
import json
import urllib
import traceback
import os


def action_and_args_from_event(event):
    if event.type == EventType.CALLBACK_QUERY:
        try:
            event_data = json.loads(event.data["callbackData"])
            return (event_data["action"], event_data["args"])
        except:
            return None

    return None


def get_text_from_event(event):
    if event.type == EventType.NEW_MESSAGE:
        try:
            return event.text
        except:
            return None
    return None


def get_attachment_from_event(event, required_type=None):
    if event.type == EventType.NEW_MESSAGE:
        try:
            event_data = event.data
            payload = event_data["parts"][0]["payload"]
            if required_type:
                if required_type != payload["type"]:
                    return None

            return (payload.get("caption", ""), payload["fileId"])
        except:
            return None
    return None


def is_one_user_dialog_event(event, default=True):
    chat_info = event.data.get("chat", None)

    if chat_info != None:
        return chat_info["type"] == "private"

    message_info = event.data.get("message", None)

    if message_info != None:
        return message_info["chat"]["type"] == "private"

    return True


def get_reference_to_file(file_id):
    return "https://files.icq.net/get/%s" % file_id


def check_in_array(array, index):
    return 0 <= index and index < len(array)


def array_element_normal(array, index):
    if check_in_array(array, index):
        return array[index]

    return None


def build_all_update(cortage):
    result = []
    for index in range(1, len(cortage)):
        result.append(("=", index, cortage[index]))
    return result


def ru_char_from_index(index):
    return chr(ord("а") + index)


def save_file(url, name):
    urllib.request.urlretrieve(url, name)


# Получение первого доступного имени файла
def get_next_file_name(template):
    i = 0
    while os.path.exists(template % (i)):
        i += 1
    return template % (i)


def is_text_message(event):
    return event.type == EventType.NEW_MESSAGE


def is_button_click(event):
    return event.type == EventType.CALLBACK_QUERY
