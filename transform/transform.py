# =============================================================================
# transform/transform.py  —  Person C owns this file
# =============================================================================
#
# PUBLIC API:
#   result = transform.run(user_id, filename, doc_id)
#   Returns: { "s3_key", "level", "intent", "annotations" }
#
# READS:  extracted/{user_id}/{filename}.txt  (OCR output)
#         DynamoDB: level, intent  (quiz output)
# WRITES: outputs/{user_id}/{filename}_transformed.txt
#         DynamoDB: transform_status, s3_transformed_key, annotations
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

# ── AWS clients ───────────────────────────────────────────────────────────────
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

BUCKET           = os.environ.get('BUCKET_NAME', 'ocr-ai-for-bharat1')
TABLE            = os.environ.get('TABLE_NAME',  'akte-users')
MODEL_TRANSFORM  = 'amazon.nova-lite-v1:0'                        # cheap: transform chunks
MODEL_ANNOTATE   = 'anthropic.claude-haiku-3-5-20251001-v1:0'    # smart: one call for annotations
CHUNK_WORDS      = 400   # smaller = Nova Lite stays focused, less likely to drift


# =============================================================================
# SECTION 1 — CHUNKING
# Split on paragraph boundaries first, then word count.
# Keeps ideas whole instead of cutting mid-argument.
# =============================================================================

def _chunk(text: str) -> list:
    paragraphs = re.split(r'\n\s*\n', text.strip())
    chunks, current_words, current_paras = [], 0, []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        wc = len(para.split())

        if current_words + wc > CHUNK_WORDS and current_paras:
            chunks.append('\n\n'.join(current_paras))
            current_paras, current_words = [], 0

        # Single oversized paragraph — split by sentences
        if wc > CHUNK_WORDS:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for s in sentences:
                sw = len(s.split())
                if current_words + sw > CHUNK_WORDS and current_paras:
                    chunks.append('\n\n'.join(current_paras))
                    current_paras, current_words = [], 0
                current_paras.append(s)
                current_words += sw
        else:
            current_paras.append(para)
            current_words += wc

    if current_paras:
        chunks.append('\n\n'.join(current_paras))

    return [c for c in chunks if c.strip()]


# =============================================================================
# SECTION 2 — PROMPTS
#
# Design philosophy:
# - System prompt establishes who the model is and its absolute constraints.
# - Level prompt defines WHAT the output looks like structurally.
# - Intent prompt defines WHY the user is reading and HOW to frame content.
# - Written as a skilled editor would brief a great writer, not a checklist.
# =============================================================================

SYSTEM_BASE = """\
You are an expert educational writer and adaptive learning specialist.
Your task: transform academic and technical text to perfectly match a specific \
reader's knowledge level and learning purpose.

What makes you exceptional:
1. You are a faithful steward of the source. You never distort, invent, or \
misrepresent any fact, number, name, formula, or citation. Every claim you write \
is grounded in what the input actually says.
2. You deeply understand the reader. You know exactly how much to explain, which \
analogies will land, what to emphasise, and how to structure things so they click.

Non-negotiable rules:
- Output ONLY the rewritten text. No preamble like "Here is the rewritten version:". \
No meta-commentary. Start immediately with content.
- Never invent facts. Never add claims not supported by the input.
- Never refuse or add disclaimers. Just write.\
"""


