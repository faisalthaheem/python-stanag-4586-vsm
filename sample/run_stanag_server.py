import asyncio
import functools
import signal
import logging
from stanag4586vsm.stanag_server import *

FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(format=FORMAT)

logger = logging.getLogger("main")
logger.setLevel(logging.DEBUG)

def ask_exit(signame, loop):
    logger.critical("got signal [{%s}]: exit".format(signame))
    loop.stop()

def handle_message(wrapper, msg):
    logger.info("Got message [{:x}]".format(wrapper.message_type))

async def main():

    loop = asyncio.get_running_loop()
    server = StanagServer(logging.DEBUG)

    # for signame in {'SIGINT', 'SIGTERM'}:
    #     loop.add_signal_handler(
    #         getattr(signal, signame),
    #         functools.partial(ask_exit, signame, loop))

    logger.debug("Creating server")
    await server.setup_service(loop)

    #set our callback to start getting requests unprocessed by default implementation
    server.get_entity("eo").set_callback_for_unhandled_messages(handle_message)

    logger.info("Listening, press Ctrl+C to terminate")
    await asyncio.sleep(3600*100)

    logger.info("Server exiting")

asyncio.run(main())