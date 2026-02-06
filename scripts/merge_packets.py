import os
import glob
import shutil

# --- CONFIGURATION ---
OUTPUT_FILE = "final_dataset.csv"
PARTIAL_FILES_PATTERN = "partial_data_*.csv"

def merge_files():
    # 1. Find all partial files
    files = sorted(glob.glob(PARTIAL_FILES_PATTERN))
    
    if not files:
        print(" * No partial files found!")
        return

    print(f" Found {len(files)} files to merge. Starting...")

    # 2. Open the main output file in Write mode
    with open(OUTPUT_FILE, 'w') as outfile:
        
        # 3. Loop through every partial file
        for i, filename in enumerate(files):
            print(f"   Processing: {filename}...")
            
            with open(filename, 'r') as infile:
                # 4. Handle Headers
                if i == 0:
                    # First file: Write EVERYTHING (Header + Data)
                    shutil.copyfileobj(infile, outfile)
                else:
                    # Other files: Skip the first line (Header), write the rest
                    next(infile) # Jump over header
                    shutil.copyfileobj(infile, outfile)
    
    print(f" ./ Success! Merged {len(files)} files into '{OUTPUT_FILE}'.")
    
    # 5. Optional: Clean up (Delete partial files)
    # Uncomment the next two lines if you want to auto-delete the small files
    # for f in files:
    #     os.remove(f)

if __name__ == "__main__":
    merge_files()
