
import sys
import os
import time
import boto3
from pathlib import Path
from ocr import extract_text, _quality_score


from dotenv import load_dotenv
load_dotenv()

AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION     = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
BUCKET    = os.environ.get("BUCKET_NAME", "ocr-ai-for-bharat1")

# Colour helpers
def green(s):  return f"\033[92m{s}\033[0m"
def red(s):    return f"\033[91m{s}\033[0m"
def yellow(s): return f"\033[93m{s}\033[0m"
def bold(s):   return f"\033[1m{s}\033[0m"

SUPPORTED = {".pdf", ".pptx", ".ppt", ".docx", ".doc",
             ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}


def upload_file(local_path: str) -> str:
    key = f"uploads/{Path(local_path).name}"
    print(f"  📤 Uploading {local_path} → s3://{BUCKET}/{key}")
    boto3.client("s3", region_name=AWS_REGION,
                 aws_access_key_id=AWS_ACCESS_KEY,
                 aws_secret_access_key=AWS_SECRET_KEY).upload_file(local_path, BUCKET, key)
    print(f"  ✅ Upload done")
    return key


def test_one(key: str) -> dict:
    """Run extraction on one S3 key and return results dict."""
    ext  = Path(key).suffix.lower()
    name = Path(key).name

    print(f"\n{'─'*60}")
    print(bold(f"  Testing: {name}"))
    print(f"{'─'*60}")
    username = "Hriday"

    result = {
        "file"   : name,
        "ext"    : ext,
        "passed" : False,
        "chars"  : 0,
        "words"  : 0,
        "score"  : 0,
        "time_s" : 0,
        "error"  : None,
        "preview": ""
    }
    t0 = time.time()
    try:
        text = extract_text(BUCKET, key)
        output_file = Path(key).stem + f'/{username}/' + "_extracted.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"  💾 Full text saved to: {output_file}")
        result["time_s"] = round(time.time() - t0, 2)
        result["chars"]  = len(text)
        result["words"]  = len(text.split())
        result["score"]  = _quality_score(text)
        result["preview"] = text[:300].replace("\n", " ")
        result["passed"] = True

    except Exception as e:
        result["time_s"] = round(time.time() - t0, 2)
        result["error"]  = str(e)

    # Print result
    if result["passed"]:
        score = result["score"]
        score_str = (
            green(f"{score}/100 ✅") if score >= 70 else
            yellow(f"{score}/100 ⚠️") if score >= 35 else
            red(f"{score}/100 ❌")
        )
        print(f"  Status  : {green('PASSED')}")
        print(f"  Chars   : {result['chars']:,}")
        print(f"  Words   : {result['words']:,}")
        print(f"  Quality : {score_str}")
        print(f"  Time    : {result['time_s']}s")
        print(f"\n  Preview (first 300 chars):")
        print(f"  {result['preview']}")
    else:
        print(f"  Status  : {red('FAILED')}")
        print(f"  Error   : {red(result['error'])}")
        print(f"  Time    : {result['time_s']}s")

    return result


def test_all_in_s3() -> list:
    s3 = boto3.client("s3", region_name=AWS_REGION,
                      aws_access_key_id=AWS_ACCESS_KEY,
                      aws_secret_access_key=AWS_SECRET_KEY)
    resp = s3.list_objects_v2(Bucket=BUCKET, Prefix="uploads/")
    keys = [
        obj["Key"] for obj in resp.get("Contents", [])
        if Path(obj["Key"]).suffix.lower() in SUPPORTED
    ]

    if not keys:
        print(red("\n  No supported files found in s3://akte-bucket/uploads/"))
        print("  Upload a test file first:")
        print("    aws s3 cp myfile.pdf s3://akte-bucket/uploads/myfile.pdf")
        return []

    print(f"\n  Found {len(keys)} supported file(s) in S3:")
    for k in keys:
        print(f"    {k}")

    return [test_one(k) for k in keys]


def print_summary(results: list):
    if not results:
        return
    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed

    print(f"\n{'═'*60}")
    print(bold("  SUMMARY"))
    print(f"{'═'*60}")
    print(f"  Total   : {len(results)}")
    print(f"  Passed  : {green(str(passed))}")
    print(f"  Failed  : {red(str(failed)) if failed else '0'}")
    print()

    for r in results:
        status = green("✅ PASS") if r["passed"] else red("❌ FAIL")
        if r["passed"]:
            score_color = green if r["score"] >= 70 else (yellow if r["score"] >= 35 else red)
            print(f"  {status}  {r['file']:<35}  "
                  f"chars={r['chars']:>6,}  "
                  f"quality={score_color(str(r['score']))}/100  "
                  f"{r['time_s']}s")
        else:
            print(f"  {status}  {r['file']:<35}  {red(str(r['error'])[:60])}")

    print(f"\n{'═'*60}")

    if failed:
        print(red(f"\n  ⚠️  {failed} file(s) failed. Check errors above."))
    else:
        print(green(f"\n  🎉 All files extracted successfully!"))
        avg_score = sum(r["score"] for r in results) / len(results)
        print(f"     Average quality score: {avg_score:.0f}/100")
        if avg_score < 50:
            print(yellow("     Consider enabling USE_HAIKU=true in Lambda env vars"))
        else:
            print(green("     Text quality is good — Haiku not needed (saving Claude API budget)"))
    print()


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "═"*60)
    print(bold("  AKTE · Person B — Extraction Tests"))
    print("═"*60)

    if len(sys.argv) > 1:
        # Single file mode: upload then test
        local_path = sys.argv[1]
        if not os.path.exists(local_path):
            print(red(f"  File not found: {local_path}"))
            sys.exit(1)
        ext = Path(local_path).suffix.lower()
        if ext not in SUPPORTED:
            print(red(f"  Unsupported type: {ext}"))
            print(f"  Supported: {', '.join(sorted(SUPPORTED))}")
            sys.exit(1)

        key     = upload_file(local_path)
        results = [test_one(key)]
    else:
        # Batch mode: test everything in S3
        results = test_all_in_s3()

    print_summary(results)