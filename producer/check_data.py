import pandas as pd

file_path = "../data/bank_transactions_data_2.csv"

df = pd.read_csv(file_path)

print("Dataset loaded successfully!")
print("Rows:", len(df))
print("Columns:", len(df.columns))

print("\nColumns:")
print(df.columns.tolist())

print("\nFirst 5 transactions:")
print(df.head())