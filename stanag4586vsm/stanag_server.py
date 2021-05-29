import asyncio
import socket
import struct
from .stanag_protocol import StanagProtocol
from .controllable_entity import ControllableEntity
import logging

class StanagServer:
    
    __controllable_entities = []
    
    def __init__(self, debug_level):
        self.logger = logging.getLogger('StanagServer')
        self.logger.setLevel(debug_level)
        self.debug_level = debug_level

    async def createUDPServer(self, loop, port_rx = 4586, port_tx = 4587, addr_rx = "224.10.10.10", addr_tx = "224.10.10.10"):

        self.createEntities(loop)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', port_rx))
        group = socket.inet_aton(addr_rx)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        self.__transport_rx, self.__protocol_rx = await loop.create_datagram_endpoint(
            lambda: StanagProtocol(loop, self.debug_level, self.messageCallback),
            sock=sock,
        )
        
    def createEntities(self, loop):
        self.__controllable_entities.append(
            ControllableEntity(loop, self.debug_level, 0x0, 0x1, 0x1)
        )

    def messageCallback(self, wrapper, msg):

        self.logger.debug("Got message [{}]".format(wrapper.message_type))

        for e in self.__controllable_entities:
            if True == e.handle_message(wrapper, msg):
                return

        # we got a message that was not understood....
        self.logger.warn('Message [{}] not understood'.format(wrapper.message_type))