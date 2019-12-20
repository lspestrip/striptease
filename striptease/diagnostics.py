# -*- encoding: utf-8 -*-

from collections import namedtuple

TagEvent = namedtuple("TagEvent", ["start_time", "end_time", "tag"])


def script_to_tagevents(script_dict, command_delay_s=0.5):
    assert type(script_dict) == list

    result = []

    current_tag_name = None
    current_tag_start_time = None
    current_time = 0.0
    for event in script_dict:
        event_kind = event["kind"]
        if event_kind == "tag":
            command = event["command"]
            if not current_tag_name:
                assert command["type"] == "START"
                current_tag_name = command["tag"]
                current_tag_start_time = current_time
            else:
                assert command["type"] == "STOP"
                assert command["tag"] == current_tag_name
                current_end_time = current_time
                result.append(
                    TagEvent(
                        start_time=current_tag_start_time,
                        end_time=current_time,
                        tag=current_tag_name,
                    )
                )
                current_tag_name = None

        elif event_kind == "wait":
            current_time += event["command"]["wait_time_s"]
        else:
            current_time += command_delay_s

    return result


def plot_tagevents(tagevent_list):
    pass
