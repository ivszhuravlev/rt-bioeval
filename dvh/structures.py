"""
Structure mapping and ROI utilities.
Handles finding structures by priority and normalizing names.
"""

from typing import List, Optional, Dict
from .parser import DVHFile, DVHData


class StructureNotFoundError(Exception):
    """Raised when required structure not found in DVH."""
    pass


class StructureMapper:
    """Maps clinical structure names to actual names in DVH file."""

    def __init__(self, mapping_config: Dict[str, List[str]]):
        """
        Args:
            mapping_config: Dict of roi_type -> list of possible names (priority order)
                Example: {"ptv": ["PTV_6600", "PTV_6000"], "lung": ["LUNGS-CTV", "LUNG_TOTAL"]}
        """
        self.mapping = mapping_config

    def find_structure(self, dvh_file: DVHFile, roi_type: str) -> DVHData:
        """
        Find structure in DVH file by roi_type.

        Args:
            dvh_file: Parsed DVH file
            roi_type: ROI type (e.g., "ptv", "lung", "heart")

        Returns:
            DVHData for the found structure

        Raises:
            StructureNotFoundError: If no matching structure found
        """
        if roi_type not in self.mapping:
            raise ValueError(f"Unknown ROI type: {roi_type}. Available: {list(self.mapping.keys())}")

        possible_names = self.mapping[roi_type]
        available_structures = dvh_file.list_structures()

        # Try each possible name in priority order
        for name in possible_names:
            if name in available_structures:
                return dvh_file.get_structure(name)

        # Not found - raise error with helpful message
        raise StructureNotFoundError(
            f"Structure '{roi_type}' not found in {dvh_file.patient_id}/{dvh_file.plan_name}. "
            f"Tried: {possible_names}. Available: {available_structures}"
        )

    def find_structure_safe(self, dvh_file: DVHFile, roi_type: str) -> Optional[DVHData]:
        """
        Find structure, return None if not found (no exception).

        Args:
            dvh_file: Parsed DVH file
            roi_type: ROI type

        Returns:
            DVHData or None if not found
        """
        try:
            return self.find_structure(dvh_file, roi_type)
        except StructureNotFoundError:
            return None


def get_default_structure_mapping() -> Dict[str, List[str]]:
    """
    Get default structure mapping for lung cancer RT.

    Returns:
        Dict of roi_type -> list of structure names (priority order)
    """
    return {
        "ptv": [
            "PTV_6600",
            "PTV_6000",
            "PTV",
        ],
        "lung": [
            "LUNG_TOTAL",  # Standard total lung for NTCP
            "LUNGS",
        ],
        "heart": [
            "HEART",
        ],
        "esophagus": [
            "ESOPHAGUS",
            "OESOPHAGUS",
        ],
        "spinal_cord": [
            "SPINAL_CORD",
            "CORD",
        ],
    }


def validate_required_structures(dvh_file: DVHFile, mapper: StructureMapper,
                                 required: List[str]) -> Dict[str, DVHData]:
    """
    Validate that all required structures are present in DVH file.

    Args:
        dvh_file: Parsed DVH file
        mapper: Structure mapper
        required: List of required ROI types (e.g., ["ptv", "lung", "heart"])

    Returns:
        Dict mapping roi_type -> DVHData

    Raises:
        StructureNotFoundError: If any required structure is missing
    """
    structures = {}
    missing = []

    for roi_type in required:
        try:
            structures[roi_type] = mapper.find_structure(dvh_file, roi_type)
        except StructureNotFoundError:
            missing.append(roi_type)

    if missing:
        raise StructureNotFoundError(
            f"Missing required structures in {dvh_file.patient_id}/{dvh_file.plan_name}: {missing}"
        )

    return structures
