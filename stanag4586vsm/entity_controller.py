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

    __vsm_id = 0x0
    __loop = None
    __callback_unhandled_messages = None

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
        self.__vsm_id = vsm_id
        self.__callback_tx_data = callback_tx_data

        self.logger = logging.getLogger('EntityController')
        self.logger.setLevel(debug_level)

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

    def handle_message(self, wrapper, msg):
        """examines incoming message and acts accordingly"""
        self.logger.debug("Got message [{}]".format(wrapper.message_type))

        if wrapper.message_type == 21:
            self.handle_message_21(wrapper, msg)
            self.logger.debug(self.__vehicles)

        elif wrapper.message_type == 300:
            self.handle_message_300(wrapper, msg)
    
        elif wrapper.message_type == 20:
            self.handle_message_20(wrapper, msg)


    def handle_message_20(self, wrapper, msg):

        if msg.vehicle_id not in self.__vehicles.keys():
            return

        vehicle_ref = self.__vehicles[msg.vehicle_id]
        vehicle_ref[self.KEY_META] = Message20(msg.encode())

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

                station_ref[self.KEY_TYPE] = msg.vehicle_type
                station_ref[self.KEY_SUB_TYPE] = msg.vehicle_sub_type
