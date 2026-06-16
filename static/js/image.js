const dropzone   = document.getElementById('dropzone');
const fileInput  = document.getElementById('fileInput');
const previewImg = document.getElementById('previewImg');
const dzIdle     = document.getElementById('dzIdle');
const btnDetect  = document.getElementById('btnDetect');
const btnClear   = document.getElementById('btnClear');
const resultPanel    = document.getElementById('resultPanel');
const resultImg      = document.getElementById('resultImg');
const resultDownload = document.getElementById('resultDownload');
const totalCount     = document.getElementById('totalCount');
const detSummary     = document.getElementById('detSummary');
const spinnerOverlay = document.getElementById('spinnerOverlay');

let selectedFile = null;

// ── Drag & drop ──
dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('dragging'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragging'));
dropzone.addEventListener('drop', e => {
  e.preventDefault();
  dropzone.classList.remove('dragging');
  const f = e.dataTransfer.files[0];
  if (f && f.type.startsWith('image/')) setFile(f);
});

dropzone.addEventListener('click', e => {
  if (e.target.classList.contains('dz-link')) fileInput.click();
});

fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) setFile(fileInput.files[0]);
});

function setFile(f) {
  selectedFile = f;
  const url = URL.createObjectURL(f);
  previewImg.src = url;
  previewImg.style.display = 'block';
  dzIdle.style.display = 'none';
  btnDetect.disabled = false;
  btnClear.disabled  = false;
  resultPanel.style.display = 'none';
}

btnClear.addEventListener('click', () => {
  selectedFile = null;
  previewImg.src = '';
  previewImg.style.display = 'none';
  dzIdle.style.display = 'flex';
  fileInput.value = '';
  btnDetect.disabled = true;
  btnClear.disabled  = true;
  resultPanel.style.display = 'none';
});

// ── Detect ──
btnDetect.addEventListener('click', async () => {
  if (!selectedFile) return;
  spinnerOverlay.style.display = 'flex';

  const form = new FormData();
  form.append('image', selectedFile);

  try {
    const res  = await fetch('/api/detect/image', { method:'POST', body: form });
    const data = await res.json();
    spinnerOverlay.style.display = 'none';

    if (data.error) { alert('Erro: ' + data.error); return; }

    resultImg.src      = data.result_url;
    resultDownload.href = data.result_url;
    totalCount.textContent = data.count;
    detSummary.innerHTML   = buildSummary(data.summary);
    resultPanel.style.display = 'flex';
    resultPanel.scrollIntoView({ behavior:'smooth', block:'start' });
  } catch(e) {
    spinnerOverlay.style.display = 'none';
    alert('Erro ao conectar com o servidor.');
  }
});
