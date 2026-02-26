"""
Learning Intelligence Module — v5 AI-POWERED (Google Gemini Edition)
=====================================================================
KEY UPGRADES:

1. AI_QUIZ_ENGINE — Uses Google Gemini API for intelligent quiz generation
   • Generates proper 4-option MCQs with real distractors
   • Questions test comprehension, not just text recall
   • Falls back to rule-based if API unavailable

2. AI_LEARN_ENGINE — Uses Google Gemini API for proper learn mode
   • Generates clean, well-explained summaries at each level
   • No OCR garbage in explanations

3. QuizGenerator — FULLY SELECTABLE MCQs
   • Every MCQ guaranteed exactly 4 options
   • Options padded if needed so UI always has 4 choices
   • type field standardized: 'mcq' | 'fill_blank' | 'true_false'
   • options always a list (never undefined/missing)

4. PostOCRTextCleaner embedded here
   • Every function cleans input text before processing
   • Removes OCR artifacts before generating quiz/learn content

SETUP:
   pip install google-generativeai
   Set environment variable: GEMINI_API_KEY=your_key_here
   Get a free API key at: https://aistudio.google.com/app/apikey
"""

import re
import random
import json
import collections
import os

# ══════════════════════════════════════════════════════
#  TEXT CLEANER — runs on all inputs before processing
# ══════════════════════════════════════════════════════

class _TextCleaner:
    """Cleans OCR-extracted text. Used internally by all classes."""

    CHAR_FIXES = [
        (r'(?<=[a-z])rn(?=[a-z])', 'm'),
        (r'\brn\b', 'm'),
        (r'\b0(?=[a-zA-Z])', 'O'),
        (r'(?<=[a-zA-Z])0(?=[a-zA-Z])', 'o'),
    ]

    NOISE_PATTERNS = [
        r'--- ?Page \d+ ?---',
        r'\bPage\s+\d+\s+of\s+\d+\b',
        r'Reprint\s+\d{4}[-]\d{2,4}',
        r'Chap\s*\d+\.indd.*',
        r'\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s*[AP]M',
        r'\bISBN[\s:-]\S+',
        r'[£€¥©®™°§¶†‡]',
    ]

    def clean(self, text: str) -> str:
        # Encoding fixes
        fixes = {
            '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
            '\u2013': '-', '\u2014': ' - ', '\u00a0': ' ', '|': 'I',
        }
        for bad, good in fixes.items():
            text = text.replace(bad, good)

        # Remove noise patterns
        for pat in self.NOISE_PATTERNS:
            text = re.sub(pat, ' ', text, flags=re.IGNORECASE)

        # Remove non-ASCII OCR artifacts
        text = re.sub(r'\b\w*[^\x00-\x7F]\w*\b', ' ', text)

        # Fix line-break splits
        text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)
        text = re.sub(r'([a-z,;])\s*\n\s*([a-z])', r'\1 \2', text)

        # Fix char errors
        for pat, rep in self.CHAR_FIXES:
            text = re.sub(pat, rep, text)

        # Fix spacing
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)
        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)

        # Remove garbage lines (< 40% alpha, too many single-char tokens)
        lines = text.split('\n')
        good_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                good_lines.append('')
                continue
            words = line.split()
            if len(words) < 2:
                continue
            alpha = sum(1 for c in line if c.isalpha())
            if alpha / max(len(line), 1) < 0.4:
                continue
            good_lines.append(line)

        text = '\n'.join(good_lines)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Capitalize sentence starts
        text = re.sub(r'(?<=[.!?]\s)([a-z])', lambda m: m.group().upper(), text)
        if text and text[0].islower():
            text = text[0].upper() + text[1:]

        return text.strip()

    def extract_sentences(self, text: str) -> list:
        clean = self.clean(text)
        raw = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'(])', clean)
        result = []
        for s in raw:
            s = s.strip()
            words = s.split()
            if len(words) < 6:
                continue
            alpha = sum(1 for c in s if c.isalpha())
            if alpha / max(len(s), 1) < 0.5:
                continue
            result.append(s)
        return result


_cleaner = _TextCleaner()


# ══════════════════════════════════════════════════════
#  AI ENGINE — Google Gemini API integration
#  Replaces Anthropic Claude API
#  Get free API key: https://aistudio.google.com/app/apikey
# ══════════════════════════════════════════════════════

