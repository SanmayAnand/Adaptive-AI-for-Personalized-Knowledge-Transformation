"""
Learning Intelligence Module
==============================
Two major features:
1. ADAPTIVE TEXT EXPANSION  — explain text at the user's level,
   pre-teach concepts/words before they appear, expand jargon, etc.
2. USER LEVEL ASSESSMENT    — quiz generated FROM the document's content,
   skill meters, weak/strong area detection, adaptive recommendations.
"""

import re
import random
import json
import collections
import os


# ─────────────────────────────────────────────────────────────────
#  CONCEPT & VOCABULARY EXTRACTOR
# ─────────────────────────────────────────────────────────────────

class ConceptExtractor:
    """
    Pulls out difficult words, technical terms, acronyms, and concepts
    from the extracted OCR text so we can explain them proactively.
    """

    # Common simple words we don't need to explain
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
        'than','too','such','then','these','those','here','there','about'
    ])

    # Patterns for different concept types
    ACRONYM_RE = re.compile(r'\b([A-Z]{2,8})\b')
    TECHNICAL_RE = re.compile(
        r'\b([a-z]+(?:tion|ization|isation|ology|ometry|ography|ometry'
        r'|ysis|ithm|ecture|ework|ization|isation|ence|ance|ility|icity'
        r'|ivity|ment|ation|ular|ular|ified|ifying))\b', re.IGNORECASE)
    HYPHENATED_RE = re.compile(r'\b([a-z]+-[a-z]+(?:-[a-z]+)?)\b', re.IGNORECASE)

    # Difficulty scoring: longer words, rare suffixes = harder
    HARD_SUFFIXES = ['ification', 'ization', 'ography', 'ometry', 'ithm',
                     'ecture', 'ology', 'ysis', 'icular']

    def extract(self, text: str) -> dict:
        """
        Returns: {
          'acronyms': [{'term': 'OCR', 'context': '...'}],
          'technical_terms': [...],
          'difficult_words': [...],
          'concepts': [...],   # multi-word important phrases
          'vocabulary_ordered': [...]  # in order they first appear in text
        }
        """
        acronyms = self._find_acronyms(text)
        technical = self._find_technical_terms(text)
        difficult = self._find_difficult_words(text)
        concepts = self._find_concepts(text)
        ordered = self._build_ordered_vocabulary(text, acronyms, technical, difficult)

        return {
            'acronyms': acronyms,
            'technical_terms': technical,
            'difficult_words': difficult,
            'concepts': concepts,
            'vocabulary_ordered': ordered
        }

    def _find_acronyms(self, text: str) -> list:
        matches = self.ACRONYM_RE.finditer(text)
        seen = set()
        results = []
        for m in matches:
            term = m.group(1)
            if term in seen or len(term) < 2:
                continue
            seen.add(term)
            # Get surrounding context
            start = max(0, m.start() - 60)
            end = min(len(text), m.end() + 60)
            context = text[start:end].replace('\n', ' ').strip()
            results.append({'term': term, 'context': context, 'type': 'acronym'})
        return results[:30]

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
                difficulty = self._score_difficulty(word)
                results.append({
                    'term': word,
                    'frequency': count,
                    'difficulty': difficulty,
                    'type': 'technical'
                })
        return sorted(results, key=lambda x: x['difficulty'], reverse=True)[:20]

    def _find_difficult_words(self, text: str) -> list:
        words = re.findall(r'\b[a-zA-Z]{8,}\b', text)
        freq = collections.Counter(w.lower() for w in words)
        results = []
        seen = set()
        for word, count in freq.most_common(60):
            if word in self.BASIC_WORDS or word in seen:
                continue
            seen.add(word)
            difficulty = self._score_difficulty(word)
            if difficulty >= 3:
                results.append({
                    'term': word,
                    'frequency': count,
                    'difficulty': difficulty,
                    'type': 'vocabulary'
                })
        return sorted(results, key=lambda x: x['difficulty'], reverse=True)[:25]

    def _find_concepts(self, text: str) -> list:
        """Multi-word noun phrases that represent key concepts."""
        pattern = re.compile(
            r'\b([A-Z][a-z]+ (?:[A-Z][a-z]+ )*(?:[A-Z][a-z]+|[A-Z]+))\b'
        )
        matches = pattern.finditer(text)
        seen = set()
        results = []
        for m in matches:
            phrase = m.group(0).strip()
            if phrase.lower() in seen or len(phrase) < 8:
                continue
            seen.add(phrase.lower())
            results.append({'term': phrase, 'type': 'concept'})
        return results[:20]

    def _score_difficulty(self, word: str) -> int:
        score = 0
        if len(word) >= 12: score += 3
        elif len(word) >= 9: score += 2
        elif len(word) >= 7: score += 1
        for suf in self.HARD_SUFFIXES:
            if word.endswith(suf):
                score += 2
                break
        return score

    def _build_ordered_vocabulary(self, text: str, acronyms, technical, difficult) -> list:
        """Return vocabulary in the order terms first appear in text."""
        all_terms = {}
        for item in acronyms:
            all_terms[item['term'].lower()] = item
        for item in technical:
            all_terms[item['term'].lower()] = item
        for item in difficult:
            all_terms[item['term'].lower()] = item

        ordered = []
        seen = set()
        words_in_order = re.findall(r'\b[A-Za-z]{3,}\b', text)
        for w in words_in_order:
            key = w.lower()
            if key in all_terms and key not in seen:
                seen.add(key)
                ordered.append(all_terms[key])
        return ordered[:40]


