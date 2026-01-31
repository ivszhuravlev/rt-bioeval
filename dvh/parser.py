"""
DVH Parser for TPS exported files.
Reads cumulative DVH data in plain text format.
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np


class DVHData:
    """Container for DVH data of a single structure."""

    def __init__(self, structure_name: str, doses_gy: np.ndarray, volumes_frac: np.ndarray):
        """
        Args:
            structure_name: Name of the structure (e.g., "PTV_6000", "LUNG_TOTAL")
            doses_gy: Dose bins in Gy (sorted ascending)
            volumes_frac: Cumulative volumes as fraction 0..1 (sorted by dose)
        """
        self.structure_name = structure_name
        self.doses_gy = doses_gy
        self.volumes_frac = volumes_frac

        # Validate
        if len(doses_gy) != len(volumes_frac):
            raise ValueError(f"Dose and volume arrays must have same length for {structure_name}")

        # Sort by dose and remove duplicates
        self._sort_and_clean()

    def _sort_and_clean(self):
        """Sort by dose and remove duplicate dose bins."""
        # Sort by dose
        sort_idx = np.argsort(self.doses_gy)
        self.doses_gy = self.doses_gy[sort_idx]
        self.volumes_frac = self.volumes_frac[sort_idx]

        # Remove duplicates (keep first occurrence)
        unique_doses, unique_idx = np.unique(self.doses_gy, return_index=True)
        self.doses_gy = self.doses_gy[unique_idx]
        self.volumes_frac = self.volumes_frac[unique_idx]

    def __repr__(self):
        return f"DVHData('{self.structure_name}', {len(self.doses_gy)} bins, dose range {self.doses_gy[0]:.2f}-{self.doses_gy[-1]:.2f} Gy)"


class DVHFile:
    """Parsed DVH file containing multiple structures."""

    def __init__(self, patient_id: str, plan_name: str, structures: Dict[str, DVHData]):
        """
        Args:
            patient_id: Patient ID (e.g., "LCMD1")
            plan_name: Plan name (e.g., "VMAT1", "IMRT")
            structures: Dict mapping structure name to DVHData
        """
        self.patient_id = patient_id
        self.plan_name = plan_name
        self.structures = structures

    def get_structure(self, name: str) -> Optional[DVHData]:
        """Get structure by exact name, or None if not found."""
        return self.structures.get(name)

    def list_structures(self) -> List[str]:
        """Return list of all structure names."""
        return sorted(self.structures.keys())

    def __repr__(self):
        return f"DVHFile(patient={self.patient_id}, plan={self.plan_name}, {len(self.structures)} structures)"


def parse_dvh_file(file_path: Path) -> DVHFile:
    """
    Parse TPS DVH export file.

    Expected format:
        Line 1: Patient ID: XXX | Plan Name: YYY | ... | Dose Units: cGy | Volume Units: %
        Line 2: English (United States) Format In-use
        Line 3: Empty or header
        Line 4+: STRUCTURE_NAME    DOSE    VOLUME

    Args:
        file_path: Path to DVH text file

    Returns:
        DVHFile object with parsed data

    Raises:
        ValueError: If file format is invalid or required metadata missing
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"DVH file not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if len(lines) < 4:
        raise ValueError(f"DVH file too short: {file_path}")

    # Parse metadata from first line
    metadata_line = lines[0].strip()
    patient_id = _extract_metadata(metadata_line, r'Patient ID:\s*(\S+)')
    plan_name = _extract_metadata(metadata_line, r'Plan Name:\s*(\S+)')
    dose_units = _extract_metadata(metadata_line, r'Dose Units:\s*(\S+)')
    volume_units = _extract_metadata(metadata_line, r'Volume Units:\s*(\S+)')

    if not all([patient_id, plan_name, dose_units, volume_units]):
        raise ValueError(f"Missing required metadata in first line: {file_path}")

    # Validate units
    if dose_units.lower() != 'cgy':
        raise ValueError(f"Expected dose units 'cGy', got '{dose_units}'")
    if volume_units != '%':
        raise ValueError(f"Expected volume units '%', got '{volume_units}'")

    # Parse structure data (skip first 3 lines: metadata, locale, header/empty)
    structures_data = _parse_structure_data(lines[3:])

    # Convert to DVHData objects
    structures = {}
    for struct_name, (doses_cgy, volumes_pct) in structures_data.items():
        # Convert units: cGy -> Gy, % -> fraction
        doses_gy = np.array(doses_cgy, dtype=np.float64) / 100.0
        volumes_frac = np.array(volumes_pct, dtype=np.float64) / 100.0

        # Clamp volumes to [0, 1]
        volumes_frac = np.clip(volumes_frac, 0.0, 1.0)

        structures[struct_name] = DVHData(struct_name, doses_gy, volumes_frac)

    if not structures:
        raise ValueError(f"No structures found in DVH file: {file_path}")

    return DVHFile(patient_id, plan_name, structures)


def _extract_metadata(line: str, pattern: str) -> Optional[str]:
    """Extract metadata field using regex pattern."""
    match = re.search(pattern, line)
    return match.group(1) if match else None


def _parse_structure_data(data_lines: List[str]) -> Dict[str, Tuple[List[float], List[float]]]:
    """
    Parse structure data lines into dict of structure_name -> (doses, volumes).

    Format: STRUCTURE_NAME    DOSE    VOLUME
    Multiple lines for same structure are accumulated.
    """
    structures = {}

    for line in data_lines:
        line = line.strip()
        if not line:
            continue

        # Skip header lines
        if 'Structure Name' in line or 'Dose' in line or 'Volume' in line:
            continue

        # Parse data line: structure_name, dose, volume
        parts = line.split()
        if len(parts) < 3:
            continue

        # First part is structure name, last two are dose and volume
        structure_name = parts[0]
        try:
            dose = float(parts[-2])
            volume = float(parts[-1])
        except (ValueError, IndexError):
            continue

        # Accumulate data for this structure
        if structure_name not in structures:
            structures[structure_name] = ([], [])

        structures[structure_name][0].append(dose)
        structures[structure_name][1].append(volume)

    return structures


def load_patient_plans(input_dir: Path, patient_id: str) -> Dict[str, DVHFile]:
    """
    Load all DVH files for a given patient.

    Args:
        input_dir: Directory containing DVH files
        patient_id: Patient ID (e.g., "LCMD1")

    Returns:
        Dict mapping plan_name -> DVHFile

    Raises:
        ValueError: If no files found for patient
    """
    input_dir = Path(input_dir)
    pattern = f"{patient_id}_*_DVH_*.txt"
    files = sorted(input_dir.glob(pattern))

    if not files:
        raise ValueError(f"No DVH files found for patient {patient_id} in {input_dir}")

    plans = {}
    for file_path in files:
        dvh_file = parse_dvh_file(file_path)

        # Use plan_name as key; if multiple files for same plan, keep first only
        if dvh_file.plan_name not in plans:
            plans[dvh_file.plan_name] = dvh_file
        else:
            # Keep first file, don't merge (prevents data corruption)
            continue

    return plans
