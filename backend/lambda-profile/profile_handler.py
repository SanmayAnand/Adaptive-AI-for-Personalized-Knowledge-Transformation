# profile_handler.py — Person D owns this
# Lambda: akte-profile
#
# Purpose: Read or manually override a user's level in DynamoDB.
#          The quiz sets the level automatically; this lets users override it if they want.
#
# ─────────────────────────────────────────────────────────────
# GET request (read user level)
# ─────────────────────────────────────────────────────────────
# Input body: { "user_id": "..." }
# Steps:
#   1. Detect method via event['requestContext']['http']['method']
#   2. DynamoDB get_item with Key={'user_id': user_id}
#   3. If not found, return default item: { 'user_id': user_id, 'level': 'intermediate' }
#   4. Return 200 with the item as JSON
#
# ─────────────────────────────────────────────────────────────
# POST request (override user level)
# ─────────────────────────────────────────────────────────────
# Input body: { "user_id": "...", "level": "beginner" | "intermediate" | "expert" }
# Steps:
#   1. Validate level is one of the three valid strings → return 400 if invalid
#   2. DynamoDB put_item: { user_id, level, updated_at (ISO timestamp) }
#   3. Return 200 { "level": level }
#
# ─────────────────────────────────────────────────────────────
# Constants:
#   TABLE = 'akte-users'
#
# CORS header required on every response: {'Access-Control-Allow-Origin': '*'}
# Return 400 if user_id is missing from body.
#
# Lambda settings:
#   Runtime: Python 3.11 | Memory: 512MB | Timeout: 60s | Role: akte-lambda-role
#   Function URL: Auth NONE | CORS enabled
#   No extra layers needed
#
# Full working code is in the blueprint document (Section: PERSON D, "Deliverable 3 — profile_handler.py").

import boto3
import json
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
TABLE = 'akte-users'


def lambda_handler(event, context):
    # TODO: detect GET vs POST, implement read and write as described above
    raise NotImplementedError
