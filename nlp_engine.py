"""
NLP Reasoning Engine — v6 PRODUCTION QUALITY
==============================================

WHAT'S NEW IN v6 (full explanation for presentation):

1. OCRTextRepair — Pre-processing layer (NEW)
   Runs 8 sequential cleaning passes on raw OCR output BEFORE any NLP:
   • Pass 1: Fix Unicode/encoding issues (curly quotes, em-dashes, null bytes)
   • Pass 2: Remove scanner artifacts (page numbers, ISBN, print info, symbol noise)
   • Pass 3: Fix line-break word splits ("beau-\ntiful" → "beautiful")
   • Pass 4: Fix character-level OCR errors (rn→m, 0→O, pipe→I)
   • Pass 5: Fix spacing (double spaces, space before punctuation)
   • Pass 6: Reconstruct broken sentence fragments
   • Pass 7: Fix capitalization and punctuation
   • Pass 8: Quality filter (drop lines that are still noise)
   WHY: All grammar problems in story/quiz/summary were caused by
   noisy OCR text reaching the NLP layer. Fix the input first.

2. SentenceRewriter — Post-extraction cleanup (NEW)
   After TextRank selects important sentences, this rewrites each one
   to ensure proper capitalization, punctuation, and completeness.
   Removes leading fragments like "And..." or "But..." that make
   sentences grammatically incomplete.

3. TextRankSummarizer — Upgraded to use clean input
   Now runs on OCR-repaired text + rewrites selected sentences.
   Result: summaries that read naturally, not like raw scanner output.

4. StoryTransformer — Upgraded
   Uses OCR-repaired + rewritten sentences as story content.
   Story templates adapt to real characters/settings from the document.

5. SmartQuizGenerator — Upgraded
   Generates questions only from high-quality (repaired+rewritten) sentences.
   6 question types including causal reasoning and main-idea questions.
"""

import re
import math
import random


# ══════════════════════════════════════════════════════════════════
#  LAYER 0: OCR TEXT REPAIR ENGINE
# ══════════════════════════════════════════════════════════════════

class OCRTextRepair:
    """
    Repairs common OCR errors before NLP processing.

    PRESENT THIS AS: A pre-processing pipeline that applies 8 sequential
    rule-based cleaning passes to raw OCR output. Each pass targets a
    specific class of systematic OCR error. Without this, every downstream
    NLP operation (summarization, story mode, quiz) receives broken input
    and produces broken output.

    This is the same concept used in enterprise OCR systems like
    ABBYY FineReader and Adobe Acrobat's OCR correction layer.
    """

    OCR_CHAR_FIXES = [
        (r'(?<=[a-z])rn(?=[a-z])', 'm'),   # "algorithrn" → "algorithm"
        (r'\brn\b', 'm'),                    # standalone "rn" → "m"
        (r'\b0(?=[a-zA-Z])', 'O'),           # "0ne" → "One"
    ]

    def repair(self, text: str) -> str:
        text = self._pass1_fix_encoding(text)
        text = self._pass2_remove_artifacts(text)
        text = self._pass3_fix_line_breaks(text)
        text = self._pass4_fix_char_errors(text)
        text = self._pass5_fix_spacing(text)
        text = self._pass6_reconstruct_sentences(text)
        text = self._pass7_fix_punctuation(text)
        text = self._pass8_quality_filter(text)
        return text.strip()

    def _pass1_fix_encoding(self, text: str) -> str:
        replacements = {
            '\u2018': "'", '\u2019': "'",
            '\u201c': '"', '\u201d': '"',
            '\u2013': '-', '\u2014': '-',
            '\u00a0': ' ', '\u2026': '...',
            '|': 'I', '\x00': '',
        }
        for bad, good in replacements.items():
            text = text.replace(bad, good)
        return text

    def _pass2_remove_artifacts(self, text: str) -> str:
        text = re.sub(r'---\s*Page \d+\s*---', ' ', text)
        text = re.sub(r'\bPage\s+\d+\s+of\s+\d+\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Reprint\s+\d{4}[-]\d{2}', '', text)
        text = re.sub(r'Chap\s*\d+\.indd.*', '', text)
        text = re.sub(r'\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s*[AP]M', '', text)
        text = re.sub(r'\bISBN[:\s]\S+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^[\d\s\-\—\.\,\>\<\|\/\\:;£$€#@*]+$', '', text, flags=re.MULTILINE)
        # Remove currency/special chars that OCR picks up from headers/footers
        text = re.sub(r'[£€¥©®™°§¶†‡]', '', text)
        # Remove words containing non-ASCII characters (OCR artifacts like "imaginablé", "£wnes")
        text = re.sub(r'\b\w*[^\x00-\x7F]\w*\b', '', text)
        # Remove obvious uppercase noise tokens (2-3 chars, all caps, not common words)
        common_short = {'AS','IS','IT','IN','ON','AT','TO','BY','AN','OR','OF',
                        'DO','GO','HE','ME','MY','NO','SO','UP','US','WE','BE'}
        def remove_noise_caps(m):
            token = m.group(0)
            return token if token in common_short else ' '
        text = re.sub(r'\b[A-Z]{2,3}\b(?!\s*:)', remove_noise_caps, text)
        return text

    def _pass3_fix_line_breaks(self, text: str) -> str:
        text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)
        text = re.sub(r'([a-z,;])\s*\n\s*([a-z])', r'\1 \2', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text

    def _pass4_fix_char_errors(self, text: str) -> str:
        for pattern, replacement in self.OCR_CHAR_FIXES:
            text = re.sub(pattern, replacement, text)
        return text

    def _pass5_fix_spacing(self, text: str) -> str:
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)
        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
        return text

    def _pass6_reconstruct_sentences(self, text: str) -> str:
        paragraphs = re.split(r'\n\n+', text)
        result_paras = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            parts = re.split(r'(?<=[.!?])\s+', para)
            merged = []
            buffer = ''
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                if buffer:
                    bwords = buffer.split()
                    has_verb = bool(re.search(
                        r'\b(is|was|are|were|had|has|have|said|told|found|went|came|took|gave|knew|felt|seemed|became)\b',
                        buffer, re.IGNORECASE))
                    if len(bwords) < 5 and not has_verb:
                        buffer = buffer.rstrip('.') + ' ' + part
                        continue
                    merged.append(buffer)
                    buffer = part
                else:
                    buffer = part
            if buffer:
                merged.append(buffer)
            result_paras.append(' '.join(merged))
        return '\n\n'.join(result_paras)

    def _pass7_fix_punctuation(self, text: str) -> str:
        lines = text.split('\n')
        fixed = []
        for line in lines:
            line = line.strip()
            if not line:
                fixed.append('')
                continue
            if line and line[0].islower() and len(line) > 3:
                line = line[0].upper() + line[1:]
            fixed.append(line)
        return '\n'.join(fixed)

    def _pass8_quality_filter(self, text: str) -> str:
        lines = text.split('\n')
        clean_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                clean_lines.append('')
                continue
            words = line.split()
            if len(words) < 3:
                continue
            alpha_chars = sum(1 for c in line if c.isalpha())
            if alpha_chars / max(len(line), 1) < 0.4:
                continue
            single_chars = sum(1 for w in words if len(re.sub(r'[^a-zA-Z]', '', w)) <= 1)
            if single_chars > len(words) * 0.4:
                continue
            clean_lines.append(line)
        result = '\n'.join(clean_lines)
        return re.sub(r'\n{3,}', '\n\n', result).strip()

    def get_quality_score(self, text: str) -> dict:
        words = text.split()
        alpha_words = [w for w in words if re.match(r'^[a-zA-Z]+$', w)]
        sentences = re.split(r'[.!?]+', text)
        valid_sents = [s.strip() for s in sentences if len(s.split()) >= 5]
        vocab = set(w.lower() for w in alpha_words)
        ttr = len(vocab) / max(len(alpha_words), 1)
        avg_len = sum(len(s.split()) for s in valid_sents) / max(len(valid_sents), 1)
        score = min(100, int(
            (len(alpha_words) / max(len(words), 1)) * 40 +
            min(ttr * 100, 30) +
            min(avg_len / 20 * 20, 20) +
            (10 if len(valid_sents) >= 3 else 0)
        ))
        return {
            'quality_score': score,
            'total_words': len(words),
            'clean_words': len(alpha_words),
            'valid_sentences': len(valid_sents),
            'vocabulary_richness': round(ttr, 3),
            'label': 'GOOD' if score >= 70 else ('FAIR' if score >= 45 else 'NOISY')
        }


