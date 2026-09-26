"""
================================================================================
FRAUD DETECTION SYSTEM - STEP 1: DATA INGESTION & VALIDATION
================================================================================
Script  : data/validate_data.py
Purpose : Load the raw transaction CSV, validate every column, report problems,
          and - only if the data is clean enough - write a cleaned output file.

Run from the project root:
    python data/validate_data.py

Author  : Fraud Detection System Team
================================================================================
"""

import os           # for building file paths safely
import sys          # for sys.exit() when critical errors occur
import pandas as pd  # main library for loading and inspecting data

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION - change these paths if the files move
# ──────────────────────────────────────────────────────────────────────────────

# The directory where this script lives (i.e. the "data/" folder)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Raw input file
INPUT_CSV = os.path.join(SCRIPT_DIR, "bank_transactions_data_2.csv")

# Output file (only written if validation passes)
OUTPUT_CSV = os.path.join(SCRIPT_DIR, "transactions_clean.csv")

# ──────────────────────────────────────────────────────────────────────────────
# EXPECTED SCHEMA
# ──────────────────────────────────────────────────────────────────────────────

EXPECTED_COLUMNS = [
    "TransactionID",
    "AccountID",
    "TransactionAmount",
    "TransactionDate",
    "TransactionType",
    "Location",
    "DeviceID",
    "IP Address",
    "MerchantID",
    "Channel",
    "CustomerAge",
    "CustomerOccupation",
    "TransactionDuration",
    "LoginAttempts",
    "AccountBalance",
    "PreviousTransactionDate",
]

FLOAT_COLUMNS = ["TransactionAmount", "AccountBalance"]
INT_COLUMNS   = ["CustomerAge", "TransactionDuration", "LoginAttempts"]
DATE_COLUMNS  = ["TransactionDate", "PreviousTransactionDate"]

ALLOWED_TRANSACTION_TYPES = {"Debit", "Credit", "Transfer", "Withdrawal", "Deposit"}
ALLOWED_CHANNELS          = {"ATM", "Online", "Branch", "Mobile"}


def section(title):
    """Print a visible section header."""
    print("\n" + "-" * 60)
    print("  " + title)
    print("-" * 60)


def load_csv(path):
    """Load the CSV file into a pandas DataFrame with error handling."""
    if not os.path.exists(path):
        print("\n[ERROR] CSV file not found: " + path)
        print("  Make sure bank_transactions_data_2.csv is in the data/ folder.")
        sys.exit(1)
    try:
        # Read all columns as strings first so we detect type problems ourselves
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        print("[OK] CSV loaded from: " + path)
        return df
    except pd.errors.EmptyDataError:
        print("[ERROR] The CSV file is empty.")
        sys.exit(1)
    except pd.errors.ParserError as exc:
        print("[ERROR] Could not parse the CSV file:\n  " + str(exc))
        sys.exit(1)
    except Exception as exc:
        print("[ERROR] Unexpected error while reading CSV:\n  " + str(exc))
        sys.exit(1)


def check_column_presence(df):
    """Verify all expected columns exist in the file."""
    section("COLUMN PRESENCE CHECK")
    actual   = set(df.columns)
    expected = set(EXPECTED_COLUMNS)
    missing  = expected - actual
    extra    = actual - expected

    if missing:
        print("[FAIL] Missing columns (" + str(len(missing)) + "): " + str(sorted(missing)))
        print("  Cannot continue without all required columns.")
        sys.exit(1)
    else:
        print("[OK] All " + str(len(EXPECTED_COLUMNS)) + " expected columns are present.")

    if extra:
        print("[INFO] Extra columns found (kept): " + str(sorted(extra)))


def check_missing_values(df):
    """Count and report blank/NaN cells in every column."""
    section("MISSING VALUE CHECK")

    df_check = df.replace("", pd.NA)
    missing_counts = df_check.isnull().sum()
    cols_with_missing = missing_counts[missing_counts > 0]

    if cols_with_missing.empty:
        print("[OK] No missing values found in any column.")
        return 0

    total = int(cols_with_missing.sum())
    print("[WARN] " + str(total) + " missing value(s) across " + str(len(cols_with_missing)) + " column(s):")
    for col, count in cols_with_missing.items():
        bad_rows = df_check.index[df_check[col].isnull()].tolist()
        preview  = bad_rows[:10]
        print("  '" + col + "': " + str(count) + " missing at rows " + str(preview) + ("..." if len(bad_rows) > 10 else ""))
    return total


