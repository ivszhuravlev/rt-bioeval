"""
DVH metrics for spinal cord.

Metrics:
    - Dmax: Maximum dose
    - D0.1cc: Dose to 0.1 cc of volume
    - D1cc: Dose to 1 cc of volume
"""

import numpy as np
from typing import Dict, Optional


def calculate_dmax(doses_gy: np.ndarray) -> float:
    """
    Calculate maximum dose.

    Args:
        doses_gy: Dose bins in Gy

    Returns:
        Maximum dose in Gy
    """
    if len(doses_gy) == 0:
        raise ValueError("Empty dose array")

    return float(np.max(doses_gy))


def calculate_dx_cc(
    doses_gy: np.ndarray,
    cumulative_volumes_cc: np.ndarray,
    volume_cc: float
) -> float:
    """
    Calculate Dx: dose to x cc of volume.

    Args:
        doses_gy: Dose bins in Gy (sorted ascending)
        cumulative_volumes_cc: Cumulative volumes in cc (NOT fraction)
        volume_cc: Volume threshold in cc (e.g., 0.1 or 1.0)

    Returns:
        Dose in Gy received by volume_cc

    Example:
        >>> d01cc = calculate_dx_cc(doses, cumulative_volumes_cc, volume_cc=0.1)
        >>> d01cc
        42.5  # 0.1 cc receives 42.5 Gy
    """
    if len(doses_gy) != len(cumulative_volumes_cc):
        raise ValueError("doses and volumes must have same length")

    if volume_cc < 0:
        raise ValueError(f"Volume must be non-negative, got {volume_cc}")

    # DVH is cumulative: larger volume at lower doses
    # We need dose where cumulative volume = volume_cc
    # If cumulative volumes are in descending order (standard DVH), we interpolate

    # Check if volume_cc is outside range
    max_volume = cumulative_volumes_cc[0]  # Maximum volume (at lowest dose)
    min_volume = cumulative_volumes_cc[-1]  # Minimum volume (at highest dose)

    if volume_cc > max_volume:
        # Volume larger than structure -> return lowest dose
        return float(doses_gy[0])
    elif volume_cc < min_volume:
        # Volume smaller than minimum -> return highest dose
        return float(doses_gy[-1])
    else:
        # Interpolate: find dose where cumulative volume = volume_cc
        # Since cumulative volume decreases with dose, we reverse for interpolation
        dx = np.interp(volume_cc, cumulative_volumes_cc[::-1], doses_gy[::-1])
        return float(dx)


def calculate_cord_metrics(
    doses_gy: np.ndarray,
    cumulative_volumes_frac: Optional[np.ndarray] = None,
    total_volume_cc: Optional[float] = None
) -> Dict[str, float]:
    """
    Calculate spinal cord DVH metrics.

    Args:
        doses_gy: Dose bins in Gy
        cumulative_volumes_frac: Cumulative volumes as fraction (0-1), optional
        total_volume_cc: Total structure volume in cc, optional for D0.1cc/D1cc

    Returns:
        Dict with keys:
            - 'dmax_gy': Maximum dose (always available)
            - 'd0_1cc_gy': Dose to 0.1 cc (only if total_volume_cc provided)
            - 'd1cc_gy': Dose to 1 cc (only if total_volume_cc provided)
    """
    metrics = {
        'dmax_gy': calculate_dmax(doses_gy)
    }

    # D0.1cc and D1cc require absolute volumes (cc)
    if cumulative_volumes_frac is not None and total_volume_cc is not None:
        # Convert fraction to cc
        cumulative_volumes_cc = cumulative_volumes_frac * total_volume_cc

        metrics['d0_1cc_gy'] = calculate_dx_cc(doses_gy, cumulative_volumes_cc, volume_cc=0.1)
        metrics['d1cc_gy'] = calculate_dx_cc(doses_gy, cumulative_volumes_cc, volume_cc=1.0)

    return metrics
