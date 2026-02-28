# quiz_handler.py — Person D owns this
# Lambda: akte-quiz
#
# Purpose: Two actions in one Lambda, selected by body.action:
#   "generate" — read uploaded PDF, use Bedrock to create 5 quiz questions
#   "score"    — check user answers, calculate level, save to DynamoDB
#
# ─────────────────────────────────────────────────────────────
# ACTION: generate
# ─────────────────────────────────────────────────────────────
# Input body: { "action": "generate", "filename": "myfile.pdf" }
# Steps:
#   1. _get_pdf_preview(filename):
#      - s3.get_object from uploads/{filename}
#      - Open with pdfplumber, read first 5 pages max
#      - Stop early if word count > 1500
#      - Return first 1500 words as a string
#   2. _generate_questions(preview_text):
#      - Build a Bedrock prompt that asks Claude to return EXACTLY 5 questions as JSON
#      - Each question: { "question": "...", "options": {"A":"...","B":"...","C":"..."}, "correct": "A" }
#      - Rules: 2 easy / 2 medium / 1 hard, conceptual (not memorisation), based ONLY on the text
#      - Parse JSON from Bedrock response (strip markdown fences if present)
#      - Return list of 5 question dicts
#   3. Return 200 { "questions": [...] }
#      Note: correct answers ARE included in the response for hackathon simplicity.
#            The frontend stores them and sends them back during scoring (see below).
#
# ─────────────────────────────────────────────────────────────
# ACTION: score
# ─────────────────────────────────────────────────────────────
# Input body: { "action": "score", "user_id": "...", "questions": [...], "answers": {"0":"A","1":"C",...} }
# Steps:
#   1. _score_and_level(questions, answers):
#      - Compare answers[str(i)] to questions[i]['correct'] for each question
#      - Score 0-5 → level mapping:
#          0-1 correct → 'beginner'
#          2-3 correct → 'intermediate'
#          4-5 correct → 'expert'
#      - Return (score, level)
#   2. _save_profile(user_id, level, score):
#      - DynamoDB put_item: { user_id, level, quiz_score, updated_at (ISO timestamp) }
#   3. Return 200 { "score": N, "total": 5, "level": "...", "message": "You scored N/5 — level set to LEVEL" }
#
# ─────────────────────────────────────────────────────────────
# Constants:
#   BUCKET = 'akte-bucket'
#   TABLE  = 'akte-users'
#   MODEL  = 'anthropic.claude-3-haiku-20240307-v1:0'
#
# CORS header required on every response: {'Access-Control-Allow-Origin': '*'}
#
# Lambda settings:
#   Runtime: Python 3.11 | Memory: 512MB | Timeout: 60s | Role: akte-lambda-role
#   Function URL: Auth NONE | CORS enabled
#   Layer: pdfplumber-layer (needed for _get_pdf_preview)
#
# Full working code is in the blueprint document (Section: PERSON D, main quiz_handler section).

import boto3
import json
from datetime import datetime

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

MODEL = 'anthropic.claude-3-haiku-20240307-v1:0'
BUCKET = 'akte-bucket'
TABLE = 'akte-users'


def _get_pdf_preview(filename):
    # TODO: download first 1500 words from PDF using pdfplumber
    raise NotImplementedError


def _generate_questions(preview_text):
    # TODO: call Bedrock, return list of 5 question dicts
    raise NotImplementedError


def _score_and_level(questions, answers):
    # TODO: compute score, map to level string, return (score, level)
    raise NotImplementedError


def _save_profile(user_id, level, score):
    # TODO: DynamoDB put_item with user_id, level, quiz_score, updated_at
    raise NotImplementedError


def lambda_handler(event, context):
    # TODO: parse action, route to generate or score logic, return JSON with CORS headers
    raise NotImplementedError
