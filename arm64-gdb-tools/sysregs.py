import gdb
import openocd

# https://developer.arm.com/documentation/ddi0595/2020-12/AArch64-Registers
sysregs = {
    "TTBR0_EL1" :   (3,0,2,0,0),
    "MAIR_EL1"  :   (3,0,10,2,0),
    "SCTLR_EL1"  :  (3,0,1,0,0)
}


class Sysregs(gdb.Command):
    """Print system registers"""

    def __init__ (self):
        super (Sysregs, self).__init__ ("sysregs", gdb.COMMAND_USER)
        self.ocd = openocd.OpenOcd()
        self.ocd.connect()
        gdb.events.exited.connect(self.ocd_disconnect)
    
    def ocd_disconnect(self):
        self.ocd.disconnect()

    def invoke(self, arg, from_tty):
        for reg in sysregs:
            out = self.ocd._mrs(sysregs[reg][0], sysregs[reg][1], sysregs[reg][2], sysregs[reg][3], sysregs[reg][4])
            print("{r}\t{v}".format(r = reg,v = out))