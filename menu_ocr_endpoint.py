"""
Menu OCR Endpoint — v5 OPENROUTER (FREE & NO QUOTA ISSUES)
===========================================================

Uses OpenRouter API with free Gemini/Llama vision models.
OpenRouter gives you FREE access to multiple vision models
with separate quotas from Google's own API.

GET FREE API KEY (2 minutes):
  1. Go to https://openrouter.ai
  2. Sign up with Google
  3. Go to Keys → Create Key
  4. Paste below or set OPENROUTER_API_KEY env variable

Free models available (auto-fallback between them):
  - google/gemini-2.0-flash-exp:free   (best quality)
  - meta-llama/llama-3.2-11b-vision-instruct:free (backup)
  - qwen/qwen2.5-vl-72b-instruct:free  (backup)
"""

import re
import os
import base64
import time
import json
import requests
from io import BytesIO
from flask import request, jsonify
from PIL import Image

# ─────────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────────

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "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")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Free vision models — will try each one in order if previous fails
# Replace the FREE_MODELS list (around line 35) with these current working ones:
FREE_MODELS = [
    "openrouter/free",                           # ← Auto-picks best available free model
    "qwen/qwen2.5-vl-32b-instruct:free",        # ← Best free OCR model right now
    "mistralai/mistral-small-3.1-24b-instruct:free",  # ← Backup
    "google/gemma-3-27b-it:free",               # ← Backup
]

# ─────────────────────────────────────────────────────────────────
#  CATEGORY CONFIG
# ─────────────────────────────────────────────────────────────────

CATEGORY_MAP = {
    "beverages": [
        "tea","coffee","juice","lassi","water","soda","shake","smoothie",
        "drink","chai","latte","cappuccino","espresso","americano","frappe",
        "mojito","lemonade","buttermilk","cold coffee","milk","milkshake",
    ],
    "appetizers": [
        "starter","soup","salad","chaat","tikka","kebab","roll","samosa",
        "pakora","vada","bruschetta","nachos","wings","snack","puri","bhel",
        "spring roll","manchurian","gobi","aloo","finger","appetizer",
    ],
    "main": [
        "rice","dal","curry","biryani","roti","naan","paratha","thali",
        "burger","pizza","pasta","sandwich","wrap","dosa","idli","fried rice",
        "noodles","chicken","paneer","mutton","fish","prawn","egg","kothu",
        "biriyani","gravy","masala","butter chicken","kadai","korma",
        "vindaloo","pulao","sabzi",
    ],
    "desserts": [
        "ice cream","kulfi","gulab","halwa","cake","brownie","pudding",
        "kheer","rasgulla","jalebi","ladoo","sweet","pastry","payasam",
        "kesari","peda","barfi","rasmalai",
    ],
    "sides": [
        "fries","bread","garlic bread","coleslaw","raita","pickle",
        "papad","chutney","sauce","chips",
    ],
}

CATEGORY_ICONS = {
    "beverages":  "☕",
    "appetizers": "🥗",
    "main":       "🍽️",
    "desserts":   "🍰",
    "sides":      "🍞",
    "other":      "🍴",
}

PROMPT = """You are a menu reader. Look at this restaurant menu image carefully.

Extract ALL food and drink items you can see, along with their prices.

Return ONLY a valid JSON array. No explanation, no markdown, no extra text.
Format exactly like this:
[
  {"name": "Butter Chicken", "price": 320},
  {"name": "Masala Chai", "price": 40},
  {"name": "Paneer Tikka", "price": 220}
]

Rules:
- Include every item you can read, even partially visible ones
- Price should be a number only (no rupee symbol, no Rs, just digits like 320)
- If price is unclear or missing, use 0
- Include items from ALL sections (starters, mains, drinks, desserts, etc.)
- Clean up OCR artifacts in names
- If this is not a menu image, return []
"""


def guess_category(name: str) -> str:
    n = name.lower()
    for cat, keywords in CATEGORY_MAP.items():
        if any(k in n for k in keywords):
            return cat
    return "other"


# ─────────────────────────────────────────────────────────────────
#  IMAGE DOWNLOADER
# ─────────────────────────────────────────────────────────────────

