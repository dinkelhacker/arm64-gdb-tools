import struct
import logging
import gdb
logger = logging.getLogger("vmmap")

from utils import format_highlight, format_hex

INDENT = "  "
TABLE_MASK = 0x3
ATTR_MASK = 0x000FFFFFFFFFF000
VM_OFFSET = 0x0
_1GB = 0x40000000
_512GB = 512 * _1GB
_2MB = 0x200000
_4K = 0x1000


# Refer to ARMv8 ARM section:
# `D4.3.3 Memory attribute fields in the VMSAv8-64 translation table format descriptors`
table_attr_mask = {
    "NSTable" : 0x8000000000000000,
    "APTable" : 0x6000000000000000,
    "UXN" :     0x1000000000000000,
    "PXN" :     0x800000000000000,
}

page_attr_mask = {
    "UXN" :       0x40000000000000,
    "PXN" :       0x20000000000000,
    "SH" :        0x300,
    "AF" :        0x400,
    "AP" :        0xC0,
    "NS" :        0x20,
    "ATTRIDX" :   0x1c,
}

class TableEntry:
    """ Everything is a Table entry """
    def __init__(self, vbase, vend, descriptor, parent = None):
        self.vbase      = vbase
        self.vend       = vend
        self.size       = vend - vbase + 1
        self.descriptor = descriptor
        self.mair       = None
        self.strrep     = ""
        self.parent     = parent

    def find(self, addr):
        if (addr >= self.vbase and addr <= self.vend):
            return self
        else:
            return None

    def print_(self, mair, pall = False, show_hierarchy = False):
        pass

class NoMapping(TableEntry):
    pass

class Block(TableEntry):
    def __init__(self, vbase, vend, pbase, descriptor, parent=None):
        TableEntry.__init__(self, vbase, vend, descriptor, parent)
        self.pbase      = pbase
        self.pend       = pbase + self.size - 1

    def print_(self, mair, pall = False, show_hierarchy=False):
        indent = ""

        if (show_hierarchy == True and self.parent != None):
            indent = (self.parent.lvl + 1) * INDENT

        if(self.strrep == "" or mair != self.mair):
            self.mair = mair
            self.strrep = (format_highlight("Virtual Addr: ") +
                            format_hex(self.vbase) + " - " + format_hex(self.vend) +
                            format_highlight(" Size: ") + format_hex(self.size) +
                            format_highlight(" Physical Addr: ") +
                            format_hex(self.pbase) + " - " + format_hex(self.pend) +
                            format_highlight(" Attributes: ") + format_hex(self.descriptor) +
                            format_highlight(" Page/Bock ") +
                            str(self.decode_attributes(self.descriptor, mair)))

        print(indent + self.strrep)

    def decode_mair_el1(self, mair):
        def decode_rw(rw):
            # Check W bit
            w = rw & 0x1
            r = rw & 0x2
            s = ""

            if (w == 0b01):
                s = "WA, "

            if (r == 0b10):
                s+= "RA, "

            return s

        def decode_cacheability(cv):
            s = ""

            if ((cv & 0xC) >> 2 == 0b00):
                s = "Write-Trough Transient, "
                s += decode_rw(cv)
            elif ((cv & 0xC) >> 2 == 0b01 and ((lh & 0x3) == 0b00)):
                s = "Non-cacheable, "
            elif ((cv & 0xC) >> 2 == 0b01 and ((lh & 0x3) != 0b00)):
                s = "Write-Back Transient"
                s += decode_rw(cv)
            elif ((cv & 0xC) >> 2 == 0b10):
                s = "Write-Through Non-Transient, "
                s += decode_rw(cv)
            elif ((cv & 0xC) >> 2 == 0b11):
                s = "Write-Back Non-Transient, "
                s += decode_rw(cv)

            return s


        def decode_lower_half(uh, lh):
            s = ""

            # Device Memory
            if (uh == 0b0000):
                if (lh == 0b0000):
                    s = "nGnRnE"
                elif (lh == 0b0100):
                    s = "nGnRE"
                elif (lh == 0b1000):
                    s = "nGRE"
                elif (lh == 0b1100):
                    s = "GRE"
                else:
                    s = "Error invalid lower half of device memory type"
            # Normal Memory
            elif (lh == 0b0000):
                s = "Unpredictable"
            else:
                s = "Inner: " + decode_cacheability(lh)

            return s

        def decode_upper_half(uh):
            s = ""

            # Device memory
            if (uh == 0b0000):
                return "Device-"
            # Normal Memory
            else:
                s = "Outer: " + decode_cacheability(uh)

            return s

        # Split `mair` into byte sized chunks.
        attributes = [ord(b) for b in struct.pack('>Q', mair)]
        attributes.reverse()
        decoded = []

        for attr_idx in attributes:
            # Mask upper and lower half
            uh = attr_idx & 0xf0 >> 4
            lh = attr_idx & 0x0f

            attr = decode_upper_half(uh) + decode_lower_half(uh, lh)
            decoded.append(attr)

        return decoded

    def decode_attributes(self, attr, mair):
        page_attr = []
        attr &= ~ATTR_MASK
        sh = ["Non-Shareable", "Error", "Outer Shareable", "Inner Shareable"]
        sh_val = (attr & page_attr_mask["SH"]) >> 8
        attr_idx = (attr & page_attr_mask["ATTRIDX"]) >> 2
        ap_val = (attr & page_attr_mask["AP"]) >> 6

        if ((attr & page_attr_mask["UXN"]) != 0):
            page_attr.append("UXN")

        if ((attr & page_attr_mask["PXN"]) != 0):
            page_attr.append("PXN")

        if ((attr & page_attr_mask["AF"]) != 0):
            page_attr.append("AF")

        if ((attr & page_attr_mask["NS"]) != 0):
            page_attr.append("NS")

        if (ap_val != 0):
            page_attr.append("AP = {ap}".format(ap = ap_val))

        if (sh_val != 1):
            page_attr.append(sh[sh_val])

        if (mair != None):
            attributes = self.decode_mair_el1(mair)
            page_attr.append(attributes[attr_idx])
        else:
            page_attr.append("AttrIdx: {idx}".format(idx = attr_idx))

        return page_attr

