"""
NLP Reasoning Engine — v4 PROPERLY FIXED
Proper summarization, story transformation, text transformation.
Works correctly on any text including English chapters, technical docs, stories.
"""

import re
import string
import collections
import random
from heapq import nlargest


# ─────────────────────────────────────────────
#  CORE NLP UTILITIES
# ─────────────────────────────────────────────

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
        'DATE': r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|'
                r'(?:January|February|March|April|May|June|July|August|September|'
                r'October|November|December)\s+\d{1,2},?\s+\d{4})\b',
        'URL': r'https?://[^\s<>"{}|\\^`\[\]]+',
        'MONEY': r'\$\s?\d+(?:,\d{3})*(?:\.\d{2})?|\d+(?:,\d{3})*\s?(?:USD|EUR|GBP|INR)',
        'PERCENTAGE': r'\d+\.?\d*\s?%',
        'PERSON_NAME': r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b',
        'ACRONYM': r'\b[A-Z]{2,6}\b',
    }

    def normalize(self, text: str) -> str:
        """Basic normalization."""
        text = text.replace('|', 'I')
        text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def clean_text(self, text: str) -> str:
        """
        Deep clean: remove OCR noise, page markers, artifacts.
        Returns clean, readable text.
        """
        # Fix common OCR character errors
        text = text.replace('|', 'I')
        text = text.replace("'", "'").replace("'", "'")
        text = text.replace('"', '"').replace('"', '"')

        # Fix hyphenated line breaks
        text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)

        # Remove page markers and publication info
        text = re.sub(r'---\s*Page \d+\s*---', ' ', text)
        text = re.sub(r'Reprint \d{4}-\d{2}', '', text)
        text = re.sub(r'Chap \d+\.indd \d+.*', '', text)
        text = re.sub(r'\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M', '', text)

        # Remove isolated special characters
        text = re.sub(r'\s[\\\/\~\^\`\<\>\[\]{}|]{1,3}\s', ' ', text)
        text = re.sub(r'^[\\\/\~\^\`\<\>\[\]{}|]+$', '', text, flags=re.MULTILINE)

        # Fix spaces before punctuation
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)
        text = re.sub(r'([a-z])\s*\n\s*([a-z])', r'\1 \2', text)

        # Clean up whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove lines that are clearly garbage
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            # Skip very short lines (likely OCR artifacts)
            if len(line) < 3:
                continue
            # Skip lines that are only numbers/symbols
            if re.match(r'^[\d\s\-\—\–\.\,\>\<\|\/\\]+$', line):
                continue
            # Skip lines that look like print info
            if re.match(r'^\d+\s*$', line):
                continue
            lines.append(line)

        return ' '.join(lines).strip()

    def extract_sentences(self, text: str) -> list:
        """Extract clean, meaningful sentences."""
        text = self.clean_text(text)

        # Split on sentence boundaries
        # Handle dialogue and multiple punctuation
        raw = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'(])', text)

        sentences = []
        for s in raw:
            s = s.strip()
            # Must be long enough
            if len(s) < 15:
                continue
            # Must have real words
            words = re.findall(r'\b[a-zA-Z]{2,}\b', s)
            if len(words) < 4:
                continue
            # Must not be just OCR garbage
            alpha_ratio = len(''.join(re.findall(r'[a-zA-Z]', s))) / max(len(s), 1)
            if alpha_ratio < 0.5:
                continue
            sentences.append(s)

        return sentences

    def tokenize(self, text: str) -> list:
        tokens = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        return tokens

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
        freq = collections.Counter(tokens)
        return freq.most_common(top_n)

    def validate_grammar_basic(self, text: str) -> list:
        issues = []
        for s in self.extract_sentences(text):
            if s and s[0].islower():
                issues.append(f"Sentence may not start correctly: '{s[:40]}'")
        return issues[:10]


# ─────────────────────────────────────────────
#  TEXT TRANSFORMER
# ─────────────────────────────────────────────

