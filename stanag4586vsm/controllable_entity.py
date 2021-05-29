import logging
import pprint
from stanag4586edav1.message_wrapper import *
from stanag4586edav1.message01 import *
from stanag4586edav1.message20 import *

class ControllableEntity:

    __station_id = 0x0 #by default we are the base platform
    __vsm_id = 0x0
    __vehicle_id = 0x0
    __monitoring_cucs_list = []
    __controlling_cucs_id = 0x0
    __loop = None

    def __init__(self, loop, debug_level, station_id, vsm_id, vehicle_id, callback_tx_data):
        self.__loop = loop
        self.__station_id = station_id
        self.__vsm_id = vsm_id
        self.__vehicle_id = vehicle_id
        self.__callback_tx_data = callback_tx_data

        self.logger = logging.getLogger('ControllableEntity[{}]'.format(self.__station_id))
        self.logger.setLevel(debug_level)

    # returns true if the message is handled
    def handle_message(self, wrapper, msg):
        self.logger.debug("Got message [{}]".format(wrapper.message_type))

        if wrapper.message_type == 0x01:
            self.logger.debug("Message is auth request.")
            return self.handle_auth_message(wrapper, msg)

        return False

    def handle_auth_message(self, wrapper, msg):
    
        if  (msg.vehicle_id and MSG_01_BROADCAST_ID) == MSG_01_BROADCAST_ID and \
            (msg.vsm_id and MSG_01_BROADCAST_ID) == MSG_01_BROADCAST_ID and \
            (msg.controlled_station and MSG_01_BROADCAST_ID) == MSG_01_BROADCAST_ID:
            self.logger.debug("Message is of type discovery")
            self.handle_broadcast(wrapper, msg)
            return False # to let the chain continue to be called at caller end

        elif msg.vehicle_id == self.__vehicle_id:
            self.logger.debug("Message is of type LOI request")
            self.handle_loi_request(wrapper, msg)
            return True

        return False

    def handle_loi_request(self, wrapper, msg):
        pass

    def handle_broadcast(self, wrapper, msg):
        
        self.logger.debug("Handling discovery request")

        self.respond_21(wrapper, msg)
        self.respond_20(wrapper, msg)

        if self.__station_id == 0x0:
            self.respond_300(msg, wrapper)

    def respond_20(self, wrapper, msg):
        self.logger.debug("Responding with Message 20")

        msg20 = Message20(MSG20_NULL)

        msg20.time_stamp = 0x00
        msg20.vehicle_id = self.__vehicle_id
        msg20.cucs_id = msg.cucs_id
        msg20.vsm_id = self.__vsm_id
        msg20.vehicle_id_update = 0x0
        msg20.vehicle_type = 0x00 #todo be filled from some config in future
        msg20.vehicle_sub_type = 00 #todo be filled from some config in future
        msg20.owning_id = 0x00 #todo be filled from some config in future
        msg20.tail_number = b"\x31\x32\x33\x34" #todo be filled from some config in future
        msg20.mission_id = b"\x31\x32\x33\x34" #todo be filled from ongoing mission
        msg20.atc_call_sign = b"\x31\x32\x33\x34" #todo be filled from some config in future
        msg20.configuration_checksum = 0xABCD

        msg20_encoded = msg20.encode()
        wrapped_reply = MessageWrapper(MESSAGE_WRAPPER_NULL)
        wrapped_reply.wrap_message(wrapper.msg_instance_id, 0x20, len(msg20_encoded), False)
        encoded_msg = wrapped_reply.encode() + msg20_encoded

        self.__loop.call_soon(self.__callback_tx_data, encoded_msg)


    def respond_21(self, wrapper, msg):
        self.logger.debug("Responding with Message 21")
        pass

    def respond_300(self, wrapper, msg):
        self.logger.debug("Responding with Message 300")
        pass
