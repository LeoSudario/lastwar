"""Pure, conservative ranking extraction and attendance rules."""
import re
import unicodedata
from rapidfuzz.fuzz import ratio


def normalize_score(text):
    if not isinstance(text, str):
        return None
    if not re.fullmatch(r'\d+(?:[., ]\d{3})*', text.strip()):
        return None
    return int(re.sub(r'[., ]', '', text))


def normalized(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    return ' '.join(''.join(c for c in text if unicodedata.category(c) != 'Cf').split())


def comparison_key(text):
    """Relax only Latin accents and decorative symbols at the edges."""
    text = normalized(text)
    while text and unicodedata.category(text[0]) in ('So', 'Sk'):
        text = text[1:].lstrip()
    while text and unicodedata.category(text[-1]) in ('So', 'Sk'):
        text = text[:-1].rstrip()
    result, latin = [], False
    for char in unicodedata.normalize('NFD', text):
        if unicodedata.category(char) == 'Mn':
            if not latin:
                result.append(char)
        else:
            latin = 'LATIN' in unicodedata.name(char, '')
            result.append(char)
    return unicodedata.normalize('NFC', ''.join(result))


def extract_rows(words, width, height, settings):
    """Pair only tokens in the same horizontal band and configured columns."""
    left, right = settings['rank_left'] * width, settings['rank_right'] * width
    split = settings['score_left'] * width
    eligible = [w for w in words if left <= w['x'] < right and 0 <= w['y'] < height]
    scores = [w for w in eligible if w['x'] >= split and normalize_score(w['text']) is not None]
    names = [w for w in eligible if w['x'] < settings.get('name_right', settings['score_left']) * width and any(c.isalpha() for c in w['text'])]
    rows = []
    while names:
        first = min(names, key=lambda w: w['y'])
        sy = first['y'] + first['h'] / 2
        aligned = [n for n in names if abs(n['y'] + n['h'] / 2 - sy) <= max(n['h'], first['h']) * .65]
        names = [n for n in names if n not in aligned]
        numbers = [s for s in scores if abs(s['y'] + s['h'] / 2 - sy) <= max(s['h'], first['h']) * .65]
        score = numbers[0] if len(numbers) == 1 else None
        # An avatar may be detected as a large, low-confidence word in the
        # same band as the real name. Retain uncertainty for manual review.
        artifact_removed = False
        if score is not None and len(aligned) > 1:
            min_height = min(n['h'] for n in aligned)
            filtered = [n for n in aligned if not (n['h'] > min_height * 2 and n['confidence'] < .6)]
            if filtered:
                artifact_removed = len(filtered) != len(aligned)
                aligned = filtered
        aligned.sort(key=lambda w: w['x'])
        parts = aligned + numbers
        x1 = min(w['x'] for w in parts)
        y1 = min(w['y'] for w in parts)
        x2 = max(w['x'] + w['w'] for w in parts)
        y2 = max(w['y'] + w['h'] for w in parts)
        rows.append({'name': ' '.join(w['text'] for w in aligned), 'score': normalize_score(score['text']) if score is not None else None,
                     'score_raw': score['text'] if score is not None else None,
                     'ocr_confidence': round(min(w['confidence'] for w in parts), 3),
                     'box': [x1, y1, x2, y2], 'name_uncertain': artifact_removed,
                     'score_ambiguous': len(numbers) > 1})
    return rows


def match_player(name, roster, confidence, rules=None):
    rules = rules or {}
    names = [(p, [p['name']] + [a for a in p.get('aliases', []) if isinstance(a, str)]) for p in roster]
    key = normalized(name)
    relaxed = comparison_key(name)
    candidates = sorted([{'id': p['id'], 'name': p['name'], 'similarity': round(max((ratio(relaxed, comparison_key(n)) / 100 for n in variants), default=0), 3)} for p, variants in names], key=lambda x: x['similarity'], reverse=True)
    suggestions = [c for c in candidates if c['similarity'] >= .60][:3]
    exact = [p for p, variants in names if key and any(normalized(n) == key for n in variants)]
    if len(exact) == 1:
        return {'player_id': exact[0]['id'], 'candidates': suggestions, 'requires_review': False, 'match_reason': 'exato'}
    if len(exact) > 1:
        return {'player_id': None, 'candidates': suggestions, 'requires_review': True, 'match_reason': 'nome ambíguo'}
    equivalent = [p for p, variants in names if relaxed and any(comparison_key(n) == relaxed for n in variants)]
    if len(equivalent) == 1:
        return {'player_id': equivalent[0]['id'], 'candidates': suggestions, 'requires_review': False, 'match_reason': 'normalizado'}
    if len(equivalent) > 1:
        return {'player_id': None, 'candidates': suggestions, 'requires_review': True, 'match_reason': 'normalização ambígua'}
    threshold = max(.85, min(1., float(rules.get('match_threshold', .85))))
    margin = max(.08, min(1., float(rules.get('match_margin', .10))))
    top = candidates[0] if candidates else None
    second = candidates[1]['similarity'] if len(candidates) > 1 else 0
    if top is not None and len(relaxed) >= 6 and top['similarity'] >= threshold and top['similarity'] - second >= margin:
        return {'player_id': top['id'], 'candidates': suggestions, 'requires_review': True, 'match_reason': 'aproximado'}
    return {'player_id': None, 'candidates': suggestions, 'requires_review': True, 'match_reason': 'sem correspondência segura'}


def classify(player_id, score, confidence, reserve, rules):
    if not player_id:
        return 'Não identificado'
    if type(score) is not int or score < 0:
        return 'Revisão necessária'
    if score == 0:
        return 'Ausente'
    if confidence < float(rules.get('min_confidence', .80)):
        return 'Revisão necessária'
    return 'Presente'
