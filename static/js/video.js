const dropzone     = document.getElementById('dropzone');
const fileInput    = document.getElementById('fileInput');
const previewVideo = document.getElementById('previewVideo');
const dzIdle       = document.getElementById('dzIdle');
const btnProcess   = document.getElementById('btnProcess');
const btnClear     = document.getElementById('btnClear');
const progressPanel  = document.getElementById('progressPanel');
const progressBar    = document.getElementById('progressBar');
const progressPct    = document.getElementById('progressPct');
const resultPanel    = document.getElementById('resultPanel');
const resultVideo    = document.getElementById('resultVideo');
const resultDownload = document.getElementById('resultDownload');
const totalCount     = document.getElementById('totalCount');
const detSummary     = document.getElementById('detSummary');

let selectedFile = null;
let pollTimer    = null;

// ── Drag & drop ──
dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('dragging'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragging'));
dropzone.addEventListener('drop', e => {
  e.preventDefault();
  dropzone.classList.remove('dragging');
  const f = e.dataTransfer.files[0];
  if (f && f.type.startsWith('video/')) setFile(f);
});

dropzone.addEventListener('click', e => {
  if (e.target.classList.contains('dz-link')) fileInput.click();
});

fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) setFile(fileInput.files[0]);
});

function setFile(f) {
  selectedFile = f;
  previewVideo.src = URL.createObjectURL(f);
  previewVideo.style.display = 'block';
  dzIdle.style.display = 'none';
  btnProcess.disabled = false;
  btnClear.disabled   = false;
  progressPanel.style.display = 'none';
  resultPanel.style.display   = 'none';
}

btnClear.addEventListener('click', () => {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  selectedFile = null;
  previewVideo.src = '';
  previewVideo.style.display = 'none';
  dzIdle.style.display = 'flex';
  fileInput.value = '';
  btnProcess.disabled = true;
  btnClear.disabled   = false;
  progressPanel.style.display = 'none';
  resultPanel.style.display   = 'none';
});

// ── Process ──
btnProcess.addEventListener('click', async () => {
  if (!selectedFile) return;
  btnProcess.disabled = true;

  const form = new FormData();
  form.append('video', selectedFile);

  progressPanel.style.display = 'flex';
  progressBar.style.width = '0%';
  progressPct.textContent = '0%';
  resultPanel.style.display = 'none';
  progressPanel.scrollIntoView({ behavior:'smooth', block:'start' });

  try {
    const res  = await fetch('/api/detect/video', { method:'POST', body: form });
    const data = await res.json();
    if (data.error) { alert('Erro: ' + data.error); progressPanel.style.display='none'; return; }
    pollJob(data.job_id);
  } catch(e) {
    alert('Erro ao enviar vídeo.');
    progressPanel.style.display = 'none';
  }
});

function pollJob(jobId) {
  pollTimer = setInterval(async () => {
    try {
      const res  = await fetch(`/api/job/${jobId}`);
      const data = await res.json();

      progressBar.style.width = data.progress + '%';
      progressPct.textContent = data.progress + '%';

      if (data.status === 'done') {
        clearInterval(pollTimer);
        showResult(data);
      } else if (data.status === 'error') {
        clearInterval(pollTimer);
        progressPanel.style.display = 'none';
        alert('Erro ao processar vídeo: ' + data.error);
        btnProcess.disabled = false;
      }
    } catch(e) { /* retry next tick */ }
  }, 800);
}

function showResult(data) {
  progressPanel.style.display = 'none';
  resultVideo.src = data.result_url;
  resultDownload.href = data.result_url;
  totalCount.textContent = data.count;
  detSummary.innerHTML   = buildSummary(data.summary || {});
  resultPanel.style.display = 'flex';
  resultPanel.scrollIntoView({ behavior:'smooth', block:'start' });
  btnProcess.disabled = false;
}
