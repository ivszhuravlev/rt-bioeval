"""
Main pipeline for DVH analysis and TCP/NTCP calculation.
Processes patient DVH files and exports results to JSON/CSV.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd
from datetime import datetime

from dvh.parser import parse_dvh_file, DVHFile
from dvh.structures import StructureMapper, validate_required_structures
from models.tcp_niemierko import calculate_tcp_from_dvh, cumulative_to_differential_dvh
from models.ntcp_lkb import calculate_ntcp_from_dvh
from metrics.lung import calculate_lung_metrics
from metrics.cord import calculate_cord_metrics


def load_config(config_path: Path) -> Dict[str, Any]:
    """Load model parameters from YAML config."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def analyze_plan(
    dvh_file: DVHFile,
    mapper: StructureMapper,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analyze single treatment plan (VMAT or IMRT).

    Args:
        dvh_file: Parsed DVH file
        mapper: Structure mapper
        config: Model parameters from config

    Returns:
        Dict with TCP, NTCP, and metrics results
    """
    results = {
        'patient_id': dvh_file.patient_id,
        'plan_name': dvh_file.plan_name,
        'tcp': {},
        'ntcp': {},
        'metrics': {}
    }

    # Find PTV
    ptv_data = mapper.find_structure(dvh_file, 'ptv')

    # Convert cumulative to differential for TCP calculation
    diff_volumes_ptv = cumulative_to_differential_dvh(
        ptv_data.doses_gy,
        ptv_data.volumes_frac
    )

    # Calculate TCP
    tcp_result = calculate_tcp_from_dvh(
        ptv_data.doses_gy,
        diff_volumes_ptv,
        config['tcp']['ptv']
    )
    results['tcp']['ptv'] = tcp_result

    # Process organs at risk
    organs = ['lung', 'heart', 'esophagus', 'spinal_cord']

    for organ in organs:
        organ_data = mapper.find_structure_safe(dvh_file, organ)

        if organ_data is None:
            continue

        # Convert cumulative to differential for NTCP
        diff_volumes = cumulative_to_differential_dvh(
            organ_data.doses_gy,
            organ_data.volumes_frac
        )

        # Calculate NTCP
        ntcp_result = calculate_ntcp_from_dvh(
            organ_data.doses_gy,
            diff_volumes,
            config['ntcp'][organ]
        )
        results['ntcp'][organ] = ntcp_result

        # Calculate organ-specific metrics
        if organ == 'lung':
            lung_metrics = calculate_lung_metrics(
                organ_data.doses_gy,
                diff_volumes,
                organ_data.volumes_frac  # cumulative for V5/V20
            )
            results['metrics']['lung'] = lung_metrics

        elif organ == 'spinal_cord':
            cord_metrics = calculate_cord_metrics(
                organ_data.doses_gy,
                cumulative_volumes_frac=organ_data.volumes_frac,
                total_volume_cc=None  # Not available in current files
            )
            results['metrics']['spinal_cord'] = cord_metrics

    return results


def compare_plans(vmat_result: Dict[str, Any], imrt_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare VMAT vs IMRT plans.

    Args:
        vmat_result: Results from VMAT plan
        imrt_result: Results from IMRT plan

    Returns:
        Dict with deltas (VMAT - IMRT)
    """
    comparison = {
        'tcp_delta': {},
        'ntcp_delta': {},
        'note': 'delta = VMAT - IMRT; negative = VMAT better (lower NTCP)'
    }

    # TCP delta
    if 'ptv' in vmat_result['tcp'] and 'ptv' in imrt_result['tcp']:
        comparison['tcp_delta']['ptv'] = (
            vmat_result['tcp']['ptv']['tcp'] - imrt_result['tcp']['ptv']['tcp']
        )

    # NTCP deltas
    for organ in vmat_result['ntcp']:
        if organ in imrt_result['ntcp']:
            comparison['ntcp_delta'][organ] = (
                vmat_result['ntcp'][organ]['ntcp'] - imrt_result['ntcp'][organ]['ntcp']
            )

    return comparison


