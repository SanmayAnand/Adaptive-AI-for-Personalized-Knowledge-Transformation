# main_handler.py — Person A writes this
# Lambda: akte-main
# Triggered by: frontend calling this Lambda's Function URL with POST body: { user_id, filename }
#
# What it does (in order):
#   1. Read user_id from request body
#   2. Look up user's level (beginner/intermediate/expert) from DynamoDB (set by Person D's quiz)
#   3. Call ocr.extract_text(bucket, key) — Person B's module — to get clean text from the PDF
#   4. Call transform.rewrite(text, level) — Person C's module — to get the rewritten document
#   5. Save rewritten text to S3 at outputs/{user_id}_{filename}.txt
#   6. Generate a pre-signed S3 URL (expires in 1 hour) and return it to the frontend
#
# Returns JSON: { download_url: "https://..." }
# On error returns: { error: "..." } with appropriate statusCode
#
# Key constants (must match Person A's infrastructure):
#   BUCKET = 'akte-bucket'
#   TABLE  = 'akte-users'
#
# Helper functions to implement:
#   _get_level(user_id) -> str
#     - DynamoDB get_item on TABLE with Key={'user_id': user_id}
#     - Return item['level'] if found, else default to 'intermediate'
#     - Wrap in try/except — always return a valid level string, never crash
#
#   _save_output(user_id, filename, text) -> presigned_url str
#     - s3.put_object to 'outputs/{user_id}_{filename}.txt', encoded as utf-8
#     - s3.generate_presigned_url for get_object, ExpiresIn=3600
#     - Return the URL string
#
#   lambda_handler(event, context)
#     - Parse body from event['body'] (JSON string)
#     - Extract user_id and filename; return 400 if filename missing
#     - Always include CORS header: {'Access-Control-Allow-Origin': '*'}
#     - Call the 4 steps above, return {'statusCode': 200, 'body': json.dumps({'download_url': url})}
#
# IMPORTANT: Do NOT put AWS keys in this file. The Lambda uses akte-lambda-role automatically.
#
# Full working code is in the blueprint document (Section: PERSON A, "main_handler.py — your code to write").
# Copy it exactly, then test with: curl -X POST <FUNCTION_URL> -H 'Content-Type: application/json' \
#   -d '{"user_id":"u1","filename":"test.pdf"}'

import json
import boto3
import ocr        # Person B's module — must be in same zip
import transform  # Person C's module — must be in same zip

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

BUCKET = 'akte-bucket'
TABLE = 'akte-users'


def _get_level(user_id):
    # TODO: implement as described above
    raise NotImplementedError


def _save_output(user_id, filename, text):
    # TODO: implement as described above
    raise NotImplementedError


def lambda_handler(event, context):
    # TODO: implement as described above
    raise NotImplementedError
