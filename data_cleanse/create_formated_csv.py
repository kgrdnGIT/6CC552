import pandas as pd
import sys

def process_csv(input_file, output_file):
    # Read the CSV file
    df = pd.read_csv(input_file)

    # Remove '@message' header
    df = df.rename(columns={'@message': 'Message'})

    # Extract required fields from 'Message' column
    df[['Duration', 'Billed Duration', 'Memory Size', 'Max Memory Used', 'Init Duration']] = df['Message'].str.extract(r'Duration: (\d+\.\d+) ms.*?Billed Duration: (\d+) ms.*?Memory Size: (\d+) MB.*?Max Memory Used: (\d+) MB(?:.*?Init Duration: (\d+\.\d+) ms)?')

    # Drop 'Message' column
    df = df.drop(columns=['Message'])

    # Save the DataFrame to a CSV file
    df.to_csv(output_file, index=False)

if __name__ == "__main__":
    # Check if the correct number of arguments is provided
    if len(sys.argv) != 3:
        print("Usage: python script.py input_file.csv output_file.csv")
        sys.exit(1)

    # Get the input and output file names from command-line arguments
    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # Process the CSV file and save the output
    process_csv(input_file, output_file)
