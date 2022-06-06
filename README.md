# arm64-gdb-tools
## Introduction
Collection (currently only one ;)) of gdb extensions that ease the development of arm64 bare metal applications.

## Install
  * Copy the content of this repo to your gdb [data-directory](https://sourceware.org/gdb/onlinedocs/gdb/Python.html). Hint: If you are using the bare metal GNU toolchain [(aarch64-none-elf)](https://developer.arm.com/downloads/-/gnu-a) provided by ARM, this should be `/gcc-arm-xxxx/share/gdb/python/gdb/command/`.

## Commands
### vmmap - print mmu translation table

Reads an arm64 compliant mmu translation table from memory and prints it in human readable format to see if it matches your expectation. Currently only Stage 1 translation tables with a 4k granule are suported.


The following options are available:
```
  -h, --help
                            show this help message and exit

  -tb TTBR, --ttbr TTBR
                            First level translation table base address.

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
**Note: Since the addresses of next-level tables within the translation table will be physical addresses, the memory where those tables are located should be either made accessible via an identity mapping or by using the -tvo option.**

### Examples:
```
vmmap -lvl 0 -tb lvl0_table -tvo 0x4000000000 -ph -m 0xff44
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