# ══════════════════════════════════════════════════════════════════
#  LAYER 1: CORE NLP ENGINE
# ══════════════════════════════════════════════════════════════════

class NLPEngine:

    STOPWORDS = set([
        'a','an','the','is','it','in','on','at','to','for','of','and','or',
        'but','not','with','this','that','was','are','were','be','been',
        'being','have','has','had','do','does','did','will','would','could',
        'should','may','might','shall','can','from','by','as','into',
        'through','during','before','after','above','below','up','down',
        'out','off','over','under','again','then','once','here','there',
        'when','where','why','how','all','each','every','both','few','more',
        'most','other','some','such','no','only','same','so','than','too',
        'very','just','because','if','while','about','its','their','our',
        'your','his','her','him','me','we','us','they','them','he','she',
        'i','my','you','said','one','like','know','get','got','upon','even',
        'back','still','also','well','now','whose','whom','which','what','who',
        'am','been','being','let','go','come','came','went','take','took',
        'make','made','see','saw','say','tell','told','ask','asked','think',
        'thought','look','looked','want','wanted','give','gave','keep','kept'
    ])

    NER_PATTERNS = {
        'EMAIL': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'PHONE': r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        'DATE':  r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|'
                 r'(?:January|February|March|April|May|June|July|August|September|'
                 r'October|November|December)\s+\d{1,2},?\s+\d{4})\b',
        'URL':   r'https?://[^\s<>"{}|\\^`\[\]]+',
        'MONEY': r'\$\s?\d+(?:,\d{3})*(?:\.\d{2})?|\d+(?:,\d{3})*\s?(?:USD|EUR|GBP|INR)',
        'PERCENTAGE': r'\d+\.?\d*\s?%',
        'PERSON_NAME': r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b',
        'ACRONYM': r'\b[A-Z]{2,6}\b',
    }

    def __init__(self):
        self.repairer = OCRTextRepair()

    def clean_text(self, text: str) -> str:
        return self.repairer.repair(text)

    def extract_sentences(self, text: str) -> list:
        raw = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'(])', text)
        sentences = []
        for s in raw:
            s = s.strip()
            if len(s) < 20:
                continue
            words = re.findall(r'\b[a-zA-Z]{2,}\b', s)
            if len(words) < 5:
                continue
            alpha_ratio = len(''.join(re.findall(r'[a-zA-Z]', s))) / max(len(s), 1)
            if alpha_ratio < 0.55:
                continue
            sentences.append(s)
        return sentences

    def tokenize(self, text: str) -> list:
        return re.findall(r'\b[a-zA-Z]+\b', text.lower())

    def named_entity_recognition(self, text: str) -> dict:
        entities = {}
        for entity_type, pattern in self.NER_PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                flat = []
                for m in matches:
                    if isinstance(m, tuple):
                        flat.extend([x for x in m if x])
                    else:
                        flat.append(m)
                unique = list(set(x.strip() for x in flat if x.strip() and len(x.strip()) > 1))
                if unique:
                    entities[entity_type] = unique[:8]
        return entities

    def get_keywords(self, text: str, top_n: int = 10) -> list:
        tokens = self.tokenize(text)
        tokens = [t for t in tokens if t not in self.STOPWORDS and len(t) > 3]
        tf = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        total = len(tokens) or 1
        scores = {}
        for word, count in tf.items():
            freq_ratio = count / total
            length_bonus = math.log(len(word)) if len(word) > 4 else 1.0
            scores[word] = freq_ratio * length_bonus
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]

    def normalize(self, text: str) -> str:
        return self.clean_text(text)

    def validate_grammar_basic(self, text: str) -> list:
        issues = []
        for s in self.extract_sentences(text):
            if s and s[0].islower():
                issues.append(f"Sentence may not start correctly: '{s[:40]}'")
        return issues[:10]


# ══════════════════════════════════════════════════════════════════
#  LAYER 2: SENTENCE REWRITER
# ══════════════════════════════════════════════════════════════════

class SentenceRewriter:
    """
    Rewrites extracted sentences into clean, grammatically complete English.

    PRESENT THIS AS: A post-extraction normalization step. TextRank selects
    the most IMPORTANT sentences, but importance doesn't guarantee cleanliness.
    This rewriter ensures every sentence in a summary, story, or quiz is
    properly capitalized, complete, and punctuated.
    """

    def rewrite_sentence(self, sentence: str) -> str:
        s = sentence.strip()
        if not s:
            return s
        s = s[0].upper() + s[1:]
        # Remove leading conjunctions that make a sentence a fragment
        s = re.sub(r'^(And|But|Or|Yet|So|Because|Although|However|Therefore)\s+',
                   '', s, flags=re.IGNORECASE)
        if s and s[0].islower():
            s = s[0].upper() + s[1:]
        if s and s[-1] not in '.!?':
            if not re.search(r'\b(who|what|where|when|why|how|which)\b', s[:20], re.IGNORECASE):
                s += '.'
        s = re.sub(r'([.!?]){2,}', r'\1', s)
        s = re.sub(r'\s+', ' ', s)
        return s.strip()

    def rewrite_list(self, sentences: list) -> list:
        return [self.rewrite_sentence(s) for s in sentences if s.strip()]

    def join_into_paragraph(self, sentences: list, connector_style: str = 'neutral') -> str:
        rewritten = self.rewrite_list(sentences)
        if not rewritten:
            return ''
        if len(rewritten) == 1:
            return rewritten[0]
        connectors = {
            'neutral':      ['', 'Additionally, ', 'Furthermore, ', 'Moreover, ',
                             'At the same time, ', 'Importantly, '],
            'storytelling': ['', 'Meanwhile, ', 'Then, ', 'As the story unfolds, ',
                             'What follows is significant: ', 'Most importantly, '],
            'academic':     ['', 'This is supported by the observation that ',
                             'The evidence shows that ', 'Notably, ',
                             'A key point is that ', 'In addition, '],
        }
        conn_list = connectors.get(connector_style, connectors['neutral'])
        parts = []
        for i, sent in enumerate(rewritten):
            conn = conn_list[i % len(conn_list)]
            if i == 0 or not conn:
                parts.append(sent)
            else:
                if sent and sent[0].isupper() and conn.endswith(' '):
                    sent_adj = sent[0].lower() + sent[1:]
                else:
                    sent_adj = sent
                parts.append(conn + sent_adj)
        return ' '.join(parts)