class Table(TableEntry):
    def __init__(self, vbase, vend, descriptor, lvl, parent = None):
        TableEntry.__init__(self, vbase, vend, descriptor, parent)
        self.table_addr = descriptor & ATTR_MASK
        self.lvl = lvl
        self.entries  = []
        self.cmpr_entries  = []
        self.attributes = self.decode_attributes(descriptor)

    def set_entries(self, entries):
        self.entries = entries
        self.compress()

    def decode_attributes(self, attr):
        table_attr = []
        attr &= ~ATTR_MASK

        if (attr & table_attr_mask["NSTable"] != 0):
            table_attr.append("NSTable")

        if (attr & table_attr_mask["APTable"] != 0):
            aptable_val = attr & table_attr_mask["APTable"] >> 61
            table_attr.append("APTable = {v}".format(v = aptable_val))

        if (attr & table_attr_mask["UXN"] != 0):
            table_attr.append("UXN")

        if (attr & table_attr_mask["PXN"] != 0):
                table_attr.append("PXN")

        return table_attr

    def print_(self, mair, pall=False, show_hierarchy = False):
        indent = ""

        if (show_hierarchy == True):
            indent = self.lvl * INDENT
            print(indent + self.to_str())

        entries = self.entries if pall == True else self.cmpr_entries

        for te in entries:
            te.print_(mair, pall, show_hierarchy)

        if (self.parent != None and show_hierarchy == True):
            print("{indent}Continuation of Lvl {lvl} Table..."
                    .format(lvl = self.parent.lvl, indent = self.lvl * INDENT))

    def to_str(self):
        if (self.strrep == ""):
                self.strrep = ("Level " + str(self.lvl) +
                        " TABLE " + ("" if self.parent == None else "(@ phys. {addr}) "
                        .format(addr = hex(self.table_addr))) +
                        format_highlight("Virtual Addr: ") +
                        format_hex(self.vbase) + " - " + format_hex(self.vend) +
                        format_highlight(" Size: ") + format_hex(self.size) +
                        format_highlight(" Attributes: ") +
                        format_hex(self.descriptor & ~ATTR_MASK) +
                        format_highlight(" Table: ") + str(self.attributes))

        return self.strrep

    def get_parents(self, parent_list=None):
        if(parent_list == None):
            parent_list = []

        parent_list.append(self)

        if (self.parent == None):
            return parent_list
        else:
            return self.parent.get_parents(parent_list)


    def compress(self):
        self.cmpr_entries = list(self.entries)
        length = len(self.cmpr_entries)
        i = 0

        while (i<length):
            if (i + 1 < len(self.cmpr_entries)):
                if (isinstance(self.cmpr_entries[i], NoMapping)):
                    self.cmpr_entries.pop(i)
                    length-=1
                elif (isinstance(self.cmpr_entries[i], Table) == False and
                    ((self.cmpr_entries[i].descriptor & ~ATTR_MASK) ==
                    (self.cmpr_entries[i+1].descriptor & ~ATTR_MASK))):
                    self.cmpr_entries[i] = Block(
                                            self.cmpr_entries[i].vbase,
                                            self.cmpr_entries[i+1].vend,
                                            self.cmpr_entries[i].pbase,
                                            self.cmpr_entries[i].descriptor & ~ATTR_MASK,
                                            self.cmpr_entries[i].parent)
                    self.cmpr_entries.pop(i+1)
                    length-=1
                else:
                    i+=1
            else:
                i+=1

    def find(self, addr):
        #naiv implementation could be done in a more performant way
        for e in self.entries:
            found = e.find(addr)
            if (found != None):
                return found
        return None