def check_duplicate_ids(df):
    """Detect rows that share the same TransactionID."""
    section("DUPLICATE TransactionID CHECK")

    dup_mask  = df.duplicated(subset=["TransactionID"], keep=False)
    dup_count = int(dup_mask.sum())

    if dup_count == 0:
        print("[OK] No duplicate TransactionIDs found.")
    else:
        print("[WARN] " + str(dup_count) + " row(s) share a non-unique TransactionID:")
        print(df[dup_mask][["TransactionID", "AccountID", "TransactionDate"]].to_string())
    return dup_count


def validate_dates(df):
    """Convert date columns to datetime; flag rows that fail parsing."""
    section("DATE COLUMN VALIDATION")

    total_invalid = 0
    for col in DATE_COLUMNS:
        converted     = pd.to_datetime(df[col], errors="coerce")
        invalid_mask  = converted.isna()
        invalid_count = int(invalid_mask.sum())

        if invalid_count == 0:
            print("[OK] '" + col + "' - all " + str(len(df)) + " values parsed successfully.")
        else:
            total_invalid += invalid_count
            bad_rows = df.index[invalid_mask].tolist()
            print("[WARN] '" + col + "' - " + str(invalid_count) + " unparseable value(s) at rows: " + str(bad_rows[:10]) + ("..." if len(bad_rows) > 10 else ""))
            print("       Sample bad values: " + str(df.loc[bad_rows[:5], col].tolist()))

        df[col] = converted

    return df, total_invalid


def validate_numerics(df):
    """Convert numeric columns, enforce business rules, report problems."""
    section("NUMERIC COLUMN VALIDATION")

    total_invalid = 0

    # Float columns
    for col in FLOAT_COLUMNS:
        converted     = pd.to_numeric(df[col], errors="coerce")
        invalid_mask  = converted.isna()
        invalid_count = int(invalid_mask.sum())
        if invalid_count > 0:
            total_invalid += invalid_count
            print("[WARN] '" + col + "' - " + str(invalid_count) + " non-numeric value(s) at rows: " + str(df.index[invalid_mask].tolist()[:10]))
        else:
            print("[OK] '" + col + "' - all values are numeric.")
        df[col] = converted

    # Integer columns
    for col in INT_COLUMNS:
        converted     = pd.to_numeric(df[col], errors="coerce")
        invalid_mask  = converted.isna()
        invalid_count = int(invalid_mask.sum())
        if invalid_count > 0:
            total_invalid += invalid_count
            print("[WARN] '" + col + "' - " + str(invalid_count) + " non-numeric value(s) at rows: " + str(df.index[invalid_mask].tolist()[:10]))
        else:
            print("[OK] '" + col + "' - all values are numeric.")
        df[col] = converted
        if invalid_count == 0:
            df[col] = df[col].astype("Int64")

    # Business rules
    section("BUSINESS RULE VALIDATION")

    if df["TransactionAmount"].notna().any():
        bad = df[df["TransactionAmount"] <= 0]
        if not bad.empty:
            total_invalid += len(bad)
            print("[WARN] 'TransactionAmount' - " + str(len(bad)) + " row(s) with amount <= 0.")
            print(bad[["TransactionID", "TransactionAmount"]].to_string())
        else:
            print("[OK] 'TransactionAmount' - all values > 0.")

    if df["AccountBalance"].notna().any():
        bad = df[df["AccountBalance"] < 0]
        if not bad.empty:
            total_invalid += len(bad)
            print("[WARN] 'AccountBalance' - " + str(len(bad)) + " row(s) with balance < 0.")
            print(bad[["TransactionID", "AccountBalance"]].to_string())
        else:
            print("[OK] 'AccountBalance' - all values >= 0.")

    if df["CustomerAge"].notna().any():
        bad = df[~df["CustomerAge"].between(1, 120)]
        if not bad.empty:
            total_invalid += len(bad)
            print("[WARN] 'CustomerAge' - " + str(len(bad)) + " row(s) outside [1, 120].")
            print(bad[["TransactionID", "CustomerAge"]].to_string())
        else:
            print("[OK] 'CustomerAge' - all values in [1, 120].")

    if df["TransactionDuration"].notna().any():
        bad = df[df["TransactionDuration"] < 1]
        if not bad.empty:
            total_invalid += len(bad)
            print("[WARN] 'TransactionDuration' - " + str(len(bad)) + " row(s) with duration < 1.")
            print(bad[["TransactionID", "TransactionDuration"]].to_string())
        else:
            print("[OK] 'TransactionDuration' - all values >= 1.")

    if df["LoginAttempts"].notna().any():
        bad = df[df["LoginAttempts"] < 0]
        if not bad.empty:
            total_invalid += len(bad)
            print("[WARN] 'LoginAttempts' - " + str(len(bad)) + " row(s) with negative login attempts.")
            print(bad[["TransactionID", "LoginAttempts"]].to_string())
        else:
            print("[OK] 'LoginAttempts' - all values >= 0.")

    return df, total_invalid


