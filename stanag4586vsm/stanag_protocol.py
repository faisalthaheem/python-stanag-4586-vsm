import logging
from stanag4586edav1.message_wrapper import *
from stanag4586edav1.message01 import *

class StanagProtocol:

    def __init__(self, loop, debug_level, message_callback):
        
        self.loop = loop
        self.message_callback = message_callback
        self.logger = logging.getLogger('StanagProtocol')
        self.logger.setLevel(debug_level)

    def connection_made(self, transport):
        self.transport = transport
        
    def datagram_received(self, data, addr):

        self.logger.debug("Got packet of len [{}]".format(len(data)))

        wrapper = MessageWrapper(data)
        self.logger.debug("Got message [{}]".format(wrapper.message_type))

        knownMessage = False
        msg = None

        if wrapper.message_type == 0x01:
            msg = Message01(data[MESSAGE_WRAPPER_LEN:])
            knownMessage = True

        if knownMessage:
            self.logger.debug("callback scheduled")
            self.loop.call_soon(self.message_callback, wrapper, msg)
