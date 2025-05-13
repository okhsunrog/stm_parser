import pandas as pd
import pyarrow.csv as pv
import pyarrow as pa
import numpy as np

# File names
research_file = "stm32_l0_l1_eeprom_research.csv"
products_l0_file = "ProductsList_L0.csv"
products_l1_file = "ProductsList_L1.csv"


# --- Helper function to load CSVs using PyArrow and convert to Pandas ---
def load_csv_pa_to_pd(filename, skip_rows=None):
    """Loads a CSV using PyArrow and converts to Pandas DataFrame."""
    try:
        if skip_rows:
            # PyArrow's read_csv doesn't have a direct skiprows list like pandas.
            # A common workaround is to read with pandas if complex skipping is needed,
            # or read all and then drop rows. For a single skip, we can do this:
            df_temp = pd.read_csv(filename, skiprows=skip_rows, low_memory=False)
            table = pa.Table.from_pandas(df_temp)
        else:
            table = pv.read_csv(filename)
        return table.to_pandas()
    except Exception as e:
        print(f"Error loading {filename} with PyArrow, falling back to Pandas: {e}")
        # Fallback to pandas for robustness, especially with tricky CSVs
        return pd.read_csv(filename, skiprows=skip_rows, low_memory=False)


# --- Load the research file ---
print(f"Loading {research_file}...")
research_df = load_csv_pa_to_pd(research_file)
# Clean up research_df columns for comparison
research_df["flash_size_kb_prog"] = pd.to_numeric(
    research_df["flash_size_kb_prog"], errors="coerce"
).astype("Int64")
research_df["ram_size_kb"] = pd.to_numeric(
    research_df["ram_size_kb"], errors="coerce"
).astype("Int64")
research_df["total_eeprom_b_from_export"] = pd.to_numeric(
    research_df["total_eeprom_b_from_export"], errors="coerce"
).astype("Int64")
research_df["eeprom_total_size_b_from_doc"] = pd.to_numeric(
    research_df["eeprom_total_size_b_from_doc"], errors="coerce"
).astype("Int64")

# --- Load Product List L0 ---
print(f"Loading {products_l0_file}...")
# The second row (index 1) is a sub-header, skip it.
products_l0_df = load_csv_pa_to_pd(products_l0_file, skip_rows=[1])
products_l0_df.rename(
    columns={
        "Flash Size (kB) (Prog)": "Product_Flash_kB",
        "RAM Size (kB)": "Product_RAM_kB",
        "Data E2PROM (B) nom": "Product_EEPROM_B",
    },
    inplace=True,
)
products_l0_df["Product_Flash_kB"] = pd.to_numeric(
    products_l0_df["Product_Flash_kB"], errors="coerce"
).astype("Int64")
products_l0_df["Product_RAM_kB"] = pd.to_numeric(
    products_l0_df["Product_RAM_kB"], errors="coerce"
).astype("Int64")
products_l0_df["Product_EEPROM_B"] = pd.to_numeric(
    products_l0_df["Product_EEPROM_B"], errors="coerce"
).astype("Int64")

# --- Load Product List L1 ---
print(f"Loading {products_l1_file}...")
# The second row (index 1) is a sub-header, skip it.
products_l1_df = load_csv_pa_to_pd(products_l1_file, skip_rows=[1])
products_l1_df.rename(
    columns={
        "Flash Size (kB) (Prog)": "Product_Flash_kB",
        "RAM Size (kB)": "Product_RAM_kB",
        "Data E2PROM (B) nom": "Product_EEPROM_B",
    },
    inplace=True,
)
products_l1_df["Product_Flash_kB"] = pd.to_numeric(
    products_l1_df["Product_Flash_kB"], errors="coerce"
).astype("Int64")
products_l1_df["Product_RAM_kB"] = pd.to_numeric(
    products_l1_df["Product_RAM_kB"], errors="coerce"
).astype("Int64")
products_l1_df["Product_EEPROM_B"] = pd.to_numeric(
    products_l1_df["Product_EEPROM_B"], errors="coerce"
).astype("Int64")


