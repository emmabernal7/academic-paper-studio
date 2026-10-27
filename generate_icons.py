import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTPUT_DIR = "web_downloader/static/icon_proposals"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Try loading fonts
try:
    FONT_PATH_BOLD = "C:/Windows/Fonts/segoeuib.ttf"
    FONT_PATH_HEAVY = "C:/Windows/Fonts/arialbd.ttf"
except Exception:
    FONT_PATH_BOLD = None
    FONT_PATH_HEAVY = None

def get_font(size, bold=True):
    try:
        path = FONT_PATH_BOLD if bold else FONT_PATH_HEAVY
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def draw_star(draw, x, y, r_outer, r_inner, fill):
    points = []
    for i in range(8):
        angle = i * math.pi / 4 - math.pi / 2
        r = r_outer if i % 2 == 0 else r_inner
        points.append((x + r * math.cos(angle), y + r * math.sin(angle)))
    draw.polygon(points, fill=fill)

def draw_telescope_1(draw, cx, cy, scale=1.0, color=(14, 165, 233), highlight=(56, 189, 248), mount=(100, 116, 139)):
    # cx, cy is the pivot point of the mount
    # Angled 35 degrees pointing up-right
    # Barrel: main tube
    angle = -math.radians(38)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)

    def rot(dx, dy):
        return (cx + dx * cos_a - dy * sin_a, cy + dx * sin_a + dy * cos_a)

    s = scale
    # Main tube polygon
    p1 = rot(-140 * s, -22 * s)
    p2 = rot(140 * s, -14 * s)
    p3 = rot(140 * s, 14 * s)
    p4 = rot(-140 * s, 22 * s)
    draw.polygon([p1, p2, p3, p4], fill=color)

    # Top highlight strip on tube
    h1 = rot(-138 * s, -21 * s)
    h2 = rot(138 * s, -13 * s)
    h3 = rot(138 * s, -6 * s)
    h4 = rot(-138 * s, -10 * s)
    draw.polygon([h1, h2, h3, h4], fill=highlight)

    # Objective lens cap / rim (front, top-right)
    c1 = rot(136 * s, -20 * s)
    c2 = rot(154 * s, -20 * s)
    c3 = rot(154 * s, 20 * s)
    c4 = rot(136 * s, 20 * s)
    draw.polygon([c1, c2, c3, c4], fill=(224, 242, 254))

    # Glow from lens
    g1 = rot(154 * s, -18 * s)
    g2 = rot(240 * s, -45 * s)
    g3 = rot(240 * s, 45 * s)
    g4 = rot(154 * s, 18 * s)
    draw.polygon([g1, g2, g3, g4], fill=(56, 189, 248, 60))

    # Eyepiece / diagonal (back, bottom-left)
    e1 = rot(-140 * s, -12 * s)
    e2 = rot(-170 * s, -10 * s)
    e3 = rot(-170 * s, 10 * s)
    e4 = rot(-140 * s, 12 * s)
    draw.polygon([e1, e2, e3, e4], fill=(71, 85, 105))

    # Small diagonal eyepiece tube pointing up-left
    d1 = rot(-165 * s, -10 * s)
    d2 = rot(-185 * s, -35 * s)
    d3 = rot(-172 * s, -42 * s)
    d4 = rot(-155 * s, -10 * s)
    draw.polygon([d1, d2, d3, d4], fill=color)

    # Mount / Joint
    draw.ellipse([cx - 26*s, cy - 26*s, cx + 26*s, cy + 26*s], fill=mount, outline=(203, 213, 225), width=int(3*s))
    draw.ellipse([cx - 10*s, cy - 10*s, cx + 10*s, cy + 10*s], fill=(224, 242, 254))

    # Tripod legs
    # Center vertical shaft
    draw.rectangle([cx - 8*s, cy + 20*s, cx + 8*s, cy + 60*s], fill=mount)
    # Left leg
    draw.line([(cx - 6*s, cy + 55*s), (cx - 110*s, cy + 240*s)], fill=mount, width=int(14*s))
    # Right leg
    draw.line([(cx + 6*s, cy + 55*s), (cx + 110*s, cy + 240*s)], fill=mount, width=int(14*s))
    # Center leg
    draw.line([(cx, cy + 55*s), (cx + 10*s, cy + 250*s)], fill=(51, 65, 85), width=int(12*s))