LEVEL_PROMPTS = {

    'beginner': """\
READER LEVEL: Complete beginner. Has never formally studied this subject.

Your job is to be the clearest, most patient teacher they have encountered.

CRITICAL LENGTH RULE: Your output MUST be at least TWICE the length of the input text. \
This is not optional. If you are given 500 words, you must write at least 1000 words. \
If you are given 1000 words, you must write at least 2000 words. \
Count your output. If it is shorter than 2x the input, you have not finished the task — \
keep writing, keep expanding, keep adding depth.

WHY SO LONG? Because the input text was written for experts. Every single sentence \
assumes knowledge the reader does not have. Your job is to unpack every assumption, \
define every term, and provide the context that was left out. This takes words.

HOW TO EXPAND every paragraph from the input:

Step 1 — DEFINE: Identify every technical term or field-specific phrase. \
Define each one in plain conversational English the first time it appears. \
Put the definition in parentheses immediately after the term. \
Example: "morphology (the study of how words are built from smaller parts — \
for instance, the word 'unhappiness' is built from 'un-' meaning not, 'happy', and '-ness' meaning a state of being)".

Step 2 — EXPLAIN: After each sentence from the input, add 2-3 sentences that explain \
what it means in plain language. Assume the reader understood none of the original sentence \
and needs it fully unpacked.

Step 3 — ANALOGISE: After each concept, write a concrete real-world analogy. \
Use the format: "Think of it like: [analogy using everyday objects or situations the reader knows]." \
The analogy must make the abstract concrete. Do not use weak analogies like "it's like a puzzle" — \
be specific and vivid.

Step 4 — CONTEXTUALISE: After each major idea, write a "Why this matters: [sentence explaining \
real-world significance]." This connects abstract knowledge to motivation.

Step 5 — EXAMPLES: Add a concrete example for every abstract claim. If the original text \
does not give an example, construct one from the information present in the text.

WRITING RULES:
- Maximum 20 words per sentence. Break long sentences into two.
- Replace academic vocabulary with everyday language. "Utilise" → "use". \
"Subsequently" → "then". "Demonstrate" → "show". "Facilitate" → "help".
- Never talk down to the reader. They are intelligent — just new to this.
- Write in flowing paragraphs, not bullet points. This is a reading experience, not a list.
- Every single piece of information from the input must appear in your output. \
You are EXPANDING, never summarising or cutting.\
""",

    'intermediate': """\
READER LEVEL: Intermediate. Has solid foundational knowledge, is not a specialist.

Your job: be a clear, efficient guide through the material.

OUTPUT LENGTH: Roughly the same as the input. You are clarifying and restructuring, \
not expanding or compressing.

HOW TO WRITE:

Vocabulary: Keep all technical terms — the reader benefits from precise language \
and knows the basics. Add a brief clarification only for the most specialised \
field-specific terms a general educated reader would not encounter outside this domain. \
Skip anything commonly understood.

Cutting: Remove purely rhetorical setup sentences — lines that tell you what \
the paragraph will say rather than saying it. Keep every substantive idea.

Clarity: Where the original is unnecessarily passive or convoluted, rewrite it \
to be direct. One idea per paragraph. Clear topic sentences.

Faithfulness: Preserve the author's argument and logical structure. You are \
editing for clarity, not replacing their reasoning.\
""",

    'expert': """\
READER LEVEL: Expert or working professional in this field.

Your job: produce the densest, most efficient version of this content possible.

OUTPUT LENGTH: 40-60% shorter than the input. Experts read fast and have zero \
tolerance for padding. Every word must earn its place.

HOW TO WRITE:

Cut ruthlessly: Delete all introductory framing, scene-setting, and \
"as we have seen" transitions. Delete any sentence stating something obvious \
to someone with field expertise. Delete repeated points.

Preserve with 100% accuracy: all formulas, numerical values, citations, \
named theorems or methods, experimental results, and proper nouns. \
These are exactly what experts are reading for.

Language: Use the most precise technical language available. \
Do not simplify terminology.

Structure: Bullet points are appropriate when listing properties, conditions, \
or sequential steps. Otherwise use compressed, information-dense prose.

Standard: The output should read like expertly-edited field notes. \
All signal, no noise.\
""",

}


