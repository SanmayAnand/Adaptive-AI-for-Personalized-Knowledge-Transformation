# upload_handler.py — Person D owns this
# Lambda: akte-upload
#
# Purpose: Receive a PDF from the React frontend and store it in S3 at uploads/{filename}
#
# How it's called:
#   POST https://<UPLOAD_LAMBDA_URL>?filename=myfile.pdf
#   Body: base64-encoded PDF bytes (sent by the FileReader in api.js)
#
# What it does:
#   1. Read filename from queryStringParameters (default: 'upload.pdf')
#   2. If no body → return 400 {'error': 'no file'}
#   3. base64.b64decode(event['body']) to get raw bytes
#   4. If decoded size > 5MB → return 413 {'error': 'Max 5MB'}
#   5. s3.put_object(Bucket=BUCKET, Key=f'uploads/{filename}', Body=data, ContentType='application/pdf')
#   6. Return 200 {'message': 'uploaded', 'filename': filename}
#
# Every response must include CORS header: {'Access-Control-Allow-Origin': '*'}
#
# Constants:
#   BUCKET = 'akte-bucket'
#
# Lambda settings:
#   Runtime: Python 3.11 | Memory: 512MB | Timeout: 60s | Role: akte-lambda-role
#   Function URL: Auth NONE | CORS enabled
#   No extra layers needed
#
# Full working code is in the blueprint document (Section: PERSON D, "Deliverable 2 — upload_handler.py").

import boto3
import base64
import json

s3 = boto3.client('s3')
BUCKET = 'akte-bucket'


def lambda_handler(event, context):
    # TODO: implement as described above
    raise NotImplementedError