def validate_categoricals(df):
    """Check TransactionType and Channel against allowed value sets."""
    section("CATEGORICAL COLUMN VALIDATION")

    total_invalid = 0

    unexpected_types = df[~df["TransactionType"].isin(ALLOWED_TRANSACTION_TYPES)]
    if unexpected_types.empty:
        print("[OK] 'TransactionType' - all values in allowed set.")
        print("       Unique values: " + str(sorted(df["TransactionType"].unique())))
    else:
        total_invalid += len(unexpected_types)
        print("[WARN] 'TransactionType' - " + str(len(unexpected_types)) + " unexpected value(s).")
        print("       Found: " + str(sorted(df["TransactionType"].unique())))

    unexpected_channels = df[~df["Channel"].isin(ALLOWED_CHANNELS)]
    if unexpected_channels.empty:
        print("[OK] 'Channel' - all values in allowed set.")
        print("       Unique values: " + str(sorted(df["Channel"].unique())))
    else:
        total_invalid += len(unexpected_channels)
        print("[WARN] 'Channel' - " + str(len(unexpected_channels)) + " unexpected value(s).")
        print("       Found: " + str(sorted(df["Channel"].unique())))

    return total_invalid


def collect_stats(df):
    """Collect uniqueness statistics for key identifier columns."""
    return {
        "unique_accounts"  : df["AccountID"].nunique(),
        "unique_devices"   : df["DeviceID"].nunique(),
        "unique_ips"       : df["IP Address"].nunique(),
        "unique_merchants" : df["MerchantID"].nunique(),
        "unique_locations" : df["Location"].nunique(),
        "unique_channels"  : df["Channel"].nunique(),
    }


def print_summary(df, stats, total_missing, total_duplicates, total_invalid_dates, total_invalid_numerics):
    """Print the final validation summary."""
    print("\n")
    print("=" * 48)
    print("  TRANSACTION DATA VALIDATION SUMMARY")
    print("=" * 48)
    print("  Rows                  : " + str(len(df)))
    print("  Columns               : " + str(len(df.columns)))
    print("  Missing values        : " + str(total_missing))
    print("  Duplicate TxIDs       : " + str(total_duplicates))
    print("  Invalid dates         : " + str(total_invalid_dates))
    print("  Invalid numeric values: " + str(total_invalid_numerics))
    print("  Unique accounts       : " + str(stats["unique_accounts"]))
    print("  Unique devices        : " + str(stats["unique_devices"]))
    print("  Unique IPs            : " + str(stats["unique_ips"]))
    print("  Unique merchants      : " + str(stats["unique_merchants"]))
    print("  Unique locations      : " + str(stats["unique_locations"]))
    print("  Unique channels       : " + str(stats["unique_channels"]))
    print("=" * 48)


def save_clean_csv(df, output_path):
    """Write the validated DataFrame to disk preserving all original columns."""
    try:
        df.to_csv(output_path, index=False)
        print("\n  Clean dataset saved to:")
        print("  " + output_path)
    except IOError as exc:
        print("[ERROR] Could not write clean CSV:\n  " + str(exc))
        sys.exit(1)


def main():
    print("=" * 60)
    print("  FRAUD DETECTION SYSTEM - STEP 1: DATA VALIDATION")
    print("=" * 60)
    print("  Input : " + INPUT_CSV)
    print("  Output: " + OUTPUT_CSV)

    df = load_csv(INPUT_CSV)
    check_column_presence(df)

    total_missing          = check_missing_values(df)
    total_duplicates       = check_duplicate_ids(df)
    df, total_invalid_dates    = validate_dates(df)
    df, total_invalid_numerics = validate_numerics(df)
    validate_categoricals(df)

    stats = collect_stats(df)
    print_summary(df, stats, total_missing, total_duplicates, total_invalid_dates, total_invalid_numerics)

    critical_issues = total_missing + total_duplicates + total_invalid_dates + total_invalid_numerics

    if critical_issues > 0:
        print("\n[WARN] " + str(critical_issues) + " issue(s) found. Clean file NOT saved.")
        print("  Review the warnings above, fix the source data, and re-run.")
    else:
        print("\n  Validation completed successfully.")
        save_clean_csv(df, OUTPUT_CSV)

    print("\n" + "=" * 60)
    print("  Done.")
    print("=" * 60)


if __name__ == "__main__":
    main()
