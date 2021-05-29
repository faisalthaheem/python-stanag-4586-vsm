import asyncio
import functools
import signal
import logging
from stanag4586vsm.stanag_server import *

FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(format=FORMAT)

def ask_exit(signame, loop):
    print("got signal %s: exit" % signame)
    loop.stop()

async def main():

    loop = asyncio.get_running_loop()
    server = StanagServer(logging.DEBUG)

    # for signame in {'SIGINT', 'SIGTERM'}:
    #     loop.add_signal_handler(
    #         getattr(signal, signame),
    #         functools.partial(ask_exit, signame, loop))

    print("Creating server")
    await server.createUDPServer(loop)

    print("Listening, press Ctrl+C to terminate")
    await asyncio.sleep(3600*100)

    print("Server exiting")

asyncio.run(main())