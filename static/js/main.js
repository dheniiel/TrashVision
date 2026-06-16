// Shared helpers

function buildDetItem(det) {
  const div = document.createElement('div');
  div.className = 'det-item';
  div.innerHTML = `
    <span class="det-label">${det.label.replace(/_/g,' ')}</span>
    <span class="det-conf">${(det.confidence*100).toFixed(1)}%</span>
  `;
  return div;
}

function buildSummary(summary) {
  return Object.entries(summary).map(([label, count]) => `
    <div class="sum-item">
      <span class="sum-label">${label.replace(/_/g,' ')}</span>
      <span class="sum-count">×${count}</span>
    </div>
  `).join('');
}