def create_option_1():
    # 1. Cosmic Neon & Deep Space
    SIZE = 1024
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Squircle background
    r = 220
    draw.rounded_rectangle([20, 20, SIZE-20, SIZE-20], radius=r, fill=(11, 19, 43))

    # Radial glow inside
    glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse([SIZE//2 - 380, SIZE//2 - 380, SIZE//2 + 380, SIZE//2 + 380], fill=(14, 116, 144, 110))
    gdraw.ellipse([SIZE//2 - 200, SIZE//2 - 200, SIZE//2 + 200, SIZE//2 + 200], fill=(6, 182, 212, 140))
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    img = Image.alpha_composite(img, glow)
    draw = ImageDraw.Draw(img)

    # Stars
    stars = [
        (200, 180, 22, 6), (750, 160, 32, 8), (880, 280, 18, 5),
        (160, 420, 14, 4), (820, 480, 20, 5), (320, 140, 12, 3),
        (650, 100, 16, 4), (480, 200, 14, 4)
    ]
    for sx, sy, ro, ri in stars:
        draw_star(draw, sx, sy, ro, ri, (255, 255, 255, 230))
        draw_star(draw, sx, sy, ro*0.6, ri*0.6, (165, 243, 252, 255))

    # Telescope in background
    tele_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(tele_layer)
    draw_telescope_1(tdraw, 520, 460, scale=1.75, color=(14, 165, 233, 230), highlight=(186, 230, 253, 255), mount=(71, 85, 105, 240))
    img = Image.alpha_composite(img, tele_layer)
    draw = ImageDraw.Draw(img)

    # Large Foreground APS Text
    font = get_font(250, bold=True)
    text = "APS"
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (SIZE - tw) // 2
    ty = SIZE - th - 180

    # Glow under text
    text_glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    tgdraw = ImageDraw.Draw(text_glow)
    for off in range(12, 28, 4):
        tgdraw.text((tx, ty), text, font=font, fill=(6, 182, 212, 80))
    text_glow = text_glow.filter(ImageFilter.GaussianBlur(16))
    img = Image.alpha_composite(img, text_glow)
    draw = ImageDraw.Draw(img)

    # Text shadow
    draw.text((tx+4, ty+8), text, font=font, fill=(5, 15, 30, 220))
    # Text main
    draw.text((tx, ty), text, font=font, fill=(255, 255, 255))
    # Subtle cyan gradient or accent
    draw.text((tx, ty), text, font=font, fill=(240, 253, 250))

    # Subtle badge border
    draw.rounded_rectangle([20, 20, SIZE-20, SIZE-20], radius=r, outline=(56, 189, 248, 160), width=16)

    return img.resize((512, 512), Image.Resampling.LANCZOS)

def create_option_2():
    # 2. Golden Observatory & Royal Navy
    SIZE = 1024
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Circular badge
    draw.ellipse([24, 24, SIZE-24, SIZE-24], fill=(15, 23, 42))

    # Celestial circle rings / astrolabe lines
    draw.ellipse([80, 80, SIZE-80, SIZE-80], outline=(245, 158, 11, 70), width=6)
    draw.ellipse([140, 140, SIZE-140, SIZE-140], outline=(245, 158, 11, 40), width=3)
    # Orbit arc
    draw.arc([60, 200, SIZE-60, SIZE-100], start=190, end=350, fill=(251, 191, 36, 120), width=5)

    # Warm gold starlight
    stars = [
        (512, 140, 36, 9), (260, 220, 20, 5), (760, 230, 24, 6),
        (340, 360, 16, 4), (680, 340, 18, 4), (820, 450, 14, 3)
    ]
    for sx, sy, ro, ri in stars:
        draw_star(draw, sx, sy, ro, ri, (254, 240, 138))
        draw_star(draw, sx, sy, ro*0.5, ri*0.5, (255, 255, 255))

    # Golden Telescope in background
    tele_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(tele_layer)
    draw_telescope_1(tdraw, 512, 450, scale=1.75, color=(217, 119, 6), highlight=(252, 211, 77), mount=(180, 83, 9))
    img = Image.alpha_composite(img, tele_layer)
    draw = ImageDraw.Draw(img)

    # Gold plaque / bar across bottom for APS
    font = get_font(230, bold=True)
    text = "APS"
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (SIZE - tw) // 2
    ty = SIZE - th - 210

    # Glow
    text_glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    tgdraw = ImageDraw.Draw(text_glow)
    tgdraw.text((tx, ty), text, font=font, fill=(245, 158, 11, 100))
    text_glow = text_glow.filter(ImageFilter.GaussianBlur(14))
    img = Image.alpha_composite(img, text_glow)
    draw = ImageDraw.Draw(img)

    # Text shadow & text
    draw.text((tx+4, ty+8), text, font=font, fill=(0, 0, 0, 240))
    draw.text((tx, ty), text, font=font, fill=(254, 243, 199))

    # Outer double gold ring
    draw.ellipse([24, 24, SIZE-24, SIZE-24], outline=(245, 158, 11), width=18)
    draw.ellipse([46, 46, SIZE-46, SIZE-46], outline=(251, 191, 36), width=6)

    return img.resize((512, 512), Image.Resampling.LANCZOS)

def create_option_3():
    # 3. Cyber Tech Hexagon (Turquesa Neón & Grafito Oscuro)
    SIZE = 1024
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Hexagon coordinates
    cx, cy = SIZE // 2, SIZE // 2
    r_hex = SIZE // 2 - 36
    hex_pts = []
    for i in range(6):
        a = i * math.pi / 3 - math.pi / 6
        hex_pts.append((cx + r_hex * math.cos(a), cy + r_hex * math.sin(a)))

    draw.polygon(hex_pts, fill=(15, 23, 42))

    # Inner hexagon
    r_hex_in = r_hex - 28
    hex_in_pts = []
    for i in range(6):
        a = i * math.pi / 3 - math.pi / 6
        hex_in_pts.append((cx + r_hex_in * math.cos(a), cy + r_hex_in * math.sin(a)))
    draw.polygon(hex_in_pts, fill=(17, 24, 39), outline=(13, 148, 136, 100))

    # Cyber grid / crosshairs
    draw.line([(cx - 320, cy), (cx + 320, cy)], fill=(20, 184, 166, 40), width=4)
    draw.line([(cx, cy - 320), (cx, cy + 320)], fill=(20, 184, 166, 40), width=4)
    draw.ellipse([cx - 220, cy - 220, cx + 220, cy + 220], outline=(20, 184, 166, 50), width=4)

    # Stylized telescope
    tele_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(tele_layer)
    draw_telescope_1(tdraw, 520, 450, scale=1.75, color=(13, 148, 136), highlight=(45, 212, 191), mount=(51, 65, 85))
    img = Image.alpha_composite(img, tele_layer)
    draw = ImageDraw.Draw(img)

    # APS Text
    font = get_font(250, bold=True)
    text = "APS"
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (SIZE - tw) // 2
    ty = SIZE - th - 190

    # Glow
    text_glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    tgdraw = ImageDraw.Draw(text_glow)
    tgdraw.text((tx, ty), text, font=font, fill=(45, 212, 191, 140))
    text_glow = text_glow.filter(ImageFilter.GaussianBlur(16))
    img = Image.alpha_composite(img, text_glow)
    draw = ImageDraw.Draw(img)

    draw.text((tx+5, ty+8), text, font=font, fill=(0, 0, 0, 240))
    draw.text((tx, ty), text, font=font, fill=(240, 253, 250))

    # Hexagon outer neon border
    draw.polygon(hex_pts, outline=(45, 212, 191), width=16)

    return img.resize((512, 512), Image.Resampling.LANCZOS)

def create_option_4():
    # 4. Modern Flat App Icon (Deep Violet-Indigo to Midnight)
    SIZE = 1024
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    r = 220
    # Gradient background simulated
    base = Image.new("RGBA", (SIZE, SIZE), (24, 18, 59))
    bdraw = ImageDraw.Draw(base)
    for y in range(SIZE):
        factor = y / SIZE
        r_c = int(40 * (1 - factor) + 15 * factor)
        g_c = int(24 * (1 - factor) + 23 * factor)
        b_c = int(80 * (1 - factor) + 50 * factor)
        bdraw.line([(0, y), (SIZE, y)], fill=(r_c, g_c, b_c))

    # Mask to squircle
    mask = Image.new("L", (SIZE, SIZE), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle([20, 20, SIZE-20, SIZE-20], radius=r, fill=255)
    img.paste(base, (0, 0), mask)
    draw = ImageDraw.Draw(img)

    # Stars
    stars = [
        (180, 200, 26, 7), (800, 180, 30, 8), (480, 160, 20, 5),
        (850, 420, 16, 4), (160, 480, 14, 4), (660, 240, 18, 5)
    ]
    for sx, sy, ro, ri in stars:
        draw_star(draw, sx, sy, ro, ri, (255, 255, 255, 220))

    # Sleek White / Silver Minimal Telescope
    tele_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(tele_layer)
    draw_telescope_1(tdraw, 520, 450, scale=1.75, color=(241, 245, 249), highlight=(255, 255, 255), mount=(148, 163, 184))
    img = Image.alpha_composite(img, tele_layer)
    draw = ImageDraw.Draw(img)

    # Bold Clean APS
    font = get_font(260, bold=True)
    text = "APS"
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (SIZE - tw) // 2
    ty = SIZE - th - 175

    # Soft dark drop shadow
    draw.text((tx+5, ty+10), text, font=font, fill=(10, 10, 25, 220))
    # Crisp white text
    draw.text((tx, ty), text, font=font, fill=(255, 255, 255))

    # Subtle inner border
    draw.rounded_rectangle([20, 20, SIZE-20, SIZE-20], radius=r, outline=(192, 132, 252, 140), width=14)

    return img.resize((512, 512), Image.Resampling.LANCZOS)

opt1 = create_option_1()
opt1.save(f"{OUTPUT_DIR}/opcion_1_cosmic_neon.png")

opt2 = create_option_2()
opt2.save(f"{OUTPUT_DIR}/opcion_2_golden_emblem.png")

opt3 = create_option_3()
opt3.save(f"{OUTPUT_DIR}/opcion_3_cyber_hexagon.png")

opt4 = create_option_4()
opt4.save(f"{OUTPUT_DIR}/opcion_4_minimal_violet.png")

# Also create a composite 2x2 comparison grid with labels and browser tab preview
comp = Image.new("RGBA", (1100, 1200), (15, 23, 42, 255))
cdraw = ImageDraw.Draw(comp)

title_font = get_font(44, bold=True)
desc_font = get_font(24, bold=False)
label_font = get_font(28, bold=True)

cdraw.text((550, 40), "PROPUESTAS DE ICONO (FAVICON) - ACADEMIC PAPER STUDIO", font=title_font, fill=(241, 245, 249), anchor="mm")
cdraw.text((550, 85), "Siglas APS + Telescopio astronómico de fondo (Alta visibilidad en pestañas)", font=desc_font, fill=(148, 163, 184), anchor="mm")

# Place the 4 options: (x, y)
positions = [
    (80, 140, opt1, "OPCIÓN 1: Cosmic Neon (Cian / Espacio)", "Cian brillante sobre noche cósmica con destellos"),
    (600, 140, opt2, "OPCIÓN 2: Golden Observatory (Emblema Dorado)", "Elegante insignia circular dorada sobre azul marino"),
    (80, 660, opt3, "OPCIÓN 3: Cyber Hexagon (Turquesa Tech)", "Geometría hexagonal moderna con retícula científica"),
    (600, 660, opt4, "OPCIÓN 4: Modern Minimal (Violeta & Blanco)", "Estilo app moderna con alto contraste para pestañas")
]

for x, y, icon_img, title, subtitle in positions:
    resized_preview = icon_img.resize((420, 420), Image.Resampling.LANCZOS)
    comp.paste(resized_preview, (x, y), resized_preview)
    cdraw.text((x + 210, y + 445), title, font=label_font, fill=(56, 189, 248), anchor="mm")
    cdraw.text((x + 210, y + 475), subtitle, font=desc_font, fill=(203, 213, 225), anchor="mm")

comp.save(f"{OUTPUT_DIR}/comparativa_opciones_aps.png")
print("Successfully generated all 4 options and comparison grid!")
