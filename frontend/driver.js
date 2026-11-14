let driverData;
let tripActionInFlight = false;

function renderTripState(trip) {
  const status = document.getElementById('trip-status');
  const startButton = document.getElementById('start-trip');
  const completeButton = document.getElementById('complete-trip');
  const locationButton = document.getElementById('location-form').querySelector('button');
  const isRunning = trip.status === 'in_progress';

  status.textContent = isRunning ? 'Trip started' : Portal.label(trip.status);
  status.className = `status-chip ${trip.status}`;
  startButton.disabled = isRunning;
  startButton.textContent = isRunning ? 'Trip started' : trip.status === 'completed' ? 'Start another trip' : 'Start trip';
  completeButton.disabled = !isRunning;
  locationButton.disabled = !isRunning;
}

function renderStudentActions(student, tripIsRunning) {
  const canBoard = tripIsRunning && student.status === 'waiting';
  const canMarkAbsent = tripIsRunning && student.status === 'waiting';
  const canDropOff = tripIsRunning && student.status === 'boarded';
  return `<button data-student="${Portal.escape(student.id)}" data-event="boarded" ${canBoard ? '' : 'disabled'}>Boarded</button><button class="absent" data-student="${Portal.escape(student.id)}" data-event="absent" ${canMarkAbsent ? '' : 'disabled'}>Absent</button><button class="drop" data-student="${Portal.escape(student.id)}" data-event="dropped_off" ${canDropOff ? '' : 'disabled'}>Dropped off</button>`;
}

