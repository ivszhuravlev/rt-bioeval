"""
Unit tests for NTCP (Normal Tissue Complication Probability) calculation.
Uses Niemierko EUD-logistic model.
"""

import pytest
import numpy as np
from models.tcp_niemierko import (
    calculate_eud,
    calculate_ntcp,
    calculate_ntcp_from_dvh
)


class TestEUDforNTCP:
    """Test EUD calculation for NTCP (with positive a parameters)."""

    def test_eud_uniform_dose_equals_dose(self):
        """For uniform dose, EUD should equal that dose."""
        dose = 20.0
        doses = np.array([dose, dose, dose, dose])
        volumes = np.array([0.25, 0.25, 0.25, 0.25])
        a = 1  # For lung (mean dose)

        eud = calculate_eud(doses, volumes, a)

        assert np.isclose(eud, dose, rtol=1e-6), f"Expected {dose}, got {eud}"

    def test_eud_lung_equals_mean_dose(self):
        """For lung (a=1), EUD should equal mean dose."""
        doses = np.array([10.0, 20.0, 30.0])
        volumes = np.array([0.2, 0.5, 0.3])
        a = 1

        eud = calculate_eud(doses, volumes, a)
        mean_dose = np.sum(doses * volumes)

        assert np.isclose(eud, mean_dose, rtol=1e-6)

    def test_eud_serial_organ_near_max(self):
        """For serial organ (large a), EUD should be near max dose."""
        doses = np.array([10.0, 20.0, 50.0])  # max = 50
        volumes = np.array([0.8, 0.15, 0.05])  # small volume at high dose
        a = 20  # spinal cord

        eud = calculate_eud(doses, volumes, a)

        # EUD should be close to max dose for serial organ
        assert eud > 40.0  # closer to 50 than to mean


class TestNTCP:
    """Test NTCP calculation (logistic model)."""

    def test_ntcp_at_td50_equals_half(self):
        """When EUD = TD50, NTCP should be exactly 0.5."""
        td50 = 24.5
        ntcp = calculate_ntcp(eud_gy=td50, td50_gy=td50, gamma50=2.0)

        assert np.isclose(ntcp, 0.5, atol=1e-10)

    def test_ntcp_increases_with_dose(self):
        """NTCP should increase as EUD increases."""
        td50 = 24.5
        gamma50 = 2.0

        ntcp_low = calculate_ntcp(eud_gy=20.0, td50_gy=td50, gamma50=gamma50)
        ntcp_mid = calculate_ntcp(eud_gy=24.5, td50_gy=td50, gamma50=gamma50)
        ntcp_high = calculate_ntcp(eud_gy=30.0, td50_gy=td50, gamma50=gamma50)

        assert ntcp_low < ntcp_mid < ntcp_high

    def test_ntcp_in_valid_range(self):
        """NTCP should always be between 0 and 1."""
        for eud in [5.0, 24.5, 50.0, 100.0]:
            ntcp = calculate_ntcp(eud_gy=eud, td50_gy=24.5, gamma50=2.0)
            assert 0.0 <= ntcp <= 1.0

    def test_ntcp_zero_for_zero_eud(self):
        """NTCP should be 0 for zero EUD."""
        ntcp = calculate_ntcp(eud_gy=0.0, td50_gy=24.5, gamma50=2.0)
        assert ntcp == 0.0

    def test_ntcp_raises_on_invalid_params(self):
        """Should raise ValueError for invalid parameters."""
        with pytest.raises(ValueError):
            calculate_ntcp(eud_gy=-1, td50_gy=24.5, gamma50=2.0)

        with pytest.raises(ValueError):
            calculate_ntcp(eud_gy=20, td50_gy=0, gamma50=2.0)

        with pytest.raises(ValueError):
            calculate_ntcp(eud_gy=20, td50_gy=24.5, gamma50=-1)


class TestNTCPFromDVH:
    """Test high-level NTCP calculation from DVH."""

    def test_ntcp_from_dvh_returns_correct_structure(self):
        """Should return dict with eud_gy, ntcp, and parameters."""
        doses = np.array([10.0, 20.0, 30.0])
        volumes = np.array([0.2, 0.5, 0.3])
        params = {'a': 1, 'td50_gy': 24.5, 'gamma50': 2.0}

        result = calculate_ntcp_from_dvh(doses, volumes, params)

        assert 'eud_gy' in result
        assert 'ntcp' in result
        assert 'parameters' in result

    def test_ntcp_from_dvh_raises_on_missing_params(self):
        """Should raise ValueError if required parameters missing."""
        doses = np.array([10.0, 20.0, 30.0])
        volumes = np.array([0.2, 0.5, 0.3])

        with pytest.raises(ValueError, match="Missing required parameter"):
            calculate_ntcp_from_dvh(doses, volumes, {'a': 1})


def test_full_ntcp_workflow():
    """
    Integration test: Full NTCP workflow for lung.

    Lung parameters: a=1 (mean dose), TD50=24.5 Gy, gamma50=2
    """
    # Simulated lung DVH
    doses = np.linspace(0, 40, 100)
    volumes = np.exp(-doses / 15.0)  # exponential decay
    volumes = volumes / volumes.sum()  # normalize

    params = {
        'a': 1,           # mean dose
        'td50_gy': 24.5,
        'gamma50': 2.0
    }

    result = calculate_ntcp_from_dvh(doses, volumes, params)

    # Check results are reasonable
    assert 0 < result['eud_gy'] < 40
    assert 0 < result['ntcp'] < 1
    assert result['parameters']['a'] == 1
