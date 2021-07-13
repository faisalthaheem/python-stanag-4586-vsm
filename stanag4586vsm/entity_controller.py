from enum import auto
import logging
import sys
import copy

from stanag4586edav1.message_wrapper import *
from stanag4586edav1.message01 import *
from stanag4586edav1.message20 import *
from stanag4586edav1.message21 import *
from stanag4586edav1.message300 import *


class EntityController:
    """CUCS end utility to manage incoming responses for vehicles"""

    KEY_META = 0
    KEY_STATIONS = 1
    KEY_CONTROLLED = 2
    KEY_MONITORED = 3
    KEY_TYPE = 4
    KEY_SUB_TYPE = 5
    KEY_TAIL_NUMBER = 6
    KEY_MISSION_ID = 7
    KEY_CALL_SIGN = 8

    __cucs_id = 0x0
    __vsm_id = 0x0
    __loop = None
    __callback_unhandled_messages = None
    __callback_vehicle_discovery = None

    # __vehicles contains the list of discovered platfomrs on the network, the format
    # of this structure is as follows
    # {
    #   vehicle_id : {
    #       KEY_CONTROLLED: Boolean
    #       KEY_MONITORED : Boolean
    #       KEY_TYPE: int
    #       KEY_SUB_TYPE: int
    #       KEY_META : {} message 20 contents
    #       KEY_STATIONS : {
    #           station_id: {
    #               KEY_CONTROLLED: Boolean
    #               KEY_MONITORED : Boolean  
    #               KEY_TYPE: int
    #           }
    #       }
    #   }
    # }
    __vehicles = {}
    

    def __init__(self, loop, debug_level, cucs_id, vsm_id, callback_tx_data):
        self.__loop = loop
        self.__cucs_id = cucs_id
        self.__vsm_id = vsm_id
        self.__callback_tx_data = callback_tx_data

        self.logger = logging.getLogger('EntityController')
        self.logger.setLevel(debug_level)


    def get_discovered_vehicles(self):
        """Getter that returns a copy of __vehicles field"""
        return copy.copy(self.__vehicles)

    def set_callback_for_unhandled_messages(self, callback):
        """for any messages we cannot process in this class"""
        self.__callback_unhandled_messages = callback

    def __invoke_handler_unhandled_msgs(self, wrapper, msg):
        """invokes the handler if it's not None"""

        if self.__callback_unhandled_messages is not None:
            try:
                self.logger.debug("Inovking handler for msg [{}]".format(wrapper.message_type))
                self.__loop.call_soon(self.__callback_unhandled_messages, wrapper, msg)
            except:
                self.logger.error("Unhandled error: [{}]".format(sys.exc_info()[0]))

    def set_callback_for_vehicle_discovery(self, callback):
        """invoked after a vehicle discovery or change in LOI"""
        self.__callback_vehicle_discovery = callback

    def __invoke_handler_vehicle_discovery(self):
        """invokes the handler if it's not None"""

        if self.__callback_vehicle_discovery is not None:
            try:
                self.logger.debug("Inovking handler for vehicle discovery")
                self.__loop.call_soon(self.__callback_vehicle_discovery, self, copy.copy(self.__vehicles))
            except:
                self.logger.error("Unhandled error: [{}]".format(sys.exc_info()[0]))


    def handle_message(self, wrapper, msg):
        """examines incoming message and acts accordingly"""
        self.logger.debug("Got message [{}]".format(wrapper.message_type))

        handled = False

        if wrapper.message_type == 21:
            self.handle_message_21(wrapper, msg)
            handled = True

        elif wrapper.message_type == 20:
            self.handle_message_20(wrapper, msg)
            handled = True

        elif wrapper.message_type == 300:
            self.handle_message_300(wrapper, msg)
            handled = True
        
        if handled:
            self.logger.debug(self.__vehicles)
            #raise event for ugv discovery
            self.__invoke_handler_vehicle_discovery()
        else:
            self.__invoke_handler_unhandled_msgs(wrapper, msg)

    def handle_message_20(self, wrapper, msg):

        if msg.vehicle_id not in self.__vehicles.keys():
            return

        vehicle_ref = self.__vehicles[msg.vehicle_id]
        vehicle_ref[self.KEY_META] = {}
        vehicle_ref[self.KEY_META][self.KEY_CALL_SIGN] = msg.get_atc_call_sign()
        vehicle_ref[self.KEY_META][self.KEY_MISSION_ID] = msg.get_mission_id()
        vehicle_ref[self.KEY_META][self.KEY_TAIL_NUMBER] = msg.get_tail_number()

    def handle_message_300(self, wrapper, msg):

        if msg.vehicle_id not in self.__vehicles.keys():
            return

        vehicle_ref = self.__vehicles[msg.vehicle_id]

        if msg.station_number not in vehicle_ref[self.KEY_STATIONS].keys():
            vehicle_ref[self.KEY_STATIONS][msg.station_number] = {
                self.KEY_CONTROLLED: False,
                self.KEY_MONITORED: False,
                self.KEY_TYPE: msg.payload_type
            }
        else:
            station_ref = vehicle_ref[self.KEY_STATIONS][msg.station_number]
            station_ref[self.KEY_TYPE] =  msg.payload_type


    def handle_message_21(self, wrapper, msg):
        
        vehicle_ref = None
        if msg.vehicle_id not in self.__vehicles.keys():
            self.__vehicles[msg.vehicle_id] = {
                self.KEY_CONTROLLED: False,
                self.KEY_MONITORED: False,
                self.KEY_META: None,
                self.KEY_STATIONS: {}
            }
        
        vehicle_ref = self.__vehicles[msg.vehicle_id]

        if msg.controlled_station == 0:          
            
            if msg.controlled_station_mode == Message21.CONTROLLED_STATION_MODE_IN_CONTROL:
                vehicle_ref[self.KEY_CONTROLLED] = True
                vehicle_ref[self.KEY_MONITORED] = True
            else:
                vehicle_ref[self.KEY_CONTROLLED] = False
                vehicle_ref[self.KEY_MONITORED] = True if ( (msg.loi_granted & Message01.LOI_02) == Message01.LOI_02) else False

            vehicle_ref[self.KEY_TYPE] = msg.vehicle_type
            vehicle_ref[self.KEY_SUB_TYPE] = msg.vehicle_sub_type
        
        else:

            """Stations are populated on message 300 only, we skip if at least once 300 has not been processed"""
            if msg.controlled_station in vehicle_ref[self.KEY_STATIONS].keys():
                station_ref = vehicle_ref[self.KEY_STATIONS][msg.controlled_station]

                if msg.controlled_station_mode == Message21.CONTROLLED_STATION_MODE_IN_CONTROL:
                    station_ref[self.KEY_CONTROLLED] = True
                    station_ref[self.KEY_MONITORED] = True
                else:
                    station_ref[self.KEY_CONTROLLED] = False
                    station_ref[self.KEY_MONITORED] = True if ( (msg.loi_granted & Message01.LOI_02) == Message01.LOI_02) else False


    def __tx_msg(self, msg_type, msg):

        if self.__callback_tx_data is None:
            self.logger.warn("self.__callback_tx_data is none, unable to tx data")
            return

        wrapper = MessageWrapper(MessageWrapper.MSGNULL)
        wrapped_msg = wrapper.wrap_message(1, msg_type, msg, False)

        self.__loop.call_soon(self.__callback_tx_data, wrapped_msg)

    def __create_msg_01(self, station_id, vehicle_id):
        
        msg01 = Message01(Message01.MSGNULL)
        msg01.time_stamp = 0x00
        msg01.vehicle_id = vehicle_id
        msg01.cucs_id = self.__cucs_id
        msg01.vsm_id = self.__vsm_id
        msg01.data_link_id = 0x00
        msg01.vehicle_type = 0x00
        msg01.vehicle_sub_type = 0x00
        msg01.controlled_station = station_id
        msg01.wait_for_vehicle_data_link_transition_coordination_message = 0x00

        return msg01

    def control_request(self, station_id, vehicle_id):
        
        msg01 = self.__create_msg_01(station_id, vehicle_id)
        
        msg01.requested_handover_loi = Message01.LOI_05
        msg01.controlled_station_mode = 0x01

        self.__tx_msg(1, msg01)

    def control_release(self, station_id, vehicle_id):

        msg01 = self.__create_msg_01(station_id, vehicle_id)
        
        msg01.requested_handover_loi = Message01.LOI_05
        msg01.controlled_station_mode = 0x00

        self.__tx_msg(1, msg01)

    def monitor_request(self, station_id, vehicle_id):
        msg01 = self.__create_msg_01(station_id, vehicle_id)
        
        msg01.requested_handover_loi = Message01.LOI_01
        msg01.controlled_station_mode = 0x01

        self.__tx_msg(1, msg01)

    def monitor_release(self, station_id, vehicle_id):
        msg01 = self.__create_msg_01(station_id, vehicle_id)
        
        msg01.requested_handover_loi = Message01.LOI_01
        msg01.controlled_station_mode = 0x00

        self.__tx_msg(1, msg01)