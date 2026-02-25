"""
NLP Reasoning Engine (Understanding Layer)
+
Custom Text Transformation (Action Layer)

No external ML libraries needed — pure Python NLP that actually works.
"""

import re
import string
import collections
from heapq import nlargest


# ─────────────────────────────────────────────
#  NLP REASONING ENGINE (Understanding Layer)
# ─────────────────────────────────────────────

class NLPEngine:
    """
    Transforms extracted text into meaningful language.
    Tasks: tokenization, normalization, grammar correction, NER, sentence detection.
    """

    # Common English stopwords
    STOPWORDS = set([
        'a', 'an', 'the', 'is', 'it', 'in', 'on', 'at', 'to', 'for',
        'of', 'and', 'or', 'but', 'not', 'with', 'this', 'that', 'was',
        'are', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may',
        'might', 'shall', 'can', 'from', 'by', 'as', 'into', 'through',
        'during', 'before', 'after', 'above', 'below', 'up', 'down',
        'out', 'off', 'over', 'under', 'again', 'then', 'once', 'here',
        'there', 'when', 'where', 'why', 'how', 'all', 'each', 'every',
        'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
        'only', 'same', 'so', 'than', 'too', 'very', 'just', 'because',
        'if', 'while', 'about', 'its'   , 'their', 'our', 'your', 'his', 'her'
    ])

    # NER patterns (Named Entity Recognition without ML)
    NER_PATTERNS = {
        'EMAIL': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'PHONE': r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        'DATE': r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|'
                r'(?:January|February|March|April|May|June|July|August|September|'
                r'October|November|December)\s+\d{1,2},?\s+\d{4})\b',
        'URL': r'https?://[^\s<>"{}|\\^`\[\]]+',
        'MONEY': r'\$\s?\d+(?:,\d{3})*(?:\.\d{2})?|\d+(?:,\d{3})*\s?(?:USD|EUR|GBP|INR)',
        'PERCENTAGE': r'\d+\.?\d*\s?%',
        'CAPITALIZED_PHRASE': r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b',
        'ACRONYM': r'\b[A-Z]{2,6}\b',
    }

    def normalize(self, text: str) -> str:
        """
        Tokenization and normalization.
        - Fix OCR artifacts (ligatures, broken words)
        - Normalize whitespace
        - Fix common OCR substitutions
        """
        # Fix OCR-common errors
        text = text.replace('|', 'I')      # pipe often misread
        text = re.sub(r'(?<=[a-z])0(?=[a-z])', 'o', text)   # 0 inside words → o
        text = re.sub(r'(?<=[A-Za-z])1(?=[A-Za-z])', 'l', text)  # 1 inside words → l
        # Fix broken hyphenated line endings
        text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)
        # Normalize whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Fix spaced-out characters like "H e l l o"
        text = re.sub(r'(?<=\b\w) (?=\w\b)', '', text)
        return text.strip()

    def extract_sentences(self, text: str) -> list:
        """Split text into sentences."""
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        return [s.strip() for s in sentences if s.strip()]

    def tokenize(self, text: str) -> list:
        """Split into words, remove punctuation."""
        tokens = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        return tokens

    def named_entity_recognition(self, text: str) -> dict:
        """Extract named entities using regex patterns (NER without ML)."""
        entities = {}
        for entity_type, pattern in self.NER_PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                # Flatten nested groups
                flat = []
                for m in matches:
                    if isinstance(m, tuple):
                        flat.extend([x for x in m if x])
                    else:
                        flat.append(m)
                entities[entity_type] = list(set(flat))
        return entities

    def get_keywords(self, text: str, top_n: int = 10) -> list:
        """Extract top N keywords by frequency (excluding stopwords)."""
        tokens = self.tokenize(text)
        tokens = [t for t in tokens if t not in self.STOPWORDS and len(t) > 2]
        freq = collections.Counter(tokens)
        return freq.most_common(top_n)

    def validate_grammar_basic(self, text: str) -> list:
        """Basic grammar/syntax checks."""
        issues = []
        sentences = self.extract_sentences(text)
        for s in sentences:
            if s and s[0].islower():
                issues.append(f"Sentence may not start correctly: '{s[:40]}...'")
            if re.search(r'\b(\w+) \1\b', s, re.IGNORECASE):
                word = re.search(r'\b(\w+) \1\b', s, re.IGNORECASE).group(1)
                issues.append(f"Possible duplicate word: '{word}'")
        return issues[:10]


# ─────────────────────────────────────────────
#  CUSTOM TEXT TRANSFORMATION (Action Layer)
# ─────────────────────────────────────────────

