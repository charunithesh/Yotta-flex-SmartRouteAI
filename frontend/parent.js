function parentStatus(status) {
  return ({ waiting: ['Waiting for pickup', 'The trip has not reached your child yet'], trip_in_progress: ['Bus is on the route', 'Waiting for your child’s pickup update'], trip_completed: ['Trip completed', 'The driver has completed the current route'], boarded: ['Your child is on the bus', 'Boarding confirmed by the driver'], absent: ['Marked absent', 'The driver recorded your child as absent'], dropped_off: ['Dropped off safely', 'The driver confirmed the drop-off'], unassigned: ['No active route', 'Please contact the school transport office'] })[status] || [Portal.label(status), 'Latest status from the driver'];
}
async function loadParent() {
  try {
    const data = await Portal.api('/api/v1/parent/dashboard');
    document.getElementById('student-name').textContent = data.student.name;
    const [headline, detail] = parentStatus(data.status);
    document.getElementById('child-status').textContent = headline;
    document.getElementById('status-time').textContent = data.events?.length ? `${detail} · ${Portal.time(data.events[0].created_at)}` : detail;
    if (!data.assignment) {
      document.getElementById('student-route').textContent = 'No current route assignment.';
      document.getElementById('journey-details').innerHTML = '<p class="empty-state">Contact the transport office for an assignment.</p>';
      return;
    }
    document.getElementById('student-route').textContent = `${data.assignment.route} · ${data.assignment.stop}`;
    document.getElementById('journey-details').innerHTML = `<div class="detail"><span>Route</span><strong>${Portal.escape(data.assignment.route)}</strong></div><div class="detail"><span>Bus</span><strong>${Portal.escape(data.assignment.bus)}</strong></div><div class="detail"><span>Driver</span><strong>${Portal.escape(data.assignment.driver)}</strong></div><div class="detail"><span>Pickup / drop stop</span><strong>${Portal.escape(data.assignment.stop)}</strong></div>`;
    const location = document.getElementById('parent-location');
    if (data.location) {
      location.innerHTML = `<div><strong>Bus location received</strong><span>${data.location.latitude.toFixed(5)}, ${data.location.longitude.toFixed(5)}</span><span>Accuracy: ${data.location.accuracy_meters ? `${Math.round(data.location.accuracy_meters)} m` : 'not supplied'}</span></div>`;
      document.getElementById('parent-location-time').textContent = Portal.time(data.location.recorded_at);
    } else {
      location.innerHTML = '<div><strong>No live location yet</strong><span>The location appears after the driver starts the trip and shares GPS.</span></div>';
      document.getElementById('parent-location-time').textContent = 'Not reported';
    }
    document.getElementById('parent-events').innerHTML = data.events.map(event => `<article class="event-row ${event.event_type}"><i class="event-dot"></i><div><strong>${Portal.label(event.event_type)}</strong><small>${event.stop ? Portal.escape(event.stop) : Portal.escape(event.route_id)}${event.note ? ` · ${Portal.escape(event.note)}` : ''}</small></div><time>${Portal.time(event.created_at)}</time></article>`).join('') || '<p class="empty-state">No journey events have been reported yet.</p>';
    Portal.setMessage('', 'info');
  } catch (error) { Portal.setMessage(error.message, 'error'); }
}
(async () => { if (await Portal.requireRole('parent')) { await loadParent(); setInterval(loadParent, 10000); } })();
