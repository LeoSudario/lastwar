"""Avalia linhas anotadas por imagem; execute: python avaliar.py exemplos/anotacoes.json."""
import json
import sys
from collections import Counter
from pathlib import Path
from backend.ocr import recognize
from backend.core import match_player, classify


def measure(expected, actual):
    expected, actual = Counter(expected), Counter(actual)
    tp = sum((expected & actual).values())
    fp, fn = sum(actual.values()) - tp, sum(expected.values()) - tp
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else (0 if precision is not None and recall is not None else None)
    return {'acertos': tp, 'falsos_positivos': fp, 'faltantes': fn, 'precisao': precision, 'recall': recall, 'f1': f1}


def main(manifest):
    path = Path(manifest)
    data = json.loads(path.read_text(encoding='utf-8'))
    expected, actual, errors = [], [], []
    for image in data['imagens']:
        filename = image['arquivo']
        found = recognize((path.parent / filename).read_bytes(), data['configuracao'])
        for row in found:
            row.update(match_player(row['name'], data['jogadores'], row['ocr_confidence']))
            player = next((p for p in data['jogadores'] if p['id'] == row['player_id']), None)
            row['status'] = classify(row['player_id'], row['score'], row['ocr_confidence'], bool(player and player.get('reserve')), {})
        expected.extend((filename, row) for row in image['linhas'])
        actual.extend((filename, row) for row in found)
        exp_pairs = Counter((r['name'], r['score']) for r in image['linhas'])
        actual_pairs = Counter((r['name'], r['score']) for r in found)
        annotated = Counter((r['name'], r['score'], r.get('player_id'), r.get('status')) for r in image['linhas'])
        observed = Counter((r['name'], r['score'], r.get('player_id'), r.get('status')) for r in found)
        if exp_pairs != actual_pairs or annotated != observed:
            errors.append({'imagem': filename, 'esperado': image['linhas'], 'encontrado': found})
    metrics = {}
    for label, fields in {'nomes': ['name'], 'pontuacoes': ['score'], 'associacao_nome_pontuacao': ['name', 'score'], 'identificacao_jogador': ['name', 'player_id'], 'classificacao_presenca': ['name', 'status']}.items():
        def values(rows):
            return [(filename, *(row.get(f) for f in fields)) for filename, row in rows]
        metrics[label] = measure(values(expected), values(actual))
    assignments = [(filename, r) for filename, r in actual if r.get('player_id')]
    expected_assignments = {(filename, r['name'], r['player_id']) for filename, r in expected}
    incorrect = sum((filename, r['name'], r['player_id']) not in expected_assignments for filename, r in assignments)
    metrics['taxa_correspondencias_incorretas'] = {'incorretas': incorrect, 'associacoes_automaticas': len(assignments), 'taxa': incorrect / len(assignments) if assignments else None}
    print(json.dumps({'metricas': metrics, 'erros_por_imagem': errors}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Uso: python avaliar.py caminho/anotacoes.json')
    main(sys.argv[1])
