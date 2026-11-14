# SmartRoute AI — School Transport Operations

SmartRoute AI is a local FastAPI and SQLite application for school transport operations. It provides separate portals for drivers, administrators, and parents, backed by one shared database.

- Drivers start and complete trips, share bus locations, and record boarded, absent, and dropped-off events.
- Administrators see route, bus, trip, location, and student-event information across the fleet.
- Parents see the journey state of their linked child.
- The allocation dashboard and analytics page use the same backend data.

The repository contains synthetic demonstration data only.

## Verified environment

The instructions below were verified from a clean copy of this repository using:

- Windows PowerShell
- Python 3.11.9
- A newly created virtual environment
- The pinned packages in `backend/requirements.txt`
- The starter seed database

The clean verification generated 100 students with Indian names, 10 drivers, 10 buses, and 30 stops. Database validation passed and all 10 regression tests passed.

## Project structure

```text
backend/
  app/                  FastAPI application, APIs, authentication, and business rules
  tests/                HTTP regression tests
  requirements.txt      Pinned Python packages
database/
  transport.db          Local SQLite database
  schema.sql            Database schema
  generate_seed.py      Deterministic starter/full data generator
  validate.py           Database integrity checks
frontend/               HTML, CSS, and JavaScript served by FastAPI
README.md               This guide
```

There is no Node.js installation or frontend build command. FastAPI serves the files in `frontend/` directly.

## Prerequisite