class ImageDownloader:
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": "https://www.google.com/",
    }

    def url_to_base64(self, url: str) -> tuple:
        try:
            url = self._upgrade_url(url)
            resp = requests.get(url, headers=self.HEADERS, timeout=20, allow_redirects=True)
            if resp.status_code != 200:
                return None, None

            ct = resp.headers.get("content-type", "image/jpeg")
            if "image" not in ct and "octet" not in ct:
                return None, None

            data = resp.content
            if len(data) < 2000:
                return None, None

            try:
                pil = Image.open(BytesIO(data)).convert("RGB")
                w, h = pil.size
                if w < 80 or h < 80:
                    return None, None
                if w > 1024 or h > 1024:
                    ratio = min(1024/w, 1024/h)
                    pil = pil.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
                buf = BytesIO()
                pil.save(buf, format="JPEG", quality=85)
                data = buf.getvalue()
            except Exception:
                pass

            b64 = base64.b64encode(data).decode("utf-8")
            return b64, "image/jpeg"

        except Exception as e:
            print(f"[DL] Failed {url[:60]}: {e}")
            return None, None

    def raw_b64_to_clean(self, b64: str) -> tuple:
        try:
            mime = "image/jpeg"
            if "," in b64:
                header, b64 = b64.split(",", 1)
                if "png" in header:
                    mime = "image/png"
            return b64, mime
        except Exception:
            return None, None

    def _upgrade_url(self, url: str) -> str:
        url = re.sub(r"&w=\d+", "&w=1200", url)
        url = re.sub(r"&h=\d+", "", url)
        url = re.sub(r"=s\d+-", "=s1200-", url)
        url = re.sub(r"=w\d+", "=w1200", url)
        return url


# ─────────────────────────────────────────────────────────────────
#  OPENROUTER VISION EXTRACTOR
# ─────────────────────────────────────────────────────────────────

class OpenRouterMenuExtractor:
    """
    Sends menu image to OpenRouter free vision models.
    Auto-falls back to next model if one is rate limited.
    """

    def extract(self, b64_image: str, mime_type: str = "image/jpeg") -> list:
        if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "PASTE_YOUR_OPENROUTER_KEY_HERE":
            raise ValueError(
                "OpenRouter API key not set. "
                "Get free key at https://openrouter.ai "
                "and set OPENROUTER_API_KEY environment variable."
            )

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",  # required by OpenRouter
            "X-Title": "Menu OCR App",
        }

        payload = {
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{b64_image}"
                        }
                    },
                    {
                        "type": "text",
                        "text": PROMPT
                    }
                ]
            }],
            "max_tokens": 2048,
            "temperature": 0.1,
        }

        # Try each free model in order
        for model in FREE_MODELS:
            payload["model"] = model
            print(f"[OCR] Trying model: {model}")

            try:
                resp = requests.post(
                    OPENROUTER_URL,
                    json=payload,
                    headers=headers,
                    timeout=40
                )

                if resp.status_code == 429:
                    print(f"[OCR] {model} rate limited, trying next model...")
                    time.sleep(2)
                    continue

                if resp.status_code != 200:
                    print(f"[OCR] {model} error {resp.status_code}: {resp.text[:200]}")
                    continue

                result = resp.json()
                text = result["choices"][0]["message"]["content"]
                print(f"[OCR] ✓ {model} responded")
                return self._parse_json(text)

            except Exception as e:
                print(f"[OCR] {model} exception: {e}")
                continue

        print("[OCR] All models failed")
        return []

    def _parse_json(self, text: str) -> list:
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        text = text.strip()

        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1:
            print(f"[OCR] No JSON array in: {text[:100]}")
            return []

        json_str = text[start:end+1]
        try:
            items = json.loads(json_str)
            return [i for i in items if isinstance(i, dict) and i.get("name")]
        except json.JSONDecodeError as e:
            print(f"[OCR] JSON parse error: {e}")
            return []


# ─────────────────────────────────────────────────────────────────
#  BATCH PROCESSOR
# ─────────────────────────────────────────────────────────────────

