import json
import os
import re  # For regex matching of part numbers if needed
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.csv as pv

# --- Configuration ---
research_file_csv = "stm32_l0_l1_eeprom_research.csv"
original_json_dir = Path("/home/okhsunrog/temp/generated_data/original/data/chips")
w_eeprom_json_dir = Path("/home/okhsunrog/temp/generated_data/w_eeprom/data/chips")


# --- Helper function to load CSV ---
def load_csv_pa_to_pd(filename):
    try:
        table = pv.read_csv(filename)
        return table.to_pandas()
    except Exception as e:
        print(f"Error loading {filename} with PyArrow, falling back to Pandas: {e}")
        return pd.read_csv(filename, low_memory=False)


# --- Load the research CSV ---
print(f"Loading {research_file_csv}...")
research_df = load_csv_pa_to_pd(research_file_csv)
research_df["part_number"] = research_df["part_number"].str.strip()
research_df["eeprom_total_size_b_from_doc"] = pd.to_numeric(
    research_df["eeprom_total_size_b_from_doc"], errors="coerce"
).astype("Int64")
research_df["eeprom_bank1_size_b"] = pd.to_numeric(
    research_df["eeprom_bank1_size_b"], errors="coerce"
).astype("Int64")
research_df["eeprom_bank2_size_b"] = pd.to_numeric(
    research_df["eeprom_bank2_size_b"], errors="coerce"
).astype("Int64")


# --- Helper function to load a JSON file ---
def load_json_file(file_path):
    if not file_path.exists():
        return None
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Warning: Could not decode JSON from: {file_path}")
        return None
    except Exception as e:
        print(f"Warning: Error reading JSON file {file_path}: {e}")
        return None


# --- Helper function to extract memory regions of a specific kind ---
def get_memory_regions_by_kind(chip_data, kind):
    regions = []
    if chip_data and "memory" in chip_data:
        for memory_bank_list in chip_data.get("memory", []):
            if not isinstance(memory_bank_list, list):
                continue
            for mem_region in memory_bank_list:
                if isinstance(mem_region, dict) and mem_region.get("kind") == kind:
                    regions.append(mem_region)
    return regions


import json

from deepdiff import DeepDiff  # You might need to install this: pip install deepdiff


def compare_json_objects_smart(obj1, obj2, chip_name, verbose_diff=False):
    is_l0_l1_chip_local = chip_name.startswith("STM32L0") or chip_name.startswith(
        "STM32L1"
    )

    obj1_copy = json.loads(json.dumps(obj1))  # Deep copy
    obj2_copy = json.loads(json.dumps(obj2))  # Deep copy

    # Standardize by removing EEPROM for L0/L1 to compare the rest
    if is_l0_l1_chip_local:
        if "memory" in obj1_copy and isinstance(obj1_copy["memory"], list):
            for bank_list_idx in range(len(obj1_copy["memory"])):
                if isinstance(obj1_copy["memory"][bank_list_idx], list):
                    obj1_copy["memory"][bank_list_idx] = [
                        mem
                        for mem in obj1_copy["memory"][bank_list_idx]
                        if not (isinstance(mem, dict) and mem.get("kind") == "eeprom")
                    ]
        if "memory" in obj2_copy and isinstance(obj2_copy["memory"], list):
            for bank_list_idx in range(len(obj2_copy["memory"])):
                if isinstance(obj2_copy["memory"][bank_list_idx], list):
                    obj2_copy["memory"][bank_list_idx] = [
                        mem
                        for mem in obj2_copy["memory"][bank_list_idx]
                        if not (isinstance(mem, dict) and mem.get("kind") == "eeprom")
                    ]

    are_equal = obj1_copy == obj2_copy

    if (
        not are_equal and verbose_diff
    ):  # Only print diff if requested and they are not equal
        print(f"DEBUG: Detailed differences for {chip_name}:")
        # Sort keys for more stable diff, especially at the top level
        # For very complex diffs, you might need a more sophisticated approach
        # or just focus on specific keys known to cause issues.

        # Using DeepDiff for a more structured output
        diff = DeepDiff(
            obj1_copy,
            obj2_copy,
            ignore_order=True,
            report_repetition=True,
            verbose_level=2,
        )  # ignore_order can be helpful
        if diff:
            print(diff.pretty())
        else:
            # If deepdiff finds them equal with ignore_order, but direct == failed, it implies order was the issue.
            print(
                "DEBUG: DeepDiff (ignoring order) found no differences, but direct equality failed. Likely an order issue in a list."
            )
            # For manual inspection if DeepDiff doesn't pinpoint it well enough:
            # for key in set(obj1_copy.keys()) | set(obj2_copy.keys()):
            #     if obj1_copy.get(key) != obj2_copy.get(key):
            #         print(f"  Key '{key}' differs.")
            #         # print(f"    Original : {obj1_copy.get(key)}")
            #         # print(f"    W_EEPROM: {obj2_copy.get(key)}")
            #         # Be careful printing large structures

    return are_equal


