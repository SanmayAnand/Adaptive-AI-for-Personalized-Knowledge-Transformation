# tests/backend/test_transform.py — Person C runs this locally
#
# Prerequisites:
#   pip install boto3
#   aws configure   (use keys from Person A)
#
# Run: python3 tests/backend/test_transform.py
#
# What to look for:
#   BEGINNER output: longer than input, has parenthetical explanations, "Think of it like:" analogies
#   INTERMEDIATE output: roughly same length, technical terms kept
#   EXPERT output: 40-60% shorter, no background sentences, dense

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend/lambda-main'))

from transform import rewrite

SAMPLE = """
Photosynthesis is the process by which plants use sunlight, water, and CO2 to
produce glucose and oxygen. It occurs in the chloroplasts. The light-dependent
reactions in the thylakoid membrane produce ATP and NADPH. The Calvin cycle in
the stroma uses these to fix CO2 into glucose (C6H12O6).
"""

if __name__ == '__main__':
    print("=" * 60)
    print("BEGINNER OUTPUT:")
    print("=" * 60)
    b = rewrite(SAMPLE, 'beginner')
    print(b)
    print(f"\n[Input: {len(SAMPLE)} chars | Output: {len(b)} chars — should be LONGER]")

    print("\n" + "=" * 60)
    print("INTERMEDIATE OUTPUT:")
    print("=" * 60)
    m = rewrite(SAMPLE, 'intermediate')
    print(m)
    print(f"\n[Input: {len(SAMPLE)} chars | Output: {len(m)} chars — should be SIMILAR]")

    print("\n" + "=" * 60)
    print("EXPERT OUTPUT:")
    print("=" * 60)
    e = rewrite(SAMPLE, 'expert')
    print(e)
    print(f"\n[Input: {len(SAMPLE)} chars | Output: {len(e)} chars — should be SHORTER (40-60%)]")
