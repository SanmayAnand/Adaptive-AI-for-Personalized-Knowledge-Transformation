# =============================================================================
# main_handler.py
# WHO WRITES THIS: Person A
# WHAT THIS IS: The main Lambda function (akte-main) that runs the full pipeline
# =============================================================================
#
# WHAT THIS FILE DOES:
#   When the user clicks "Transform Document" on the website, the frontend
#   calls this Lambda. This file does 4 things in order:
#     1. Looks up the user's level (beginner/intermediate/expert) from DynamoDB
#     2. Calls ocr.extract_text() to read the PDF and get clean text
#     3. Calls transform.rewrite() to rewrite that text for the user's level
#     4. Saves the result to S3 and returns a download link to the frontend
#
# HOW THE FRONTEND CALLS THIS:
#   POST request to this Lambda's URL
#   Body (JSON): { "user_id": "user_abc123", "filename": "myfile.pdf" }
#   Response:    { "download_url": "https://s3.presigned.url..." }
#
# HOW TO DEPLOY (Person A does this on Day 2):
#   1. Make sure you have ocr.py (from Person B) and transform.py (from Person C)
#   2. Zip all 3 files together: main_handler.py + ocr.py + transform.py
#      Command: zip akte_main.zip main_handler.py ocr.py transform.py
#   3. Go to AWS Lambda → akte-main → Code → Upload .zip → Deploy
#   4. Add the pdfplumber Lambda Layer to this function (Person B needs it)
#
# AWS PERMISSIONS NEEDED (already set if you created akte-lambda-role correctly):
#   S3: GetObject, PutObject, GetPresignedUrl
#   DynamoDB: GetItem
#
# =============================================================================

import json
import boto3

# Import Person B's and Person C's modules
# These files must be in the same zip when deployed
import ocr        # from ocr/ocr.py
import transform  # from transform/transform.py

s3       = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

BUCKET = 'akte-bucket'   # must match the S3 bucket Person A created
TABLE  = 'akte-users'    # must match the DynamoDB table Person A created


def _get_user_level(user_id):
    """
    Look up the user's level from DynamoDB.
    Returns 'beginner', 'intermediate', or 'expert'.
    If the user isn't found (they skipped the quiz), default to 'intermediate'.

    HOW TO IMPLEMENT:
      response = dynamodb.Table(TABLE).get_item(Key={'user_id': user_id})
      return response.get('Item', {}).get('level', 'intermediate')
      Wrap in try/except — always return a string, never crash.
    """
    # TODO: implement this
    pass


def _save_and_get_link(user_id, filename, text):
    """
    Save the rewritten text to S3 and return a pre-signed download URL.

    WHERE IT SAVES: s3://akte-bucket/outputs/{user_id}_{filename}.txt
    WHAT IT RETURNS: a pre-signed URL string (expires in 1 hour)

    HOW TO IMPLEMENT:
      key = f'outputs/{user_id}_{filename}.txt'
      s3.put_object(Bucket=BUCKET, Key=key, Body=text.encode('utf-8'))
      url = s3.generate_presigned_url('get_object',
                Params={'Bucket': BUCKET, 'Key': key},
                ExpiresIn=3600)
      return url
    """
    # TODO: implement this
    pass


def lambda_handler(event, context):
    """
    Entry point. AWS calls this function when the Lambda is triggered.

    HOW TO IMPLEMENT:
      1. Parse the body:
           body = json.loads(event.get('body', '{}'))
           user_id  = body.get('user_id', 'guest')
           filename = body.get('filename', '')

      2. If filename is empty, return a 400 error:
           return {
             'statusCode': 400,
             'headers': {'Access-Control-Allow-Origin': '*'},
             'body': json.dumps({'error': 'filename is required'})
           }

      3. Get user level:
           level = _get_user_level(user_id)

      4. Extract text from PDF (calls Person B's code):
           text = ocr.extract_text(BUCKET, f'uploads/{filename}')

      5. Rewrite text for user's level (calls Person C's code):
           rewritten = transform.rewrite(text, level)

      6. Save and get download link:
           download_url = _save_and_get_link(user_id, filename, rewritten)

      7. Return success:
           return {
             'statusCode': 200,
             'headers': {'Access-Control-Allow-Origin': '*'},
             'body': json.dumps({'download_url': download_url})
           }

      Wrap steps 3-6 in try/except and return a 500 error if anything fails.
    """
    # TODO: implement this
    pass
