# =============================================================================
# transform/transform.py
# WHO WRITES THIS: Person C
# WHAT THIS IS: Rewrites text using AWS Bedrock AI based on user's level
# =============================================================================
#
# YOUR ONE JOB:
#   Write the function rewrite(text, level) → string
#   Person A's main_handler.py calls: rewritten = transform.rewrite(clean_text, 'beginner')
#   You call Bedrock AI with the right prompt for that level and return the rewritten text.
#
# THE 3 LEVELS:
#   'beginner'     → explain everything, add analogies, keep sentences short
#   'intermediate' → keep technical terms, trim only the obvious basics
#   'expert'       → condense aggressively, delete all background, keep only key info
#
# WHY CHUNKING:
#   Long documents won't fit in one Bedrock call. Split into ~400-word chunks,
#   rewrite each chunk separately, then join them back together.
#
# INSTALL:
#   pip install boto3
#
# =============================================================================

import boto3
import json
import re

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
MODEL   = 'anthropic.claude-3-haiku-20240307-v1:0'


# =============================================================================
# PROMPTS — THIS IS THE MOST IMPORTANT PART. SPEND THE MOST TIME HERE.
# After writing, test all 3 on the same paragraph and compare the outputs.
# Beginner output should look visibly LONGER with inline explanations.
# Expert output should look visibly SHORTER and denser.
# =============================================================================

PROMPTS = {

    'beginner': '''You are an adaptive learning assistant. Rewrite the following text for a BEGINNER.

Follow every rule:
1. At the FIRST use of any technical term, immediately add a plain-English explanation in parentheses.
   Example: "ATP (the molecule cells use as fuel)"
2. After each new concept, add one concrete analogy starting with "Think of it like:".
3. Maximum 20 words per sentence. Break long sentences apart.
4. Replace formal vocabulary with everyday words where the meaning is preserved.
5. NEVER change any number, formula, date, name, or factual claim.
6. The output should feel like a brilliant tutor explaining to a smart 16-year-old.

Text to rewrite:
''',

    'intermediate': '''You are an adaptive learning assistant. Rewrite the following text for an INTERMEDIATE reader.

Follow every rule:
1. Keep all technical terms. Add a one-line clarification only for the most complex ones.
   Skip terms the reader likely already knows.
2. Trim very basic background sentences but keep all substantive content.
3. NEVER change any number, formula, date, name, or factual claim.
4. Output should be roughly similar in length to the input.

Text to rewrite:
''',

    'expert': '''You are an adaptive learning assistant. Condense the following text for an EXPERT reader.

Follow every rule:
1. Delete all introductory and background sentences. Experts already know the context.
2. Remove every sentence that states something an expert in this field finds obvious.
3. Keep ALL formulas, numerical results, technical terms, and conclusions exactly as written.
4. Output should be 40–60% shorter than the input. Dense, no hand-holding.
5. Preserve the same logical order, but cut every redundant sentence.

Text to rewrite:
''',

}


def _chunk(text, size=400):
    """
    Split text into chunks of roughly `size` words each.
    Split on sentence boundaries (after . ! ?) so we don't cut mid-sentence.
    Returns a list of strings.

    HOW TO IMPLEMENT:
      sentences = re.split(r'(?<=[.!?])\s+', text)
      chunks, current, count = [], [], 0
      for sentence in sentences:
          words = sentence.split()
          if count + len(words) > size and current:
              chunks.append(' '.join(current))
              current, count = words, len(words)
          else:
              current.extend(words)
              count += len(words)
      if current:
          chunks.append(' '.join(current))
      return chunks
    """
    # TODO: implement this
    pass


def _call_bedrock(prompt, chunk):
    """
    Send one chunk to Bedrock Claude and return the rewritten text.

    HOW TO IMPLEMENT:
      body = json.dumps({
          'anthropic_version': 'bedrock-2023-05-31',
          'max_tokens': 1500,
          'messages': [{'role': 'user', 'content': prompt + '\n' + chunk}]
      })
      response = bedrock.invoke_model(modelId=MODEL, body=body)
      result   = json.loads(response['body'].read())
      return result['content'][0]['text'].strip()
    """
    # TODO: implement this
    pass


def _is_valid(original, output, level):
    """
    Check if the rewritten output is acceptable.
    If not valid, we fall back to the original chunk (never return garbage).

    RULES:
      - Output must be at least 40 characters
      - Must not contain AI refusal phrases like 'I cannot', 'I apologize', 'As an AI'
      - For 'expert': output should be shorter than 90% of original (it was condensed)
      - For 'beginner': output should be longer than 70% of original (it was expanded)

    HOW TO IMPLEMENT:
      if len(output) < 40:
          return False
      for phrase in ['I cannot', 'I apologize', 'As an AI']:
          if phrase in output:
              return False
      if level == 'expert' and len(output) > len(original) * 0.9:
          return False
      if level == 'beginner' and len(output) < len(original) * 0.7:
          return False
      return True
    """
    # TODO: implement this
    pass


def rewrite(text, level):
    """
    MAIN FUNCTION — this is the only function Person A calls.

    Takes the full document text and rewrites it for the given level.
    Splits into chunks, rewrites each one, joins them back.

    HOW TO IMPLEMENT:
      # Default to intermediate if invalid level passed
      if level not in PROMPTS:
          level = 'intermediate'

      prompt = PROMPTS[level]
      chunks = _chunk(text)

      print(f'[Transform] {len(chunks)} chunks, level={level}')

      output = []
      for i, chunk in enumerate(chunks):
          print(f'[Transform] processing chunk {i+1}/{len(chunks)}')
          try:
              result = _call_bedrock(prompt, chunk)
              if not _is_valid(chunk, result, level):
                  print(f'[Transform] validation failed on chunk {i+1}, using original')
                  result = chunk
              output.append(result)
          except Exception as e:
              print(f'[Transform] error on chunk {i+1}: {e}, using original')
              output.append(chunk)   # never fail — use original chunk if Bedrock errors

      # Add a header so the user knows what level their document was written for
      level_labels = {
          'beginner':     'BEGINNER — Full explanations and examples added',
          'intermediate': 'INTERMEDIATE — Balanced for moderate prior knowledge',
          'expert':       'EXPERT — Condensed for professionals',
      }
      header = f'[ AKTE — {level_labels[level]} ]\n' + '='*60 + '\n\n'

      return header + '\n\n'.join(output)
    """
    # TODO: implement this
    pass
