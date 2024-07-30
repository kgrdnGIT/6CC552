import pandas as pd

# Read the CSV file
df = pd.read_csv('lambda-test-logs-csv')

# Remove '@message' header
df = df.rename(columns={'@message': 'Message'})

# Extract required fields from 'Message' column
df[['Duration', 'Billed Duration', 'Memory Size', 'Max Memory Used', 'Init Duration']] = df['Message'].str.extract(r'Duration: (\d+\.\d+) ms.*?Billed Duration: (\d+) ms.*?Memory Size: (\d+) MB.*?Max Memory Used: (\d+) MB(?:.*?Init Duration: (\d+\.\d+) ms)?')

# Drop 'Message' column
df = df.drop(columns=['Message'])

# Print the modified DataFrame
print(df)

