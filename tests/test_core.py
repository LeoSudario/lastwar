import unittest

from backend.core import extract_rows, match_player, classify, normalize_score


class CoreTests(unittest.TestCase):
    def test_score_separators(self):
        self.assertEqual(normalize_score('15.000'), 15000)
        self.assertEqual(normalize_score('0'), 0)
        self.assertIsNone(normalize_score('12K'))
        self.assertIsNone(normalize_score(None))
        self.assertIsNone(normalize_score(''))
        self.assertEqual(normalize_score('1.250'), 1250)
        self.assertEqual(normalize_score('12,500'), 12500)

    def test_styled_names_accents_and_spaces(self):
        cases = [('DragonBR', 'DRAGONBR'), ('ShadowX', 'ＳｈａｄｏｗＸ'),
                 ('Phoenix', '𝓟𝓱𝓸𝓮𝓷𝓲𝔁'), ('Luna War', 'Luna   War'),
                 ('DragonBR', 'DragonBR★'), ('João', 'JOAO')]
        for registered, ocr in cases:
            with self.subTest(ocr=ocr):
                self.assertEqual(match_player(ocr, [{'id': '1', 'name': registered}], .99)['player_id'], '1')

    def test_fuzzy_match_needs_review_and_ambiguous_match_is_rejected(self):
        match = match_player('Dr4gonBR', [{'id': '1', 'name': 'DragonBR'}], .99)
        self.assertEqual(match['player_id'], '1')
        self.assertTrue(match['requires_review'])
        match = match_player('ShadowX', [{'id': '1', 'name': 'ShadowXX'}, {'id': '2', 'name': 'ShadowXY'}], .99)
        self.assertIsNone(match['player_id'])

    def test_player_alias_is_matched(self):
        match = match_player('Dr4g0n', [{'id': '1', 'name': 'DragonBR', 'aliases': ['Dr4g0n']}], .99)
        self.assertEqual(match['player_id'], '1')

    def test_alias_collision_and_relaxed_accent_collision_are_ambiguous(self):
        roster = [{'id': '1', 'name': 'José', 'aliases': ['Fantasma']}, {'id': '2', 'name': 'Jose', 'aliases': ['Fantasma']}]
        self.assertIsNone(match_player('Fantasma', roster, .99)['player_id'])
        self.assertIsNone(match_player('Jose★', roster, .99)['player_id'])

    def test_invisible_characters_and_configurable_fuzzy_threshold(self):
        roster = [{'id': '1', 'name': 'DragonBR'}]
        self.assertEqual(match_player('Dragon\u200bBR', roster, .99)['player_id'], '1')
        self.assertIsNone(match_player('Dr4gonBR', roster, .99, {'match_threshold': .95})['player_id'])
        self.assertIsNone(match_player('Luna', [{'id': '1', 'name': 'LunaBR'}], .99)['player_id'])

    def test_invalid_scores_are_not_confirmed(self):
        for value in (None, '', '0', 'ilegível', -1, False, 0.0):
            with self.subTest(value=value):
                self.assertEqual(classify('1', value, .99, False, {}), 'Revisão necessária')
        for value, expected in [(0, 'Ausente'), (1, 'Presente'), (15000, 'Presente')]:
            self.assertEqual(classify('1', value, .99, False, {}), expected)

    def test_zero_is_not_confused_with_level(self):
        words = [dict(text='Player', x=100, y=100, w=80, h=20, confidence=.99),
                 dict(text='30', x=300, y=100, w=20, h=20, confidence=.99),
                 dict(text='0', x=450, y=100, w=12, h=20, confidence=.99)]
        rows = extract_rows(words, 600, 300, {'rank_left': .1, 'name_right': .4, 'score_left': .7, 'rank_right': .9})
        self.assertEqual(rows[0]['score'], 0)
        self.assertEqual(classify('1', rows[0]['score'], rows[0]['ocr_confidence'], False, {}), 'Ausente')

    def test_geometric_association(self):
        words = [
            dict(text='DragonBR', x=100, y=100, w=90, h=20, confidence=.96),
            dict(text='15,000', x=400, y=101, w=70, h=20, confidence=.95),
            dict(text='ShadowX', x=100, y=160, w=90, h=20, confidence=.93),
            dict(text='0', x=400, y=160, w=15, h=20, confidence=.94),
        ]
        rows = extract_rows(words, 600, 300, {'rank_left': .1, 'rank_right': .9, 'score_left': .6})
        self.assertEqual([(r['name'], r['score']) for r in rows], [('DragonBR', 15000), ('ShadowX', 0)])

    def test_ambiguous_match_is_not_automatic(self):
        roster = [{'id': '1', 'name': 'DragonBR'}, {'id': '2', 'name': 'DragonBX'}]
        self.assertIsNone(match_player('DragonB', roster, .99)['player_id'])

    def test_avatar_fragment_is_not_joined_to_player_name(self):
        words = [dict(text='Pa', x=81, y=453, w=49, h=51, confidence=.46),
                 dict(text='GaalGeriLevi', x=135, y=470, w=96, h=20, confidence=.91),
                 dict(text='235970', x=349, y=472, w=60, h=12, confidence=.96)]
        rows = extract_rows(words, 430, 680, {'rank_left': .1, 'name_right': .65, 'score_left': .65, 'rank_right': .95})
        self.assertEqual([(r['name'], r['score']) for r in rows], [('GaalGeriLevi', 235970)])
        self.assertTrue(rows[0]['name_uncertain'])
        self.assertEqual(match_player(rows[0]['name'], [{'id': '1', 'name': 'gaalgerilevi'}], rows[0]['ocr_confidence'])['player_id'], '1')

    def test_case_insensitive_name_does_not_select_ambiguous_roster(self):
        roster = [{'id': '1', 'name': 'gaalgerilevi'}, {'id': '2', 'name': 'GaalGeriLevi'}]
        self.assertIsNone(match_player('GAALGERILEVI', roster, .99)['player_id'])

    def test_absence_not_inferred(self):
        self.assertEqual(classify(None, None, 1, False, {}), 'Não identificado')
        self.assertEqual(classify('1', 0, .99, True, {}), 'Ausente')
        self.assertEqual(classify('1', 0, .45, False, {}), 'Ausente')
        self.assertEqual(classify('1', 10, .3, False, {}), 'Revisão necessária')

    def test_multiple_numbers_on_same_row_need_review(self):
        words = [dict(text='Dragon', x=100, y=100, w=80, h=20, confidence=.99),
                 dict(text='30', x=400, y=100, w=20, h=20, confidence=.99),
                 dict(text='15000', x=450, y=100, w=60, h=20, confidence=.99)]
        rows = extract_rows(words, 600, 300, {'rank_left': .1, 'rank_right': .9, 'score_left': .6})
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]['score'])
        self.assertTrue(rows[0]['score_ambiguous'])

    def test_level_outside_score_region_is_ignored(self):
        words = [dict(text='Dragon', x=100, y=100, w=80, h=20, confidence=.99),
                 dict(text='30', x=300, y=100, w=20, h=20, confidence=.99),
                 dict(text='15000', x=450, y=100, w=60, h=20, confidence=.99)]
        rows = extract_rows(words, 600, 300, {'rank_left': .1, 'name_right': .4, 'score_left': .7, 'rank_right': .9})
        self.assertEqual([(r['name'], r['score']) for r in rows], [('Dragon', 15000)])


if __name__ == '__main__':
    unittest.main()
