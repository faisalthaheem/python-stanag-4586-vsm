import asyncio
import logging
import json
from stanag4586edav1.message20 import Message20

from stanag4586vsm.stanag_server import *
from stanag4586edav1.message_wrapper import *
from stanag4586edav1.message20020 import *
from stanag4586edav1.message21 import *


FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(format=FORMAT)

logger = logging.getLogger("vehicle")
logger.setLevel(logging.DEBUG)

loop = None
server = None

def ask_exit(signame, loop):
    logger.critical("got signal [{%s}]: exit".format(signame))
    loop.stop()

def process_eo_messages(wrapper, msg):
    
    logger.info("Got message [{}]".format(wrapper.message_type))
    if wrapper.message_type == 20010:
        #respond with dummy config data
        msg20020 = Message20020(Message20020.MSGNULL)
    
        msg20020.time_stamp = 0x00
        msg20020.vehicle_id = msg.vehicle_id
        msg20020.cucs_id = msg.cucs_id
        msg20020.station_number = msg.station_number
        msg20020.requested_query_type = msg.query_type
        msg20020.set_response(json.dumps({"daylight":"rtsp://127.0.0.1:8554/live"}))

        wrapped_reply = MessageWrapper(MessageWrapper.MSGNULL)
        wrapped_reply = wrapped_reply.wrap_message(wrapper.msg_instance_id, 20020, msg20020, False)

        loop.call_soon(server.tx_data, wrapped_reply)

async def main():

    global loop
    global server

    loop = asyncio.get_running_loop()
    server = StanagServer(logging.DEBUG)

    # for signame in {'SIGINT', 'SIGTERM'}:
    #     loop.add_signal_handler(
    #         getattr(signal, signame),
    #         functools.partial(ask_exit, signame, loop))

    logger.debug("Creating server")
    await server.setup_service(loop, StanagServer.MODE_VEHICLE, Message21.VEHICLE_TYPE_UGV, Message21.UGV_SUB_TYPE_SURV)

    #set our callback to start getting requests unprocessed by default implementation
    server.get_entity("eo").set_callback_for_unhandled_messages(process_eo_messages)

    logger.info("Listening, press Ctrl+C to terminate")
    await asyncio.sleep(3600*100)

    logger.info("Server exiting")

asyncio.run(main())