Install Python 3.11 from [python.org](https://www.python.org/downloads/) and enable **Add Python to PATH** during installation.

Confirm that Python is available:

```powershell
python --version
```

The verified output was `Python 3.11.9`. If Windows does not recognize `python`, try `py -3.11` in place of `python` in the setup commands.

## First-time setup in VS Code or another IDE

### 1. Open the correct folder

In VS Code, select **File → Open Folder** and choose the folder that contains `backend`, `database`, `frontend`, and this `README.md` file.

Open **Terminal → New Terminal**. Every command in this guide must be run from that project root. For the current workspace, the command is:

```powershell
cd "C:\CandidateWorkspace\yotta flexx in office hackathon"
```

Confirm the current folder contains the application:

```powershell
Get-ChildItem
```

You should see `backend`, `database`, and `frontend` in the output.

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

This creates an isolated Python environment in `.venv`. It only needs to be created once.

### 3. Activate the virtual environment

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

The terminal prompt should begin with `(.venv)` after activation.

If PowerShell reports that script execution is disabled, allow scripts only for the current terminal and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Windows Command Prompt uses this activation command instead:

```bat
.venv\Scripts\activate.bat
```

macOS/Linux uses:

```bash
source .venv/bin/activate
```

### 4. Install the Python packages

Run this after the virtual environment is activated:

```powershell
python -m pip install -r backend\requirements.txt
```

The project installs FastAPI, Uvicorn, SQLAlchemy, Pydantic, and their required packages. Reinstall only when `backend/requirements.txt` changes or when creating a new virtual environment.

### 5. Choose whether to keep or rebuild the database

The repository already includes `database/transport.db`. To keep its current trips and portal state, do not run the seed generator; continue to step 6.

To create a clean deterministic starter database, first make a backup:

```powershell
Copy-Item database\transport.db database\transport.backup.db
```

Then regenerate and validate the database:

```powershell
python database\generate_seed.py --scale starter
python database\validate.py
```

Expected validation output:

```text
orphan_assignments: 0
over_capacity_routes: 0
duplicate_active_students: 0
validation: PASS
```

> **Important:** `generate_seed.py` deletes and recreates `database/transport.db`. It resets trips, locations, sessions, and portal activity. Do not run it when you need to preserve current application data.

The optional full dataset is generated with the following command. It creates 5,000 students and one million attendance events, so it takes substantially longer and uses more disk space:

```powershell
python database\generate_seed.py --scale full
```

### 6. Start the application

Use port `8010` for this project:

```powershell
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8010
```

Successful startup includes output similar to:

```text
Application startup complete.
Uvicorn running on http://127.0.0.1:8010
```

Keep this terminal open while using the application. The `--reload` option automatically reloads the server after Python source changes.

### 7. Check the backend

Open a second terminal and run:

```powershell
Invoke-RestMethod http://127.0.0.1:8010/api/v1/health
```

Expected result:

```text
status
------
ok
```

### 8. Open the application

Use these exact URLs:

| Page | URL |
|---|---|
| Role login | <http://127.0.0.1:8010/login> |
| Operations dashboard | <http://127.0.0.1:8010/> |
| Analytics | <http://127.0.0.1:8010/analytics> |
| Interactive API documentation | <http://127.0.0.1:8010/docs> |
| Health check | <http://127.0.0.1:8010/api/v1/health> |

Sign in from the role login page. A successful login keeps the login page available and opens the selected portal in a new browser tab.

## Demo accounts

All accounts and names are synthetic.

| Role | Email | Password |
|---|---|---|
| Admin | `admin@smartroute.local` | `Admin@2026` |
| Parent | `parent1@smartroute.local` | `Parent@2026` |
| Driver 1 | `driver1@smartroute.local` | `Driver@2026` |
| Drivers 2–10 | `driver2@smartroute.local` through `driver10@smartroute.local` | `Driver@2026` |

The login page includes a driver selector and a Show/Hide password control. Each driver can access only their assigned driver, bus, route, stops, and students.

## Driver trip workflow

1. Sign in as a driver.
2. Select **Start trip**.
3. The button immediately shows **Starting…**, then changes to **Trip started** and displays the recorded start time.
4. Share the bus location or use device GPS.
5. Mark students as boarded, absent, or dropped off.
6. Select **Complete trip** at the end of the route.
7. A completed trip can be followed by **Start another trip**.

Driver updates are available to the administrator and the linked parent through the backend APIs.

## Normal startup after the first setup

For later sessions, do not recreate the virtual environment, reinstall dependencies, or regenerate the database. Run only:

```powershell
cd "C:\CandidateWorkspace\yotta flexx in office hackathon"
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8010
```

Then open <http://127.0.0.1:8010/login>.

## Run the regression tests safely

The HTTP tests start/complete trips and create sessions. Run them against a copied database so your normal portal state is not changed.

### Terminal 1: create a test database and start a test server

Activate the virtual environment, then run:

```powershell
Copy-Item database\transport.db database\test_transport.db -Force
$env:DATABASE_URL = "sqlite:///./database/test_transport.db"
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8011
```

Keep Terminal 1 running.

### Terminal 2: run all tests

Open another terminal in the project root and run:

```powershell
.\.venv\Scripts\Activate.ps1
$env:TEST_BASE_URL = "http://127.0.0.1:8011"
python -m unittest discover -s backend\tests -v
```

A successful run ends with:

```text
Ran 10 tests

OK
```

The suite covers health checks, invalid login attempts, all 10 drivers, role authorization, driver/admin/parent event flow, trip completion and restart, logout, navigation links, frontend assets, and Start Trip feedback.

### Stop and clean up the test server

Return to Terminal 1 and press `Ctrl+C`. Then run:

```powershell
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
Remove-Item database\test_transport.db
```

Terminal 2 can clear its test URL with:

```powershell
Remove-Item Env:TEST_BASE_URL -ErrorAction SilentlyContinue
```

On macOS/Linux, use `cp` instead of `Copy-Item`, `export NAME=value` instead of `$env:NAME = value`, forward slashes in paths, and `rm` instead of `Remove-Item`.

## Stop the application

In the terminal running Uvicorn, press:

```text
Ctrl+C
```

Deactivate the virtual environment when finished:

```powershell
deactivate
```

## Troubleshooting

### `python` is not recognized

Install Python 3.11 and reopen the IDE. On Windows, try `py -3.11` instead of `python`.

### `No module named uvicorn` or `No module named fastapi`

The virtual environment is not active or dependencies were not installed. Activate `.venv` and run:

```powershell
python -m pip install -r backend\requirements.txt
```

### PowerShell blocks `Activate.ps1`

Run the following in the same terminal. It changes the policy only for that terminal process:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### `Address already in use`

Another server is using port `8010`. Stop the older server with `Ctrl+C`, or use another port:

```powershell
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8012
```

When changing the port, use the same port in every browser URL and health-check command.

### The browser shows an older or different dashboard

Check the terminal URL and port. This guide starts the current application on port `8010`. Refresh the browser with `Ctrl+F5` after frontend changes.

### Database or static-file errors

Stop the server and confirm the terminal is in the project root—the folder containing `backend`, `database`, and `frontend`. The default SQLite and frontend paths are relative to that folder.

### Login redirects back to the login page

Use the exact role matching the account. For example, a driver email must be used with the Driver role. If necessary, refresh the login page and sign in again to create a new 12-hour session.

## Data and security notes

- Passwords are stored as PBKDF2-SHA256 hashes.
- Raw session tokens are not stored in the database.
- Sessions expire after 12 hours.
- Role checks are enforced by the backend, not only by the browser UI.
- SQLite is the local development database.
- Assignment, attendance, notification, and exception history is retained unless the seed generator resets the database.

See `database/DATA_DICTIONARY.md` and `database/schema.sql` for the database entities and validation rules.
