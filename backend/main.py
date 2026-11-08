import json
import logging
import os
from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .ocr import recognize
from .core import match_player, classify, normalized

logger = logging.getLogger(__name__)
if os.environ.get('LASTWAR_OCR_DEBUG') == '1':
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    logger.propagate = False

app = FastAPI(title='Last War — conferência local')
WEB = Path(__file__).resolve().parent.parent / 'web'
app.mount('/static', StaticFiles(directory=WEB), name='static')


@app.get('/')
def index():
    return FileResponse(WEB / 'index.html')


@app.post('/api/analyze')
async def analyze(file: UploadFile = File(), roster: str = Form('[]'), settings: str = Form('{}'), rules: str = Form('{}')):
    if not (file.filename or '').lower().endswith(('.png', '.jpg', '.jpeg')):
        raise HTTPException(400, 'Use PNG, JPG ou JPEG.')
    content = await file.read(20 * 1024 * 1024 + 1)
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(400, 'Imagem excede 20 MB.')
    try:
        players, config, options = json.loads(roster), json.loads(settings), json.loads(rules)
        rows = recognize(content, config)
        for row in rows:
            match = match_player(row['name'], players, row['ocr_confidence'], options)
            row.update(match)
            player = next((p for p in players if p['id'] == row['player_id']), None)
            row['status'] = classify(row['player_id'], row['score'], row['ocr_confidence'], bool(player and player.get('reserve')), options)
            reason = row['match_reason']
            if row['score'] is None:
                reason = 'pontuação ausente ou ilegível'
            elif row['score'] != 0 and row['ocr_confidence'] < float(options.get('min_confidence', .80)):
                reason = 'confiança OCR insuficiente'
            if row['player_id'] and (row.get('name_uncertain') or row.get('requires_review')):
                row['status'] = 'Revisão necessária'
                reason = 'fragmento no nome' if row.get('name_uncertain') else row['match_reason']
            elif row['player_id'] is None and row['candidates']:
                row['status'] = 'Revisão necessária'
            logger.debug('OCR nome=%r normalizado=%r jogador=%r candidatos=%r pontos_ocr=%r pontos=%r status=%r motivo=%r',
                         row['name'], normalized(row['name']), player['name'] if player else None,
                         row['candidates'], row.get('score_raw'), row['score'], row['status'],
                         reason)
        return {'rows': rows}
    except (ValueError, RuntimeError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(400, str(exc)) from exc
