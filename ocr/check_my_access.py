# check_my_access.py
# Finds your bucket region and checks what services you can use
# Run: python check_my_access.py

import boto3, json
import os

from dotenv import load_dotenv
load_dotenv()

ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
SECRET_KEY =  os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION            = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
BUCKET_NAME           = os.environ.get("BUCKET_NAME", "ocr-ai-for-bharat1")

def client(service, region="us-east-1"):
    return boto3.client(service, region_name=region,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY)

print("\n" + "="*50)
print("  Checking your AWS access...")
print("="*50)

# ── Step 1: Find actual bucket region ─────────────
print("\n[1] Finding bucket region...")
try:
    s3 = client("s3")
    loc = s3.get_bucket_location(Bucket=BUCKET_NAME)
    region = loc["LocationConstraint"] or "us-east-1"
    print(f"  ✅ Bucket '{BUCKET_NAME}' is in region: {region}")
    print(f"  ← USE THIS REGION IN ALL YOUR CODE")
except Exception as e:
    print(f"  ❌ {e}")
    region = "us-east-1"

# ── Step 2: List bucket contents ──────────────────
print("\n[2] Listing bucket contents...")
try:
    s3r = client("s3", region)
    resp = s3r.list_objects_v2(Bucket=BUCKET_NAME, MaxKeys=10)
    files = [o["Key"] for o in resp.get("Contents", [])]
    print(f"  ✅ Can access bucket — {len(files)} file(s) found")
    for f in files: print(f"       📄 {f}")
    if not files: print("       (bucket is empty — that's fine)")
except Exception as e:
    print(f"  ❌ {e}")

# ── Step 3: Check Bedrock in bucket's region ──────
print(f"\n[3] Checking Bedrock in {region}...")
HAIKU = "anthropic.claude-3-haiku-20240307-v1:0"
try:
    bd = client("bedrock-runtime", region)
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 10,
        "messages": [{"role": "user", "content": "say: OK"}]
    })
    resp = bd.invoke_model(modelId=HAIKU, contentType="application/json",
                           accept="application/json", body=body)
    reply = json.loads(resp["body"].read())["content"][0]["text"]
    print(f"  ✅ Bedrock works! Haiku said: {reply.strip()}")
except Exception as e:
    err = str(e)
    print(f"  ❌ Bedrock failed: {err[:80]}")
    if "payment" in err.lower():
        print("  → Your FRIEND needs to add a card to their AWS account")
        print("    and enable Claude Haiku in Bedrock Model Access")
    elif "Could not connect" in err or "not available" in err.lower():
        print(f"  → Bedrock may not be available in {region}")
        print("  → Will try us-east-1 as fallback...")
        # Try us-east-1 as fallback
        try:
            bd2 = client("bedrock-runtime", "us-east-1")
            resp2 = bd2.invoke_model(modelId=HAIKU, contentType="application/json",
                                     accept="application/json", body=body)
            reply2 = json.loads(resp2["body"].read())["content"][0]["text"]
            print(f"  ✅ Bedrock works in us-east-1! Use that region for Bedrock calls.")
        except Exception as e2:
            print(f"  ❌ us-east-1 also failed: {str(e2)[:80]}")
    elif "AccessDenied" in err:
        print("  → Your friend needs to add AmazonBedrockFullAccess to your IAM user")

# ── Step 4: Check Textract ─────────────────────────
print(f"\n[4] Checking Textract in {region}...")
try:
    tx = client("textract", region)
    tx.detect_document_text(
        Document={"S3Object": {"Bucket": BUCKET_NAME, "Name": "__test__"}})
except Exception as e:
    err = str(e)
    if "InvalidS3Object" in err or "UnsupportedDocument" in err:
        print(f"  ✅ Textract reachable in {region}")
    elif "AccessDenied" in err:
        print(f"  ❌ No Textract access — friend needs AmazonTextractFullAccess on your IAM user")
    else:
        print(f"  ✅ Textract endpoint reachable ({err[:50]})")

# ── Summary ────────────────────────────────────────
print("\n" + "="*50)
print(f"  YOUR REGION TO USE: {region}")
print(f"  Put this in ocr.py and test_connections.py:")
print(f'  AWS_REGION = "{region}"')
print("="*50 + "\n")