# =============================================================================
# transform/transform.py  —  Person C owns this file entirely
# =============================================================================
#
# WHERE THIS FILE LIVES IN THE REPO:
#   transform/transform.py
#
# DEPLOYED AS:
#   Zipped together with main_handler.py and sent to Person A.
#   Person A adds it to the akte-main Lambda zip alongside ocr.py.
#
# PUBLIC API — one function Person A calls:
#   result = transform.run(user_id, filename, doc_id)
#   Returns: {
#     "s3_key":      "outputs/{user_id}/{filename}_transformed.txt",
#     "level":       "beginner" | "intermediate" | "expert",
#     "intent":      "studying" | "applying" | "explaining" | "exploring",
#     "annotations": [ {"term":..., "short":..., "detail":..., "type":...}, ... ]
#   }
#
# READS FROM S3:
#   extracted/{user_id}/{filename}.txt     ← Person B (ocr) writes this
#
# READS FROM DYNAMODB:
#   Table: akte-users
#   Key:   { user_id: ..., doc_id: ... }
#   Reads: level, intent   (written by quiz_handler score action)
#
# WRITES TO S3:
#   outputs/{user_id}/{filename}_transformed.txt
#
# UPDATES DYNAMODB (update_item — NEVER put_item, that would wipe quiz results):
#   transform_status   → 'complete' | 'failed: ...'
#   s3_transformed_key → S3 path of the output file
#   annotations        → list of clickable term objects for the frontend
#   updated_at         → ISO timestamp
#
# ENV VARS (read from Lambda environment — Person A sets these):
#   BUCKET_NAME        → S3 bucket (default: 'akte-bucket')
#   TABLE_NAME         → DynamoDB table (default: 'akte-users')
#   AWS_DEFAULT_REGION → region (default: 'us-east-1')
#
# =============================================================================

import boto3
import json
import re
import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ── AWS clients (lazy, same pattern as ocr.py) ────────────────────────────────
_s3 = _bedrock = _dynamodb = None