# ─────────────────────────────────────────────────────────────────
#  TEXT EXPANSION ENGINE
# ─────────────────────────────────────────────────────────────────

class TextExpander:
    """
    Takes extracted text and enriches it based on user's level.
    - Beginner: explain every term, add analogies, define acronyms inline
    - Intermediate: explain technical terms, skip obvious ones
    - Advanced: light annotations, focus on domain-specific nuances
    """

    # Built-in mini knowledge base for common tech/academic terms
    # (no API needed — this is pre-loaded knowledge)
    TERM_KNOWLEDGE = {
        # OCR/CV terms
        'OCR': {
            'full': 'Optical Character Recognition',
            'beginner': 'A technology that reads text from images, like how you photograph a receipt and it becomes editable text.',
            'intermediate': 'Converts raster images of text into machine-readable character data using pattern recognition.',
            'advanced': 'Image-to-text conversion pipeline combining binarization, segmentation, feature extraction, and classification.'
        },
        'CNN': {
            'full': 'Convolutional Neural Network',
            'beginner': 'A type of AI brain that is especially good at recognizing patterns in images, inspired by how human eyes work.',
            'intermediate': 'Deep learning architecture using sliding filter kernels to extract spatial features hierarchically.',
            'advanced': 'Feedforward network with learned convolutional filters, pooling, and fully-connected layers for spatial feature extraction.'
        },
        'NLP': {
            'full': 'Natural Language Processing',
            'beginner': 'Teaching computers to read, understand, and work with human language — like text and speech.',
            'intermediate': 'Computational techniques for analyzing, understanding, and generating human language.',
            'advanced': 'Subfield of AI combining linguistics and ML for tasks like tokenization, parsing, NER, and language modeling.'
        },
        'NER': {
            'full': 'Named Entity Recognition',
            'beginner': 'AI that identifies important names in text — people, places, organizations, dates.',
            'intermediate': 'NLP task that classifies tokens in text into predefined categories such as person, location, or organization.',
            'advanced': 'Sequence labeling task using IOB tagging schemes, often approached with CRF or transformer-based architectures.'
        },
        'LSTM': {
            'full': 'Long Short-Term Memory',
            'beginner': 'A type of AI that can remember things from earlier in a sentence to understand the full meaning.',
            'intermediate': 'Recurrent neural network variant with gating mechanisms to preserve long-range dependencies.',
            'advanced': 'RNN architecture with input, forget, and output gates controlling information flow through memory cells.'
        },
        'PSM': {
            'full': 'Page Segmentation Mode',
            'beginner': 'A setting that tells Tesseract how to split up the image — is it one word, one line, or a full page?',
            'intermediate': 'Tesseract parameter controlling how the engine segments text regions before recognition.',
            'advanced': 'Tesseract\'s PSM controls layout analysis from single character (PSM 10) to full auto-segment (PSM 3).'
        },
        'OEM': {
            'full': 'OCR Engine Mode',
            'beginner': 'Tells Tesseract which AI model to use — the older fast one or the newer smarter LSTM one.',
            'intermediate': 'Tesseract parameter selecting between legacy engine, LSTM, or combined recognition modes.',
            'advanced': 'OEM 3 uses both legacy and LSTM engines with automatic selection; OEM 1 forces pure LSTM (Tesseract 4+).'
        },
        'CLAHE': {
            'full': 'Contrast Limited Adaptive Histogram Equalization',
            'beginner': 'A technique that makes dark images clearer by brightening them intelligently without washing out bright areas.',
            'intermediate': 'Local contrast enhancement that applies histogram equalization in small tiles to handle uneven illumination.',
            'advanced': 'Adaptive HE variant that clips histogram peaks to limit noise amplification in uniform regions.'
        },
        'CER': {
            'full': 'Character Error Rate',
            'beginner': 'Measures how many letters the OCR got wrong. 0% is perfect, 100% means every letter is wrong.',
            'intermediate': 'Ratio of character-level edit distance to reference length; standard OCR accuracy metric.',
            'advanced': 'Levenshtein distance at character level normalized by reference length; complements WER for fine-grained evaluation.'
        },
        'WER': {
            'full': 'Word Error Rate',
            'beginner': 'Like CER but counts whole wrong words instead of individual letters.',
            'intermediate': 'Word-level edit distance normalized by reference word count.',
            'advanced': 'Standard ASR/OCR metric; computed as (substitutions + deletions + insertions) / reference words.'
        },
        # General academic/tech
        'algorithm': {
            'beginner': 'A step-by-step recipe a computer follows to solve a problem — like a cooking recipe but for data.',
            'intermediate': 'A defined sequence of operations for solving a computational problem with measurable complexity.',
            'advanced': 'Formal procedure with defined inputs, outputs, and time/space complexity characteristics.'
        },
        'pipeline': {
            'beginner': 'A series of steps where the output of one step automatically becomes the input of the next.',
            'intermediate': 'Sequential processing chain where data flows through transformation stages.',
            'advanced': 'Directed acyclic graph of processing nodes optimized for throughput and latency.'
        },
        'preprocessing': {
            'beginner': 'Cleaning up data before the main work — like washing vegetables before cooking.',
            'intermediate': 'Data cleaning and normalization steps applied before the primary analysis or modeling.',
            'advanced': 'Feature engineering and noise reduction to improve downstream model performance and convergence.'
        },
        'binarization': {
            'beginner': 'Converting a grey or coloured image to pure black-and-white so text stands out clearly.',
            'intermediate': 'Thresholding operation that converts grayscale pixels to binary (0 or 1) values.',
            'advanced': 'Adaptive or global thresholding techniques including Otsu, Sauvola, and Niblack methods.'
        },
        'segmentation': {
            'beginner': 'Splitting an image into separate meaningful parts, like cutting a cake into slices.',
            'intermediate': 'Partitioning an image or text stream into meaningful regions or units for analysis.',
            'advanced': 'Pixel-level classification or region proposal used in semantic, instance, or panoptic contexts.'
        },
        'tokenization': {
            'beginner': 'Breaking a sentence into individual words or pieces so a computer can analyze each one.',
            'intermediate': 'Splitting text into tokens (words, subwords, or characters) as the first NLP processing step.',
            'advanced': 'Encoding scheme selection — BPE, WordPiece, SentencePiece — affects vocabulary size and OOV handling.'
        },
        'normalization': {
            'beginner': 'Making data consistent — like converting all text to lowercase so "Hello" and "hello" are treated the same.',
            'intermediate': 'Standardizing data to a common format or scale to reduce noise and improve comparability.',
            'advanced': 'Layer normalization, batch normalization, or text canonicalization depending on context.'
        },
        'confidence': {
            'beginner': 'How sure the AI is about its answer — 95% confident means it\'s almost certain, 40% means it\'s guessing.',
            'intermediate': 'Probability score assigned by a model to its predictions, indicating certainty level.',
            'advanced': 'Posterior probability from softmax output; calibration techniques align confidence with empirical accuracy.'
        },
        'fine-tuning': {
            'beginner': 'Taking an AI that already knows a lot and training it more on your specific topic to make it better for you.',
            'intermediate': 'Continuing to train a pre-trained model on domain-specific data to adapt it to a new task.',
            'advanced': 'Transfer learning technique adjusting pre-trained weights via low learning rate gradient updates.'
        },
    }

    def expand(self, text: str, level: str, concepts_data: dict) -> dict:
        """
        Returns expanded content at the right level.
        level: 'beginner' | 'intermediate' | 'advanced'
        Returns {
            'annotated_text': text with inline annotations,
            'glossary': ordered list of term explanations,
            'pre_reading': concepts to understand before reading,
            'simplified_summary': if beginner, a plain-language summary
        }
        """
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

    def _build_glossary(self, concepts_data: dict, level: str) -> list:
        glossary = []
        seen = set()

        # From acronyms
        for item in concepts_data.get('acronyms', []):
            term = item['term']
            if term in seen:
                continue
            seen.add(term)
            kb = self.TERM_KNOWLEDGE.get(term, {})
            entry = {
                'term': term,
                'type': 'acronym',
                'full_form': kb.get('full', f'[{term}] — acronym found in document'),
                'explanation': kb.get(level, kb.get('intermediate', 'Technical term used in this document.')),
                'context': item.get('context', '')
            }
            glossary.append(entry)

        # From technical terms
        for item in concepts_data.get('technical_terms', []):
            term = item['term'].lower()
            if term in seen:
                continue
            seen.add(term)
            kb = self.TERM_KNOWLEDGE.get(term, {})
            if kb or item.get('difficulty', 0) >= 3:
                entry = {
                    'term': item['term'],
                    'type': 'technical',
                    'full_form': None,
                    'explanation': kb.get(level, self._generic_explanation(item['term'], level)),
                    'context': ''
                }
                glossary.append(entry)

        return glossary[:30]

    def _generic_explanation(self, word: str, level: str) -> str:
        """Generate a generic explanation for unknown terms."""
        if level == 'beginner':
            return f'"{word}" is a technical term used in this field. Look it up if unsure.'
        elif level == 'intermediate':
            return f'Technical term: "{word}" — see domain references for precise definition.'
        else:
            return f'Domain-specific term: {word}.'

    def _annotate_text(self, text: str, glossary: list, level: str) -> str:
        """Add [?] markers after terms that have explanations."""
        if level == 'advanced':
            return text  # advanced users don't need inline markers

        term_map = {g['term'].lower(): g for g in glossary}
        lines = text.split('\n')
        result = []
        for line in lines:
            words = line.split()
            new_words = []
            for word in words:
                clean = re.sub(r'[^a-zA-Z]', '', word).lower()
                if clean in term_map:
                    new_words.append(word + '†')  # † marks annotated terms
                else:
                    new_words.append(word)
            result.append(' '.join(new_words))
        return '\n'.join(result)

    def _build_pre_reading(self, concepts_data: dict, level: str) -> list:
        """
        Concepts you should understand BEFORE reading the document.
        Ordered from most fundamental to most specific.
        """
        pre = []
        if level == 'beginner':
            # Give all acronyms as pre-reading
            for item in concepts_data.get('acronyms', [])[:8]:
                kb = self.TERM_KNOWLEDGE.get(item['term'], {})
                if kb:
                    pre.append({
                        'term': item['term'],
                        'why_needed': f'This term appears early in the document.',
                        'explanation': kb.get('beginner', kb.get('intermediate', ''))
                    })
        elif level == 'intermediate':
            for item in concepts_data.get('technical_terms', [])[:6]:
                kb = self.TERM_KNOWLEDGE.get(item['term'], {})
                if kb:
                    pre.append({
                        'term': item['term'],
                        'why_needed': f'Core concept used throughout the document.',
                        'explanation': kb.get('intermediate', '')
                    })
        return pre[:8]

    def _simplify_if_needed(self, text: str, level: str) -> str:
        """For beginners, produce a plain-English version."""
        if level != 'beginner':
            return ''
        # Replace known hard terms with simple equivalents
        replacements = {
            r'\bpreprocessing\b': 'cleaning up the data',
            r'\bbinarization\b': 'converting to black and white',
            r'\bsegmentation\b': 'splitting into parts',
            r'\btokenization\b': 'breaking into words',
            r'\bnormalization\b': 'standardizing',
            r'\barchitecture\b': 'design/structure',
            r'\bpipeline\b': 'series of steps',
            r'\balgorithm\b': 'step-by-step process',
            r'\bconfidence score\b': 'how sure the AI is',
            r'\bfine-tuning\b': 'further training',
            r'\bparameter\b': 'setting/option',
            r'\bthreshold\b': 'cutoff point',
        }
        simplified = text
        for pattern, replacement in replacements.items():
            simplified = re.sub(pattern, replacement, simplified, flags=re.IGNORECASE)
        return simplified[:1500]  # cap length for display


