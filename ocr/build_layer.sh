#!/bin/bash
# Builds a Lambda Layer containing tesseract binary + pytesseract
# Run this on an Amazon Linux 2 EC2 or via Docker

docker run --rm -v $(pwd):/output amazonlinux:2 bash -c "
  yum install -y tesseract poppler-utils zip python3-pip &&
  mkdir -p /layer/bin /layer/lib &&
  cp /usr/bin/tesseract /layer/bin/ &&
  cp /usr/bin/pdfinfo /layer/bin/ &&
  cp /usr/bin/pdftoppm /layer/bin/ &&
  cp -r /usr/share/tesseract/tessdata /layer/ &&
  ldd /usr/bin/tesseract | awk '{print \$3}' | grep '/' | xargs -I{} cp {} /layer/lib/ &&
  pip3 install pytesseract pdf2image Pillow -t /layer/python/ &&
  cd /layer && zip -r /output/tesseract_layer.zip . &&
  echo 'Layer zip built!'
"

echo ""
echo "Upload to Lambda:"
echo "  AWS Console → Lambda → Layers → Create Layer"
echo "  Name: tesseract-layer | Upload tesseract_layer.zip | Runtime: Python 3.11"
echo ""
echo "Then in Lambda env vars, set:"
echo "  TESSERACT_CMD = /opt/bin/tesseract"
echo "  TESSDATA_PREFIX = /opt/tessdata"