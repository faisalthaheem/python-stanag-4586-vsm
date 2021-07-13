import asyncio
import functools
import signal
import logging
from stanag4586vsm.stanag_server import *

FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(format=FORMAT)

logger = logging.getLogger("cucs")
logger.setLevel(logging.DEBUG)

def ask_exit(signame, loop):
    logger.critical("got signal [{%s}]: exit".format(signame))
    loop.stop()

def handle_message(wrapper, msg):
    logger.info("Got message [{:x}]".format(wrapper.message_type))

discovered_vehicles = {}

def handle_vehicle_discovery(controller, vehicles):
    logger.info("Vehicles discovered [{}]".format(vehicles))

    discovered_vehicles = vehicles

    #for poc purposes we have just one vehicle
    #we check if it's not already controlled by us, then we request for it to be controlled
    for veh_id in discovered_vehicles.keys():
        if discovered_vehicles[veh_id][EntityController.KEY_CONTROLLED] is False:
            controller.control_request(0x0, veh_id)

async def main():

    loop = asyncio.get_running_loop()
    server = StanagServer(logging.DEBUG)

    # for signame in {'SIGINT', 'SIGTERM'}:
    #     loop.add_signal_handler(
    #         getattr(signal, signame),
    #         functools.partial(ask_exit, signame, loop))

    logger.debug("Creating server")
    await server.setup_service(loop, StanagServer.MODE_CUCS)
    server.get_entity_controller().set_callback_for_vehicle_discovery(handle_vehicle_discovery)

    logger.info("Listening, press Ctrl+C to terminate")
    await asyncio.sleep(3600*100)

    logger.info("Server exiting")

asyncio.run(main())