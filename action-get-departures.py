#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys
sys.path.append("venv/local/bin")

import ConfigParser
import kvvliveapi as kvv
import difflib
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


def _generate_result_sentence(departures, station_name):
    result_sentence = ''

    if len(departures) is 0:
        result_sentence += "Es wurden keine Abfahrten für {} gefunden.".format(station_name)
    else:
        result_sentence += "Die nächsten Abfahrten ab {} sind: ".format(station_name)
        for departure in departures:
            time_delta = math.floor(((departure.time - datetime.now()).total_seconds() / 60))
            if time_delta > 0:
                temp_sentence = "Linie {} in {} Minuten in Richtung {}. ".format(departure.route.encode("utf8"),
                                                                                 str(time_delta).split('.')[0],
                                                                                 departure.destination.encode("utf8"))
            else:
                temp_sentence = "Linie {} fährt jetzt in Richtung {}. ".format(departure.route.encode("utf8"),
                                                                               departure.destination.encode("utf8"))
            result_sentence += temp_sentence
    return result_sentence


def _search_for_station_id(station_name):
    result_id = -1
    result_list = kvv.search_by_name(station_name)
    name_list = [x.name.encode("utf8") for x in result_list]
    if "karlsruhe" not in station_name.lower():
        station_name = "Karlsruhe " + station_name
    result = difflib.get_close_matches(station_name, name_list, 1)
    if len(result) > 0:
        result_station_name = result[0]
        result_id = [[x.stop_id for x in result_list if x.name.encode("utf8") == result_station_name][0], result_station_name]
    else:
        if len(result_list) > 0:
            result_id = result_list[0].stop_id
    return result_id


def action_wrapper(hermes, intentMessage, conf):
    """ Write the body of the function that will be executed once the intent is recognized.
    In your scope, you have the following objects :
    - intentMessage : an object that represents the recognized intent
    - hermes : an object with methods to communicate with the MQTT bus following the hermes protocol.
    - conf : a dictionary that holds the skills parameters you defined
    Refer to the documentation for further details.
    """

    default_station_name = conf['secret']['default_station']
    station_name = "Karlsruhe Hbf Vorplatz"

    if default_station_name:
        station_name = default_station_name

    try:
        station_name = str(intentMessage.slots.station_name.first().value)
    except:
        pass

    next_departures = []
    search_result = _search_for_station_id(station_name)

    if search_result is not -1:
        station_name, station_id = search_result
        next_departures = kvv.get_departures(station_id, 4)

    current_session_id = intentMessage.session_id
    hermes.publish_end_session(current_session_id, _generate_result_sentence(next_departures, station_name))


if __name__ == "__main__":
    with Hermes("localhost:1883") as h:
        h.subscribe_intent("simfire:getKVVNextDepartures", subscribe_intent_callback) \
.start()
