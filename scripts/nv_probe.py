# Probe NVIDIA models (text + receipt image). Usage:
#   NV=$(grep "^NVIDIA_API_KEY=" /opt/kharcha/.env | cut -d= -f2) uv run --no-project --with pillow python scripts/nv_probe.py
import base64, io, json, os, time, urllib.request
from PIL import Image, ImageDraw, ImageFont

KEY = os.environ["NV"]
URL = "https://integrate.api.nvidia.com/v1/chat/completions"

def call(model, messages, max_tokens=200):
    body = json.dumps({"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0}).encode()
    req = urllib.request.Request(URL, body, {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            d = json.load(r)
        return round(time.time() - t, 1), (d["choices"][0]["message"].get("content") or "").strip()
    except urllib.error.HTTPError as e:
        return round(time.time() - t, 1), f"HTTP {e.code}: {e.read().decode()[:160]}"
    except Exception as e:
        return round(time.time() - t, 1), f"ERROR {e}"

# synthetic receipt image
img = Image.new("RGB", (520, 360), "white"); d = ImageDraw.Draw(img)
try: f = ImageFont.truetype("DejaVuSans.ttf", 26)
except OSError: f = ImageFont.load_default()
for i, line in enumerate(["BARBEQUE NATION", "Koregaon Park, Pune", "Date: 13/10/2026",
                          "Veg buffet x2   1562.00", "CGST 2.5%        39.00", "SGST 2.5%        39.00",
                          "TOTAL  Rs 1640.00"]):
    d.text((24, 20 + i * 46), line, fill="black", font=f)
buf = io.BytesIO(); img.save(buf, "PNG"); b64 = base64.b64encode(buf.getvalue()).decode()
ask = 'Read this receipt. Reply ONLY with JSON: {"vendor": str, "date": "YYYY-MM-DD", "total_rupees": number}'

print("== TEXT (expect OK)")
for m in ["nvidia/nemotron-3.5-lightning-30b-a3b", "nvidia/nemotron-3-super-120b-a12b", "nvidia/nemotron-nano-3-30b-a3b"]:
    s, out = call(m, [{"role": "user", "content": "Reply with the single word OK"}], 400)
    print(f"{m:48s} {s:5}s  {out[-80:]!r}")

print("== VISION (expect vendor BARBEQUE NATION, 2026-10-13, 1640)")
for m in ["nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", "google/gemma-4-31b-it", "google/gemma-3-12b-it",
          "meta/llama-3.2-90b-vision-instruct", "meta/llama-3.2-11b-vision-instruct", "microsoft/phi-3-vision-128k-instruct"]:
    msg = [{"role": "user", "content": [{"type": "text", "text": ask},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}]}]
    s, out = call(m, msg, 600)
    print(f"{m:48s} {s:5}s  {out[-160:]!r}")
