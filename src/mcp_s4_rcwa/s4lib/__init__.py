import ctypes
import os
import numpy as np

_lib = ctypes.CDLL(os.path.join(os.path.dirname(__file__), 'libS4.so'))

_lib.S4_Simulation_New.restype = ctypes.c_void_p
_lib.S4_Simulation_New.argtypes = [
    np.ctypeslib.ndpointer(dtype=np.float64),
    ctypes.c_uint,
    ctypes.POINTER(ctypes.c_int),
]

_lib.S4_Simulation_Destroy.restype = None
_lib.S4_Simulation_Destroy.argtypes = [ctypes.c_void_p]

_lib.S4_Simulation_SetMaterial.restype = ctypes.c_int
_lib.S4_Simulation_SetMaterial.argtypes = [
    ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
    np.ctypeslib.ndpointer(dtype=np.float64),
]

_lib.S4_Simulation_SetLayer.restype = ctypes.c_int
_lib.S4_Simulation_SetLayer.argtypes = [
    ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p,
    np.ctypeslib.ndpointer(dtype=np.float64),
    ctypes.c_int, ctypes.c_int,
]

_lib.S4_Layer_SetRegionHalfwidths.restype = ctypes.c_int
_lib.S4_Layer_SetRegionHalfwidths.argtypes = [
    ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    np.ctypeslib.ndpointer(dtype=np.float64),
    np.ctypeslib.ndpointer(dtype=np.float64),
    np.ctypeslib.ndpointer(dtype=np.float64),
]

_lib.S4_Simulation_ExcitationPlanewave.restype = ctypes.c_int
_lib.S4_Simulation_ExcitationPlanewave.argtypes = [
    ctypes.c_void_p,
    np.ctypeslib.ndpointer(dtype=np.float64),
    np.ctypeslib.ndpointer(dtype=np.float64),
    np.ctypeslib.ndpointer(dtype=np.float64),
    np.ctypeslib.ndpointer(dtype=np.float64),
]

_lib.S4_Simulation_SetFrequency.restype = ctypes.c_int
_lib.S4_Simulation_SetFrequency.argtypes = [
    ctypes.c_void_p,
    np.ctypeslib.ndpointer(dtype=np.float64),
]

_lib.S4_Simulation_GetPowerFlux.restype = ctypes.c_int
_lib.S4_Simulation_GetPowerFlux.argtypes = [
    ctypes.c_void_p, ctypes.c_int,
    np.ctypeslib.ndpointer(dtype=np.float64),
    np.ctypeslib.ndpointer(dtype=np.float64),
]

_lib.S4_Layer_ClearRegions.restype = ctypes.c_int
_lib.S4_Layer_ClearRegions.argtypes = [ctypes.c_void_p, ctypes.c_int]


class S4Simulation:
    def __init__(self, period_um, n_G=101):
        Lr = np.array([period_um, 0.0, 0.0, period_um], dtype=np.float64)
        self._sim = _lib.S4_Simulation_New(Lr, n_G, None)
        self._layers = {}
        self._materials = {}
        self._n_G = n_G

    def destroy(self):
        if self._sim:
            _lib.S4_Simulation_Destroy(self._sim)
            self._sim = None

    def set_material(self, name, eps_real, eps_imag=0.0):
        eps = np.array([eps_real, eps_imag], dtype=np.float64)
        mid = _lib.S4_Simulation_SetMaterial(
            self._sim, -1, name.encode(), 2 if eps_imag == 0 else 3, eps)
        self._materials[name] = mid
        return mid

    def add_layer(self, name, thickness_um, material_name=None, copy_name=None):
        thick = np.array([thickness_um], dtype=np.float64)
        material_id = self._materials.get(material_name, -1) if material_name else -1
        copy_id = self._layers.get(copy_name, -1) if copy_name else -1
        lid = _lib.S4_Simulation_SetLayer(
            self._sim, -1, name.encode(), thick, copy_id, material_id)
        self._layers[name] = lid
        return lid

    def add_rect_pattern(self, layer_name, material_name, halfwidths_um, center_um=(0, 0)):
        hw = np.array([halfwidths_um[0], halfwidths_um[1]], dtype=np.float64)
        c = np.array([center_um[0], center_um[1]], dtype=np.float64)
        angle = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        mid = self._materials[material_name]
        lid = self._layers[layer_name]
        _lib.S4_Layer_SetRegionHalfwidths(
            self._sim, lid, mid, 12, hw, c, angle)

    def set_excitation_planewave(self, kdir=(0, 0, -1), udir=(1, 0, 0),
                                  amp_u_real=1.0, amp_u_imag=0.0,
                                  amp_v_real=0.0, amp_v_imag=0.0):
        kdir = np.array(kdir, dtype=np.float64)
        udir = np.array(udir, dtype=np.float64)
        amp_u = np.array([amp_u_real, amp_u_imag], dtype=np.float64)
        amp_v = np.array([amp_v_real, amp_v_imag], dtype=np.float64)
        _lib.S4_Simulation_ExcitationPlanewave(self._sim, kdir, udir, amp_u, amp_v)

    def set_frequency(self, wavelength_um):
        omega = np.array([1.0 / wavelength_um, 0.0], dtype=np.float64)
        _lib.S4_Simulation_SetFrequency(self._sim, omega)

    def get_power_flux(self, layer_name, offset_um=0.0):
        offset = np.array([offset_um], dtype=np.float64)
        power = np.zeros(4, dtype=np.float64)
        lid = self._layers[layer_name]
        _lib.S4_Simulation_GetPowerFlux(self._sim, lid, offset, power)
        return power

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.destroy()