# --- Main Checking Logic ---
print("\n--- Starting JSON Comparison and EEPROM Validation ---")
overall_mismatches_found = False
files_processed = 0
l0_l1_chips_found_in_csv = set(
    research_df[research_df["part_number"].str.startswith(("STM32L0", "STM32L1"))][
        "part_number"
    ]
)

for original_json_file in original_json_dir.glob("*.json"):
    files_processed += 1
    chip_name_from_filename = original_json_file.stem  # e.g., STM32L071C8

    w_eeprom_json_file = w_eeprom_json_dir / original_json_file.name

    original_data = load_json_file(original_json_file)
    w_eeprom_data = load_json_file(w_eeprom_json_file)

    if original_data is None:
        print(f"ERROR: Could not load original JSON: {original_json_file}")
        overall_mismatches_found = True
        continue

    if w_eeprom_data is None:
        print(
            f"ERROR: Could not load w_eeprom JSON: {w_eeprom_json_file} (corresponding to {original_json_file.name})"
        )
        overall_mismatches_found = True
        continue

    is_l0_l1_chip = chip_name_from_filename.startswith(
        "STM32L0"
    ) or chip_name_from_filename.startswith("STM32L1")

    # 1. Compare JSONs (original vs. w_eeprom)
    verbose_debugging = True  # Debug all mismatches

    if not compare_json_objects_smart(
        original_data,
        w_eeprom_data,
        chip_name_from_filename,
        verbose_diff=verbose_debugging,
    ):
        if (
            not overall_mismatches_found
        ):  # Print the general mismatch message only once per chip
            print(
                f"MISMATCH_STRUCTURE: Chip {chip_name_from_filename} - JSON structures differ (excluding EEPROM for L0/L1). See details above/below if verbose."
            )
        overall_mismatches_found = True
    else:
        # If structures (excluding EEPROM for L0/L1) are the same,
        # for non-L0/L1, ensure no EEPROM was added to w_eeprom version.
        if not is_l0_l1_chip:  # <<< CORRECTED HERE
            eeprom_regions_w_eeprom = get_memory_regions_by_kind(
                w_eeprom_data, "eeprom"
            )
            if eeprom_regions_w_eeprom:
                print(
                    f"MISMATCH_UNEXPECTED_EEPROM: Chip {chip_name_from_filename} (non-L0/L1) - has EEPROM in w_eeprom version."
                )
                overall_mismatches_found = True
        else:  # It is an L0/L1 chip
            eeprom_regions_original = get_memory_regions_by_kind(
                original_data, "eeprom"
            )
            if eeprom_regions_original:
                print(
                    f"INFO: Chip {chip_name_from_filename} (L0/L1) - original JSON already contained EEPROM. This is unusual if your branch was meant to add it."
                )
                # This might not be an error depending on the starting state of original data.

    # 2. Validate EEPROM in `w_eeprom` JSONs against `research.csv` (for L0/L1 chips)
    if is_l0_l1_chip:
        if chip_name_from_filename not in l0_l1_chips_found_in_csv:
            # print(f"INFO: Chip {chip_name_from_filename} (L0/L1) found in JSONs but not in the research CSV. Skipping EEPROM CSV validation for it.")
            pass
        else:
            csv_row_series = research_df[
                research_df["part_number"] == chip_name_from_filename
            ]
            if (
                csv_row_series.empty
            ):  # Should not happen if chip_name_from_filename in l0_l1_chips_found_in_csv
                print(
                    f"WARNING: Chip {chip_name_from_filename} was in l0_l1_chips_found_in_csv but no row found. Skipping CSV validation."
                )
                continue
            csv_row = csv_row_series.iloc[0]

            csv_eeprom_total_b = csv_row["eeprom_total_size_b_from_doc"]
            csv_eeprom_b1_size = csv_row["eeprom_bank1_size_b"]
            csv_eeprom_b2_size = csv_row["eeprom_bank2_size_b"]

            json_eeprom_regions = get_memory_regions_by_kind(w_eeprom_data, "eeprom")

            if not json_eeprom_regions:
                if not pd.isna(csv_eeprom_total_b) and csv_eeprom_total_b > 0:
                    print(
                        f"MISMATCH_EEPROM_MISSING: Chip {chip_name_from_filename} - Expected EEPROM size {csv_eeprom_total_b}B from CSV, but no EEPROM found in w_eeprom JSON."
                    )
                    overall_mismatches_found = True
                continue

            json_total_eeprom_b = sum(r.get("size", 0) for r in json_eeprom_regions)

            if pd.isna(csv_eeprom_total_b):
                if json_total_eeprom_b > 0:
                    print(
                        f"MISMATCH_EEPROM_UNEXPECTED_JSON: Chip {chip_name_from_filename} - CSV has no EEPROM size, but JSON has {json_total_eeprom_b}B."
                    )
                    overall_mismatches_found = True
            elif json_total_eeprom_b != csv_eeprom_total_b:
                print(
                    f"MISMATCH_EEPROM_TOTAL_SIZE: Chip {chip_name_from_filename} - Total EEPROM size mismatch. CSV: {csv_eeprom_total_b}B, JSON: {json_total_eeprom_b}B."
                )
                overall_mismatches_found = True

            json_bank1_size = pd.NA
            json_bank2_size = pd.NA

            # Try to map JSON EEPROM regions to CSV banks
            # This is a simplified mapping; your Rust code's naming ("EEPROM", "EEPROM_BANK_1") is key.
            # We assume if there's only one EEPROM entry in JSON, it corresponds to the total or bank1.
            # If there are multiple, we look for names.

            temp_json_eeproms_by_name = {
                r.get("name", f"UNNAMED_EEPROM_{i}").upper(): r.get("size", 0)
                for i, r in enumerate(json_eeprom_regions)
            }

            if "EEPROM_BANK_1" in temp_json_eeproms_by_name:
                json_bank1_size = temp_json_eeproms_by_name["EEPROM_BANK_1"]
            elif (
                "EEPROM" in temp_json_eeproms_by_name and len(json_eeprom_regions) == 1
            ):  # Single unnamed or "EEPROM"
                json_bank1_size = temp_json_eeproms_by_name["EEPROM"]
            elif (
                "EEPROM" in temp_json_eeproms_by_name
                and "EEPROM_BANK_2" not in temp_json_eeproms_by_name
            ):  # if "EEPROM" and no "EEPROM_BANK_2", assume "EEPROM" is bank 1
                json_bank1_size = temp_json_eeproms_by_name["EEPROM"]

            if "EEPROM_BANK_2" in temp_json_eeproms_by_name:
                json_bank2_size = temp_json_eeproms_by_name["EEPROM_BANK_2"]

            # Refined bank comparison
            if not pd.isna(csv_eeprom_b1_size):  # If CSV expects a bank 1 size
                if pd.isna(json_bank1_size) or csv_eeprom_b1_size != json_bank1_size:
                    print(
                        f"MISMATCH_EEPROM_B1_SIZE: Chip {chip_name_from_filename} - EEPROM Bank 1. CSV: {csv_eeprom_b1_size}B, JSON detected: {json_bank1_size}B."
                    )
                    overall_mismatches_found = True
            elif not pd.isna(json_bank1_size) and pd.isna(
                csv_eeprom_b1_size
            ):  # JSON has B1 but CSV does not (and CSV has total > 0)
                if (
                    not pd.isna(csv_eeprom_total_b) and csv_eeprom_total_b > 0
                ):  # only if CSV expects some eeprom
                    print(
                        f"INFO: Chip {chip_name_from_filename} - JSON has EEPROM Bank 1 ({json_bank1_size}B), but CSV does not define Bank 1 size explicitly (Total: {csv_eeprom_total_b}B)."
                    )

            if not pd.isna(csv_eeprom_b2_size):  # If CSV expects a bank 2 size
                if pd.isna(json_bank2_size) or csv_eeprom_b2_size != json_bank2_size:
                    print(
                        f"MISMATCH_EEPROM_B2_SIZE: Chip {chip_name_from_filename} - EEPROM Bank 2. CSV: {csv_eeprom_b2_size}B, JSON detected: {json_bank2_size}B."
                    )
                    overall_mismatches_found = True
            elif not pd.isna(json_bank2_size) and pd.isna(
                csv_eeprom_b2_size
            ):  # JSON has B2 but CSV does not
                if not pd.isna(csv_eeprom_total_b) and csv_eeprom_total_b > 0:
                    print(
                        f"INFO: Chip {chip_name_from_filename} - JSON has EEPROM Bank 2 ({json_bank2_size}B), but CSV does not define Bank 2 size explicitly (Total: {csv_eeprom_total_b}B)."
                    )


# --- Final Summary ---
if files_processed == 0:
    print("No JSON files found in the original directory to process.")
elif not overall_mismatches_found:
    print(
        "\n--- All Checks Passed: JSON structures match (conditionally), and L0/L1 EEPROM data aligns with CSV. ---"
    )
else:
    print(
        "\n--- Some Mismatches or Errors Encountered. Please review the output above. ---"
    )