# ══════════════════════════════════════════════════════════════════
#  LAYER 3: TEXTRANK SUMMARIZER
# ══════════════════════════════════════════════════════════════════

class TextRankSummarizer:
    """
    TextRank: Graph-based ML algorithm (same family as Google PageRank).

    PRESENTATION TALKING POINT:
    ─────────────────────────────────────────────────────────────
    Step 1: Each sentence → NODE in a graph
    Step 2: TF vector for each sentence over shared vocabulary
    Step 3: Cosine similarity between every pair → EDGE WEIGHT
            cosine(A,B) = dot(A,B) / (||A|| × ||B||)
            0.0 = completely different topics, 1.0 = same content
    Step 4: PageRank power iteration → sentences that share content
            with many OTHER important sentences score highest
            (circular reinforcement — same math as Google search ranking)
    Step 5: Top-N by score, preserve original order → SUMMARY
    ─────────────────────────────────────────────────────────────
    Zero word-frequency counting. Pure linear algebra on sentence vectors.
    """

    def __init__(self, nlp: NLPEngine):
        self.nlp = nlp
        self.rewriter = SentenceRewriter()

    def _sentence_to_vector(self, sentence: str, vocab: set) -> dict:
        tokens = self.nlp.tokenize(sentence)
        tokens = [t for t in tokens if t not in self.nlp.STOPWORDS and t in vocab]
        vec = {}
        for t in tokens:
            vec[t] = vec.get(t, 0) + 1
        return vec

    def _cosine_similarity(self, vec_a: dict, vec_b: dict) -> float:
        if not vec_a or not vec_b:
            return 0.0
        dot = sum(vec_a.get(w, 0) * vec_b.get(w, 0) for w in vec_a)
        norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
        norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _build_similarity_matrix(self, sentences: list) -> list:
        n = len(sentences)
        vocab = set()
        for s in sentences:
            tokens = self.nlp.tokenize(s)
            vocab.update(t for t in tokens if t not in self.nlp.STOPWORDS)
        vectors = [self._sentence_to_vector(s, vocab) for s in sentences]
        matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    matrix[i][j] = self._cosine_similarity(vectors[i], vectors[j])
        return matrix

    def _pagerank(self, matrix: list, damping: float = 0.85,
                  iterations: int = 50, tol: float = 1e-5) -> list:
        n = len(matrix)
        if n == 0:
            return []
        scores = [1.0 / n] * n
        norm_matrix = []
        for row in matrix:
            row_sum = sum(row)
            norm_matrix.append(
                [v / row_sum for v in row] if row_sum > 0 else [1.0 / n] * n
            )
        for _ in range(iterations):
            new_scores = []
            for i in range(n):
                rank = (1 - damping) / n + damping * sum(
                    norm_matrix[j][i] * scores[j] for j in range(n))
                new_scores.append(rank)
            if sum(abs(new_scores[i] - scores[i]) for i in range(n)) < tol:
                break
            scores = new_scores
        return scores

    def summarize(self, text: str, ratio: float = 0.35, max_sentences: int = 8,
                  min_sentences: int = 3) -> str:
        sentences = self.nlp.extract_sentences(text)
        if not sentences:
            return text[:500]
        if len(sentences) <= min_sentences:
            return self.rewriter.join_into_paragraph(sentences, 'neutral')
        matrix = self._build_similarity_matrix(sentences)
        scores = self._pagerank(matrix)
        n = len(sentences)
        for i in range(n):
            if i == 0:
                scores[i] *= 1.5
            elif i == n - 1:
                scores[i] *= 1.2
            elif i / n < 0.1:
                scores[i] *= 1.1
        num = max(min_sentences, min(max_sentences, int(len(sentences) * ratio)))
        indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        top_indices = sorted([idx for idx, _ in indexed[:num]])
        selected = [sentences[i] for i in top_indices]
        return self.rewriter.join_into_paragraph(selected, 'neutral')

    def summarize_with_structure(self, text: str) -> dict:
        sentences = self.nlp.extract_sentences(text)
        keywords = self.nlp.get_keywords(text, top_n=15)
        core = self.summarize(text, ratio=0.3, max_sentences=6)
        if len(sentences) >= 5:
            matrix = self._build_similarity_matrix(sentences)
            scores = self._pagerank(matrix)
            indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
            raw_facts = [sentences[i] for i, _ in indexed[:6]]
            key_facts = self.rewriter.rewrite_list(raw_facts)
        else:
            key_facts = self.rewriter.rewrite_list(sentences[:5])
        kw_words = [k for k, _ in keywords]
        skip = {'said','asked','know','just','like','want','came','went',
                'took','back','could','would','should','been','have','this','that'}
        topic_words = [k for k in kw_words if k not in skip and len(k) > 4]
        theme = topic_words[0].title() if topic_words else "General Document"
        tl = text.lower()
        pos = sum(1 for w in ['good','great','excellent','success','happy','wonderful',
                               'beautiful','positive','achieve','win','love','joy'] if w in tl)
        neg = sum(1 for w in ['fail','bad','poor','loss','sad','angry','wrong',
                               'stolen','problem','crisis','fear','terrible'] if w in tl)
        sentiment = 'Positive' if pos > neg else ('Negative' if neg > pos else 'Neutral')
        return {
            'core_summary': core,
            'key_facts': key_facts,
            'main_theme': theme,
            'keywords': kw_words[:10],
            'sentiment': sentiment,
            'sentence_count': len(sentences),
            'word_count': len(text.split()),
        }


# ══════════════════════════════════════════════════════════════════
#  LAYER 4: TEXT TRANSFORMER (public API for app.py)
# ══════════════════════════════════════════════════════════════════

