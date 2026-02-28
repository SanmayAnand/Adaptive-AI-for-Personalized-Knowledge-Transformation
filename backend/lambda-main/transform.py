# transform.py — Person C owns this entirely
# Lambda: akte-main (placed here by Person A when received)
#
# Public API (Person A calls this):
#   rewrite(text: str, level: str) -> str
#
# What it does:
#   1. Validate level — if not in ['beginner','intermediate','expert'], default to 'intermediate'
#   2. Split text into ~400-word chunks on sentence boundaries (_chunk)
#   3. For each chunk, call Bedrock Claude 3 Haiku with the level-specific prompt (_call)
#   4. Validate the output (_valid) — reject if:
#      - Output < 40 chars
#      - Contains refusal phrases: 'I cannot', 'I apologize', 'As an AI'
#      - expert: output longer than 90% of input (not condensed enough)
#      - beginner: output shorter than 70% of input (not expanded enough)
#      If invalid → fall back to original chunk (never return empty/garbage)
#   5. Prepend a header line identifying the level
#   6. Join all chunks with double newlines and return
#
# Bedrock client:
#   bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
#   MODEL = 'anthropic.claude-3-haiku-20240307-v1:0'
#
# PROMPTS dict (THREE prompts — this is the most important part of the module):
#   'beginner':
#     - First use of any technical term → add plain-English explanation in parentheses
#     - After each concept → add analogy starting with "Think of it like:"
#     - Max 20 words per sentence
#     - Replace formal vocab with everyday words
#     - NEVER change numbers, formulas, dates, names, factual claims
#     - Should feel like a brilliant tutor explaining to a smart 16-year-old
#   'intermediate':
#     - Keep all technical terms; clarify only the most complex ones
#     - Trim basic background; keep all substantive content
#     - NEVER change numbers, formulas, dates, names, factual claims
#     - Roughly same length as input
#   'expert':
#     - Delete all introductory/background sentences
#     - Remove sentences obvious to an expert
#     - Keep ALL formulas, numerical results, technical terms, conclusions exactly
#     - Output 40–60% shorter than input
#     - Same logical order, no hand-holding
#
# Private helpers to implement:
#   _chunk(text, size=400) -> list[str]    — sentence-boundary splitting
#   _call(prompt, chunk) -> str            — Bedrock API call, returns text content
#   _valid(orig, out, level) -> bool       — output quality gate
#   rewrite(text, level) -> str            ← THIS IS THE ONLY PUBLIC FUNCTION
#
# IMPORTANT: The function name must be exactly rewrite(text, level).
#            main_handler.py imports it as: from transform import rewrite
#            Do NOT rename it.
#
# Test locally:
#   python3 -c "from transform import rewrite; print(rewrite('Mitosis is cell division.', 'beginner'))"
#
# Full working code is in the blueprint document (Section: PERSON C, "Full code — transform.py").
# Spend the most time on the PROMPTS dict — that's where the product value lives.
# After writing, test all 3 levels on the same paragraph and compare outputs visually.

import boto3
import json
import re

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
MODEL = 'anthropic.claude-3-haiku-20240307-v1:0'

# TODO: fill in all three prompts as described above
PROMPTS = {
    'beginner': '''TODO: beginner prompt here''',
    'intermediate': '''TODO: intermediate prompt here''',
    'expert': '''TODO: expert prompt here''',
}


def _chunk(text, size=400):
    # TODO: split on sentence boundaries, ~size words per chunk
    raise NotImplementedError


def _call(prompt, chunk):
    # TODO: call bedrock.invoke_model with MODEL, return text string
    raise NotImplementedError


def _valid(orig, out, level):
    # TODO: quality gate — see rules above
    raise NotImplementedError


def rewrite(text, level):
    """
    Called by main_handler.py.
    text = clean text from Person B's ocr.py
    level = 'beginner' | 'intermediate' | 'expert'
    Returns fully rewritten document as string.
    """
    # TODO: implement as described above
    raise NotImplementedError
