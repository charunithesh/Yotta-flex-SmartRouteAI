const byId = (id) => document.getElementById(id);
const number = new Intl.NumberFormat('en-IN');

function pct(value) {
  return `${Number(value || 0).toFixed(1).replace('.0', '')}%`;
}

function safe(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  })[character]);
}

function renderHealth(summary) {
  const coverage = summary.active_students
    ? summary.active_assignments / summary.active_students * 100
    : 0;
  const cards = [
    { icon: '✓', label: 'Students allocated', value: `${number.format(summary.active_assignments)} / ${number.format(summary.active_students)}`, detail: `${pct(coverage)} coverage`, tone: coverage >= 95 ? 'good' : 'warn' },
    { icon: '↗', label: 'Boarded rate', value: pct(summary.boarded_rate), detail: `${number.format(summary.attendance_events)} attendance records`, tone: summary.boarded_rate >= 90 ? 'good' : 'warn' },
    { icon: '!', label: 'Needs allocation', value: number.format(summary.unallocated_students), detail: summary.unallocated_students ? 'Students require review' : 'Every active student is covered', tone: summary.unallocated_students ? 'warn' : 'good' },
    { icon: '▦', label: 'Attendance records', value: number.format(summary.attendance_events), detail: 'Used in these insights', tone: 'neutral' }
  ];
  byId('health-cards').innerHTML = cards.map((card) => `
    <article class="health-card ${card.tone}">
      <span class="metric-icon" aria-hidden="true">${card.icon}</span>
      <span class="metric-label">${card.label}</span>
      <strong>${card.value}</strong>
      <small>${card.detail}</small>
    </article>`).join('');

  const panel = byId('attention-panel');
  panel.hidden = false;
  panel.className = `attention-panel ${summary.unallocated_students ? 'needs-action' : 'all-clear'}`;
  panel.innerHTML = summary.unallocated_students
    ? `<span aria-hidden="true">!</span><div><strong>${number.format(summary.unallocated_students)} students need attention</strong><p>Open the operations dashboard to review students without an active route assignment.</p></div><a href="/#unallocated">Review students →</a>`
    : `<span aria-hidden="true">✓</span><div><strong>No allocation gaps found</strong><p>All active students currently have a route assignment.</p></div>`;
}

function renderAttendance(attendance, trend, boardedRate) {
  const boarded = attendance.boarded || 0;
  const absent = attendance.absent || 0;
  const missed = attendance.missed_pickup || 0;
  const total = Math.max(1, boarded + absent + missed);
  const boardedDeg = boarded / total * 360;
  const absentDeg = (boarded + absent) / total * 360;
  byId('attendance-donut').style.background = `conic-gradient(var(--forest) 0deg ${boardedDeg}deg,var(--ochre) ${boardedDeg}deg ${absentDeg}deg,var(--terra) ${absentDeg}deg 360deg)`;
  byId('boarded-rate').textContent = pct(boardedRate);
  byId('attendance-legend').innerHTML = [
    ['boarded', 'Boarded', boarded, 'Students successfully picked up'],
    ['absent', 'Absent', absent, 'Students marked absent'],
    ['missed', 'Missed pickup', missed, 'Pickups requiring follow-up']
  ].map(([tone, label, value, detail]) => `<div><i class="${tone}"></i><span><strong>${safe(label)}</strong><small>${safe(detail)}</small></span><b>${number.format(value)}</b></div>`).join('');

  if (!trend.length) {
    byId('trend-chart').innerHTML = '<p class="empty-chart">No attendance history is available yet.</p>';
    return;
  }
  const max = Math.max(1, ...trend.map((day) => Object.values(day.statuses).reduce((sum, value) => sum + value, 0)));
  byId('trend-chart').innerHTML = `<div class="trend-bars">${trend.map((day) => {
    const date = new Date(`${day.date}T00:00:00`);
    const label = date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
    const values = day.statuses;
    const height = (value) => `${Math.max(value ? 4 : 0, value / max * 100)}%`;
    return `<div class="trend-day" title="${safe(label)}: ${values.boarded || 0} boarded, ${values.absent || 0} absent, ${values.missed_pickup || 0} missed">
      <div class="trend-stack"><i class="boarded" style="height:${height(values.boarded || 0)}"></i><i class="absent" style="height:${height(values.absent || 0)}"></i><i class="missed" style="height:${height(values.missed_pickup || 0)}"></i></div>
      <span>${safe(label)}</span>
    </div>`;
  }).join('')}</div>`;
}

function renderZones(zones) {
  byId('zone-chart').innerHTML = zones.length ? zones.map((zone) => {
    const coverage = zone.students ? zone.allocated / zone.students * 100 : 0;
    return `<article class="insight-row">
      <div class="row-label"><span><strong>${safe(zone.zone)}</strong><small>${number.format(zone.allocated)} of ${number.format(zone.students)} allocated</small></span><b>${pct(coverage)}</b></div>
      <div class="meter" role="progressbar" aria-label="${safe(zone.zone)} allocation coverage" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${coverage.toFixed(0)}"><i style="width:${Math.min(100, coverage)}%"></i></div>
      ${zone.unallocated ? `<small class="row-alert">${number.format(zone.unallocated)} still need a route</small>` : '<small class="row-ok">Fully allocated</small>'}
    </article>`;
  }).join('') : '<p class="empty-chart">No zone allocation data is available.</p>';
}

function capacityTone(utilization) {
  if (utilization >= 90) return ['high', 'High'];
  if (utilization >= 70) return ['watch', 'Watch'];
  return ['low', 'Low'];
}

function renderRoutes(routes) {
  byId('route-list').innerHTML = routes.length ? routes.map((route) => {
    const [tone, label] = capacityTone(route.utilization);
    const remaining = Math.max(0, route.capacity - route.allocated);
    return `<article class="route-row">
      <div class="route-name"><strong>${safe(route.route)}</strong><small>${number.format(route.allocated)} students · ${number.format(remaining)} seats available</small></div>
      <div class="route-meter"><div class="meter" role="progressbar" aria-label="${safe(route.route)} utilization" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${route.utilization}"><i class="${tone}" style="width:${Math.min(100, route.utilization)}%"></i></div><span>${pct(route.utilization)}</span></div>
      <span class="capacity-chip ${tone}">${label}</span>
    </article>`;
  }).join('') : '<p class="empty-chart">No active route capacity data is available.</p>';
}

async function loadAnalytics() {
  const status = byId('analytics-status');
  const button = byId('refresh-analytics');
  button.disabled = true;
  status.className = 'analytics-status loading';
  status.textContent = 'Loading current operational data…';
  try {
    const response = await fetch('/api/v1/analytics');
    if (!response.ok) throw new Error(`Request failed (${response.status})`);
    const data = await response.json();
    renderHealth(data.summary);
    renderAttendance(data.attendance, data.attendance_trend, data.summary.boarded_rate);
    renderZones(data.zone_allocation);
    renderRoutes(data.route_utilization);
    const updated = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
    status.className = 'analytics-status success';
    status.textContent = `Live database records · Updated at ${updated}`;
  } catch (error) {
    status.className = 'analytics-status error';
    status.textContent = `Unable to load analytics. ${error.message}`;
  } finally {
    button.disabled = false;
  }
}

byId('refresh-analytics').addEventListener('click', loadAnalytics);
loadAnalytics();
