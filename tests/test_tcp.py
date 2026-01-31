"""
Unit tests for TCP (Tumor Control Probability) calculation.
"""

import pytest
import numpy as np
from models.tcp_niemierko import (
    calculate_eud,
    calculate_tcp,
    calculate_tcp_from_dvh,
    cumulative_to_differential_dvh
)


class TestEUD:
    """Test Equivalent Uniform Dose calculation."""

    def test_eud_uniform_dose_equals_dose(self):
        """
        For uniform dose (all bins same), EUD should equal that dose.

        """
        dose = 50.0
        doses = np.array([dose, dose, dose, dose])
        volumes = np.array([0.25, 0.25, 0.25, 0.25])  # uniform
        a = -10

        eud = calculate_eud(doses, volumes, a)

        # For uniform dose, EUD = D regardless of 'a'
        assert np.isclose(eud, dose, rtol=1e-6), f"Expected {dose}, got {eud}"

    def test_eud_positive_for_tumor(self):
        """
        For tumor (a < 0), EUD should be weighted toward lower doses.

            - Behavior tests are more robust than exact number tests
        """
        doses = np.array([40.0, 50.0, 60.0])
        volumes = np.array([0.2, 0.5, 0.3])
        a = -10  # tumor parameter

        eud = calculate_eud(doses, volumes, a)

        # EUD should be between min and max dose
        assert doses.min() <= eud <= doses.max()

        # For a < 0, EUD should be closer to lower doses
        weighted_mean = np.sum(doses * volumes)
        assert eud < weighted_mean  # EUD < mean for tumor

    def test_eud_raises_on_mismatched_lengths(self):
        """
        Should raise ValueError if doses and volumes have different lengths.

        """
        doses = np.array([50.0, 60.0])
        volumes = np.array([0.5, 0.3, 0.2])  # different length!
        a = -10

        with pytest.raises(ValueError, match="same length"):
            calculate_eud(doses, volumes, a)

    def test_eud_raises_on_volumes_not_summing_to_one(self):
        """
        Should raise ValueError if volumes don't sum to ~1.0.

            - Error message should be helpful (tell user what's wrong)
        """
        doses = np.array([50.0, 60.0, 70.0])
        volumes = np.array([0.2, 0.3, 0.3])  # sum = 0.8, not 1.0!
        a = -10

        with pytest.raises(ValueError, match="sum to ~1.0"):
            calculate_eud(doses, volumes, a)


class TestTCP:
    """Test Tumor Control Probability calculation."""

    def test_tcp_at_tcd50_equals_half(self):
        """
        When EUD = TCD50, TCP should be exactly 0.5.

            - Mathematical property that MUST hold
        """
        eud = 60.0
        tcd50 = 60.0
        gamma50 = 2.0

        tcp = calculate_tcp(eud, tcd50, gamma50)

        assert np.isclose(tcp, 0.5, atol=1e-9), f"Expected 0.5, got {tcp}"

    def test_tcp_increases_with_dose(self):
        """
        TCP should increase monotonically with EUD.

        """
        tcd50 = 60.0
        gamma50 = 2.0

        tcp_low = calculate_tcp(eud_gy=50.0, tcd50_gy=tcd50, gamma50=gamma50)
        tcp_mid = calculate_tcp(eud_gy=60.0, tcd50_gy=tcd50, gamma50=gamma50)
        tcp_high = calculate_tcp(eud_gy=70.0, tcd50_gy=tcd50, gamma50=gamma50)

        assert tcp_low < tcp_mid < tcp_high, "TCP should increase with dose"

    def test_tcp_in_valid_range(self):
        """
        TCP should always be in range [0, 1].

            - Probabilities MUST be in [0, 1]
        """
        tcd50 = 60.0
        gamma50 = 2.0

        for eud in [10.0, 30.0, 50.0, 70.0, 100.0]:
            tcp = calculate_tcp(eud, tcd50, gamma50)
            assert 0 <= tcp <= 1, f"TCP {tcp} out of range [0, 1] for EUD={eud}"

    def test_tcp_raises_on_invalid_params(self):
        """
        Should raise ValueError for invalid parameters.

        """
        with pytest.raises(ValueError):
            calculate_tcp(eud_gy=-10.0, tcd50_gy=60.0, gamma50=2.0)

        with pytest.raises(ValueError):
            calculate_tcp(eud_gy=60.0, tcd50_gy=-60.0, gamma50=2.0)

        with pytest.raises(ValueError):
            calculate_tcp(eud_gy=60.0, tcd50_gy=60.0, gamma50=-2.0)


