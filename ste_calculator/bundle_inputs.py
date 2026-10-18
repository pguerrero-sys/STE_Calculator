"""Contrato de entradas compartido entre Haces y Transposición, sin Streamlit.

Recibe una instantánea de los widgets actuales. No conserva geometrías ni
resultados entre ejecuciones y no necesita frecuencia o longitud longitudinal.
"""

from collections.abc import Mapping

from .bundles import BundleSpec, build_bundles
from .inductance import RMGInput, SOLID_UNIFORM, MANUFACTURER, IDEAL_GROUND, NO_GROUND, resolve_rmg
from .models import InputError, PHASES, finite_number

MATERIALS = ["Seleccionar modelo inductivo", "Macizo no magnético, corriente uniforme", "ACSR/trenzado: RMG del fabricante"]


def build_bundle_context(conductors, circuit_count, values: Mapping, coordinate_error=""):
    """Valida entradas geométricas; un error de RMG solo retira la inductancia.

    Las claves haz_* son las mismas que usan los widgets. Los valores del
    editor de Geometría se reciben ya convertidos a conductores en app.py.
    """
    if circuit_count != 1:
        raise InputError(f"Número de circuitos = {circuit_count}: se requiere un circuito A/B/C.")
    if conductors is None:
        raise InputError("Coordenadas de Geometría inválidas: " + (coordinate_error or "no se recibieron conductores A/B/C."))
    if len(conductors) != 3 or {(c.circuit, c.phase) for c in conductors} != {(1,p) for p in PHASES}:
        raise InputError("Geometría debe contener exactamente C1-A, C1-B y C1-C.")
    specs = []
    for conductor in sorted(conductors, key=lambda c: PHASES.index(c.phase)):
        phase = conductor.phase
        count = values.get(f"haz_n_{phase}", 1)
        if type(count) is not int or count not in (1,2,3,4):
            raise InputError(f"Subconductores {phase} (haz_n_{phase}): usa 1, 2, 3 o 4.")
        radius = finite_number(values.get(f"haz_r_{phase}"), f"Radio exterior individual {phase} [m] (haz_r_{phase})")
        spacing = None if count == 1 else finite_number(values.get(f"haz_s_{phase}"), f"Separación entre vecinos {phase} [m] (haz_s_{phase})")
        angle = finite_number(values.get(f"haz_angle_{phase}", 0.0), f"Rotación adicional {phase} [°] (haz_angle_{phase})")
        if radius <= 0:
            raise InputError(f"Radio exterior individual {phase} [m] (haz_r_{phase}) = {radius:g}: debe ser positivo.")
        specs.append(BundleSpec(conductor,count,radius,spacing,angle))
    geometry = build_bundles(tuple(specs))
    cap_choices = {"Suelo ideal": IDEAL_GROUND, "Sin suelo · carga total cero": NO_GROUND}
    ind_choices = {"Suelo ideal": IDEAL_GROUND, "Sin suelo · corrientes de suma cero": NO_GROUND}
    cap_choice = values.get("haz_cap_ground", "Suelo ideal")
    ind_choice = values.get("haz_ind_ground", "Suelo ideal")
    if cap_choice not in cap_choices:
        raise InputError(f"Suelo para capacitancia (haz_cap_ground): opción no implementada {cap_choice!r}.")
    if ind_choice not in ind_choices:
        raise InputError(f"Suelo para inductancia (haz_ind_ground): opción no implementada {ind_choice!r}.")
    inputs, inductance_error = None, ""
    try:
        material = values.get("haz_material", MATERIALS[0])
        if material == MATERIALS[1]:
            if values.get("haz_confirm") is not True:
                raise InputError("Confirma subconductores macizos, μr=1 y corriente uniforme (haz_confirm).")
            method = SOLID_UNIFORM
        elif material == MATERIALS[2]:
            method = MANUFACTURER
        else:
            raise InputError("Selecciona el modelo inductivo del subconductor (haz_material).")
        inputs_list = []
        for spec in geometry.specs:
            phase = spec.center.phase
            data = RMGInput(spec.radius_m,method,values.get(f"haz_g_{phase}"),values.get("haz_source", ""))
            try:
                resolve_rmg(data)
            except InputError as exc:
                raise InputError(f"RMG fase {phase} (haz_g_{phase}, haz_source): {exc}") from exc
            inputs_list.append(data)
        inputs = tuple(inputs_list)
    except InputError as exc:
        inductance_error = str(exc)
    return {"geometry":geometry,"rmg_inputs":inputs,"inductance_model":ind_choices[ind_choice],
            "capacitance_model":cap_choices[cap_choice],"inductance_error":inductance_error}
