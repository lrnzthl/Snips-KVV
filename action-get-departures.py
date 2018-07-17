#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys
sys.path.append("venv/local/bin")

import ConfigParser
import kvvliveapi as kvv
from datetime import datetime
from hermes_python.hermes import Hermes
from hermes_python.ontology import *
import io
import math

CONFIGURATION_ENCODING_FORMAT = "utf-8"
CONFIG_INI = "config.ini"

class SnipsConfigParser(ConfigParser.SafeConfigParser):
    def to_dict(self):
        return {section : {option_name : option for option_name, option in self.items(section)} for section in self.sections()}


def read_configuration_file(configuration_file):
    try:
        with io.open(configuration_file, encoding=CONFIGURATION_ENCODING_FORMAT) as f:
            conf_parser = SnipsConfigParser()
            conf_parser.readfp(f)
            return conf_parser.to_dict()
    except (IOError, ConfigParser.Error) as e:
        return dict()

def subscribe_intent_callback(hermes, intentMessage):
    conf = read_configuration_file(CONFIG_INI)
    action_wrapper(hermes, intentMessage, conf)


def action_wrapper(hermes, intentMessage, conf):
    """ Write the body of the function that will be executed once the intent is recognized.
    In your scope, you have the following objects :
    - intentMessage : an object that represents the recognized intent
    - hermes : an object with methods to communicate with the MQTT bus following the hermes protocol.
    - conf : a dictionary that holds the skills parameters you defined
    Refer to the documentation for further details.
    """
    station_name = str(intentMessage.slots.station_name.first().value)
    station_id = 'de:8212:3013'
    if station_name.lower() is not "büchig":
        search_result = kvv.search_by_name(station_name)
        station_id = search_result[0].stop_id.encode("utf8")
        station_name = search_result[0].name.encode("utf8")

    next_departures = kvv.get_departures(station_id, 4)
    
    result_sentence = ""

    if len(next_departures) is 0:
        result_sentence += "Es wurden keine Abfahrten für {} gefunden.".format(station_name)
    else:
        result_sentence += "Die nächsten Abfahrten ab {} sind: ".format(station_name)
        for dep in next_departures:
            time_delta = math.floor(((dep.time - datetime.now()).total_seconds() / 60))
            temp_sentence = ""
            if time_delta > 0:
                temp_sentence = "Linie {} in {} Minuten in Richtung {}. ".format(dep.route.encode("utf8"), str(time_delta).split('.')[0], dep.destination.encode("utf8"))
            else:
                temp_sentence = "Linie {} fährt jetzt in Richtung {}. ".format(dep.route.encode("utf8"), dep.destination.encode("utf8"))
            result_sentence += temp_sentence

    current_session_id = intentMessage.session_id
    hermes.publish_end_session(current_session_id, result_sentence)

if __name__ == "__main__":
    with Hermes("localhost:1883") as h:
        h.subscribe_intent("simfire:getKVVNextDepartures", subscribe_intent_callback) \
.start()