class TestCumulativeToDifferential:
    """Test DVH conversion from cumulative to differential."""

    def test_cumulative_to_differential_simple(self):
        """
        Test basic cumulative -> differential conversion.

            - Hand-calculated expected values
        """
        doses = np.array([0.0, 10.0, 20.0, 30.0])
        cumulative = np.array([1.0, 0.8, 0.5, 0.0])

        # Expected differential:
        # bin 0: 1.0 - 0.8 = 0.2
        # bin 1: 0.8 - 0.5 = 0.3
        # bin 2: 0.5 - 0.0 = 0.5
        # bin 3: 0.0 (last bin)
        expected = np.array([0.2, 0.3, 0.5, 0.0])

        diff = cumulative_to_differential_dvh(doses, cumulative)

        np.testing.assert_allclose(diff, expected, rtol=1e-6)

    def test_differential_sums_to_one(self):
        """
        Differential volumes should sum to 1.0 (or initial cumulative value).

            - Sum of probabilities = 1
        """
        doses = np.array([0.0, 20.0, 40.0, 60.0, 80.0])
        cumulative = np.array([1.0, 0.9, 0.6, 0.3, 0.0])

        diff = cumulative_to_differential_dvh(doses, cumulative)

        assert np.isclose(np.sum(diff), 1.0, atol=1e-6)


class TestTCPFromDVH:
    """Test high-level TCP calculation from DVH."""

    def test_tcp_from_dvh_returns_correct_structure(self):
        """
        Test that output has correct structure for JSON export.

        """
        doses = np.array([40.0, 50.0, 60.0, 70.0])
        volumes = np.array([0.1, 0.3, 0.4, 0.2])  # differential
        params = {'a': -10, 'tcd50_gy': 60.0, 'gamma50': 2.0}

        result = calculate_tcp_from_dvh(doses, volumes, params)

        # Check structure
        assert 'eud_gy' in result
        assert 'tcp' in result
        assert 'parameters' in result

        # Check types
        assert isinstance(result['eud_gy'], float)
        assert isinstance(result['tcp'], float)
        assert isinstance(result['parameters'], dict)

        # Check values in valid ranges
        assert result['eud_gy'] > 0
        assert 0 <= result['tcp'] <= 1

    def test_tcp_from_dvh_raises_on_missing_params(self):
        """
        Should raise ValueError if required parameters missing.

            - Config errors should fail fast
        """
        doses = np.array([50.0, 60.0])
        volumes = np.array([0.5, 0.5])

        # Missing 'gamma50'
        params = {'a': -10, 'tcd50_gy': 60.0}

        with pytest.raises(ValueError, match="Missing required parameter"):
            calculate_tcp_from_dvh(doses, volumes, params)


@pytest.fixture
def sample_dvh():
    """
    Fixture providing sample DVH data for tests.

        - Makes tests cleaner and more maintainable
    """
    return {
        'doses': np.array([0.0, 20.0, 40.0, 60.0, 80.0]),
        'cumulative_volumes': np.array([1.0, 0.9, 0.6, 0.2, 0.0]),
        'params': {'a': -10, 'tcd50_gy': 60.0, 'gamma50': 2.0}
    }


def test_full_workflow_with_fixture(sample_dvh):
    """
    Test complete workflow: cumulative DVH -> differential -> EUD -> TCP.

    """
    # Convert cumulative to differential
    diff_volumes = cumulative_to_differential_dvh(
        sample_dvh['doses'],
        sample_dvh['cumulative_volumes']
    )

    # Calculate TCP
    result = calculate_tcp_from_dvh(
        sample_dvh['doses'],
        diff_volumes,
        sample_dvh['params']
    )

    # Sanity checks
    assert result['eud_gy'] > 0
    assert 0 <= result['tcp'] <= 1
    assert result['parameters']['a'] == -10


if __name__ == "__main__":
    # Allow running tests directly: python -m tests.test_tcp
    pytest.main([__file__, "-v"])
