"""
Learning Intelligence Module — v4 PROPERLY FIXED
=================================================
1. CONCEPT EXTRACTOR — pulls real concepts from any document type
2. TEXT EXPANDER     — explains at user's level, generates real PDFs
3. QUIZ GENERATOR    — generates questions FROM the actual document text
4. USER ASSESSOR     — scores and recommends based on quiz results
"""

import re
import random
import json
import collections
import os


# ─────────────────────────────────────────────────────────────────
#  PDF GENERATOR
# ─────────────────────────────────────────────────────────────────

def generate_pdf(title: str, sections: list, output_path: str) -> str:
    """Generate a properly formatted PDF using reportlab."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.colors import HexColor, black
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                     HRFlowable, KeepTogether)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=22*mm, leftMargin=22*mm,
        topMargin=20*mm, bottomMargin=20*mm
    )

    styles = getSampleStyleSheet()

    # Define styles
    S = {
        'title': ParagraphStyle('T', parent=styles['Title'],
            fontSize=20, textColor=HexColor('#4c1d95'),
            spaceAfter=4, fontName='Helvetica-Bold', alignment=TA_CENTER),
        'subtitle': ParagraphStyle('Sub', parent=styles['Normal'],
            fontSize=10, textColor=HexColor('#6b7280'),
            spaceAfter=16, alignment=TA_CENTER),
        'heading': ParagraphStyle('H', parent=styles['Heading2'],
            fontSize=13, textColor=HexColor('#7c3aed'),
            spaceBefore=14, spaceAfter=6, fontName='Helvetica-Bold'),
        'subheading': ParagraphStyle('SH', parent=styles['Normal'],
            fontSize=11, textColor=HexColor('#0891b2'),
            spaceBefore=8, spaceAfter=4, fontName='Helvetica-Bold'),
        'body': ParagraphStyle('B', parent=styles['Normal'],
            fontSize=11, textColor=HexColor('#111827'),
            spaceAfter=7, leading=18, alignment=TA_JUSTIFY),
        'term': ParagraphStyle('Term', parent=styles['Normal'],
            fontSize=11, textColor=HexColor('#065f46'),
            spaceBefore=5, spaceAfter=2, fontName='Helvetica-Bold'),
        'definition': ParagraphStyle('Def', parent=styles['Normal'],
            fontSize=10.5, textColor=HexColor('#374151'),
            spaceAfter=8, leftIndent=14, leading=16),
        'bullet': ParagraphStyle('Bul', parent=styles['Normal'],
            fontSize=11, textColor=HexColor('#111827'),
            spaceAfter=5, leftIndent=18, leading=16),
        'quote': ParagraphStyle('Q', parent=styles['Normal'],
            fontSize=11, textColor=HexColor('#1e3a5f'),
            spaceAfter=8, leftIndent=20, rightIndent=20,
            leading=18, fontName='Helvetica-Oblique'),
        'note': ParagraphStyle('N', parent=styles['Normal'],
            fontSize=9.5, textColor=HexColor('#6b7280'),
            spaceAfter=6, leftIndent=14),
    }

    def safe(t):
        """Escape text for ReportLab."""
        if not t:
            return ''
        return (str(t)
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;'))

    story = []
    story.append(Paragraph(safe(title), S['title']))
    story.append(HRFlowable(width='100%', thickness=1.5, color=HexColor('#7c3aed')))
    story.append(Spacer(1, 5*mm))

    for sec in sections:
        stype = sec.get('type', 'body')
        text = sec.get('text', '').strip()
        sub = sec.get('sub', '').strip()

        if not text and stype not in ('spacer', 'hr'):
            continue

        if stype == 'subtitle':
            story.append(Paragraph(safe(text), S['subtitle']))
        elif stype == 'heading':
            story.append(Spacer(1, 2*mm))
            story.append(Paragraph(safe(text), S['heading']))
        elif stype == 'subheading':
            story.append(Paragraph(safe(text), S['subheading']))
        elif stype == 'body':
            story.append(Paragraph(safe(text), S['body']))
        elif stype == 'term':
            story.append(Paragraph(safe(text), S['term']))
            if sub:
                story.append(Paragraph(safe(sub), S['definition']))
        elif stype == 'bullet':
            story.append(Paragraph(f'• {safe(text)}', S['bullet']))
        elif stype == 'quote':
            story.append(Paragraph(f'"{safe(text)}"', S['quote']))
        elif stype == 'note':
            story.append(Paragraph(safe(text), S['note']))
        elif stype == 'spacer':
            story.append(Spacer(1, 4*mm))
        elif stype == 'hr':
            story.append(Spacer(1, 2*mm))
            story.append(HRFlowable(width='100%', thickness=0.5,
                                     color=HexColor('#d1d5db')))
            story.append(Spacer(1, 2*mm))

    doc.build(story)
    return output_path


# ─────────────────────────────────────────────────────────────────
#  CONCEPT EXTRACTOR
# ─────────────────────────────────────────────────────────────────

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
        'even','back','still','like','about','upon','been','whom','whose',
        'shall','must','done','going','being','having','putting','getting',
        'well','good','bad','little','much','many','long','right','great'
    ])

    ACRONYM_RE = re.compile(r'\b([A-Z]{2,8})\b')
    TECHNICAL_RE = re.compile(
        r'\b([a-z]+(?:tion|ization|isation|ology|ometry|ysis|ithm|ecture'
        r'|ework|ence|ance|ility|icity|ivity|ment|ular|ified|ifying))\b',
        re.IGNORECASE)

    def extract(self, text: str) -> dict:
        # Clean text first
        clean = self._clean(text)
        acronyms = self._find_acronyms(clean)
        technical = self._find_technical_terms(clean)
        difficult = self._find_difficult_words(clean)
        concepts = self._find_key_concepts(clean)
        key_sentences = self._extract_key_sentences(clean)
        people = self._find_people(clean)

        return {
            'acronyms': acronyms,
            'technical_terms': technical,
            'difficult_words': difficult,
            'concepts': concepts,
            'key_sentences': key_sentences,
            'people': people,
            'vocabulary_ordered': self._build_ordered(clean, acronyms, technical, difficult)
        }

    def _clean(self, text: str) -> str:
        text = re.sub(r'--- Page \d+ ---', ' ', text)
        text = re.sub(r'Reprint \d+-\d+', '', text)
        text = re.sub(r'Chap \d+\.indd.*', '', text)
        text = re.sub(r'\d{1,2}/\d{1,2}/\d{4}.*', '', text)
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()

    def _extract_key_sentences(self, text: str) -> list:
        """Extract meaningful sentences for quiz generation."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        result = []
        for s in sentences:
            s = s.strip()
            words = s.split()
            # Good sentence: 8-50 words, has real content
            if 8 <= len(words) <= 60:
                alpha = sum(1 for c in s if c.isalpha())
                if alpha > len(s) * 0.5:
                    result.append(s)
        return result[:60]

    def _find_people(self, text: str) -> list:
        """Find character/person names."""
        names = re.findall(r'\b([A-Z][a-z]{2,})\b', text)
        non_names = {'The','He','She','It','We','You','They','But','And','So',
                     'As','If','When','Then','That','This','His','Her','My',
                     'All','Each','One','Now','For','Not','With','From','By',
                     'True','False','Page','Chapter','Summer','Morning','Evening',
                     'Well','Good','Little','Great','First','Last','Next','Some'}
        freq = collections.Counter(n for n in names if n not in non_names)
        return [{'name': n, 'count': c} for n, c in freq.most_common(8) if c >= 2]

    def _find_acronyms(self, text: str) -> list:
        seen = set()
        results = []
        for m in self.ACRONYM_RE.finditer(text):
            term = m.group(1)
            if term in seen or len(term) < 2:
                continue
            seen.add(term)
            start = max(0, m.start() - 60)
            end = min(len(text), m.end() + 60)
            ctx = text[start:end].replace('\n', ' ').strip()
            results.append({'term': term, 'context': ctx, 'type': 'acronym'})
        return results[:20]

    def _find_technical_terms(self, text: str) -> list:
        words = re.findall(r'\b[a-zA-Z]{6,}\b', text)
        freq = collections.Counter(w.lower() for w in words)
        results = []
        seen = set()
        for word, count in freq.most_common(50):
            if word in self.BASIC_WORDS or word in seen:
                continue
            if self.TECHNICAL_RE.match(word):
                seen.add(word)
                results.append({'term': word, 'frequency': count,
                                 'difficulty': self._score(word), 'type': 'technical'})
        return sorted(results, key=lambda x: x['difficulty'], reverse=True)[:20]

    def _find_difficult_words(self, text: str) -> list:
        words = re.findall(r'\b[a-zA-Z]{7,}\b', text)
        freq = collections.Counter(w.lower() for w in words)
        results = []
        seen = set()
        for word, count in freq.most_common(60):
            if word in self.BASIC_WORDS or word in seen:
                continue
            seen.add(word)
            sc = self._score(word)
            if sc >= 2:
                results.append({'term': word, 'frequency': count,
                                 'difficulty': sc, 'type': 'vocabulary'})
        return sorted(results, key=lambda x: x['difficulty'], reverse=True)[:20]

    def _find_key_concepts(self, text: str) -> list:
        pattern = re.compile(r'\b([A-Z][a-z]+ (?:[A-Z][a-z]+ )*(?:[A-Z][a-z]+|[A-Z]+))\b')
        seen = set()
        results = []
        for m in pattern.finditer(text):
            phrase = m.group(0).strip()
            if phrase.lower() in seen or len(phrase) < 6:
                continue
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
        for item in acronyms:
            all_terms[item['term'].lower()] = item
        for item in technical:
            all_terms[item['term'].lower()] = item
        for item in difficult:
            all_terms[item['term'].lower()] = item
        ordered = []
        seen = set()
        for w in re.findall(r'\b[A-Za-z]{3,}\b', text):
            key = w.lower()
            if key in all_terms and key not in seen:
                seen.add(key)
                ordered.append(all_terms[key])
        return ordered[:30]


