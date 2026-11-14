const el = selector => document.querySelector(selector);
const colors = {boarded: '#2878d0', absent: '#f0a52b', missed_pickup: '#d95656'};
const labels = {boarded: 'Boarded', absent: 'Absent', missed_pickup: 'Missed pickup'};

async function api(url, options = {}) {
  return Portal.api(url, options);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[character]);
}

function show(title, content) {
  el('#title').textContent = title;
  el('#content').innerHTML = content;
  el('#modal').showModal();
}

async function load() {
  try {
    const [overview, assignments, unallocated] = await Promise.all([
      api('/api/v1/allocation/overview'),
      api('/api/v1/allocation/assignments'),
      api('/api/v1/allocation/unallocated')
    ]);
    el('#cards').innerHTML = Object.entries(overview).map(([key, value]) => `
      <article class="summary-card">
        <strong>${escapeHtml(value)}${key.includes('score') || key.includes('utilization') ? '%' : ''}</strong>
        <span>${escapeHtml(key.replaceAll('_', ' '))}</span>
      </article>`).join('');
    el('#assignments').innerHTML = assignments.map(item => `
      <tr>
        <td>${escapeHtml(item.student)}<small>${escapeHtml(item.student_id)}</small></td>
        <td>${escapeHtml(item.bus)}</td><td>${escapeHtml(item.route)}</td>
        <td>${escapeHtml(item.stop)}</td><td>${escapeHtml(item.score ?? '—')}</td>
        <td>${escapeHtml(item.status)}</td>
        <td><button class="table-button" onclick="details('${escapeHtml(item.student_id)}')">Details</button>
          <button class="table-button" onclick="history('${escapeHtml(item.student_id)}')">History</button></td>
      </tr>`).join('');
    el('#unallocated').innerHTML = unallocated.length ? unallocated.map(item => `
      <article><b>${escapeHtml(item.student)}</b>: ${item.reasons.map(escapeHtml).join('; ')}
        <br><small>${escapeHtml(item.action)}</small></article>`).join('')
      : '<p>Every eligible student has an active allocation.</p>';
  } catch (error) {
    el('#message').textContent = error.message;
  }
}

function renderPie(attendance) {
  const entries = Object.entries(labels).map(([key, label]) => ({
    key, label, value: attendance[key] || 0
  }));
  const total = entries.reduce((sum, item) => sum + item.value, 0);
  let start = 0;
  const segments = entries.map(item => {
    const end = start + (total ? item.value / total * 100 : 0);
    const segment = `${colors[item.key]} ${start}% ${end}%`;
    start = end;
    return segment;
  });
  el('#attendance-pie').style.background = total
    ? `conic-gradient(${segments.join(',')})`
    : 'conic-gradient(#e7edf5 0% 100%)';
  el('#attendance-pie').setAttribute('aria-label',
    `Attendance outcomes: ${entries.map(item => `${item.label} ${item.value}`).join(', ')}`);
  el('#attendance-legend').innerHTML = entries.map(item => `
    <div class="legend-item"><span class="legend-swatch" style="--swatch:${colors[item.key]}"></span>
      <span>${item.label}</span><b>${item.value.toLocaleString()}</b>
      <small>${total ? (item.value / total * 100).toFixed(1) : '0.0'}%</small></div>`).join('');
}

function renderTrend(days) {
  const container = el('#attendance-trend');
  if (!days.length) {
    container.innerHTML = '<p class="empty-chart">No attendance events recorded yet.</p>';
    el('#trend-legend').innerHTML = '';
    return;
  }
  const width = 900, height = 250, left = 52, right = 18, top = 18, bottom = 40;
  const plotWidth = width - left - right, plotHeight = height - top - bottom;
  const maxValue = Math.max(1, ...days.flatMap(day => Object.values(day.statuses)));
  const x = index => left + (days.length === 1 ? plotWidth / 2 : index * plotWidth / (days.length - 1));
  const y = value => top + plotHeight - value / maxValue * plotHeight;
  let svg = `<svg class="trend-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Daily attendance outcomes line chart">`;
  for (let tick = 0; tick <= 2; tick++) {
    const value = Math.round(maxValue * tick / 2);
    const tickY = y(value);
    svg += `<line x1="${left}" y1="${tickY}" x2="${width - right}" y2="${tickY}" class="grid-line"/>`;
    svg += `<text x="${left - 10}" y="${tickY + 4}" text-anchor="end" class="axis-label">${value}</text>`;
  }
  for (const [status, label] of Object.entries(labels)) {
    const points = days.map((day, index) => `${x(index)},${y(day.statuses[status] || 0)}`).join(' ');
    svg += `<polyline points="${points}" fill="none" stroke="${colors[status]}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>`;
    days.forEach((day, index) => {
      svg += `<circle cx="${x(index)}" cy="${y(day.statuses[status] || 0)}" r="3.5" fill="${colors[status]}"><title>${day.date} — ${label}: ${day.statuses[status] || 0}</title></circle>`;
    });
  }
  days.forEach((day, index) => {
    if (days.length <= 8 || index % 2 === 0 || index === days.length - 1) {
      svg += `<text x="${x(index)}" y="${height - 12}" text-anchor="middle" class="axis-label">${escapeHtml(day.date.slice(5))}</text>`;
    }
  });
  svg += '</svg>';
  container.innerHTML = svg;
  el('#trend-legend').innerHTML = Object.entries(labels).map(([key, label]) => `
    <span class="legend-key"><span class="legend-swatch" style="--swatch:${colors[key]}"></span>${label}</span>`).join('');
}

