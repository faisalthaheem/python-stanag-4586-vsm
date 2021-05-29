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

async def main():

    loop = asyncio.get_running_loop()
    server = StanagServer(logging.DEBUG)

    # for signame in {'SIGINT', 'SIGTERM'}:
    #     loop.add_signal_handler(
    #         getattr(signal, signame),
    #         functools.partial(ask_exit, signame, loop))

    logger.debug("Creating server")
    await server.setup_service(loop)

    logger.info("Listening, press Ctrl+C to terminate")
    await asyncio.sleep(3600*100)

    logger.info("Server exiting")

asyncio.run(main())