"""
ML Feedback Loop / Training Module
===================================
This is for IMPROVING the OCR system over time.
You don't NEED to run this to use the main app — but it makes it smarter.

Learning Modes (as per your presentation):
1. Supervised learning using labeled data
2. Semi-supervised improvement  
3. Error-driven fine-tuning

Flow: Errors → Analysis → Retraining → Improved Performance
"""

import json
import os
import csv
import re
import collections


class TrainingDataCollector:
    """
    Collect corrections to build a training dataset.
    When OCR gets something wrong, you manually correct it → system learns.
    """

    def __init__(self, corrections_file='models/corrections.json'):
        self.corrections_file = corrections_file
        os.makedirs('models', exist_ok=True)
        self.corrections = self._load()

    def _load(self):
        if os.path.exists(self.corrections_file):
            with open(self.corrections_file) as f:
                return json.load(f)
        return {'pairs': [], 'char_corrections': {}, 'word_corrections': {}}

    def save(self):
        with open(self.corrections_file, 'w') as f:
            json.dump(self.corrections, f, indent=2)
        print(f"Saved {len(self.corrections['pairs'])} correction pairs.")

    def add_correction(self, ocr_text: str, correct_text: str, source: str = ''):
        """
        Add a manual correction pair.
        OCR thought it was X, but it should be Y.
        """
        self.corrections['pairs'].append({
            'ocr': ocr_text,
            'correct': correct_text,
            'source': source
        })
        # Extract character-level corrections
        self._extract_char_patterns(ocr_text, correct_text)
        self.save()
        print(f"✅ Added correction pair #{len(self.corrections['pairs'])}")

    def _extract_char_patterns(self, ocr: str, correct: str):
        """Learn common substitution errors."""
        ocr_words = ocr.split()
        correct_words = correct.split()
        for o, c in zip(ocr_words, correct_words):
            if o != c and len(o) == len(c):
                for oc, cc in zip(o, c):
                    if oc != cc:
                        key = f"{oc}→{cc}"
                        self.corrections['char_corrections'][key] = \
                            self.corrections['char_corrections'].get(key, 0) + 1

    def add_bulk_from_csv(self, csv_path: str):
        """
        Load corrections from a CSV file with columns: ocr_text, correct_text
        Great for batch corrections from Tesseract output.
        """
        count = 0
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.add_correction(row['ocr_text'], row['correct_text'])
                count += 1
        print(f"Loaded {count} corrections from CSV.")


class OCRPostProcessor:
    """
    Error-driven fine-tuning: apply learned corrections to new OCR output.
    This is the ML Feedback Loop in action.
    """

    def __init__(self, corrections_file='models/corrections.json'):
        self.corrections_file = corrections_file
        self.corrections = {}
        self.char_fixes = {}
        self._load_corrections()

    def _load_corrections(self):
        if not os.path.exists(self.corrections_file):
            return
        with open(self.corrections_file) as f:
            data = json.load(f)

        # Build word-level correction dict from pairs
        for pair in data.get('pairs', []):
            ocr_words = pair['ocr'].split()
            correct_words = pair['correct'].split()
            for o, c in zip(ocr_words, correct_words):
                if o != c:
                    # Vote-based: most frequent correction wins
                    if o not in self.corrections:
                        self.corrections[o] = collections.Counter()
                    self.corrections[o][c] += 1

        # Load char corrections (only use high-frequency ones)
        char_data = data.get('char_corrections', {})
        self.char_fixes = {k: v for k, v in char_data.items() if v >= 3}

    def apply(self, text: str) -> tuple:
        """Apply learned corrections. Returns (corrected_text, list_of_changes)."""
        changes = []
        words = text.split()
        result = []

        for word in words:
            clean = word.strip(r'.,!?;:')
            if clean in self.corrections:
                best = self.corrections[clean].most_common(1)[0][0]
                changes.append(f"'{clean}' → '{best}'")
                result.append(word.replace(clean, best))
            else:
                result.append(word)

        corrected = ' '.join(result)
        return corrected, changes


