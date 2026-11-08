import os
import shutil
import re
from pathlib import Path
import cv2
import numpy as np
import pytesseract
from .core import extract_rows, normalize_score


def recognize(content, settings):
    path = os.environ.get('TESSERACT_CMD') or shutil.which('tesseract')
    if not path:
        default = Path(r'C:\Program Files\Tesseract-OCR\tesseract.exe')
        path = str(default) if default.exists() else None
    if not path:
        raise RuntimeError('Tesseract não encontrado. Instale-o ou defina TESSERACT_CMD.')
    pytesseract.pytesseract.tesseract_cmd = path
    image = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError('Arquivo não é uma imagem PNG ou JPEG válida.')
    h, w = image.shape[:2]
    if h * w > 40000000:
        raise ValueError('Imagem muito grande (limite: 40 megapixels).')
    # Power leaderboards are not event participation scores. Inspect the title
    # independently of user-configured columns, which may exclude that title.
    header = image[:max(1, int(h * .12))]
    title = pytesseract.image_to_string(header, config='--psm 6', timeout=30)
    title_key = re.sub(r'[^a-z]', '', title.casefold())
    if 'totalheropower' in title_key:
        raise ValueError('Este print mostra poder dos heróis (Total Hero Power), não pontos de participação. '
                         'Importe o relatório de batalha do evento com a coluna Points/Pontos.')
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.bilateralFilter(gray, 5, 35, 35)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    gray = cv2.addWeighted(gray, 1.5, cv2.GaussianBlur(gray, (0, 0), 1), -.5, 0)
    data = pytesseract.image_to_data(gray, config='--psm 6', output_type=pytesseract.Output.DICT, timeout=120)
    words = []
    for i, text in enumerate(data['text']):
        conf = float(data['conf'][i])
        if text.strip() and conf >= 0:
            words.append(dict(text=text.strip(), x=data['left'][i]/2, y=data['top'][i]/2,
                              w=data['width'][i]/2, h=data['height'][i]/2, confidence=conf/100))
    # A dedicated digit pass avoids confusing isolated zeros with letters or punctuation.
    # Coordinates remain in the full-image coordinate system for geometric pairing.
    split = int(settings['score_left'] * w * 2)
    right = int(settings['rank_right'] * w * 2)
    if right <= split or split < 0 or right > w * 2:
        raise ValueError('Colunas do ranking inválidas.')
    numbers = pytesseract.image_to_data(gray[:, split:right], config='--psm 6 -c tessedit_char_whitelist=0123456789,.', output_type=pytesseract.Output.DICT, timeout=120)
    words = [word for word in words if word['x'] < split / 2]
    for i, text in enumerate(numbers['text']):
        conf = float(numbers['conf'][i])
        if text.strip() and conf >= 0:
            words.append(dict(text=text.strip(), x=(numbers['left'][i]+split)/2, y=numbers['top'][i]/2,
                              w=numbers['width'][i]/2, h=numbers['height'][i]/2, confidence=conf/100))
    rows = extract_rows(words, w, h, settings)
    # Retry only missing, unambiguous rows, within their configured score column.
    # The unrestricted OCR pass avoids forcing letters into digits.
    raw_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    for row in rows:
        if row['score'] is None and not row['score_ambiguous']:
            x1, y1, x2, y2 = row['box']
            pad = (y2 - y1) * .4
            top = max(0, int(y1 - pad))
            bottom = min(h, int(y2 + pad) + 1)
            left, end = int(settings['score_left'] * w), int(settings['rank_right'] * w)
            crop = raw_gray[top:bottom, left:end]
            if crop.size:
                crop = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
                detail = pytesseract.image_to_data(crop, config='--psm 7', output_type=pytesseract.Output.DICT, timeout=120)
                candidates = []
                for i, text in enumerate(detail['text']):
                    score = normalize_score(text)
                    confidence = float(detail['conf'][i]) / 100
                    cy = top + (detail['top'][i] + detail['height'][i] / 2) / 3
                    if score is not None and confidence > 0 and y1 - pad <= cy <= y2 + pad:
                        candidates.append((score, confidence, i))
                if len(candidates) == 1:
                    score, confidence, i = candidates[0]
                    row['score'] = score
                    row['score_raw'] = detail['text'][i]
                    row['ocr_confidence'] = round(min(row['ocr_confidence'], confidence), 3)
                    row['box'] = [x1, min(y1, top + detail['top'][i] / 3),
                                  max(x2, left + (detail['left'][i] + detail['width'][i]) / 3),
                                  max(y2, top + (detail['top'][i] + detail['height'][i]) / 3)]
        row['box'] = [round(v) for v in row['box']]
    return rows