class TextTransformer:
    """
    Proper text transformation. Summarization that actually works
    on literary, academic, and technical text.
    """

    def __init__(self):
        self.nlp = NLPEngine()

    def summarize(self, text: str, ratio: float = 0.35, max_sentences: int = 8) -> str:
        """
        TF-IDF-style extractive summarization.
        Selects most informative sentences, preserves original order.
        Works on stories, chapters, technical docs.
        """
        text_clean = self.nlp.clean_text(text)
        sentences = self.nlp.extract_sentences(text_clean)

        if not sentences:
            return text_clean[:600]
        if len(sentences) <= 3:
            return ' '.join(sentences)

        # Build word frequencies (TF)
        all_words = []
        for s in sentences:
            all_words.extend(self.nlp.tokenize(s))
        content_words = [w for w in all_words if w not in self.nlp.STOPWORDS and len(w) > 3]
        freq = collections.Counter(content_words)
        max_freq = freq.most_common(1)[0][1] if freq else 1

        # Score each sentence
        scores = {}
        for i, sentence in enumerate(sentences):
            words = self.nlp.tokenize(sentence)
            cw = [w for w in words if w not in self.nlp.STOPWORDS and len(w) > 3]
            if not cw:
                scores[i] = 0
                continue

            # TF score normalized by sentence length
            score = sum(freq.get(w, 0) / max_freq for w in cw) / len(cw)

            # Position bonuses
            pos = i / len(sentences)
            if i == 0: score *= 1.7          # first sentence very important
            elif i == 1: score *= 1.3
            elif i == len(sentences)-1: score *= 1.2  # last sentence important
            elif pos < 0.15: score *= 1.2    # early in doc

            # Length penalties
            wc = len(words)
            if wc < 5: score *= 0.4
            elif wc < 8: score *= 0.7
            elif wc > 60: score *= 0.7

            # Bonus for containing named entities (people, places)
            if re.search(r'\b[A-Z][a-z]{2,}\b', sentence):
                score *= 1.1

            # Bonus for dialogue (interesting for stories)
            if '"' in sentence or "'" in sentence:
                score *= 1.05

            scores[i] = max(score, 0)

        n = max(3, min(max_sentences, int(len(sentences) * ratio)))
        top_indices = sorted(nlargest(n, scores, key=scores.get))
        top_sentences = [sentences[i] for i in top_indices]

        return ' '.join(top_sentences)

    def extract_information(self, text: str) -> dict:
        text_clean = self.nlp.clean_text(text)
        entities = self.nlp.named_entity_recognition(text_clean)
        keywords = self.nlp.get_keywords(text_clean, top_n=15)
        sentences = self.nlp.extract_sentences(text_clean)

        # Extract character names (for literary text)
        names = re.findall(r'\b([A-Z][a-z]{2,})\b', text_clean)
        non_names = {'The','He','She','It','We','You','They','But','And','So',
                     'As','If','When','Then','That','This','His','Her','My',
                     'All','Each','One','Now','But','For','Not','With','From'}
        name_freq = collections.Counter(n for n in names if n not in non_names)
        characters = [(n, c) for n, c in name_freq.most_common(8) if c >= 2]

        # Extract dialogue
        dialogues = re.findall(r'["""]([^"""]{10,150})["""]', text_clean)

        # Extract key-value style pairs (for technical text)
        kv = {}
        for m in re.finditer(r'([A-Z][a-z]{2,30}):\s*([^\n]{5,60})', text_clean):
            kv[m.group(1)] = m.group(2).strip()

        return {
            'named_entities': entities,
            'top_keywords': keywords,
            'characters': characters,
            'dialogue_lines': dialogues[:6],
            'key_value_pairs': kv,
            'sentence_count': len(sentences),
            'word_count': len(text_clean.split()),
            'char_count': len(text_clean)
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
        return {
            'redacted_text': redacted_text,
            'redaction_log': redaction_log,
            'items_redacted': len(redaction_log)
        }

    def format_text(self, text: str, style: str = 'clean') -> str:
        text = self.nlp.clean_text(text)
        if style == 'bullet_points':
            sentences = self.nlp.extract_sentences(text)
            return '\n'.join(f'• {s}' for s in sentences)
        elif style == 'markdown':
            return self._to_markdown(text)
        return text

    def _to_markdown(self, text: str) -> str:
        headings = self._extract_headings(text)
        result = []
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                result.append('')
            elif line in headings:
                result.append(f'## {line}')
            else:
                result.append(line)
        return '\n'.join(result)

    def _extract_headings(self, text: str) -> list:
        lines = text.split('\n')
        headings = []
        for line in lines:
            line = line.strip()
            if (8 < len(line) < 80 and
                    line[0].isupper() and
                    not line.endswith(('.', ',', ';', '?', '!')) and
                    len(line.split()) <= 8):
                headings.append(line)
        return headings[:10]

    def classify_and_tag(self, text: str) -> dict:
        tl = text.lower()
        categories = {
            'Academic/Research': ['abstract','methodology','conclusion','hypothesis','experiment','analysis','results','study','research'],
            'Legal/Contract': ['hereby','pursuant','jurisdiction','liability','indemnify','clause','agreement','party','terms'],
            'Medical/Health': ['patient','diagnosis','treatment','clinical','medication','symptoms','disease','healthcare','doctor'],
            'Financial': ['revenue','profit','loss','balance','quarter','fiscal','investment','assets','market'],
            'Technical/Engineering': ['algorithm','system','architecture','implementation','module','pipeline','processing','neural'],
            'News/Article': ['according','reported','announced','sources','officials','government','minister'],
            'Literary/Story': ['said','replied','whispered','heart','love','felt','horse','rode','stolen','cousin','morning','summer','family'],
            'Educational': ['chapter','lesson','exercise','curriculum','student','teacher','learn','textbook'],
        }
        scores = {cat: sum(1 for kw in kws if kw in tl) for cat, kws in categories.items()}
        best = max(scores, key=scores.get)
        conf = round(min(scores[best] / max(len(categories[best]) * 0.3, 1) * 100, 100), 1)
        keywords = self.nlp.get_keywords(text, top_n=10)
        tags = [kw[0] for kw in keywords]
        pos_words = ['good','great','excellent','happy','beautiful','wonderful','love','joy','success']
        neg_words = ['poor','bad','fail','stolen','afraid','frightened','sad','angry','wrong','problem']
        pos_score = sum(1 for w in pos_words if w in tl)
        neg_score = sum(1 for w in neg_words if w in tl)
        sentiment = 'Positive' if pos_score > neg_score else ('Negative' if neg_score > pos_score else 'Neutral')
        return {
            'document_type': best,
            'type_confidence': conf,
            'all_scores': dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)),
            'semantic_tags': tags,
            'sentiment': sentiment,
            'language': 'English'
        }


