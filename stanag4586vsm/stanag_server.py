import asyncio
import socket
import struct
from types import coroutine
from .stanag_protocol import StanagProtocol
from .controllable_entity import ControllableEntity
from .entity_controller import EntityController
import logging
from stanag4586edav1.message300 import *
from stanag4586edav1.message_wrapper import *
from stanag4586edav1.message01 import *

STANAG_SERVER_MODE_VEHICLE = 0
STANAG_SERVER_MODE_CUCS = 1

class StanagServer:

    MODE_VEHICLE = 0
    MODE_CUCS = 1


    """Config parameters, to be read from config"""
    __CUCS_ID = 0xFAFAFAFA
    __VEHICLE_ID = 0
    __VSM_ID = 0
    __VEHICLE_TYPE = 0
    __VEHICLE_SUB_TYPE = 0

    """Holds reference to the current asyncio loop this class was created on"""
    __loop = None
    
    __controllable_entities = {}
    __entities_controller = None
    __mode = MODE_VEHICLE

    """Encapsulates a task that sends out periodic discover 01 messages on network"""
    __task_discover = None
    
    def __init__(self, debug_level):
        self.logger = logging.getLogger('StanagServer')
        self.logger.setLevel(debug_level)
        self.debug_level = debug_level

    async def cleanup_service(self):
        if self.__task_discover is not None:
            self.__task_discover.cancel()

    async def setup_service(self, loop, mode, vehicle_type = 0, vehicle_sub_type = 0, 
        port_rx = 4586, port_tx = 4587, addr_rx = "224.10.10.10", addr_tx = "224.10.10.10"):

        self.logger.info("Server setup Started.")

        self.__loop = loop
        self.__mode = mode
        self.__VEHICLE_TYPE = vehicle_type
        self.__VEHICLE_SUB_TYPE = vehicle_sub_type

        if mode is self.MODE_VEHICLE:
            self.logger.info("Creating entities.")
            self.create_entities(loop)


        if mode is self.MODE_VEHICLE:
            self.logger.info("Setting up network i/o on vehicle side.")
            await self.create_rx_socket(loop, port_rx, addr_rx)
            await self.create_tx_socket(loop, port_tx, addr_tx)
        else:
            self.logger.info("Setting up network i/o on cucs side.")
            await self.create_rx_socket(loop, port_tx, addr_tx)
            await self.create_tx_socket(loop, port_rx, addr_rx)

        if mode is self.MODE_CUCS:
            self.create_cucs_tasks()
        
        self.logger.info("Server setup completed.")

    def on_rx_con_lost(self):
        pass

    async def create_rx_socket(self, loop, port_rx, addr_rx):

        self.logger.info("Binding to port 0.0.0.0:{}".format(port_rx))

        self.__sock_rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__sock_rx.bind(('', port_rx))
        group = socket.inet_aton(addr_rx)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        self.__sock_rx.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        self.__sock_rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__sock_rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        self.__transport_rx, self.__protocol_rx = await loop.create_datagram_endpoint(
            lambda: StanagProtocol(loop, self.debug_level, self.on_msg_rx, self.on_rx_con_lost, True),
            sock=self.__sock_rx,
        )
    
    def on_tx_con_lost(self):
        pass

    async def create_tx_socket(self, loop, port_tx, addr_tx):

        self.__transport_tx, self.__protocol_tx = await loop.create_datagram_endpoint(
            lambda: StanagProtocol(loop, self.debug_level, self.on_msg_rx, self.on_tx_con_lost, False),
            remote_addr=(addr_tx, port_tx)
        )

    def tx_data(self, data):
        """Transmit the data on network using __transport_tx, returns nothing."""
        if self.__transport_tx is not None:
            self.__transport_tx.sendto(data)

    def create_cucs_tasks(self):
        self.__entities_controller = EntityController(self.__loop, self.debug_level, self.__CUCS_ID, self.__VSM_ID, self.tx_data)
        self.__task_discover = self.__loop.create_task(self.task_discover())

        
    def create_entities(self, loop):
        """Creates all the sensors and stations that can be controlled by CUCS. Returns nothing."""
        
        self.__controllable_entities['base'] = ControllableEntity(
            loop, 
            self.debug_level, 0x0, 
            self.__VSM_ID, self.__VEHICLE_ID, 
            self.__VEHICLE_TYPE, self.__VEHICLE_SUB_TYPE,
            self.tx_data)
            
        self.__controllable_entities['eo'] = ControllableEntity(
            loop, 
            self.debug_level, 0x1, 
            self.__VSM_ID, self.__VEHICLE_ID, 
            self.__VEHICLE_TYPE, self.__VEHICLE_SUB_TYPE,
            self.tx_data)
        
        self.__controllable_entities['base'].set_available_stations(0x01)
        self.__controllable_entities['eo'].set_payload_type(Message300.PAYLOAD_TYPE_EOIR)

    def get_entity(self, entity_name):
        if entity_name in self.__controllable_entities.keys():
            return self.__controllable_entities[entity_name]
                
    def get_entity_controller(self):
        return self.__entities_controller

    def on_msg_rx(self, wrapper, msg):
        """Callback passed to stanag protocal and is invoked when a known message arrives."""
        self.logger.debug("Got message [{}]".format(wrapper.message_type))

        if self.__mode is self.MODE_VEHICLE:
            """If running on the vehicle end"""
            for k,v in self.__controllable_entities.items():
                if True == v.handle_message(wrapper, msg):
                    return

            if wrapper.message_type != 1:
                # got a message that was not handled....
                self.logger.warn('Message [{}] not handled'.format(wrapper.message_type))

        elif self.__mode is self.MODE_CUCS:
            """If running on the cucs side"""
            self.__entities_controller.handle_message(wrapper, msg)


    @coroutine
    def task_discover(self):
        self.logger.debug("Started discover task")
        while True:
            """Send Msg 01 to discover vehicles on the network"""

            msg01 = Message01(Message01.MSGNULL)
            msg01.make_discovery_message(self.__CUCS_ID)
            
            wrapper = MessageWrapper(MessageWrapper.MSGNULL)
            wrapped_msg = wrapper.wrap_message(1, 0x01, msg01, False)

            self.__loop.call_soon(self.tx_data, wrapped_msg)
            
            self.logger.debug("Discover message sent")

            """Should be read from the config file"""
            yield from asyncio.sleep(5)