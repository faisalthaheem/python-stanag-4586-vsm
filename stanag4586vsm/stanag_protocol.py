import logging
from stanag4586edav1.message_wrapper import *
from stanag4586edav1.message01 import *
from stanag4586edav1.message20 import *
from stanag4586edav1.message21 import *
from stanag4586edav1.message200 import *
from stanag4586edav1.message300 import *
from stanag4586edav1.message301 import *
from stanag4586edav1.message302 import *
from stanag4586edav1.message1200 import *
from stanag4586edav1.message20000 import *
from stanag4586edav1.message20010 import *
from stanag4586edav1.message20020 import *
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

        msg = None

        known_messages = {
            1 : Message01,
            20 : Message20,
            21 : Message21,
            200 : Message200,
            300 : Message300,
            301 : Message301,
            302 : Message302,
            1200 : Message1200,
            20000 : Message20000,
            20010 : Message20010,
            20020 : Message20020,
        }
        

        if wrapper.message_type in known_messages.keys():
            msg_type_to_instantiate = known_messages[wrapper.message_type]
            msg = msg_type_to_instantiate(data[MessageWrapper.MSGLEN:])

        if msg is not None:
            self.logger.debug("callback scheduled")
            self.loop.call_soon(self.on_msg_rx_callback, wrapper, msg)
