# test_connections.py
# Tests ALL AWS connections without AWS CLI
# Using Amazon Bedrock Nova Lite instead of Claude Haiku

import json
import os
from dotenv import load_dotenv
load_dotenv()

import boto3

AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION     = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
BUCKET_NAME    = os.environ.get("BUCKET_NAME", "ocr-ai-for-bharat1")

# ── Switched from Claude Haiku → Amazon Nova Lite ──
# Other Nova options:
#   amazon.nova-micro-v1:0  (fastest, text-only, cheapest)
#   amazon.nova-lite-v1:0   (fast, multimodal, cheap)     ← using this
#   amazon.nova-pro-v1:0    (most capable, multimodal)
NOVA_MODEL = "amazon.nova-lite-v1:0"

# ─────────────────────────────────────────────
# Colours
# ─────────────────────────────────────────────
def green(s):  return f"\033[92m{s}\033[0m"
def red(s):    return f"\033[91m{s}\033[0m"
def yellow(s): return f"\033[93m{s}\033[0m"
def bold(s):   return f"\033[1m{s}\033[0m"

# ─────────────────────────────────────────────
# Create AWS client
# ─────────────────────────────────────────────
def make_client(service):
    return boto3.client(
        service,
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )

print("\n" + "═"*60)
print(bold(" AKTE · Person B — AWS Connection Tests"))
print("═"*60 + "\n")

passed_all = True

# ─────────────────────────────────────────────
# CHECK 1 — boto3
# ─────────────────────────────────────────────
print("[ 1/5 ] boto3 package")

try:
    print(f"  {green('✅ boto3 installed')} version {boto3.__version__}")
except Exception:
    print(f"  {red('❌ boto3 missing')}")
    print("     Fix: pip install boto3")
    passed_all = False


# ─────────────────────────────────────────────
# CHECK 2 — S3
# ─────────────────────────────────────────────
print("\n[ 2/5 ] S3 bucket access")

try:
    s3 = make_client("s3")

    resp = s3.list_objects_v2(
        Bucket=BUCKET_NAME,
        MaxKeys=10
    )

    objects = resp.get("Contents", [])

    print(f"  {green('✅ S3 connected')} — bucket: {BUCKET_NAME}")
    print(f"     Objects found: {len(objects)}")

    for obj in objects[:5]:
        print(f"       📄 {obj['Key']}")

except Exception as e:
    print(f"  {red('❌ S3 failed')}: {e}")
    print("     Check IAM permissions or bucket name")
    passed_all = False


# ─────────────────────────────────────────────
# CHECK 3 — Bedrock Amazon Nova Lite
# ─────────────────────────────────────────────
# Nova uses a DIFFERENT request/response format vs Claude:
#
#  Request body:
#    messages[].content is a list of {"text": "..."} objects
#    token limit key is "max_new_tokens" inside "inferenceConfig"
#    NO "anthropic_version" field needed
#
#  Response path:
#    result["output"]["message"]["content"][0]["text"]
#
# ─────────────────────────────────────────────
print("\n[ 3/5 ] Bedrock — Amazon Nova Lite")

try:
    bedrock = make_client("bedrock-runtime")

    # Nova request format (different from Claude)
    body = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "text": "Reply with exactly: CONNECTED"
                    }
                ]
            }
        ],
        "inferenceConfig": {
            "max_new_tokens": 20,
            "temperature": 0
        }
    }

    response = bedrock.invoke_model(
        modelId=NOVA_MODEL,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body)
    )

    result = json.loads(response["body"].read())

    # Nova response path (different from Claude)
    reply = result["output"]["message"]["content"][0]["text"].strip()

    print(f"  {green('✅ Bedrock Nova connected')} — model: {NOVA_MODEL}")
    print(f"     Reply: {reply}")

except Exception as e:
    print(f"  {red('❌ Bedrock Nova failed')}: {e}")

    if "AccessDenied" in str(e) or "access" in str(e).lower():
        print("     Fix: Enable Amazon Nova model access in Bedrock console:")
        print("       AWS Console → Bedrock → Model Access → Request Access")
        print("       Enable: Amazon Nova Lite (amazon.nova-lite-v1:0)")

    elif "ResourceNotFoundException" in str(e):
        print("     Fix: Model ID not found — check region supports Nova")
        print("       Nova is available in: us-east-1, us-west-2")
        print(f"       Your region: {AWS_REGION}")

    elif "ValidationException" in str(e):
        print("     Fix: Request format issue — check body structure")

    passed_all = False


# ─────────────────────────────────────────────
# CHECK 4 — Textract
# ─────────────────────────────────────────────
print("\n[ 4/5 ] Textract")

try:
    textract = make_client("textract")

    try:
        textract.detect_document_text(
            Document={
                "S3Object": {
                    "Bucket": BUCKET_NAME,
                    "Name": "__test__"
                }
            }
        )
    except Exception:
        pass

    print(f"  {green('✅ Textract reachable')}")

except Exception as e:
    print(f"  {red('❌ Textract failed')}: {e}")
    print("     Fix: Add AmazonTextractFullAccess to IAM user")
    passed_all = False


# ─────────────────────────────────────────────
# CHECK 5 — pytesseract
# ─────────────────────────────────────────────
print("\n[ 5/5 ] pytesseract OCR")

try:
    import pytesseract
    from PIL import Image, ImageDraw

    win_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    if os.path.exists(win_path):
        pytesseract.pytesseract.tesseract_cmd = win_path

    img = Image.new("RGB", (250, 60), "white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 20), "Hello OCR 123", fill="black")

    text = pytesseract.image_to_string(img).strip()

    print(f"  {green('✅ pytesseract working')} — read: {text}")

except ImportError:
    print(f"  {yellow('⚠ pytesseract not installed')}")
    print("     Fix: pip install pytesseract pillow")

except Exception:
    print(f"  {yellow('⚠ Tesseract binary missing')}")
    print("     Install from:")
    print("     https://github.com/UB-Mannheim/tesseract/wiki")


# ─────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────
print("\n" + "─"*60)

if passed_all:
    print(green(" 🎉 All core services reachable"))
    print(" Next step: python test_extract.py yourfile.pdf")
else:
    print(yellow(" ⚠ Some checks failed — fix them and run again"))

print("─"*60 + "\n")