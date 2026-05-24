from pathlib import Path
from typing import Literal, Optional, Dict, Any, List, Tuple, Union
import os

from backend.mcp_server import mcp
from backend.mcp_server.util.comm import generate_work_path, run_command
#@mcp.tool()
def generate_novel_ions(
    base_molecule_smile: str,
    molecule_type: Literal["cation", "anion"],
    num_molecules: int = 10,
    temperature: float = 0.7,
) -> str:
    """Generate novel ionic liquid molecules using a machine learning pipeline.

    Runs an external bash script that uses FlashFormer to generate new ion
    candidates, computes SA Score and similarity, and outputs ranked results.

    Args:
        base_molecule_smile: SMILES of the starting fragment (e.g. "C", "CCN").
        molecule_type: "cation" or "anion".
        num_molecules: Number of molecules to generate (default 10).
        temperature: Sampling diversity, 0.1–1.0 (default 0.7). Lower → more similar.

    Returns:
        Path to the sorted CSV file (columns: smiles, sa_score, similarity).

    Requires:
        ILS4GAS_MOLECULE_GEN_SCRIPT set to the pipeline script path.
        The script must accept: --ion, --start, --num, --temp, --output.
    """
    script_path = os.environ.get("ILS4GAS_MOLECULE_GEN_SCRIPT", "")
    if not script_path:
        raise ValueError(
            "ILS4GAS_MOLECULE_GEN_SCRIPT is not set. "
            "Set it to the path of the generation pipeline script."
        )

    script = Path(script_path)
    if not script.exists():
        raise FileNotFoundError(f"Script not found: {script}")

    ion_map = {"cation": "ca", "anion": "an"}
    if molecule_type not in ion_map:
        raise ValueError(
            f"molecule_type must be 'cation' or 'anion', got '{molecule_type}'"
        )

    if not (0.1 <= temperature <= 1.0):
        raise ValueError(
            f"temperature must be 0.1–1.0, got {temperature}"
        )

    work_path = generate_work_path(create=True)
    output_prefix = str(
        Path(work_path) / f"{molecule_type}_{num_molecules}_{temperature:.1f}"
    )

    cmd = (
        f"bash {script} "
        f"--ion {ion_map[molecule_type]} "
        f"--start {base_molecule_smile} "
        f"--num {num_molecules} "
        f"--temp {temperature} "
        f"--output {output_prefix}"
    )

    return_code, out, err = run_command(cmd, cwd=str(script.parent))

    if return_code != 0:
        raise RuntimeError(f"Pipeline failed (exit {return_code}):\n{err}")

    sorted_csv = f"{output_prefix}_results_sorted.csv"
    if not Path(sorted_csv).exists():
        raise FileNotFoundError(f"Output not found: {sorted_csv}")

    return sorted_csv


#@mcp.tool()
def predict_binding_energy(
    complex_xyz_path: str,
    part1_xyz_path: str,
    part2_xyz_path: str,
    part1_eps_path: str,
    part2_eps_path: str,
) -> Dict[str, float]:
    """Predict binding energy between two molecular structures using a pre-trained model.

    Runs the Eb_predict.py script in single mode with the provided structure and EPS files.

    Args:
        complex_xyz_path: Path to complex structure file (xyz format).
        part1_xyz_path: Path to monomer 1 structure file (xyz format).
        part2_xyz_path: Path to monomer 2 structure file (xyz format).
        part1_eps_path: Path to monomer 1 electrostatic potential file (eps format).
        part2_eps_path: Path to monomer 2 electrostatic potential file (eps format).

    Returns:
        Dict with "binding_energy" key containing the predicted value.

    Requires:
        ILS4GAS_EB_PREDICT_SCRIPT set to the Eb_predict.py script path.
    """
    script_path = os.environ.get("ILS4GAS_EB_PREDICT_SCRIPT", "")
    if not script_path:
        raise ValueError(
            "ILS4GAS_EB_PREDICT_SCRIPT is not set. "
            "Set it to the path of the Eb_predict.py script."
        )

    script = Path(script_path)
    if not script.exists():
        raise FileNotFoundError(f"Script not found: {script}")

    # Validate all input files exist
    input_files = [
        ("complex_xyz", complex_xyz_path),
        ("part1_xyz", part1_xyz_path),
        ("part2_xyz", part2_xyz_path),
        ("part1_eps", part1_eps_path),
        ("part2_eps", part2_eps_path),
    ]
    for name, path in input_files:
        if not Path(path).exists():
            raise FileNotFoundError(f"{name} file not found: {path}")

    work_path = generate_work_path(create=True)
    output_file = Path(work_path) / "binding_energy_result.txt"

    cmd = (
        f"python {script} single "
        f"{complex_xyz_path} "
        f"{part1_xyz_path} "
        f"{part2_xyz_path} "
        f"{part1_eps_path} "
        f"{part2_eps_path} "
        f"-o {output_file}"
    )

    return_code, out, err = run_command(cmd, cwd=str(work_path))

    if return_code != 0:
        raise RuntimeError(f"Binding energy prediction failed (exit {return_code}):\n{err}")

    # Read result from output file
    if not output_file.exists():
        raise FileNotFoundError(f"Result output file not found: {output_file}")

    with open(output_file, "r") as f:
        result_line = f.read().strip()
        try:
            binding_energy = float(result_line)
        except ValueError:
            raise RuntimeError(f"Invalid result format from prediction: {result_line}")

    return {"binding_energy": binding_energy}