# Parser Code
def is_table(desc, lvl):
    return (((desc & TABLE_MASK) == TABLE_MASK) and (lvl != 3))

def get_table_addr(desc):
    return (desc & ATTR_MASK) + VM_OFFSET

def get_virtual_addr(lvlidx):
    return (lvlidx[0] * _512GB) + (lvlidx[1] * _1GB) + (lvlidx[2] * _2MB) + (lvlidx[3] * _4K)

def get_physical_addr(desc):
    return (desc & ATTR_MASK)

def get_virtual_range(lvlidx, curr_lvl):
    next_idx = list(lvlidx)
    next_idx[curr_lvl] += 1

    return (get_virtual_addr(lvlidx), get_virtual_addr(next_idx) - 1)

def get_table_range(lvlidx, lvl):
    tsize = {0 : _512GB * 512,
             1 : _1GB * 512,
             2 : _2MB * 512,
             3 : _4K * 512}

    b = get_virtual_addr(lvlidx)
    e = b + tsize[lvl] - 1
    return (b, e)

def parse_descriptor(desc, lvlidx, curr_lvl, parent, is_root_tabel = False):
    if (is_table(desc, curr_lvl) or is_root_tabel):
        # If it is not the root table, the descriptor will contain the physical
        # address of the next lvl table. We have to mask out the attributes and
        # add the virtual address offset if no identity mapping for the physical
        # address is available.
        if (is_root_tabel == False):
            taddr = get_table_addr(desc)
        # In case we are parsing the root table, the descriptor only contains the
        # address of the root table. If the mmu is already turned on this is a
        # virtual address.
        else:
            taddr = desc

        logger.debug("\t" * (curr_lvl + 1) + "lvl "+ str(curr_lvl + 1) + " Table at " +
                hex(taddr) + str(curr_lvl + 1) + " " + str(lvlidx))
        base, end = get_table_range(lvlidx, curr_lvl + 1)
        table = Table(base, end, desc, curr_lvl + 1, parent)
        tentries = []

        for i in range(512):
            lvlidx[curr_lvl + 1] = i
            elem = taddr + (i*8)
            vp = gdb.Value(elem).cast(gdb.lookup_type('uint64_t').pointer())
            v = int((vp.dereference()))
            tentries.append(parse_descriptor(v, lvlidx, curr_lvl + 1, table))

        lvlidx[curr_lvl + 1] = 0
        table.set_entries(tentries)

        return table

    elif (desc == 0):
        base, end = get_virtual_range(lvlidx, curr_lvl)
        logger.debug("\t" * curr_lvl +
                            "BLOCK/PAGE " + str(lvlidx[curr_lvl]) +
                            " Addr: " +  hex(base) + " - " + hex(end)
                            + " Not mapped!" + str(curr_lvl) +" " + str(lvlidx))

        return NoMapping(base, end, 0)

    else:
        base, end = get_virtual_range(lvlidx, curr_lvl)
        phybase = get_physical_addr(desc)

        logger.debug("\t" * curr_lvl + "BLOCK/PAGE " + str(lvlidx[curr_lvl]) +" Addr: " +
                            hex(base)  + " - " + hex(end) +" physical " +
                            hex(get_physical_addr(desc)) + " value "
                            + hex(desc)+ str(curr_lvl) +" " + str(lvlidx))

        return Block(base, end, phybase, desc, parent)
