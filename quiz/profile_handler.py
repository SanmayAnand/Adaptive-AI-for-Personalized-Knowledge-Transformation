# =============================================================================
# quiz/profile_handler.py
# WHO WRITES THIS: Person D
# WHAT THIS IS: Lambda that reads or manually overrides a user's level in DynamoDB
# =============================================================================
#
# WHY THIS EXISTS:
#   The quiz automatically sets the level. But the Level Result screen lets
#   the user override their level manually (e.g. "I'm actually intermediate").
#   This Lambda handles that override.
#
# HOW THE FRONTEND CALLS THIS:
#
#   GET (read level):
#     Body: { "user_id": "user_abc123" }
#     Response: { "user_id": "...", "level": "intermediate" }
#
#   POST (override level):
#     Body: { "user_id": "user_abc123", "level": "beginner" }
#     Response: { "level": "beginner" }
#
# HOW TO DEPLOY: Person A creates Lambda 'akte-profile' and pastes this file.
#
# =============================================================================

import boto3
import json
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
TABLE    = 'akte-users'
CORS     = {'Access-Control-Allow-Origin': '*'}


def lambda_handler(event, context):
    """
    HOW TO IMPLEMENT:

      # Detect GET vs POST
      method  = event.get('requestContext', {}).get('http', {}).get('method', 'POST')
      body    = json.loads(event.get('body', '{}'))
      user_id = body.get('user_id')
      table   = dynamodb.Table(TABLE)

      # Always require user_id
      if not user_id:
          return {'statusCode': 400, 'headers': CORS,
                  'body': json.dumps({'error': 'user_id is required'})}

      # ── GET: read the user's current level ────────────────────
      if method == 'GET':
          response = table.get_item(Key={'user_id': user_id})
          item = response.get('Item', {'user_id': user_id, 'level': 'intermediate'})
          return {'statusCode': 200, 'headers': CORS,
                  'body': json.dumps(item)}

      # ── POST: override the user's level ───────────────────────
      level = body.get('level')
      if level not in ['beginner', 'intermediate', 'expert']:
          return {'statusCode': 400, 'headers': CORS,
                  'body': json.dumps({'error': 'level must be beginner, intermediate, or expert'})}

      table.put_item(Item={
          'user_id':    user_id,
          'level':      level,
          'updated_at': datetime.utcnow().isoformat()
      })

      return {'statusCode': 200, 'headers': CORS,
              'body': json.dumps({'level': level})}
    """
    # TODO: implement this
    pass
