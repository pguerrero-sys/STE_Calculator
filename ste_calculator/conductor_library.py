"""Biblioteca local transcrita de las columnas publicadas, sin estimar materiales."""
from dataclasses import dataclass
import json
from pathlib import Path

from .models import InputError


@dataclass(frozen=True)
class ConductorData:
    designation: str
    gauge: str
    aluminium_strands: int | None
    steel_strands: int | None
    diameter_m: float | None
    gmr_m: float | None
    nominal_current_a: float | None
    r_dc20_ohm_km: float | None
    r_ac_ohm_km: dict
    sources: dict
    warnings: tuple = ()
    resistance_frequency_hz: float = 60.0
    rmg_method: str = 'manufacturer'

    @property
    def radius_m(self):
        return None if self.diameter_m is None else self.diameter_m/2


def load_catalog():
    data=json.loads((Path(__file__).resolve().parents[1]/'referencias/acsr_catalog.json').read_text(encoding='utf-8'))
    return {r['designation']:ConductorData(**{k:v for k,v in r.items() if k!='raw_rows'}) for r in data['records']}


def conductor(name):
    try:
        return load_catalog()[name]
    except KeyError as exc:
        raise InputError('Conductor no encontrado en la biblioteca ACSR.') from exc
