"""
DVH metrics for lung tissue.

Metrics:
    - Mean Lung Dose (MLD): Average dose to lung
    - V5: Percentage of lung volume receiving ≥5 Gy
    - V20: Percentage of lung volume receiving ≥20 Gy
"""

import numpy as np
from typing import Dict


def calculate_mean_dose(doses_gy: np.ndarray, volumes_frac: np.ndarray) -> float:
    """
    Calculate mean dose from differential DVH.

    Formula:
        Mean Dose = Σ (vᵢ × Dᵢ)

    Args:
        doses_gy: Dose bins in Gy
        volumes_frac: Differential volumes (must sum to ~1.0)

    Returns:
        Mean dose in Gy
    """
    if len(doses_gy) != len(volumes_frac):
        raise ValueError("doses and volumes must have same length")

    if not np.isclose(np.sum(volumes_frac), 1.0, atol=0.01):
        raise ValueError(f"Volumes must sum to ~1.0 (got {np.sum(volumes_frac):.4f})")

    mean_dose = np.sum(doses_gy * volumes_frac)
    return float(mean_dose)


def calculate_vx(
    doses_gy: np.ndarray,
    cumulative_volumes_frac: np.ndarray,
    threshold_gy: float
) -> float:
    """
    Calculate Vx: percentage of volume receiving ≥ threshold dose.

    Args:
        doses_gy: Dose bins in Gy (sorted ascending)
        cumulative_volumes_frac: Cumulative volumes (fraction 0-1)
        threshold_gy: Dose threshold in Gy (e.g., 5 or 20)

    Returns:
        Volume percentage receiving ≥ threshold (0-100)

    Example:
        >>> v5 = calculate_vx(doses, cumulative_volumes, threshold_gy=5.0)
        >>> v5
        45.0  # 45% of lung receives ≥5 Gy
    """
    if len(doses_gy) != len(cumulative_volumes_frac):
        raise ValueError("doses and volumes must have same length")

    if threshold_gy < 0:
        raise ValueError(f"Threshold must be non-negative, got {threshold_gy}")

    # Find volume at threshold dose using linear interpolation
    if threshold_gy <= doses_gy[0]:
        # Threshold below minimum dose -> all volume receives this dose
        vx_frac = cumulative_volumes_frac[0]
    elif threshold_gy >= doses_gy[-1]:
        # Threshold above maximum dose -> last volume value
        vx_frac = cumulative_volumes_frac[-1]
    else:
        # Interpolate
        vx_frac = np.interp(threshold_gy, doses_gy, cumulative_volumes_frac)

    # Convert to percentage
    vx_percent = vx_frac * 100.0

    return float(vx_percent)


def calculate_lung_metrics(
    doses_gy: np.ndarray,
    differential_volumes_frac: np.ndarray,
    cumulative_volumes_frac: np.ndarray
) -> Dict[str, float]:
    """
    Calculate standard lung DVH metrics.

    Args:
        doses_gy: Dose bins in Gy
        differential_volumes_frac: Differential volumes (for mean dose)
        cumulative_volumes_frac: Cumulative volumes (for Vx)

    Returns:
        Dict with keys:
            - 'mean_dose_gy': Mean lung dose
            - 'v5_percent': Percentage of lung receiving ≥5 Gy
            - 'v20_percent': Percentage of lung receiving ≥20 Gy
    """
    mld = calculate_mean_dose(doses_gy, differential_volumes_frac)
    v5 = calculate_vx(doses_gy, cumulative_volumes_frac, threshold_gy=5.0)
    v20 = calculate_vx(doses_gy, cumulative_volumes_frac, threshold_gy=20.0)

    return {
        'mean_dose_gy': mld,
        'v5_percent': v5,
        'v20_percent': v20,
    }
