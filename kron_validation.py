"""Contraste independiente de Kron con las ecuaciones completas de frontera."""

from dataclasses import dataclass
import numpy as np
from scipy.linalg import solve
from .models import InputError


@dataclass(frozen=True)
class GuardValidation:
    independent_z_ohm_per_m: np.ndarray
    relative_error: float
    max_error_ohm_per_m: float
    boundary_residual: float


def validate_two_guards(augmented,reduced):
    """No usa reduce_kron ni su complemento de Schur.

    Impone Ip=Icolumna y ΔVn=0 simultáneamente mediante un sistema completo
    con scipy.linalg.solve, y calcula ΔVp=Zprimitiva I por multiplicación.
    La normalización de filas auxiliares evita mezclar escalas numéricas.
    Esta comparación verifica álgebra, no la hipótesis física de puesta a tierra.
    """
    if len(augmented.auxiliaries)!=2 or any(a.role!="guard" for a in augmented.auxiliaries):
        raise InputError("La validación independiente requiere exactamente dos cables de guarda.")
    n = len(augmented.phase_labels)
    z = augmented.z_ohm_per_m
    scale = max(float(np.max(np.abs(z[n:,:]))),np.finfo(float).tiny)
    constraints = np.vstack((np.hstack((np.eye(n),np.zeros((n,2)))),z[n:,:]/scale))
    rhs = np.vstack((np.eye(n),np.zeros((2,n))))
    try:
        response = solve(constraints,rhs,assume_a="gen",check_finite=True)
    except (ValueError,np.linalg.LinAlgError) as exc:
        raise InputError("No se pudo resolver el contraste independiente de dos guardas.") from exc
    drops = z @ response
    reference = drops[:n,:]
    error = reference-reduced.z_ohm_per_m
    relative = float(np.linalg.norm(error)/max(np.linalg.norm(reference),np.finfo(float).tiny))
    boundary = float(np.linalg.norm(drops[n:,:])/max(np.linalg.norm(z)*np.linalg.norm(response),np.finfo(float).tiny))
    return GuardValidation(reference,relative,float(np.max(np.abs(error))),boundary)
