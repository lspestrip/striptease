#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from argparse import ArgumentParser
import curses
import json
import time
from datetime import datetime
from pathlib import Path
import socket

import astropy
import telegram_send

from striptease import StripConnection, append_to_run_log

args = None
cur_json_procedure = []
DEFAULT_WAIT_TIME_S = 0.5


premature_quit = False
warnings = []


def warning(stdscr, msg):
    stdscr.addstr(msg + "\n", curses.color_pair(1))
    warnings.append(msg)
    stdscr.refresh()


def tagmsg(stdscr, msg):
    stdscr.addstr(msg + "\n", curses.color_pair(2))
    stdscr.refresh()


def logmsg(stdscr, msg):
    stdscr.addstr(msg + "\n", curses.color_pair(3))
    stdscr.refresh()


def commandmsg(stdscr, msg):
    stdscr.addstr(msg + "\n", curses.color_pair(4))
    stdscr.refresh()


def waitmsg(stdscr, msg):
    stdscr.addstr(msg + "\n", curses.color_pair(5))
    stdscr.refresh()


def prompt(stdscr, msg):
    stdscr.addstr(msg + "\n", curses.color_pair(6))
    stdscr.refresh()


def readkey(stdscr):
    stdscr.nodelay(False)
    choice = stdscr.getkey()
    stdscr.nodelay(True)
    return choice


def close_tags(stdscr, conn):
    tags = [x for x in conn.tag_query() if x["stop"] < 0.0]

    if not tags:
        return

    if args.close_tags:
        for cur_tag in tags:
            conn.tag_stop(
                cur_tag["tag"],
                comment="Closed automatically by program_batch_runner.py",
            )
    else:
        tags = ", ".join([('"' + x["tag"] + '"') for x in tags])
        warning(stdscr, f"The tags {tags} are still open, do you want to quit (y/n)?")
        choice = readkey(stdscr)
        if choice.upper() == "Y":
            return True

    return False


def send_message_to_telegram(args, message: str):
    if args.no_telegram or args.dry_run:
        return

    telegram_send.send(
        conf=args.telegram_conf, parse_mode="markdown", messages=[message]
    )


