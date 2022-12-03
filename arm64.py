import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/arm64-gdb-tools')

from vmmap import VMMAP
from sysregs import Sysregs

VMMAP()
Sysregs()
