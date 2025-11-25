import pynini
from pynini import Fst
import os
import string

class EnglishNumberNormalizer:
    def __init__(self):
        self.normalizer_fst = self._build_complete_normalizer()
    
    def _build_complete_normalizer(self):
        """
        Constructs the Finite State Transducer (FST) for English numbers.
        Uses weights to prioritize longest matches (hundreds) over single digits.
        """
        
        # --- 1. VOCABULARY (Pure, Weight 0) ---
        
        # Digits 1-9
        digit_map = [
            ("1", "one"), ("2", "two"), ("3", "three"), ("4", "four"),
            ("5", "five"), ("6", "six"), ("7", "seven"), ("8", "eight"), ("9", "nine")
        ]
        # digits_pure is used inside larger numbers (21, 150) without penalty
        digits_pure = pynini.string_map(digit_map).optimize()
        
        # Zero
        zero = pynini.cross("0", "zero")

        # Teens 10-19
        teens_map = [
            ("10", "ten"), ("11", "eleven"), ("12", "twelve"), ("13", "thirteen"),
            ("14", "fourteen"), ("15", "fifteen"), ("16", "sixteen"), 
            ("17", "seventeen"), ("18", "eighteen"), ("19", "nineteen")
        ]
        teens = pynini.string_map(teens_map).optimize()

        # Tens 20, 30... 90
        tens_map = [
            ("2", "twenty"), ("3", "thirty"), ("4", "forty"), ("5", "fifty"),
            ("6", "sixty"), ("7", "seventy"), ("8", "eighty"), ("9", "ninety")
        ]
        tens = pynini.string_map(tens_map).optimize()

        # --- 2. PENALTY FOR STANDALONE DIGITS ---
        # We create a version of digits with weight=1.0.
        # This makes the FST avoid using this rule if a "cheaper" rule (hundreds) is available.
        weight_one = pynini.accep("", weight=1.0)
        digits_penalized = digits_pure + weight_one

        # --- 3. COMPOSITE NUMBERS 20-99 ---
        
        ins_space = pynini.cross("", " ")
        
        # 20, 30...
        tens_clean = tens + pynini.cross("0", "")
        # 21-99 (Uses digits_pure, so cost is 0)
        tens_composite = tens + ins_space + digits_pure
        
        numbers_20_99 = (tens_clean | tens_composite).optimize()

        # Group 1-99 for use inside hundreds (Pure versions)
        numbers_1_99_pure = (digits_pure | teens | numbers_20_99).optimize()

        # --- 4. HUNDREDS 100-999 ---
        
        ins_hundred = pynini.cross("", " hundred")
        ins_hundred_and = pynini.cross("", " hundred and ")
        
        # Exact Hundreds (e.g., 100)
        hundreds_exact = digits_pure + pynini.cross("00", "") + ins_hundred
        
        # Hundreds with remainder (e.g., 123)
        # 0-padding handling for 101-109
        padded_digits = pynini.cross("0", "") + digits_pure
        remainder_100 = (padded_digits | numbers_1_99_pure)
        
        # 123 -> "one" + " hundred and " + "twenty three" (Total Cost 0)
        hundreds_with_rest = digits_pure + ins_hundred_and + remainder_100
        
        hundreds = (hundreds_exact | hundreds_with_rest).optimize()
        
        # --- 5. SPECIAL: DIGIT SEQUENCES (004) ---
        # Logic: "0" + space + "0" + space + "4"
        zero_word = pynini.cross("0", " zero")
        
        # We use digits_pure here so it's cheaper (Cost 0) than fallback (Cost 1)
        any_digit_word = (zero_word | digits_pure)
        
        
        # Matches "0" followed by 1+ digits, inserting spaces before each subsequent digit
        seq_digits = zero_word  + (pynini.cross("", " ") + any_digit_word).closure(1)
        # --- 6. FINAL UNION ---
        
        thousand = pynini.cross("1000", "one thousand")

        # Negatives
        minus = pynini.cross("-", "minus ")
        
        # We assemble the positive numbers.
        # CRITICAL: digits_penalized is the ONLY way to match a single digit 1-9 here.
        # Everything else uses digits_pure internally.
        positive_cardinals = (
            thousand |          # Cost 0
            hundreds |          # Cost 0
            seq_digits |        # Cost 0
            numbers_20_99 |     # Cost 0
            teens |             # Cost 0
            zero |              # Cost 0
            digits_penalized    # Cost 1 (Last resort)
        ).optimize()
        
        # Combine with negatives
        final_grammar = (positive_cardinals | (minus + positive_cardinals)).optimize()

        # --- 7. CONTEXT (SIGMA STAR) ---
        safe_printables = [c for c in string.printable if c not in "[]"]
        chars = pynini.union(*[pynini.escape(c) for c in safe_printables])
        sigma_star = pynini.closure(chars)
        
        return pynini.cdrewrite(
            final_grammar,
            "",
            "",
            sigma_star
        ).optimize()

    def normalize_text(self, text):
        """
        Uses native composition and shortestpath to respect weights.
        """
        try:
            input_fst = pynini.escape(text)
            lattice = input_fst @ self.normalizer_fst
            # shortestpath will pick the path with lowest weight (Cost 0 vs Cost 3)
            shortest_path = pynini.shortestpath(lattice).optimize()
            return shortest_path.string()
        except pynini.FstOpError:
            return text
        except Exception:
            return text

    def export_far(self, filename="normalizer.far"):
        if os.path.exists(filename):
            try: os.remove(filename)
            except: pass
        
        with pynini.Far(filename, mode="w", arc_type="standard") as far:
            far.add("NORMALIZE", self.normalizer_fst)
        print(f" FAR file generated: {os.path.abspath(filename)}")

if __name__ == "__main__":
    norm = EnglishNumberNormalizer()
    norm.export_far()
    
    print("\n--- Final Diagnostic Test ---")
    # Expected: "onetwothree" MUST be gone. 
    # Expected: "zerozerofour" MUST have spaces.
    tests = ["1", "123", "-2", "004", "1000", "I have 3 dogs"]
    
    for t in tests:
        res = norm.normalize_text(t)
        print(f"Input: '{t}' -> Output: '{res}'")