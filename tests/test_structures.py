"""
Unit tests for structure mapping.
"""

import pytest
from pathlib import Path
from dvh.parser import parse_dvh_file, load_patient_plans
from dvh.structures import (
    StructureMapper,
    StructureNotFoundError,
    get_default_structure_mapping,
    validate_required_structures
)


def test_structure_mapper_find():
    """Test finding structures by priority."""
    input_dir = Path(__file__).parent.parent / "input"
    dvh_files = sorted(input_dir.glob("LCMD*_DVH_*.txt"))

    if not dvh_files:
        pytest.skip("No DVH files found")

    dvh_file = parse_dvh_file(dvh_files[0])
    mapper = StructureMapper(get_default_structure_mapping())

    # Try to find PTV (should succeed)
    ptv = mapper.find_structure(dvh_file, "ptv")
    assert ptv is not None
    assert "PTV" in ptv.structure_name

    # Try to find non-existent structure (should raise)
    with pytest.raises(StructureNotFoundError):
        mapper.find_structure(dvh_file, "nonexistent")


def test_structure_mapper_safe():
    """Test safe find (returns None instead of raising)."""
    input_dir = Path(__file__).parent.parent / "input"
    dvh_files = sorted(input_dir.glob("LCMD*_DVH_*.txt"))

    if not dvh_files:
        pytest.skip("No DVH files found")

    dvh_file = parse_dvh_file(dvh_files[0])
    mapper = StructureMapper(get_default_structure_mapping())

    # Try to find non-existent structure (should return None)
    result = mapper.find_structure_safe(dvh_file, "nonexistent")
    assert result is None


def test_validate_required_structures():
    """Test validation of required structures."""
    input_dir = Path(__file__).parent.parent / "input"
    dvh_files = sorted(input_dir.glob("LCMD*_DVH_*.txt"))

    if not dvh_files:
        pytest.skip("No DVH files found")

    dvh_file = parse_dvh_file(dvh_files[0])
    mapper = StructureMapper(get_default_structure_mapping())

    # Should succeed for PTV (always present)
    structures = validate_required_structures(dvh_file, mapper, ["ptv"])
    assert "ptv" in structures

    # Should fail for non-existent structure
    with pytest.raises(StructureNotFoundError):
        validate_required_structures(dvh_file, mapper, ["nonexistent"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