INTENT_PROMPTS = {

    'studying': """\
READING PURPOSE: The reader is studying to understand and remember this material.

Apply these techniques:

Opening each section: Lead with a single bold sentence that states the core \
point of what follows. Format: **[The key point in one sentence.]** \
This gives the reader a frame before the detail arrives.

Examples: Ground abstract claims in concrete examples. If the original text \
implies an example but does not state one, construct one using only information \
present in the text.

Memory anchors: End each distinct topic with: \
"Key takeaway: [the single most important thing to remember about this topic]." \
This aids consolidation — the reader knows what to hold onto.

Sequences: Where the text describes a process or progression, make it \
explicitly sequential. Use "First...", "Then...", "Finally..." so the logic \
is easy to follow and reconstruct from memory.

Scannability: Bold key terms on first use. Clear paragraph breaks. \
The reader will return to this — make navigation easy.\
""",

    'applying': """\
READING PURPOSE: The reader is a practitioner — they want to USE this knowledge. \
They may be a student working on a project, or a professional applying concepts.

Apply these techniques:

Lead with action: Open each section by establishing what the concept enables \
someone to DO, not just what it is.

Practical bridges: After each concept, add: \
"In practice: [a concrete example of how this is actually applied or used, \
drawn from information in the text or its direct implications]."

Relevance filter: De-emphasise historical background and theoretical debates \
unless they directly inform how something works or is used today. \
Keep everything that answers "how do I use this?"

Procedures: If the text describes steps, methods, or procedures, make them as \
explicit and actionable as possible. Number them if they are sequential.

The reader's question: They are always asking "so what do I do with this?" \
Answer that question consistently throughout.\
""",

    'explaining': """\
READING PURPOSE: The reader wants to explain this material to someone else — \
a student, a colleague, a non-expert. They need to understand it well enough \
to make others understand it.

Apply these techniques:

Analogies first: For each major concept, lead with the best analogy you can \
construct from the material. Analogies are the core technology of explanation.

Explanation prompts: At key moments, add: \
"One way to explain this: [a 1-2 sentence explanation using an analogy or \
plain-English framing that a non-expert would immediately grasp]."

Logical scaffolding: Structure the content so each idea naturally prepares \
the reader for the next. This mirrors how you would explain something verbally — \
you build understanding brick by brick.

Counterintuition: Flag anything that is commonly misunderstood or \
counterintuitive. These are exactly the points the reader will need to handle \
when explaining to others.

Tone: A knowledgeable friend who genuinely enjoys making complex things click. \
Warm, precise, and never condescending.\
""",

    'exploring': """\
READING PURPOSE: The reader is curious and browsing — they want to understand \
the landscape of this topic, discover what is interesting, and follow their curiosity.

Apply these techniques:

Hook curiosity: Lead each section with what is surprising, non-obvious, or \
intellectually interesting about the idea before delivering the explanation. \
Make the reader want to keep going.

Intrigue markers: Add "Interestingly, ..." or \
"A surprising implication of this: ..." where the content genuinely supports it. \
Do not manufacture false excitement — only where it is real.

Connections: Where the text supports it, briefly note how an idea connects \
to broader significance or other domains of knowledge.

Prose quality: Keep writing flowing and readable. This reader enjoys good prose, \
not just information. Vary sentence structure. Let the material breathe.

Closing: End with a "What to explore next:" paragraph — 2-3 sentences \
identifying the natural questions this material raises, based only on what \
is in the document. Give the reader somewhere to go.\
""",

}


def _build_system_prompt(level: str, intent: str) -> str:
    level_p  = LEVEL_PROMPTS.get(level,  LEVEL_PROMPTS['intermediate'])
    intent_p = INTENT_PROMPTS.get(intent, INTENT_PROMPTS['studying'])
    return f"{SYSTEM_BASE}\n\n{level_p}\n\n{intent_p}"


def _build_user_message(chunk: str, chunk_num: int, total_chunks: int,
                        level: str, intent: str) -> str:
    if total_chunks > 1:
        if chunk_num == 1:
            position = "This is the opening section of the document. "
        elif chunk_num == total_chunks:
            position = "This is the final section of the document. "
        else:
            position = f"This is section {chunk_num} of {total_chunks}. "
    else:
        position = ""

    return (
        f"{position}Rewrite the following text for a {level}-level reader "
        f"in {intent} mode. Follow all instructions precisely.\n\n"
        f"<text>\n{chunk}\n</text>"
    )


# =============================================================================
# SECTION 3 — BEDROCK CALL
# =============================================================================

def _call_bedrock(system_prompt: str, user_message: str,
                  max_tokens: int = 2000, temperature: float = 0.65) -> str:
    # Nova Lite request format (different from Claude)
    body = json.dumps({
        'system': [{'text': system_prompt}],
        'messages': [{'role': 'user', 'content': [{'text': user_message}]}],
        'inferenceConfig': {'maxTokens': max_tokens, 'temperature': temperature},
    })
    resp = _get_bedrock().invoke_model(modelId=MODEL_TRANSFORM, body=body)
    return json.loads(resp['body'].read())['output']['message']['content'][0]['text'].strip()


