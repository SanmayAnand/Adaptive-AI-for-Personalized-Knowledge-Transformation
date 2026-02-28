# Person A — AWS Infrastructure Setup Guide

## Day 1 Checklist (do in this order)

### 1. Enable Bedrock Model Access
- AWS Console → Bedrock → Model Access → Claude 3 Haiku → Request access
- Wait for approval (usually instant in us-east-1)
- Model ID you'll use in code: `anthropic.claude-3-haiku-20240307-v1:0`

### 2. Create S3 Bucket
- AWS Console → S3 → Create Bucket
- Name: `akte-bucket`
- Region: `us-east-1`
- Block all public access: ON (we use pre-signed URLs for outputs; website hosting is a separate config)
- After creation, manually create two "folders" (just upload a blank placeholder file): `uploads/` and `outputs/`

### 3. Create DynamoDB Table
- AWS Console → DynamoDB → Create Table
- Table name: `akte-users`
- Partition key: `user_id` (String)
- Sort key: none
- Capacity mode: On-demand (no provisioning needed for hackathon)

### 4. Create Lambda Execution Role
- AWS Console → IAM → Roles → Create Role
- Trusted entity: AWS Service → Lambda
- Attach these 4 policies:
  - `AmazonS3FullAccess`
  - `AmazonDynamoDBFullAccess`
  - `AmazonBedrockFullAccess`
  - `AmazonTextractFullAccess`
- Role name: `akte-lambda-role`
- This role is attached to every Lambda at creation time. No keys go in code.

### 5. Create IAM Users for Teammates
Create one user per person (B, C, D) for local development testing:
- AWS Console → IAM → Users → Create User
- Usernames: `akte-personB`, `akte-personC`, `akte-personD`
- Access type: Programmatic access (generates Access Key ID + Secret Access Key)
- Attach the same 4 policies as above
- ⚠️ Download the CSV immediately — the secret key is shown ONCE
- Send each person their keys privately (WhatsApp DM, not group chat)

### 6. Set Budget Alert
- Billing → Budgets → Create Budget → $20 threshold
- Prevents surprise charges if something runs in a loop

---

## Day 2 — Build pdfplumber Lambda Layer
Run this on your laptop (Python must be installed):

```bash
mkdir python
pip install pdfplumber -t python/
zip -r pdfplumber_layer.zip python/
```

Then in AWS Console:
- Lambda → Layers → Create Layer
- Name: `pdfplumber-layer`
- Upload: `pdfplumber_layer.zip`
- Compatible runtimes: Python 3.11
- Create

---

## Day 2 — Deploy All 4 Lambda Functions

For EACH Lambda (settings apply to all unless noted):
- Lambda → Create Function → Author from scratch
- Runtime: Python 3.11
- Execution role: Use existing → `akte-lambda-role`
- Memory: 512 MB
- Timeout: 60 seconds
- After deploy: Configuration → Function URL → Create → Auth type: NONE → CORS: Enable
- Copy the Function URL → share in group chat

### Lambda 1: akte-main (Person A zips this)
- Receive `ocr.py` from Person B and `transform.py` from Person C
- Put all three files in one folder: `main_handler.py`, `ocr.py`, `transform.py`
- See `scripts/zip_main.sh`
- **Add pdfplumber layer** to this Lambda (Layers section at bottom of page)

### Lambda 2: akte-upload
- Code: `backend/lambda-upload/upload_handler.py`
- No layer needed

### Lambda 3: akte-quiz
- Code: `backend/lambda-quiz/quiz_handler.py`
- **Add pdfplumber layer** (it reads the PDF directly to generate questions)

### Lambda 4: akte-profile
- Code: `backend/lambda-profile/profile_handler.py`
- No layer needed

---

## Day 3 — Host React App on S3

Person D sends you the `/build` folder (output of `npm run build`).

1. S3 → `akte-bucket` → Create folder: `website/`
2. Upload everything inside `/build` into `website/`
3. Bucket → Properties → Static website hosting → Enable
   - Index document: `index.html`
   - Error document: `index.html` (React handles routing client-side)
4. Permissions → Bucket Policy → paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::akte-bucket/website/*"
  }]
}
```

5. App is live at: `http://akte-bucket.s3-website-us-east-1.amazonaws.com`

---

## Summary: Who Gets What

| Person | Gets | Used for | How |
|--------|------|----------|-----|
| A | Root account | AWS Console only | Browser login |
| B | akte-personB keys | Testing ocr.py locally | `aws configure` |
| C | akte-personC keys | Testing transform.py + Bedrock | `aws configure` |
| D | akte-personD keys | Testing quiz_handler + DynamoDB | `aws configure` |
| Lambdas | akte-lambda-role | Running in cloud | Assigned at creation |

⚠️ Keys go in NO file. Not .py, not .js, not GitHub. `aws configure` stores them in `~/.aws/credentials`.