class TextTransformer:

    def __init__(self):
        self.nlp = NLPEngine()
        self.summarizer = TextRankSummarizer(self.nlp)
        self.rewriter = SentenceRewriter()

    def _prepare(self, text: str) -> str:
        return self.nlp.clean_text(text)

    def summarize(self, text: str, ratio: float = 0.35, max_sentences: int = 8) -> str:
        clean = self._prepare(text)
        return self.summarizer.summarize(clean, ratio=ratio, max_sentences=max_sentences)

    def extract_information(self, text: str) -> dict:
        clean = self._prepare(text)
        entities = self.nlp.named_entity_recognition(clean)
        keywords = self.nlp.get_keywords(clean, top_n=15)
        structured = self.summarizer.summarize_with_structure(clean)
        names = re.findall(r'\b([A-Z][a-z]{2,})\b', clean)
        non_names = {'The','He','She','It','We','You','They','But','And','So',
                     'As','If','When','Then','That','This','His','Her','My',
                     'All','Each','One','Now','For','Not','With','From'}
        name_map = {}
        for n in names:
            if n not in non_names:
                name_map[n] = name_map.get(n, 0) + 1
        characters = [(n, c) for n, c in
                      sorted(name_map.items(), key=lambda x: x[1], reverse=True)
                      if c >= 2][:8]
        dialogues = re.findall(r'["""]([^"""]{10,150})["""]', clean)
        kv = {}
        for m in re.finditer(r'([A-Z][a-z]{2,30}):\s*([^\n]{5,60})', clean):
            kv[m.group(1)] = m.group(2).strip()
        return {
            'named_entities': entities,
            'top_keywords': keywords,
            'characters': characters,
            'dialogue_lines': dialogues[:6],
            'key_value_pairs': kv,
            'structured_summary': structured,
            'sentence_count': structured['sentence_count'],
            'word_count': structured['word_count'],
            'char_count': len(clean),
        }

    def redact(self, text: str, redact_types: list = None) -> dict:
        if redact_types is None:
            redact_types = ['EMAIL', 'PHONE', 'MONEY']
        redacted_text = text
        redaction_log = []
        for entity_type, pattern in self.nlp.NER_PATTERNS.items():
            if entity_type not in redact_types:
                continue
            for match in re.finditer(pattern, redacted_text):
                original = match.group(0)
                replacement = f'[{entity_type}_REDACTED]'
                redacted_text = redacted_text.replace(original, replacement, 1)
                redaction_log.append({'type': entity_type, 'original': original})
        return {'redacted_text': redacted_text, 'redaction_log': redaction_log,
                'items_redacted': len(redaction_log)}

    def format_text(self, text: str, style: str = 'clean') -> str:
        clean = self._prepare(text)
        if style == 'bullet_points':
            sentences = self.nlp.extract_sentences(clean)
            rewritten = self.rewriter.rewrite_list(sentences)
            return '\n'.join(f'• {s}' for s in rewritten)
        elif style == 'markdown':
            headings = [l.strip() for l in clean.split('\n')
                        if 8 < len(l.strip()) < 80 and l.strip()[:1].isupper()
                        and not l.strip().endswith(('.', ',', ';', '?', '!'))
                        and len(l.strip().split()) <= 8][:10]
            result = []
            for line in clean.split('\n'):
                line = line.strip()
                if not line:
                    result.append('')
                elif line in headings:
                    result.append(f'## {line}')
                else:
                    result.append(line)
            return '\n'.join(result)
        return clean

    def classify_and_tag(self, text: str) -> dict:
        clean = self._prepare(text)
        tl = clean.lower()
        categories = {
            'Academic/Research': ['abstract','methodology','conclusion','hypothesis',
                                   'experiment','analysis','results','study','research'],
            'Legal/Contract':    ['hereby','pursuant','jurisdiction','liability',
                                   'indemnify','clause','agreement','party','terms'],
            'Medical/Health':    ['patient','diagnosis','treatment','clinical',
                                   'medication','symptoms','disease','healthcare'],
            'Financial':         ['revenue','profit','loss','balance','quarter',
                                   'fiscal','investment','assets','market'],
            'Technical':         ['algorithm','system','architecture','implementation',
                                   'module','pipeline','processing','neural'],
            'News/Article':      ['according','reported','announced','sources',
                                   'officials','government','minister'],
            'Literary/Story':    ['said','replied','whispered','heart','love','felt',
                                   'morning','summer','family','rode','stolen','tribe'],
            'Educational':       ['chapter','lesson','exercise','curriculum',
                                   'student','teacher','learn','textbook'],
        }
        scores = {cat: sum(1 for kw in kws if kw in tl) for cat, kws in categories.items()}
        best = max(scores, key=scores.get)
        conf = round(min(scores[best] / max(len(categories[best]) * 0.3, 1) * 100, 100), 1)
        keywords = self.nlp.get_keywords(clean, top_n=10)
        tags = [kw[0] for kw in keywords]
        pos = sum(1 for w in ['good','great','excellent','happy','wonderful','love','joy'] if w in tl)
        neg = sum(1 for w in ['poor','bad','fail','stolen','afraid','sad','angry'] if w in tl)
        sentiment = 'Positive' if pos > neg else ('Negative' if neg > pos else 'Neutral')
        return {
            'document_type': best, 'type_confidence': conf,
            'all_scores': dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)),
            'semantic_tags': tags, 'sentiment': sentiment, 'language': 'English'
        }


# ══════════════════════════════════════════════════════════════════
#  LAYER 5: STORY TRANSFORMER
# ══════════════════════════════════════════════════════════════════

