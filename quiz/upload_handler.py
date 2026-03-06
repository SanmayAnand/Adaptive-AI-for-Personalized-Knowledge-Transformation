# upload_handler.py — Person D owns this
# Deployed as Lambda: akte-upload
#
# STATUS: complete and syntax-verified — awaiting AWS infrastructure from Person A
# DEPENDS ON:
#   - S3 bucket        : akte-bucket (Person A)
#   - akte-lambda-role : assigned at deploy time (Person A)
#   - S3 trigger       : Person A configures S3 to invoke Person B's Lambda
#                        automatically when a file lands in uploads/
#   - No Lambda layers : no external dependencies
#
# ── Security notes ────────────────────────────────────────────────────────────
#
# NO API KEYS IN THIS FILE
#   boto3 uses the Lambda execution role (akte-lambda-role) for credentials.
#   Credentials never appear in code or in any response payload.
#   The pre-signed URL contains a signature but never the underlying key.
#
# WHITELIST SANITISATION (not blacklist)
#   Filename characters are whitelisted to ASCII alphanumeric, underscore,
#   hyphen, and dot only. Anything outside this set is stripped.
#   Whitelist is stronger than blacklist — we define exactly what is allowed
#   rather than trying to enumerate every forbidden character.
#
# NO CLIENT-SIDE AWS KEYS
#   Frontend calls this Lambda to get a pre-signed URL.
#   Frontend then PUTs the file directly to S3 using that URL.
#   No AWS SDK, no AWS keys, no credentials ever reach the frontend.
#   Tell the frontend person: never import AWS SDK in React,
#   never put any AWS key in JavaScript code.
#
# ACCEPTED FILE TYPES
#   .pdf  — digital and scanned PDFs
#   .docx — Microsoft Word documents
#   Person B handles text extraction for both formats.
#   Person B must save extracted text to extracted/{user_id}/{filename}.txt
#   regardless of source format — quiz_handler reads that .txt file always.
#
# RATE LIMITING
#   API Gateway default: 10,000 requests/second (sufficient for hackathon)
#   Lambda default concurrency: 1,000 simultaneous executions
#   Bedrock cost protection: quiz_handler enforces per-user rate limit on
#   the expensive generate action. Upload itself is cheap — no extra limit needed.
#
# ── What this file does ───────────────────────────────────────────────────────
#
# Generates a pre-signed S3 URL so the frontend uploads a file directly
# to S3 without routing the bytes through Lambda.
#
# WHY pre-signed URL instead of base64 through Lambda:
#   - API Gateway has a hard 10MB payload limit
#   - Base64 encoding inflates file size ~33%
#   - Any file over ~7.5MB would be silently rejected via base64
#   - Pre-signed URL bypasses Lambda for the actual file transfer
#   - No size limit — file goes straight from browser to S3
#
# ── Frontend flow ─────────────────────────────────────────────────────────────
#
# Step 1 — call this Lambda:
#   POST { "user_id": "abc123", "filename": "biology notes.pdf" }
#   Response: {
#     "upload_url": "https://akte-bucket.s3.amazonaws.com/...?sig=...",
#     "filename":   "biology_notes.pdf",   ← sanitised — USE THIS in all future calls
#     "s3_key":     "uploads/abc123/biology_notes.pdf",
#     "expires_in": 300
#   }
#
# Step 2 — PUT raw file bytes directly to S3:
#   PUT <upload_url>
#   Headers: { "Content-Type": "application/pdf" }  or "application/vnd.openxmlformats..."
#   Body: raw file bytes — NOT base64
#   Wait for HTTP 200 from S3 before proceeding.
#
# Step 3 — S3 trigger fires (Person A configured this):
#   Person B's Lambda invoked automatically on upload.
#   Person B extracts text, saves to extracted/{user_id}/{filename}.txt
#
# Step 4 — poll quiz_handler action='check_ready' every 3-5 seconds:
#   Returns { ready: false } while Person B is processing.
#   Returns { ready: true, doc_id: "..." } when done.
#
# ── S3 path structure ─────────────────────────────────────────────────────────
#   uploads/{user_id}/{filename}           ← this handler writes here
#   extracted/{user_id}/{filename}.txt     ← Person B writes here
#   outputs/{user_id}/{filename}_transformed.txt ← Person C writes here