class ModelEvaluator:
    """
    Measure OCR accuracy: Character Error Rate (CER) and Word Error Rate (WER).
    These are the standard metrics for OCR quality.
    """

    def character_error_rate(self, hypothesis: str, reference: str) -> float:
        """
        CER = edit distance / len(reference)
        Lower is better. 0 = perfect, 1 = completely wrong.
        """
        return self._edit_distance(hypothesis, reference) / max(len(reference), 1)

    def word_error_rate(self, hypothesis: str, reference: str) -> float:
        """
        WER = word-level edit distance / number of reference words.
        Lower is better.
        """
        h_words = hypothesis.split()
        r_words = reference.split()
        return self._edit_distance_list(h_words, r_words) / max(len(r_words), 1)

    def _edit_distance(self, s1: str, s2: str) -> int:
        """Levenshtein distance between two strings."""
        m, n = len(s1), len(s2)
        dp = list(range(n + 1))
        for i in range(1, m + 1):
            prev = dp[:]
            dp[0] = i
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    dp[j] = prev[j-1]
                else:
                    dp[j] = 1 + min(prev[j], dp[j-1], prev[j-1])
        return dp[n]

    def _edit_distance_list(self, l1: list, l2: list) -> int:
        """Edit distance between word lists."""
        m, n = len(l1), len(l2)
        dp = list(range(n + 1))
        for i in range(1, m + 1):
            prev = dp[:]
            dp[0] = i
            for j in range(1, n + 1):
                if l1[i-1] == l2[j-1]:
                    dp[j] = prev[j-1]
                else:
                    dp[j] = 1 + min(prev[j], dp[j-1], prev[j-1])
        return dp[n]

    def evaluate_batch(self, pairs: list) -> dict:
        """
        Evaluate on a batch of (hypothesis, reference) pairs.
        pairs = [{'ocr': '...', 'correct': '...'}, ...]
        """
        cers = []
        wers = []
        for pair in pairs:
            cer = self.character_error_rate(pair['ocr'], pair['correct'])
            wer = self.word_error_rate(pair['ocr'], pair['correct'])
            cers.append(cer)
            wers.append(wer)

        return {
            'mean_cer': sum(cers) / len(cers) if cers else 0,
            'mean_wer': sum(wers) / len(wers) if wers else 0,
            'accuracy': (1 - sum(cers)/len(cers)) * 100 if cers else 0,
            'total_samples': len(pairs)
        }


# ── CLI Training Interface ────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 55)
    print("  OCR Training & Evaluation Tool")
    print("  ML Feedback Loop: Errors → Analysis → Retraining")
    print("=" * 55)
    print()

    collector = TrainingDataCollector()
    post_processor = OCRPostProcessor()
    evaluator = ModelEvaluator()

    while True:
        print("\nOptions:")
        print("  1. Add a manual correction")
        print("  2. Test post-processor on text")
        print("  3. Evaluate accuracy (batch)")
        print("  4. View correction statistics")
        print("  5. Exit")
        
        choice = input("\nChoice: ").strip()

        if choice == '1':
            print("\nEnter the WRONG text (what OCR said):")
            ocr_text = input("> ")
            print("Enter the CORRECT text:")
            correct_text = input("> ")
            source = input("Source (optional, press Enter to skip): ")
            collector.add_correction(ocr_text, correct_text, source)

        elif choice == '2':
            print("\nPaste text to auto-correct (press Enter twice when done):")
            lines = []
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
            text = '\n'.join(lines)
            corrected, changes = post_processor.apply(text)
            print("\n─── Corrected Text ───")
            print(corrected)
            if changes:
                print(f"\n─── {len(changes)} corrections applied ───")
                for c in changes:
                    print(f"  {c}")
            else:
                print("\nNo known corrections to apply.")

        elif choice == '3':
            pairs = collector.corrections.get('pairs', [])
            if not pairs:
                print("No correction pairs yet. Add some first.")
            else:
                metrics = evaluator.evaluate_batch(pairs)
                print(f"\n─── Evaluation Results ───")
                print(f"  Samples:       {metrics['total_samples']}")
                print(f"  Mean CER:      {metrics['mean_cer']:.3f} (Character Error Rate)")
                print(f"  Mean WER:      {metrics['mean_wer']:.3f} (Word Error Rate)")
                print(f"  Accuracy:      {metrics['accuracy']:.1f}%")

        elif choice == '4':
            pairs = collector.corrections.get('pairs', [])
            char_corr = collector.corrections.get('char_corrections', {})
            print(f"\n─── Statistics ───")
            print(f"  Total correction pairs: {len(pairs)}")
            print(f"  Unique char patterns learned: {len(char_corr)}")
            if char_corr:
                top = sorted(char_corr.items(), key=lambda x: x[1], reverse=True)[:10]
                print(f"  Top 10 char substitutions:")
                for pattern, count in top:
                    print(f"    {pattern}: {count} occurrences")

        elif choice == '5':
            print("Exiting training tool.")
            break
        else:
            print("Invalid choice.")