def _call_haiku(prompt: str, max_tokens: int = 1200) -> str:
    # Haiku / Claude format (used for annotations only)
    body = json.dumps({
        'anthropic_version': 'bedrock-2023-05-31',
        'max_tokens': max_tokens,
        'temperature': 0.2,
        'messages': [{'role': 'user', 'content': prompt}],
    })
    resp = _get_bedrock().invoke_model(modelId=MODEL_ANNOTATE, body=body)
    return json.loads(resp['body'].read())['content'][0]['text'].strip()


# =============================================================================
# SECTION 4 — VALIDATION
# =============================================================================

def _valid(original: str, rewritten: str, level: str) -> bool:
    if len(rewritten.strip()) < 50:
        return False

    # Model went off-task or preambled
    bad_prefixes = [
        'I cannot', 'I apologize', 'As an AI', "I'm unable", 'I am unable',
        'Here is', "Here's the", 'The following is', 'Below is', 'I have rewritten',
        'Sure,', 'Certainly,',
    ]
    first_80 = rewritten[:80]
    if any(first_80.startswith(p) for p in bad_prefixes):
        return False

    orig_len = len(original)
    rewr_len = len(rewritten)

    # Expert must compress
    if level == 'expert' and rewr_len > orig_len * 0.92:
        return False

    # Beginner must expand — enforce 2x minimum, warn at 1.5x
    if level == 'beginner' and rewr_len < orig_len * 1.5:
        return False

    # Any level: suspiciously short means something went wrong
    if rewr_len < orig_len * 0.30:
        return False

    return True


# =============================================================================
# SECTION 5 — ANNOTATIONS
# =============================================================================

def _generate_annotations(text: str, level: str) -> list:
    sample = ' '.join(text.split()[:3500])

    depth = {
        'beginner': (
            'Write for someone with zero prior knowledge. '
            '"short" must be plain English a 16-year-old would grasp. '
            '"detail" must be two sentences using simple language and ideally a brief analogy.'
        ),
        'intermediate': (
            'Write for someone educated but not a specialist. '
            '"short" should be a crisp one-liner. '
            '"detail" should be two sentences covering what it is and how it fits this field.'
        ),
        'expert': (
            'Write for a field professional. '
            '"short" should be a precise technical definition. '
            '"detail" should cover technical nuance or field-specific context in two sentences.'
        ),
    }.get(level, '')

    prompt = (
        f"Read the document excerpt and identify the 8-10 most important technical terms, "
        f"key concepts, named methods, or significant people that appear in it.\n\n"
        f"For each produce:\n"
        f'- "term": exact phrase from the text (2-4 words max)\n'
        f'- "short": tooltip of at most 10 words\n'
        f'- "detail": exactly 2 sentences\n'
        f'- "type": one of: concept, formula, person, definition\n\n'
        f'{depth}\n\n'
        f'Return ONLY a valid JSON array. No markdown fences. No other text.\n'
        f'[{{"term":"...","short":"...","detail":"...","type":"concept"}}]\n\n'
        f'<document>\n{sample}\n</document>'
    )

    try:
        raw    = _call_haiku(prompt, max_tokens=1200)
        raw    = re.sub(r'^```(?:json)?\s*', '', raw)
        raw    = re.sub(r'\s*```$', '', raw)
        match  = re.search(r'\[.*\]', raw, re.DOTALL)
        if not match:
            logger.warning('[Transform] No JSON array in annotation response')
            return []
        parsed = json.loads(match.group(0))
        valid_types = {'concept', 'formula', 'person', 'definition'}
        return [
            {**item, 'type': item['type'] if item['type'] in valid_types else 'concept'}
            for item in parsed
            if all(k in item for k in ('term', 'short', 'detail', 'type'))
        ]
    except Exception as e:
        logger.warning(f'[Transform] Annotation generation failed: {e}')
        return []


# =============================================================================
# SECTION 6 — DYNAMODB HELPERS
# =============================================================================

