"""
generate_sample_receipt.py - Creates a clean sample receipt image for testing
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_sample_receipt(output_path="sample_receipt.png"):
    # Create white canvas with receipt dimensions
    width, height = 400, 580
    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Receipt border & header line
    draw.rectangle([10, 10, width - 10, height - 10], outline=(200, 200, 200), width=2)

    # Header
    draw.text((120, 30), "SUPERMARKET PLUS", fill=(30, 30, 30))
    draw.text((130, 55), "123 Main Street, Suite 4", fill=(100, 100, 100))
    draw.text((140, 75), "Tel: (555) 019-2834", fill=(100, 100, 100))

    draw.line([(30, 105), (370, 105)], fill=(180, 180, 180), width=1)

    # Meta
    draw.text((30, 120), "Date: 2026-08-26", fill=(60, 60, 60))
    draw.text((250, 120), "Time: 14:32", fill=(60, 60, 60))
    draw.text((30, 140), "Cashier: Alex M.", fill=(60, 60, 60))
    draw.text((250, 140), "Receipt #: 98421", fill=(60, 60, 60))

    draw.line([(30, 170), (370, 170)], fill=(180, 180, 180), width=1)

    # Items
    draw.text((30, 185), "ITEM DESCRIPTION", fill=(40, 40, 40))
    draw.text((310, 185), "PRICE", fill=(40, 40, 40))
    draw.line([(30, 205), (370, 205)], fill=(220, 220, 220), width=1)

    items = [
        ("Organic Whole Milk (1 gal)", "$4.99"),
        ("Fresh Strawberries (1 lb)", "$3.50"),
        ("Sourdough Artisan Bread", "$5.25"),
        ("Greek Yogurt 32oz", "$6.49"),
        ("Free-Range Eggs (12 pk)", "$4.79"),
        ("Avocados (Bag of 4)", "$3.99"),
        ("Olive Oil Extra Virgin 500ml", "$11.50"),
    ]

    y = 220
    for name, price in items:
        draw.text((30, y), name, fill=(50, 50, 50))
        draw.text((320, y), price, fill=(50, 50, 50))
        y += 28

    draw.line([(30, y + 10), (370, y + 10)], fill=(180, 180, 180), width=1)
    y += 25

    # Totals
    draw.text((200, y), "Subtotal:", fill=(70, 70, 70))
    draw.text((320, y), "$40.51", fill=(70, 70, 70))
    y += 24

    draw.text((200, y), "Sales Tax (8.5%):", fill=(70, 70, 70))
    draw.text((320, y), "$3.44", fill=(70, 70, 70))
    y += 28

    draw.line([(200, y), (370, y)], fill=(100, 100, 100), width=2)
    y += 10

    draw.text((170, y), "TOTAL AMOUNT:", fill=(10, 10, 10))
    draw.text((310, y), "$43.95", fill=(10, 10, 10))
    y += 35

    draw.text((30, y), "Payment: Apple Pay (Visa ****1234)", fill=(80, 80, 80))
    y += 35

    draw.text((115, y), "*** THANK YOU FOR SHOPPING ***", fill=(100, 100, 100))

    image.save(output_path)
    print(f"Sample receipt saved to {output_path}")

if __name__ == "__main__":
    create_sample_receipt(os.path.join(os.path.dirname(__file__), "sample_receipt.png"))
