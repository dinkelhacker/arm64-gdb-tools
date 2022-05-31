"""Arm64 gdb tools utility module."""
import logging
logger = logging.getLogger("vmmap")

colors = {
    "HEADER" : '\033[95m',
    "OKBLUE" : '\033[94m',
    "OKGREEN" : '\033[92m',
    "WARNING" : '\033[93m',
    "FAIL" : '\033[91m',
    "ENDC" : '\033[0m',
    "BOLD" : '\033[1m',
    "BRIGHT" : '\033[97m',
    "UNDERLINE" : '\033[4m',
}


def format_hex(i):
    """ Print hex in a eye-friendly way. """

    s = "0x"+hex(i)[2:].zfill(16)
    i = 2
    while i <= len(s) - 2:
        if s[i] != "0":
            break
        i+=1

    return s[:i] + format_bold(s[i:])

def format_bold(s):
    """ Make String bold. """

    return colors["BOLD"] + s + colors["ENDC"]

def format_highlight(s):
    """ Highlight text (green). """

    return colors["OKGREEN"] + s + colors["ENDC"]

def parse_hex(s):
    """ Try to parse hex string. Raise `SystemExit` exception on error. """

    try:
        v = int(s, 16)
        return v
    except (ValueError, TypeError) as error:
        logger.debug(error)
        print("{hs} is not valid. Expecting hex string.".format(hs=s))
        raise SystemExit
