import boto3
import json
import os
import logging
import transform  # Person C

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3     = boto3.client('s3', region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
BUCKET = os.environ.get('BUCKET_NAME', 'ocr-ai-for-bharat1')  # reads from Lambda env var
CORS   = {
    'Access-Control-Allow-Origin':  '*',
    'Access-Control-Allow-Headers': 'content-type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
}


def lambda_handler(event, context):
    # ── CORS preflight ─────────────────────────────────────────────────────────
    method = event.get('requestContext', {}).get('http', {}).get('method', '')
    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS, 'body': ''}

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
        result = transform.run(user_id, filename, doc_id)
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
        return {'statusCode': 422, 'headers': CORS, 'body': json.dumps({'error': str(e)})}
    except Exception as e:
        logger.error(f'[Main] Unhandled error: {e}')
        return {'statusCode': 500, 'headers': CORS, 'body': json.dumps({'error': str(e)})}