class AIEngine:
    """
    Calls the Google Gemini API to generate quiz questions and
    learning content from the document text.

    Install:  pip install google-generativeai
    API key:  Set GEMINI_API_KEY environment variable
    Free key: https://aistudio.google.com/app/apikey

    Gemini 1.5 Flash is used by default — it's fast and free-tier friendly.
    Falls back gracefully to rule-based generation if API is unavailable.
    """

    # ── Model selection ──────────────────────────────────────────
    # "gemini-1.5-flash"  → fast, generous free quota (recommended)
    # "gemini-1.5-pro"    → more powerful, lower free quota
    # "gemini-2.0-flash"  → latest flash model (if available on your key)
    MODEL = "gemini-1.5-flash"
    GEMINI_API_KEY = 'AIzaSyCLJ9Rx8fH_6T_yz7zQNj-qkamGbKzU1NI'

    MAX_TOKENS = 2000

    def __init__(self):
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        try:
            import google.generativeai  # noqa: F401
            key = os.environ.get('GEMINI_API_KEY', '')
            return bool(key)
        except ImportError:
            return False

    def _call(self, system_prompt: str, user_prompt: str) -> str:
        """
        Make a single Gemini API call.
        Returns the response text or an empty string on failure.

        Gemini combines system + user prompt into a single prompt string
        since the google-generativeai SDK handles system instructions
        separately only in newer versions. We prepend the system prompt
        as a preamble for maximum compatibility.
        """
        try:
            import google.generativeai as genai

            genai.configure(api_key=os.environ.get('GEMINI_API_KEY', ''))

            model = genai.GenerativeModel(
                model_name=self.MODEL,
                # system_instruction is supported in google-generativeai >= 0.5
                # If you have an older version, the preamble fallback below handles it
                system_instruction=system_prompt,
            )

            response = model.generate_content(
                user_prompt,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=self.MAX_TOKENS,
                    temperature=0.4,   # Lower = more deterministic/factual
                ),
            )

            # Extract text safely
            if response and response.text:
                return response.text
            return ''

        except TypeError:
            # Older SDK versions don't support system_instruction in constructor
            # Fall back to prepending system prompt in the user message
            try:
                import google.generativeai as genai
                genai.configure(api_key=os.environ.get('GEMINI_API_KEY', ''))
                model = genai.GenerativeModel(model_name=self.MODEL)
                combined_prompt = f"{system_prompt}\n\n{user_prompt}"
                response = model.generate_content(combined_prompt)
                return response.text if response and response.text else ''
            except Exception:
                return ''

        except Exception:
            return ''

    def generate_quiz(self, clean_text: str, level: str, n: int = 8) -> list:
        """
        Generate quiz questions using Gemini.
        Returns list of question dicts — same format as rule-based generator.
        Falls back to empty list if API unavailable.
        """
        if not self._available:
            return []

        # Trim text to fit in prompt (keep first 3000 chars)
        snippet = clean_text[:3000]

        system = (
            "You are a quiz generator. Generate quiz questions from the provided text. "
            "Return ONLY a JSON array — no explanation, no markdown fences, just the raw JSON array. "
            "Each question must have these fields: "
            "type (must be exactly 'mcq', 'fill_blank', or 'true_false'), "
            "question (string), "
            "options (array of exactly 4 strings — REQUIRED for mcq, empty array [] for others), "
            "answer (string matching one of the options for mcq), "
            "explanation (string), "
            "difficulty (string: 'beginner', 'intermediate', or 'advanced'), "
            "topic (string). "
            "For MCQ: always provide exactly 4 options. One correct, three plausible but wrong. "
            "For fill_blank: question contains ___________ where the answer goes. "
            "For true_false: options should be ['True', 'False']."
        )

        user = (
            f"Generate {n} quiz questions at {level} level from this text. "
            f"Mix of mcq (majority), fill_blank, and true_false. "
            f"For MCQ always provide EXACTLY 4 options.\n\n"
            f"TEXT:\n{snippet}"
        )

        raw = self._call(system, user)
        if not raw:
            return []

        # Parse JSON — strip accidental markdown fences Gemini sometimes adds
        try:
            raw = re.sub(r'^```(?:json)?\s*', '', raw.strip())
            raw = re.sub(r'\s*```$', '', raw.strip())
            questions = json.loads(raw)
            if not isinstance(questions, list):
                return []

            # Validate and normalize each question
            valid = []
            for q in questions:
                if not isinstance(q, dict):
                    continue
                qtype = q.get('type', 'mcq')
                if qtype not in ('mcq', 'fill_blank', 'true_false'):
                    qtype = 'mcq'

                options = q.get('options', [])
                if not isinstance(options, list):
                    options = []

                # Ensure MCQ always has exactly 4 options
                if qtype == 'mcq':
                    options = _ensure_4_options(options, q.get('answer', ''))

                # True/False always has exactly 2 options
                if qtype == 'true_false':
                    options = ['True', 'False']

                valid.append({
                    'type':        qtype,
                    'question':    str(q.get('question', '')),
                    'options':     options,
                    'answer':      str(q.get('answer', '')),
                    'explanation': str(q.get('explanation', '')),
                    'difficulty':  str(q.get('difficulty', level)),
                    'topic':       str(q.get('topic', 'document content')),
                })

            return valid

        except (json.JSONDecodeError, TypeError, KeyError):
            return []

    def generate_learn_content(self, clean_text: str, level: str) -> dict:
        """
        Generate structured learning content using Gemini.
        Returns dict with summary, key_points, glossary, simplified.
        Falls back to empty dict if unavailable.
        """
        if not self._available:
            return {}

        snippet = clean_text[:3000]
        level_desc = {
            'beginner':     'Use very simple language, short sentences, everyday examples. Avoid jargon.',
            'intermediate': 'Clear language, explain technical terms, moderate detail.',
            'advanced':     'Full technical depth, precise terminology, no over-simplification.'
        }.get(level, 'intermediate level')

        system = (
            "You are an adaptive learning content generator. "
            "Return ONLY a JSON object — no markdown, no explanation. "
            "The JSON must have these fields: "
            "summary (string: 3-5 sentence overview), "
            "key_points (array of 5-7 strings, each a key fact or insight), "
            "glossary (array of objects with 'term' and 'definition' fields), "
            "simplified (string: 2-3 sentence plain-language version for beginners). "
        )

        user = (
            f"Create learning content at {level} level ({level_desc}) "
            f"from this text:\n\n{snippet}"
        )

        raw = self._call(system, user)
        if not raw:
            return {}

        try:
            raw = re.sub(r'^```(?:json)?\s*', '', raw.strip())
            raw = re.sub(r'\s*```$', '', raw.strip())
            result = json.loads(raw)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, TypeError):
            pass
        return {}


_ai = AIEngine()


# ══════════════════════════════════════════════════════
#  HELPER — ensure MCQ always has exactly 4 options
# ══════════════════════════════════════════════════════

_FILLER_OPTIONS = [
    "None of the above",
    "Cannot be determined from the text",
    "All of the above",
    "The text does not specify this",
]

def _ensure_4_options(options: list, correct: str) -> list:
    """
    Guarantee exactly 4 options for MCQ.
    - If > 4: keep correct + 3 random wrong ones
    - If < 4: pad with filler options
    - Always includes correct answer
    """
    if not isinstance(options, list):
        options = []

    # Make sure correct answer is in the list
    if correct and correct not in options:
        options = [correct] + options

    # Remove duplicates
    seen = set()
    unique = []
    for o in options:
        key = str(o).strip().lower()[:60]
        if key not in seen:
            seen.add(key)
            unique.append(o)
    options = unique

    # Trim to 4 keeping correct answer
    if len(options) > 4:
        wrong = [o for o in options if o != correct]
        random.shuffle(wrong)
        options = [correct] + wrong[:3]

    # Pad to 4
    filler_idx = 0
    while len(options) < 4:
        filler = _FILLER_OPTIONS[filler_idx % len(_FILLER_OPTIONS)]
        if filler not in options:
            options.append(filler)
        filler_idx += 1

    random.shuffle(options)
    return options[:4]


# ══════════════════════════════════════════════════════
#  PDF GENERATOR
# ══════════════════════════════════════════════════════

