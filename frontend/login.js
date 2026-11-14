const demos = {
  driver: { username: 'driver1@smartroute.local', password: 'Driver@2026' },
  admin: { username: 'admin@smartroute.local', password: 'Admin@2026' },
  parent: { username: 'parent1@smartroute.local', password: 'Parent@2026' }
};
const form = document.getElementById('login-form');
const driverField = document.getElementById('driver-account-field');
const driverSelect = document.getElementById('driver-account');
const password = document.getElementById('password');
const passwordToggle = document.getElementById('toggle-password');

function selectedRole() {
  return new FormData(form).get('role');
}

function syncRoleFields(role) {
  driverField.hidden = role !== 'driver';
  if (role === 'driver' && driverSelect.value) {
    form.username.value = driverSelect.value;
    form.password.value = demos.driver.password;
  } else if (role !== 'driver') {
    form.username.value = demos[role].username;
    form.password.value = demos[role].password;
  }
}

function selectDemo(role) {
  document.querySelector(`input[name="role"][value="${role}"]`).checked = true;
  syncRoleFields(role);
}

async function loadDriverAccounts() {
  try {
    const drivers = await Portal.api('/api/v1/auth/demo-drivers');
    driverSelect.innerHTML = drivers.map(driver => `<option value="${Portal.escape(driver.username)}">${Portal.escape(driver.display_name)} · ${Portal.escape(driver.driver_id)}</option>`).join('');
    if (!drivers.length) throw new Error('No driver accounts are available');
    const requestedDriver = new URLSearchParams(location.search).get('driver');
    if (requestedDriver && drivers.some(driver => driver.username === requestedDriver)) driverSelect.value = requestedDriver;
    demos.driver.username = driverSelect.value;
    if (selectedRole() === 'driver') syncRoleFields('driver');
  } catch (error) {
    driverSelect.innerHTML = '<option value="">No drivers available</option>';
    Portal.setMessage(error.message, 'error');
  }
}

document.querySelectorAll('[data-demo]').forEach(button => button.addEventListener('click', () => selectDemo(button.dataset.demo)));
document.querySelectorAll('input[name="role"]').forEach(input => input.addEventListener('change', () => syncRoleFields(input.value)));
driverSelect.addEventListener('change', () => {
  form.username.value = driverSelect.value;
  form.password.value = demos.driver.password;
});
passwordToggle.addEventListener('click', () => {
  const showing = password.type === 'text';
  password.type = showing ? 'password' : 'text';
  passwordToggle.textContent = showing ? 'Show' : 'Hide';
  passwordToggle.setAttribute('aria-pressed', String(!showing));
});

const requestedRole = new URLSearchParams(location.search).get('role');
selectDemo(demos[requestedRole] ? requestedRole : 'driver');
loadDriverAccounts();
if (new URLSearchParams(location.search).has('expired')) Portal.setMessage('Your session expired. Please sign in again.', 'error');

form.addEventListener('submit', async event => {
  event.preventDefault();
  const button = form.querySelector('button[type="submit"]');
  const portalTab = window.open('about:blank', '_blank');
  if (!portalTab) {
    Portal.setMessage('Your browser blocked the new portal tab. Allow pop-ups for this local application and try again.', 'error');
    return;
  }
  portalTab.document.title = 'Opening SmartRoute portal…';
  portalTab.document.body.innerHTML = '<p style="font:16px system-ui;padding:32px;color:#173d34">Signing in and opening your portal…</p>';
  button.disabled = true;
  Portal.setMessage('Signing in…');
  try {
    const role = selectedRole();
    const result = await Portal.api('/api/v1/auth/login', { method: 'POST', body: JSON.stringify({ role, username: form.username.value.trim(), password: form.password.value }) });
    Portal.saveSession(result, portalTab);
    portalTab.location.replace(`/portal/${result.user.role}`);
    Portal.setMessage(`${Portal.label(result.user.role)} portal opened in a new tab. This login page will stay available.`, 'success');
  } catch (error) {
    portalTab.close();
    Portal.setMessage(error.message, 'error');
  } finally { button.disabled = false; }
});
