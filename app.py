import os
import io
import base64
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, render_template, request, send_file, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
import numpy as np
import cv2
from ultralytics import YOLO

UPLOAD_FOLDER = 'uploads'
ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg'}
ALLOWED_VIDEO_EXT = {'mp4', 'mov', 'avi', 'mkv'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

MODEL = None
MODEL_PATH = "best.pt" # your detection model
  
def load_model():
    global MODEL
    if MODEL is None:
        MODEL = YOLO(MODEL_PATH)  # YOLO detection model
    return MODEL
 
def detect_image_pil(pil_image):
    """
    Run YOLO detection on a PIL image.
    Returns list of detections with normalized labels.
    """
    model = load_model()
    results = model(pil_image)

    # 🔑 NORMALIZATION MAP (VERY IMPORTANT)
    label_map = {
        'with helmet': 'helmet',
        'without helmet': 'no_helmet',
        'without helmets': 'no_helmet',
        'helmet': 'helmet',
        'no_helmet': 'no_helmet',
        'rider': 'rider',
        'plate number': 'platenumber',
        'platenumber': 'platenumber'
    }

    dets = []

    for r in results:
        boxes = r.boxes.xyxy.cpu().numpy()
        scores = r.boxes.conf.cpu().numpy()
        labels = r.boxes.cls.cpu().numpy().astype(int)
        names = r.names  # index → label name

        for box, score, label_id in zip(boxes, scores, labels):
            raw_label = names[label_id].lower().strip()

            # Normalize label
            norm_label = label_map.get(raw_label, raw_label)

            dets.append({
                'x1': float(box[0]),
                'y1': float(box[1]),
                'x2': float(box[2]),
                'y2': float(box[3]),
                'label': norm_label,
                'score': float(score)
            })

    return dets


def draw_detections_pil(pil_image, detections):
    """
    Draw bounding boxes with labels below each box and a centered bottom legend.
    Font sizes and box widths scale with image size.
    """
    im = pil_image.convert('RGB')
    draw = ImageDraw.Draw(im)

    # Dynamically calculate font size based on image height
    fh = pil_image.height
    font_size = max(fh // 25, 12)  # minimum font size 12
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()

    class_colors = {
        'helmet': 'green',
        'no_helmet': 'red',
        'rider': 'blue',
        'platenumber': 'orange'
    }

    # Draw bounding boxes and labels below each box
    for d in detections:
        x1, y1, x2, y2 = d['x1'], d['y1'], d['x2'], d['y2']
        color = class_colors.get(d['label'], 'gray')

        # Draw bounding box
        draw.rectangle(
            [x1, y1, x2, y2],
            outline=color,
            width=max(2, font_size // 10)
        )

        # Prepare label text
        label_text = f"{d['label']} {d['score']:.2f}"
        bbox = font.getbbox(label_text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Position label below the box
        text_x = x1
        text_y = y2 + 2  # small gap below the box

        # Draw white background rectangle
        draw.rectangle(
            [text_x - 1, text_y - 1, text_x + text_width + 2, text_y + text_height + 10],
            fill='white'
        )

        # Draw text
        draw.text((text_x, text_y), label_text, fill=color, font=font)

    # Draw centered legend at the bottom
    padding = 5
    legend_items = list(class_colors.items())
    # Calculate total legend width
    total_width = 0
    for cls, _ in legend_items:
        text_w = font.getbbox(cls)[2] - font.getbbox(cls)[0]
        total_width += font_size + text_w + 3 * padding
    total_width -= padding  # remove last extra padding

    # Start x to center the legend
    x_start = (pil_image.width - total_width) // 2
    y_start = pil_image.height - font_size - 2 * padding - 10  # bottom margin
  
    # White background rectangle for legend
    draw.rectangle(
        [x_start - padding, y_start - padding,
         x_start + total_width + padding, pil_image.height -17],
        fill='white'
    )

    # Draw each legend item
    x = x_start
    y = y_start
    for cls, color in legend_items:
        # Color box
        draw.rectangle([x, y, x + font_size, y + font_size], fill=color)
        x += font_size + padding

        # Text
        draw.text((x, y), cls, fill='black', font=font)
        text_w = font.getbbox(cls)[2] - font.getbbox(cls)[0]
        x += text_w + 2 * padding

    return im




def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

@app.route('/')
def index():
    return render_template('index.html')

# --- Picture demo ---
@app.route('/picture', methods=['GET', 'POST'])
def picture():
    result_image = None

    if request.method == 'POST':
        if 'image' not in request.files:
            return render_template('picture.html')

        file = request.files['image']
        if file.filename == '':
            return render_template('picture.html')

        if file and allowed_file(file.filename, ALLOWED_IMAGE_EXT):
            filename = secure_filename(file.filename)
            in_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(in_path)

            # Load image
            pil = Image.open(in_path).convert("RGB")

            # Detect
            dets = detect_image_pil(pil)

            # Draw detections
            out_im = draw_detections_pil(pil, dets)

            # Save output image
            out_filename = "out_" + filename
            out_path = os.path.join(app.config['UPLOAD_FOLDER'], out_filename)
            out_im.save(out_path, "JPEG")

            result_image = url_for('uploaded_file', filename=out_filename)

    return render_template('picture.html', result_image=result_image)

# --- Video demo ---
from flask import url_for

@app.route('/video', methods=['GET', 'POST'])
def video():
    result_video = None

    if request.method == 'POST':
        if 'video' not in request.files:
            return "No video uploaded", 400

        file = request.files['video']
        if file.filename == '':
            return "Empty filename", 400

        if file and allowed_file(file.filename, ALLOWED_VIDEO_EXT):
            filename = secure_filename(file.filename)
            in_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(in_path)

            out_filename = 'out_' + filename
            out_path = os.path.join(app.config['UPLOAD_FOLDER'], out_filename)

            # Open input video
            cap = cv2.VideoCapture(in_path)
            original_fps = cap.get(cv2.CAP_PROP_FPS) or 25
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # Output video slower for smooth effect
            slow_fps = min(15, original_fps)  # slow-motion effect
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(out_path, fourcc, slow_fps, (w, h))

            model = load_model()
            FRAME_SKIP = 2  # detect every 2 frames
            frame_idx = 0
            last_dets = []  # store last detections

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                fh, fw = frame.shape[:2]
                # Resize frame for faster detection
                scale = 1.0
                MAX_WIDTH = 640
                if fw > MAX_WIDTH:
                    scale = MAX_WIDTH / fw
                    frame_resized = cv2.resize(frame, (int(fw*scale), int(fh*scale)))
                else:
                    frame_resized = frame.copy()

                # Run detection every FRAME_SKIP frames
                if frame_idx % FRAME_SKIP == 0:
                    pil = Image.fromarray(cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB))
                    last_dets = detect_image_pil(pil)

                # Draw last detections on the frame
                annotated = draw_detections_pil(Image.fromarray(cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)), last_dets)
                annotated = annotated.resize((fw, fh))
                frame_out = cv2.cvtColor(np.array(annotated), cv2.COLOR_RGB2BGR)
                out.write(frame_out)

                frame_idx += 1

            cap.release()
            out.release()

            # Pass processed video URL to template
            result_video = url_for('uploaded_file', filename=out_filename)

    return render_template('video.html', result_video=result_video)

# Serve uploaded files
from flask import send_from_directory

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# --- Realtime demo ---
@app.route('/realtime')
def realtime():
    return render_template('realtime.html')

@app.route('/realtime/frame', methods=['POST'])
def realtime_frame():
    import base64, io
    from PIL import Image
    from flask import request, jsonify

    data = request.json
    if not data or 'image' not in data:
        return jsonify({'error': 'no image'}), 400

    b64 = data['image'].split(',', 1)[-1]
    image_bytes = base64.b64decode(b64)
    pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    dets = detect_image_pil(pil)  # your detection function
    return jsonify({'detections': dets})


if __name__ == '__main__':
    app.run(debug=True)
