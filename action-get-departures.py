#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import ConfigParser
import kvvliveapi as kvv
import math
from datetime import datetime
from kvvliveapi import Depatures
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
    station_name = str(intentMessage.slots.firstTerm.first().value)
    if not station_name:
        station_name = "Büchig"
    station_id = 'de:8212:3013'
    next_departures = kvv.get_departures(station_id, 4)

    result_sentence = "Die nächsten Abfahrten ab {} sind: ".format(station_name)

    for dep in next_departures:
        time_delta = math.floor(((dep.time - datetime.now()).total_seconds() / 60))
        if time_delta > 0:
            temp_sentence = "{} in {} Minuten in Richtung {}. ".format(dep.route, time_delta, dep.destination)
        else:
            temp_sentence = "{} jetzt in Richtung {}. ".format(dep.route, dep.destination)
        result_sentence += temp_sentence

    current_session_id = intentMessage.session_id
    hermes.publish_end_session(current_session_id, result_sentence)


if __name__ == "__main__":
    with Hermes("localhost:1883") as h:
        h.subscribe_intent("simfire:getKVVNextDepartures", subscribe_intent_callback) \
.start()