def _get_s3():
    global _s3
    if not _s3:
        _s3 = boto3.client('s3', region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
    return _s3

def _get_bedrock():
    global _bedrock
    if not _bedrock:
        _bedrock = boto3.client('bedrock-runtime',
                                region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
    return _bedrock

def _get_dynamodb():
    global _dynamodb
    if not _dynamodb:
        _dynamodb = boto3.resource('dynamodb',
                                   region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
    return _dynamodb

# ── Constants (match what quiz_handler and upload_handler use) ────────────────
BUCKET = os.environ.get('BUCKET_NAME', 'akte-bucket')
TABLE  = os.environ.get('TABLE_NAME',  'akte-users')
MODEL  = 'anthropic.claude-3-haiku-20240307-v1:0'

# How many words per Bedrock call. 450 words ≈ 600 tokens input, ~900 output.
# Cheap and fast. Haiku handles ~200K context but we chunk for cost control.
CHUNK_WORDS = 450


# =============================================================================
# SECTION 1 — TEXT CHUNKING
# =============================================================================

def _chunk(text: str) -> list:
    """
    Split text into ~CHUNK_WORDS-word chunks, breaking on sentence boundaries.
    Sentence-aware splitting keeps each chunk coherent — no cut-off thoughts.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks, current, count = [], [], 0
    for s in sentences:
        w = s.split()
        if count + len(w) > CHUNK_WORDS and current:
            chunks.append(' '.join(current))
            current, count = list(w), len(w)
        else:
            current.extend(w)
            count += len(w)
    if current:
        chunks.append(' '.join(current))
    return chunks


# =============================================================================
# SECTION 2 — PROMPTS
# This is the most important part of this file.
# level  → controls density, depth, explanation volume
# intent → controls framing, emphasis, tone
# =============================================================================

def _build_system_prompt(level: str, intent: str) -> str:
    """
    Constructs the Bedrock system prompt by combining level + intent rules.
    System prompt is more token-efficient than putting instructions in the
    user message — Haiku respects system prompts reliably.
    """

    # ── Level rules ───────────────────────────────────────────────────────────
    level_rules = {
        'beginner': (
            "LEVEL: BEGINNER\n"
            "1. At the FIRST use of each technical term, add a plain-English explanation "
            "in parentheses immediately after. E.g. 'mitosis (the process where one cell "
            "splits into two identical copies)'.\n"
            "2. After each new concept introduce a concrete analogy beginning with "
            "'Think of it like: '.\n"
            "3. Max 20 words per sentence. Break long sentences into shorter ones.\n"
            "4. Replace formal academic vocabulary with everyday language.\n"
            "5. Output will be LONGER than input — explanations and analogies take space.\n"
        ),
        'intermediate': (
            "LEVEL: INTERMEDIATE\n"
            "1. Keep all technical vocabulary. Add a one-line clarification only for the "
            "most specialised terms — skip anything the reader likely already knows.\n"
            "2. Trim purely introductory background sentences, keep all substantive content.\n"
            "3. Sentence length is unrestricted — the reader handles complexity.\n"
            "4. Output should be roughly the same length as the input.\n"
        ),
        'expert': (
            "LEVEL: EXPERT\n"
            "1. Delete all introductory and background sentences — experts skip them anyway.\n"
            "2. Compress every sentence that states something any expert in this field "
            "would find obvious or self-evident.\n"
            "3. Preserve ALL formulas, numerical values, citations, and technical terms exactly.\n"
            "4. Output should be 40–60% shorter than the input. Dense. No hand-holding.\n"
        ),
    }

    # ── Intent rules ──────────────────────────────────────────────────────────
    intent_rules = {
        'studying': (
            "INTENT: STUDY MODE\n"
            "- Begin each section with one concise key-point sentence in bold (*like this*).\n"
            "- At the end of each chunk add a 'Key takeaway: ...' line.\n"
            "- Put the single most important term in each chunk in **double asterisks**.\n"
        ),
        'applying': (
            "INTENT: APPLICATION MODE\n"
            "- Emphasise concrete steps, outputs, and real-world uses of each concept.\n"
            "- Add 'In practice: ...' lines to connect theory to doing.\n"
            "- Skip historical background unless directly relevant to taking action.\n"
        ),
        'explaining': (
            "INTENT: EXPLAIN-TO-OTHERS MODE\n"
            "- Favour analogies and comparisons to familiar everyday things.\n"
            "- Add 'One way to explain this: ...' lines at key moments.\n"
            "- Tone: a knowledgeable friend explaining something to a smart non-expert.\n"
        ),
        'exploring': (
            "INTENT: EXPLORATION MODE\n"
            "- Keep prose flowing and engaging — not everything needs bullet points.\n"
            "- Add 'Interestingly, ...' or 'A surprising implication: ...' where warranted.\n"
            "- Tone: curious and energetic — make the content feel worth reading.\n"
        ),
    }

    base = (
        "You are AKTE — an adaptive knowledge engine. "
        "Your job is to rewrite the provided document chunk according to the rules below.\n\n"
        "NON-NEGOTIABLE RULES (override everything else):\n"
        "- NEVER alter any fact, number, formula, date, name, or citation.\n"
        "- NEVER refuse or comment on the task — output ONLY the rewritten text.\n"
        "- NEVER add a preamble like 'Here is the rewritten text:' — start immediately.\n\n"
    )

    lvl  = level_rules.get(level, level_rules['intermediate'])
    intn = intent_rules.get(intent, intent_rules['studying'])
    return base + lvl + "\n" + intn


# =============================================================================
# SECTION 3 — BEDROCK CALL
# =============================================================================

def _call_bedrock(system_prompt: str, chunk: str) -> str:
    body = json.dumps({
        'anthropic_version': 'bedrock-2023-05-31',
        'max_tokens': 1500,
        'system': system_prompt,
        'messages': [{'role': 'user', 'content': f'<chunk>\n{chunk}\n</chunk>'}]
    })
    resp = _get_bedrock().invoke_model(modelId=MODEL, body=body)
    return json.loads(resp['body'].read())['content'][0]['text'].strip()


# =============================================================================
# SECTION 4 — OUTPUT VALIDATION
# Basic sanity checks before accepting a rewritten chunk.
# On failure: fall back to original chunk — pipeline never breaks.
# =============================================================================

def _valid(original: str, rewritten: str, level: str) -> bool:
    if len(rewritten.strip()) < 40:
        return False
    # Model refused or went off-task
    refusals = ['I cannot', 'I apologize', 'As an AI', "I'm unable", 'I am unable']
    if any(p in rewritten for p in refusals):
        return False
    # Expert output must be shorter — if it isn't, the prompt didn't work
    if level == 'expert' and len(rewritten) > len(original) * 0.95:
        return False
    # Beginner output must not be shorter — we added explanations
    if level == 'beginner' and len(rewritten) < len(original) * 0.65:
        return False
    return True


# =============================================================================
# SECTION 5 — ANNOTATIONS
# Annotations = clickable/hoverable terms in the frontend learning view.
# One Bedrock call for the whole document (not per chunk) — cheap.
# Returns a list of objects the frontend uses for inline popups.
# =============================================================================

def _generate_annotations(text: str, level: str) -> list:
    """
    Identify the 8 most important terms/concepts in the document.
    For each: produce a short tooltip (≤12 words) and a 2-sentence explanation.
    Depth of explanation scales with level.

    Returns: [{"term": ..., "short": ..., "detail": ..., "type": ...}, ...]
    type is one of: concept | formula | person | definition
    """
    sample = ' '.join(text.split()[:2000])  # cap for cost

    depth_note = {
        'beginner':     'Assume zero prior knowledge. Use simple everyday language.',
        'intermediate': 'Some jargon is fine. Keep explanations accessible.',
        'expert':       'Be technically precise. Skip basic definitions.',
    }.get(level, '')

    prompt = (
        f"Identify the 8 most important technical terms or concepts in this document.\n"
        f"For each: provide (1) a short tooltip max 12 words, "
        f"(2) a 2-sentence detail explanation. {depth_note}\n"
        f"Return ONLY a valid JSON array, no markdown, no other text:\n"
        f'[{{"term":"...","short":"...","detail":"...","type":"concept"}}]\n'
        f'type must be exactly one of: concept, formula, person, definition\n\n'
        f'<document>\n{sample}\n</document>'
    )

    body = json.dumps({
        'anthropic_version': 'bedrock-2023-05-31',
        'max_tokens': 900,
        'messages': [{'role': 'user', 'content': prompt}]
    })

    try:
        resp = _get_bedrock().invoke_model(modelId=MODEL, body=body)
        raw  = json.loads(resp['body'].read())['content'][0]['text'].strip()
        # Strip markdown fences if Claude adds them
        if raw.startswith('```'):
            parts = raw.split('```')
            raw = parts[1] if len(parts) > 1 else raw
            if raw.lower().startswith('json'):
                raw = raw[4:]
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if not match:
            return []
        return json.loads(match.group(0))
    except Exception as e:
        logger.warning(f'[Transform] Annotation generation failed: {e}')
        return []


# =============================================================================
# SECTION 6 — DYNAMODB HELPERS
# CRITICAL: Always use update_item, NEVER put_item.
# quiz_handler already wrote the full row with quiz results.
# put_item would overwrite everything including the quiz score and level.
# =============================================================================

def _get_profile(user_id: str, doc_id: str) -> tuple:
    """
    Read level and intent from the DynamoDB row that quiz_handler wrote.
    Returns (level, intent) with safe defaults if read fails.
    """
    try:
        resp = _get_dynamodb().Table(TABLE).get_item(
            Key={'user_id': user_id, 'doc_id': doc_id}
        )
        item   = resp.get('Item', {})
        level  = item.get('level',  'intermediate')
        intent = item.get('intent', 'studying')
        return level, intent
    except Exception as e:
        logger.warning(f'[Transform] DynamoDB read failed, using defaults: {e}')
        return 'intermediate', 'studying'


def _update_dynamo_complete(user_id: str, doc_id: str,
                            s3_key: str, annotations: list):
    """Mark transform as complete. update_item preserves all existing fields."""
    _get_dynamodb().Table(TABLE).update_item(
        Key={'user_id': user_id, 'doc_id': doc_id},
        UpdateExpression=(
            'SET transform_status = :status, '
            's3_transformed_key = :key, '
            'annotations = :ann, '
            'updated_at = :ts'
        ),
        ExpressionAttributeValues={
            ':status': 'complete',
            ':key':    s3_key,
            ':ann':    annotations,
            ':ts':     datetime.now(timezone.utc).isoformat(),
        }
    )


def _update_dynamo_failed(user_id: str, doc_id: str, error: str):
    """Mark transform as failed. Swallows its own errors — never crash on cleanup."""
    try:
        _get_dynamodb().Table(TABLE).update_item(
            Key={'user_id': user_id, 'doc_id': doc_id},
            UpdateExpression='SET transform_status = :s, updated_at = :ts',
            ExpressionAttributeValues={
                ':s':  f'failed: {error[:200]}',
                ':ts': datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception:
        pass


# =============================================================================
# SECTION 7 — PUBLIC API
# =============================================================================

def run(user_id: str, filename: str, doc_id: str) -> dict:
    """
    Main entry point. Called by main_handler.py as:
        result = transform.run(user_id, filename, doc_id)

    Full pipeline:
      1. Read level + intent from DynamoDB (quiz_handler wrote these)
      2. Read extracted text from S3  (Person B / ocr wrote this)
      3. Build prompt from level + intent
      4. Chunk text → call Bedrock per chunk → validate → fallback on error
      5. Generate annotations (one extra Bedrock call on full text sample)
      6. Save output to S3: outputs/{user_id}/{filename}_transformed.txt
      7. Update DynamoDB: transform_status, s3_transformed_key, annotations

    Args:
        user_id  : same user_id used throughout the pipeline
        filename : sanitised filename from upload_handler (no raw user input)
        doc_id   : the sort key quiz_handler generated (user_id#filename#timestamp)

    Returns:
        {
            "s3_key":      "outputs/{user_id}/{filename}_transformed.txt",
            "level":       "beginner" | "intermediate" | "expert",
            "intent":      "studying" | "applying" | "explaining" | "exploring",
            "annotations": [ {"term":..., "short":..., "detail":..., "type":...}, ... ]
        }

    Raises:
        ValueError   — extracted text not found or empty (Person B hasn't finished)
        RuntimeError — S3 write failed
    """
    logger.info(f'[Transform] START  user={user_id}  file={filename}  doc={doc_id}')

    # ── 1. Get level + intent ─────────────────────────────────────────────────
    level, intent = _get_profile(user_id, doc_id)
    logger.info(f'[Transform] level={level}  intent={intent}')

    # ── 2. Read Person B's extracted text ─────────────────────────────────────
    # Path matches exactly what quiz_handler and upload_handler expect:
    # extracted/{user_id}/{filename}.txt
    extracted_key = f'extracted/{user_id}/{filename}.txt'
    try:
        obj  = _get_s3().get_object(Bucket=BUCKET, Key=extracted_key)
        text = obj['Body'].read().decode('utf-8')
    except Exception as e:
        _update_dynamo_failed(user_id, doc_id, str(e))
        raise ValueError(
            f'Extracted text not found at s3://{BUCKET}/{extracted_key}. '
            f'Ensure Person B\'s OCR Lambda has finished before calling transform. '
            f'Error: {e}'
        )

    if not text.strip():
        _update_dynamo_failed(user_id, doc_id, 'empty extracted text')
        raise ValueError(
            f'Extracted text at {extracted_key} exists but is empty. '
            f'This usually means the document had no readable content.'
        )

    # ── 3. Build system prompt ────────────────────────────────────────────────
    system_prompt = _build_system_prompt(level, intent)

    # ── 4. Chunk and rewrite ──────────────────────────────────────────────────
    chunks = _chunk(text)
    logger.info(f'[Transform] {len(chunks)} chunks to process')

    rewritten_chunks = []
    for i, chunk in enumerate(chunks):
        logger.info(f'[Transform] chunk {i + 1}/{len(chunks)}')
        try:
            result = _call_bedrock(system_prompt, chunk)
            if not _valid(chunk, result, level):
                logger.warning(f'[Transform] validation failed chunk {i} — using original')
                result = chunk
            rewritten_chunks.append(result)
        except Exception as e:
            logger.error(f'[Transform] Bedrock error chunk {i}: {e} — using original')
            rewritten_chunks.append(chunk)   # pipeline never breaks

    # ── 5. Assemble output with header ────────────────────────────────────────
    level_labels = {
        'beginner':     'Beginner — Full explanations and examples added',
        'intermediate': 'Intermediate — Balanced for moderate prior knowledge',
        'expert':       'Expert — Condensed for professionals',
    }
    intent_labels = {
        'studying':   'Study Mode',
        'applying':   'Application Mode',
        'explaining': 'Explain-to-Others Mode',
        'exploring':  'Exploration Mode',
    }
    header = (
        f'AKTE Personalised Document\n'
        f'Level:  {level_labels.get(level, level)}\n'
        f'Intent: {intent_labels.get(intent, intent)}\n'
        f'Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}\n'
        f'{"=" * 60}\n\n'
    )
    full_output = header + '\n\n'.join(rewritten_chunks)

    # ── 6. Generate annotations ───────────────────────────────────────────────
    logger.info('[Transform] Generating annotations...')
    annotations = _generate_annotations(text, level)
    logger.info(f'[Transform] {len(annotations)} annotations generated')

    # ── 7. Save to S3 ─────────────────────────────────────────────────────────
    # Path matches what upload_handler.py documents:
    # outputs/{user_id}/{filename}_transformed.txt
    output_key = f'outputs/{user_id}/{filename}_transformed.txt'
    try:
        _get_s3().put_object(
            Bucket=BUCKET,
            Key=output_key,
            Body=full_output.encode('utf-8'),
            ContentType='text/plain; charset=utf-8'
        )
    except Exception as e:
        _update_dynamo_failed(user_id, doc_id, f'S3 write failed: {e}')
        raise RuntimeError(f'Failed to save output to S3: {e}')

    # ── 8. Update DynamoDB ────────────────────────────────────────────────────
    _update_dynamo_complete(user_id, doc_id, output_key, annotations)
    logger.info(f'[Transform] DONE → s3://{BUCKET}/{output_key}')

    return {
        's3_key':      output_key,
        'level':       level,
        'intent':      intent,
        'annotations': annotations,
    }