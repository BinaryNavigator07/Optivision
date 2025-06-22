from __future__ import annotations
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
import io

from .models.detector import detect_objects
from .models.scene import classify_environment
from .services.ocr_space import run_ocr
from .utils.weather import current_weather
from .utils.text_narrator import craft_sentence 
from .config import get_settings

app      = FastAPI(title="Optivision Inference API")
settings = get_settings()


@app.post("/inference")
async def inference(image: UploadFile = File(...)):
    # 0 ── read & validate image ------------------------------------------------
    try:
        img_bytes = await image.read()
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid image file")

    # 1 ── computer-vision tasks ------------------------------------------------
    detections = detect_objects(img)
    object_names = sorted({d.class_name for d in detections})

    env = classify_environment(img)  # "indoor" | "outdoor"

    # 2 ── OCR ------------------------------------------------------------------
    ocr_json = run_ocr(img)
    ocr_text = (
        (ocr_json.get("ParsedResults", [{}])[0].get("ParsedText") or "").strip()
        or None
    )

    # 3 ── weather (only when outdoors) ----------------------------------------
    weather = current_weather(31.5204, 74.3587) if env == "outdoor" else None

    # 4 ── friendly sentence ----------------------------------------------------
    description = craft_sentence(object_names, ocr_text, env, weather)

    print(f"{JSONResponse.__name__} {image.filename} → {description}")

    # 5 ── JSON response --------------------------------------------------------
    return JSONResponse(
        content={
            "description": description,                   # 🌟 for the frontend
            "detections":  [d.dict() for d in detections],
            "ocr_text":    ocr_text,
            "environment": env,
            "weather":     weather,
        }
    )
