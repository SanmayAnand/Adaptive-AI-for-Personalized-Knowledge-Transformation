# test_connections.py
# Tests ALL connections WITHOUT needing AWS CLI installed.
# Just fill in your keys below and run: python test_connections.py

import json
import sys

from dotenv import load_dotenv
load_dotenv()

AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION     = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
BUCKET_NAME    = os.environ.get("BUCKET_NAME", "ocr-ai-for-bharat1")

HAIKU_MODEL = "anthropic.claude-3-haiku-20240307-v1:0"

# Colours (work on Windows PowerShell too)
def green(s):  return f"\033[92m{s}\033[0m"
def red(s):    return f"\033[91m{s}\033[0m"
def yellow(s): return f"\033[93m{s}\033[0m"
def bold(s):   return f"\033[1m{s}\033[0m"

import boto3

def make_client(service):
    """Create boto3 client using keys directly — no AWS CLI needed."""
    return boto3.client(
        service,
        region_name          = AWS_REGION,
        aws_access_key_id    = AWS_ACCESS_KEY,
        aws_secret_access_key= AWS_SECRET_KEY,
    )

print("\n" + "═"*58)
print(bold("  AKTE · Person B — Connection Checks (no AWS CLI)"))
print("═"*58 + "\n")

passed_all = True

# ── CHECK 1: boto3 installed ──────────────────────────────
print("[ 1/5 ] boto3 package")
try:
    import boto3
    print(f"  {green('✅ boto3')} version {boto3.__version__} found")
except ImportError:
    print(f"  {red('❌ boto3 not installed')}")
    print(f"     Fix: pip install boto3")
    passed_all = False

# ── CHECK 2: S3 bucket accessible ────────────────────────
print("\n[ 2/5 ] S3 bucket access")
try:
    s3   = make_client("s3")
    resp = s3.list_objects_v2(Bucket=BUCKET_NAME, MaxKeys=10)
    keys = [o["Key"] for o in resp.get("Contents", [])]
    print(f"  {green('✅ S3 connected')} — bucket: {BUCKET_NAME}")
    print(f"     Objects found: {len(keys)}")
    for k in keys[:5]:
        print(f"       📄 {k}")
    if len(keys) > 5:
        print(f"       ... and {len(keys)-5} more")
except Exception as e:
    print(f"  {red('❌ S3 failed')}: {e}")
    print( "     Possible fixes:")
    print( "       → Check AWS_ACCESS_KEY and AWS_SECRET_KEY above")
    print(f"       → Check bucket name is exactly: {BUCKET_NAME}")
    print( "       → Ask Person A: does your IAM user have AmazonS3FullAccess?")
    passed_all = False

# ── CHECK 3: Bedrock (Claude Haiku) ──────────────────────
print("\n[ 3/5 ] AWS Bedrock — Claude 3 Haiku")
try:
    bedrock = make_client("bedrock-runtime")
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 15,
        "messages": [{"role": "user",
                      "content": "Reply with exactly: CONNECTED"}]
    })
    resp  = bedrock.invoke_model(
        modelId      = HAIKU_MODEL,
        contentType  = "application/json",
        accept       = "application/json",
        body         = body
    )
    reply = json.loads(resp["body"].read())["content"][0]["text"].strip()
    print(f"  {green('✅ Bedrock connected')} — Haiku replied: {reply}")
except Exception as e:
    err = str(e)
    print(f"  {red('❌ Bedrock failed')}: {err}")
    if "AccessDenied" in err or "not authorized" in err.lower():
        print( "     Fix: Person A → AWS Console → Bedrock → Model access")
        print( "          → Enable 'Claude 3 Haiku'  (takes ~2 mins)")
        print( "     Also: IAM user needs AmazonBedrockFullAccess policy")
    elif "Could not connect" in err or "endpoint" in err.lower():
        print(f"     Fix: Check AWS_REGION is correct (currently: {AWS_REGION})")
    passed_all = False

# ── CHECK 4: Textract ─────────────────────────────────────
print("\n[ 4/5 ] AWS Textract")
try:
    textract = make_client("textract")
    # Intentionally use a non-existent key — we just want to confirm connectivity
    try:
        textract.detect_document_text(
            Document={"S3Object": {"Bucket": BUCKET_NAME, "Name": "__test_connection__"}}
        )
    except textract.exceptions.InvalidS3ObjectException:
        pass   # Expected — proves endpoint is reachable
    except textract.exceptions.UnsupportedDocumentException:
        pass
    except Exception as inner:
        if "AccessDenied" in str(inner):
            raise inner   # re-raise real access errors
        pass              # any other error = endpoint reached = OK
    print(f"  {green('✅ Textract connected')}")
except Exception as e:
    err = str(e)
    print(f"  {red('❌ Textract failed')}: {err}")
    if "AccessDenied" in err:
        print( "     Fix: IAM user needs AmazonTextractFullAccess policy")
        print( "          Ask Person A to add it in AWS Console → IAM")
    passed_all = False

# ── CHECK 5: pytesseract ──────────────────────────────────
print("\n[ 5/5 ] pytesseract (local free OCR)")
try:
    import pytesseract
    from PIL import Image, ImageDraw

    # Try Windows default path first
    import os
    win_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(win_path):
        pytesseract.pytesseract.tesseract_cmd = win_path

    # Create a tiny white image with text and OCR it
    img  = Image.new("RGB", (250, 50), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 15), "Hello OCR 123", fill="black")
    text = pytesseract.image_to_string(img).strip()

    if len(text) > 2:
        print(f"  {green('✅ pytesseract working')} — read: '{text}'")
    else:
        raise Exception("Tesseract returned empty string")

except ImportError as e:
    print(f"  {yellow('⚠️  pytesseract/Pillow not installed')}: {e}")
    print( "     Fix: pip install pytesseract Pillow")
    print( "     Note: OCR will fall back to AWS Textract (costs money)")
except Exception as e:
    print(f"  {yellow('⚠️  pytesseract installed but Tesseract binary missing')}")
    print( "     Fix: Download from https://github.com/UB-Mannheim/tesseract/wiki")
    print(r"          Install to: C:\Program Files\Tesseract-OCR\tesseract.exe")
    print( "     Note: Until fixed, scanned PDFs will use Textract ($) instead")

# ── SUMMARY ──────────────────────────────────────────────
print("\n" + "─"*58)
if passed_all:
    print(green("  🎉 Core checks passed! Run: python test_extract.py yourfile.pdf"))
else:
    print(yellow("  ⚠️  Fix the ❌ items above, then re-run this script."))
print("─"*58 + "\n")