class BatchMenuProcessor:
    def __init__(self):
        self.dl = ImageDownloader()
        self.extractor = OpenRouterMenuExtractor()

    def process_urls(self, urls: list, max_images: int = 20) -> dict:
        unique = list(dict.fromkeys(u for u in urls if u))[:max_images]
        total = len(unique)
        print(f"[Batch] Processing {total} images via OpenRouter...")

        all_raw_items = []
        ok, fail = 0, 0

        for i, url in enumerate(unique):
            try:
                print(f"[Batch] Image {i+1}/{total}: downloading...")
                b64, mime = self.dl.url_to_base64(url)
                if b64 is None:
                    print(f"[Batch] Image {i+1}/{total}: download failed")
                    fail += 1
                    continue

                print(f"[Batch] Image {i+1}/{total}: sending to OCR...")
                items = self.extractor.extract(b64, mime)
                all_raw_items.extend(items)
                ok += 1
                print(f"[Batch] Image {i+1}/{total}: ✓ found {len(items)} items")

                if i < total - 1:
                    time.sleep(2)  # OpenRouter is more generous, 2s is enough

            except Exception as e:
                fail += 1
                print(f"[Batch] Image {i+1}/{total}: error: {e}")

        merged = self._merge(all_raw_items)
        print(f"[Batch] Done: {ok} ok, {fail} fail → {len(merged)} unique items")

        return {
            "items": merged,
            "stats": {
                "images_processed": ok,
                "images_failed": fail,
                "total_images": total,
                "items_found": len(merged),
            }
        }

    def process_b64_list(self, b64_list: list, max_images: int = 20) -> dict:
        all_raw_items = []
        ok, fail = 0, 0
        total = min(len(b64_list), max_images)

        for i, b64 in enumerate(b64_list[:max_images]):
            try:
                clean_b64, mime = self.dl.raw_b64_to_clean(b64)
                if not clean_b64:
                    fail += 1
                    continue
                items = self.extractor.extract(clean_b64, mime)
                all_raw_items.extend(items)
                ok += 1
                print(f"[Batch] b64 {i+1}/{total}: {len(items)} items")
                if i < total - 1:
                    time.sleep(2)
            except Exception as e:
                fail += 1
                print(f"[Batch] b64 {i+1}: error: {e}")

        merged = self._merge(all_raw_items)
        return {
            "items": merged,
            "stats": {"processed": ok, "failed": fail, "items_found": len(merged)},
        }

    def _merge(self, raw_items: list) -> list:
        seen = {}
        result = []

        for raw in raw_items:
            name = str(raw.get("name", "")).strip()
            if not name or len(name) < 2:
                continue

            key = re.sub(r"[\s\W]", "", name.lower())
            if not key:
                continue

            price_raw = raw.get("price", 0)
            try:
                price = float(price_raw)
            except (ValueError, TypeError):
                price = 0.0

            if key in seen:
                existing = seen[key]
                if len(name) > len(existing["name"]):
                    seen[key]["name"] = name
                if price > 0 and existing["price"] == 0:
                    seen[key]["price"] = price
                continue

            cat = guess_category(name)
            item = {
                "id": f"menu_{len(seen)}_{name[:10].replace(' ','_')}",
                "name": name.title(),
                "price": price,
                "priceRaw": f"₹{int(price)}" if price > 0 else "Price N/A",
                "category": cat,
                "icon": CATEGORY_ICONS.get(cat, "🍴"),
            }
            seen[key] = item
            result.append(item)

        for i, item in enumerate(result):
            item["id"] = f"menu_{i}_{item['name'][:10].replace(' ','_')}"

        return result


# ─────────────────────────────────────────────────────────────────
#  FLASK ROUTE
# ─────────────────────────────────────────────────────────────────

_processor = BatchMenuProcessor()


def register_menu_ocr_routes(app, ocr_engine_instance=None):
    @app.route("/api/menu-ocr", methods=["POST"])
    def api_menu_ocr():
        try:
            if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "PASTE_YOUR_OPENROUTER_KEY_HERE":
                return jsonify({
                    "error": (
                        "OpenRouter API key not configured. "
                        "Get free key at https://openrouter.ai "
                        "then set OPENROUTER_API_KEY env variable."
                    )
                }), 500

            data = request.get_json(silent=True) or {}

            urls = list(data.get("image_urls", []))
            single = data.get("image_url", "").strip()
            if single:
                urls = [single] + [u for u in urls if u != single]

            b64s = data.get("images_b64", [])

            if not urls and not b64s:
                return jsonify({"error": "Send image_urls or images_b64"}), 400

            if b64s:
                result = _processor.process_b64_list(b64s, max_images=20)
            else:
                result = _processor.process_urls(urls, max_images=20)

            return jsonify({
                "items":      result["items"],
                "stats":      result.get("stats", {}),
                "item_count": len(result["items"]),
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    return app


# ─────────────────────────────────────────────────────────────────
#  QUICK TEST
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        url = sys.argv[1]
        print(f"Testing with URL: {url}\n")
        p = BatchMenuProcessor()
        result = p.process_urls([url])
        print(f"\nFound {len(result['items'])} items:")
        for item in result["items"]:
            print(f"  {item['icon']} [{item['category']:10}]  "
                  f"{item['name']:<35} {item['priceRaw']}")
    else:
        print("Usage: python menu_ocr_endpoint.py <image_url>")
        print("\nChecking API key...")
        if OPENROUTER_API_KEY and OPENROUTER_API_KEY != "PASTE_YOUR_OPENROUTER_KEY_HERE":
            print(f"✓ OpenRouter key set: {OPENROUTER_API_KEY[:15]}...")
        else:
            print("✗ Key NOT set. Get free key at: https://openrouter.ai")