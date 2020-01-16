#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from argparse import ArgumentParser
import curses
import json
import time
import sys

from striptease import StripConnection

args = None
DEFAULT_WAIT_TIME_S = 0.5


def warning(stdscr, msg):
    stdscr.addstr(msg + "\n", curses.color_pair(1))
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
        tags = ", ".join([f"\"{x['tag']}\"" for x in tags])
        warning(stdscr, f"The tags {tags} are still open, do you want to quit (y/n)?")
        choice = readkey(stdscr)
        if choice.upper() == "Y":
            return True

    return False


def main(stdscr):
    global args

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

    commands = []
    for cur_file in args.json_files:
        with open(cur_file, "rt") as fp:
            commands += json.load(fp)

    if not args.dry_run:
        print(f"{len(commands)} commands ready to be executed, let's go!")
        print("Going to establish a connection with the server…")
        conn = StripConnection()
        conn.login()
        if close_tags(stdscr, conn):
            return

        print("…connection established")
    else:
        conn = None

    open_tags = set([])
    indent_level = 0
    for cur_command in commands:
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
                    warning(
                        f"Tag {cmddict['tag']} is being closed, but the tags currently open are {', '.join(open_tags)}"
                    )
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
                warning(stdscr, f"Error in \"{cur_command['kind']}\" command: {e}")
                prompt(stdscr, "Press q to quit, any other key to continue")
                choice = readkey(stdscr)
                if choice.upper() == "Q":
                    return

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
                    conn.post("/rest/log", message={"level": "INFO", "message": msg})

                logmsg(stdscr, f'Custom log message "{msg}" sent to the server')

    prompt(stdscr, "Execution completed, press a key to exit")
    readkey(stdscr)
    if not args.dry_run:
        conn.logout()


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

    args = parser.parse_args()

    curses.wrapper(main)
