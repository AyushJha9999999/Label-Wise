"""Create a synthetic test label; it is not a real food product."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT = Path(__file__).with_name("labelwise_demo_peanut_diabetes.png")
W, H = 1200, 1580
INK = "#172b24"
MUTED = "#52645b"
ACCENT = "#b64a31"
BG = "#fffdf7"


def font(size: int, bold: bool = False):
    path = Path("C:/Windows/Fonts") / ("arialbd.ttf" if bold else "arial.ttf")
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default()


def ean13_bits(code: str) -> str:
    left = {
        "0": "0001101", "1": "0011001", "2": "0010011", "3": "0111101", "4": "0100011",
        "5": "0110001", "6": "0101111", "7": "0111011", "8": "0110111", "9": "0001011",
    }
    left_g = {
        "0": "0100111", "1": "0110011", "2": "0011011", "3": "0100001", "4": "0011101",
        "5": "0111001", "6": "0000101", "7": "0010001", "8": "0001001", "9": "0010111",
    }
    right = {
        "0": "1110010", "1": "1100110", "2": "1101100", "3": "1000010", "4": "1011100",
        "5": "1001110", "6": "1010000", "7": "1000100", "8": "1001000", "9": "1110100",
    }
    parity = ("LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG", "LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL", "LGGLGL")
    first = int(code[0])
    middle = "".join((left if p == "L" else left_g)[digit] for p, digit in zip(parity[first], code[1:7]))
    bits = "101" + middle + "01010" + "".join(right[digit] for digit in code[7:]) + "101"
    return bits


def draw_barcode(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], code: str):
    x0, y0, x1, y1 = box
    bits = ean13_bits(code)
    module = (x1 - x0) / len(bits)
    for i, bit in enumerate(bits):
        if bit == "1":
            x = round(x0 + i * module)
            right = round(x0 + (i + 1) * module)
            is_guard = i < 3 or 45 <= i < 50 or i >= 92
            draw.rectangle((x, y0, right, y1 + (22 if is_guard else 0)), fill="#111111")
    draw.text((x0, y1 + 25), f"{code[0]}  {code[1:7]}  {code[7:]}", fill="#111111", font=font(29))


def main():
    image = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(image)
    margin = 70
    d.rounded_rectangle((35, 35, W - 35, H - 35), radius=28, outline="#c8d5c8", width=4)
    d.text((margin, 65), "LABELWISE · DEMO TEST LABEL", fill=ACCENT, font=font(25, True))
    d.text((margin, 120), "Chilli Peanut Crunch", fill=INK, font=font(58, True))
    d.text((margin, 195), "FICTIONAL PRODUCT — NOT FOR CONSUMPTION", fill=ACCENT, font=font(24, True))
    d.line((margin, 245, W - margin, 245), fill="#b7c5b8", width=3)

    d.text((margin, 280), "INGREDIENTS", fill=INK, font=font(31, True))
    ingredients = (
        "Puffed rice (38%), roasted peanuts (22%), chickpeas (12%),",
        "sunflower oil, jaggery, red chilli powder, salt, turmeric,",
        "cumin, garlic powder, citric acid (E330), and rosemary extract.",
    )
    y = 328
    for line in ingredients:
        d.text((margin, y), line, fill=MUTED, font=font(27))
        y += 43
    d.rounded_rectangle((margin, 480, W - margin, 548), radius=14, fill="#fff0e9", outline="#e3aa98", width=2)
    d.text((margin + 20, 499), "CONTAINS: PEANUTS", fill="#9f321f", font=font(28, True))
    d.text((margin, 578), "May contain traces of milk and sesame.", fill=MUTED, font=font(24))

    left, top, right, bottom = margin, 645, W - margin, 1110
    d.rectangle((left, top, right, bottom), outline=INK, width=3)
    d.text((left + 18, top + 14), "NUTRITION INFORMATION", fill=INK, font=font(30, True))
    d.text((left + 18, top + 58), "Per 100 g  |  Serving size: 30 g", fill=MUTED, font=font(22))
    d.line((left + 15, top + 100, right - 15, top + 100), fill=INK, width=3)
    rows = [
        ("Energy", "1750 kJ / 418 kcal"),
        ("Total fat", "15 g"),
        ("of which saturates", "3 g"),
        ("Total carbohydrate", "61 g"),
        ("of which sugars", "18 g"),
        ("Protein", "10 g"),
        ("Salt", "1.25 g"),
    ]
    row_y = top + 120
    for label, value in rows:
        d.text((left + 20, row_y), label, fill=INK, font=font(24))
        box = d.textbbox((0, 0), value, font=font(24, True))
        d.text((right - 20 - (box[2] - box[0]), row_y), value, fill=INK, font=font(24, True))
        d.line((left + 15, row_y + 38, right - 15, row_y + 38), fill="#d4d9d1", width=1)
        row_y += 47

    d.text((margin, 1145), "Barcode demo · restricted-use test number", fill=MUTED, font=font(20))
    draw_barcode(d, (300, 1190, 900, 1385), "2001234567893")
    d.text((margin, 1470), "Use only to test label reading, allergy matching, nutrition caution, and barcode detection.", fill=MUTED, font=font(18))
    image.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