# ─────────────────────────────────────────────────────────────────
#  TEXT EXPANDER + PDF GENERATOR
# ─────────────────────────────────────────────────────────────────

class TextExpander:
    """
    Expands or shrinks text at a given level.
    Generates proper PDF output.
    """

    # Knowledge base for technical/academic terms
    TERM_KNOWLEDGE = {
        'OCR': {'full': 'Optical Character Recognition',
                'beginner': 'A technology that reads text from images, like scanning a receipt to make it editable.',
                'intermediate': 'Converts images of text into machine-readable characters using pattern recognition.',
                'advanced': 'Image-to-text pipeline: binarization → segmentation → feature extraction → classification.'},
        'CNN': {'full': 'Convolutional Neural Network',
                'beginner': 'An AI model that recognizes patterns in images, inspired by how human eyes work.',
                'intermediate': 'Deep learning architecture using filter kernels to extract spatial features.',
                'advanced': 'Feedforward network with learned convolutional filters, pooling, and FC layers.'},
        'NLP': {'full': 'Natural Language Processing',
                'beginner': 'Teaching computers to understand human language — like text and speech.',
                'intermediate': 'Computational analysis and generation of human language.',
                'advanced': 'Combines linguistics and ML for tokenization, parsing, NER, and language modeling.'},
        'LSTM': {'full': 'Long Short-Term Memory',
                 'beginner': 'An AI that can remember earlier parts of text to understand full meaning.',
                 'intermediate': 'Recurrent neural network variant that preserves long-range dependencies.',
                 'advanced': 'RNN with input/forget/output gates controlling memory cell information flow.'},
        'CLAHE': {'full': 'Contrast Limited Adaptive Histogram Equalization',
                  'beginner': 'Makes dark images clearer by brightening them without washing out bright areas.',
                  'intermediate': 'Local contrast enhancement that handles uneven illumination in images.',
                  'advanced': 'Adaptive HE variant that clips peaks to limit noise amplification.'},
        'CER': {'full': 'Character Error Rate',
                'beginner': 'Percentage of individual letters the OCR got wrong (0% = perfect).',
                'intermediate': 'Character-level edit distance divided by reference length.',
                'advanced': 'Levenshtein distance normalized by reference length; complements WER.'},
        'WER': {'full': 'Word Error Rate',
                'beginner': 'Like CER but counts whole wrong words instead of letters.',
                'intermediate': 'Word-level edit distance normalized by reference word count.',
                'advanced': '(substitutions + deletions + insertions) / reference words.'},
        'algorithm': {'beginner': 'A step-by-step recipe a computer follows to solve a problem.',
                      'intermediate': 'A defined sequence of operations for solving a computational problem.',
                      'advanced': 'Formal procedure with defined complexity characteristics.'},
        'pipeline': {'beginner': 'A chain of steps where each step\'s output feeds into the next.',
                     'intermediate': 'Sequential processing chain where data flows through transformation stages.',
                     'advanced': 'Directed graph of processing nodes optimized for throughput.'},
        'binarization': {'beginner': 'Converting a grey image to pure black-and-white.',
                         'intermediate': 'Thresholding operation converting grayscale to binary values.',
                         'advanced': 'Adaptive thresholding: Otsu, Sauvola, or Niblack methods.'},
        'confidence': {'beginner': 'How sure the AI is — 95% means almost certain, 40% means guessing.',
                       'intermediate': 'Probability score the model assigns to its predictions.',
                       'advanced': 'Posterior from softmax; calibration aligns confidence with empirical accuracy.'},
    }

    def expand(self, text: str, level: str, concepts_data: dict) -> dict:
        """Expand text with explanations at the given level."""
        glossary = self._build_glossary(concepts_data, level)
        annotated = self._annotate_text(text, glossary, level)
        pre_reading = self._build_pre_reading(concepts_data, level)
        simplified = self._simplify_if_needed(text, level)

        return {
            'annotated_text': annotated,
            'glossary': glossary,
            'pre_reading': pre_reading,
            'simplified_summary': simplified,
            'level': level,
            'total_terms_explained': len(glossary)
        }

    def expand_to_pdf(self, text: str, level: str, concepts_data: dict,
                       output_path: str) -> str:
        """Generate a full annotated learning PDF."""
        glossary = self._build_glossary(concepts_data, level)
        pre_reading = self._build_pre_reading(concepts_data, level)
        annotated = self._annotate_text(text, glossary, level)
        simplified = self._simplify_if_needed(text, level)

        level_label = {
            'beginner': '🌱 Beginner Level',
            'intermediate': '📘 Intermediate Level',
            'advanced': '🚀 Advanced Level'
        }.get(level, level.title())

        sections = []
        sections.append({'type': 'subtitle', 'text': f'Adaptive Learning Document — {level_label}'})

        # Pre-reading
        if pre_reading:
            sections.append({'type': 'heading', 'text': '📚 Pre-Reading — Know These First'})
            sections.append({'type': 'note', 'text': 'Understand these terms before reading the main content.'})
            for p in pre_reading[:8]:
                sections.append({'type': 'term', 'text': f"📌 {p['term']}",
                                  'sub': p['explanation']})
            sections.append({'type': 'hr', 'text': ''})

        # Main content
        sections.append({'type': 'heading', 'text': '📄 Document Content — Annotated'})
        sections.append({'type': 'note',
                          'text': f'Key terms have been annotated inline at the {level_label}.'})
        sections.append({'type': 'spacer', 'text': ''})

        # Split annotated text into paragraphs
        for para in annotated.split('\n\n'):
            para = para.strip()
            if para:
                sections.append({'type': 'body', 'text': para})

        # Simplified version for beginners
        if simplified and level == 'beginner':
            sections.append({'type': 'hr', 'text': ''})
            sections.append({'type': 'heading', 'text': '🌱 Plain-Language Summary'})
            sections.append({'type': 'note', 'text': 'The key ideas in simple words.'})
            for sent in simplified.split('. '):
                sent = sent.strip()
                if sent and len(sent) > 15:
                    sections.append({'type': 'bullet', 'text': sent})

        # Glossary
        if glossary:
            sections.append({'type': 'hr', 'text': ''})
            sections.append({'type': 'heading',
                              'text': f'📖 Glossary — {len(glossary)} Terms Explained'})
            sections.append({'type': 'note',
                              'text': f'All terms explained at the {level_label}.'})
            for g in glossary:
                full = f" ({g['full_form']})" if g.get('full_form') else ''
                sections.append({
                    'type': 'term',
                    'text': f"{g['term']}{full}",
                    'sub': g.get('explanation', 'See domain references.')
                })

        return generate_pdf(f'IntelliDoc — Learning Document', sections, output_path)

    def shrink_to_pdf(self, text: str, output_path: str, ratio: float = 0.3) -> str:
        """Generate a condensed summary PDF."""
        from heapq import nlargest

        stop = set(['a','an','the','is','was','are','were','be','been','have','has',
                    'had','do','does','did','will','would','could','should','and',
                    'or','but','not','with','this','that','from','by','as','into',
                    'at','on','in','to','for','of','it','its','we','you','he','she',
                    'they','them','their','our','said','just','very','some','all',
                    'also','even','back','still','more','most','when','where','what'])

        # Clean text
        clean = re.sub(r'--- Page \d+ ---', ' ', text)
        clean = re.sub(r'Reprint \d+-\d+', '', clean)
        clean = re.sub(r'Chap \d+\.indd.*', '', clean)
        clean = re.sub(r'[ \t]+', ' ', clean).strip()

        # Extract sentences
        raw_sents = re.split(r'(?<=[.!?])\s+(?=[A-Z"(])', clean)
        sentences = []
        for s in raw_sents:
            s = s.strip()
            words = s.split()
            if len(words) >= 6 and len(s) < 400:
                alpha = sum(1 for c in s if c.isalpha())
                if alpha > len(s) * 0.5:
                    sentences.append(s)

        if not sentences:
            sentences = [clean[:500]]

        # Score sentences
        all_words = [w.lower() for s in sentences for w in re.findall(r'\b[a-zA-Z]+\b', s)]
        freq = collections.Counter(t for t in all_words if t not in stop and len(t) > 3)

        scores = {}
        for i, s in enumerate(sentences):
            toks = re.findall(r'\b[a-zA-Z]+\b', s.lower())
            sc = sum(freq.get(t, 0) for t in toks if t not in stop)
            if len(toks) > 0:
                sc = sc / len(toks)
            if i == 0: sc *= 1.7
            elif i <= 2: sc *= 1.3
            elif i == len(sentences)-1: sc *= 1.2
            if len(toks) < 5: sc *= 0.4
            scores[i] = sc

        n = max(4, min(10, int(len(sentences) * ratio)))
        top_idx = sorted(nlargest(n, scores, key=scores.get))
        summary = [sentences[i] for i in top_idx]

        # Characters/names found
        names = re.findall(r'\b([A-Z][a-z]{2,})\b', clean)
        non = {'The','He','She','It','We','You','They','But','And','So','As',
               'If','When','Then','That','This','His','Her','My','All','Each'}
        nfreq = collections.Counter(n for n in names if n not in non)
        chars = [n for n, _ in nfreq.most_common(5) if _ >= 2]

        # Keywords
        kw = [w for w, _ in freq.most_common(10)]

        sections = []
        sections.append({'type': 'subtitle',
                          'text': f'Condensed Summary — {len(summary)} key sentences from {len(sentences)} total'})

        sections.append({'type': 'heading', 'text': '📋 Summary'})
        for sent in summary:
            sections.append({'type': 'body', 'text': sent})

        sections.append({'type': 'hr', 'text': ''})
        sections.append({'type': 'heading', 'text': '🔑 Key Points'})
        for sent in summary[:6]:
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
        glossary = []
        seen = set()
        kb = self.TERM_KNOWLEDGE

        # From acronyms
        for item in concepts_data.get('acronyms', []):
            term = item['term']
            if term in seen:
                continue
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

        # From technical terms
        for item in concepts_data.get('technical_terms', [])[:12]:
            term = item['term'].lower()
            if term in seen:
                continue
            seen.add(term)
            info = kb.get(term, {})
            exp = info.get(level, info.get('intermediate',
                  f'Technical term appearing {item.get("frequency", 1)}x in document.'))
            glossary.append({
                'term': term,
                'full_form': info.get('full', ''),
                'explanation': exp,
                'context': '',
                'type': 'technical'
            })

        # From difficult words
        for item in concepts_data.get('difficult_words', [])[:8]:
            term = item['term'].lower()
            if term in seen:
                continue
            seen.add(term)
            info = kb.get(term, {})
            exp = info.get(level, info.get('intermediate',
                  f'Important vocabulary word in this document.'))
            glossary.append({
                'term': term,
                'full_form': '',
                'explanation': exp,
                'context': '',
                'type': 'vocabulary'
            })

        return glossary[:25]

    def _annotate_text(self, text: str, glossary: list, level: str) -> str:
        """Add inline annotations without breaking readability."""
        # Clean the text first
        clean = re.sub(r'--- Page \d+ ---', ' ', text)
        clean = re.sub(r'Reprint \d+-\d+', '', clean)
        clean = re.sub(r'Chap \d+\.indd.*', '', clean)
        clean = re.sub(r'[ \t]+', ' ', clean).strip()

        if level == 'beginner':
            # Add brief definitions after first occurrence
            annotated = clean
            for g in glossary[:10]:
                term = g['term']
                exp = g['explanation']
                # Short explanation
                short = exp[:70] + '...' if len(exp) > 70 else exp
                note = f' [{short}]'
                # Only annotate first occurrence
                pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
                annotated = pattern.sub(term + note, annotated, count=1)
            return annotated

        elif level == 'intermediate':
            # Add full forms for acronyms only
            annotated = clean
            for g in glossary[:8]:
                if g.get('full_form'):
                    term = g['term']
                    full = g['full_form']
                    pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
                    annotated = pattern.sub(f'{term} ({full})', annotated, count=1)
            return annotated

        else:
            # Advanced: minimal, just full forms
            annotated = clean
            for g in glossary[:5]:
                if g.get('full_form'):
                    term = g['term']
                    full = g['full_form']
                    annotated = re.sub(r'\b' + re.escape(term) + r'\b',
                                       f'{term} [{full}]', annotated, count=1, flags=re.IGNORECASE)
            return annotated

    def _build_pre_reading(self, concepts_data: dict, level: str) -> list:
        if level == 'advanced':
            return []
        pre = []
        seen = set()
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
        sentences = re.split(r'(?<=[.!?])\s+', text)
        simple = []
        for s in sentences:
            s = s.strip()
            words = s.split()
            # Pick clear, relatively short sentences
            if 8 <= len(words) <= 30 and s.count(',') <= 2:
                simple.append(s)
        return ' '.join(simple[:8])