import boto3
import json
import re
import os

# ── AWS client ────────────────────────────────────────────────────────────────
s3 = boto3.client('s3', region_name='us-east-1')

# ── Constants ─────────────────────────────────────────────────────────────────
BUCKET           = 'akte-bucket'
CORS             = {'Access-Control-Allow-Origin': '*'}
URL_EXPIRY_SECS  = 300    # pre-signed URL valid for 5 minutes
MAX_FILENAME_LEN = 100    # base name cap before extension

# ── Accepted file types ───────────────────────────────────────────────────────
# Maps allowed extension → S3 ContentType
# To add a new type: add the extension and its MIME type here.
# Person B must also support the new format in their extraction logic.
ALLOWED_EXTENSIONS = {
    '.pdf':  'application/pdf',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}

# ── Whitelist: exactly which ASCII characters are allowed in a filename ────────
# Allowed: a-z  A-Z  0-9  underscore  hyphen  dot
# Everything else is stripped during sanitisation.
# Using explicit ASCII ranges — no unicode word characters (\w includes
# letters from all languages which could cause issues on some systems).
FILENAME_WHITELIST = re.compile(r'[^a-zA-Z0-9_\-\.]')


# ── Helper: Sanitise filename (whitelist approach) ────────────────────────────
def _sanitise_filename(filename):
    """
    Cleans the filename before using it as an S3 key.

    WHY WHITELIST NOT BLACKLIST:
      Blacklisting tries to enumerate every forbidden character — you will
      always miss something. Whitelisting defines exactly what IS allowed
      and strips everything else. Safer by design.

    Allowed characters (explicit ASCII whitelist):
      a-z  A-Z  0-9  _ (underscore)  - (hyphen)  . (dot)
      No unicode, no spaces, no special characters, no path separators.

    Steps:
      1. Reject if empty
      2. Strip leading/trailing whitespace
      3. Replace spaces with underscores (common case — do before stripping)
      4. Apply whitelist — strip any character not in [a-zA-Z0-9_\\-\\.]
      5. Check extension is in ALLOWED_EXTENSIONS
      6. Verify base name has at least 2 characters after sanitisation
      7. Cap base name at MAX_FILENAME_LEN characters

    Returns sanitised filename string.
    Raises ValueError with user-facing message on any failure.

    The sanitised filename is returned to the frontend in the response.
    Frontend MUST use this sanitised version in all subsequent calls —
    not the original raw filename the user typed.
    """
    if not filename or not isinstance(filename, str):
        raise ValueError("Filename cannot be empty")

    name = filename.strip()

    if not name:
        raise ValueError("Filename cannot be empty")

    # Replace spaces with underscores before whitelisting
    name = name.replace(' ', '_')

    # Apply whitelist — strip everything not in [a-zA-Z0-9_\-\.]
    name = FILENAME_WHITELIST.sub('', name)

    # Split into base and extension for individual checks
    base, ext = os.path.splitext(name)

    # Extension must be in our allowed set
    if ext.lower() not in ALLOWED_EXTENSIONS:
        allowed = ', '.join(ALLOWED_EXTENSIONS.keys())
        raise ValueError(f"Only {allowed} files are accepted")

    # os.path.splitext('.pdf') returns ('.pdf', '') — catch files with no real base
    # base must have at least 2 meaningful characters
    if len(base) < 2:
        raise ValueError("Filename is too short — please rename your file")

    # Cap base name length — preserve extension
    if len(base) > MAX_FILENAME_LEN:
        base = base[:MAX_FILENAME_LEN]
        name = base + ext

    return name