def main(stdscr):
    global args
    global cur_json_procedure
    global premature_quit

    curses.start_color()
    curses.use_default_colors()
    curses.cbreak()
    curses.noecho()

    # Warning
    curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLACK)

    # Tag message
    curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)

    # Log message
    curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)

    # Command message
    curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLACK)

    # Wait message
    curses.init_pair(5, curses.COLOR_BLUE, curses.COLOR_BLACK)

    # User prompt
    curses.init_pair(6, curses.COLOR_MAGENTA, curses.COLOR_BLACK)

    stdscr.scrollok(True)
    stdscr.idlok(True)
    stdscr.nodelay(True)  # Don't wait for keypresses
    stdscr.keypad(True)

    if not args.dry_run:
        print(f"{len(cur_json_procedure)} commands ready to be executed, let's go!")
        print("Going to establish a connection with the server…")
        conn = StripConnection()
        conn.login()
        if close_tags(stdscr, conn):
            return

        print("…connection established")

        if (not args.dry_run) and (not args.do_not_round):
            conn.round_all_files()
    else:
        conn = None

    open_tags = set([])
    indent_level = 0
    for cur_command in cur_json_procedure:
        cmddict = cur_command["command"]
        print_fn = None

        indent_level_incr = 0
        curpath = cur_command["path"]
        if cur_command["kind"] == "tag":
            print_fn = tagmsg
            if cmddict["type"] == "START":
                command_descr = f"start of tag {cmddict['tag']}"
                open_tags.add(cmddict["tag"])
                indent_level_incr = 4
            else:
                if not cmddict["tag"] in open_tags:
                    msg = f"Tag {cmddict['tag']} is being closed, but the tags currently open are {', '.join(open_tags)}"
                    warning(stdscr, msg)
                else:
                    open_tags.discard(cmddict["tag"])

                command_descr = f"end of tag {cmddict['tag']}"
                indent_level = -4

        elif cur_command["kind"] == "log":
            print_fn = logmsg
            command_descr = f"log message '{cmddict['message']}' ({cmddict['level']})"
        elif cur_command["kind"] == "command":
            print_fn = commandmsg
            method, base_addr, data = [
                cmddict[x] for x in ("method", "base_addr", "data")
            ]

            datastr = ", ".join([str(x) for x in data])
            command_descr = f"command {method} {base_addr}, data={datastr}"
        elif cur_command["kind"] == "wait":
            print_fn = waitmsg
            curpath = "/waitcmd"
            command_descr = f"wait for {cur_command['command']['wait_time_s']} s"
        else:
            warning(
                stdscr,
                f"\"{cur_command['kind']}\" is not recognized as a valid command type",
            )
            print_fn = prompt

        print_fn(stdscr, " " * indent_level + f"{curpath}: {command_descr}")

        try:
            if cur_command["kind"] != "wait":
                if not args.dry_run:
                    conn.post(cur_command["path"], message=cmddict)

                time.sleep(args.wait_time)
            else:
                wait_time = cmddict["wait_time_s"]
                if args.waitcmd_time is not None:
                    wait_time = args.waitcmd_time
                time.sleep(wait_time)
        except Exception as e:
            if cur_command["kind"] == "tag":
                warning(
                    stdscr, f"Error while submitting tag {cmddict['tag']}, ignoring it"
                )
            else:
                warning_msg = f"Error in \"{cur_command['kind']}\" command: {e}"
                warning(stdscr, warning_msg)

        indent_level += indent_level_incr
        if indent_level < 0:
            indent_level = 0

        # Check for keypresses
        key = stdscr.getch()
        if key != curses.ERR:
            if key in [ord(" "), ord("p")]:
                # Pause
                curses.flash()
                prompt(stdscr, "Paused, press any key to resume")
                stdscr.nodelay(False)
                stdscr.getch()
                stdscr.nodelay(True)
            elif key == ord("q"):
                # Quit
                curses.flash()
                prompt(stdscr, "Are you sure you want to quit? (y/n)")
                choice = readkey(stdscr)
                if choice.upper() == "Y":
                    premature_quit = True
                    break
            elif key == ord("l"):
                # Log message
                curses.flash()
                prompt(stdscr, "Enter a log message:")
                stdscr.nodelay(False)
                curses.echo()
                msg = stdscr.getstr()
                curses.noecho()
                stdscr.nodelay(True)

                if not args.dry_run:
                    conn.log(message=msg)

                logmsg(stdscr, f'Custom log message "{msg}" sent to the server')

    if args.wait_at_end:
        prompt(stdscr, "Execution completed, press a key to exit")
        readkey(stdscr)

    if not args.dry_run:
        if conn and (not args.do_not_round):
            conn.round_all_files()

        conn.logout()

    if warnings:
        print("Here are the warning messages produced during the execution:")
        for msg in warnings:
            print(msg)


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Run a STRIP test procedure.",
        epilog="""
You can pause the execution with the keys SPACE or "p".
Pressing "l" allows the user to enter a log message.
Pressing "q" will halt the execution.
""",
    )
    parser.add_argument(
        "--wait-at-end",
        default=False,
        action="store_true",
        help="Wait a key before ending the procedure",
    )
    parser.add_argument(
        "--wait-time",
        metavar="SECONDS",
        type=float,
        default=DEFAULT_WAIT_TIME_S,
        help=f"""
Specify the amount of time to wait before running the
next command. Default is {DEFAULT_WAIT_TIME_S}
""",
    )
    parser.add_argument(
        "--waitcmd-time",
        metavar="SECONDS",
        type=float,
        default=None,
        help="Override the duration of wait commands in the script",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Do not send any command to the server",
    )
    parser.add_argument(
        "--close-tags",
        action="store_true",
        default=False,
        help="Automatically close any tag that is open before the script starts running",
    )
    parser.add_argument(
        "json_files",
        metavar="JSON_FILE",
        type=str,
        nargs="+",
        help="Name of the JSON files containing the test procedures. More "
        "than one file can be provided. If no files are provided, the JSON record "
        "will be read from the terminal.",
    )
    parser.add_argument(
        "--do-not-round",
        action="store_false",
        default=True,
        help="Avoid closing HDF5 files before and after the execution of the "
        "script. (Default is forcing the server to keep all the data acquired "
        "during the procedure in one HDF file.)",
    )
    parser.add_argument(
        "--telegram-conf",
        metavar="FILE",
        type=str,
        nargs="+",
        default=None,
        help="Path to the configuration file used by telegram-send to send "
        "messages to a Telegram chat or group. You can use this switch more "
        "than once and send the same message to multiple chats/groups.",
    )
    parser.add_argument(
        "--no-telegram",
        action="store_true",
        default=False,
        help="Avoid sending messages to Telegram using telegram-send (see also "
        "the switch --telegram-conf)",
    )

    args = parser.parse_args()

    for cur_file in args.json_files:
        cur_file = Path(cur_file)
        with cur_file.open("rt") as fp:
            cur_json_procedure = json.load(fp)

        start_time = datetime.now()
        send_message_to_telegram(
            args,
            (
                "Starting a new acquisition on `{host}`, commands are read from `{cur_file}` "
                "({num_of_commands} commands). The system date is {datetime} (MJD: {mjd})"
            ).format(
                host=socket.gethostname(),
                cur_file=cur_file.absolute(),
                num_of_commands=len(cur_json_procedure),
                datetime=start_time,
                mjd=astropy.time.Time(start_time).mjd,
            ),
        )

        curses.wrapper(main)
        end_time = datetime.now()

        if premature_quit:
            end_message = (
                "The acquisition for `{name}` on `{hostname}` was "
                "*interrupted by the user* after {time}. The MJD range "
                "is {mjd_start}–{mjd_end}."
            )

        else:
            end_message = (
                "The acquisition for `{name}` on `{hostname}` was *completed*, "
                "and it took {time} to complete. The MJD range "
                "is {mjd_start}–{mjd_end}."
            )

        end_message = end_message.format(
            name=cur_file.name,
            hostname=socket.gethostname(),
            time=end_time - start_time,
            mjd_start=astropy.time.Time(start_time).mjd,
            mjd_end=astropy.time.Time(end_time).mjd,
        )

        send_message_to_telegram(args, end_message)
        print(end_message)

        if not args.dry_run:
            append_to_run_log(
                start_time=start_time,
                end_time=end_time,
                wait_time_s=args.wait_time,
                wait_cmd_time_s=args.waitcmd_time,
                full_path=str(Path(cur_file).absolute()),
                procedure=cur_json_procedure,
            )