# ─────────────────────────────────────────────────────────────────
#  QUIZ GENERATOR — FROM ACTUAL DOCUMENT CONTENT
# ─────────────────────────────────────────────────────────────────

class QuizGenerator:
    """
    Generates quiz questions directly from the uploaded document's text.
    
    Types of questions:
    1. Who/What/Where questions from document sentences
    2. Fill-in-the-blank from important sentences
    3. True/False from actual document statements
    4. Multiple choice from key facts in the document
    5. Acronym expansion (for technical docs)
    """

    QUESTION_WORDS = ['who', 'what', 'where', 'when', 'why', 'how', 'which']

    def generate(self, text: str, concepts_data: dict, level: str,
                 n_questions: int = 8) -> list:
        """Generate questions from the actual document text."""

        # Clean the text
        clean = self._clean(text)
        key_sentences = concepts_data.get('key_sentences',
                                           self._extract_key_sentences(clean))
        people = concepts_data.get('people', [])

        questions = []

        # 1. Generate fill-in-the-blank from important sentences
        questions.extend(self._fill_blank_from_text(key_sentences, level))

        # 2. True/False from document sentences
        questions.extend(self._true_false_from_text(key_sentences, level))

        # 3. Who/What questions based on character names and events
        questions.extend(self._who_what_questions(key_sentences, people, level))

        # 4. MCQ from document facts (select the correct statement)
        questions.extend(self._fact_mcq(key_sentences, level))

        # 5. Acronym questions (if technical doc)
        questions.extend(self._acronym_questions(concepts_data))

        # Deduplicate
        seen = set()
        unique = []
        for q in questions:
            key = q.get('question', '')[:60].lower()
            if key not in seen:
                seen.add(key)
                unique.append(q)

        # Shuffle and select
        random.shuffle(unique)
        selected = unique[:n_questions]

        # Add IDs
        for i, q in enumerate(selected):
            q['id'] = i + 1
            if 'difficulty' not in q:
                q['difficulty'] = level

        return selected

    def _clean(self, text: str) -> str:
        text = re.sub(r'--- Page \d+ ---', ' ', text)
        text = re.sub(r'Reprint \d+-\d+', '', text)
        text = re.sub(r'Chap \d+\.indd.*', '', text)
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()

    def _extract_key_sentences(self, text: str) -> list:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        result = []
        for s in sentences:
            s = s.strip()
            words = s.split()
            if 8 <= len(words) <= 60:
                alpha = sum(1 for c in s if c.isalpha())
                if alpha > len(s) * 0.5:
                    result.append(s)
        return result[:50]

    def _fill_blank_from_text(self, sentences: list, level: str) -> list:
        """
        Creates fill-in-blank by removing an important word from a sentence.
        Only blanks out: names (capitalized), numbers, specific content words.
        """
        questions = []
        skip_words = {'the','a','an','is','was','are','were','be','been','and',
                      'or','but','not','with','this','that','from','by','as','it',
                      'he','she','they','we','i','his','her','their','our','you',
                      'said','had','have','has','did','do','does','will','would',
                      'could','should','very','just','also','even','then','when',
                      'where','what','who','how','all','some','any','no','more',
                      'much','many','few','each','every','both','other','another',
                      'into','upon','about','after','before','through','during'}

        good_sentences = [s for s in sentences if len(s.split()) >= 10]
        random.shuffle(good_sentences)

        for sent in good_sentences[:20]:
            if len(questions) >= 4:
                break

            words = sent.split()
            # Find a good word to blank — prefer: names, numbers, content words >5 chars
            candidates = []
            for i, word in enumerate(words):
                clean_word = re.sub(r'[^a-zA-Z0-9]', '', word)
                if not clean_word or len(clean_word) < 3:
                    continue
                if clean_word.lower() in skip_words:
                    continue
                # Prefer: capitalized words (names), longer words
                score = 0
                if clean_word[0].isupper() and i > 0:  # name
                    score += 3
                if len(clean_word) >= 5:
                    score += 2
                if clean_word.isdigit():
                    score += 2
                if score >= 2:
                    candidates.append((i, word, clean_word, score))

            if not candidates:
                continue

            # Pick highest scoring candidate
            candidates.sort(key=lambda x: x[3], reverse=True)
            idx, original_word, clean_answer, _ = candidates[0]

            blanked = words.copy()
            blanked[idx] = '_________'
            question_text = ' '.join(blanked)

            questions.append({
                'type': 'fill_blank',
                'question': f'Fill in the blank based on the document:<br><em>"{question_text}"</em>',
                'answer': clean_answer,
                'hint': f'Hint: {len(clean_answer)} letters, starts with "{clean_answer[0].upper()}"',
                'explanation': f'From the document: "{sent}"',
                'difficulty': 'beginner' if len(clean_answer) <= 5 else level,
                'topic': 'document content'
            })

        return questions

    def _true_false_from_text(self, sentences: list, level: str) -> list:
        """
        True/False using real sentences + mutated versions.
        """
        questions = []
        good = [s for s in sentences if 12 <= len(s.split()) <= 40]
        random.shuffle(good)

        mutations = [
            ('not ', ''), ('never ', 'always '), ('always ', 'never '),
            ('before ', 'after '), ('after ', 'before '),
            ('could not', 'could'), ('could', 'could not'),
            ('refused', 'agreed'), ('agreed', 'refused'),
            ('stolen', 'bought'), ('bought', 'stolen'),
            ('beautiful', 'ugly'), ('kind', 'cruel'),
            ('happy', 'sad'), ('sad', 'happy'),
        ]

        for sent in good[:8]:
            if len(questions) >= 4:
                break

            # TRUE question
            questions.append({
                'type': 'true_false',
                'question': f'True or False: <em>"{sent}"</em>',
                'answer': 'True',
                'explanation': 'This statement appears directly in the document.',
                'difficulty': 'beginner',
                'topic': 'reading comprehension'
            })

            # Try to create a FALSE version by mutation
            mutated = sent
            mutated_ok = False
            for orig, repl in mutations:
                if orig.lower() in sent.lower():
                    mutated = re.sub(re.escape(orig), repl, sent, count=1, flags=re.IGNORECASE)
                    if mutated != sent:
                        mutated_ok = True
                        break

            if mutated_ok and len(questions) < 4:
                questions.append({
                    'type': 'true_false',
                    'question': f'True or False: <em>"{mutated}"</em>',
                    'answer': 'False',
                    'explanation': f'The correct version is: "{sent}"',
                    'difficulty': 'beginner',
                    'topic': 'reading comprehension'
                })

        return questions[:4]

    def _who_what_questions(self, sentences: list, people: list, level: str) -> list:
        """
        Generate WHO/WHAT questions from sentences that contain character names.
        """
        questions = []
        if not people:
            return questions

        people_names = [p['name'] if isinstance(p, dict) else p for p in people]

        for sent in sentences:
            if len(questions) >= 4:
                break

            # Find sentences that mention a person AND describe an action
            for name in people_names:
                if name in sent and len(sent.split()) >= 8:
                    # What did [name] do?
                    # Check if there's a clear action verb
                    if re.search(r'\b(said|told|asked|replied|went|came|took|gave|'
                                 r'rode|stolen|found|refused|believed|knew|heard|'
                                 r'jumped|cried|laughed|felt|looked|wanted|wished)\b',
                                 sent, re.IGNORECASE):
                        # Generate MCQ options using other sentences about the same person
                        other_sents = [s for s in sentences
                                       if name in s and s != sent and len(s.split()) >= 6]

                        wrong_options = []
                        for ws in other_sents[:3]:
                            # Trim to make a plausible-sounding option
                            ws_words = ws.split()
                            if len(ws_words) > 15:
                                ws = ' '.join(ws_words[:15]) + '...'
                            wrong_options.append(ws)

                        if len(wrong_options) >= 2:
                            correct = sent
                            options = [correct] + wrong_options[:3]
                            random.shuffle(options)
                            questions.append({
                                'type': 'mcq',
                                'question': f'Which of the following best describes what <strong>{name}</strong> does in the story?',
                                'options': options,
                                'answer': correct,
                                'explanation': f'This is stated directly in the document.',
                                'difficulty': level,
                                'topic': f'{name}\'s actions'
                            })
                            break

        return questions[:3]

    def _fact_mcq(self, sentences: list, level: str) -> list:
        """
        Multiple choice: one correct statement from the document vs. others.
        """
        questions = []
        good = [s for s in sentences if 10 <= len(s.split()) <= 35]

        if len(good) < 4:
            return questions

        random.shuffle(good)

        for i in range(0, min(len(good)-3, 12), 4):
            if len(questions) >= 3:
                break
            correct = good[i]
            wrongs = good[i+1:i+4]

            if len(wrongs) < 2:
                continue

            options = [correct] + wrongs[:3]
            random.shuffle(options)

            questions.append({
                'type': 'mcq',
                'question': 'Which of the following statements is taken directly from the document?',
                'options': options,
                'answer': correct,
                'explanation': 'This sentence appears word-for-word in the original text.',
                'difficulty': level,
                'topic': 'document recall'
            })

        return questions

    def _acronym_questions(self, concepts_data: dict) -> list:
        """What does X stand for? — from document acronyms."""
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
            options = [correct] + wrong
            random.shuffle(options)
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


