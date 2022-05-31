import gdb
import argparse
import logging

logger = logging.getLogger("vmmap")

import ttable
from utils import *



class VMMAP(gdb.Command):
    """Print current MMU address mapping."""

    def __init__ (self):
        super (VMMAP, self).__init__ ("vmmap", gdb.COMMAND_USER)
        self.isInit = False
        self.mair = None
        self.entry = None
        self.entry_arg = None

        self.parser = argparse.ArgumentParser(description='Inspect MMU translation table.')
        showgrp = self.parser.add_mutually_exclusive_group()

        self.parser.add_argument('-tb', '--ttbr',
                                    help='First level translation table base address.')
        self.parser.add_argument('-m', '--mair',
                                    help='Value stored in MAIR register.')
        self.parser.add_argument('-v', '--verbose', action='store_true',
                                    help='Print debug statements.')
        self.parser.add_argument('-ph', '--print_hierarchy', action='store_true',
                                    help='Print hierarchical information.')
        showgrp.add_argument('-pa', '--print_all', action='store_true',
                                    help='Print all mappings.')
        showgrp.add_argument('-a', '--addr',
                                    help='Print mapping at address.')
        showgrp.add_argument('-s', '--symbol',
                                    help='Print mapping of symbol.')
        self.parser.add_argument('-c', '--clear', action='store_true',
                                    help='Clear cached values.')
        self.parser.add_argument('-tvo', '--tvirt_offset',
                                    help='Sets virtual address offset of next level table addresses.')
        self.parser.add_argument('-lvl', '--level', type=int, choices=range(0,2), default=0,
                                    help='Specifies the table lvl at which the translation starts. Default is 0.')


    def invoke (self, arg, from_tty):
        args = gdb.string_to_argv(arg)
        try:
            pargs = self.parser.parse_args(args)

            if (pargs.verbose):
                logging.basicConfig(level=logging.DEBUG)

            if (pargs.mair):
                self.mair = parse_hex(pargs.mair)

            if (pargs.tvirt_offset):
                ttable.VM_OFFSET = parse_hex(pargs.tvirt_offset)

            if (pargs.ttbr):
                if (self.entry_arg != pargs.ttbr or pargs.clear == True):
                    self.entry_arg = pargs.ttbr

                    if(pargs.ttbr[:2] == '0x'):
                        entry_addr = parse_hex(pargs.ttbr)
                        self.entry = entry_addr
                    else:
                        self.entry = int(gdb.parse_and_eval(pargs.ttbr).address)

                    self.isInit = False
                else:
                    print("[INFO] `{table}` was also used in last invocation. "
                    "Using cached values. Use -c to force recomputation.\n"
                    .format(table = pargs.ttbr))


            if (self.isInit == False):
                if (self.mair is None):
                    print("MAIR not given. Memory attributes won't be decoded...")
                else:
                    print("MAIR: {mair}".format(mair = format_hex(self.mair)))

                if (self.entry is None):
                    print("No entry lvl table specified.\n"
                    "You have to pass the name  or the address of the first translation table. \n"
                    "Hint: Subsquent calls will use last specified value and don't need to pass "
                    "it again.\n")
                    return
                else:
                    print("Reading translation table from memory...")
                    print("First lvl Table: " + self.entry_arg)

                lvlidx = [0,0,0,0]
                self.table = ttable.parse_descriptor(
                        self.entry, lvlidx, pargs.level - 1 , None, True)
                self.isInit = True

            if (pargs.addr):
                self.print_mapping_at(pargs.addr)
            elif (pargs.symbol):
                try:
                    sym = str(gdb.parse_and_eval(pargs.symbol)).split(" ")[0]
                except gdb.error as error:
                    print(error)
                    raise SystemExit

                logger.debug("Parsed expression:")
                logger.debug(sym)
                self.print_mapping_at(str(sym))
            else:
                self.table.print_(
                        self.mair,
                        True if pargs.print_all == True else False,
                        True if pargs.print_hierarchy == True else False)

        # Catch SystemExit here so errors won't close active gdb session
        except SystemExit:
            pass

    def print_mapping_at(self, in_addr):
            addr = parse_hex(in_addr)
            mapping = self.table.find(addr)

            if (isinstance(mapping, ttable.Block)):
                parents = mapping.parent.get_parents()
                parents.reverse()

                for p in parents:
                    print(p.to_str())

                mapping.print_(self.mair)
            else:
                print("No mapping!")

