# Data dictionary and lifecycle

| Entity | Primary key | Relationships | Required validation |
|---|---|---|---|
| Student | `STU-nnnnnn` | N:1 AddressZone; 1:N GuardianContact/Assignment/AttendanceEvent | active status, approved zone before assignment |
| GuardianContact | `GDN-nnnnnn` | N:1 Student; 1:N Notification | synthetic phone, `valid=true` before send |
| AddressZone | `ZONE-nnn` | 1:N Student/Stop | approved flag gates assignment |
| Stop | `STOP-nnnnnn` | N:1 Zone; N:M Route via RouteStop | approved, must be served by route |
| Bus | `BUS-nnnnnn` | 1:N Route | positive capacity, accessibility capability |
| Driver | `DRV-nnnnnn` | 1:N Route | licensed/active |
| Route | `ROUTE-2026-nnnnnn` | N:1 Bus; N:M Stop; 1:N Assignment | active and capacity available |
| RouteStop | `(route_id,stop_id)` | bridge Route↔Stop | unique ordered sequence; pickup window |
| Assignment | `ASN-<student>-2026` | N:1 Student/Route/Stop | effective dates; active assignment checked |
| AttendanceEvent | surrogate integer | N:1 Student | immutable status event / school date |
| Notification | `NOT-2026-nnnnnn` | N:1 GuardianContact | only valid contacts may be sent |
| AppUser | `USR-<ROLE>-nnn` | optional 1:1 Driver or GuardianContact | role is admin, driver or parent; password stored as PBKDF2 hash |
| UserSession | token SHA-256 hash | N:1 AppUser | bearer token expires after 12 hours |
| Trip | `TRIP-<date>-<route>` | N:1 Route/Driver | one trip per route and service date |
| BusLocation | surrogate integer | N:1 Route/Driver | validated latitude and longitude, append-only history |
| StudentTripEvent | surrogate integer | N:1 Trip/Student/Route/Driver | immutable boarded, absent or dropped-off event |

Assignment state moves `active → ended`; changes produce `assignment_events`, never mutation of historical records. The generator holds five deliberate negative scenarios in `data_issues` and `ground_truth.json`. Capacity, route compatibility and approved-zone rules are enforced by the API, not by client code.

Driver updates follow `Driver portal → authenticated API → Trip/BusLocation/StudentTripEvent`. Admin users can read all routes and events. Parent users are restricted to the student linked through their guardian record.