# ─────────────────────────────────────────────────────────────────
#  USER LEVEL ASSESSOR
# ─────────────────────────────────────────────────────────────────

class UserLevelAssessor:

    def calculate_score(self, answers: list, questions: list) -> dict:
        question_map = {q['id']: q for q in questions}
        topic_scores = collections.defaultdict(lambda: {'correct': 0, 'total': 0})
        details = []
        correct_count = 0

        for ans in answers:
            q = question_map.get(ans['id'])
            if not q:
                continue
            topic = q.get('topic', 'General')
            given = str(ans.get('given', '')).strip().lower()
            correct = str(q.get('answer', '')).strip().lower()

            # Flexible matching
            is_correct = (given == correct or
                          given[:30] in correct[:50] or
                          correct[:30] in given[:50] or
                          (len(given) > 3 and given in correct))

            topic_scores[topic]['total'] += 1
            if is_correct:
                topic_scores[topic]['correct'] += 1
                correct_count += 1

            details.append({
                'id': q['id'],
                'question': q['question'],
                'given': ans.get('given', ''),
                'correct_answer': q['answer'],
                'is_correct': is_correct,
                'explanation': q.get('explanation', ''),
                'topic': topic
            })

        total = len(answers)
        pct = round(correct_count / total * 100) if total > 0 else 0

        skill_meters = {}
        for topic, scores in topic_scores.items():
            tp = round(scores['correct'] / scores['total'] * 100) if scores['total'] > 0 else 0
            skill_meters[topic] = {
                'score': tp,
                'correct': scores['correct'],
                'total': scores['total'],
                'level': 'Strong' if tp >= 80 else ('Developing' if tp >= 55 else 'Needs Work')
            }

        weak = [t for t, s in skill_meters.items() if s['score'] < 50]
        strong = [t for t, s in skill_meters.items() if s['score'] >= 75]
        inferred = 'advanced' if pct >= 75 else ('intermediate' if pct >= 45 else 'beginner')

        return {
            'overall_score': pct,
            'correct': correct_count,
            'total': total,
            'inferred_level': inferred,
            'skill_meters': skill_meters,
            'weak_areas': weak,
            'strong_areas': strong,
            'details': details,
            'recommendations': self._recommendations(inferred, weak, strong)
        }

    def _recommendations(self, level, weak, strong) -> list:
        recs = []
        if level == 'beginner':
            recs.append('📚 Read the glossary carefully before re-reading the document.')
            recs.append('🔤 Use the Beginner Learning View for plain-language explanations.')
            recs.append('🌙 Try Story Mode — it makes the same content much easier to absorb.')
        elif level == 'intermediate':
            recs.append('🧩 Use the Intermediate Learning View for annotated explanations.')
            recs.append('📊 Focus on the sections where you scored lowest.')
        else:
            recs.append('🚀 Try the Advanced Learning View for deep technical annotations.')
            recs.append('🔬 You have strong comprehension — focus on applying the concepts.')
        for area in weak[:2]:
            recs.append(f'⚠️ Weak area: <strong>{area}</strong> — revisit this in the document.')
        for area in strong[:1]:
            recs.append(f'✅ Strong area: <strong>{area}</strong> — solid understanding here.')
        return recs