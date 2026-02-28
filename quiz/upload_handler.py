# =============================================================================
# quiz/upload_handler.py
# WHO WRITES THIS: Person D
# WHAT THIS IS: Lambda that receives a PDF from the frontend and saves it to S3
# =============================================================================
#
# HOW THE FRONTEND CALLS THIS:
#   POST https://<UPLOAD_LAMBDA_URL>?filename=myfile.pdf
#   Body: base64-encoded PDF bytes
#   Response: { "message": "uploaded", "filename": "myfile.pdf" }
#
# HOW TO DEPLOY: Person A creates Lambda 'akte-upload' and pastes this file.
#
# =============================================================================

import boto3
import base64
import json

s3     = boto3.client('s3')
BUCKET = 'akte-bucket'
CORS   = {'Access-Control-Allow-Origin': '*'}


def lambda_handler(event, context):
    """
    HOW TO IMPLEMENT:

      # Get filename from the URL query string (?filename=myfile.pdf)
      params   = event.get('queryStringParameters') or {}
      filename = params.get('filename', 'upload.pdf')

      # Return error if no file body
      if not event.get('body'):
          return {'statusCode': 400, 'headers': CORS,
                  'body': json.dumps({'error': 'no file in request'})}

      # Decode the base64 body back to raw bytes
      try:
          data = base64.b64decode(event['body'])
      except Exception as e:
          return {'statusCode': 400, 'headers': CORS,
                  'body': json.dumps({'error': str(e)})}

      # Reject files over 5MB
      if len(data) > 5 * 1024 * 1024:
          return {'statusCode': 413, 'headers': CORS,
                  'body': json.dumps({'error': 'File too large. Maximum size is 5MB.'})}

      # Save to S3
      s3.put_object(Bucket=BUCKET, Key=f'uploads/{filename}',
                    Body=data, ContentType='application/pdf')

      return {'statusCode': 200, 'headers': CORS,
              'body': json.dumps({'message': 'uploaded', 'filename': filename})}
    """
    # TODO: implement this
    pass
