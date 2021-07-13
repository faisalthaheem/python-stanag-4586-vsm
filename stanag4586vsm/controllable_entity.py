from enum import auto
import logging
import sys
from stanag4586edav1.message_wrapper import *
from stanag4586edav1.message01 import *
from stanag4586edav1.message20 import *
from stanag4586edav1.message21 import *
from stanag4586edav1.message300 import *

class ControllableEntity:

    __station_id = 0x0 #by default we are the base platform
    __vsm_id = 0x0
    __vehicle_id = 0x0
    __vehicle_type = 0x0
    __vehicle_sub_type = 0x0
    __monitoring_cucs_list = []
    __controlling_cucs_id = 0x0
    __loop = None
    __available_stations = 0x00
    __payload_type = 0x00
    __callback_unhandled_messages = None

    def __init__(self, loop, debug_level, station_id, vsm_id, vehicle_id, vehicle_type, vehicle_sub_type, callback_tx_data):
        self.__loop = loop
        self.__station_id = station_id
        self.__vsm_id = vsm_id
        self.__vehicle_id = vehicle_id
        self.__vehicle_type = vehicle_type
        self.__vehicle_sub_type = vehicle_sub_type
        self.__callback_tx_data = callback_tx_data

        self.logger = logging.getLogger('ControllableEntity[{}]'.format(self.__station_id))
        self.logger.setLevel(debug_level)

    def handle_message(self, wrapper, msg):
        """returns true if the message is handled"""
        self.logger.debug("Got message [{}]".format(wrapper.message_type))

        if wrapper.message_type == 1:
            self.logger.debug("Message is auth request.")
            return self.handle_auth_message(wrapper, msg)

        # filter out unnecessary invocations of outer message handler below by ensuring this entity is the intended recepient
        # of the message
        if msg.has_station_number_field and (msg.station_number != self.__station_id):
            return False
        
        # for messages that do not have station_number we have no choice but to invoke handler
        self.process_incoming_message(wrapper, msg)

        return True

    def set_callback_for_unhandled_messages(self, callback):
        """for any messages we cannot process in this class"""
        self.__callback_unhandled_messages = callback

    def process_incoming_message(self, wrapper, msg):
        """invokes the __callback_unhandled_messages if it's not None"""
        if self.__callback_unhandled_messages is not None:
            try:
                self.logger.debug("Inovking unhandled message handler [{}]".format(wrapper.message_type))
                self.__loop.call_soon(self.__callback_unhandled_messages, wrapper, msg)
            except:
                self.logger.error("Unhandled error: [{}]".format(sys.exc_info()[0]))

    def handle_auth_message(self, wrapper, msg):
    
        if  (msg.vehicle_id & Message01.BROADCAST_ID) == Message01.BROADCAST_ID and \
            (msg.vsm_id & Message01.BROADCAST_ID) == Message01.BROADCAST_ID and \
            (msg.controlled_station & Message01.BROADCAST_ID) == Message01.BROADCAST_ID:
            self.logger.debug("Message is of type discovery")
            self.handle_broadcast(wrapper, msg)
            return False # to let the chain continue to be called at caller end

        elif msg.vehicle_id == self.__vehicle_id:
            self.logger.debug("Message is of type LOI request")
            self.handle_loi_request(wrapper, msg)
            return True

        return False

    def handle_broadcast(self, wrapper, msg):
        
        self.logger.debug("Handling discovery request")

        self.respond_21(wrapper, msg)

        if self.__station_id == 0x0: #base platform
            self.respond_20(wrapper, msg)

        self.respond_300(wrapper, msg)

    def respond_20(self, wrapper, msg):
        self.logger.debug("Responding with Message 20")

        msg20 = Message20(Message20.MSGNULL)

        msg20.time_stamp = 0x00
        msg20.vehicle_id = self.__vehicle_id
        msg20.cucs_id = msg.cucs_id
        msg20.vsm_id = self.__vsm_id
        msg20.vehicle_id_update = 0x0
        msg20.vehicle_type = self.__vehicle_type
        msg20.vehicle_sub_type = self.__vehicle_sub_type
        msg20.owning_id = 0x00 #todo be filled from some config in future
        msg20.set_tail_number("1234") #todo be filled from some config in future
        msg20.set_mission_id("1234") #todo be filled from some config mission
        msg20.set_atc_call_sign("1234") #todo be filled from some config in future
        msg20.configuration_checksum = 0xABCD

        wrapped_reply = MessageWrapper(MessageWrapper.MSGNULL)
        wrapped_reply = wrapped_reply.wrap_message(wrapper.msg_instance_id, 20, msg20, False)

        self.__loop.call_soon(self.__callback_tx_data, wrapped_reply)


    def respond_21(self, wrapper, msg):
        self.logger.debug("Responding with Message 21")
        
        msg21 = Message21(Message21.MSGNULL)

        msg21.time_stamp = 0x00
        msg21.vehicle_id = self.__vehicle_id
        msg21.cucs_id = msg.cucs_id
        msg21.vsm_id = self.__vsm_id
        msg21.data_link_id = 0x0
        msg21.loi_authorized = self.get_loi_authorized(msg.cucs_id)
        msg21.loi_granted = self.get_loi_granted(msg.cucs_id)
        msg21.controlled_station = self.__station_id
        msg21.controlled_station_mode = 1 if ( (msg21.loi_granted & Message01.LOI_05) == Message01.LOI_05) else 0
        msg21.vehicle_type = self.__vehicle_type
        msg21.vehicle_sub_type = self.__vehicle_sub_type

        wrapped_reply = MessageWrapper(MessageWrapper.MSGNULL)
        wrapped_reply = wrapped_reply.wrap_message(wrapper.msg_instance_id, 21, msg21, False)

        self.__loop.call_soon(self.__callback_tx_data, wrapped_reply)

    def respond_300(self, wrapper, msg):

        """No 300 for BP"""
        if self.__station_id == 0: return

        self.logger.debug("Responding with Message 300")
        
        msg300 = Message300(Message300.MSGNULL)
        msg300.time_stamp = 0x00
        msg300.vehicle_id = self.__vehicle_id
        msg300.cucs_id = msg.cucs_id
        msg300.vsm_id = self.__vsm_id
        msg300.station_number = self.__station_id

        if self.__station_id == 0x0:
            msg300.payload_stations_available = self.__available_stations
            msg300.payload_type = Message300.STATION_TYPE_UNSPECIFIED
        else:
            msg300.payload_stations_available = 0x00
            msg300.payload_type = self.__payload_type
        
        msg300.station_door = 0x00
        msg300.number_of_payload_recording_devices = 0x00

        wrapped_reply = MessageWrapper(MessageWrapper.MSGNULL)
        wrapped_reply = wrapped_reply.wrap_message(wrapper.msg_instance_id, 300, msg300, False)

        self.__loop.call_soon(self.__callback_tx_data, wrapped_reply)

    def get_loi_granted(self, requesting_cucs_id):
        """Calculates and returns the loi_granted field value given a cucs_id"""
        
        granted_loi = 0
        
        if self.__controlling_cucs_id == requesting_cucs_id:
            granted_loi = Message01.LOI_05
        
        if requesting_cucs_id in self.__monitoring_cucs_list:
            """This is a repeat in case the previous statment is true since there is no control without monitoring"""
            granted_loi = (granted_loi or Message01.LOI_02)

        return granted_loi

    def get_loi_authorized(self, requesting_cucs_id):
        """Calculates and returns the loi_authorized field value given a cucs_id"""
        
        """By default everyone can monitor"""
        authorized_loi = Message01.LOI_02

        if self.__controlling_cucs_id in [0, requesting_cucs_id]:
            authorized_loi = (authorized_loi or Message01.LOI_05)
        
        return authorized_loi

    def set_available_stations(self, available_stations):
        self.__available_stations = available_stations
    
    def set_payload_type(self, __payload_type):
        self.__payload_type = __payload_type

    def is_control_bit_set(self, msg):

        CONTROL_LOI_BIT = Message01.LOI_03 if self.__station_id != 0 else Message01.LOI_05
        
        return (msg.requested_handover_loi & CONTROL_LOI_BIT) == CONTROL_LOI_BIT

    def is_monitor_bit_set(self, msg):

        return (msg.requested_handover_loi & Message01.LOI_02) == Message01.LOI_02

    def add_cucs_to_monitoring_list(self, msg):
        
        if msg.cucs_id not in self.__monitoring_cucs_list:
            self.__monitoring_cucs_list.append(msg.cucs_id)
            self.logger.debug("Cucs [{}] added to monitoring list.".format(msg.cucs_id))
        else:
            self.logger.debug("cucs_id already in monitoring list")

        self.logger.debug("Monitoring list is: [{}]".format(self.__monitoring_cucs_list))

    def remove_cucs_from_monitoring_list(self, msg):
        
        if msg.cucs_id in self.__monitoring_cucs_list:
            self.__monitoring_cucs_list.remove(msg.cucs_id)
            self.logger.debug("Cucs [{}] removed from monitoring list.".format(msg.cucs_id))
        else:
            self.logger.debug("cucs_id not present in monitoring list")

        self.logger.debug("Monitoring list is: [{}]".format(self.__monitoring_cucs_list))

    def handle_loi_request(self, wrapper, msg):
        self.logger.debug("Processing LOI request")
        
        if msg.controlled_station_mode == 0x01:
            """asking for something"""

            if self.is_monitor_bit_set(msg):
                """this is a request for monitor"""
                self.add_cucs_to_monitoring_list(msg)

            if self.is_control_bit_set(msg):
                if self.__controlling_cucs_id == 0:
                    self.__controlling_cucs_id = msg.cucs_id
                    self.logger.debug("Control granted to [{}]".format(msg.cucs_id))
                else:
                    self.logger.debug("Cannot grant control to [{}] as already controlled by [{}]".format(msg.cucs_id, self.__controlling_cucs_id))
                
        else:
            """letting go of something"""

            if self.is_monitor_bit_set(msg):
                """this is a request about monitor"""
                self.remove_cucs_from_monitoring_list(msg)

            if self.is_control_bit_set(msg):
                if self.__controlling_cucs_id == msg.cucs_id:
                    self.__controlling_cucs_id = 0
                    self.logger.debug("Control revoked from [{}]".format(msg.cucs_id))
                elif self.__controlling_cucs_id != 0:
                    self.logger.debug("Cannot remove control from [{}] as being controlled by [{}]".format(msg.cucs_id, self.__controlling_cucs_id))

        self.respond_21(wrapper, msg)

