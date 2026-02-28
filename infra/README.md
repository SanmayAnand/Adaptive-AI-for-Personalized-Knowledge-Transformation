# AWS Setup Guide
### Person A follows this on Day 1

This is your entire job on Day 1. Do these steps in order before anyone else can start testing.

---

## Step 1 — Enable Bedrock (10 min)
1. Go to AWS Console → Bedrock → Model Access
2. Find **Claude 3 Haiku** → click Request Access
3. Wait for approval (usually instant in us-east-1)
4. The model ID you'll use in code: `anthropic.claude-3-haiku-20240307-v1:0`

---

## Step 2 — Create S3 Bucket (10 min)
1. AWS Console → S3 → Create Bucket
2. Bucket name: `akte-bucket`
3. Region: `us-east-1`
4. Keep "Block all public access" ON (we use pre-signed URLs for downloads)
5. After creation, create two folders inside: `uploads/` and `outputs/`
   (just upload a blank .txt file inside each to create the folder)

---

## Step 3 — Create DynamoDB Table (5 min)
1. AWS Console → DynamoDB → Create Table
2. Table name: `akte-users`
3. Partition key: `user_id` (type: String)
4. No sort key
5. Capacity mode: **On-demand**
6. Create table

---

## Step 4 — Create IAM Role for Lambda (10 min)
All 4 Lambda functions use this one role. It gives them permission to use S3, DynamoDB, Bedrock, and Textract.

1. AWS Console → IAM → Roles → Create Role
2. Trusted entity: AWS Service → Lambda
3. Attach these 4 policies:
   - `AmazonS3FullAccess`
   - `AmazonDynamoDBFullAccess`
   - `AmazonBedrockFullAccess`
   - `AmazonTextractFullAccess`
4. Role name: `akte-lambda-role`
5. Create role

**When creating each Lambda, select this role. The Lambda can then call all AWS services without any keys in the code.**

---

## Step 5 — Create IAM Users for Teammates (15 min)
B, C, and D need keys to test their code locally against real AWS services.

For each person (do this 3 times):
1. AWS Console → IAM → Users → Create User
2. Usernames: `akte-personB`, `akte-personC`, `akte-personD`
3. Access type: **Programmatic access**
4. Attach the same 4 policies from Step 4
5. **Download the CSV immediately** — the secret key is shown only once
6. Send each person their **Access Key ID** and **Secret Access Key** privately (WhatsApp DM, not group chat)

---

## Step 6 — What each teammate does with their keys
Tell B, C, and D to run this on their laptop:

```
Install AWS CLI from: https://aws.amazon.com/cli/

Then run:
aws configure

It will ask:
  AWS Access Key ID:     → paste the key ID you sent them
  AWS Secret Access Key: → paste the secret key you sent them
  Default region:        → us-east-1
  Default output format: → json

Verify it works:
aws s3 ls
(should show akte-bucket without errors)
```

---

## Step 7 — Build the pdfplumber Lambda Layer (Day 2)
Person B's OCR code uses the `pdfplumber` library. Lambda doesn't have it by default, so you need to bundle it as a Layer.

Run on your laptop (needs Python installed):
```
mkdir python
pip install pdfplumber -t python/
zip -r pdfplumber_layer.zip python/
```

Then in AWS Console:
1. Lambda → Layers → Create Layer
2. Name: `pdfplumber-layer`
3. Upload: `pdfplumber_layer.zip`
4. Compatible runtimes: Python 3.11
5. Create

**Add this layer to: akte-main and akte-quiz (both use pdfplumber)**

---

## Step 8 — Create the 4 Lambda Functions (Day 2)
Do this once you have all .py files from B, C, D.

For every Lambda, the settings are:
- Runtime: Python 3.11
- Execution role: akte-lambda-role
- Memory: 512 MB
- Timeout: 60 seconds
- After saving: Configuration → Function URL → Create → Auth: NONE → CORS: Enable
- **Copy the Function URL and share it in the group chat**

### Lambda 1: akte-main
- Code: zip main_handler.py + ocr.py + transform.py together and upload
- Add the pdfplumber-layer to this Lambda

### Lambda 2: akte-upload
- Code: quiz/quiz_handler.py → just the upload_handler.py section (Person D gives you this)

### Lambda 3: akte-quiz
- Code: quiz/quiz_handler.py (Person D gives you this)
- Add the pdfplumber-layer to this Lambda

### Lambda 4: akte-profile
- Code: the profile_handler.py (Person D gives you this)

---

## Step 9 — Host the React App on S3 (Day 3)
Person D will send you a `/build` folder (the compiled React app).

1. S3 → akte-bucket → Create folder: `website/`
2. Upload everything inside `/build` into `website/`
3. Bucket → Properties → Static Website Hosting → Enable
   - Index document: `index.html`
   - Error document: `index.html`
4. Permissions → Bucket Policy → paste this:

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

5. The app is now live at: `http://akte-bucket.s3-website-us-east-1.amazonaws.com`

---

## Step 10 — Set a Budget Alert
AWS Billing → Budgets → Create Budget → set $20 threshold with email alert.
This project should cost well under $5 total.
