import asyncio
import socket
import struct
from .stanag_protocol import StanagProtocol
from .controllable_entity import ControllableEntity
import logging
from stanag4586edav1.message300 import *

class StanagServer:
    
    __controllable_entities = {}
    
    def __init__(self, debug_level):
        self.logger = logging.getLogger('StanagServer')
        self.logger.setLevel(debug_level)
        self.debug_level = debug_level

    async def setup_service(self, loop, port_rx = 4586, port_tx = 4587, addr_rx = "224.10.10.10", addr_tx = "224.10.10.10"):

        self.logger.info("Server setup Started.")

        self.logger.info("Creating entities.")
        self.create_entities(loop)

        self.logger.info("Setting up network i/o.")
        await self.create_rx_socket(loop, port_rx, addr_rx)
        await self.create_tx_socket(loop, port_tx, addr_tx)

        self.logger.info("Server setup completed.")

    def on_rx_con_lost(self):
        pass

    async def create_rx_socket(self, loop, port_rx, addr_rx):
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
            remote_addr=(addr_tx, port_tx),
        )

    def tx_data(self, data):
        """Transmit the data on network using __transport_tx, returns nothing."""
        if self.__transport_tx is not None:
            self.__transport_tx.sendto(data)
        
    def create_entities(self, loop):
        """Creates all the sensors and stations that can be controlled by CUCS. Returns nothing."""
        
        self.__controllable_entities['base'] = ControllableEntity(loop, self.debug_level, 0x0, 0x1, 0x1, self.tx_data)
        self.__controllable_entities['eo'] = ControllableEntity(loop, self.debug_level, 0x1, 0x1, 0x1, self.tx_data)
        
        self.__controllable_entities['base'].set_available_stations(0x01)
        self.__controllable_entities['eo'].set_payload_type(STATION_TYPE_EO)

    def on_msg_rx(self, wrapper, msg):
        """Callback passed to stanag protocal and is invoked when a known message arrives."""
        self.logger.debug("Got message [{}]".format(wrapper.message_type))

        for k,v in self.__controllable_entities.items():
            if True == v.handle_message(wrapper, msg):
                return

        if wrapper.message_type != 0x01:
            # got a message that was not understood....
            self.logger.warn('Message [{}] not understood'.format(wrapper.message_type))

    def get_entity(self, entity_name):
        if entity_name in self.__controllable_entities.keys():
            return self.__controllable_entities[entity_name]