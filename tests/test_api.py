import json
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app


class AttendanceApiTests(unittest.TestCase):
    def test_zero_with_alias_is_absent(self):
        row = {'name': '𝓟𝓱𝓸𝓮𝓷𝓲𝔁', 'score': 0, 'score_raw': '0', 'ocr_confidence': .99, 'box': [10, 10, 100, 20]}
        with patch('backend.main.recognize', return_value=[row]):
            response = TestClient(app).post('/api/analyze', files={'file': ('rank.png', b'image', 'image/png')}, data={'roster': json.dumps([{'id': '1', 'name': 'Jogador', 'aliases': ['Phoenix']}])})
        self.assertEqual(response.status_code, 200)
        result = response.json()['rows'][0]
        self.assertEqual((result['player_id'], result['score'], result['status']), ('1', 0, 'Ausente'))

    def test_zero_with_low_ocr_confidence_is_absent_for_exact_name(self):
        row = {'name': 'ShadowX', 'score': 0, 'score_raw': '0', 'ocr_confidence': .45, 'box': [10, 10, 100, 20]}
        with patch('backend.main.recognize', return_value=[row]):
            result = TestClient(app).post('/api/analyze', files={'file': ('rank.png', b'image', 'image/png')}, data={'roster': json.dumps([{'id': '1', 'name': 'ShadowX'}])}).json()['rows'][0]
        self.assertEqual((result['score'], result['status']), (0, 'Ausente'))

    def test_fuzzy_match_is_not_confirmed_automatically(self):
        row = {'name': 'Dr4gonBR', 'score': 0, 'score_raw': '0', 'ocr_confidence': .99, 'box': [10, 10, 100, 20]}
        with patch('backend.main.recognize', return_value=[row]):
            response = TestClient(app).post('/api/analyze', files={'file': ('rank.png', b'image', 'image/png')}, data={'roster': json.dumps([{'id': '1', 'name': 'DragonBR'}])})
        result = response.json()['rows'][0]
        self.assertEqual(result['player_id'], '1')
        self.assertEqual(result['status'], 'Revisão necessária')

    def test_ambiguous_name_is_unassociated_and_marked_for_review(self):
        row = {'name': 'ShadowX', 'score': 0, 'score_raw': '0', 'ocr_confidence': .99, 'box': [10, 10, 100, 20]}
        roster = [{'id': '1', 'name': 'ShadowXX'}, {'id': '2', 'name': 'ShadowXY'}]
        with patch('backend.main.recognize', return_value=[row]):
            result = TestClient(app).post('/api/analyze', files={'file': ('rank.png', b'image', 'image/png')}, data={'roster': json.dumps(roster)}).json()['rows'][0]
        self.assertIsNone(result['player_id'])
        self.assertEqual(result['status'], 'Revisão necessária')