# ─────────────────────────────────────────────────────────────────
#  QUIZ GENERATOR
# ─────────────────────────────────────────────────────────────────

class QuizGenerator:
    """
    Generates questions FROM the document content.
    Question types:
    - Acronym expansion (What does OCR stand for?)
    - Definition MCQ (What is binarization?)
    - True/False from document facts
    - Fill-in-the-blank from key sentences
    - Concept ordering (arrange pipeline steps)
    """

    def generate(self, text: str, concepts_data: dict, level: str, n_questions: int = 10) -> list:
        """
        Generate n_questions questions appropriate for the level.
        Returns list of question dicts.
        """
        questions = []

        # 1. Acronym questions (great for all levels)
        qs = self._acronym_questions(concepts_data)
        questions.extend(qs)

        # 2. Definition MCQ from knowledge base
        qs = self._definition_mcq(concepts_data, level)
        questions.extend(qs)

        # 3. Fill-in-the-blank from document text
        qs = self._fill_in_blank(text, level)
        questions.extend(qs)

        # 4. True/False
        qs = self._true_false(text, concepts_data)
        questions.extend(qs)

        # 5. Ordering question (pipeline steps)
        qs = self._ordering_question(text)
        questions.extend(qs)

        # Shuffle and pick n
        random.shuffle(questions)
        selected = questions[:n_questions]

        # Tag difficulty
        for i, q in enumerate(selected):
            q['id'] = i + 1
            if 'difficulty' not in q:
                q['difficulty'] = level

        return selected

    def _acronym_questions(self, concepts_data: dict) -> list:
        questions = []
        kb = TextExpander.TERM_KNOWLEDGE
        acronyms = [a['term'] for a in concepts_data.get('acronyms', []) if a['term'] in kb]

        for term in acronyms[:5]:
            info = kb[term]
            if 'full' not in info:
                continue
            # What does X stand for?
            correct = info['full']
            # Generate wrong options from other full forms
            wrong_pool = [v['full'] for k, v in kb.items()
                          if k != term and 'full' in v and v['full'] != correct]
            wrong = random.sample(wrong_pool, min(3, len(wrong_pool)))
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

    def _definition_mcq(self, concepts_data: dict, level: str) -> list:
        questions = []
        kb = TextExpander.TERM_KNOWLEDGE
        found_terms = (
            [a['term'] for a in concepts_data.get('acronyms', [])] +
            [t['term'].lower() for t in concepts_data.get('technical_terms', [])]
        )

        for term in found_terms[:8]:
            if term not in kb:
                continue
            info = kb[term]
            explanation = info.get(level, info.get('intermediate', ''))
            if not explanation or len(explanation) < 20:
                continue

            # "Which best describes X?"
            correct = explanation
            wrong_pool = [v.get(level, v.get('intermediate', ''))
                          for k, v in kb.items()
                          if k != term and v.get(level, v.get('intermediate', ''))]
            wrong_pool = [w for w in wrong_pool if w != correct and len(w) > 20]
            wrong = random.sample(wrong_pool, min(3, len(wrong_pool)))
            if not wrong:
                continue
            options = [correct] + wrong
            random.shuffle(options)
            questions.append({
                'type': 'mcq',
                'question': f'Which statement best describes <strong>{term.upper() if len(term) <= 5 else term}</strong>?',
                'options': options,
                'answer': correct,
                'explanation': info.get('advanced', explanation),
                'difficulty': level,
                'topic': term
            })
        return questions

    def _fill_in_blank(self, text: str, level: str) -> list:
        """Extract key sentences and blank out important words."""
        questions = []
        # Find sentences with technical terms
        sentences = re.split(r'(?<=[.!?])\s+', text)
        kb_terms = set(TextExpander.TERM_KNOWLEDGE.keys())

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 40 or len(sentence) > 200:
                continue
            # Find a blankable term
            words = sentence.split()
            for i, word in enumerate(words):
                clean = re.sub(r'[^a-zA-Z]', '', word)
                if clean.upper() in kb_terms or clean.lower() in kb_terms:
                    blanked = words.copy()
                    blanked[i] = '___________'
                    question_text = ' '.join(blanked)
                    questions.append({
                        'type': 'fill_blank',
                        'question': f'Fill in the blank: <em>"{question_text}"</em>',
                        'answer': clean,
                        'hint': f'Hint: {len(clean)} letters, starts with "{clean[0]}"',
                        'explanation': TextExpander.TERM_KNOWLEDGE.get(
                            clean.upper(),
                            TextExpander.TERM_KNOWLEDGE.get(clean.lower(), {})
                        ).get('intermediate', ''),
                        'difficulty': level,
                        'topic': clean
                    })
                    break
            if len(questions) >= 4:
                break
        return questions

    def _true_false(self, text: str, concepts_data: dict) -> list:
        """Generate true/false questions from document statements."""
        questions = []
        sentences = re.split(r'(?<=[.!?])\s+', text)
        kb = TextExpander.TERM_KNOWLEDGE

        true_sentences = [s.strip() for s in sentences
                          if 40 < len(s.strip()) < 180 and
                          any(k.lower() in s.lower() for k in kb)][:4]

        for sentence in true_sentences:
            # TRUE question: real sentence from doc
            questions.append({
                'type': 'true_false',
                'question': f'True or False: <em>"{sentence}"</em>',
                'answer': 'True',
                'explanation': 'This statement appears directly in the document.',
                'difficulty': 'beginner',
                'topic': 'document comprehension'
            })

            # FALSE question: mutate the sentence
            mutated = self._mutate_sentence(sentence)
            if mutated and mutated != sentence:
                questions.append({
                    'type': 'true_false',
                    'question': f'True or False: <em>"{mutated}"</em>',
                    'answer': 'False',
                    'explanation': f'The actual statement is: "{sentence}"',
                    'difficulty': 'beginner',
                    'topic': 'document comprehension'
                })

        return questions[:4]

    def _mutate_sentence(self, sentence: str) -> str:
        """Flip a word to make a sentence false."""
        replacements = {
            'not': '', '': 'not ', 'high': 'low', 'low': 'high',
            'before': 'after', 'after': 'before', 'always': 'never',
            'never': 'always', 'increase': 'decrease', 'decrease': 'increase',
            'correct': 'incorrect', 'accurate': 'inaccurate',
            'improves': 'worsens', 'better': 'worse',
            'extracts': 'ignores', 'enhances': 'degrades'
        }
        for orig, replacement in replacements.items():
            if orig and orig in sentence.lower():
                return re.sub(orig, replacement, sentence, count=1, flags=re.IGNORECASE)
        return ''

    def _ordering_question(self, text: str) -> list:
        """Find pipeline/step sequences in the document."""
        # Look for arrows or numbered lists suggesting sequence
        arrow_pattern = re.compile(r'(\w[\w\s]{2,20})\s*[→→>]\s*(\w[\w\s]{2,20})')
        matches = arrow_pattern.findall(text)
        if len(matches) >= 3:
            steps = [m[0].strip() for m in matches[:5]]
            shuffled = steps.copy()
            random.shuffle(shuffled)
            if shuffled != steps:
                return [{
                    'type': 'ordering',
                    'question': 'Arrange these pipeline steps in the correct order:',
                    'items': shuffled,
                    'answer': steps,
                    'explanation': 'This is the correct processing sequence from the document.',
                    'difficulty': 'intermediate',
                    'topic': 'pipeline architecture'
                }]
        return []


