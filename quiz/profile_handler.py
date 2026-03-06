# profile_handler.py — Person D owns this
# Deployed as Lambda: akte-profile
#
# STATUS: complete and syntax-verified — awaiting AWS infrastructure from Person A
# DEPENDS ON:
#   - DynamoDB table : akte-users, partition key=user_id, sort key=doc_id (Person A)
#   - Lambda role    : needs dynamodb:Query, dynamodb:UpdateItem on akte-users
#   - No S3 access   : this file never touches S3
#   - No Bedrock     : this file never calls Bedrock
#
# ── Security notes ────────────────────────────────────────────────────────────
#
# NO API KEYS IN THIS FILE
#   boto3 uses the Lambda execution role for credentials.
#
# user_id and doc_id are validated against strict whitelists before
# being used in any DynamoDB call.
#
# NEVER uses put_item — always update_item.
#   put_item would wipe the entire row including quiz results, score,
#   intent, and extraction data. update_item touches only the fields
#   we specify. This is the same contract Person C follows.
#
# ── What this file does ───────────────────────────────────────────────────────
#
# Two actions:
#
#   action='get_level'
#     Returns the current level for a specific document session.
#     Used by the Level Result screen to display the current level
#     before the user decides whether to override it.
#
#   action='set_level'
#     Overrides the level for a specific document session.
#     Used when the user taps "I'm actually intermediate" on the
#     Level Result screen. Writes to DynamoDB using update_item —
#     only the level and updated_at fields are touched.
#
# ── Why doc_id is required (not just user_id) ─────────────────────────────────
#
#   akte-users has a composite key: user_id (partition) + doc_id (sort).
#   A user can have many documents, each with their own level.
#   You cannot get_item or update_item with user_id alone — DynamoDB
#   requires both keys. The doc_id was returned by quiz_handler's
#   check_ready action and should be stored by the frontend.
#
# ── DynamoDB operation used ───────────────────────────────────────────────────
#   get_level : table.get_item  (read one specific row)
#   set_level : table.update_item (patch level + updated_at only)
#
# ── Frontend contract ─────────────────────────────────────────────────────────
#
#   GET level:
#     Request:  { "action": "get_level", "user_id": "abc123",
#                 "doc_id": "abc123#biology.pdf#20260306120000" }
#     Response: { "user_id": "abc123",
#                 "doc_id":  "abc123#biology.pdf#20260306120000",
#                 "level":   "intermediate",
#                 "filename": "biology.pdf" }
#
#   SET level (manual override):
#     Request:  { "action": "set_level", "user_id": "abc123",
#                 "doc_id": "abc123#biology.pdf#20260306120000",
#                 "level":  "beginner" }
#     Response: { "user_id": "abc123",
#                 "doc_id":  "abc123#biology.pdf#20260306120000",
#                 "level":   "beginner",
#                 "updated_at": "2026-03-06T12:05:00+00:00" }

import boto3
import json
import re
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Key

# ── AWS client ─────────────────────────────────────────────────────────────────
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

# ── Constants ──────────────────────────────────────────────────────────────────
TABLE          = 'akte-users'
CORS           = {'Access-Control-Allow-Origin': '*'}
VALID_LEVELS   = {'beginner', 'intermediate', 'expert'}

# ── Input validation ───────────────────────────────────────────────────────────
def _validate_user_id(user_id):
    """
    Whitelist: alphanumeric and hyphens only, max 64 chars.
    Matches UUID format. Prevents path traversal or injection.
    """
    if not user_id or not isinstance(user_id, str):
        raise ValueError("user_id must be a non-empty string")
    if not re.match(r'^[a-zA-Z0-9\-]{1,64}$', user_id.strip()):
        raise ValueError("user_id contains invalid characters")
    return user_id.strip()


def _validate_doc_id(doc_id):
    """
    doc_id format: {user_id}#{filename}#{timestamp}
    Whitelist: alphanumeric, hyphens, underscores, dots, and exactly two # separators.
    Must have 3 parts when split on #.
    """
    if not doc_id or not isinstance(doc_id, str):
        raise ValueError("doc_id must be a non-empty string")
    doc_id = doc_id.strip()
    # Allow alphanumeric, hyphen, underscore, dot, hash — and nothing else
    if not re.match(r'^[a-zA-Z0-9\-_\.#]{1,256}$', doc_id):
        raise ValueError("doc_id contains invalid characters")
    parts = doc_id.split('#')
    if len(parts) != 3:
        raise ValueError("doc_id format invalid — expected user_id#filename#timestamp")
    return doc_id


# ── Helper: get level for one document session ─────────────────────────────────
def _get_level(user_id, doc_id):
    """
    Reads a single DynamoDB row by composite key (user_id + doc_id).
    Returns a safe subset of fields — never leaks internal S3 paths,
    self_answers, or extraction metadata to the frontend.

    Raises KeyError if the item does not exist.
    """
    table    = dynamodb.Table(TABLE)
    response = table.get_item(Key={'user_id': user_id, 'doc_id': doc_id})
    item     = response.get('Item')

    if not item:
        raise KeyError(f"No document found for doc_id '{doc_id}'")

    # Return only what the frontend needs — never leak internal fields
    return {
        'user_id':    item.get('user_id'),
        'doc_id':     item.get('doc_id'),
        'level':      item.get('level', 'beginner'),
        'filename':   item.get('filename', ''),
        'quiz_score': item.get('quiz_score'),
        'created_at': item.get('created_at'),
    }


