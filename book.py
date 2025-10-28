import pandas as pd

# Try reading the CSV file with different configurations to handle errors
try:
    books_df = pd.read_csv("books.csv", encoding="utf-8", delimiter=",", on_bad_lines="skip")
except Exception as e:
    print(f"Error loading CSV: {e}")
    exit()

# Display first few rows to check the structure
print(books_df.head())