# ─────────────────────────────────────────────────────────────────
#  USER LEVEL ASSESSOR
# ─────────────────────────────────────────────────────────────────

class UserLevelAssessor:
    """
    Manages the full user assessment flow:
    1. Self-reported level + intentions
    2. Quiz from document content
    3. Skill meter calculation per topic
    4. Weak area identification
    5. Personalized study recommendations
    """

    TOPICS = ['Core Concepts', 'Technical Terms', 'Architecture', 'Pipeline Steps', 'Applications']

    def calculate_score(self, answers: list, questions: list) -> dict:
        """
        answers: [{'id': 1, 'given': 'user answer'}, ...]
        questions: original question list
        Returns score breakdown by topic and overall.
        """
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
            is_correct = given == correct or given in correct or correct in given

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
        overall_pct = round(correct_count / total * 100) if total > 0 else 0

        # Build skill meters
        skill_meters = {}
        for topic, scores in topic_scores.items():
            pct = round(scores['correct'] / scores['total'] * 100) if scores['total'] > 0 else 0
            skill_meters[topic] = {
                'score': pct,
                'correct': scores['correct'],
                'total': scores['total'],
                'level': self._pct_to_level(pct)
            }

        weak_areas = [t for t, s in skill_meters.items() if s['score'] < 50]
        strong_areas = [t for t, s in skill_meters.items() if s['score'] >= 75]
        inferred_level = self._infer_level(overall_pct)

        return {
            'overall_score': overall_pct,
            'correct': correct_count,
            'total': total,
            'inferred_level': inferred_level,
            'skill_meters': skill_meters,
            'weak_areas': weak_areas,
            'strong_areas': strong_areas,
            'details': details,
            'recommendations': self._get_recommendations(inferred_level, weak_areas, strong_areas)
        }

    def _pct_to_level(self, pct: int) -> str:
        if pct >= 80: return 'Strong'
        if pct >= 55: return 'Developing'
        return 'Needs Work'

    def _infer_level(self, pct: int) -> str:
        if pct >= 75: return 'advanced'
        if pct >= 45: return 'intermediate'
        return 'beginner'

    def _get_recommendations(self, level: str, weak: list, strong: list) -> list:
        recs = []
        if level == 'beginner':
            recs.append('📚 Start with the Glossary — read all term definitions before the main text.')
            recs.append('🔤 Use "Expand Text (Beginner)" mode to get plain-language explanations inline.')
            recs.append('🎯 Focus on understanding acronyms first — they appear frequently.')
        elif level == 'intermediate':
            recs.append('🧩 Use "Expand Text (Intermediate)" to get precise technical definitions.')
            recs.append('📊 Read the architecture section carefully — focus on how steps connect.')
        else:
            recs.append('🚀 Use "Expand Text (Advanced)" for implementation-focused annotations.')
            recs.append('🔬 Focus on the Confidence & Error Analysis sections for depth.')

        for area in weak[:2]:
            recs.append(f'⚠️ Weak area: <strong>{area}</strong> — review the related glossary entries.')
        for area in strong[:1]:
            recs.append(f'✅ Strong area: <strong>{area}</strong> — you can skim this section.')

        return recs