async function loadDriver() {
  try {
    driverData = await Portal.api('/api/v1/driver/dashboard');
    const { trip, route, bus, location, students, stops } = driverData;
    document.getElementById('trip-date').textContent = `${trip.service_date} · ${route.id}${trip.started_at && trip.status === 'in_progress' ? ` · Started ${Portal.time(trip.started_at)}` : ''}`;
    renderTripState(trip);
    document.getElementById('trip-overview').innerHTML = `<div><span>Route</span><strong>${Portal.escape(route.id)}</strong></div><div><span>Bus</span><strong>${Portal.escape(bus.id)}</strong></div><div><span>Students</span><strong>${students.length}</strong></div><div><span>Stops</span><strong>${stops.length}</strong></div>`;
    if (location) {
      document.getElementById('latitude').value = location.latitude;
      document.getElementById('longitude').value = location.longitude;
      document.getElementById('location-time').textContent = Portal.time(location.recorded_at);
    } else {
      document.getElementById('latitude').value = '';
      document.getElementById('longitude').value = '';
      document.getElementById('location-time').textContent = 'Not reported';
    }
    document.getElementById('stop-list').innerHTML = stops.map(stop => `<div class="stop-row"><span class="stop-number">${stop.sequence}</span><span><strong>${Portal.escape(stop.name)}</strong><small>${Portal.escape(stop.id)}</small></span><small>${Portal.escape(stop.pickup_window)}</small></div>`).join('');
    const firstStop = stops[0], lastStop = stops[stops.length - 1];
    document.getElementById('route-endpoints').innerHTML = stops.length ? `<div><span>Start point</span><strong>${Portal.escape(firstStop.name)}</strong><small>${Portal.escape(firstStop.pickup_window)}</small></div><b aria-hidden="true">→</b><div><span>End point</span><strong>${Portal.escape(lastStop.name)}</strong><small>${Portal.escape(lastStop.pickup_window)}</small></div>` : '<p class="empty-state">No stops are configured for this route.</p>';
    document.getElementById('route-map').innerHTML = stops.map((stop, index) => `<div class="route-map-stop ${index === 0 ? 'start' : ''} ${index === stops.length - 1 ? 'end' : ''}"><i>${stop.sequence}</i><span><strong>${Portal.escape(stop.name)}</strong><small>${index === 0 ? 'Trip starts here' : index === stops.length - 1 ? 'Trip ends here' : 'Route stop'}</small></span></div>`).join('');
    document.getElementById('student-list').innerHTML = students.map(student => `<tr><td><strong>${Portal.escape(student.name)}</strong><small>${Portal.escape(student.id)}</small></td><td>${Portal.escape(student.stop)}</td><td><span class="status-chip ${student.status}">${Portal.label(student.status)}</span></td><td><div class="student-actions">${renderStudentActions(student, trip.status === 'in_progress')}</div></td></tr>`).join('') || '<tr><td colspan="4" class="empty-state">No students assigned.</td></tr>';
  } catch (error) { Portal.setMessage(error.message, 'error'); }
}
async function tripAction(action) {
  if (tripActionInFlight) return;
  tripActionInFlight = true;

  const button = document.getElementById(action === 'start' ? 'start-trip' : 'complete-trip');
  const status = document.getElementById('trip-status');
  const previousTrip = driverData?.trip ? { ...driverData.trip } : null;
  const progressLabel = action === 'start' ? 'Starting…' : 'Completing…';

  button.disabled = true;
  button.textContent = progressLabel;
  button.classList.add('is-loading');
  button.setAttribute('aria-busy', 'true');
  status.textContent = progressLabel;
  status.className = 'status-chip pending';
  Portal.setMessage(action === 'start' ? 'Starting trip…' : 'Completing trip…', 'info');

  try {
    const result = await Portal.api('/api/v1/driver/trip', { method: 'POST', body: JSON.stringify({ action }) });
    if (driverData?.trip) driverData.trip.status = result.status;
    renderTripState(driverData?.trip || { status: result.status });
    await loadDriver();
    Portal.setMessage(action === 'start' ? 'Trip started successfully. Location and student updates are now enabled.' : 'Trip completed successfully.', 'success');
  } catch (error) {
    if (previousTrip) renderTripState(previousTrip);
    Portal.setMessage(error.message, 'error');
  } finally {
    tripActionInFlight = false;
    button.classList.remove('is-loading');
    button.removeAttribute('aria-busy');
  }
}
document.getElementById('start-trip').addEventListener('click', () => tripAction('start'));
document.getElementById('complete-trip').addEventListener('click', () => tripAction('complete'));
document.getElementById('location-form').addEventListener('submit', async event => { event.preventDefault(); try { const latitude = Number(event.currentTarget.latitude.value), longitude = Number(event.currentTarget.longitude.value); await Portal.api('/api/v1/driver/location', { method: 'POST', body: JSON.stringify({ latitude, longitude }) }); Portal.setMessage('Bus location shared with the admin and parent portals.', 'success'); await loadDriver(); } catch (error) { Portal.setMessage(error.message, 'error'); } });
document.getElementById('use-gps').addEventListener('click', () => { if (!navigator.geolocation) return Portal.setMessage('This device does not support location services.', 'error'); navigator.geolocation.getCurrentPosition(position => { document.getElementById('latitude').value = position.coords.latitude; document.getElementById('longitude').value = position.coords.longitude; Portal.setMessage('Device location captured. Select “Share location” to publish it.', 'info'); }, error => Portal.setMessage(`Location unavailable: ${error.message}`, 'error'), { enableHighAccuracy: true, timeout: 10000 }); });
document.getElementById('student-list').addEventListener('click', async event => { const button = event.target.closest('button[data-event]'); if (!button) return; button.disabled = true; try { await Portal.api('/api/v1/driver/student-event', { method: 'POST', body: JSON.stringify({ student_id: button.dataset.student, event_type: button.dataset.event }) }); Portal.setMessage(`Student marked ${Portal.label(button.dataset.event).toLowerCase()}. Parent and admin views have been updated.`, 'success'); await loadDriver(); } catch (error) { Portal.setMessage(error.message, 'error'); button.disabled = false; } });
(async () => { if (await Portal.requireRole('driver')) await loadDriver(); })();
