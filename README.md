# arm64-gdb-tools
## Introduction
Collection of gdb extensions that ease the development of Aarch64 bare metal applications.

## Install
  * Copy the content of this repo to your gdb [data-directory](https://sourceware.org/gdb/onlinedocs/gdb/Python.html). Hint: If you are using the bare metal GNU toolchain [(aarch64-none-elf)](https://developer.arm.com/downloads/-/gnu-a) provided by ARM, this should be `/gcc-arm-xxxx/share/gdb/python/gdb/command/`.

  * Some functionality depends on two OpenOcd patches which currently haven't made it into the master branch. The resprective commands are maked below (OpenOcd).
    * Patch 1: Adds msr/mrs command to OpenOcd which is needed to read out system registers.
      * https://review.openocd.org/c/openocd/+/5003
    * Patch 2: Fixes a bug which ignored the most significant bits when reading 64 bit values from memory.
      * https://review.openocd.org/c/openocd/+/7192 

## Commands

1. [vmmap](#vmmap) - print mmu translation table (gdb/OpenOcd)
2. [sysregs](#sysregs) - print system registers (OpenOcd)

## vmmap

Reads an Aarch64 compliant mmu translation table from memory and prints it in human readable format to see if it matches your expectation. Currently only Stage 1 translation tables with a 4k granule are suported.  

This command comes in two flavours.

* GDB - uses only gdb and is independet from OpenOcd. This comes with a few downsides. 
  * **TTBR0_EL1 / MAIR_EL1** Since gdb can't read out system registers, the root table and the value of the MAIR_EL1 register must be passed via the **-tb** and **-m** options.
  * **Virtual address offset:** Since gdb is looking at the memory through the eyes of the core that is debugged, turning on the MMU means we can only read virtual memory. That means the translation table must be mapped to virtual memory. If no identity mapping is used the the **-tvo** option must be used to tell the command the virtual address offset of the translation tables (this is due to the fact that inside the translation tables the addresses of next level tables are physical addresses).

* OpenOcd - If gdb uses OpenOcd under the hood the aformentioned options don't have to be provided as we can use it to directly access system registers and read physical memory. Set [this flag](https://github.com/dinkelhacker/arm64-gdb-tools/blob/be87d5699e4b6c1bdf667c689fe97b6bf13fc73d/arm64-gdb-tools/vmmap.py#L22) to use this version of the command.

The following options are available:
```
  -h, --help
                            show this help message and exit

  -tb TTBR, --ttbr TTBR
                            First level translation table base address. (symbol or address)

  -m MAIR, --mair MAIR
                            Value stored in MAIR register.

  -v, --verbose
                            Print debug statements.

  -ph, --print_hierarchy
                            Print hierarchical information.

  -pa, --print_all
                            Print all mappings.

  -a ADDR, --addr ADDR
                            Print mapping at address.

  -s SYMBOL, --symbol SYMBOL
                            Print mapping of symbol.

  -c, --clear
                            Clear cached values.

  -tvo TVIRT_OFFSET, --tvirt_offset TVIRT_OFFSET
                            Sets virtual address offset of next level table addresses.

  -lvl {0,1}, --level {0,1}
                            Specifies the table lvl at which the translation starts. Default is 0.
```

#### Examples:
```
// Both versions would produce the same output.
vmmap -tb lvl0_table -tvo 0x4000000000 -ph -m 0xff44 (GDB version)
vmmap -ph (OpenOcd version)

MAIR: 0x000000000000ff44
Reading translation table from memory...
First lvl Table: lvl0_table
Level 0 TABLE Virtual Addr: 0x0000000000000000 - 0x0000ffffffffffff Size: 0x0001000000000000 Attributes: 0x0000000000000000 Table: []
  Level 1 TABLE (@ phys. 0x363000) Virtual Addr: 0x0000000000000000 - 0x0000007fffffffff Size: 0x0000008000000000 Attributes: 0x0000000000000003 Table: []
    Level 2 TABLE (@ phys. 0x364000) Virtual Addr: 0x0000004000000000 - 0x000000403fffffff Size: 0x0000000040000000 Attributes: 0x0000000000000003 Table: []
      Level 3 TABLE (@ phys. 0x365000) Virtual Addr: 0x0000004000000000 - 0x00000040001fffff Size: 0x0000000000200000 Attributes: 0x0000000000000003 Table: []
        Virtual Addr: 0x0000004000000000 - 0x000000400003ffff Size: 0x0000000000040000 Physical Addr: 0x0000000000000000 - 0x000000000003ffff Attributes: 0x0000000000000707 Page/Bock ['Inner Shareable', 'Outer: Write-Back Non-Transient, WA, RA, Inner: Write-Back Non-Transient, WA, RA, ']
        Virtual Addr: 0x0000004000040000 - 0x000000400004ffff Size: 0x0000000000010000 Physical Addr: 0x0000000000040000 - 0x000000000004ffff Attributes: 0x0000000000000703 Page/Bock ['Inner Shareable', 'Outer: Non-cacheable, Inner: Non-cacheable, ']
        Virtual Addr: 0x0000004000050000 - 0x00000040001fffff Size: 0x00000000001b0000 Physical Addr: 0x0000000000050000 - 0x00000000001fffff Attributes: 0x0000000000000707 Page/Bock ['Inner Shareable', 'Outer: Write-Back Non-Transient, WA, RA, Inner: Write-Back Non-Transient, WA, RA, ']
      Continuation of Lvl 2 Table...
      Virtual Addr: 0x0000004000200000 - 0x000000403fffffff Size: 0x000000003fe00000 Physical Addr: 0x0000000000200000 - 0x000000003fffffff Attributes: 0x0000000000000705 Page/Bock ['Inner Shareable', 'Outer: Write-Back Non-Transient, WA, RA, Inner: Write-Back Non-Transient, WA, RA, ']
    Continuation of Lvl 1 Table...
    Virtual Addr: 0x0000004040000000 - 0x00000040bfffffff Size: 0x0000000080000000 Physical Addr: 0x0000000040000000 - 0x00000000bfffffff Attributes: 0x0000000000000705 Page/Bock ['Inner Shareable', 'Outer: Write-Back Non-Transient, WA, RA, Inner: Write-Back Non-Transient, WA, RA, ']
    Virtual Addr: 0x00000040c0000000 - 0x00000040ffffffff Size: 0x0000000040000000 Physical Addr: 0x00000000c0000000 - 0x00000000ffffffff Attributes: 0x00600000c0000409 Page/Bock ['UXN', 'PXN', 'Non-Shareable', 'Device-nGnRnE']
  Continuation of Lvl 0 Table...
```

Tried and tested with:
```
[phil@fedora os]$ ./build/gcc-arm/bin/aarch64-none-elf-gdb -v
GNU gdb (GNU Toolchain for the A-profile Architecture 10.3-2021.07 (arm-10.29)) 10.2.90.20210621-git
...
[phil@fedora os]$ openocd -v
Open On-Chip Debugger 0.11.0
...
```

## sysregs

The `sysregs` command uses OpenOcds capability to read out system registers like SCTLR_EL1 or TTBR0_EL1 and prints them to the console. [Just add the registers your interested in.](https://github.com/dinkelhacker/arm64-gdb-tools/blob/be87d5699e4b6c1bdf667c689fe97b6bf13fc73d/arm64-gdb-tools/sysregs.py#L5)

```
>>> sysregs
TTBR0_EL1	0x0000000000000000
SCTLR_EL1	0x0000000000c50838
MAIR_EL1	0x44e048e000098aa4
```