def process_patient(
    patient_id: str,
    input_dir: Path,
    mapper: StructureMapper,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process all plans for a single patient.

    Args:
        patient_id: Patient ID (e.g., "LCMD1")
        input_dir: Directory containing DVH files
        mapper: Structure mapper
        config: Model parameters

    Returns:
        Dict with patient results including comparison
    """
    # Find all DVH files for this patient
    pattern = f"{patient_id}_*_DVH_*.txt"
    files = sorted(input_dir.glob(pattern))

    if not files:
        raise ValueError(f"No DVH files found for patient {patient_id}")

    # Group files by plan (VMAT/IMRT)
    plans = {}
    for file_path in files:
        dvh_file = parse_dvh_file(file_path)
        plan_name = dvh_file.plan_name

        # Keep first file per plan (don't merge, prevents data corruption)
        if plan_name not in plans:
            plans[plan_name] = dvh_file
        else:
            continue  # Skip additional files for same plan

    # Analyze each plan
    results = []
    for plan_name, dvh_file in plans.items():
        plan_result = analyze_plan(dvh_file, mapper, config)
        results.append(plan_result)

    # Build patient result
    patient_result = {
        'patient_id': patient_id,
        'plans': results
    }

    # Compare VMAT vs IMRT (if both exist)
    vmat_plan = next((p for p in results if 'VMAT' in p['plan_name'].upper()), None)
    imrt_plan = next((p for p in results if 'IMRT' in p['plan_name'].upper()), None)

    if vmat_plan and imrt_plan:
        patient_result['comparison'] = compare_plans(vmat_plan, imrt_plan)

    return patient_result


def export_json(results: Dict[str, Any], output_path: Path):
    """Export results to JSON file."""
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)


def export_csv(results: Dict[str, Any], output_path: Path):
    """
    Export results to CSV (one row per plan).

    Columns: patient_id, plan_name, tcp_ptv, ntcp_lung, ntcp_heart, etc.
    """
    rows = []

    for patient in results['patients']:
        for plan in patient['plans']:
            row = {
                'patient_id': plan['patient_id'],
                'plan_name': plan['plan_name'],
            }

            # TCP
            if 'ptv' in plan['tcp']:
                row['tcp_ptv'] = plan['tcp']['ptv']['tcp']
                row['eud_gy'] = plan['tcp']['ptv']['eud_gy']

            # NTCP
            for organ in ['lung', 'heart', 'esophagus', 'spinal_cord']:
                if organ in plan['ntcp']:
                    row[f'ntcp_{organ}'] = plan['ntcp'][organ]['ntcp']
                    row[f'deff_{organ}_gy'] = plan['ntcp'][organ]['deff_gy']

            # Metrics
            if 'lung' in plan['metrics']:
                row['mld_gy'] = plan['metrics']['lung']['mean_dose_gy']
                row['v5_percent'] = plan['metrics']['lung']['v5_percent']
                row['v20_percent'] = plan['metrics']['lung']['v20_percent']

            if 'spinal_cord' in plan['metrics']:
                row['cord_dmax_gy'] = plan['metrics']['spinal_cord']['dmax_gy']

            rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)


def run_analysis(
    input_dir: Path,
    output_dir: Path,
    config_path: Path,
    patient_ids: List[str] = None
):
    """
    Run complete DVH analysis pipeline.

    Args:
        input_dir: Directory with DVH files
        output_dir: Directory for output files
        config_path: Path to config YAML
        patient_ids: List of patient IDs to process (None = all)
    """
    # Load configuration
    config = load_config(config_path)

    # Create structure mapper
    mapper = StructureMapper(config['structure_mapping'])

    # Find all patients if not specified
    if patient_ids is None:
        all_files = list(input_dir.glob("LCMD*_DVH_*.txt"))
        patient_ids = sorted(set(f.name.split('_')[0] for f in all_files))

    print(f"Processing {len(patient_ids)} patients...")

    # Process each patient
    all_results = []
    for patient_id in patient_ids:
        try:
            print(f"  Processing {patient_id}...")
            patient_result = process_patient(patient_id, input_dir, mapper, config)
            all_results.append(patient_result)
        except Exception as e:
            print(f"  ERROR: {patient_id} - {e}")

    # Build final output
    output = {
        'metadata': {
            'analysis_date': datetime.now().strftime('%Y-%m-%d'),
            'n_patients': len(all_results),
            'comparison': 'VMAT/VIMA vs IMRT'
        },
        'patients': all_results
    }

    # Export results
    output_dir.mkdir(exist_ok=True)

    json_path = output_dir / 'results.json'
    csv_path = output_dir / 'results.csv'

    print(f"\nExporting results...")
    export_json(output, json_path)
    export_csv(output, csv_path)

    print(f"  JSON: {json_path}")
    print(f"  CSV: {csv_path}")
    print(f"\nDone! Processed {len(all_results)} patients.")


if __name__ == "__main__":
    # Default paths
    input_dir = Path("input")
    output_dir = Path("output")
    config_path = Path("config/model_params.yaml")

    run_analysis(input_dir, output_dir, config_path)
