# ocr/ocr_lambda.py
# NEW FILE — create this in your ocr/ folder
#
# This is the S3-triggered Lambda.
# Triggered automatically when a file lands in uploads/{user_id}/{filename}
# Calls ocr.extract_text(), saves result to extracted/{user_id}/{filename}.txt
#
# Person A deploys this as Lambda: akte-ocr
# Person A sets S3 trigger: bucket=ocr-ai-for-bharat1, prefix=uploads/, event=ObjectCreated

import boto3
import os
import logging
from urllib.parse import unquote_plus
from ocr import extract_text

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3     = boto3.client('s3', region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
BUCKET = os.environ.get('BUCKET_NAME', 'akte-bucket')


def lambda_handler(event, context):
    """
    S3 PUT trigger. Called automatically when a file lands in uploads/.
    event['Records'][0]['s3']['object']['key'] = 'uploads/user_id/filename.pdf'
    """
    for record in event.get('Records', []):
        s3_key = unquote_plus(record['s3']['object']['key'])
        logger.info(f'[OCR Lambda] triggered for: {s3_key}')

        # Parse: uploads/{user_id}/{filename}
        parts = s3_key.split('/')
        if len(parts) < 3 or parts[0] != 'uploads':
            logger.warning(f'[OCR Lambda] unexpected key format: {s3_key}')
            continue

        user_id  = parts[1]
        filename = '/'.join(parts[2:])
        output_key = f'extracted/{user_id}/{filename}.txt'

        try:
            text = extract_text(BUCKET, s3_key)
            logger.info(f'[OCR Lambda] extracted {len(text)} chars from {s3_key}')

            s3.put_object(
                Bucket=BUCKET,
                Key=output_key,
                Body=text.encode('utf-8'),
                ContentType='text/plain; charset=utf-8'
            )
            logger.info(f'[OCR Lambda] saved to s3://{BUCKET}/{output_key}')

        except Exception as e:
            logger.error(f'[OCR Lambda] failed for {s3_key}: {e}')
            # Write empty marker so check_ready doesn't poll forever
            # quiz_handler will detect empty and return 422
            try:
                s3.put_object(Bucket=BUCKET, Key=output_key,
                              Body=b'', ContentType='text/plain')
            except Exception:
                pass