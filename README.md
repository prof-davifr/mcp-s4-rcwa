# mcp-s4-rcwa

An [MCP](https://modelcontextprotocol.io) server that runs [S4](https://web.stanford.edu/group/fan/S4/) (the Stanford Stratified Structure Solver) — a rigorous coupled-wave analysis (RCWA) engine — so MCP clients can simulate laterally periodic, layered photonic structures directly in conversation: gratings, zero-contrast gratings, DBR/photonic-crystal stacks, guided-mode-resonance absorbers, thin-film filters.

RCWA (a.k.a. the Fourier Modal Method) is the fast, semi-analytic way to get a reflection/transmission/absorption spectrum of a stack of uniform or in-plane-patterned layers, without resorting to full FDTD/FEM.

## Why not `pip install S4`?

The upstream `S4` Python binding is Python-2 only (it hits `PyString_AsStringAndSize`, removed in Python 3) and fails to import on any current interpreter. This server instead drives a locally compiled `libS4.so` through a small hand-written `ctypes` wrapper (`s4lib/`, vendored in this repo) — no server, no license step, plain `python3`.

## Tools

- **`simulate_stack_spectrum`** — build a layered stack (with optional rectangular grating patterns per layer), sweep wavelength, and get back R/T/A as JSON plus a PNG plot.
- **`check_engine_sanity`** — bare air/Si interface sanity check against the analytic Fresnel reflectance (~0.3055). Run this once per session before trusting other results — it confirms the compiled `libS4.so` loads and computes correctly on the host machine.

Both tools are read-only / side-effect-free (pure computation, no network access).

## Conventions (baked into the wrapper)

- All lengths in micrometers (µm).
- Layers are ordered bottom (substrate) → top (incidence medium), matching S4's internal call order.
- Polarization must be passed explicitly (`TE` = E-field along y, `TM` = E-field in the plane of incidence) — it's easy to silently simulate the wrong one and get peaks that are tens of nm off.
- `S4` frequency convention is `1/wavelength` (not `2π/λ`), handled internally.
- R/T/A are derived from the `[forward_re, backward_re, forward_im, backward_im]` power-flux layout S4 returns, guarding the divide when incident flux is ~0.

See `src/mcp_s4_rcwa/s4_core.py` for the implementation and `check_engine_sanity` for the Fresnel guard.

## Install

```bash
pip install -e .
```

Requires Linux x86-64 (the vendored `libS4.so` is a compiled binary for that platform). On another platform you'll need to build `S4` yourself and drop `libS4.so` into `src/mcp_s4_rcwa/s4lib/`.

## Run

As a local stdio MCP server:

```bash
mcp-s4-rcwa
```

### MCP client config

```json
{
  "mcpServers": {
    "s4-rcwa": {
      "command": "mcp-s4-rcwa"
    }
  }
}
```

## Example

```json
{
  "period": 1.0,
  "materials": {
    "Si": {"n": 3.47},
    "SiO2": {"n": 1.44},
    "air": {"n": 1.0}
  },
  "layers": [
    {"name": "substrate", "thickness": 0.5, "material": "Si"},
    {"name": "spacer", "thickness": 0.3, "material": "SiO2"},
    {"name": "superstrate", "thickness": 0.5, "material": "air"}
  ],
  "incidence_layer": "superstrate",
  "substrate_layer": "substrate",
  "polarization": "TE",
  "wavelength_start": 1.4,
  "wavelength_stop": 1.8,
  "wavelength_points": 200
}
```

## License

This repository's code is MIT-licensed (see `LICENSE`). It vendors a compiled `libS4.so` built from [S4](https://github.com/victorliu/S4), which is licensed GPL-3.0 by Victor Liu / Stanford University — see `THIRD_PARTY_NOTICES.md`.
