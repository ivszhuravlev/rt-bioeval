"""
Unit tests for DVH parser.
"""

import pytest
import numpy as np
from pathlib import Path
from dvh.parser import parse_dvh_file, DVHData


def test_dvh_data_sort_and_clean():
    """Test that DVHData sorts by dose and removes duplicates."""
    doses = np.array([0.0, 50.0, 30.0, 50.0, 60.0])  # unsorted with duplicate
    volumes = np.array([1.0, 0.5, 0.7, 0.4, 0.2])

    dvh = DVHData("TEST", doses, volumes)

    # Should be sorted by dose
    assert np.all(dvh.doses_gy[:-1] <= dvh.doses_gy[1:])

    # Should have no duplicate doses
    assert len(np.unique(dvh.doses_gy)) == len(dvh.doses_gy)

    # Should have correct length after duplicate removal
    assert len(dvh.doses_gy) == 4  # 0, 30, 50 (one duplicate removed), 60


def test_parse_real_dvh_file():
    """Test parsing a real DVH file from input directory."""
    # Find first available DVH file
    input_dir = Path(__file__).parent.parent / "input"
    dvh_files = sorted(input_dir.glob("LCMD*_DVH_*.txt"))

    if not dvh_files:
        pytest.skip("No DVH files found in input directory")

    dvh_file = parse_dvh_file(dvh_files[0])

    # Check metadata
    assert dvh_file.patient_id.startswith("LCMD")
    assert dvh_file.plan_name in ["VMAT", "VMAT1", "VIMA", "IMRT"]

    # Check structures
    assert len(dvh_file.structures) > 0

    # Check that at least PTV and LUNG are present
    structure_names = dvh_file.list_structures()
    assert any("PTV" in name for name in structure_names), f"No PTV found in {structure_names}"
    assert any("LUNG" in name for name in structure_names), f"No LUNG found in {structure_names}"

    # Check dose conversion (cGy -> Gy)
    for struct in dvh_file.structures.values():
        # All doses should be in reasonable Gy range (0-100 Gy)
        assert np.all(struct.doses_gy >= 0)
        assert np.all(struct.doses_gy <= 100)

        # Volumes should be in range [0, 1]
        assert np.all(struct.volumes_frac >= 0)
        assert np.all(struct.volumes_frac <= 1)

        # Doses should be sorted
        assert np.all(struct.doses_gy[:-1] <= struct.doses_gy[1:])


def test_parse_missing_file():
    """Test that parsing non-existent file raises error."""
    with pytest.raises(FileNotFoundError):
        parse_dvh_file(Path("/nonexistent/file.txt"))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
