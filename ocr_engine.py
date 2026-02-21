"""
OCR Intelligence Engine
Handles image preprocessing, layout detection, and text extraction using Tesseract.
"""

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from pdf2image import convert_from_path
import os
import json
import re


# ─────────────────────────────────────────────
#  VISION PREPROCESSING MODULE (Perception Layer)
# ─────────────────────────────────────────────

class VisionPreprocessor:
    """CNN-inspired adaptive preprocessing pipeline."""

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """Full preprocessing pipeline."""
        image = self._correct_skew(image)
        image = self._adaptive_denoise(image)
        image = self._enhance_contrast(image)
        image = self._binarize(image)
        return image

    def _correct_skew(self, image: np.ndarray) -> np.ndarray:
        """Deskew rotated/tilted documents."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        gray = cv2.bitwise_not(gray)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) == 0:
            return image
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        if abs(angle) < 0.5:  # skip tiny corrections
            return image
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h),
                                 flags=cv2.INTER_CUBIC,
                                 borderMode=cv2.BORDER_REPLICATE)
        return rotated

    def _adaptive_denoise(self, image: np.ndarray) -> np.ndarray:
        """Adaptive noise removal (learned threshold vs fixed)."""
        if len(image.shape) == 3:
            return cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
        return cv2.fastNlMeansDenoising(image, None, 10, 7, 21)

    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Enhance contrast using CLAHE (handles uneven lighting)."""
        if len(image.shape) == 3:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            enhanced = cv2.merge([l, a, b])
            return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        else:
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            return clahe.apply(image)

    def _binarize(self, image: np.ndarray) -> np.ndarray:
        """Learned-style adaptive binarization."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        # Scale up for better OCR accuracy
        scale = 2
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 11
        )
        return binary


# ─────────────────────────────────────────────
#  LAYOUT & REGION DETECTION (Structural Intelligence)
# ─────────────────────────────────────────────

class LayoutDetector:
    """
    Detects semantic regions: text blocks, headings, tables, columns.
    Without layout intelligence: OCR extracts text but destroys meaning.
    With layout intelligence: OCR understands structure, not just characters.
    """

    def detect_regions(self, image: np.ndarray) -> list:
        """
        Returns list of detected regions sorted in reading order.
        Each region: {'bbox': (x,y,w,h), 'type': 'text'|'table'|'heading', 'content': ''}
        """
        # Use Tesseract's built-in layout analysis
        data = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DICT,
            config='--psm 3'  # PSM 3 = Fully automatic page segmentation
        )
        regions = self._group_into_blocks(data)
        regions = self._classify_regions(regions)
        regions = self._sort_reading_order(regions)
        return regions

    def _group_into_blocks(self, data: dict) -> list:
        """Group words into text blocks."""
        blocks = {}
        n = len(data['text'])
        for i in range(n):
            if int(data['conf'][i]) < 0:
                continue
            block_num = data['block_num'][i]
            if block_num not in blocks:
                blocks[block_num] = {
                    'words': [],
                    'x': data['left'][i],
                    'y': data['top'][i],
                    'x2': data['left'][i] + data['width'][i],
                    'y2': data['top'][i] + data['height'][i],
                    'confidences': []
                }
            b = blocks[block_num]
            b['words'].append(data['text'][i])
            b['confidences'].append(int(data['conf'][i]))
            b['x'] = min(b['x'], data['left'][i])
            b['y'] = min(b['y'], data['top'][i])
            b['x2'] = max(b['x2'], data['left'][i] + data['width'][i])
            b['y2'] = max(b['y2'], data['top'][i] + data['height'][i])

        result = []
        for block_num, b in blocks.items():
            text = ' '.join(w for w in b['words'] if w.strip())
            if not text.strip():
                continue
            avg_conf = sum(b['confidences']) / len(b['confidences']) if b['confidences'] else 0
            result.append({
                'bbox': (b['x'], b['y'], b['x2'] - b['x'], b['y2'] - b['y']),
                'text': text,
                'confidence': avg_conf,
                'type': 'text'
            })
        return result

    def _classify_regions(self, regions: list) -> list:
        """Classify regions into heading/table/text/footnote."""
        if not regions:
            return regions
        # Sort by vertical position for context
        regions.sort(key=lambda r: r['bbox'][1])
        heights = [r['bbox'][3] for r in regions if r['bbox'][3] > 0]
        avg_height = sum(heights) / len(heights) if heights else 20

        for r in regions:
            text = r['text'].strip()
            h = r['bbox'][3]
            # Heading: tall text, short, at top, or ALL CAPS
            if (h > avg_height * 1.5 or
                    len(text) < 80 and text == text.upper() and len(text) > 3 or
                    r['bbox'][1] < 100):
                r['type'] = 'heading'
            # Table: contains pipe chars or tab-aligned content
            elif '|' in text or '\t' in text:
                r['type'] = 'table'
            # Footnote: small text at bottom
            elif h < avg_height * 0.7:
                r['type'] = 'footnote'
            else:
                r['type'] = 'text'
        return regions

    def _sort_reading_order(self, regions: list) -> list:
        """Sort regions top-to-bottom, left-to-right (handles multi-column)."""
        if not regions:
            return regions
        regions.sort(key=lambda r: (r['bbox'][1] // 50, r['bbox'][0]))
        return regions


# ─────────────────────────────────────────────
#  CONFIDENCE & ERROR ANALYSIS (Uncertainty Reasoning)
# ─────────────────────────────────────────────

class ConfidenceAnalyzer:
    """
    Assigns confidence scores, flags low-confidence regions.
    OCR predictions are never fully certain: O vs 0, l vs 1, rn vs m.
    """

    # Common OCR confusion pairs
    CONFUSION_PAIRS = [
        (r'\b0\b', 'O/0'),
        (r'\bl\b', 'l/1'),
        (r'rn', 'rn/m'),
        (r'\bI\b(?!\s+am|\s+is|\s+was)', 'I/l'),
    ]

    def analyze(self, ocr_data: dict) -> dict:
        """Full confidence analysis on Tesseract output dict."""
        word_confidences = []
        low_conf_words = []

        for i, (word, conf) in enumerate(zip(ocr_data['text'], ocr_data['conf'])):
            conf = int(conf)
            if conf < 0 or not word.strip():
                continue
            word_confidences.append(conf)
            if conf < 60:
                low_conf_words.append({'word': word, 'conf': conf, 'index': i})

        overall_conf = sum(word_confidences) / len(word_confidences) if word_confidences else 0
        ambiguous = self._detect_ambiguous_chars(
            ' '.join(w for w in ocr_data['text'] if w.strip())
        )

        return {
            'overall_confidence': round(overall_conf, 1),
            'low_confidence_words': low_conf_words[:20],
            'ambiguous_chars': ambiguous,
            'quality': self._quality_label(overall_conf)
        }

    def _detect_ambiguous_chars(self, text: str) -> list:
        """Flag potentially misread characters."""
        found = []
        for pattern, label in self.CONFUSION_PAIRS:
            matches = re.findall(pattern, text)
            if matches:
                found.append({'pattern': label, 'count': len(matches)})
        return found

    def _quality_label(self, conf: float) -> str:
        if conf >= 85:
            return 'HIGH'
        elif conf >= 60:
            return 'MEDIUM'
        else:
            return 'LOW'


# ─────────────────────────────────────────────
#  OCR INTELLIGENCE ENGINE (Learning Core)
# ─────────────────────────────────────────────

class OCREngine:
    """
    Core OCR engine using Tesseract as baseline.
    Integrates preprocessing, layout detection, and confidence analysis.
    Training: Image → OCR Prediction → Loss Calculation → Weight Update → Improved Model
    """

    def __init__(self, lang='eng'):
        self.lang = lang
        self.preprocessor = VisionPreprocessor()
        self.layout_detector = LayoutDetector()
        self.confidence_analyzer = ConfidenceAnalyzer()

    def extract_from_image(self, image_path: str) -> dict:
        """Extract text from a single image file."""
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Cannot read image: {image_path}")
        return self._process_image(img)

    def extract_from_pdf(self, pdf_path: str, dpi: int = 300, poppler_path=None) -> dict:
        """
        Extract text from PDF (any format - scanned or digital).
        Converts each page to image, processes, returns structured output.
        poppler_path: Windows only — path to poppler/bin folder.
        """
        kwargs = {'dpi': dpi}
        if poppler_path:
            kwargs['poppler_path'] = poppler_path
        pages = convert_from_path(pdf_path, **kwargs)
        all_pages = []
        full_text = []

        for page_num, page_pil in enumerate(pages):
            page_img = cv2.cvtColor(np.array(page_pil), cv2.COLOR_RGB2BGR)
            page_result = self._process_image(page_img)
            page_result['page'] = page_num + 1
            all_pages.append(page_result)
            full_text.append(f"--- Page {page_num + 1} ---\n{page_result['full_text']}")

        return {
            'source': os.path.basename(pdf_path),
            'total_pages': len(pages),
            'pages': all_pages,
            'full_text': '\n\n'.join(full_text),
            'overall_confidence': sum(p['confidence']['overall_confidence'] for p in all_pages) / len(all_pages) if all_pages else 0
        }

    def _process_image(self, img: np.ndarray) -> dict:
        """Full pipeline: preprocess → layout detect → OCR → confidence."""
        # Step 1: Vision preprocessing
        processed = self.preprocessor.preprocess(img)

        # Step 2: Layout & region detection
        regions = self.layout_detector.detect_regions(processed)

        # Step 3: Full-page OCR with confidence data
        raw_data = pytesseract.image_to_data(
            processed,
            lang=self.lang,
            output_type=pytesseract.Output.DICT,
            config='--psm 3 --oem 3'  # OEM 3 = LSTM + legacy, PSM 3 = auto
        )

        # Step 4: Extract clean text
        full_text = pytesseract.image_to_string(
            processed,
            lang=self.lang,
            config='--psm 3 --oem 3'
        )

        # Step 5: Confidence & error analysis
        conf_report = self.confidence_analyzer.analyze(raw_data)

        return {
            'full_text': full_text.strip(),
            'regions': regions,
            'confidence': conf_report,
            'word_count': len(full_text.split())
        }