# ── Helper: override level for one document session ────────────────────────────
def _set_level(user_id, doc_id, level):
    """
    Updates ONLY the level and updated_at fields on an existing DynamoDB row.

    Uses update_item with a ConditionExpression to ensure the row exists
    before writing. This prevents creating phantom rows for non-existent
    document sessions.

    Why update_item and not put_item:
      put_item replaces the entire row — quiz_score, intent, self_answers,
      s3_original_key, transform_status, and everything else would be wiped.
      update_item is surgical — it only touches the two fields specified.

    Raises KeyError if the row does not exist (item was never scored).
    """
    table      = dynamodb.Table(TABLE)
    now_iso    = datetime.now(timezone.utc).isoformat()

    try:
        response = table.update_item(
            Key={'user_id': user_id, 'doc_id': doc_id},
            UpdateExpression='SET #lvl = :level, updated_at = :now',
            # 'level' is a reserved word in DynamoDB expression syntax
            # Use ExpressionAttributeNames to alias it safely
            ExpressionAttributeNames={'#lvl': 'level'},
            ExpressionAttributeValues={
                ':level': level,
                ':now':   now_iso
            },
            # Ensure the row already exists — don't create phantom rows
            ConditionExpression='attribute_exists(user_id)',
            ReturnValues='ALL_NEW'
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            raise KeyError(f"No document found for doc_id '{doc_id}' — cannot override level")
        raise

    updated = response.get('Attributes', {})
    return {
        'user_id':    updated.get('user_id'),
        'doc_id':     updated.get('doc_id'),
        'level':      updated.get('level'),
        'filename':   updated.get('filename', ''),
        'updated_at': updated.get('updated_at'),
    }


# ── Lambda entry point ─────────────────────────────────────────────────────────
def lambda_handler(event, context):
    """
    ── get_level ─────────────────────────────────────────────────────────────
    Request:  { "action": "get_level",
                "user_id": "abc123",
                "doc_id":  "abc123#biology.pdf#20260306120000" }

    Response (200): { "user_id": "...", "doc_id": "...",
                      "level": "intermediate", "filename": "biology.pdf",
                      "quiz_score": 3, "created_at": "..." }
    Response (404): { "error": "No document found for doc_id '...'" }

    ── set_level ─────────────────────────────────────────────────────────────
    Request:  { "action": "set_level",
                "user_id": "abc123",
                "doc_id":  "abc123#biology.pdf#20260306120000",
                "level":   "beginner" }

    Response (200): { "user_id": "...", "doc_id": "...",
                      "level": "beginner", "updated_at": "..." }
    Response (400): { "error": "level must be beginner, intermediate, or expert" }
    Response (404): { "error": "No document found for doc_id '...'" }
    """
    # ── Parse body ─────────────────────────────────────────────────────────────
    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': CORS,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }

    action = body.get('action')

    # ── ACTION: get_level ──────────────────────────────────────────────────────
    if action == 'get_level':
        raw_user_id = body.get('user_id')
        raw_doc_id  = body.get('doc_id')

        if not raw_user_id or not raw_doc_id:
            return {
                'statusCode': 400,
                'headers': CORS,
                'body': json.dumps({'error': "'user_id' and 'doc_id' are required for action=get_level"})
            }

        try:
            user_id = _validate_user_id(raw_user_id)
            doc_id  = _validate_doc_id(raw_doc_id)
        except ValueError as e:
            return {
                'statusCode': 400,
                'headers': CORS,
                'body': json.dumps({'error': str(e)})
            }

        try:
            result = _get_level(user_id, doc_id)
            return {
                'statusCode': 200,
                'headers': CORS,
                'body': json.dumps(result)
            }
        except KeyError as e:
            return {
                'statusCode': 404,
                'headers': CORS,
                'body': json.dumps({'error': str(e)})
            }
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': CORS,
                'body': json.dumps({'error': str(e)})
            }

    # ── ACTION: set_level ──────────────────────────────────────────────────────
    elif action == 'set_level':
        raw_user_id = body.get('user_id')
        raw_doc_id  = body.get('doc_id')
        level       = body.get('level')

        if not raw_user_id or not raw_doc_id or not level:
            return {
                'statusCode': 400,
                'headers': CORS,
                'body': json.dumps({'error': "'user_id', 'doc_id', and 'level' are required for action=set_level"})
            }

        if level not in VALID_LEVELS:
            return {
                'statusCode': 400,
                'headers': CORS,
                'body': json.dumps({'error': "level must be 'beginner', 'intermediate', or 'expert'"})
            }

        try:
            user_id = _validate_user_id(raw_user_id)
            doc_id  = _validate_doc_id(raw_doc_id)
        except ValueError as e:
            return {
                'statusCode': 400,
                'headers': CORS,
                'body': json.dumps({'error': str(e)})
            }

        try:
            result = _set_level(user_id, doc_id, level)
            return {
                'statusCode': 200,
                'headers': CORS,
                'body': json.dumps(result)
            }
        except KeyError as e:
            return {
                'statusCode': 404,
                'headers': CORS,
                'body': json.dumps({'error': str(e)})
            }
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': CORS,
                'body': json.dumps({'error': str(e)})
            }

    # ── Unknown action ─────────────────────────────────────────────────────────
    else:
        return {
            'statusCode': 400,
            'headers': CORS,
            'body': json.dumps({
                'error': f"Unknown action '{action}'. Use 'get_level' or 'set_level'."
            })
        }