# =============================================================================
# quiz/quiz_handler.py
# WHO WRITES THIS: Person D
# WHAT THIS IS: Lambda that generates quiz questions AND scores user answers
# =============================================================================
#
# HOW THE FRONTEND CALLS THIS:
#
#   Action 1 — Generate questions:
#     POST body: { "action": "generate", "filename": "myfile.pdf" }
#     Response:  { "questions": [ {question, options, correct}, ... ] }
#
#   Action 2 — Score answers and save level:
#     POST body: { "action": "score", "user_id": "...", "questions": [...], "answers": {"0":"A","1":"C",...} }
#     Response:  { "score": 3, "total": 5, "level": "intermediate", "message": "..." }
#
# HOW TO DEPLOY (Person A does this):
#   Lambda → akte-quiz → paste this file → Deploy
#   Add the pdfplumber-layer (needed by _get_pdf_preview)
#
# =============================================================================

import boto3
import json
from datetime import datetime

s3       = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
bedrock  = boto3.client('bedrock-runtime', region_name='us-east-1')

MODEL  = 'anthropic.claude-3-haiku-20240307-v1:0'
BUCKET = 'akte-bucket'
TABLE  = 'akte-users'
CORS   = {'Access-Control-Allow-Origin': '*'}


def _get_pdf_preview(filename):
    """
    Download the first ~1500 words of the uploaded PDF.
    Used as context for generating quiz questions.
    We don't need the full document — just enough to generate 5 questions.

    HOW TO IMPLEMENT:
      import pdfplumber, io

      obj  = s3.get_object(Bucket=BUCKET, Key=f'uploads/{filename}')
      data = obj['Body'].read()

      text = ''
      with pdfplumber.open(io.BytesIO(data)) as pdf:
          for page in pdf.pages[:5]:       # read max 5 pages
              t = page.extract_text()
              if t:
                  text += t + '\n'
              if len(text.split()) > 1500:
                  break

      return ' '.join(text.split()[:1500])  # cap at 1500 words
    """
    # TODO: implement this
    pass


def _generate_questions(preview_text):
    """
    Ask Bedrock to generate 5 multiple-choice questions about the document.
    Returns a list of 5 dicts, each: { question, options: {A,B,C}, correct }

    THE BEDROCK PROMPT:
      Tell Claude to:
        - Generate exactly 5 questions about the document's KEY CONCEPTS
        - Each question has exactly 3 options: A, B, C
        - Only one option is correct
        - Mix difficulty: 2 easy, 2 medium, 1 hard
        - Base ALL questions strictly on the text — no outside knowledge required
        - Test conceptual understanding, not just memorization
        - Respond ONLY with valid JSON in this exact format, no other text:

          [
            {
              "question": "...",
              "options": {"A": "...", "B": "...", "C": "..."},
              "correct": "A"
            }
          ]

    HOW TO IMPLEMENT:
      prompt = f'''[your prompt above]

Document excerpt:
{preview_text}'''

      body = json.dumps({
          'anthropic_version': 'bedrock-2023-05-31',
          'max_tokens': 1200,
          'messages': [{'role': 'user', 'content': prompt}]
      })
      response = bedrock.invoke_model(modelId=MODEL, body=body)
      raw = json.loads(response['body'].read())['content'][0]['text'].strip()

      # Strip markdown code fences if Bedrock wraps the JSON in ```json ... ```
      if raw.startswith('```'):
          raw = raw.split('```')[1]
          if raw.startswith('json'):
              raw = raw[4:]

      return json.loads(raw.strip())
    """
    # TODO: implement this
    pass


def _score_and_level(questions, answers):
    """
    Compare user's answers to correct answers. Calculate score and level.

    answers format: { '0': 'A', '1': 'C', '2': 'B', '3': 'A', '4': 'C' }
    (index as string → chosen option letter)

    SCORING:
      0–1 correct → 'beginner'
      2–3 correct → 'intermediate'
      4–5 correct → 'expert'

    HOW TO IMPLEMENT:
      score = 0
      for i, question in enumerate(questions):
          if answers.get(str(i)) == question['correct']:
              score += 1

      if score <= 1:   level = 'beginner'
      elif score <= 3: level = 'intermediate'
      else:            level = 'expert'

      return score, level
    """
    # TODO: implement this
    pass


def _save_profile(user_id, level, score):
    """
    Save the user's detected level to DynamoDB.

    HOW TO IMPLEMENT:
      dynamodb.Table(TABLE).put_item(Item={
          'user_id':    user_id,
          'level':      level,
          'quiz_score': score,
          'updated_at': datetime.utcnow().isoformat()
      })
    """
    # TODO: implement this
    pass


def lambda_handler(event, context):
    """
    Entry point. Routes to generate or score based on action field.

    HOW TO IMPLEMENT:

      body   = json.loads(event.get('body', '{}'))
      action = body.get('action')

      # ── ACTION: generate ──────────────────────────────────────
      if action == 'generate':
          filename = body.get('filename')
          if not filename:
              return {'statusCode': 400, 'headers': CORS,
                      'body': json.dumps({'error': 'filename required'})}
          try:
              preview   = _get_pdf_preview(filename)
              questions = _generate_questions(preview)
              return {'statusCode': 200, 'headers': CORS,
                      'body': json.dumps({'questions': questions})}
          except Exception as e:
              return {'statusCode': 500, 'headers': CORS,
                      'body': json.dumps({'error': str(e)})}

      # ── ACTION: score ─────────────────────────────────────────
      elif action == 'score':
          user_id   = body.get('user_id')
          questions = body.get('questions')
          answers   = body.get('answers')

          if not all([user_id, questions, answers]):
              return {'statusCode': 400, 'headers': CORS,
                      'body': json.dumps({'error': 'user_id, questions, and answers are all required'})}

          score, level = _score_and_level(questions, answers)
          _save_profile(user_id, level, score)

          return {'statusCode': 200, 'headers': CORS,
                  'body': json.dumps({
                      'score':   score,
                      'total':   len(questions),
                      'level':   level,
                      'message': f'You scored {score}/{len(questions)} — level set to {level.upper()}'
                  })}

      # ── Unknown action ────────────────────────────────────────
      else:
          return {'statusCode': 400, 'headers': CORS,
                  'body': json.dumps({'error': 'action must be "generate" or "score"'})}
    """
    # TODO: implement this
    pass
