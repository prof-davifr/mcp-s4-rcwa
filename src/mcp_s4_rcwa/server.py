"""MCP server exposing S4 (Stanford Stratified Structure Solver) RCWA
simulations of laterally periodic, layered photonic stacks: gratings,
zero-contrast gratings, DBR/photonic-crystal stacks, guided-mode-resonance
absorbers, thin-film filters.

Pure local computation, no network access and no side effects — every tool is
read-only.
"""
from __future__ import annotations

import json
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent, TextContent

from . import s4_core

mcp = FastMCP("s4-rcwa")

_MATERIAL_SCHEMA_HINT = (
    "Each material is {\"n\": <real index>, \"k\": <optional extinction coeff>} "
    "or {\"eps_real\": ..., \"eps_imag\": ...} for a direct permittivity."
)

_LAYER_SCHEMA_HINT = (
    "Each layer is {\"name\": str, \"thickness\": float (um), \"material\": str "
    "(key into `materials`), \"pattern\": optional {\"material\": str, "
    "\"halfwidths\": [hx, hy] (um), \"center\": [cx, cy] (um, default [0,0])} "
    "to stamp a rectangular ridge/hole into the layer (e.g. a grating groove). "
    "Order layers bottom (substrate) to top (incidence medium) — this matches "
    "S4's call order. Two adjacent layers of the same material optically merge "
    "and can detune cavity resonances, so keep distinct layers separated by a "
    "different index if that matters to your design."
)


_SIMULATE_STACK_DESCRIPTION = (
    "Run an RCWA (S4) simulation of a laterally periodic, layered stack and "
    "return the reflectance/transmittance/absorptance (R/T/A) spectrum vs "
    "wavelength. Use this for gratings, zero-contrast gratings, DBR/photonic "
    "crystal stacks, guided-mode-resonance absorbers, and thin-film filters — "
    "any structure periodic in the lateral (x,y) plane and uniform or patterned "
    "per layer. Does NOT handle non-periodic structures or isolated scatterers "
    "(those need FDTD/FEM instead).\n\n"
    "All lengths are in micrometers (um), matching S4's convention. Wavelength "
    "sweep is linear from wavelength_start to wavelength_stop, inclusive of both "
    f"ends. {_MATERIAL_SCHEMA_HINT} {_LAYER_SCHEMA_HINT}\n\n"
    "incidence_layer / substrate_layer must name entries in `layers`: the "
    "incidence_layer is the top (superstrate) medium the plane wave enters "
    "from, substrate_layer is the bottom medium power is transmitted into.\n\n"
    "polarization is TE (E-field along y, `udir=(0,1,0)`) or TM (E-field in the "
    "plane of incidence, `udir=(1,0,0)`) — always pass this explicitly, since "
    "peak positions for gratings depend strongly on it. theta_deg is the polar "
    "angle of incidence in degrees (0 = normal incidence). n_harmonics is the "
    "number of Fourier harmonics (higher = more accurate, slower); 51 is a good "
    "default for low-contrast dielectric stacks, increase for high-index-"
    "contrast or metallic gratings and check the result is stable vs this value.\n\n"
    "Returns the spectrum as JSON (wavelength, R, T, A arrays) plus, if "
    "include_plot is true, a PNG plot of R/T/A vs wavelength."
)


@mcp.tool(
    description=_SIMULATE_STACK_DESCRIPTION,
    annotations={
        "title": "Simulate periodic photonic stack (RCWA)",
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def simulate_stack_spectrum(
    period: float,
    materials: dict[str, dict[str, float]],
    layers: list[dict[str, Any]],
    incidence_layer: str,
    substrate_layer: str,
    wavelength_start: float,
    wavelength_stop: float,
    wavelength_points: int = 200,
    polarization: Literal["TE", "TM"] = "TE",
    theta_deg: float = 0.0,
    n_harmonics: int = 51,
    include_plot: bool = True,
) -> list[TextContent | ImageContent]:
    spectrum = s4_core.run_stack_spectrum(
        period=period,
        n_harmonics=n_harmonics,
        materials=materials,
        layers=layers,
        incidence_layer=incidence_layer,
        substrate_layer=substrate_layer,
        polarization=polarization,
        theta_deg=theta_deg,
        wavelength_start=wavelength_start,
        wavelength_stop=wavelength_stop,
        wavelength_points=wavelength_points,
    )

    content: list[TextContent | ImageContent] = [
        TextContent(type="text", text=json.dumps(spectrum))
    ]
    if include_plot:
        png_b64 = s4_core.plot_spectrum_png(spectrum)
        content.append(ImageContent(type="image", data=png_b64, mimeType="image/png"))
    return content


@mcp.tool(
    annotations={
        "title": "Check S4 engine sanity (Fresnel test)",
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def check_engine_sanity(n_harmonics: int = 11) -> str:
    """Run a bare air/Si interface RCWA calculation and compare against the
    analytic Fresnel reflectance (~0.3055 at normal incidence). Use this once
    before trusting other results in a session, to confirm the compiled S4
    engine (libS4.so) loads and computes correctly in this environment — a
    mismatch here means don't trust simulate_stack_spectrum output. Does not
    require any stack design input.
    """
    result = s4_core.check_fresnel_sanity(n_harmonics=n_harmonics)
    ok = abs(result["R"] - result["expected_R"]) < 0.01
    result["ok"] = ok
    return json.dumps(result)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
