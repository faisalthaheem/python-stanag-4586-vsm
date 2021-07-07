import logging
from stanag4586edav1.message_wrapper import *
from stanag4586edav1.message01 import *
from stanag4586edav1.message200 import *
from stanag4586edav1.message1200 import *
from stanag4586edav1.message20000 import *

class StanagProtocol:

    def __init__(self, loop, debug_level, on_msg_rx_callback, on_con_lost_callback, rx_enabled = True):
        
        self.loop = loop
        self.transport = None

        self.on_msg_rx_callback = on_msg_rx_callback
        self.on_con_lost_callback = on_con_lost_callback
        
        self.logger = logging.getLogger('StanagProtocol')
        self.logger.setLevel(debug_level)

        self.rx_enabled = rx_enabled

    def connection_made(self, transport):
        self.transport = transport
    
    def error_received(self, exc):
        self.logger.error('Error received [{}]'.format(exc))

    def connection_lost(self, exc):
        self.logger.error("Connection lost")
        self.loop.call_soon(self.on_con_lost_callback)
        
    def datagram_received(self, data, addr):

        if not self.rx_enabled:
            self.logger.warn("Rx is disabled and yet got a message on this socket.")
            return

        self.logger.debug("Got packet of len [{}]".format(len(data)))

        wrapper = MessageWrapper(data)
        self.logger.debug("Got message [{:}]".format(wrapper.message_type))

        knownMessage = False
        msg = None

        if wrapper.message_type == 1:
            msg = Message01(data[MESSAGE_WRAPPER_LEN:])
            knownMessage = True

        elif wrapper.message_type == 200:
            msg = Message200(data[MESSAGE_WRAPPER_LEN:])
            knownMessage = True

        elif wrapper.message_type == 1200:
            msg = Message1200(data[MESSAGE_WRAPPER_LEN:])
            knownMessage = True

        elif wrapper.message_type == 20000:
            msg = Message20000(data[MESSAGE_WRAPPER_LEN:])
            knownMessage = True

        if knownMessage:
            self.logger.debug("callback scheduled")
            self.loop.call_soon(self.on_msg_rx_callback, wrapper, msg)
