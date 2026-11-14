async function loadAdmin() {
  try {
    const data = await Portal.api('/api/v1/admin/operations');
    const summary = data.summary;
    document.getElementById('admin-kpis').innerHTML = [
      ['Active routes', summary.active_routes, 'Routes currently in service', ''],
      ['Trips in progress', summary.active_trips, 'Drivers who started today', summary.active_trips ? '' : 'warn'],
      ['Students on buses', summary.students_on_buses, 'Boarded and not dropped off', ''],
      ['Reporting location', `${summary.routes_reporting_location}/${summary.active_routes}`, 'Routes with a location update', summary.routes_reporting_location < summary.active_routes ? 'warn' : '']
    ].map(([label, value, detail, tone]) => `<article class="kpi ${tone}"><span>${label}</span><strong>${value}</strong><small>${detail}</small></article>`).join('');
    document.getElementById('route-grid').innerHTML = data.routes.map(route => `<article class="route-card"><div class="route-card-head"><div><h3>${Portal.escape(route.id)}</h3><p>${Portal.escape(route.driver)} · ${Portal.escape(route.bus)}</p></div><span class="status-chip ${route.trip_status}">${Portal.label(route.trip_status)}</span></div><div class="route-stats"><div><strong>${route.assigned_students}</strong><span>Assigned</span></div><div><strong>${route.students_on_bus}</strong><span>On bus</span></div><div><strong>${route.capacity}</strong><span>Seats</span></div></div><div class="location-line">${route.location ? `Last location: ${route.location.latitude.toFixed(5)}, ${route.location.longitude.toFixed(5)} · ${Portal.time(route.location.recorded_at)}` : 'No location reported yet'}</div></article>`).join('') || '<p class="empty-state">No active routes.</p>';
    document.getElementById('event-list').innerHTML = data.recent_events.map(event => `<article class="event-row ${event.event_type}"><i class="event-dot"></i><div><strong>${Portal.escape(event.student)} · ${Portal.label(event.event_type)}</strong><small>${Portal.escape(event.route_id)} · ${Portal.escape(event.driver)}${event.stop ? ` · ${Portal.escape(event.stop)}` : ''}</small></div><time>${Portal.time(event.created_at)}</time></article>`).join('') || '<p class="empty-state">No driver events have been reported yet.</p>';
    document.getElementById('last-refresh').textContent = `Updated ${new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}`;
    Portal.setMessage('', 'info');
  } catch (error) { Portal.setMessage(error.message, 'error'); }
}
(async () => { if (await Portal.requireRole('admin')) { await loadAdmin(); setInterval(loadAdmin, 15000); } })();
document.getElementById('refresh').addEventListener('click', loadAdmin);