class StoryTransformer:
    """
    Transforms document text into 7 narrative styles.
    v6: Uses OCR-repaired + rewritten sentences. Content adapts to the actual document.
    """

    STYLE_CONFIGS = {
        'romantic':          {'name': '💕 Romantic Story',    'description': 'Concepts as a love story'},
        'detective_thriller':{'name': '🔍 Detective Thriller', 'description': 'Concepts as a mystery'},
        'sci_fi':            {'name': '🚀 Sci-Fi Adventure',   'description': 'Futuristic space retelling'},
        'bedtime_story':     {'name': '🌙 Bedtime Story',      'description': 'Gentle warm retelling'},
        'news_reporter':     {'name': '📰 Breaking News',      'description': 'Reported as live news'},
        'sports_commentary': {'name': '🏆 Sports Commentary',  'description': 'Live sports commentary'},
        'mythology':         {'name': '⚡ Epic Mythology',     'description': 'Ancient myth style'},
    }

    def __init__(self):
        self.nlp = NLPEngine()
        self.summarizer = TextRankSummarizer(self.nlp)
        self.rewriter = SentenceRewriter()

    def get_available_styles(self) -> list:
        return [{'key': k, 'name': v['name'], 'description': v['description']}
                for k, v in self.STYLE_CONFIGS.items()]

    def transform_to_story(self, text: str, style: str, custom_characters: str = '') -> dict:
        if style not in self.STYLE_CONFIGS:
            style = 'detective_thriller'
        clean = self.nlp.clean_text(text)
        structured = self.summarizer.summarize_with_structure(clean)
        key_sentences = structured['key_facts']
        core_summary  = structured['core_summary']
        theme         = structured['main_theme']
        keywords      = structured['keywords']
        content_data  = self._extract_story_content(clean, key_sentences)
        chars         = self._parse_characters(custom_characters, content_data['characters'], theme)
        story = self._build_story(key_sentences, core_summary, style, theme,
                                   chars, keywords, content_data)
        words = story.split()
        return {
            'story_text': story,
            'style_used': self.STYLE_CONFIGS[style]['name'],
            'style_key': style,
            'topic_detected': theme,
            'concepts_woven': keywords[:10],
            'reading_time_minutes': max(1, round(len(words) / 200)),
            'word_count': len(words),
            'original_word_count': len(clean.split()),
        }

    def _extract_story_content(self, clean_text: str, key_sentences: list) -> dict:
        names = re.findall(r'\b([A-Z][a-z]{2,})\b', clean_text)
        non_names = {'The','He','She','It','We','You','They','But','And','So',
                     'As','If','When','Then','That','This','His','Her','My',
                     'All','Each','One','Now','For','Not','With','From','By',
                     'True','False','Page','Chapter','Summer','Morning','Evening'}
        name_map = {}
        for n in names:
            if n not in non_names:
                name_map[n] = name_map.get(n, 0) + 1
        characters = [n for n, c in sorted(name_map.items(), key=lambda x: x[1], reverse=True) if c >= 2][:5]
        locs = re.findall(
            r'\b(forest|city|village|room|house|school|hospital|office|barn|field|'
            r'farm|market|street|garden|mountain|river|sea|island|palace|castle|'
            r'station|laboratory|ship|valley|desert|stable|yard|meadow)\b',
            clean_text.lower())
        unique_locs = list(dict.fromkeys(locs))[:3]
        dialogues = re.findall(r'["""]([^"""]{15,120})["""]', clean_text)[:4]
        time_refs = re.findall(
            r'\b(morning|evening|night|dawn|dusk|summer|winter|spring|autumn|'
            r'early|late|one day|that day|long ago)\b', clean_text.lower())
        time_ctx = time_refs[0].strip() if time_refs else 'one day'
        return {'characters': characters, 'locations': unique_locs,
                'dialogues': dialogues, 'time_context': time_ctx}

    def _parse_characters(self, custom: str, auto: list, topic: str) -> dict:
        chars = {}
        if custom:
            for part in custom.split(','):
                part = part.strip()
                if ':' in part:
                    role, name = part.split(':', 1)
                    chars[role.strip().lower()] = name.strip()
        n1 = ['Arjun', 'Rohan', 'Dev', 'Kiran', 'Rajan', 'Vikram']
        n2 = ['Priya', 'Maya', 'Ananya', 'Riya', 'Kavya', 'Nisha']
        m  = ['Dr. Rao', 'Professor Singh', 'Dr. Meera', 'Master Krishnan']
        if 'protagonist' not in chars:
            chars['protagonist'] = auto[0] if auto else random.choice(n1)
        if 'mentor' not in chars:
            chars['mentor'] = auto[1] if len(auto) > 1 else random.choice(m)
        if 'sidekick' not in chars:
            chars['sidekick'] = auto[2] if len(auto) > 2 else random.choice(n2)
        return chars

    def _build_story(self, ks, summary, style, topic, chars, kw, cd) -> str:
        p, mentor, sk = chars['protagonist'], chars['mentor'], chars['sidekick']
        builders = {
            'romantic':           self._romantic,
            'detective_thriller': self._detective,
            'sci_fi':             self._scifi,
            'bedtime_story':      self._bedtime,
            'news_reporter':      self._news,
            'sports_commentary':  self._sports,
            'mythology':          self._mythology,
        }
        return builders.get(style, self._detective)(ks, summary, topic, p, mentor, sk, kw, cd)

    def _romantic(self, ks, summary, topic, hero, mentor, heroine, kw, cd):
        loc = cd['locations'][0] if cd['locations'] else 'a quiet room'
        time = cd['time_context']
        fkw = kw[0] if kw else topic.lower()
        dlg = cd['dialogues'][0] if cd['dialogues'] else None
        parts = [
            f"It was {time}, and {hero} was in the {loc} when it all began.\n\n"
            f"The subject was {topic} — the kind of thing you might pass over "
            f"without a second thought. But {hero} had made a promise to {heroine}, "
            f"and a promise was a promise. The first thing that caught {hero}'s "
            f"attention was {fkw}. Something about it refused to let go."
        ]
        connectors = [
            f"Hours passed. {hero} barely noticed.",
            f"Something was shifting — quietly, the way important things always do.",
            f"And then came the moment {hero} would remember longest:",
            f"{heroine} leaned closer. 'Read that one again,' she said softly.",
            f"{mentor} had always said that real understanding comes slowly. Here was proof:",
        ]
        for i, sentence in enumerate(ks[:5]):
            parts.append(f"{connectors[i % len(connectors)]}\n\n{sentence}\n\n"
                          f"{hero} paused. Some sentences deserve a second reading.")
        if dlg:
            parts.append(f"\"{dlg}\"\n\n{heroine} said it quietly, but it echoed. "
                          f"That was the heart of {topic}.")
        parts.append(
            f"\n\n— — —\n\nLater, when asked to explain {topic}, {hero} found the words came easily:\n\n"
            f"{summary}\n\n\"You actually understand it,\" {heroine} said.\n\n"
            f"\"I had a good reason to,\" said {hero}."
        )
        return '\n\n'.join(parts)

    def _detective(self, ks, summary, topic, detective, captain, partner, kw, cd):
        loc = cd['locations'][0] if cd['locations'] else 'the evidence room'
        time = cd['time_context']
        fkw = kw[0] if kw else topic.lower()
        dlg = cd['dialogues'][0] if cd['dialogues'] else None
        parts = [
            f"CASE FILE: {topic.upper()}\n"
            f"DETECTIVE: {detective.upper()} | STATUS: ACTIVE\n\n"
            f"The file arrived {time}. No cover note. Just the subject: {topic}.\n\n"
            f"Detective {detective} went straight to the {loc}. "
            f"The first clue was already there: {fkw}."
        ]
        clue_frames = [
            f"EVIDENCE LOG — {detective} isolates the first key finding:",
            f"Captain {captain} appeared at the door. 'What have you got?'\n"
            f"'{detective} pointed to the critical line.",
            f"Partner {partner} had flagged this passage. She was right.",
            f"Cross-referencing the earlier evidence confirmed it:",
            f"The theory was forming. One final piece would close the case:",
        ]
        for i, sentence in enumerate(ks[:5]):
            parts.append(f"{clue_frames[i % len(clue_frames)]}\n\n"
                          f"[EXHIBIT {i+1}]: {sentence}\n\n"
                          f"{detective} circled it. Confirmed.")
        if dlg:
            parts.append(f"A key statement surfaced:\n\n\"{dlg}\"\n\n"
                          f"That was the missing piece. {detective} closed the folder.")
        parts.append(
            f"\n\nCASE SUMMARY:\n\n{summary}\n\n"
            f"Captain {captain}: 'How did you crack it?'\n\n"
            f"Detective {detective}: 'The evidence was always there. "
            f"You just have to know what to look for.'\n\n[CASE {topic.upper()} — CLOSED]"
        )
        return '\n\n'.join(parts)

    def _scifi(self, ks, summary, topic, commander, ai_name, crew, kw, cd):
        loc = cd['locations'][0] if cd['locations'] else 'deep space'
        fkw = kw[0] if kw else topic.lower()
        parts = [
            f"STARSHIP ATHENA — MISSION LOG\nSUBJECT: {topic.upper()} | PRIORITY: CRITICAL\n\n"
            f"Commander {commander} had faced hard missions before — but none that required "
            f"complete mastery of {topic} before reaching {loc}.\n\n"
            f"Crew member {crew} pulled up the first data packet. "
            f"The ship AI — codename {ai_name} — flagged it immediately: "
            f"'{fkw}. High-relevance signal.'"
        ]
        log_headers = [
            f"NEURAL ARCHIVE — CLUSTER 1\n[{ai_name}] processes primary data:",
            f"MISSION LOG — HOUR 2\nCommander {commander} reviews the critical finding:",
            f"CREW ANNOTATION by {crew}: 'This changes the picture completely:'",
            f"[{ai_name}] ALERT — High-confidence pattern confirmed:",
            f"CLASSIFIED DATA — Commander {commander} reads aloud:",
        ]
        for i, sentence in enumerate(ks[:5]):
            parts.append(f"{log_headers[i % len(log_headers)]}\n\n>> {sentence}\n\n"
                          f"[{ai_name}] Analysis complete. Data integrated.")
        parts.append(
            f"\n\nMISSION DEBRIEF:\n\n{summary}\n\n"
            f"Commander {commander} looked at the stars.\n\n"
            f"'{ai_name}, log this: understanding {topic.lower()} was the mission. We completed it.'\n\n"
            f"[MISSION {topic.upper()} — SUCCESS]"
        )
        return '\n\n'.join(parts)

    def _bedtime(self, ks, summary, topic, child, elder, friend, kw, cd):
        loc = cd['locations'][0] if cd['locations'] else 'a warm room'
        time = cd['time_context']
        fkw = kw[0] if kw else topic.lower()
        dlg = cd['dialogues'][0] if cd['dialogues'] else None
        parts = [
            f"It was {time}, and the {loc} was just the right kind of quiet.\n\n"
            f"{child} settled close to {elder} and asked the question "
            f"that had been waiting all day:\n\n\"Tell me about {topic.lower()}.\"\n\n"
            f"{elder} smiled. 'It begins,' they said gently, 'with {fkw}.'"
        ]
        gentle = [
            f"\"Now here's the first important part,\" said {elder} softly:",
            f"\"{child}, this is the piece your friend {friend} always asks about:\"",
            f"\"Are you following so far? Good. Because now comes the heart of it:\"",
            f"\"This part surprised even me the first time I heard it:\"",
            f"\"Almost there. Just one more thing you need to know:\"",
        ]
        for i, sentence in enumerate(ks[:5]):
            parts.append(f"{gentle[i % len(gentle)]}\n\n{sentence}\n\n"
                          f"{child} nodded slowly. 'I think I understand that.'")
        if dlg:
            parts.append(f"'Do you know what someone once said about this?' asked {elder}.\n\n"
                          f"'{dlg}'\n\n{child} thought about it. 'That makes sense.'")
        parts.append(
            f"\n\n{child}'s eyes were growing heavy.\n\n"
            f"\"So to put it all together,\" {elder} whispered:\n\n{summary}\n\n"
            f"\"Is that everything about {topic.lower()}?\"\n\n"
            f"\"That's all you need tonight. The rest you'll discover yourself — "
            f"that's the best kind of learning.\"\n\n"
            f"And {child} drifted off to sleep."
        )
        return '\n\n'.join(parts)

    def _news(self, ks, summary, topic, reporter, anchor, crew, kw, cd):
        loc = cd['locations'][0] if cd['locations'] else 'the scene'
        time = cd['time_context']
        fkw = kw[0] if kw else topic.lower()
        parts = [
            f"🔴 BREAKING — LIVE COVERAGE\n\n"
            f"ANCHOR: We interrupt regular programming. The story: {topic.upper()}. "
            f"Correspondent {reporter} has been on the ground since {time}.\n\n"
            f"REPORTER {reporter.upper()}: We are at the {loc}. "
            f"The first confirmed finding concerns {fkw}."
        ]
        updates = [
            f"REPORTER {reporter.upper()} — LIVE UPDATE:",
            f"ANCHOR: New information, {reporter}?\n\nREPORTER: Yes — sources confirm:",
            f"BREAKING DEVELOPMENT:",
            f"EXCLUSIVE — our investigation reveals:",
            f"ANCHOR: Final confirmation?\n\nREPORTER: Confirmed and verified:",
        ]
        for i, sentence in enumerate(ks[:5]):
            parts.append(f"{updates[i % len(updates)]}\n\n{sentence}\n\nANCHOR: Remarkable. Continue.")
        parts.append(
            f"\n\nANCHOR: The complete picture, {reporter}?\n\n"
            f"REPORTER {reporter.upper()}:\n\n{summary}\n\n"
            f"ANCHOR: That wraps our live special on {topic.upper()}."
        )
        return '\n\n'.join(parts)

    def _sports(self, ks, summary, topic, athlete, coach, rival, kw, cd):
        loc = cd['locations'][0] if cd['locations'] else 'the arena'
        time = cd['time_context']
        fkw = kw[0] if kw else topic.lower()
        parts = [
            f"🎙️ LIVE FROM THE {loc.upper()}! It is {time} and the crowd is electric.\n\n"
            f"Tonight's challenge: {topic.upper()}. Our champion {athlete.upper()}, "
            f"trained by Coach {coach}, steps up. The opening play: "
            f"{athlete} goes straight for {fkw}. THE CROWD ERUPTS!"
        ]
        plays = [
            f"PLAY 1 — {athlete} drives into the first key section:",
            f"INCREDIBLE! Coach {coach}'s preparation is showing! The key move:",
            f"THE CROWD HOLDS ITS BREATH — the crucial moment:",
            f"RIVAL {rival.upper()} thought this would stop the charge — WRONG!",
            f"UNSTOPPABLE! Total focus, total preparation:",
        ]
        for i, sentence in enumerate(ks[:5]):
            parts.append(f"{plays[i % len(plays)]}\n\n{sentence}\n\n"
                          f"THE SCOREBOARD UPDATES! {athlete} is dominating!")
        parts.append(
            f"\n\nFULL TIME!\n\n{athlete.upper()} HAS CONQUERED {topic.upper()}!\n\n"
            f"The complete performance:\n\n{summary}\n\n"
            f"Coach {coach}: 'This is what real preparation looks like.' LEGENDARY."
        )
        return '\n\n'.join(parts)

    def _mythology(self, ks, summary, topic, hero, oracle, companion, kw, cd):
        loc = cd['locations'][0] if cd['locations'] else 'the sacred mountain'
        time = cd['time_context']
        fkw = kw[0] if kw else topic.lower()
        dlg = cd['dialogues'][0] if cd['dialogues'] else None
        parts = [
            f"IN THE AGE OF {time.upper()}, when truth was carved in stone, "
            f"a seeker named {hero} journeyed to {loc}.\n\n"
            f"The oracle {oracle} spoke first:\n\n"
            f"\"The path begins with {fkw}. Listen, seeker, with everything you are.\""
        ]
        divine = [
            f"The first truth was revealed:",
            f"Companion {companion} spoke the ancient words:",
            f"By decree of the ages, the next revelation came:",
            f"{hero} knelt at the altar. The universe answered:",
            f"The prophecy had spoken of this moment:",
        ]
        for i, sentence in enumerate(ks[:5]):
            parts.append(f"{divine[i % len(divine)]}\n\n{sentence}\n\n"
                          f"{hero} bowed. Another truth received.")
        if dlg:
            parts.append(f"The oracle spoke what had never been spoken:\n\n\"{dlg}\"\n\n"
                          f"{hero} was silent. Then: 'Now I understand.'")
        parts.append(
            f"\n\nAt the summit of {loc}, {hero} looked out across all creation.\n\n"
            f"The knowledge of {topic}:\n\n{summary}\n\n"
            f"The oracle {oracle} spoke one last time: "
            f"\"You came seeking {topic.upper()}. You leave carrying it. "
            f"That is the oldest wisdom.\"\n\nEternal. Complete."
        )
        return '\n\n'.join(parts)