# ─────────────────────────────────────────────
#  STORY TRANSFORMER — PROPERLY WORKING
# ─────────────────────────────────────────────

class StoryTransformer:
    """
    Transforms extracted text into different narrative styles.
    Produces coherent, readable, engaging stories.
    """

    STYLE_CONFIGS = {
        'romantic': {
            'name': '💕 Romantic Story',
            'description': 'Concepts as a love story — perfect for any chapter or topic',
        },
        'detective_thriller': {
            'name': '🔍 Detective Thriller',
            'description': 'Concepts as a mystery to solve — great for any topic',
        },
        'sci_fi': {
            'name': '🚀 Sci-Fi Adventure',
            'description': 'A futuristic space mission retelling — perfect for any subject',
        },
        'bedtime_story': {
            'name': '🌙 Bedtime Story',
            'description': 'A gentle, warm retelling — ideal for beginners',
        },
        'news_reporter': {
            'name': '📰 Breaking News',
            'description': 'Reported as urgent live news — engaging for any topic',
        },
        'sports_commentary': {
            'name': '🏆 Sports Commentary',
            'description': 'A live sports commentary retelling — energetic and fun',
        },
        'mythology': {
            'name': '⚡ Epic Mythology',
            'description': 'Ancient myths and legends style — magical for any topic',
        },
    }

    def __init__(self):
        self.nlp = NLPEngine()

    def get_available_styles(self) -> list:
        return [{'key': k, 'name': v['name'], 'description': v['description']}
                for k, v in self.STYLE_CONFIGS.items()]

    def transform_to_story(self, text: str, style: str, custom_characters: str = '') -> dict:
        if style not in self.STYLE_CONFIGS:
            style = 'detective_thriller'

        clean = self.nlp.clean_text(text)
        sentences = self.nlp.extract_sentences(clean)

        if not sentences:
            sentences = re.split(r'[.!?]+', clean)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

        keywords = dict(self.nlp.get_keywords(clean, top_n=20))
        topic = self._detect_topic(clean, keywords)

        # Auto-detect characters from text
        auto_chars = self._find_characters(clean)
        chars = self._parse_characters(custom_characters, auto_chars, topic)

        # Build proper narrative paragraphs from content
        # Group sentences into content blocks of 3-4 sentences
        blocks = []
        for i in range(0, len(sentences), 4):
            block = sentences[i:i+4]
            if block:
                blocks.append(' '.join(block))

        story = self._build_story(blocks, style, topic, chars, keywords)

        words = story.split()
        return {
            'story_text': story,
            'style_used': self.STYLE_CONFIGS[style]['name'],
            'style_key': style,
            'topic_detected': topic,
            'concepts_woven': list(keywords.keys())[:10],
            'reading_time_minutes': max(1, round(len(words) / 200)),
            'word_count': len(words),
            'original_word_count': len(clean.split()),
        }

    def _find_characters(self, text: str) -> list:
        names = re.findall(r'\b([A-Z][a-z]{2,})\b', text)
        non_names = {'The','He','She','It','We','You','They','But','And','So',
                     'As','If','When','Then','That','This','His','Her','My',
                     'All','Each','One','Now','For','Not','With','From','By',
                     'True','False','Page','Chapter','Summer','Morning','Evening'}
        freq = collections.Counter(n for n in names if n not in non_names)
        return [n for n, _ in freq.most_common(5) if _ >= 2]

    def _parse_characters(self, custom: str, auto: list, topic: str) -> dict:
        chars = {}
        if custom:
            for part in custom.split(','):
                part = part.strip()
                if ':' in part:
                    role, name = part.split(':', 1)
                    chars[role.strip().lower()] = name.strip()

        defaults_1 = ['Arjun', 'Rohan', 'Dev', 'Kiran', 'Rajan', 'Vikram']
        defaults_2 = ['Priya', 'Maya', 'Ananya', 'Riya', 'Kavya', 'Nisha']
        defaults_mentor = ['Dr. Rao', 'Professor Singh', 'Dr. Meera', 'Master Krishnan']

        if 'protagonist' not in chars:
            chars['protagonist'] = auto[0] if auto else random.choice(defaults_1)
        if 'mentor' not in chars:
            chars['mentor'] = auto[1] if len(auto) > 1 else random.choice(defaults_mentor)
        if 'sidekick' not in chars:
            chars['sidekick'] = auto[2] if len(auto) > 2 else random.choice(defaults_2)

        return chars

    def _detect_topic(self, text: str, keywords: dict) -> str:
        skip = {'said','asked','know','just','like','want','came','went','took',
                'back','could','would','should','been','have','this','that','will',
                'from','with','they','them','their','were','when','what','which',
                'also','very','well','good','more','some','much','many','little',
                'each','every','other','into','been','upon','time','year','day',
                'came','told','made','keep','pass','take','give','come','left'}
        good = [k for k in keywords if len(k) > 4 and k not in skip]
        if good:
            return good[0].title()
        m = re.search(r'\b([A-Z][a-z]{3,}(?:\s+[A-Z][a-z]{3,})*)\b', text)
        return m.group(0) if m else 'the Journey'

    def _build_story(self, blocks: list, style: str, topic: str,
                     chars: dict, keywords: dict) -> str:
        p = chars.get('protagonist', 'Arjun')
        mentor = chars.get('mentor', 'Dr. Rao')
        sidekick = chars.get('sidekick', 'Maya')
        kw_list = [k for k in keywords if len(k) > 4]

        builders = {
            'romantic': self._romantic,
            'detective_thriller': self._detective,
            'sci_fi': self._scifi,
            'bedtime_story': self._bedtime,
            'news_reporter': self._news,
            'sports_commentary': self._sports,
            'mythology': self._mythology,
        }
        fn = builders.get(style, self._detective)
        return fn(blocks, topic, p, mentor, sidekick, kw_list)

    def _romantic(self, blocks, topic, hero, mentor, heroine, kw):
        first_kw = kw[0] if kw else topic
        parts = []
        parts.append(
            f"It was the kind of morning that felt like the beginning of something irreversible.\n\n"
            f"{hero} had never imagined that the story of {topic.lower()} would matter this much — "
            f"that it would unfold like a slow confession, demanding to be heard, demanding to be understood.\n\n"
            f"It had started simply enough. {hero} had picked up the pages, barely paying attention. "
            f"Then came the first line about {first_kw}, and everything changed."
        )

        connectors = [
            f"Hours passed. {hero} barely noticed.",
            f"Something was shifting — quietly, the way important things always do.",
            f"And then came the part that {hero} would remember longest:",
            f"It was {heroine} who first put it into words: \"This is the heart of it, isn't it?\"",
            f"{mentor} had always said that true understanding comes when you stop fighting the text and simply let it speak.",
        ]

        for i, block in enumerate(blocks[:5]):
            conn = connectors[i % len(connectors)]
            parts.append(f"{conn}\n\n{block}")

        parts.append(
            f"\n\nBy the time the last page was turned, {hero} understood something that no summary could have conveyed: "
            f"{topic} was not just a subject. It was a story — one that had been waiting, patient and complete, "
            f"for exactly this moment to be read.\n\n"
            f"Some things you learn. Some things you feel. The story of {topic.lower()} had been both."
        )
        return '\n\n'.join(parts)

    def _detective(self, blocks, topic, detective, captain, partner, kw):
        first_kw = kw[0] if kw else topic
        parts = []
        parts.append(
            f"DETECTIVE {detective.upper()} — CASE FILE: {topic.upper()}\n\n"
            f"The file landed on the desk at 7:43 AM. No cover note. No explanation. "
            f"Just a single word underlined in red: {topic.upper()}.\n\n"
            f"Detective {detective} had solved harder cases. Missing heirs. Forged identities. "
            f"But something about this one was different. The first clue was buried in the opening lines — "
            f"something about {first_kw} that didn't quite add up."
        )

        clues = [
            f"Captain {captain} leaned across the desk. 'What have you found?'\n\n'{detective} ran a hand through his hair. 'This part. Read it.'",
            f"The evidence was clear once you knew what you were looking for:",
            f"Partner {partner} had cracked it. 'The answer was here the whole time,' she said, pointing.",
            f"A second review of the evidence confirmed the theory:",
            f"And then — the breakthrough. {detective} saw the connection that had been hiding in plain sight:",
        ]

        for i, block in enumerate(blocks[:5]):
            cl = clues[i % len(clues)]
            parts.append(f"{cl}\n\n{block}\n\n{detective} circled the key section. Another piece in place.")

        parts.append(
            f"\n\nCase closed.\n\n"
            f"Detective {detective} pushed back from the desk and looked at the completed file. "
            f"{topic} had no more secrets. The truth, as always, had been patient — "
            f"waiting for someone to look carefully enough to find it.\n\n"
            f"'The best cases,' {captain} always said, 'are the ones that teach you something.'\n\n"
            f"This had been one of those cases."
        )
        return '\n\n'.join(parts)

    def _scifi(self, blocks, topic, commander, ai_name, crew, kw):
        first_kw = kw[0] if kw else topic
        parts = []
        parts.append(
            f"MISSION LOG — STARSHIP ATHENA — YEAR 2247\n\n"
            f"Mission: {topic.upper()}\n"
            f"Commander: {commander}\n"
            f"Status: ACTIVE\n\n"
            f"The briefing had been simple: understand {topic.lower()} completely before reaching the destination, "
            f"or the mission fails.\n\n"
            f"Commander {commander} pulled up the first data cluster. The ship's AI — designation {ai_name} — "
            f"processed it instantly. The first flag: {first_kw}. Classified as HIGH IMPORTANCE."
        )

        logs = [
            f"NEURAL ARCHIVE — CLUSTER {i+1}\nCommander {commander} activated the holographic display." for i in range(6)
        ]

        for i, block in enumerate(blocks[:5]):
            parts.append(f"{logs[i % len(logs)]}\n\n{block}\n\n[Crew member {crew} adds annotation: Confirmed and understood. Proceeding.]")

        parts.append(
            f"\n\nMISSION COMPLETE.\n\n"
            f"Commander {commander} removed the neural interface and looked out at the stars. "
            f"The data on {topic.lower()} had been fully processed. Every question answered.\n\n"
            f"'{ai_name},' {commander} said quietly, 'log this: knowledge is the fastest route between any two points.'\n\n"
            f"The ship accelerated toward its next destination. There was always more to learn."
        )
        return '\n\n'.join(parts)

    def _bedtime(self, blocks, topic, child, elder, friend, kw):
        first_kw = kw[0] if kw else topic
        parts = []
        parts.append(
            f"Once upon a time, when the stars were just beginning to come out and the world was getting quiet, "
            f"a child named {child} curled up beside {elder} and asked the question that had been waiting all day:\n\n"
            f"\"Tell me about {topic.lower()}.\"\n\n"
            f"{elder} smiled — that slow, warm smile that meant a story was coming — "
            f"and began:\n\n"
            f"\"Well now. It all starts with {first_kw}. And you have to listen carefully, because this part matters.\""
        )

        gentle = [
            f"\"First,\" said {elder}, settling in,",
            f"\"Now here's the part your friend {friend} always finds hard to believe. Listen:\"",
            f"\"And this — this is the most important bit:\"",
            f"\"Are you still with me? Good. Because now comes the part that makes it all make sense:\"",
            f"\"{child} blinked. \"I think I understand.\" {elder} shook their head gently. \"Almost. One more thing:\"",
        ]

        for i, block in enumerate(blocks[:5]):
            g = gentle[i % len(gentle)]
            parts.append(f"{g}\n\n{block}")

        parts.append(
            f"\n\n{child}'s eyes were very heavy now.\n\n"
            f"\"Is that all of {topic.lower()}?\" came the sleepy question.\n\n"
            f"\"That's all you need for tonight,\" said {elder}, tucking in the blanket. "
            f"\"The rest you'll find yourself, when you're ready. That's the best kind of learning — "
            f"the kind that feels like discovering something that was always yours.\"\n\n"
            f"And {child} drifted off to sleep, carrying {topic.lower()} gently into dreams."
        )
        return '\n\n'.join(parts)

    def _news(self, blocks, topic, reporter, anchor, crew, kw):
        first_kw = kw[0] if kw else topic
        parts = []
        parts.append(
            f"🔴 LIVE — BREAKING NEWS\n\n"
            f"ANCHOR: Good evening. We are coming to you LIVE with a story that has captured the attention of the world. "
            f"The subject: {topic.upper()}. Our senior correspondent {reporter} has been on the ground investigating. "
            f"{reporter}, what can you tell us?\n\n"
            f"REPORTER {reporter.upper()}: Thank you. I am here where it all began — the story of {topic.lower()} "
            f"in full detail. Our first confirmed finding concerns {first_kw}, and what we've discovered is extraordinary."
        )

        updates = [
            f"REPORTER {reporter.upper()} — CONTINUED LIVE COVERAGE:",
            f"BREAKING — NEW DEVELOPMENT JUST CONFIRMED:",
            f"EXCLUSIVE UPDATE — our investigation reveals:",
            f"ANCHOR: {reporter}, we're hearing more details?\n\nREPORTER {reporter.upper()}: Yes — sources confirm:",
            f"LIVE — the full picture is emerging:",
        ]

        for i, block in enumerate(blocks[:5]):
            u = updates[i % len(updates)]
            parts.append(f"{u}\n\n{block}\n\nANCHOR: Remarkable. Continue.")

        parts.append(
            f"\n\nANCHOR: {reporter}, final assessment — what does this mean?\n\n"
            f"REPORTER {reporter.upper()}: Simply this: {topic.lower()} is now fully documented and understood. "
            f"We have the complete picture. For the first time, everything about {topic.lower()} "
            f"is clear, confirmed, and on the record.\n\n"
            f"ANCHOR: Extraordinary reporting. That's our live special: {topic.upper()} — the full story, "
            f"as it happened. We'll continue coverage as more develops."
        )
        return '\n\n'.join(parts)

    def _sports(self, blocks, topic, athlete, coach, rival, kw):
        first_kw = kw[0] if kw else topic
        parts = []
        parts.append(
            f"🎙️ WELCOME SPORTS FANS — you are joining us LIVE for the championship of {topic.upper()}!\n\n"
            f"In the arena tonight: our champion {athlete.upper()}, facing the biggest challenge of the season. "
            f"Coach {coach} has prepared this team for months. The game plan? Master {topic.lower()} completely. "
            f"No shortcuts. No excuses.\n\n"
            f"THE OPENING PLAY — {athlete} dives straight into {first_kw}! "
            f"And it's STRONG! The crowd is already on their feet!"
        )

        commentary = [
            f"THE MOMENTUM IS BUILDING! {athlete} drives into the next section — pure determination:",
            f"INCREDIBLE! What a read by {athlete}! The crowd cannot believe what they're seeing:",
            f"Coach {coach} called this play! And it's WORKING! The textbook move:",
            f"RIVAL {rival.upper()} thought this would stop the charge — but NOTHING can stop {athlete} now:",
            f"UNSTOPPABLE! In a stunning display of focus and preparation:",
        ]

        for i, block in enumerate(blocks[:5]):
            c = commentary[i % len(commentary)]
            parts.append(f"{c}\n\n{block}\n\nTHE SCOREBOARD UPDATES! {athlete} is dominating!")

        parts.append(
            f"\n\nFULL TIME! THE FINAL WHISTLE BLOWS!\n\n"
            f"{athlete.upper()} HAS CONQUERED {topic.upper()}! "
            f"WHAT A PERFORMANCE from start to finish!\n\n"
            f"Coach {coach}: 'I always knew they had it. This is what preparation looks like.'\n\n"
            f"The crowd erupts. Tonight, {topic.lower()} has been faced down, understood completely, "
            f"and defeated. LEGENDARY."
        )
        return '\n\n'.join(parts)

    def _mythology(self, blocks, topic, hero, oracle, companion, kw):
        first_kw = kw[0] if kw else topic
        parts = []
        parts.append(
            f"IN THE AGE BEFORE MEMORY, when gods still walked among mortals and truth was hidden in mountains of mystery, "
            f"there came a seeker named {hero}.\n\n"
            f"{hero} had been chosen — not by chance, but by curiosity — to face the great mystery of {topic.upper()}.\n\n"
            f"The oracle {oracle} spoke first: \"The path begins with {first_kw}. "
            f"Listen, mortal. Listen with everything you have.\"\n\n"
            f"And so the quest began."
        )

        divine = [
            f"The first sacred scroll was opened. The oracle read aloud:",
            f"The gods sent a sign. Companion {companion} translated the ancient words:",
            f"By divine decree, the next truth was revealed:",
            f"{hero} knelt before the altar of knowledge. The cosmos answered:",
            f"The prophecy had spoken of this moment. Now it arrived:",
        ]

        for i, block in enumerate(blocks[:5]):
            d = divine[i % len(divine)]
            parts.append(f"{d}\n\n{block}\n\n{hero} bowed. Another sacred truth had been received.")

        parts.append(
            f"\n\nAnd when the final truth had been spoken and the last scroll had been sealed, "
            f"{hero} stood at the summit and looked out across the world.\n\n"
            f"The oracle {oracle} spoke one last time: \"You have faced {topic.upper()} "
            f"and it has not broken you. It has made you.\"\n\n"
            f"Thus ends the myth of {topic}. It was written into the stars on that day — "
            f"eternal, unchanging, complete.\n\n"
            f"Remember it. Pass it on. The truth endures."
        )
        return '\n\n'.join(parts)