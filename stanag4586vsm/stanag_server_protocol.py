from stanag4586edav1.message_wrapper import *
from stanag4586edav1.message01 import *

class StanagServerProtocol:

    __this_station_id = 0x0 #by default we are the base platform
    __monitoring_cucs_list = []
    __controlling_cucs_id = 0x0


    def __init__(self, loop, message_callback, port_tx, addr_tx):
        
        self.port_tx = port_tx
        self.addr_tx = addr_tx
        self.loop = loop
        self.message_callback = message_callback

    def configure(self, station_id, vsm_id, vehicle_id):
        self.__this_station_id = station_id
        self.vsm_id = vsm_id
        self.vehicle_id = vehicle_id

    def connection_made(self, transport):
        self.transport = transport
        
    def datagram_received(self, data, addr):
        # message = data.decode()
        # print('Received %r from %s' % (message, addr))
        # print('Send %r to %s' % (message, addr))
        # self.transport.sendto(data, addr)
        print("Got data")
        wrapper = MessageWrapper(data)
        print("Got message of type: ", wrapper.message_type)

        messageKnown = False
        msg = None

        if wrapper.message_type == 0x01:
            msg = Message01(data[MESSAGE_WRAPPER_LEN:])
            print("{:x}".format(msg.vsm_id))
            messageKnown = True

        if messageKnown:
            print("callback scheduled")
            self.loop.call_soon(self.message_callback, wrapper, msg)
                