class TextTransformer:
    """
    Goal-directed AI behavior: transform extracted text for different purposes.
    Same text, multiple transformations depending on user intent.
    
    Transformations:
    - Summarization
    - Information Extraction
    - Redaction of sensitive data
    - Formatting and restructuring
    - Classification and tagging
    """

    def __init__(self):
        self.nlp = NLPEngine()

    # ── 1. SUMMARIZATION ──────────────────────────────────

    def summarize(self, text: str, ratio: float = 0.3, max_sentences: int = 8) -> str:
        """
        Extractive summarization using sentence scoring.
        Scores sentences by keyword frequency + position.
        """
        text = self.nlp.normalize(text)
        sentences = self.nlp.extract_sentences(text)
        if len(sentences) <= 3:
            return text

        # Score each sentence
        keywords = dict(self.nlp.get_keywords(text, top_n=20))
        scores = {}
        for i, sentence in enumerate(sentences):
            tokens = self.nlp.tokenize(sentence)
            score = sum(keywords.get(t, 0) for t in tokens)
            # Bonus for early sentences (title/intro often important)
            if i == 0:
                score *= 1.5
            elif i < 3:
                score *= 1.2
            # Penalize very short or very long sentences
            word_count = len(tokens)
            if word_count < 5:
                score *= 0.5
            elif word_count > 40:
                score *= 0.8
            scores[sentence] = score

        n = max(2, min(max_sentences, int(len(sentences) * ratio)))
        top_sentences = nlargest(n, scores, key=scores.get)
        # Restore original order
        ordered = [s for s in sentences if s in top_sentences]
        return ' '.join(ordered)

    # ── 2. INFORMATION EXTRACTION ─────────────────────────

    def extract_information(self, text: str) -> dict:
        """
        Extract structured information from unstructured text.
        Returns: entities, keywords, stats, key-value pairs.
        """
        text = self.nlp.normalize(text)
        entities = self.nlp.named_entity_recognition(text)
        keywords = self.nlp.get_keywords(text, top_n=15)
        stats = self._extract_statistics(text)
        key_values = self._extract_key_value_pairs(text)
        headings = self._extract_headings(text)

        return {
            'named_entities': entities,
            'top_keywords': keywords,
            'statistics': stats,
            'key_value_pairs': key_values,
            'headings': headings,
            'sentence_count': len(self.nlp.extract_sentences(text)),
            'word_count': len(text.split()),
            'char_count': len(text)
        }

    def _extract_statistics(self, text: str) -> list:
        """Find numbers with context."""
        pattern = r'(\d+(?:\.\d+)?(?:\s?%)?)\s+([a-zA-Z\s]{3,30})'
        matches = re.findall(pattern, text)
        return [{'value': m[0], 'context': m[1].strip()} for m in matches[:10]]

    def _extract_key_value_pairs(self, text: str) -> dict:
        """Extract label: value patterns."""
        pattern = r'([A-Z][a-z\s]{2,30}):\s*([^\n]{3,60})'
        matches = re.findall(pattern, text)
        return {m[0].strip(): m[1].strip() for m in matches[:15]}

    def _extract_headings(self, text: str) -> list:
        """Find likely headings (short lines, capitalized)."""
        lines = text.split('\n')
        headings = []
        for line in lines:
            line = line.strip()
            if (10 < len(line) < 80 and
                    (line[0].isupper() or line.isupper()) and
                    not line.endswith(('.', ',', ';'))):
                headings.append(line)
        return headings[:20]

    # ── 3. REDACTION ──────────────────────────────────────

    def redact(self, text: str, redact_types: list = None) -> dict:
        """
        Redact sensitive information (PII).
        redact_types: list from ['EMAIL', 'PHONE', 'DATE', 'MONEY', 'CAPITALIZED_PHRASE']
        """
        if redact_types is None:
            redact_types = ['EMAIL', 'PHONE', 'MONEY']

        redacted_text = text
        redaction_log = []

        for entity_type, pattern in self.nlp.NER_PATTERNS.items():
            if entity_type not in redact_types:
                continue
            matches = re.finditer(pattern, redacted_text)
            for match in matches:
                original = match.group(0)
                replacement = f'[{entity_type}_REDACTED]'
                redacted_text = redacted_text.replace(original, replacement, 1)
                redaction_log.append({
                    'type': entity_type,
                    'original': original,
                    'replacement': replacement
                })

        return {
            'redacted_text': redacted_text,
            'redaction_log': redaction_log,
            'items_redacted': len(redaction_log)
        }

    # ── 4. FORMATTING & RESTRUCTURING ─────────────────────

    def format_text(self, text: str, style: str = 'clean') -> str:
        """
        Restructure text into clean formats.
        style: 'clean' | 'bullet_points' | 'numbered' | 'markdown' | 'json_structure'
        """
        text = self.nlp.normalize(text)

        if style == 'clean':
            return self._clean_format(text)
        elif style == 'bullet_points':
            return self._to_bullet_points(text)
        elif style == 'numbered':
            return self._to_numbered(text)
        elif style == 'markdown':
            return self._to_markdown(text)
        elif style == 'json_structure':
            return self._to_json_structure(text)
        return text

    def _clean_format(self, text: str) -> str:
        lines = [line.strip() for line in text.split('\n')]
        return '\n'.join(line for line in lines if line)

    def _to_bullet_points(self, text: str) -> str:
        sentences = self.nlp.extract_sentences(text)
        return '\n'.join(f'• {s}' for s in sentences if s.strip())

    def _to_numbered(self, text: str) -> str:
        sentences = self.nlp.extract_sentences(text)
        return '\n'.join(f'{i+1}. {s}' for i, s in enumerate(sentences) if s.strip())

    def _to_markdown(self, text: str) -> str:
        headings = self._extract_headings(text)
        result = []
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                result.append('')
            elif line in headings:
                result.append(f'## {line}')
            else:
                result.append(line)
        return '\n'.join(result)

    def _to_json_structure(self, text: str) -> str:
        import json
        info = self.extract_information(text)
        sentences = self.nlp.extract_sentences(text)
        structure = {
            'headings': info['headings'],
            'paragraphs': [' '.join(sentences[i:i+3]) for i in range(0, len(sentences), 3)],
            'entities': info['named_entities'],
            'keywords': [kw[0] for kw in info['top_keywords']]
        }
        return json.dumps(structure, indent=2)

    # ── 5. CLASSIFICATION & TAGGING ───────────────────────

    def classify_and_tag(self, text: str) -> dict:
        """
        Classify document type and add semantic tags.
        No ML needed — rule-based classification using keyword signals.
        """
        text_lower = text.lower()
        scores = {}

        categories = {
            'Academic/Research': ['abstract', 'methodology', 'conclusion', 'references',
                                  'hypothesis', 'experiment', 'analysis', 'results', 'study'],
            'Legal/Contract': ['hereby', 'pursuant', 'jurisdiction', 'liability',
                               'indemnify', 'clause', 'agreement', 'party', 'terms'],
            'Medical/Health': ['patient', 'diagnosis', 'treatment', 'clinical',
                               'medication', 'symptoms', 'disease', 'healthcare'],
            'Financial': ['revenue', 'profit', 'loss', 'balance', 'quarter',
                          'fiscal', 'investment', 'assets', 'liabilities'],
            'Technical/Engineering': ['algorithm', 'system', 'architecture',
                                      'implementation', 'module', 'api', 'database'],
            'News/Article': ['according', 'reported', 'announced', 'said', 'told',
                             'sources', 'officials', 'government'],
            'Educational': ['learn', 'students', 'course', 'chapter', 'lesson',
                            'exercise', 'curriculum', 'teacher'],
        }

        for category, keywords in categories.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            scores[category] = score

        best_category = max(scores, key=scores.get)
        confidence = scores[best_category] / len(categories[best_category]) * 100

        # Generate semantic tags from top keywords
        keywords = self.nlp.get_keywords(text, top_n=10)
        tags = [kw[0] for kw in keywords]

        # Sentiment approximation (very basic)
        pos_words = ['good', 'great', 'excellent', 'improved', 'success', 'benefit',
                     'efficient', 'effective', 'better', 'best', 'innovative']
        neg_words = ['poor', 'bad', 'fail', 'error', 'problem', 'issue', 'difficult',
                     'slow', 'expensive', 'risk', 'challenge']
        pos_score = sum(1 for w in pos_words if w in text_lower)
        neg_score = sum(1 for w in neg_words if w in text_lower)
        sentiment = 'Positive' if pos_score > neg_score else ('Negative' if neg_score > pos_score else 'Neutral')

        return {
            'document_type': best_category,
            'type_confidence': round(min(confidence, 100), 1),
            'all_scores': dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)),
            'semantic_tags': tags,
            'sentiment': sentiment,
            'language': self._detect_language(text)
        }

    def _detect_language(self, text: str) -> str:
        """Very basic language detection by common word frequency."""
        lang_words = {
            'English': ['the', 'is', 'are', 'and', 'for', 'this'],
            'French': ['le', 'la', 'les', 'est', 'pour', 'que'],
            'Spanish': ['el', 'la', 'los', 'es', 'para', 'que'],
            'German': ['der', 'die', 'das', 'ist', 'und', 'für'],
        }
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))
        scores = {lang: sum(1 for w in kws if w in words)
                  for lang, kws in lang_words.items()}
        return max(scores, key=scores.get)
