# =============================================================================
# main_handler.py  —  root of repo, Person A deploys this as akte-main Lambda
#
# HOW TO DEPLOY (Person A does this):
#   1. Put these files in one folder:
#        main_handler.py   ← this file
#        transform.py      ← Person C
#        ocr.py            ← Person B
#   2. zip -r akte_main.zip main_handler.py transform.py ocr.py
#   3. Upload zip to akte-main Lambda
#   4. Add pdfplumber Lambda Layer to akte-main
#   5. Set Lambda env var: BUCKET_NAME = akte-bucket (or ocr-ai-for-bharat1)
#
# CALLED BY:
#   React frontend — after quiz is complete and user clicks "Transform"
#
# REQUEST BODY:
#   { "user_id": "abc123", "filename": "biology_notes.pdf", "doc_id": "abc123#biology_notes.pdf#20250301120000" }
#
# RESPONSE (200):
#   { "download_url": "...", "level": "...", "intent": "...", "annotations": [...] }
# =============================================================================

import boto3
import json
import os
import logging
import ocr        # Person B — extract_text(bucket, key) -> str
import transform  # Person C — run(user_id, filename, doc_id) -> dict

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3     = boto3.client('s3', region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
BUCKET = os.environ.get('BUCKET_NAME', 'akte-bucket')
CORS   = {'Access-Control-Allow-Origin': '*'}


def lambda_handler(event, context):
    try:
        body     = json.loads(event.get('body', '{}'))
        user_id  = body.get('user_id')
        filename = body.get('filename')
        doc_id   = body.get('doc_id')
    except Exception:
        return {'statusCode': 400, 'headers': CORS,
                'body': json.dumps({'error': 'Invalid JSON'})}

    if not all([user_id, filename, doc_id]):
        return {'statusCode': 400, 'headers': CORS,
                'body': json.dumps({'error': 'user_id, filename, doc_id all required'})}

    try:
        # Person C's transform.run() handles everything:
        # reads extracted text, reads level+intent from DDB,
        # rewrites, generates annotations, saves to S3, updates DDB.
        result = transform.run(user_id, filename, doc_id)

        # Pre-signed URL valid 2 hours — enough for the user to download
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET, 'Key': result['s3_key']},
            ExpiresIn=7200
        )

        return {
            'statusCode': 200,
            'headers': CORS,
            'body': json.dumps({
                'download_url': url,
                'level':        result['level'],
                'intent':       result['intent'],
                'annotations':  result['annotations'],
                's3_key':       result['s3_key'],
            })
        }

    except ValueError as e:
        return {'statusCode': 422, 'headers': CORS,
                'body': json.dumps({'error': str(e)})}
    except Exception as e:
        logger.error(f'[Main] Unhandled error: {e}')
        return {'statusCode': 500, 'headers': CORS,
                'body': json.dumps({'error': str(e)})}