# ══════════════════════════════════════════════════════════════════
#  LAYER 6: SMART QUIZ GENERATOR
# ══════════════════════════════════════════════════════════════════

class SmartQuizGenerator:
    """
    Generates 6 types of quiz questions from clean, repaired text.
    All questions use OCR-repaired + rewritten sentences.
    """

    def __init__(self):
        self.nlp = NLPEngine()
        self.summarizer = TextRankSummarizer(self.nlp)
        self.rewriter = SentenceRewriter()

    def generate(self, text: str, level: str = 'intermediate', n_questions: int = 8) -> list:
        clean = self.nlp.clean_text(text)
        structured = self.summarizer.summarize_with_structure(clean)
        key_sentences = structured['key_facts']
        all_sentences = self.rewriter.rewrite_list(self.nlp.extract_sentences(clean))
        keywords = structured['keywords']
        theme = structured['main_theme']
        summary = structured['core_summary']

        questions = []
        questions.extend(self._comprehension_mcq(key_sentences, all_sentences, theme, level))
        questions.extend(self._smart_fill_blank(key_sentences, level))
        questions.extend(self._semantic_true_false(key_sentences, level))
        questions.extend(self._causal_questions(all_sentences, level))
        questions.extend(self._keyword_context_questions(key_sentences, keywords, level))
        questions.extend(self._theme_question(summary, theme, key_sentences, level))

        seen = set()
        unique = []
        for q in questions:
            key = q.get('question', '')[:60].lower()
            if key not in seen and len(key) > 10:
                seen.add(key)
                unique.append(q)

        unique.sort(key=lambda q: q.get('quality_score', 0), reverse=True)
        selected = unique[:n_questions]
        random.shuffle(selected)
        for i, q in enumerate(selected):
            q['id'] = i + 1
            q.pop('quality_score', None)
        return selected

    def _comprehension_mcq(self, key_sentences, all_sentences, theme, level):
        questions = []
        used = set(s[:40] for s in key_sentences)
        pool = [s for s in all_sentences if s[:40] not in used and 8 <= len(s.split()) <= 35]
        for correct in key_sentences[:3]:
            if len(correct.split()) < 7:
                continue
            similar = sorted(pool, key=lambda s: abs(len(s.split()) - len(correct.split())))
            distractors = similar[:3]
            if len(distractors) < 2:
                continue
            options = [correct] + distractors[:3]
            random.shuffle(options)
            questions.append({
                'type': 'mcq',
                'question': 'According to the text, which of the following statements is most accurate?',
                'options': options,
                'answer': correct,
                'explanation': f'This is a key point from the document about {theme}.',
                'difficulty': level, 'topic': theme, 'quality_score': 3,
            })
        return questions

    def _smart_fill_blank(self, key_sentences, level):
        questions = []
        action_words = {
            'said','told','asked','replied','went','came','took','gave',
            'rode','found','refused','believed','knew','heard','felt',
            'discovered','revealed','decided','realized','created','saved',
            'returned','stole','stolen','trusted','proved','showed','visited'
        }
        for sent in key_sentences[:5]:
            words = sent.split()
            if len(words) < 8:
                continue
            best_idx, best_word, best_score = -1, '', 0
            for i, word in enumerate(words):
                clean = re.sub(r'[^a-zA-Z0-9]', '', word)
                if len(clean) < 3:
                    continue
                if clean.lower() in self.nlp.STOPWORDS:
                    continue
                if word.endswith("'s") or word.endswith("s'"):
                    continue
                score = 0
                if clean[0].isupper() and 0 < i < len(words) - 1:
                    score += 4
                if clean.lower() in action_words:
                    score += 3
                if len(clean) >= 5:
                    score += 2
                if re.match(r'^\d+', clean):
                    score += 2
                if score > best_score:
                    best_score, best_idx, best_word = score, i, clean
            if best_idx < 0 or best_score < 2:
                continue
            blanked = words.copy()
            blanked[best_idx] = '___________'
            questions.append({
                'type': 'fill_blank',
                'question': f'Complete the sentence:\n"{" ".join(blanked)}"',
                'answer': best_word,
                'hint': f'{len(best_word)} letters, starts with "{best_word[0].upper()}"',
                'explanation': f'The original sentence: "{sent}"',
                'difficulty': 'beginner' if best_score <= 3 else level,
                'topic': 'document comprehension', 'quality_score': best_score,
            })
        return questions

    def _semantic_true_false(self, key_sentences, level):
        questions = []
        antonyms = {
            'before':'after','after':'before','first':'last','last':'first',
            'found':'lost','lost':'found','gave':'took','took':'gave',
            'agreed':'refused','refused':'agreed','began':'ended','ended':'began',
            'returned':'stole','stole':'returned','trusted':'doubted',
            'guilty':'innocent','innocent':'guilty',
            'healthy':'sick','stronger':'weaker','weaker':'stronger',
            'honest':'dishonest','poor':'rich','rich':'poor',
        }
        all_names = []
        for s in key_sentences:
            all_names.extend(re.findall(r'\b[A-Z][a-z]{2,}\b', s))
        unique_names = list(set(all_names))

        for sent in key_sentences[:4]:
            questions.append({
                'type': 'true_false',
                'question': f'True or False: "{sent}"',
                'answer': 'True',
                'explanation': 'This statement is directly supported by the text.',
                'difficulty': 'beginner', 'topic': 'reading comprehension', 'quality_score': 2,
            })
            mutated, mutation_made = sent, False
            for word, opposite in antonyms.items():
                if re.search(r'\b' + word + r'\b', sent, re.IGNORECASE):
                    mutated = re.sub(r'\b' + word + r'\b', opposite, sent, count=1, flags=re.IGNORECASE)
                    if mutated != sent:
                        mutation_made = True
                        break
            if not mutation_made and len(unique_names) >= 2:
                sent_names = re.findall(r'\b[A-Z][a-z]{2,}\b', sent)
                others = [n for n in unique_names if n not in sent_names]
                if sent_names and others:
                    mutated = sent.replace(sent_names[0], others[0], 1)
                    mutation_made = (mutated != sent)
            if mutation_made:
                questions.append({
                    'type': 'true_false',
                    'question': f'True or False: "{mutated}"',
                    'answer': 'False',
                    'explanation': f'The correct version is: "{sent}"',
                    'difficulty': level, 'topic': 'reading comprehension', 'quality_score': 3,
                })
        return questions[:6]

    def _causal_questions(self, all_sentences, level):
        questions = []
        causal_pairs = [
            (r'(.+?)\s+because\s+(.+)',        'because'),
            (r'(.+?)\s+therefore\s+(.+)',       'therefore'),
            (r'(.+?)\s+thus\s+(.+)',            'thus'),
            (r'(.+?),?\s+as a result,?\s+(.+)', 'as a result'),
            (r'(.+?)\s+led to\s+(.+)',          'led to'),
            (r'(.+?)\s+so that\s+(.+)',         'so that'),
        ]
        for sent in all_sentences:
            if len(questions) >= 3:
                break
            for pattern, keyword in causal_pairs:
                m = re.match(pattern, sent, re.IGNORECASE)
                if not m:
                    continue
                cause_part  = m.group(1).strip()
                effect_part = m.group(2).strip()
                if len(cause_part.split()) < 3 or len(effect_part.split()) < 3:
                    continue
                cause_short  = cause_part[:70] + ('...' if len(cause_part) > 70 else '')
                effect_short = effect_part[:70] + ('...' if len(effect_part) > 70 else '')
                if keyword in ('because', 'thus', 'therefore', 'so that'):
                    q_text  = f'According to the text, what is the result of: "{cause_short}"?'
                    correct = effect_part[:120]
                else:
                    q_text  = f'According to the text, what caused: "{effect_short}"?'
                    correct = cause_part[:120]
                others = [s[:120] for s in all_sentences if s != sent and len(s.split()) >= 6][:3]
                if len(others) < 2:
                    continue
                options = [correct] + others[:3]
                random.shuffle(options)
                questions.append({
                    'type': 'mcq',
                    'question': q_text,
                    'options': options,
                    'answer': correct,
                    'explanation': f'The full sentence: "{sent}"',
                    'difficulty': level, 'topic': 'causal reasoning', 'quality_score': 4,
                })
                break
        return questions

    def _keyword_context_questions(self, key_sentences, keywords, level):
        questions = []
        for kw in keywords[:4]:
            kw_lower = kw.lower()
            containing     = [s for s in key_sentences if kw_lower in s.lower() and len(s.split()) >= 8]
            not_containing = [s for s in key_sentences if kw_lower not in s.lower() and len(s.split()) >= 8]
            if not containing or len(not_containing) < 2:
                continue
            correct = containing[0]
            options = [correct] + not_containing[:3]
            random.shuffle(options)
            questions.append({
                'type': 'mcq',
                'question': f'The text uses the word "{kw}". Which sentence best shows how it is used?',
                'options': options,
                'answer': correct,
                'explanation': f'"{kw}" appears in context: "{correct}"',
                'difficulty': level, 'topic': 'vocabulary in context', 'quality_score': 3,
            })
        return questions

    def _theme_question(self, summary, theme, key_sentences, level):
        if not summary or len(key_sentences) < 3:
            return []
        distractors = [s for s in key_sentences if s[:50] != summary[:50]][:3]
        if len(distractors) < 2:
            return []
        options = [summary] + distractors[:3]
        random.shuffle(options)
        return [{
            'type': 'mcq',
            'question': f'What is the MAIN IDEA of this text about {theme}?',
            'options': options,
            'answer': summary,
            'explanation': 'The main idea covers the overall message of the complete document.',
            'difficulty': level, 'topic': 'main idea / theme', 'quality_score': 5,
        }]