def _get_profile(user_id: str, doc_id: str) -> tuple:
    try:
        resp   = _get_dynamodb().Table(TABLE).get_item(
            Key={'user_id': user_id, 'doc_id': doc_id}
        )
        item   = resp.get('Item', {})
        return item.get('level', 'intermediate'), item.get('intent', 'studying')
    except Exception as e:
        logger.warning(f'[Transform] DynamoDB read failed, using defaults: {e}')
        return 'intermediate', 'studying'


def _update_dynamo_complete(user_id, doc_id, s3_key, annotations):
    _get_dynamodb().Table(TABLE).update_item(
        Key={'user_id': user_id, 'doc_id': doc_id},
        UpdateExpression=(
            'SET transform_status = :status, s3_transformed_key = :key, '
            'annotations = :ann, updated_at = :ts'
        ),
        ExpressionAttributeValues={
            ':status': 'complete',
            ':key':    s3_key,
            ':ann':    annotations,
            ':ts':     datetime.now(timezone.utc).isoformat(),
        }
    )


def _update_dynamo_failed(user_id, doc_id, error):
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
    logger.info(f'[Transform] START  user={user_id}  file={filename}  doc={doc_id}')

    level, intent = _get_profile(user_id, doc_id)
    logger.info(f'[Transform] level={level}  intent={intent}')

    extracted_key = f'extracted/{user_id}/{filename}.txt'
    try:
        obj  = _get_s3().get_object(Bucket=BUCKET, Key=extracted_key)
        text = obj['Body'].read().decode('utf-8')
    except Exception as e:
        _update_dynamo_failed(user_id, doc_id, str(e))
        raise ValueError(
            f'Extracted text not found at s3://{BUCKET}/{extracted_key}. '
            f'Ensure OCR Lambda has finished. Error: {e}'
        )

    if not text.strip():
        _update_dynamo_failed(user_id, doc_id, 'empty extracted text')
        raise ValueError(f'Extracted text at {extracted_key} is empty.')

    logger.info(f'[Transform] {len(text.split())} words to transform')

    system_prompt = _build_system_prompt(level, intent)
    chunks        = _chunk(text)
    logger.info(f'[Transform] {len(chunks)} chunks')

    max_tok = {'beginner': 2500, 'intermediate': 1500, 'expert': 900}.get(level, 1500)

    rewritten_chunks = []
    for i, chunk in enumerate(chunks):
        logger.info(f'[Transform] chunk {i+1}/{len(chunks)} ({len(chunk.split())} words)')
        user_msg = _build_user_message(chunk, i + 1, len(chunks), level, intent)
        try:
            result = _call_bedrock(system_prompt, user_msg, max_tokens=max_tok)
            if _valid(chunk, result, level):
                rewritten_chunks.append(result)
            else:
                logger.warning(f'[Transform] chunk {i+1} failed validation — retrying')
                result2 = _call_bedrock(system_prompt, user_msg,
                                        max_tokens=max_tok, temperature=0.8)
                rewritten_chunks.append(result2 if _valid(chunk, result2, level) else chunk)
        except Exception as e:
            logger.error(f'[Transform] Bedrock error chunk {i+1}: {e} — using original')
            rewritten_chunks.append(chunk)

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

    logger.info('[Transform] Generating annotations...')
    annotations = _generate_annotations(text, level)
    logger.info(f'[Transform] {len(annotations)} annotations')

    output_key = f'outputs/{user_id}/{filename}_transformed.txt'
    try:
        _get_s3().put_object(
            Bucket=BUCKET, Key=output_key,
            Body=full_output.encode('utf-8'),
            ContentType='text/plain; charset=utf-8'
        )
    except Exception as e:
        _update_dynamo_failed(user_id, doc_id, f'S3 write failed: {e}')
        raise RuntimeError(f'Failed to save output to S3: {e}')

    _update_dynamo_complete(user_id, doc_id, output_key, annotations)
    logger.info(f'[Transform] DONE → s3://{BUCKET}/{output_key}')

    return {
        's3_key':      output_key,
        'level':       level,
        'intent':      intent,
        'annotations': annotations,
    }