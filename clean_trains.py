import pandas as pd

# Read the cleaned CSV
df = pd.read_csv(r'c:\Users\prana\OneDrive\Documents\Railway_Block_Planner\Trains_Schedule_CLEANED.csv')

print('🔧 SECOND PASS CLEANING...\n')

initial_rows = len(df)

# Remove rows with missing departure or arrival times
df = df.dropna(subset=['departure', 'arrival'])

# Remove rows with missing station names
df = df.dropna(subset=['station_name'])

# Remove rows where train_number is 0 (conversion failed)
df = df[df['train_number'] != 0]

rows_removed = initial_rows - len(df)

print(f'Initial rows: {initial_rows:,}')
print(f'Rows removed (invalid data): {rows_removed:,}')
print(f'Final clean rows: {len(df):,}\n')

# Save final cleaned dataset
df.to_csv(r'c:\Users\prana\OneDrive\Documents\Railway_Block_Planner\Trains_Schedule_CLEANED.csv', index=False)

print('✅ FINAL CLEANED DATASET SAVED!\n')
print(f'Final dataset shape: {df.shape}')
print(f'Columns: {list(df.columns)}')
print(f'\nData Sample:')
print(df.head(15))
print(f'\nData Quality Check:')
print(f'Missing values: {df.isnull().sum().sum()} (0 is perfect)')
print(f'Duplicate rows: {df.duplicated().sum()}')
print(f'Unique trains: {df["train_number"].nunique()}')
print(f'Unique stations: {df["station_name"].nunique()}')
