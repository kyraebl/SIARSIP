import os
import sys

from PIL import Image


def main(path):
    img = Image.open(path).convert("RGBA")
    img = img.crop(img.getbbox())
    os.makedirs("static", exist_ok=True)

    tinggi = 320
    icon = img.resize((round(img.width * tinggi / img.height), tinggi), Image.LANCZOS)
    icon.save("static/logo-icon.png", optimize=True)

    sisi = max(img.size)
    kanvas = Image.new("RGBA", (sisi, sisi), (0, 0, 0, 0))
    kanvas.paste(img, ((sisi - img.width) // 2, (sisi - img.height) // 2), img)
    kanvas.resize((64, 64), Image.LANCZOS).save("static/favicon.png", optimize=True)
    print("Selesai: static/logo-icon.png dan static/favicon.png")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Pakai: python buat_logo.py Dewan_Sumber_Daya_Air_Nasional.png")
    main(sys.argv[1])