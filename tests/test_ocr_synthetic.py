"""Synthetic OCR smoke test: not representative of screenshots from the game."""
import io
import os
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageDraw, ImageFont
from backend.ocr import recognize


def tesseract_available():
    return bool(os.environ.get('TESSERACT_CMD') or shutil.which('tesseract') or Path(r'C:\Program Files\Tesseract-OCR\tesseract.exe').exists())


@unittest.skipUnless(tesseract_available(), 'Tesseract não instalado')
class SyntheticOCRTests(unittest.TestCase):
    def test_power_ranking_is_rejected_in_attendance_flow(self):
        image = Image.new('RGB', (400, 180), 'white')
        output = io.BytesIO()
        image.save(output, format='PNG')
        with patch('backend.ocr.pytesseract.image_to_string', return_value='TOTAL HERO POWER: o'):
            with self.assertRaisesRegex(ValueError, 'poder dos heróis'):
                recognize(output.getvalue(), {'rank_left': .1, 'score_left': .65, 'rank_right': .95})

    def test_recovers_zero_when_column_pass_misses_it(self):
        image = Image.new('RGB', (400, 180), 'white')
        output = io.BytesIO()
        image.save(output, format='PNG')
        def data(text, left, top, width, height, conf):
            return dict(text=text, left=left, top=top, width=width, height=height, conf=conf)
        name = data(['Player'], [220], [160], [100], [24], [95])
        no_scores = data([], [], [], [], [], [])
        zero = data(['0'], [210], [20], [20], [24], [92])
        with patch('backend.ocr.pytesseract.image_to_data', side_effect=[name, no_scores, zero]):
            rows = recognize(output.getvalue(), {'rank_left': .1, 'score_left': .65, 'rank_right': .95})
        self.assertEqual(rows[0]['score'], 0)
        self.assertGreaterEqual(rows[0]['ocr_confidence'], .8)

    def test_real_ocr_on_synthetic_ranking(self):
        image = Image.new('RGB', (900, 260), 'white')
        draw = ImageDraw.Draw(image)
        font_path = Path(r'C:\Windows\Fonts\arial.ttf')
        if not font_path.exists():
            self.skipTest('Fonte Arial não disponível para fixture sintética')
        font = ImageFont.truetype(str(font_path), 38)
        draw.text((140, 45), 'DragonBR', fill='black', font=font)
        draw.text((650, 45), '15,000', fill='black', font=font)
        draw.text((140, 145), 'ShadowX', fill='black', font=font)
        draw.text((650, 145), '0', fill='black', font=font)
        output = io.BytesIO()
        image.save(output, format='PNG')
        rows = recognize(output.getvalue(), {'rank_left': .1, 'score_left': .65, 'rank_right': .95})
        self.assertEqual([(r['name'], r['score']) for r in rows], [('DragonBR', 15000), ('ShadowX', 0)])


if __name__ == '__main__':
    unittest.main()
