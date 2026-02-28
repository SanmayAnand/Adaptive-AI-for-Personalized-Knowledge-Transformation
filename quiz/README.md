# Quiz Lambda
### Person D works in this folder

---

## What this Lambda does
Two things, controlled by `action` in the request body:

1. **`action: "generate"`** — reads the uploaded PDF, asks Bedrock to generate 5 quiz questions, returns them to the frontend
2. **`action: "score"`** — receives the user's answers, calculates their level, saves it to DynamoDB

---

## How to test locally

```
pip install pdfplumber boto3
aws configure    ← use keys from Person A
```

Upload a test PDF first:
```
aws s3 cp any_pdf.pdf s3://akte-bucket/uploads/test.pdf
```

Then test:
```python
# Simulate the generate action
import json
from quiz_handler import lambda_handler

# Test generate
event = {'body': json.dumps({'action': 'generate', 'filename': 'test.pdf'})}
result = lambda_handler(event, None)
print(result)

# Test score
event = {'body': json.dumps({
    'action': 'score',
    'user_id': 'test-user-1',
    'questions': [{'question': 'Q?', 'options': {'A':'Yes','B':'No','C':'Maybe'}, 'correct': 'A'}],
    'answers': {'0': 'A'}
})}
result = lambda_handler(event, None)
print(result)
```

---

## When you're done
Send `quiz_handler.py` to Person A. They deploy it as the `akte-quiz` Lambda.
Also send them `upload_handler.py` and `profile_handler.py` (which you'll create in this folder too).