function renderZones(zones) {
  el('#zone-chart').innerHTML = zones.length ? zones.map(zone => {
    const total = zone.students || 0;
    const allocatedWidth = total ? zone.allocated / total * 100 : 0;
    const unallocatedWidth = total ? zone.unallocated / total * 100 : 0;
    return `<div class="bar-row">
      <div class="bar-label"><span>${escapeHtml(zone.zone)}</span><b>${zone.allocated}/${total}</b></div>
      <div class="stacked-track" role="img" aria-label="${escapeHtml(zone.zone)}: ${zone.allocated} allocated, ${zone.unallocated} unallocated">
        <span class="stacked-allocated" style="width:${allocatedWidth}%"></span>
        <span class="stacked-unallocated" style="width:${unallocatedWidth}%"></span>
      </div>
    </div>`;
  }).join('') : '<p class="empty-chart">No active student zones found.</p>';
}

function renderRoutes(routes) {
  el('#route-chart').innerHTML = routes.length ? routes.map(route => {
    const width = Math.min(100, Math.max(0, route.utilization));
    return `<div class="bar-row">
      <div class="bar-label"><span>${escapeHtml(route.route)}</span>
        <b>${route.allocated}/${route.capacity} · ${route.utilization}%</b></div>
      <div class="bar-track" role="img" aria-label="${escapeHtml(route.route)}: ${route.allocated} of ${route.capacity} seats used">
        <span class="bar-fill" style="width:${width}%"></span>
      </div>
    </div>`;
  }).join('') : '<p class="empty-chart">No active routes found.</p>';
}

async function loadAnalytics() {
  const message = el('#analytics-message');
  message.textContent = '';
  try {
    const data = await api('/api/v1/analytics');
    const cards = [
      ['Active students', data.summary.active_students],
      ['Active assignments', data.summary.active_assignments],
      ['Awaiting allocation', data.summary.unallocated_students],
      ['Boarded rate', `${data.summary.boarded_rate}%`],
      ['Attendance events', data.summary.attendance_events]
    ];
    el('#analytics-cards').innerHTML = cards.map(([label, value]) => `
      <article class="summary-card"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></article>`).join('');
    renderPie(data.attendance);
    renderTrend(data.attendance_trend);
    renderZones(data.zone_allocation);
    renderRoutes(data.route_utilization);
  } catch (error) {
    message.textContent = `Unable to load analytics: ${error.message}`;
  }
}

el('#run').onclick = async () => {
  try {
    const result = await api('/api/v1/allocation/run', {method: 'POST', body: '{}'});
    el('#message').textContent = `Allocated ${result.allocated.length}; ${result.unallocated.length} unresolved.`;
    await load();
    if (el('#analytics-modal').open) loadAnalytics();
  } catch (error) {
    el('#message').textContent = error.message;
  }
};

el('#refresh-analytics').onclick = loadAnalytics;
el('#analytics').onclick = () => {
  el('#analytics-modal').showModal();
  loadAnalytics();
};

async function details(id) {
  const assignment = (await api('/api/v1/allocation/assignments')).find(item => item.student_id === id);
  if (!assignment) return;
  show('Allocation details', `<p>${escapeHtml(assignment.explanation || 'No explanation recorded.')}</p>
    <p>${escapeHtml(assignment.bus)} / ${escapeHtml(assignment.route)} / ${escapeHtml(assignment.stop)}</p>`);
}

async function history(id) {
  const assignments = await api(`/api/v1/allocation/${encodeURIComponent(id)}/history`);
  show('Allocation history', assignments.map(item => `
    <p>${escapeHtml(item.status)}: ${escapeHtml(item.route)} / ${escapeHtml(item.stop)}</p>`).join(''));
}

window.details = details;
window.history = history;
(async () => { if (await Portal.requireRole('admin')) await load(); })();
