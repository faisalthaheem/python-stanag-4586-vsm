import asyncio
import functools
import signal
from stanag4586vsm.stanag_server_helper import *

def ask_exit(signame, loop):
    print("got signal %s: exit" % signame)
    loop.stop()

def messageCallback(wrapper, msg):
    print("In host program: ", wrapper.message_type)

async def main():

    loop = asyncio.get_running_loop()

    # for signame in {'SIGINT', 'SIGTERM'}:
    #     loop.add_signal_handler(
    #         getattr(signal, signame),
    #         functools.partial(ask_exit, signame, loop))

    print("Creating server")
    transport, protocol = await createUDPServer(loop, messageCallback)

    print("Listening, press Ctrl+C to terminate")
    await asyncio.sleep(3600*100)

    print("Server exiting")

asyncio.run(main())