# ══════════════════════════════════════════════════════════════════
#  BACKWARD COMPATIBILITY
# ══════════════════════════════════════════════════════════════════

QuizGenerator = SmartQuizGenerator


# ══════════════════════════════════════════════════════════════════
#  DEMO — python nlp_engine.py
# ══════════════════════════════════════════════════════════════════

if __name__ == '__main__':

    SAROYAN_OCR = """
    This story is about two poor Armenian boys whe Ne toa tribe 8 hallmarks LES
    One day back there in, the good old days £wnes Iwas nine and the world was full
    of every imaginablé kind of magnificence, and life was still a delightful and
    mysterious dream, Thy cd cousin Mourad who was considered crazy by everybody
    who knew him except me me, came. ton my house at four in the morning and woke
    me up tapping on the window AS: Ty room. are trust and honesty.
    My cousin Mourad was sitting on a beautiful white horse. If you were crazy
    about horses the way my cousin Mourad and I an Armenian tribe The Summer of
    the Beautiful White Horse were, it wasn't stealing. My cousin Mourad got off
    the horse. We could keep the horse a year, I said. My cousin Mourad put his
    arms around the horse, pressed his nose into the horse's nose, patted it,
    and then we went away.
    The Garoghlanian family was known throughout the world for its honesty.
    A farmer named John Byro visited and talked sadly about his stolen horse.
    When they met John Byro on the road, he recognized the horse but trusted
    the family's reputation for honesty and did not accuse them.
    Feeling guilty and respecting their family values, the boys returned
    the horse quietly one morning. John Byro later found his horse healthier
    and stronger than before, proving the boys had taken good care of it.
    """

    print("=" * 65)
    print("  NLP ENGINE v6 — FULL PIPELINE TEST")
    print("  Input: Raw OCR from William Saroyan story (with noise)")
    print("=" * 65)

    repairer = OCRTextRepair()
    repaired = repairer.repair(SAROYAN_OCR)
    quality  = repairer.get_quality_score(repaired)
    print(f"\n🔧 OCR REPAIR RESULTS")
    print(f"   Quality: {quality['quality_score']}/100 ({quality['label']})")
    print(f"   Clean words: {quality['clean_words']} | Valid sentences: {quality['valid_sentences']}")
    print(f"\n   Cleaned text (first 400 chars):\n   {repaired[:400]}...")

    nlp = NLPEngine()
    summarizer = TextRankSummarizer(nlp)
    summary = summarizer.summarize(repaired)
    structured = summarizer.summarize_with_structure(repaired)

    print(f"\n📊 TEXTRANK SUMMARY:\n   {summary}")
    print(f"\n   Theme: {structured['main_theme']} | Sentiment: {structured['sentiment']}")
    print(f"   Top keywords: {structured['keywords'][:5]}")

    print(f"\n🎭 STORY MODE — Detective Thriller:")
    st = StoryTransformer()
    result = st.transform_to_story(SAROYAN_OCR, 'detective_thriller')
    print(result['story_text'][:700] + "...\n")

    print(f"\n🧠 SMART QUIZ (5 questions):")
    qgen = SmartQuizGenerator()
    questions = qgen.generate(SAROYAN_OCR, level='intermediate', n_questions=5)
    for q in questions:
        print(f"\n  Q{q['id']} [{q['type'].upper()}] — {q['topic']}")
        print(f"  {q['question'][:100]}")
        print(f"  ✅ Answer: {str(q['answer'])[:90]}")
        if 'hint' in q:
            print(f"  💡 {q['hint']}")