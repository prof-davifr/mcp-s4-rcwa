# Third-party notices

## S4 (Stanford Stratified Structure Solver)

`src/mcp_s4_rcwa/s4lib/libS4.so` is a compiled binary built from
[S4](https://github.com/victorliu/S4) by Victor Liu (Stanford University),
licensed under the GNU General Public License v3.0 (GPL-3.0). Source code is
available upstream at https://github.com/victorliu/S4.

`src/mcp_s4_rcwa/s4lib/__init__.py` (the `S4Simulation` ctypes wrapper) is a
thin binding around S4's C API and is likewise subject to the terms that
apply to works built against S4's headers.

This repository's own code (the MCP server, tool schemas, plotting helpers) is
licensed separately under the MIT License — see `LICENSE`.
