# from EventHandlers import hello, run, help, buttons_answer_cb, buttons_get_cb
import event_handler as EventHandlers
import bot_states as bot_states

from mailru_im_async_bot import graphyte
from mailru_im_async_bot.bot import Bot
from mailru_im_async_bot.handler import DefaultHandler
from mailru_im_async_bot.filter import Filter

# from signal import signal, SIGUSR1
from pid import PidFile
import configparser
import asyncio
import logging
import logging.config
import sys
import os

import bot_db
import state
import json
import os.path


SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))


# set default config path
configs_path = SCRIPT_PATH

# get config path from args
if len(sys.argv) > 1:
    configs_path = sys.argv[1]

# check exists config
for config in ["config.ini", "logging.ini"]:
    if not os.path.isfile(os.path.join(configs_path, config)):
        raise FileExistsError(f"file {config} not found in path {configs_path}")

# read config
config = configparser.ConfigParser()
config.read(os.path.join(configs_path, "config.ini"))
logging.config.fileConfig(
    os.path.join(configs_path, "logging.ini"), disable_existing_loggers=False
)
log = logging.getLogger(__name__)

# init graphite sender
if config.getboolean("graphite", "enable"):
    prefix = "%s.%s.%s" % (
        config.get("graphite", "prefix"),
        config.get("main", "alias").split(".")[1],
        config.get("main", "alias").split(".")[0],
    )

    graphyte.init(
        host=config.get("graphite", "server"),
        port=config.get("graphite", "port"),
        prefix=prefix,
        timeout=2,
    )

# register signal for rotate log
# signal(SIGUSR1, do_rollover_log)

NAME = "shawarma_bot"
VERSION = "0.0.1"
HASH_ = None
TOKEN = config.get("icq_bot", "token")
POLL_TIMEOUT_S = int(config.get("icq_bot", "poll_time_s"))
REQUEST_TIMEOUT_S = int(config.get("icq_bot", "request_timeout_s"))
TASK_TIMEOUT_S = int(config.get("icq_bot", "task_timeout_s"))
TASK_MAX_LEN = int(config.get("icq_bot", "task_max_len"))
DEV = config.has_option("main", "dev") and config.getboolean("main", "dev")
state.TRASH_CHAT = config.get("icq_bot", "trash_chat")
bot_db.load_admins(json.loads(config.get("icq_bot", "admins")))

DB_HOST = config.get("tarantool", "host")
DB_PORT = config.get("tarantool", "port")

PUT_FACES_IP = config.get("put_faces_service", "host")
PUT_FACES_PORT = config.get("put_faces_service", "port")

loop = asyncio.get_event_loop()
bot = Bot(
    token=TOKEN,
    version=VERSION,
    name=NAME,
    poll_time_s=POLL_TIMEOUT_S,
    request_timeout_s=REQUEST_TIMEOUT_S,
    task_max_len=TASK_MAX_LEN,
    task_timeout_s=TASK_TIMEOUT_S,
)

bot.dispatcher.add_handler(
    DefaultHandler(callback=EventHandlers.handle_session_start, multiline=True)
)


bot_states.init(PUT_FACES_IP, PUT_FACES_PORT, DB_HOST, int(DB_PORT))

# ---------------------------------------------------------------------


def role_change(current, new):
    if current == new:
        log.info(f"the role remained the same: {current}")
    else:
        if new == "main":
            loop.create_task(bot.start_polling())
        else:
            loop.create_task(bot.stop_polling())
        log.info(f"role was change from {current} to {new}")


# async def process(rq: incoming_request):
#     log.info('{}: process called'.format(rq))
#     rq.reply(200, 'ok')

with PidFile(NAME):
    if not DEV:
        pass
        # pypros.ctlr.g_git_hash = HASH_ if HASH_ else VERSION
        # pypros.ctlr.role_changed_cb = lambda current, new: role_change(current, new)
        # pypros.ctlr.incoming_handlers.CHECK = lambda cn, p: cn.reply(p, 200, 'ok')
        # pypros.ctlr.init(
        #     self_alias=config['main']['alias'],
        #     host=config['ctlr']['host'],
        #     port=config['ctlr']['port']
        # )
    server = None
    try:
        loop.run_until_complete(bot.init())
        if not DEV:
            pass
            # server = loop.run_until_complete(
            #     pypros.listen(
            #         config['main']['host'],
            #         int(config['main']['port']), process)
            # )
        else:
            role_change("None", "main")
        loop.run_forever()
    finally:
        if server:
            server.close()
        # loop.run_until_complete(pypros.ipros.shutdown())
        loop.close()
