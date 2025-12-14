let stream = null;
let captureInterval = null;
let videoEl = document.getElementById("localVideo");
let overlay = document.getElementById("overlay");
let ctx = overlay.getContext("2d");
let select = document.getElementById("videoSelect");
let fpsCounter = document.getElementById("fpsCounter");
let spinnerOverlay = document.getElementById("spinnerOverlay");
let spinnerBorder = document.getElementById("spinnerborder");

let lastFrameTime = Date.now();
let frameCount = 0;
let fps = 0;

let lastDetections = []; // cache last detections
let detectionInterval = 200; // ms between detection requests (~5 FPS)
let lastDetectionTime = 0;

// --------------------
// List available cameras
// --------------------
async function listDevices() {
  const devices = await navigator.mediaDevices.enumerateDevices();
  const cams = devices.filter((d) => d.kind === "videoinput");
  select.innerHTML = "";
  cams.forEach((c, i) => {
    const opt = document.createElement("option");
    opt.value = c.deviceId;
    opt.text = c.label || `Camera ${i + 1}`;
    select.appendChild(opt);
  });
}

// --------------------
// Start camera
// --------------------
async function start() {
  stop(); // stop any previous stream

  spinnerOverlay.style.display = "flex";
  spinnerBorder.style.display = "flex";
  document.getElementById("startBtn").disabled = true;
  document.getElementById("stopBtn").disabled = false;

  setTimeout(async () => {
    try {
      const deviceId = select.value || undefined;
      stream = await navigator.mediaDevices.getUserMedia({
        video: { deviceId: deviceId ? { exact: deviceId } : undefined },
        audio: false,
      });

      videoEl.srcObject = stream;

      videoEl.onplaying = () => {
        spinnerOverlay.style.display = "none";
        spinnerBorder.style.display = "none";
      };

      captureInterval = requestAnimationFrame(updateFrame);
    } catch (err) {
      console.error("Error accessing camera:", err);
      spinnerOverlay.style.display = "none";
      spinnerBorder.style.display = "none";
      document.getElementById("startBtn").disabled = false;
      document.getElementById("stopBtn").disabled = true;
    }
  }, 1000);
}

// --------------------
// Stop camera
// --------------------
function stop() {
  if (captureInterval) cancelAnimationFrame(captureInterval);
  captureInterval = null;

  if (stream) {
    stream.getTracks().forEach((t) => t.stop());
    stream = null;
  }

  videoEl.srcObject = null;
  ctx.clearRect(0, 0, overlay.width, overlay.height);

  spinnerOverlay.style.display = "none";
  spinnerBorder.style.display = "none";

  document.getElementById("startBtn").disabled = false;
  document.getElementById("stopBtn").disabled = true;

  fpsCounter.textContent = "0";
}

// --------------------
// Update frame (animation loop)
// --------------------
function updateFrame() {
  if (!videoEl || videoEl.readyState < 2) {
    captureInterval = requestAnimationFrame(updateFrame);
    return;
  }

  const now = Date.now();

  // Update overlay size
  overlay.width = videoEl.videoWidth;
  overlay.height = videoEl.videoHeight;

  // Send frame for detection only every detectionInterval
  if (now - lastDetectionTime > detectionInterval) {
    sendFrameForDetection();
    lastDetectionTime = now;
  }

  // Draw last detections for smooth overlay
  drawDetections(lastDetections);

  // FPS calculation
  frameCount++;
  if (now - lastFrameTime >= 1000) {
    fps = frameCount;
    frameCount = 0;
    lastFrameTime = now;
    fpsCounter.textContent = fps;
  }

  captureInterval = requestAnimationFrame(updateFrame);
}

// --------------------
// Send frame to backend
// --------------------
async function sendFrameForDetection() {
  const w = videoEl.videoWidth;
  const h = videoEl.videoHeight;

  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  const cctx = c.getContext("2d");
  cctx.drawImage(videoEl, 0, 0, w, h);
  const dataUrl = c.toDataURL("image/jpeg", 0.8);

  try {
    const res = await fetch("/realtime/frame", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: dataUrl }),
    });
    const json = await res.json();
    if (json.detections) lastDetections = json.detections;
  } catch (err) {
    console.error(err);
  }
}

// --------------------
// Draw detections on overlay
// --------------------
function drawDetections(dets) {
  ctx.clearRect(0, 0, overlay.width, overlay.height);
  if (!dets) return;

  const classColors = {
    helmet: "red",
    no_helmet: "orange",
    rider: "blue",
    platenumber: "green",
  };

  // Draw bounding boxes and labels
  const fontSize = 18;
  ctx.font = `${fontSize}px sans-serif`;
  ctx.textBaseline = "top";
  ctx.lineWidth = 3;

  dets.forEach((d) => {
    const x = d.x1;
    const y = d.y1;
    const w = d.x2 - d.x1;
    const h = d.y2 - d.y1;
    const color = classColors[d.label] || "red";

    ctx.strokeStyle = color;
    ctx.strokeRect(x, y, w, h);

    const labelText = `${d.label} ${d.score.toFixed(2)}`;
    const textWidth = ctx.measureText(labelText).width;
    const textHeight = fontSize + 4;
    const labelX = x;
    const labelY = y + h + 2; // below box

    // White background
    ctx.fillStyle = "white";
    ctx.globalAlpha = 0.8;
    ctx.fillRect(labelX, labelY, textWidth + 6, textHeight);
    ctx.globalAlpha = 1.0;

    ctx.fillStyle = color;
    ctx.fillText(labelText, labelX + 3, labelY + 2);
  });

  // Draw bottom-center legend with white background
  const legendPadding = 10;
  const legendSpacing = 20;
  let totalWidth = 0;
  const entries = Object.entries(classColors);

  // Compute total width for centering
  entries.forEach(([cls, color]) => {
    totalWidth += 15 + 5 + ctx.measureText(cls).width + 20;
  });
  let startX = (overlay.width - totalWidth) / 2;
  const legendY = overlay.height - 30;

  // Draw white background for whole legend
  const legendHeight = 20;
  ctx.fillStyle = "white";
  ctx.globalAlpha = 0.7;
  ctx.fillRect(0, legendY - 2, overlay.width, legendHeight);
  ctx.globalAlpha = 1.0;

  // Draw legend items
  entries.forEach(([cls, color]) => {
    ctx.fillStyle = color;
    ctx.fillRect(startX, legendY, 15, 15);
    ctx.fillStyle = "black";
    ctx.fillText(cls, startX + 20, legendY + 0);
    startX += 15 + 5 + ctx.measureText(cls).width + 20;
  });
}

// --------------------
// Event listeners
// --------------------
window.addEventListener("load", async () => {
  await listDevices();
  document.getElementById("startBtn").addEventListener("click", start);
  document.getElementById("stopBtn").addEventListener("click", stop);
});

// Cleanup on page unload
function cleanup() {
  stop();
}
window.addEventListener("beforeunload", cleanup);
document.addEventListener("visibilitychange", () => {
  if (document.hidden) cleanup();
});
