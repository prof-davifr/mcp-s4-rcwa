"""JSON-friendly layer on top of the real S4 (Stanford Stratified Structure
Solver) RCWA engine, driven through the compiled `libS4.so` via the `s4lib`
ctypes wrapper (`S4Simulation`).

Encodes the conventions from this machine's `s4-rcwa` skill: bottom-to-top
layer order, explicit TE/TM polarization, `frequency = 1/wavelength`, and the
`[forward_re, backward_re, forward_im, backward_im]` power-flux layout used to
derive R/T/A.
"""
from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from typing import Any

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .s4lib import S4Simulation


class S4Error(ValueError):
    """Raised for invalid stack/sweep specifications."""


@dataclass
class LayerSpec:
    name: str
    thickness: float
    material: str
    pattern: dict[str, Any] | None = None  # {"material": str, "halfwidths": [hx, hy], "center": [cx, cy]}


def _eps_of(material: dict[str, Any]) -> tuple[float, float]:
    if "n" in material:
        n = complex(material["n"], material.get("k", 0.0))
        eps = n * n
        return float(eps.real), float(eps.imag)
    return float(material.get("eps_real", 1.0)), float(material.get("eps_imag", 0.0))


def run_stack_spectrum(
    period: float,
    n_harmonics: int,
    materials: dict[str, dict[str, Any]],
    layers: list[dict[str, Any]],
    incidence_layer: str,
    substrate_layer: str,
    polarization: str,
    theta_deg: float,
    wavelength_start: float,
    wavelength_stop: float,
    wavelength_points: int,
) -> dict[str, list[float]]:
    """Build the stack once and sweep wavelength, returning R/T/A.

    `layers` must be ordered bottom (substrate) -> top (incidence medium), matching
    S4's call order. `incidence_layer` / `substrate_layer` name entries in `layers`
    used to read power flux (offset 0 into each).
    """
    if wavelength_points < 2:
        raise S4Error("`wavelength_points` must be >= 2.")
    if wavelength_stop <= wavelength_start:
        raise S4Error("`wavelength_stop` must be greater than `wavelength_start`.")
    if not layers:
        raise S4Error("`layers` must contain at least one layer.")
    if polarization not in ("TE", "TM"):
        raise S4Error("`polarization` must be 'TE' or 'TM'.")

    layer_names = {spec["name"] for spec in layers}
    if incidence_layer not in layer_names:
        raise S4Error(f"incidence_layer '{incidence_layer}' not found among layer names {sorted(layer_names)}.")
    if substrate_layer not in layer_names:
        raise S4Error(f"substrate_layer '{substrate_layer}' not found among layer names {sorted(layer_names)}.")

    sim = S4Simulation(period, n_G=n_harmonics)
    try:
        for name, mat in materials.items():
            er, ei = _eps_of(mat)
            sim.set_material(name, er, ei)

        for spec in layers:
            sim.add_layer(spec["name"], spec["thickness"], spec["material"])
            pattern = spec.get("pattern")
            if pattern:
                hw = pattern["halfwidths"]
                center = pattern.get("center", (0.0, 0.0))
                sim.add_rect_pattern(spec["name"], pattern["material"], tuple(hw), center_um=tuple(center))

        theta = np.deg2rad(theta_deg)
        kdir = (np.sin(theta), 0.0, -np.cos(theta))
        udir = (0.0, 1.0, 0.0) if polarization == "TE" else (1.0, 0.0, 0.0)
        sim.set_excitation_planewave(kdir=kdir, udir=udir)

        wavelengths = np.linspace(wavelength_start, wavelength_stop, wavelength_points)
        R = np.empty(wavelength_points)
        T = np.empty(wavelength_points)
        for i, lam in enumerate(wavelengths):
            sim.set_frequency(float(lam))
            ps = sim.get_power_flux(incidence_layer, 0.0)
            pb = sim.get_power_flux(substrate_layer, 0.0)
            incident = abs(ps[1])
            if incident < 1e-15:
                R[i] = 0.0
                T[i] = 0.0
                continue
            R[i] = ps[0] / incident
            T[i] = abs(pb[1]) / incident

        A = 1.0 - R - T
        return {
            "wavelength": wavelengths.tolist(),
            "R": R.tolist(),
            "T": T.tolist(),
            "A": A.tolist(),
        }
    finally:
        sim.destroy()


def check_fresnel_sanity(n_harmonics: int = 11) -> dict[str, float]:
    """Bare air/Si interface at 0.5 um; analytic Fresnel R ~ 0.3055.

    Used as a self-test tool so the caller can confirm the compiled
    libS4.so is working correctly in this environment before trusting results.
    """
    result = run_stack_spectrum(
        period=1.0,
        n_harmonics=n_harmonics,
        materials={"Si": {"eps_real": 3.47 ** 2}, "air": {"eps_real": 1.0}},
        layers=[
            {"name": "substrate", "thickness": 0.5, "material": "Si"},
            {"name": "superstrate", "thickness": 0.5, "material": "air"},
        ],
        incidence_layer="superstrate",
        substrate_layer="substrate",
        polarization="TE",
        theta_deg=0.0,
        wavelength_start=0.5,
        wavelength_stop=0.5001,
        wavelength_points=2,
    )
    return {"R": result["R"][0], "T": result["T"][0], "A": result["A"][0], "expected_R": 0.3055}


def plot_spectrum_png(spectrum: dict[str, list[float]]) -> str:
    fig, ax = plt.subplots(figsize=(6, 4), dpi=120)
    ax.plot(spectrum["wavelength"], spectrum["R"], label="Reflectance (R)")
    ax.plot(spectrum["wavelength"], spectrum["T"], label="Transmittance (T)")
    ax.plot(spectrum["wavelength"], spectrum["A"], label="Absorptance (A)")
    ax.set_xlabel("Wavelength (µm)")
    ax.set_ylabel("Fraction")
    ax.set_ylim(-0.02, 1.02)
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")
