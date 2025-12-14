# Helmet Detection Flask Demo

This repository contains a starter Flask web app for demonstrating motor rider helmet detection with three demo modes:

1. **Picture** — upload a single image, run detection, receive an annotated image.
2. **Video** — upload a video, the server processes frames and returns an annotated output video for download/playback.
3. **Realtime** — the browser captures frames from a selected connected camera and sends them to the server for per-frame detection and overlay (low-latency demo).

> ⚠️ **Note:** The code includes placeholders for the actual helmet detection model. Replace the `detect_image_pil` and `load_model` functions in `app.py` with your real model loading and inference code (YOLOv8 or other).

---

## Quick Start

### 1. Create and activate a virtual environment

**Windows (cmd):**
```cmd
python -m venv venv
venv\Scripts\activate
```

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

---

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

Typical dependencies include:
- Flask
- Pillow (PIL)
- OpenCV (`opencv-python`)
- NumPy
- YOLOv8 or your chosen model library (`ultralytics` if using YOLOv8)

---

### 3. Run the Flask app
```bash
python app.py
```

By default, Flask will run on `http://127.0.0.1:5000`.

---

### 4. Access the demo modes

- **Picture mode:** `http://127.0.0.1:5000/`
- **Video mode:** `http://127.0.0.1:5000/video`
- **Realtime mode:** `http://127.0.0.1:5000/realtime`

> The realtime demo requires camera permission in your browser.

---

### 5. Folder structure

```
.
├── app.py                 # Flask app routes and logic
├── templates/             # HTML templates
│   ├── base.html
│   ├── index.html         # Picture mode
│   ├── video.html         # Video mode
│   └── realtime.html      # Realtime mode
├── static/
│   ├── js/
│   │   └── realtime.js
│   ├── css/
│   └── uploads/           # Saved uploads and processed results
├── requirements.txt
└── README.md
```

---

### 6. Adding your model

Replace the stub functions in `app.py`:

```python
def load_model():
    # Load your YOLOv8 or other helmet detection model here
    return model


def detect_image_pil(pil_image):
    # Run model inference on the PIL image
    # Return list of detections as dicts:
    # {x1, y1, x2, y2, label, score}
    return detections
```

---

### 7. Tips for Video Mode

- **Smooth detection:** Cache detection results for a few frames or apply a low-pass filter on box positions.
- **Slow motion / lower FPS:** Reducing frames per second can make detection more stable and reduce CPU usage.
- **Downloadable result:** Processed video files are saved to the `uploads/` folder. The frontend provides a direct download link after processing.
- **Video resolution:** Consider resizing frames to a max width (e.g., 640 px) to improve performance without losing detection accuracy.

---

### 8. Tips for Realtime Demo

- **Limit detection FPS** (e.g., 5–10 FPS) to reduce server load and latency.
- **Cache last detections** to draw smoothly between frames.
- **Resize frames** if the camera resolution is high to improve speed.
- The browser handles camera permissions; allow access to the selected camera.

---

### 9. Best Practices

- Test with a variety of lighting conditions and helmet colors for robust detection.
- For multiple users or high-resolution cameras, consider using a dedicated GPU or optimizing the model with TensorRT or ONNX.
- Monitor FPS and latency to ensure the realtime demo is smooth.

---

### 10. License

This project is provided as a starter demo. You can modify, distribute, or integrate it into your projects. Ensure compliance with licenses of any pretrained models used.