# --- Combine Product Lists ---
# Select only relevant columns to avoid duplicate column name issues if any exist beyond the renamed ones
cols_to_keep_product = [
    "Part Number",
    "Product_Flash_kB",
    "Product_RAM_kB",
    "Product_EEPROM_B",
]
all_products_df = pd.concat(
    [products_l0_df[cols_to_keep_product], products_l1_df[cols_to_keep_product]],
    ignore_index=True,
)

# Drop duplicates in case a part number appears in both (though unlikely for L0 vs L1)
all_products_df.drop_duplicates(subset=["Part Number"], keep="first", inplace=True)


# --- Merge research data with combined product data ---
print("Merging dataframes...")
merged_df = pd.merge(
    research_df,
    all_products_df,
    left_on="part_number",
    right_on="Part Number",
    how="left",
)

# --- Perform Checks ---
mismatches_found = False
print("\n--- Checking Data ---")

for index, row in merged_df.iterrows():
    part_num = row["part_number"]
    current_mismatches = []

    # Check if product was found
    if pd.isna(row["Part Number"]):
        print(
            f"MISMATCH Part Number: {part_num} - Not found in Product Lists L0 or L1."
        )
        mismatches_found = True
        continue  # Skip further checks for this part

    # Flash Size
    # Need to handle NaN comparison carefully. (a == a) is False if a is NaN.
    # (pd.isna(x) and pd.isna(y)) or (x == y)
    if not (
        (pd.isna(row["flash_size_kb_prog"]) and pd.isna(row["Product_Flash_kB"]))
        or row["flash_size_kb_prog"] == row["Product_Flash_kB"]
    ):
        current_mismatches.append(
            f"Flash (Research: {row['flash_size_kb_prog']} kB, ProductList: {row['Product_Flash_kB']} kB)"
        )
        mismatches_found = True

    # RAM Size
    if not (
        (pd.isna(row["ram_size_kb"]) and pd.isna(row["Product_RAM_kB"]))
        or row["ram_size_kb"] == row["Product_RAM_kB"]
    ):
        current_mismatches.append(
            f"RAM (Research: {row['ram_size_kb']} kB, ProductList: {row['Product_RAM_kB']} kB)"
        )
        mismatches_found = True

    # EEPROM Size (total_eeprom_b_from_export vs Product_EEPROM_B)
    if not (
        (
            pd.isna(row["total_eeprom_b_from_export"])
            and pd.isna(row["Product_EEPROM_B"])
        )
        or row["total_eeprom_b_from_export"] == row["Product_EEPROM_B"]
    ):
        current_mismatches.append(
            f"EEPROM (Export) (Research: {row['total_eeprom_b_from_export']} B, ProductList: {row['Product_EEPROM_B']} B)"
        )
        mismatches_found = True

    # EEPROM Size (eeprom_total_size_b_from_doc vs Product_EEPROM_B) - Additional check
    # This one is expected to mismatch sometimes, as per your 'notes' in research.csv
    if not (
        (
            pd.isna(row["eeprom_total_size_b_from_doc"])
            and pd.isna(row["Product_EEPROM_B"])
        )
        or row["eeprom_total_size_b_from_doc"] == row["Product_EEPROM_B"]
    ):
        current_mismatches.append(
            f"EEPROM (Doc) (Research: {row['eeprom_total_size_b_from_doc']} B, ProductList: {row['Product_EEPROM_B']} B) -- Note: This can differ based on 'notes'"
        )
        # Not necessarily setting mismatches_found = True here, as it's an advisory check
        # You can decide if this should be a hard failure. For now, it just reports.

    if current_mismatches:
        print(f"MISMATCH Part Number: {part_num}")
        for mis in current_mismatches:
            print(f"  - {mis}")

if not mismatches_found:
    print(
        "\n--- All Checked Values Match Product Lists (for flash, ram, total_eeprom_b_from_export) ---"
    )
else:
    print("\n--- Some Mismatches Found ---")

# You can inspect merged_df for more details if needed
# print("\nFirst 5 rows of merged data for inspection:")
# print(merged_df.head())
