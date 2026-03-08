import boto3
import json
import re
import os
from botocore.exceptions import ClientError
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

TABLE        = os.environ.get('TABLE_NAME', 'akte-users')
CORS         = {
    'Access-Control-Allow-Origin':  '*',
    'Access-Control-Allow-Headers': 'content-type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
}
VALID_LEVELS = {'beginner', 'intermediate', 'expert'}


def _validate_user_id(user_id):
    if not user_id or not isinstance(user_id, str):
        raise ValueError("user_id must be a non-empty string")
    if not re.match(r'^[a-zA-Z0-9\-]{1,64}$', user_id.strip()):
        raise ValueError("user_id contains invalid characters")
    return user_id.strip()


def _validate_doc_id(doc_id):
    if not doc_id or not isinstance(doc_id, str):
        raise ValueError("doc_id must be a non-empty string")
    doc_id = doc_id.strip()
    if not re.match(r'^[a-zA-Z0-9\-_\.#]{1,256}$', doc_id):
        raise ValueError("doc_id contains invalid characters")
    if len(doc_id.split('#')) != 3:
        raise ValueError("doc_id format invalid — expected user_id#filename#timestamp")
    return doc_id


def _get_level(user_id, doc_id):
    table    = dynamodb.Table(TABLE)
    response = table.get_item(Key={'user_id': user_id, 'doc_id': doc_id})
    item     = response.get('Item')
    if not item:
        raise KeyError(f"No document found for doc_id '{doc_id}'")
    return {
        'user_id':    item.get('user_id'),
        'doc_id':     item.get('doc_id'),
        'level':      item.get('level', 'beginner'),
        'filename':   item.get('filename', ''),
        'quiz_score': item.get('quiz_score'),
        'created_at': item.get('created_at'),
    }


def _set_level(user_id, doc_id, level):
    table   = dynamodb.Table(TABLE)
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        response = table.update_item(
            Key={'user_id': user_id, 'doc_id': doc_id},
            UpdateExpression='SET #lvl = :level, updated_at = :now',
            ExpressionAttributeNames={'#lvl': 'level'},
            ExpressionAttributeValues={':level': level, ':now': now_iso},
            ConditionExpression='attribute_exists(user_id)',
            ReturnValues='ALL_NEW'
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            raise KeyError(f"No document found for doc_id '{doc_id}'")
        raise
    updated = response.get('Attributes', {})
    return {
        'user_id':    updated.get('user_id'),
        'doc_id':     updated.get('doc_id'),
        'level':      updated.get('level'),
        'filename':   updated.get('filename', ''),
        'updated_at': updated.get('updated_at'),
    }


def lambda_handler(event, context):
    # ── CORS preflight ─────────────────────────────────────────────────────────
    method = event.get('requestContext', {}).get('http', {}).get('method', '')
    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS, 'body': ''}

    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        return {'statusCode': 400, 'headers': CORS,
                'body': json.dumps({'error': 'Invalid JSON in request body'})}

    action = body.get('action')

    if action == 'get_level':
        raw_user_id = body.get('user_id')
        raw_doc_id  = body.get('doc_id')
        if not raw_user_id or not raw_doc_id:
            return {'statusCode': 400, 'headers': CORS,
                    'body': json.dumps({'error': "'user_id' and 'doc_id' are required"})}
        try:
            user_id = _validate_user_id(raw_user_id)
            doc_id  = _validate_doc_id(raw_doc_id)
        except ValueError as e:
            return {'statusCode': 400, 'headers': CORS, 'body': json.dumps({'error': str(e)})}
        try:
            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps(_get_level(user_id, doc_id))}
        except KeyError as e:
            return {'statusCode': 404, 'headers': CORS, 'body': json.dumps({'error': str(e)})}
        except Exception as e:
            return {'statusCode': 500, 'headers': CORS, 'body': json.dumps({'error': str(e)})}

    elif action == 'set_level':
        raw_user_id = body.get('user_id')
        raw_doc_id  = body.get('doc_id')
        level       = body.get('level')
        if not raw_user_id or not raw_doc_id or not level:
            return {'statusCode': 400, 'headers': CORS,
                    'body': json.dumps({'error': "'user_id', 'doc_id', and 'level' are required"})}
        if level not in VALID_LEVELS:
            return {'statusCode': 400, 'headers': CORS,
                    'body': json.dumps({'error': "level must be 'beginner', 'intermediate', or 'expert'"})}
        try:
            user_id = _validate_user_id(raw_user_id)
            doc_id  = _validate_doc_id(raw_doc_id)
        except ValueError as e:
            return {'statusCode': 400, 'headers': CORS, 'body': json.dumps({'error': str(e)})}
        try:
            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps(_set_level(user_id, doc_id, level))}
        except KeyError as e:
            return {'statusCode': 404, 'headers': CORS, 'body': json.dumps({'error': str(e)})}
        except Exception as e:
            return {'statusCode': 500, 'headers': CORS, 'body': json.dumps({'error': str(e)})}

    else:
        return {'statusCode': 400, 'headers': CORS, 'body': json.dumps({
            'error': f"Unknown action '{action}'. Use 'get_level' or 'set_level'."
        })}