# -*- encoding: utf-8 -*-

from collections import namedtuple
import re

import numpy as np

import astropy.time
import astropy.units as u

TagEvent = namedtuple("TagEvent", ["start_time", "end_time", "tag", "polarimeter"])


def script_to_tagevents(script_dict, command_delay_s=0.5):
    assert type(script_dict) == list

    result = []
    pol_regexp = re.compile("[IGBVROYW][0-6]")

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

                # Try to extract a valid polarimeter name from the tag
                match = pol_regexp.search(current_tag_name)
                if match:
                    current_polarimeter = match.group(0)
                else:
                    current_polarimeter = None

                result.append(
                    TagEvent(
                        start_time=current_tag_start_time,
                        end_time=current_time,
                        tag=current_tag_name,
                        polarimeter=current_polarimeter,
                    )
                )
                current_tag_name = None

        elif event_kind == "wait":
            current_time += event["command"]["wait_time_s"]
        else:
            current_time += command_delay_s

    return result


def plot_tagevents(
    tagevent_list,
    ax,
    polarimeters,
    colors,
    global_line=True,
    foreground_color="#808080",
    edge_color="#000000",
    timeticks=None,
    timelabels=None,
    timeformatter=None,
):
    """Draw a timetable of turnon times for a list of polarimeters.
    
    Arguments:
      - `tagevent_list`: a list of objects of type ``TagEvent``, typically
                         created using `striptease.script_to_tagevents`
      - `ax`: a matplotlib.Axis object, already configured
      - `polarimeters`: a list of strings identifying the
                        polarimeters. Pass `None` if you want to
                        include every polarimeter appearing in
                        `tagevent_list`
      - `colors`: a dictionary associating polarimeter names with RGB colors
      
    Optional keywords:

      - `global_line`: include one row for global events, not belonging to
                       any polarimeter
      - `foreground_color`: default color to be used for rectangles
      - `edge_color`: the color used to draw the edge of rectangles
      - `timeticks`: list of ticks along the x axis (MJD)
      - `timelabels`: list of tick labels along the x axis (strings)
      - `timeformatter`: function that produces a tick label (string)
                         from a time (MJD). Used if `timelabels` is not provided
    Example:
    
    ```python
    import matplotlib.pylab
    fig, ax = matplotlib.pylab.subplots(1)

    with open("G0_turnon.json", "rt") as f:
        import json
        events = striptease.script_to_tagevents(json.load(f))

    striptease.turnon_time_table(events, ax, ["G0"], {"G0": "#a0a0a0"})
    ```

    """

    # Use these imports only if this function is actually called,
    # otherwise it will import "tkinter", and this might lead to
    # nasty effects on headless servers
    import matplotlib.pylab as plt
    from matplotlib.patches import Rectangle
    from matplotlib.collections import PatchCollection
    import matplotlib.transforms as transforms

    if polarimeters:
        true_pol_list = polarimeters
    else:
        # Using "set", we throw away duplicates
        true_pol_list = sorted(
            list(set([x.polarimeter for x in tagevent_list if x.polarimeter]))
        )

    if global_line:
        true_pol_list = [None] + true_pol_list

    # This dictionary is used to associate the name of a polarimeter
    # to the row it belongs. It works with None too!
    #
    # If true_pol_list = [None, "G0", G1"], then
    #
    #     pol_to_row[None] = 0
    #     pol_to_row["G0"] = 1
    #     pol_to_row["G1"] = 2

    pol_to_row = {}
    for idx, pol in enumerate(true_pol_list):
        pol_to_row[pol] = idx

    # Used to scale the x axis of the plot
    minlim, maxlim = tagevent_list[0].start_time, tagevent_list[-1].end_time

    for cur_event in tagevent_list:
        try:
            cur_color = colors[cur_event.polarimeter]
        except KeyError:
            cur_color = foreground_color

        cur_rect = Rectangle(
            xy=(cur_event.start_time, pol_to_row[cur_event.polarimeter] + 0.2),
            width=(cur_event.end_time - cur_event.start_time),
            height=0.6,
            facecolor=cur_color,
            edgecolor=edge_color,
        )
        ax.add_patch(cur_rect)

    ax.set_xlim(minlim, maxlim)
    ax.set_ylim(0, len(true_pol_list))

    if timeticks:
        ax.set_xticks(timeticks)
        if timelabels:
            ax.set_xticklabels(timelabels)
        elif timeformatter:
            ax.set_xticklabels([timeformatter(x) for x in timeticks])

    ax.set_yticks(np.arange(len(true_pol_list)) + 0.5)
    ax.set_yticklabels(true_pol_list)

    return ax