# ── Helper: Validate user_id ──────────────────────────────────────────────────
def _validate_user_id(user_id):
    """
    Validates user_id before embedding it in an S3 key or DynamoDB key.

    user_id is generated client-side as a UUID (random alphanumeric string).
    We apply a strict whitelist — only alphanumeric characters and hyphens.
    This matches standard UUID format and prevents any path traversal.

    Rules:
      - Non-empty string
      - Whitelist: only [a-zA-Z0-9-]
      - Max 64 characters

    Raises ValueError if invalid.
    """
    if not user_id or not isinstance(user_id, str):
        raise ValueError("user_id must be a non-empty string")

    user_id = user_id.strip()

    # Strict whitelist — only UUID-safe characters
    if not re.match(r'^[a-zA-Z0-9\-]{1,64}$', user_id):
        raise ValueError("user_id contains invalid characters")

    return user_id


# ── Helper: Generate pre-signed upload URL ────────────────────────────────────
def _generate_upload_url(user_id, filename):
    """
    Generates a pre-signed S3 PUT URL for the given user and filename.

    What a pre-signed URL is:
      A normal S3 URL with a time-limited cryptographic signature embedded
      as query parameters. Proves to S3 that the Lambda role authorised
      this specific PUT to this specific key within this time window.
      After URL_EXPIRY_SECS the signature is rejected.
      The underlying AWS credentials are NEVER included or exposed.

    ContentType is set per file extension from ALLOWED_EXTENSIONS.
    The frontend must send the matching Content-Type header on the PUT.

    Returns: (presigned_url: str, s3_key: str, content_type: str)
    """
    _, ext        = os.path.splitext(filename)
    content_type  = ALLOWED_EXTENSIONS[ext.lower()]
    s3_key        = f'uploads/{user_id}/{filename}'

    presigned_url = s3.generate_presigned_url(
        ClientMethod='put_object',
        Params={
            'Bucket':      BUCKET,
            'Key':         s3_key,
            'ContentType': content_type
        },
        ExpiresIn=URL_EXPIRY_SECS
    )

    return presigned_url, s3_key, content_type


# ── Lambda entry point ────────────────────────────────────────────────────────
def lambda_handler(event, context):
    """
    Request:
      POST { "user_id": "abc123", "filename": "biology notes.pdf" }
      POST { "user_id": "abc123", "filename": "lecture notes.docx" }

    Success response (200):
      {
        "upload_url":   "https://akte-bucket.s3.amazonaws.com/uploads/abc123/biology_notes.pdf?...",
        "filename":     "biology_notes.pdf",   ← sanitised — use this in all future calls
        "s3_key":       "uploads/abc123/biology_notes.pdf",
        "content_type": "application/pdf",     ← use as Content-Type header on the PUT
        "expires_in":   300
      }

    Frontend must:
      1. PUT raw file bytes to upload_url
         Header: Content-Type must match the content_type field returned here
      2. Wait for HTTP 200 from S3
      3. Poll quiz_handler action='check_ready' until { ready: true }
      4. Use the sanitised filename (not the original) in all subsequent calls

    Error responses:
      400 — missing fields / invalid user_id / unsupported file type / bad filename
      500 — S3 error or unexpected failure
    """
    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': CORS,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }

    raw_user_id  = body.get('user_id')
    raw_filename = body.get('filename')

    if not raw_user_id or not raw_filename:
        return {
            'statusCode': 400,
            'headers': CORS,
            'body': json.dumps({'error': "'user_id' and 'filename' are both required"})
        }

    try:
        user_id  = _validate_user_id(raw_user_id)
        filename = _sanitise_filename(raw_filename)
    except ValueError as e:
        return {
            'statusCode': 400,
            'headers': CORS,
            'body': json.dumps({'error': str(e)})
        }

    try:
        upload_url, s3_key, content_type = _generate_upload_url(user_id, filename)
        return {
            'statusCode': 200,
            'headers': CORS,
            'body': json.dumps({
                'upload_url':   upload_url,
                'filename':     filename,      # sanitised — frontend uses this everywhere
                's3_key':       s3_key,
                'content_type': content_type,  # frontend uses this as Content-Type on PUT
                'expires_in':   URL_EXPIRY_SECS
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': CORS,
            'body': json.dumps({'error': str(e)})
        }