def generate_pdf(title: str, sections: list, output_path: str) -> str:
    """Generate a formatted PDF using ReportLab."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.colors import HexColor
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                     HRFlowable)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        rightMargin=22*mm, leftMargin=22*mm,
        topMargin=20*mm, bottomMargin=20*mm
    )
    styles = getSampleStyleSheet()
    S = {
        'title':      ParagraphStyle('T',   parent=styles['Title'],    fontSize=20,
                        textColor=HexColor('#4c1d95'), spaceAfter=4,
                        fontName='Helvetica-Bold', alignment=TA_CENTER),
        'subtitle':   ParagraphStyle('Sub', parent=styles['Normal'],   fontSize=10,
                        textColor=HexColor('#6b7280'), spaceAfter=16, alignment=TA_CENTER),
        'heading':    ParagraphStyle('H',   parent=styles['Heading2'], fontSize=13,
                        textColor=HexColor('#7c3aed'), spaceBefore=14, spaceAfter=6,
                        fontName='Helvetica-Bold'),
        'subheading': ParagraphStyle('SH',  parent=styles['Normal'],   fontSize=11,
                        textColor=HexColor('#0891b2'), spaceBefore=8, spaceAfter=4,
                        fontName='Helvetica-Bold'),
        'body':       ParagraphStyle('B',   parent=styles['Normal'],   fontSize=11,
                        textColor=HexColor('#111827'), spaceAfter=7, leading=18,
                        alignment=TA_JUSTIFY),
        'term':       ParagraphStyle('Trm', parent=styles['Normal'],   fontSize=11,
                        textColor=HexColor('#065f46'), spaceBefore=5, spaceAfter=2,
                        fontName='Helvetica-Bold'),
        'definition': ParagraphStyle('Def', parent=styles['Normal'],   fontSize=10.5,
                        textColor=HexColor('#374151'), spaceAfter=8, leftIndent=14,
                        leading=16),
        'bullet':     ParagraphStyle('Bul', parent=styles['Normal'],   fontSize=11,
                        textColor=HexColor('#111827'), spaceAfter=5, leftIndent=18,
                        leading=16),
        'quote':      ParagraphStyle('Q',   parent=styles['Normal'],   fontSize=11,
                        textColor=HexColor('#1e3a5f'), spaceAfter=8, leftIndent=20,
                        rightIndent=20, leading=18, fontName='Helvetica-Oblique'),
        'note':       ParagraphStyle('N',   parent=styles['Normal'],   fontSize=9.5,
                        textColor=HexColor('#6b7280'), spaceAfter=6, leftIndent=14),
    }

    def safe(t):
        if not t: return ''
        return (str(t).replace('&','&amp;').replace('<','&lt;')
                      .replace('>','&gt;').replace('"','&quot;'))

    story = []
    story.append(Paragraph(safe(title), S['title']))
    story.append(HRFlowable(width='100%', thickness=1.5, color=HexColor('#7c3aed')))
    story.append(Spacer(1, 5*mm))

    for sec in sections:
        stype = sec.get('type', 'body')
        text  = sec.get('text', '').strip()
        sub   = sec.get('sub', '').strip()
        if not text and stype not in ('spacer', 'hr'):
            continue
        if stype == 'subtitle':     story.append(Paragraph(safe(text), S['subtitle']))
        elif stype == 'heading':
            story.append(Spacer(1, 2*mm))
            story.append(Paragraph(safe(text), S['heading']))
        elif stype == 'subheading': story.append(Paragraph(safe(text), S['subheading']))
        elif stype == 'body':       story.append(Paragraph(safe(text), S['body']))
        elif stype == 'term':
            story.append(Paragraph(safe(text), S['term']))
            if sub: story.append(Paragraph(safe(sub), S['definition']))
        elif stype == 'bullet':     story.append(Paragraph(f'• {safe(text)}', S['bullet']))
        elif stype == 'quote':      story.append(Paragraph(f'"{safe(text)}"', S['quote']))
        elif stype == 'note':       story.append(Paragraph(safe(text), S['note']))
        elif stype == 'spacer':     story.append(Spacer(1, 4*mm))
        elif stype == 'hr':
            story.append(Spacer(1, 2*mm))
            story.append(HRFlowable(width='100%', thickness=0.5, color=HexColor('#d1d5db')))
            story.append(Spacer(1, 2*mm))

    doc.build(story)
    return output_path


# ══════════════════════════════════════════════════════
#  CONCEPT EXTRACTOR
# ══════════════════════════════════════════════════════

class ConceptExtractor:
    """Extracts key concepts, terms, and vocabulary from any document."""

    BASIC_WORDS = set([
        'the','a','an','is','was','are','were','be','been','being','have',
        'has','had','do','does','did','will','would','could','should','may',
        'might','and','or','but','not','with','this','that','from','by','as',
        'into','at','on','in','to','for','of','up','down','out','off','over',
        'it','its','we','our','you','your','he','she','they','their','i',
        'my','me','him','her','us','them','what','which','who','how','when',
        'where','why','all','each','every','some','any','no','more','most',
        'other','also','just','very','can','get','use','used','using','make',
        'made','take','taken','give','given','go','goes','come','comes','see',
        'seen','know','known','think','thought','want','need','look','work',
        'way','day','time','year','new','old','large','small','high','low',
        'different','important','following','based','between','including',
        'without','through','during','before','after','both','only','same',
        'than','too','such','then','these','those','here','there','about',
        'said','told','asked','replied','went','came','took','gave','knew',
        'even','back','still','like','upon','been','whom','whose','shall',
        'must','done','going','being','having','well','good','bad','little',
        'much','many','long','right','great','first','last','next','people',
        'thing','things','something','anything','nothing','everything'
    ])

    ACRONYM_RE  = re.compile(r'\b([A-Z]{2,8})\b')
    TECHNICAL_RE = re.compile(
        r'\b([a-z]+(?:tion|ization|isation|ology|ometry|ysis|ithm|ecture'
        r'|ework|ence|ance|ility|icity|ivity|ment|ular|ified|ifying))\b',
        re.IGNORECASE)

    def extract(self, text: str) -> dict:
        clean = _cleaner.clean(text)
        return {
            'acronyms':          self._find_acronyms(clean),
            'technical_terms':   self._find_technical_terms(clean),
            'difficult_words':   self._find_difficult_words(clean),
            'concepts':          self._find_key_concepts(clean),
            'key_sentences':     _cleaner.extract_sentences(clean)[:60],
            'people':            self._find_people(clean),
            'vocabulary_ordered': self._build_ordered(
                clean,
                self._find_acronyms(clean),
                self._find_technical_terms(clean),
                self._find_difficult_words(clean)
            )
        }

    def _find_people(self, text: str) -> list:
        names = re.findall(r'\b([A-Z][a-z]{2,})\b', text)
        non_names = {
            'The','He','She','It','We','You','They','But','And','So','As',
            'If','When','Then','That','This','His','Her','My','All','Each',
            'One','Now','For','Not','With','From','By','True','False','Page',
            'Chapter','Summer','Morning','Evening','Well','Good','Little',
            'Great','First','Last','Next','Some','Also','Just','Even','Back'
        }
        freq = collections.Counter(n for n in names if n not in non_names)
        return [{'name': n, 'count': c} for n, c in freq.most_common(8) if c >= 2]

    def _find_acronyms(self, text: str) -> list:
        seen, results = set(), []
        for m in self.ACRONYM_RE.finditer(text):
            term = m.group(1)
            if term in seen or len(term) < 2: continue
            seen.add(term)
            start = max(0, m.start() - 60)
            ctx = text[start:min(len(text), m.end()+60)].replace('\n',' ').strip()
            results.append({'term': term, 'context': ctx, 'type': 'acronym'})
        return results[:20]

    def _find_technical_terms(self, text: str) -> list:
        words = re.findall(r'\b[a-zA-Z]{6,}\b', text)
        freq = collections.Counter(w.lower() for w in words)
        results, seen = [], set()
        for word, count in freq.most_common(50):
            if word in self.BASIC_WORDS or word in seen: continue
            if self.TECHNICAL_RE.match(word):
                seen.add(word)
                results.append({'term': word, 'frequency': count,
                                 'difficulty': self._score(word), 'type': 'technical'})
        return sorted(results, key=lambda x: x['difficulty'], reverse=True)[:20]

    def _find_difficult_words(self, text: str) -> list:
        words = re.findall(r'\b[a-zA-Z]{7,}\b', text)
        freq = collections.Counter(w.lower() for w in words)
        results, seen = [], set()
        for word, count in freq.most_common(60):
            if word in self.BASIC_WORDS or word in seen: continue
            seen.add(word)
            sc = self._score(word)
            if sc >= 2:
                results.append({'term': word, 'frequency': count,
                                 'difficulty': sc, 'type': 'vocabulary'})
        return sorted(results, key=lambda x: x['difficulty'], reverse=True)[:20]

    def _find_key_concepts(self, text: str) -> list:
        pattern = re.compile(r'\b([A-Z][a-z]+ (?:[A-Z][a-z]+ )*(?:[A-Z][a-z]+|[A-Z]+))\b')
        seen, results = set(), []
        for m in pattern.finditer(text):
            phrase = m.group(0).strip()
            if phrase.lower() in seen or len(phrase) < 6: continue
            seen.add(phrase.lower())
            results.append({'term': phrase, 'type': 'concept'})
        return results[:15]

    def _score(self, word: str) -> int:
        score = 0
        if len(word) >= 12: score += 3
        elif len(word) >= 9: score += 2
        elif len(word) >= 7: score += 1
        for suf in ['ification','ization','ography','ology','ysis','ithm','ecture']:
            if word.endswith(suf):
                score += 2
                break
        return score

    def _build_ordered(self, text, acronyms, technical, difficult) -> list:
        all_terms = {}
        for item in acronyms:   all_terms[item['term'].lower()] = item
        for item in technical:  all_terms[item['term'].lower()] = item
        for item in difficult:  all_terms[item['term'].lower()] = item
        ordered, seen = [], set()
        for w in re.findall(r'\b[A-Za-z]{3,}\b', text):
            key = w.lower()
            if key in all_terms and key not in seen:
                seen.add(key)
                ordered.append(all_terms[key])
        return ordered[:30]


# ══════════════════════════════════════════════════════
#  TEXT EXPANDER — Learn Mode
# ══════════════════════════════════════════════════════

class TextExpander:
    """
    Generates learning content at beginner / intermediate / advanced level.
    v5: Uses Gemini AI for richer explanations when available, clean rule-based fallback.
    """

    TERM_KNOWLEDGE = {
        'OCR':    {'full': 'Optical Character Recognition',
                   'beginner': 'A technology that reads text from images, like scanning a page to make it editable.',
                   'intermediate': 'Converts images of text into machine-readable characters using pattern recognition.',
                   'advanced': 'Image-to-text pipeline: binarization → segmentation → feature extraction → classification.'},
        'CNN':    {'full': 'Convolutional Neural Network',
                   'beginner': 'An AI that recognizes patterns in images, inspired by how eyes work.',
                   'intermediate': 'Deep learning architecture using filter kernels to extract spatial features.',
                   'advanced': 'Feedforward network with learned convolutional filters, pooling, and FC layers.'},
        'NLP':    {'full': 'Natural Language Processing',
                   'beginner': 'Teaching computers to understand human language.',
                   'intermediate': 'Computational analysis and generation of human language.',
                   'advanced': 'Combines linguistics and ML for tokenization, parsing, NER, and language modeling.'},
        'LSTM':   {'full': 'Long Short-Term Memory',
                   'beginner': 'An AI that remembers earlier parts of text to understand full meaning.',
                   'intermediate': 'Recurrent neural network variant that preserves long-range dependencies.',
                   'advanced': 'RNN with input/forget/output gates controlling memory cell information flow.'},
        'CLAHE':  {'full': 'Contrast Limited Adaptive Histogram Equalization',
                   'beginner': 'Makes dark images clearer without washing out the bright parts.',
                   'intermediate': 'Local contrast enhancement that handles uneven illumination.',
                   'advanced': 'Adaptive HE variant that clips peaks to limit noise amplification.'},
        'CER':    {'full': 'Character Error Rate',
                   'beginner': 'Percentage of individual letters the OCR got wrong.',
                   'intermediate': 'Character-level edit distance divided by reference length.',
                   'advanced': 'Levenshtein distance normalized by reference length.'},
        'WER':    {'full': 'Word Error Rate',
                   'beginner': 'Percentage of whole words the OCR got wrong.',
                   'intermediate': 'Word-level edit distance normalized by reference word count.',
                   'advanced': '(substitutions + deletions + insertions) / reference words.'},
        'algorithm': {
                   'beginner': 'A step-by-step set of instructions a computer follows to solve a problem.',
                   'intermediate': 'A defined sequence of operations for solving a computational problem.',
                   'advanced': 'Formal procedure with defined complexity: O(n), O(log n), etc.'},
        'pipeline': {
                   'beginner': 'A chain of steps where each step feeds into the next, like an assembly line.',
                   'intermediate': 'Sequential processing chain where data flows through transformation stages.',
                   'advanced': 'Directed graph of processing nodes optimized for throughput.'},
        'binarization': {
                   'beginner': 'Converting a grey image to pure black-and-white.',
                   'intermediate': 'Thresholding operation converting grayscale to binary values.',
                   'advanced': 'Adaptive thresholding: Otsu, Sauvola, or Niblack methods.'},
        'confidence': {
                   'beginner': 'How sure the AI is about its answer — 95% means almost certain.',
                   'intermediate': 'Probability score the model assigns to its predictions.',
                   'advanced': 'Posterior from softmax; calibration aligns confidence with empirical accuracy.'},
        'honesty': {
                   'beginner': 'Being truthful and not deceiving others.',
                   'intermediate': 'A moral principle of truthfulness and integrity.',
                   'advanced': 'An ethical virtue central to trust-based social and institutional relationships.'},
        'integrity': {
                   'beginner': 'Always doing the right thing, even when nobody is watching.',
                   'intermediate': 'Adherence to moral and ethical principles.',
                   'advanced': 'Coherent alignment between stated values and observable behaviour.'},
    }

    def expand(self, text: str, level: str, concepts_data: dict) -> dict:
        """Generate learn-mode content. Uses Gemini AI if available."""
        clean = _cleaner.clean(text)

        # Try AI-powered content first
        ai_content = _ai.generate_learn_content(clean, level)

        glossary    = self._build_glossary(concepts_data, level)
        pre_reading = self._build_pre_reading(concepts_data, level)

        if ai_content:
            summary    = ai_content.get('summary', '')
            key_points = ai_content.get('key_points', [])
            simplified = ai_content.get('simplified', '')
            ai_glossary = ai_content.get('glossary', [])
            # Merge AI glossary with rule-based glossary
            for g in ai_glossary:
                if isinstance(g, dict) and 'term' in g and 'definition' in g:
                    if not any(x['term'].lower() == g['term'].lower() for x in glossary):
                        glossary.append({
                            'term': g['term'],
                            'full_form': '',
                            'explanation': g['definition'],
                            'type': 'ai_generated'
                        })
            annotated = summary if summary else self._annotate_text(clean, glossary, level)
        else:
            annotated  = self._annotate_text(clean, glossary, level)
            simplified = self._simplify_if_needed(clean, level)
            key_points = []
            summary    = ''

        return {
            'annotated_text':        annotated,
            'summary':               summary,
            'key_points':            key_points,
            'glossary':              glossary,
            'pre_reading':           pre_reading,
            'simplified_summary':    simplified,
            'level':                 level,
            'total_terms_explained': len(glossary),
            'ai_powered':            bool(ai_content),
        }

    def expand_to_pdf(self, text: str, level: str, concepts_data: dict,
                       output_path: str) -> str:
        """Generate full annotated learning PDF."""
        clean       = _cleaner.clean(text)
        content     = self.expand(clean, level, concepts_data)
        glossary    = content['glossary']
        pre_reading = content['pre_reading']
        key_points  = content.get('key_points', [])
        summary     = content.get('summary', '')
        annotated   = content['annotated_text']
        simplified  = content['simplified_summary']
        ai_powered  = content.get('ai_powered', False)

        level_label = {
            'beginner':     '🌱 Beginner Level',
            'intermediate': '📘 Intermediate Level',
            'advanced':     '🚀 Advanced Level'
        }.get(level, level.title())

        sections = []
        badge = ' ✨ AI-Enhanced (Gemini)' if ai_powered else ''
        sections.append({'type': 'subtitle',
                          'text': f'Adaptive Learning Document — {level_label}{badge}'})

        if pre_reading:
            sections.append({'type': 'heading', 'text': '📚 Pre-Reading — Know These First'})
            sections.append({'type': 'note',
                              'text': 'Understand these terms before reading the main content.'})
            for p in pre_reading[:8]:
                sections.append({'type': 'term', 'text': f"📌 {p['term']}",
                                  'sub': p['explanation']})
            sections.append({'type': 'hr', 'text': ''})

        if key_points:
            sections.append({'type': 'heading', 'text': '🎯 Key Points'})
            for pt in key_points[:7]:
                sections.append({'type': 'bullet', 'text': str(pt)})
            sections.append({'type': 'hr', 'text': ''})

        sections.append({'type': 'heading', 'text': '📄 Document Content — Annotated'})
        sections.append({'type': 'note',
                          'text': f'Key terms annotated at {level_label}.'})
        sections.append({'type': 'spacer', 'text': ''})

        if summary:
            sections.append({'type': 'body', 'text': summary})
        else:
            for para in annotated.split('\n\n'):
                para = para.strip()
                if para:
                    sections.append({'type': 'body', 'text': para})

        if simplified and level == 'beginner':
            sections.append({'type': 'hr', 'text': ''})
            sections.append({'type': 'heading', 'text': '🌱 Plain-Language Summary'})
            sections.append({'type': 'note', 'text': 'The key ideas in simple words.'})
            for sent in simplified.split('. '):
                sent = sent.strip()
                if sent and len(sent) > 15:
                    sections.append({'type': 'bullet', 'text': sent})

        if glossary:
            sections.append({'type': 'hr', 'text': ''})
            sections.append({'type': 'heading',
                              'text': f'📖 Glossary — {len(glossary)} Terms Explained'})
            sections.append({'type': 'note',
                              'text': f'All terms explained at the {level_label}.'})
            for g in glossary:
                full = f" ({g['full_form']})" if g.get('full_form') else ''
                sections.append({'type': 'term', 'text': f"{g['term']}{full}",
                                  'sub': g.get('explanation', '')})

        return generate_pdf('IntelliDoc — Learning Document', sections, output_path)

    def shrink_to_pdf(self, text: str, output_path: str, ratio: float = 0.3) -> str:
        """Generate a condensed summary PDF."""
        from heapq import nlargest
        clean = _cleaner.clean(text)

        ai_content = _ai.generate_learn_content(clean, 'intermediate')

        stop = set(['a','an','the','is','was','are','were','be','been','have','has',
                    'had','do','does','did','will','would','could','should','and',
                    'or','but','not','with','this','that','from','by','as','into',
                    'at','on','in','to','for','of','it','its','we','you','he','she',
                    'they','them','their','our','said','just','very','some','all',
                    'also','even','back','still','more','most'])

        sentences = _cleaner.extract_sentences(clean)
        if not sentences:
            sentences = [clean[:500]]

        all_words = [w.lower() for s in sentences for w in re.findall(r'\b[a-zA-Z]+\b', s)]
        freq = collections.Counter(t for t in all_words if t not in stop and len(t) > 3)

        scores = {}
        for i, s in enumerate(sentences):
            toks = re.findall(r'\b[a-zA-Z]+\b', s.lower())
            sc = sum(freq.get(t, 0) for t in toks if t not in stop)
            if toks: sc /= len(toks)
            if i == 0: sc *= 1.7
            elif i <= 2: sc *= 1.3
            elif i == len(sentences)-1: sc *= 1.2
            if len(toks) < 5: sc *= 0.4
            scores[i] = sc

        n = max(4, min(10, int(len(sentences) * ratio)))
        top_idx = sorted(nlargest(n, scores, key=scores.get))
        summary_sents = [sentences[i] for i in top_idx]

        names = re.findall(r'\b([A-Z][a-z]{2,})\b', clean)
        non = {'The','He','She','It','We','You','They','But','And','So','As',
               'If','When','Then','That','This','His','Her','My','All','Each'}
        nfreq = collections.Counter(nm for nm in names if nm not in non)
        chars = [nm for nm, _ in nfreq.most_common(5) if _ >= 2]
        kw = [w for w, _ in freq.most_common(10)]

        sections = [
            {'type': 'subtitle',
             'text': f'Condensed Summary — {len(summary_sents)} key sentences'},
            {'type': 'heading', 'text': '📋 Summary'},
        ]

        if ai_content and ai_content.get('summary'):
            sections.append({'type': 'body', 'text': ai_content['summary']})
            sections.append({'type': 'hr', 'text': ''})
            sections.append({'type': 'heading', 'text': '🎯 Key Points'})
            for pt in ai_content.get('key_points', [])[:6]:
                sections.append({'type': 'bullet', 'text': str(pt)})
        else:
            for sent in summary_sents:
                sections.append({'type': 'body', 'text': sent})
            sections.append({'type': 'hr', 'text': ''})
            sections.append({'type': 'heading', 'text': '🔑 Key Points'})
            for sent in summary_sents[:6]:
                sections.append({'type': 'bullet', 'text': sent})

        if chars:
            sections.append({'type': 'hr', 'text': ''})
            sections.append({'type': 'heading', 'text': '👥 Key Figures / Characters'})
            for c in chars:
                sections.append({'type': 'bullet', 'text': c})

        if kw:
            sections.append({'type': 'hr', 'text': ''})
            sections.append({'type': 'heading', 'text': '🏷️ Key Terms'})
            sections.append({'type': 'body', 'text': ', '.join(kw)})

        return generate_pdf('IntelliDoc — Document Summary', sections, output_path)

    def _build_glossary(self, concepts_data: dict, level: str) -> list:
        glossary, seen = [], set()
        kb = self.TERM_KNOWLEDGE

        for item in concepts_data.get('acronyms', []):
            term = item['term']
            if term in seen: continue
            seen.add(term)
            info = kb.get(term, {})
            glossary.append({
                'term': term,
                'full_form': info.get('full', ''),
                'explanation': info.get(level, info.get('intermediate',
                               f'Acronym found in document: {term}')),
                'context': item.get('context', ''),
                'type': 'acronym'
            })

        for item in concepts_data.get('technical_terms', [])[:12]:
            term = item['term'].lower()
            if term in seen: continue
            seen.add(term)
            info = kb.get(term, {})
            glossary.append({
                'term': term,
                'full_form': info.get('full', ''),
                'explanation': info.get(level, info.get('intermediate',
                               f'Technical term appearing {item.get("frequency",1)}x in document.')),
                'context': '',
                'type': 'technical'
            })

        for item in concepts_data.get('difficult_words', [])[:8]:
            term = item['term'].lower()
            if term in seen: continue
            seen.add(term)
            info = kb.get(term, {})
            glossary.append({
                'term': term,
                'full_form': '',
                'explanation': info.get(level, info.get('intermediate',
                               'Important vocabulary word in this document.')),
                'context': '',
                'type': 'vocabulary'
            })

        return glossary[:25]

    def _annotate_text(self, text: str, glossary: list, level: str) -> str:
        if level == 'beginner':
            annotated = text
            for g in glossary[:10]:
                term = g['term']
                exp  = g['explanation']
                short = exp[:70] + '...' if len(exp) > 70 else exp
                pat  = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
                annotated = pat.sub(term + f' [{short}]', annotated, count=1)
            return annotated
        elif level == 'intermediate':
            annotated = text
            for g in glossary[:8]:
                if g.get('full_form'):
                    term = g['term']
                    pat  = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
                    annotated = pat.sub(f'{term} ({g["full_form"]})', annotated, count=1)
            return annotated
        else:
            annotated = text
            for g in glossary[:5]:
                if g.get('full_form'):
                    term = g['term']
                    annotated = re.sub(r'\b' + re.escape(term) + r'\b',
                                       f'{term} [{g["full_form"]}]', annotated, count=1,
                                       flags=re.IGNORECASE)
            return annotated

    def _build_pre_reading(self, concepts_data: dict, level: str) -> list:
        if level == 'advanced':
            return []
        pre, seen = [], set()
        kb = self.TERM_KNOWLEDGE
        for item in concepts_data.get('acronyms', []):
            term = item['term']
            if term in kb and term not in seen:
                seen.add(term)
                info = kb[term]
                pre.append({
                    'term': term,
                    'why_needed': 'Appears frequently in the document.',
                    'explanation': info.get('beginner' if level == 'beginner' else 'intermediate', '')
                })
            if len(pre) >= 8:
                break
        return pre

    def _simplify_if_needed(self, text: str, level: str) -> str:
        if level != 'beginner':
            return ''
        sentences = _cleaner.extract_sentences(text)
        simple = [s for s in sentences if 8 <= len(s.split()) <= 30 and s.count(',') <= 2]
        return ' '.join(simple[:8])


# ══════════════════════════════════════════════════════
#  QUIZ GENERATOR — v5 AI-POWERED + ALWAYS SELECTABLE
# ══════════════════════════════════════════════════════

class QuizGenerator:
    """
    Generates quiz questions with guaranteed selectable MCQs.
    Uses Google Gemini AI for better questions when available.
    """

    QUESTION_WORDS = ['who', 'what', 'where', 'when', 'why', 'how', 'which']

    def generate(self, text: str, concepts_data: dict, level: str,
                 n_questions: int = 8) -> list:
        clean = _cleaner.clean(text)
        key_sentences = concepts_data.get('key_sentences',
                                           _cleaner.extract_sentences(clean))
        people = concepts_data.get('people', [])

        # ── Try AI generation first ──────────────────────────────
        ai_questions = _ai.generate_quiz(clean, level, n_questions)

        if ai_questions and len(ai_questions) >= max(3, n_questions // 2):
            questions = ai_questions
        else:
            questions = []
            questions.extend(self._fill_blank_from_text(key_sentences, level))
            questions.extend(self._true_false_from_text(key_sentences, level))
            questions.extend(self._who_what_questions(key_sentences, people, level))
            questions.extend(self._fact_mcq(key_sentences, level))
            questions.extend(self._acronym_questions(concepts_data))
            questions.extend(ai_questions)

        # ── Deduplicate ──────────────────────────────────────────
        seen, unique = set(), []
        for q in questions:
            key = q.get('question', '')[:60].lower()
            if key not in seen and len(key) > 8:
                seen.add(key)
                unique.append(q)

        # ── Normalize EVERY question ─────────────────────────────
        normalized = [self._normalize_question(q, level) for q in unique]

        # ── Shuffle and assign IDs ───────────────────────────────
        random.shuffle(normalized)
        selected = normalized[:n_questions]
        for i, q in enumerate(selected):
            q['id'] = i + 1

        return selected

    def _normalize_question(self, q: dict, level: str) -> dict:
        qtype = q.get('type', 'mcq')
        if qtype not in ('mcq', 'fill_blank', 'true_false'):
            qtype = 'mcq'

        question_text = str(q.get('question', 'Question not available'))
        answer        = str(q.get('answer', ''))
        explanation   = str(q.get('explanation', ''))
        difficulty    = str(q.get('difficulty', level))
        topic         = str(q.get('topic', 'document content'))
        options       = q.get('options', [])
        if not isinstance(options, list):
            options = []

        if qtype == 'mcq':
            options = _ensure_4_options(options, answer)
        elif qtype == 'true_false':
            options = ['True', 'False']
            if answer not in ('True', 'False'):
                answer = 'True'
        elif qtype == 'fill_blank':
            options = []

        return {
            'type':        qtype,
            'question':    question_text,
            'options':     options,
            'answer':      answer,
            'explanation': explanation,
            'difficulty':  difficulty,
            'topic':       topic,
            'hint':        q.get('hint', ''),
        }

    # ── Rule-based question generators (fallback) ────────────────

    def _fill_blank_from_text(self, sentences: list, level: str) -> list:
        questions = []
        skip_words = {
            'the','a','an','is','was','are','were','be','been','and','or',
            'but','not','with','this','that','from','by','as','it','he',
            'she','they','we','i','his','her','their','our','you','said',
            'had','have','has','did','do','does','will','would','could',
            'should','very','just','also','even','then','when','where',
            'what','who','how','all','some','any','no','more','much',
            'many','few','each','every','both','other','another','into',
            'upon','about','after','before','through','during'
        }
        good = [s for s in sentences if len(s.split()) >= 10]
        random.shuffle(good)

        for sent in good[:20]:
            if len(questions) >= 4:
                break
            words = sent.split()
            candidates = []
            for i, word in enumerate(words):
                cw = re.sub(r'[^a-zA-Z0-9]', '', word)
                if not cw or len(cw) < 3: continue
                if cw.lower() in skip_words: continue
                if word.endswith("'s") or word.endswith("s'"): continue
                score = 0
                if cw[0].isupper() and i > 0: score += 3
                if len(cw) >= 5: score += 2
                if cw.isdigit(): score += 2
                if score >= 2:
                    candidates.append((i, word, cw, score))
            if not candidates:
                continue
            candidates.sort(key=lambda x: x[3], reverse=True)
            idx, _, ans, _ = candidates[0]
            blanked = words.copy()
            blanked[idx] = '_________'
            questions.append({
                'type': 'fill_blank',
                'question': f'Fill in the blank:<br><em>"{" ".join(blanked)}"</em>',
                'options': [],
                'answer': ans,
                'hint': f'{len(ans)} letters, starts with "{ans[0].upper()}"',
                'explanation': f'From the document: "{sent}"',
                'difficulty': 'beginner' if len(ans) <= 5 else level,
                'topic': 'document content'
            })
        return questions

    def _true_false_from_text(self, sentences: list, level: str) -> list:
        questions = []
        mutations = [
            ('not ', ''), ('never ', 'always '), ('always ', 'never '),
            ('before ', 'after '), ('after ', 'before '),
            ('could not', 'could'), ('could', 'could not'),
            ('refused', 'agreed'), ('agreed', 'refused'),
            ('stolen', 'bought'), ('returned', 'kept'),
            ('beautiful', 'ugly'), ('honest', 'dishonest'),
            ('happy', 'sad'), ('trusted', 'doubted'),
        ]
        good = [s for s in sentences if 12 <= len(s.split()) <= 40]
        random.shuffle(good)

        for sent in good[:8]:
            if len(questions) >= 4:
                break
            questions.append({
                'type': 'true_false',
                'question': f'True or False:<br><em>"{sent}"</em>',
                'options': ['True', 'False'],
                'answer': 'True',
                'explanation': 'This statement appears directly in the document.',
                'difficulty': 'beginner',
                'topic': 'reading comprehension'
            })
            mutated, ok = sent, False
            for orig, repl in mutations:
                if orig.lower() in sent.lower():
                    mutated = re.sub(re.escape(orig), repl, sent, count=1, flags=re.IGNORECASE)
                    if mutated != sent:
                        ok = True
                        break
            if ok and len(questions) < 8:
                questions.append({
                    'type': 'true_false',
                    'question': f'True or False:<br><em>"{mutated}"</em>',
                    'options': ['True', 'False'],
                    'answer': 'False',
                    'explanation': f'The correct version is: "{sent}"',
                    'difficulty': level,
                    'topic': 'reading comprehension'
                })
        return questions[:6]

    def _who_what_questions(self, sentences: list, people: list, level: str) -> list:
        questions = []
        if not people:
            return questions
        people_names = [p['name'] if isinstance(p, dict) else p for p in people]

        for sent in sentences:
            if len(questions) >= 3:
                break
            for name in people_names:
                if name in sent and len(sent.split()) >= 8:
                    if re.search(r'\b(said|told|asked|replied|went|came|took|gave|'
                                 r'rode|stolen|found|refused|believed|knew|heard|'
                                 r'jumped|cried|laughed|felt|looked|wanted|wished)\b',
                                 sent, re.IGNORECASE):
                        others = [s for s in sentences
                                  if name in s and s != sent and len(s.split()) >= 6]
                        wrong = []
                        for ws in others[:3]:
                            ws_words = ws.split()
                            if len(ws_words) > 15:
                                ws = ' '.join(ws_words[:15]) + '...'
                            wrong.append(ws)
                        if len(wrong) >= 2:
                            options = _ensure_4_options([sent] + wrong[:3], sent)
                            questions.append({
                                'type': 'mcq',
                                'question': (f'Which best describes what '
                                             f'<strong>{name}</strong> does?'),
                                'options': options,
                                'answer': sent,
                                'explanation': 'Stated directly in the document.',
                                'difficulty': level,
                                'topic': f"{name}'s actions"
                            })
                            break
        return questions

    def _fact_mcq(self, sentences: list, level: str) -> list:
        questions = []
        good = [s for s in sentences if 10 <= len(s.split()) <= 35]
        if len(good) < 4:
            return questions
        random.shuffle(good)

        for i in range(0, min(len(good)-3, 12), 4):
            if len(questions) >= 3:
                break
            correct = good[i]
            wrongs  = good[i+1:i+4]
            if len(wrongs) < 2:
                continue
            options = _ensure_4_options([correct] + wrongs[:3], correct)
            questions.append({
                'type': 'mcq',
                'question': 'Which statement is taken directly from the document?',
                'options': options,
                'answer': correct,
                'explanation': 'This sentence appears in the original text.',
                'difficulty': level,
                'topic': 'document recall'
            })
        return questions

    def _acronym_questions(self, concepts_data: dict) -> list:
        questions = []
        kb = TextExpander.TERM_KNOWLEDGE
        acronyms = [a['term'] for a in concepts_data.get('acronyms', [])
                    if a['term'] in kb]
        for term in acronyms[:4]:
            info = kb[term]
            if 'full' not in info:
                continue
            correct = info['full']
            wrong_pool = [v['full'] for k, v in kb.items()
                          if k != term and 'full' in v and v['full'] != correct]
            wrong = random.sample(wrong_pool, min(3, len(wrong_pool)))
            if not wrong:
                continue
            options = _ensure_4_options([correct] + wrong[:3], correct)
            questions.append({
                'type': 'mcq',
                'question': f'What does <strong>{term}</strong> stand for?',
                'options': options,
                'answer': correct,
                'explanation': info.get('intermediate', ''),
                'difficulty': 'beginner',
                'topic': term
            })
        return questions


# ══════════════════════════════════════════════════════
#  USER LEVEL ASSESSOR
# ══════════════════════════════════════════════════════

class UserLevelAssessor:

    def calculate_score(self, answers: list, questions: list) -> dict:
        question_map  = {q['id']: q for q in questions}
        topic_scores  = collections.defaultdict(lambda: {'correct': 0, 'total': 0})
        details       = []
        correct_count = 0

        for ans in answers:
            q = question_map.get(ans['id'])
            if not q:
                continue
            topic   = q.get('topic', 'General')
            given   = str(ans.get('given', '')).strip().lower()
            correct = str(q.get('answer', '')).strip().lower()

            is_correct = (
                given == correct or
                given[:30] in correct[:50] or
                correct[:30] in given[:50] or
                (len(given) > 3 and given in correct)
            )

            topic_scores[topic]['total'] += 1
            if is_correct:
                topic_scores[topic]['correct'] += 1
                correct_count += 1

            details.append({
                'id':             q['id'],
                'question':       q['question'],
                'given':          ans.get('given', ''),
                'correct_answer': q['answer'],
                'is_correct':     is_correct,
                'explanation':    q.get('explanation', ''),
                'topic':          topic
            })

        total = len(answers)
        pct   = round(correct_count / total * 100) if total > 0 else 0

        skill_meters = {}
        for topic, scores in topic_scores.items():
            tp = round(scores['correct'] / scores['total'] * 100) if scores['total'] > 0 else 0
            skill_meters[topic] = {
                'score':   tp,
                'correct': scores['correct'],
                'total':   scores['total'],
                'level':   'Strong' if tp >= 80 else ('Developing' if tp >= 55 else 'Needs Work')
            }

        weak   = [t for t, s in skill_meters.items() if s['score'] < 50]
        strong = [t for t, s in skill_meters.items() if s['score'] >= 75]
        inferred = 'advanced' if pct >= 75 else ('intermediate' if pct >= 45 else 'beginner')

        return {
            'overall_score':  pct,
            'correct':        correct_count,
            'total':          total,
            'inferred_level': inferred,
            'skill_meters':   skill_meters,
            'weak_areas':     weak,
            'strong_areas':   strong,
            'details':        details,
            'recommendations':self._recommendations(inferred, weak, strong)
        }

    def _recommendations(self, level, weak, strong) -> list:
        recs = []
        if level == 'beginner':
            recs.append('📚 Read the glossary carefully before re-reading the document.')
            recs.append('🌱 Use Beginner Learning View for plain-language explanations.')
            recs.append('🌙 Try Story Mode — same content, much easier to absorb.')
        elif level == 'intermediate':
            recs.append('🧩 Use the Intermediate Learning View for annotated explanations.')
            recs.append('📊 Focus on sections where you scored lowest.')
        else:
            recs.append('🚀 Try the Advanced Learning View for deep technical depth.')
            recs.append('🔬 Strong comprehension — focus on applying the concepts.')
        for area in weak[:2]:
            recs.append(f'⚠️ Weak area: <strong>{area}</strong> — revisit in the document.')
        for area in strong[:1]:
            recs.append(f'✅ Strong area: <strong>{area}</strong> — solid understanding.')
        return recs