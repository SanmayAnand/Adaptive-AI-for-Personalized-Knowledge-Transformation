#!/bin/bash
# scripts/zip_main.sh — Person A runs this to build the akte-main deployment zip
#
# Prerequisites:
#   - ocr.py must already be copied into backend/lambda-main/ (from Person B)
#   - transform.py must already be copied into backend/lambda-main/ (from Person C)
#   - Run from the repo root: bash scripts/zip_main.sh
#
# Output: akte_main.zip in the current directory
# Then: upload via Lambda console → Code tab → Upload from .zip file → Deploy

set -e

LAMBDA_DIR="backend/lambda-main"
OUTPUT="akte_main.zip"

echo "Checking for required files..."

for f in main_handler.py ocr.py transform.py; do
  if [ ! -f "$LAMBDA_DIR/$f" ]; then
    echo "ERROR: $LAMBDA_DIR/$f not found. Has Person B/C sent their files?"
    exit 1
  fi
done

echo "Zipping..."
cd "$LAMBDA_DIR"
zip -j "../../$OUTPUT" main_handler.py ocr.py transform.py
cd ../..

echo "Done: $OUTPUT created."
echo ""
echo "Next steps:"
echo "  1. Go to AWS Lambda → akte-main → Code → Upload from .zip file"
echo "  2. Upload $OUTPUT → Deploy"
echo "  3. Confirm pdfplumber-layer is attached (Layers section)"
