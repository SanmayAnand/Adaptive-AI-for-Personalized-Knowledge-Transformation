#!/bin/bash
# scripts/build_layer.sh — Person A runs this to build the pdfplumber Lambda Layer
#
# Run once, before deploying any Lambda.
# Requires Python and pip installed locally.
#
# Output: pdfplumber_layer.zip
# Then upload via: Lambda → Layers → Create Layer → name: pdfplumber-layer
#                  Runtime: Python 3.11 → Create

set -e

echo "Building pdfplumber Lambda Layer..."
rm -rf python pdfplumber_layer.zip

mkdir python
pip install pdfplumber -t python/

zip -r pdfplumber_layer.zip python/

echo "Done: pdfplumber_layer.zip"
echo ""
echo "Next steps:"
echo "  1. AWS Console → Lambda → Layers → Create Layer"
echo "  2. Name: pdfplumber-layer"
echo "  3. Upload: pdfplumber_layer.zip"
echo "  4. Compatible runtimes: Python 3.11"
echo "  5. Create"
echo ""
echo "Add this layer to: akte-main and akte-quiz"
