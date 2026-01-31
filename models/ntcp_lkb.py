"""
NTCP (Normal Tissue Complication Probability) calculation using Lyman-Kutcher-Burman model.

References:
    Lyman JT. (1985). Complication probability as assessed from dose-volume histograms.
    Radiat Res Suppl 8:S13-19.

    Kutcher GJ, Burman C. (1989). Calculation of complication probability factors for
    non-uniform normal tissue irradiation: the effective volume method.
    Int J Radiat Oncol Biol Phys 16(6):1623-1630.
"""

import numpy as np
from scipy.special import ndtr
from typing import Dict, Any


def calculate_deff(doses_gy: np.ndarray, volumes_frac: np.ndarray, n: float) -> float:
    """
    Calculate effective dose (Deff) using Lyman-Kutcher-Burman formula.

    Formula:
        Deff = ( Σ vᵢ × Dᵢ^(1/n) )^n

    Args:
        doses_gy: Dose bins in Gy (1D array, sorted ascending)
        volumes_frac: Differential volumes (1D array, same length as doses)
                     Must sum to ~1.0
        n: Volume parameter (organ-specific, typically 0.05-1.0)

    Returns:
        Effective dose in Gy

    Raises:
        ValueError: If inputs are invalid

    Example:
        >>> doses = np.array([10.0, 20.0, 30.0])
        >>> volumes = np.array([0.3, 0.5, 0.2])  # differential volumes
        >>> deff = calculate_deff(doses, volumes, n=0.87)
        >>> deff
        20.5  # approximately
    """
    if len(doses_gy) != len(volumes_frac):
        raise ValueError(
            f"doses and volumes must have same length: "
            f"got {len(doses_gy)} vs {len(volumes_frac)}"
        )

    if not np.isclose(np.sum(volumes_frac), 1.0, atol=0.01):
        raise ValueError(
            f"Volumes must sum to ~1.0 (got {np.sum(volumes_frac):.4f})"
        )

    if n <= 0:
        raise ValueError(f"Parameter 'n' must be positive, got {n}")

    mask = doses_gy > 0
    doses = doses_gy[mask]
    volumes = volumes_frac[mask]

    if len(doses) == 0:
        return 0.0

    # Deff = ( Σ vᵢ × Dᵢ^(1/n) )^n
    powered_doses = np.power(doses, 1.0 / n)
    weighted_sum = np.sum(volumes * powered_doses)
    deff = np.power(weighted_sum, n)

    return float(deff)


def calculate_ntcp(deff_gy: float, td50_gy: float, m: float) -> float:
    """
    Calculate NTCP from effective dose using Lyman-Kutcher-Burman model.

    Formula:
        t = (Deff - TD50) / (m × TD50)
        NTCP = Φ(t)

    where Φ(t) is the cumulative normal distribution.

    Args:
        deff_gy: Effective dose in Gy
        td50_gy: Dose for 50% complication probability (Gy)
        m: Slope parameter of dose-response curve (dimensionless)

    Returns:
        NTCP as probability in range [0, 1]

    Raises:
        ValueError: If parameters are invalid

    Example:
        >>> ntcp = calculate_ntcp(deff_gy=24.5, td50_gy=24.5, m=0.18)
        >>> ntcp
        0.5  # exactly 0.5 when Deff = TD50
    """
    if deff_gy < 0:
        raise ValueError(f"Deff must be non-negative, got {deff_gy}")

    if td50_gy <= 0:
        raise ValueError(f"TD50 must be positive, got {td50_gy}")

    if m <= 0:
        raise ValueError(f"m must be positive, got {m}")

    # t = (Deff - TD50) / (m × TD50)
    t = (deff_gy - td50_gy) / (m * td50_gy)

    # NTCP = Φ(t) using scipy.special.ndtr (faster than scipy.stats.norm.cdf)
    ntcp = ndtr(t)

    return float(ntcp)


def calculate_ntcp_from_dvh(
    doses_gy: np.ndarray,
    volumes_frac: np.ndarray,
    params: Dict[str, Any]
) -> Dict[str, float]:
    """
    Calculate NTCP from DVH data using LKB model.

    Args:
        doses_gy: Dose bins in Gy
        volumes_frac: Differential volumes (must sum to ~1.0)
        params: Dict with keys 'n', 'm', 'td50_gy', 'endpoint' (optional)

    Returns:
        Dict with keys:
            - 'deff_gy': Effective dose
            - 'ntcp': Normal Tissue Complication Probability
            - 'endpoint': Clinical endpoint description
            - 'parameters': Copy of input parameters

    Example:
        >>> params = {'n': 0.87, 'm': 0.18, 'td50_gy': 24.5, 'endpoint': 'pneumonitis grade ≥2'}
        >>> result = calculate_ntcp_from_dvh(doses, volumes, params)
        >>> result['ntcp']
        0.12
    """
    required_keys = ['n', 'm', 'td50_gy']
    for key in required_keys:
        if key not in params:
            raise ValueError(f"Missing required parameter: {key}")

    n = params['n']
    m = params['m']
    td50_gy = params['td50_gy']
    endpoint = params.get('endpoint', 'not specified')

    deff_gy = calculate_deff(doses_gy, volumes_frac, n)
    ntcp = calculate_ntcp(deff_gy, td50_gy, m)

    return {
        'deff_gy': deff_gy,
        'ntcp': ntcp,
        'endpoint': endpoint,
        'parameters': {
            'n': n,
            'm': m,
            'td50_gy': td50_gy,
        }
    }
