import jiwer
import os
from normalizer import EnglishNumberNormalizer

def evaluate_smart():
    # Check if FAR exists
    if not os.path.exists("normalizer.far"):
        print("Warning: normalizer.far not found. Run 'python solution.py' first.")
    
    norm = EnglishNumberNormalizer()
    hypothesis = []
    reference = []
    
    print("Reading file and evaluating...")
    
    try:
        # utf-8-sig handles BOM characters often present in Windows text files
        with open("test_en.txt", "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("Error: 'test_en.txt' file not found.")
        return

    count = 0
    errors = 0

    for line in lines:
        parts = line.strip().split("~")
        if len(parts) < 2: continue
        
        inp = parts[0].strip()
        ref = parts[1].strip()
        
        # --- SCOPE FILTERING ---
        # The challenge is strictly 0-1000. The dataset contains millions.
        # We must ignore out-of-scope numbers to get an accurate WER.
        
        is_valid = False
        
        # Case 1: Special digit reading (e.g., 004)
        if inp.startswith("0") and len(inp) > 1: 
            is_valid = True 
        else:
            # Case 2: Standard integer -1000 to 1000
            try:
                val = int(inp)
                if -1000 <= val <= 1000: 
                    is_valid = True
            except: 
                pass # Ignore non-integers (like floats or dates)

        if is_valid:
            # Normalize
            pred = norm.normalize_text(inp)
            
            hypothesis.append(pred)
            reference.append(ref)
            count += 1
            
            # Print errors for debugging
            if pred != ref:
                print(f"[ERROR] Input: {inp} | Predicted: '{pred}' | Expected: '{ref}'")
                errors += 1

    if count > 0:
        wer = jiwer.wer(reference, hypothesis)
        print(f"\n--- FINAL RESULTS ---")
        print(f"Sentences tested (0-1000 range): {count}")
        print(f"Total Errors: {errors}")
        print(f"Global WER: {wer * 100:.2f}%")
    else:
        print("No valid lines (range 0-1000) found in the file.")

if __name__ == "__main__":
    evaluate_smart()