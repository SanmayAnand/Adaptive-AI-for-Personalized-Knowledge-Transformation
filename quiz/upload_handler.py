import boto3
import json
import re
import os

# ── AWS client ────────────────────────────────────────────────────────────────
s3 = boto3.client('s3', region_name='us-east-1')

# ── Constants ─────────────────────────────────────────────────────────────────
BUCKET           = os.environ.get('BUCKET_NAME', 'ocr-ai-for-bharat1')  # reads from Lambda env var
CORS             = {
    'Access-Control-Allow-Origin':  '*',
    'Access-Control-Allow-Headers': 'content-type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
}
URL_EXPIRY_SECS  = 300
MAX_FILENAME_LEN = 100

ALLOWED_EXTENSIONS = {
    '.pdf':  'application/pdf',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}

FILENAME_WHITELIST = re.compile(r'[^a-zA-Z0-9_\-\.]')


def _sanitise_filename(filename):
    if not filename or not isinstance(filename, str):
        raise ValueError("Filename cannot be empty")
    name = filename.strip().replace(' ', '_')
    name = FILENAME_WHITELIST.sub('', name)
    base, ext = os.path.splitext(name)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        allowed = ', '.join(ALLOWED_EXTENSIONS.keys())
        raise ValueError(f"Only {allowed} files are accepted")
    if len(base) < 2:
        raise ValueError("Filename is too short — please rename your file")
    if len(base) > MAX_FILENAME_LEN:
        base = base[:MAX_FILENAME_LEN]
        name = base + ext
    return name


def _validate_user_id(user_id):
    if not user_id or not isinstance(user_id, str):
        raise ValueError("user_id must be a non-empty string")
    if not re.match(r'^[a-zA-Z0-9\-]{1,64}$', user_id.strip()):
        raise ValueError("user_id contains invalid characters")
    return user_id.strip()


def _generate_upload_url(user_id, filename):
    _, ext        = os.path.splitext(filename)
    content_type  = ALLOWED_EXTENSIONS[ext.lower()]
    s3_key        = f'uploads/{user_id}/{filename}'
    presigned_url = s3.generate_presigned_url(
        ClientMethod='put_object',
        Params={'Bucket': BUCKET, 'Key': s3_key, 'ContentType': content_type},
        ExpiresIn=URL_EXPIRY_SECS
    )
    return presigned_url, s3_key, content_type


def lambda_handler(event, context):
    # ── CORS preflight ────────────────────────────────────────────────────────
    method = event.get('requestContext', {}).get('http', {}).get('method', '')
    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS, 'body': ''}

    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        return {'statusCode': 400, 'headers': CORS,
                'body': json.dumps({'error': 'Invalid JSON in request body'})}

    raw_user_id  = body.get('user_id')
    raw_filename = body.get('filename')

    if not raw_user_id or not raw_filename:
        return {'statusCode': 400, 'headers': CORS,
                'body': json.dumps({'error': "'user_id' and 'filename' are both required"})}

    try:
        user_id  = _validate_user_id(raw_user_id)
        filename = _sanitise_filename(raw_filename)
    except ValueError as e:
        return {'statusCode': 400, 'headers': CORS, 'body': json.dumps({'error': str(e)})}

    try:
        upload_url, s3_key, content_type = _generate_upload_url(user_id, filename)
        return {
            'statusCode': 200,
            'headers': CORS,
            'body': json.dumps({
                'upload_url':   upload_url,
                'filename':     filename,
                's3_key':       s3_key,
                'content_type': content_type,
                'expires_in':   URL_EXPIRY_SECS
            })
        }
    except Exception as e:
        return {'statusCode': 500, 'headers': CORS, 'body': json.dumps({'error': str(e)})}