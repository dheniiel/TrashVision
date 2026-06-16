const video    = document.getElementById('videoFeed');
const canvas   = document.getElementById('overlayCanvas');
const scanLine = document.getElementById('scanLine');
const cameraIdle = document.getElementById('cameraIdle');
const btnStart = document.getElementById('btnStart');
const btnStop  = document.getElementById('btnStop');
const btnSnap  = document.getElementById('btnSnap');
const fpsSel   = document.getElementById('fpsSel');
const detList  = document.getElementById('detectionList');
const detCount = document.getElementById('detCount');
const snapshotArea = document.getElementById('snapshotArea');
const snapshotImg  = document.getElementById('snapshotImg');
const snapDL       = document.getElementById('snapshotDownload');

let stream   = null;
let timer    = null;
let running  = false;

// ── Canvas overlay (draw bbox locally) ──
const ctx = canvas.getContext('2d');

function syncCanvas() {
  canvas.width  = video.videoWidth;
  canvas.height = video.videoHeight;
}

// ── Start / stop camera ──
btnStart.addEventListener('click', async () => {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode:'environment' }, audio: false });
    video.srcObject = stream;
    await video.play();
    video.style.display = 'block';
    canvas.style.display = 'block';
    cameraIdle.style.display = 'none';
    syncCanvas();

    btnStart.disabled = true;
    btnStop.disabled  = false;
    btnSnap.disabled  = false;
    running = true;
    startLoop();
  } catch(e) {
    alert('Não foi possível acessar a câmera: ' + e.message);
  }
});

btnStop.addEventListener('click', stopCamera);

function stopCamera() {
  running = false;
  if (timer) { clearInterval(timer); timer = null; }
  if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
  video.style.display = 'none';
  canvas.style.display = 'none';
  cameraIdle.style.display = 'flex';
  scanLine.classList.remove('active');
  btnStart.disabled = false;
  btnStop.disabled  = true;
  btnSnap.disabled  = true;
}

// ── Detection loop ──
function startLoop() {
  const interval = parseInt(fpsSel.value);
  if (timer) clearInterval(timer);
  timer = setInterval(detectFrame, interval);
  scanLine.classList.add('active');
}

fpsSel.addEventListener('change', () => { if (running) startLoop(); });

let detecting = false;
async function detectFrame() {
  if (detecting || !running || video.readyState < 2) return;
  detecting = true;
  syncCanvas();

  const cap = document.createElement('canvas');
  cap.width  = video.videoWidth;
  cap.height = video.videoHeight;
  cap.getContext('2d').drawImage(video, 0, 0);
  const b64 = cap.toDataURL('image/jpeg', 0.8);

  try {
    const res = await fetch('/api/detect/frame', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ frame: b64 })
    });
    const data = await res.json();
    if (data.error) { detecting = false; return; }
    renderDetections(data.detections);
    drawAnnotated(data.annotated_frame);
  } catch(e) { /* network blip */ }
  detecting = false;
}

function drawAnnotated(b64Url) {
  const img = new Image();
  img.onload = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
  };
  img.src = b64Url;
}

function renderDetections(dets) {
  detCount.textContent = dets.length;
  if (!dets.length) {
    detList.innerHTML = '<p class="empty-msg">Nenhum resíduo detectado<br>neste quadro.</p>';
    return;
  }
  detList.innerHTML = '';
  dets.forEach(d => detList.appendChild(buildDetItem(d)));
}

// ── Snapshot ──
btnSnap.addEventListener('click', async () => {
  if (!running || video.readyState < 2) return;
  syncCanvas();
  const cap = document.createElement('canvas');
  cap.width  = video.videoWidth;
  cap.height = video.videoHeight;
  cap.getContext('2d').drawImage(video, 0, 0);
  const b64 = cap.toDataURL('image/jpeg', 0.9);

  const res  = await fetch('/api/detect/frame', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ frame: b64 })
  });
  const data = await res.json();
  if (data.annotated_frame) {
    snapshotImg.src = data.annotated_frame;
    snapDL.href = data.annotated_frame;
    snapshotArea.style.display = 'flex';
    snapshotArea.style.flexDirection = 'column';
  }
});
