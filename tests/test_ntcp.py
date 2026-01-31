"""
Unit tests for NTCP (Normal Tissue Complication Probability) calculation.
"""

import pytest
import numpy as np
from models.ntcp_lkb import (
    calculate_deff,
    calculate_ntcp,
    calculate_ntcp_from_dvh
)


class TestDeff:
    """Test effective dose calculation."""

    def test_deff_uniform_dose_equals_dose(self):
        """For uniform dose, Deff should equal that dose."""
        dose = 20.0
        doses = np.array([dose, dose, dose, dose])
        volumes = np.array([0.25, 0.25, 0.25, 0.25])
        n = 0.87

        deff = calculate_deff(doses, volumes, n)

        assert np.isclose(deff, dose, rtol=1e-6), f"Expected {dose}, got {deff}"

    def test_deff_positive(self):
        """Deff should be between min and max dose."""
        doses = np.array([10.0, 20.0, 30.0])
        volumes = np.array([0.2, 0.5, 0.3])
        n = 0.87

        deff = calculate_deff(doses, volumes, n)

        assert doses.min() <= deff <= doses.max()

    def test_deff_raises_on_mismatched_lengths(self):
        """Should raise ValueError if doses and volumes have different lengths."""
        doses = np.array([10.0, 20.0])
        volumes = np.array([0.5, 0.3, 0.2])
        n = 0.87

        with pytest.raises(ValueError, match="same length"):
            calculate_deff(doses, volumes, n)

    def test_deff_raises_on_volumes_not_summing_to_one(self):
        """Should raise ValueError if volumes don't sum to ~1.0."""
        doses = np.array([10.0, 20.0, 30.0])
        volumes = np.array([0.2, 0.3, 0.3])  # sum = 0.8
        n = 0.87

        with pytest.raises(ValueError, match="sum to ~1.0"):
            calculate_deff(doses, volumes, n)

    def test_deff_raises_on_invalid_n(self):
        """Should raise ValueError if n <= 0."""
        doses = np.array([10.0, 20.0])
        volumes = np.array([0.5, 0.5])

        with pytest.raises(ValueError):
            calculate_deff(doses, volumes, n=-0.87)

        with pytest.raises(ValueError):
            calculate_deff(doses, volumes, n=0.0)


class TestNTCP:
    """Test NTCP calculation."""

    def test_ntcp_at_td50_equals_half(self):
        """When Deff = TD50, NTCP should be exactly 0.5."""
        deff = 24.5
        td50 = 24.5
        m = 0.18

        ntcp = calculate_ntcp(deff, td50, m)

        assert np.isclose(ntcp, 0.5, atol=1e-9), f"Expected 0.5, got {ntcp}"

    def test_ntcp_increases_with_dose(self):
        """NTCP should increase monotonically with Deff."""
        td50 = 24.5
        m = 0.18

        ntcp_low = calculate_ntcp(deff_gy=10.0, td50_gy=td50, m=m)
        ntcp_mid = calculate_ntcp(deff_gy=24.5, td50_gy=td50, m=m)
        ntcp_high = calculate_ntcp(deff_gy=40.0, td50_gy=td50, m=m)

        assert ntcp_low < ntcp_mid < ntcp_high, "NTCP should increase with dose"

    def test_ntcp_in_valid_range(self):
        """NTCP should always be in range [0, 1]."""
        td50 = 24.5
        m = 0.18

        for deff in [0.0, 10.0, 24.5, 40.0, 60.0]:
            ntcp = calculate_ntcp(deff, td50, m)
            assert 0 <= ntcp <= 1, f"NTCP {ntcp} out of range [0, 1] for Deff={deff}"

    def test_ntcp_raises_on_invalid_params(self):
        """Should raise ValueError for invalid parameters."""
        with pytest.raises(ValueError):
            calculate_ntcp(deff_gy=-10.0, td50_gy=24.5, m=0.18)

        with pytest.raises(ValueError):
            calculate_ntcp(deff_gy=24.5, td50_gy=-24.5, m=0.18)

        with pytest.raises(ValueError):
            calculate_ntcp(deff_gy=24.5, td50_gy=24.5, m=-0.18)


class TestNTCPFromDVH:
    """Test high-level NTCP calculation from DVH."""

    def test_ntcp_from_dvh_returns_correct_structure(self):
        """Test that output has correct structure for JSON export."""
        doses = np.array([0.0, 10.0, 20.0, 30.0])
        volumes = np.array([0.1, 0.3, 0.4, 0.2])
        params = {
            'n': 0.87,
            'm': 0.18,
            'td50_gy': 24.5,
            'endpoint': 'pneumonitis grade ≥2'
        }

        result = calculate_ntcp_from_dvh(doses, volumes, params)

        assert 'deff_gy' in result
        assert 'ntcp' in result
        assert 'endpoint' in result
        assert 'parameters' in result

        assert isinstance(result['deff_gy'], float)
        assert isinstance(result['ntcp'], float)
        assert isinstance(result['endpoint'], str)
        assert isinstance(result['parameters'], dict)

        assert result['deff_gy'] >= 0
        assert 0 <= result['ntcp'] <= 1
        assert result['endpoint'] == 'pneumonitis grade ≥2'

    def test_ntcp_from_dvh_raises_on_missing_params(self):
        """Should raise ValueError if required parameters missing."""
        doses = np.array([10.0, 20.0])
        volumes = np.array([0.5, 0.5])

        params = {'n': 0.87, 'm': 0.18}  # missing td50_gy

        with pytest.raises(ValueError, match="Missing required parameter"):
            calculate_ntcp_from_dvh(doses, volumes, params)


@pytest.fixture
def lung_dvh():
    """Fixture providing sample lung DVH data."""
    return {
        'doses': np.array([0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0]),
        'cumulative_volumes': np.array([1.0, 0.8, 0.6, 0.4, 0.2, 0.1, 0.0]),
        'params': {
            'n': 0.87,
            'm': 0.18,
            'td50_gy': 24.5,
            'endpoint': 'pneumonitis grade ≥2'
        }
    }


def test_full_ntcp_workflow(lung_dvh):
    """Test complete NTCP workflow."""
    from models.tcp_niemierko import cumulative_to_differential_dvh

    diff_volumes = cumulative_to_differential_dvh(
        lung_dvh['doses'],
        lung_dvh['cumulative_volumes']
    )

    result = calculate_ntcp_from_dvh(
        lung_dvh['doses'],
        diff_volumes,
        lung_dvh['params']
    )

    assert result['deff_gy'] > 0
    assert 0 <= result['ntcp'] <= 1
    assert result['parameters']['n'] == 0.87


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
