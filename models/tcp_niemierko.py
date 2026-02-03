"""
TCP (Tumor Control Probability) calculation using Niemierko's EUD-based model.

References:
    Niemierko A. (1997). Reporting and analyzing dose distributions: a concept of
    equivalent uniform dose. Med Phys 24(1):103-110.
"""

import numpy as np
from typing import Dict, Any


def calculate_eud(doses_gy: np.ndarray, volumes_frac: np.ndarray, a: float) -> float:
    """
    Calculate Equivalent Uniform Dose (EUD) using Niemierko's formula.

    Formula:
        EUD = ( Σ vᵢ × Dᵢᵃ )^(1/a)

    Args:
        doses_gy: Dose bins in Gy (1D array, sorted ascending)
        volumes_frac: Fractional volumes (1D array, same length as doses)
                     Must be differential volumes (NOT cumulative)
        a: Tissue-specific parameter (negative for tumors, e.g., -10)

    Returns:
        EUD in Gy

    Raises:
        ValueError: If inputs are invalid (different lengths, zero volume, etc.)

    Example:
        >>> doses = np.array([50.0, 60.0, 70.0])
        >>> volumes = np.array([0.2, 0.5, 0.3])  # differential volumes
        >>> eud = calculate_eud(doses, volumes, a=-10)
        >>> eud
        62.5  # approximately
    """
    if len(doses_gy) != len(volumes_frac):
        raise ValueError(
            f"doses and volumes must have same length: "
            f"got {len(doses_gy)} vs {len(volumes_frac)}"
        )

    if not np.isclose(np.sum(volumes_frac), 1.0, atol=0.01):
        raise ValueError(
            f"Volumes must sum to ~1.0 (got {np.sum(volumes_frac):.4f}). "
            f"Did you pass cumulative DVH instead of differential?"
        )

    if a == 0:
        raise ValueError("Parameter 'a' cannot be zero")

    mask = doses_gy > 0
    doses = doses_gy[mask]
    volumes = volumes_frac[mask]

    if len(doses) == 0:
        return 0.0

    # EUD = ( Σ vᵢ × Dᵢᵃ )^(1/a)
    powered_doses = np.power(doses, a)
    weighted_sum = np.sum(volumes * powered_doses)
    eud = np.power(weighted_sum, 1.0 / a)

    return float(eud)


def calculate_tcp(
    eud_gy: float,
    tcd50_gy: float,
    gamma50: float
) -> float:
    """
    Calculate Tumor Control Probability (TCP) from EUD.

    Formula:
        TCP = 1 / ( 1 + (TCD50 / EUD)^(4×γ₅₀) )

    Args:
        eud_gy: Equivalent Uniform Dose in Gy
        tcd50_gy: Dose for 50% tumor control probability (Gy)
        gamma50: Slope of dose-response curve (dimensionless)

    Returns:
        TCP as probability in range [0, 1]

    Raises:
        ValueError: If parameters are invalid

    Example:
        >>> tcp = calculate_tcp(eud_gy=60.0, tcd50_gy=60.0, gamma50=2.0)
        >>> tcp
        0.5  # exactly 0.5 when EUD = TCD50
    """
    if eud_gy <= 0:
        raise ValueError(f"EUD must be positive, got {eud_gy}")

    if tcd50_gy <= 0:
        raise ValueError(f"TCD50 must be positive, got {tcd50_gy}")

    if gamma50 <= 0:
        raise ValueError(f"gamma50 must be positive, got {gamma50}")

    # TCP = 1 / ( 1 + (TCD50 / EUD)^(4×γ₅₀) )
    ratio = tcd50_gy / eud_gy
    exponent = 4 * gamma50
    tcp = 1.0 / (1.0 + np.power(ratio, exponent))

    return float(tcp)


def calculate_tcp_from_dvh(
    doses_gy: np.ndarray,
    volumes_frac: np.ndarray,
    params: Dict[str, Any]
) -> Dict[str, float]:
    """
    Calculate TCP from DVH data using Niemierko model.

    This is a high-level function that combines EUD + TCP calculation.

    Args:
        doses_gy: Dose bins in Gy
        volumes_frac: Differential volumes (must sum to ~1.0)
        params: Dict with keys 'a', 'tcd50_gy', 'gamma50'

    Returns:
        Dict with keys:
            - 'eud_gy': Equivalent Uniform Dose
            - 'tcp': Tumor Control Probability
            - 'parameters': Copy of input parameters

    Example:
        >>> params = {'a': -10, 'tcd50_gy': 60.0, 'gamma50': 2.0}
        >>> result = calculate_tcp_from_dvh(doses, volumes, params)
        >>> result['tcp']
        0.85
    """
    required_keys = ['a', 'tcd50_gy', 'gamma50']
    for key in required_keys:
        if key not in params:
            raise ValueError(f"Missing required parameter: {key}")

    a = params['a']
    tcd50_gy = params['tcd50_gy']
    gamma50 = params['gamma50']

    eud_gy = calculate_eud(doses_gy, volumes_frac, a)
    tcp = calculate_tcp(eud_gy, tcd50_gy, gamma50)

    return {
        'eud_gy': eud_gy,
        'tcp': tcp,
        'parameters': {
            'a': a,
            'tcd50_gy': tcd50_gy,
            'gamma50': gamma50,
        }
    }


def cumulative_to_differential_dvh(
    doses_gy: np.ndarray,
    cumulative_volumes_frac: np.ndarray
) -> np.ndarray:
    """
    Convert cumulative DVH to differential DVH.

    Cumulative DVH: V(D) = fraction of volume receiving ≥ D
    Differential DVH: dV = fraction of volume receiving exactly D

    Args:
        doses_gy: Dose bins (sorted ascending)
        cumulative_volumes_frac: Cumulative volumes (decreasing from 1.0 to 0.0)

    Returns:
        Differential volumes (sum = 1.0)
    """
    if len(doses_gy) != len(cumulative_volumes_frac):
        raise ValueError("doses and volumes must have same length")

    diff_volumes = np.zeros(len(doses_gy))

    for i in range(len(doses_gy) - 1):
        diff_volumes[i] = cumulative_volumes_frac[i] - cumulative_volumes_frac[i + 1]

    diff_volumes[-1] = cumulative_volumes_frac[-1]

    expected_sum = cumulative_volumes_frac[0]
    actual_sum = np.sum(diff_volumes)

    if not np.isclose(actual_sum, expected_sum, atol=0.01):
        raise ValueError(
            f"Differential volumes sum to {actual_sum:.4f}, "
            f"expected {expected_sum:.4f}"
        )

    return diff_volumes


def differential_to_cumulative_dvh(
    doses_gy: np.ndarray,
    differential_volumes_frac: np.ndarray
) -> np.ndarray:
    """
    Convert differential DVH to cumulative DVH.

    Differential DVH: dV = fraction of volume receiving exactly D
    Cumulative DVH: V(D) = fraction of volume receiving ≥ D

    Args:
        doses_gy: Dose bins (sorted ascending)
        differential_volumes_frac: Differential volumes (sum ≈ 1.0)

    Returns:
        Cumulative volumes (decreasing from 1.0 to ~0.0)
    """
    if len(doses_gy) != len(differential_volumes_frac):
        raise ValueError("doses and volumes must have same length")

    # Cumulative[i] = sum of all differential volumes from i to end
    # This is reverse cumsum
    cumulative_volumes = np.cumsum(differential_volumes_frac[::-1])[::-1]

    return cumulative_volumes
