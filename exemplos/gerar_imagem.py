"""Gera um ranking fictício, não uma captura real do jogo."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

folder = Path(__file__).resolve().parent
font = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 38)
image = Image.new('RGB', (900, 260), 'white')
draw = ImageDraw.Draw(image)
for x, y, text in [(140, 45, 'DragonBR'), (650, 45, '15,000'), (140, 145, 'ShadowX'), (650, 145, '0')]:
    draw.text((x, y), text, fill='black', font=font)
image.save(folder / 'ranking-ficticio.png')
print('Criado:', folder / 'ranking-ficticio.png')
