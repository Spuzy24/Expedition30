# Expedition 33 — Trip Planner · Build Progress

> Planning memory for the build. Check items off as they're finished.

## 0. Source data — extracted & verified
- [x] Read all 9 PDFs (4 booking.com were image-only → rendered & OCR'd visually)
- [x] Read the Google Sheet master plan (day-by-day grid)
- [x] Reconcile conflicts (Nancy→Basel return bus is superseded by Nancy→Strasbourg; flag as backup)
- [x] Identify gaps (Basel apartment 15–16 Jun has no booking → placeholder)

### Trip facts
- Travelers: Sebastijan Koščak & Mia Mohač (2 adults)
- Dates: 9–16 June 2026
- Centerpiece: Clair Obscur: Expedition 33 — "A Painted Symphony", Zénith de Nancy, Fri 12 Jun 21:00

### Accommodations
- [x] Hotel Libertas elements pure — Freiburger Tor 1, 79249 Freiburg DE · +49 761 76995300 · 9–11 Jun · conf 6742.104.160 / PIN 7828 · €205.09
- [x] Hotel ibis budget Nancy Centre — 4 Allée du Chanoine Drioton, 54000 Nancy FR · +33 3 83 32 37 19 · 11–13 Jun · conf 5054.678.868 / PIN 6809 · €111.52
- [x] Hotel Strasbourg Montagne Verte & Restaurant Louisiane — 14 rue des Corroyeurs, 67200 Strasbourg FR · +33 3 88 29 06 06 · 13–15 Jun · conf 6761.153.084 / PIN 8402 · €140
- [x] Basel apartment 15–16 Jun — PLACEHOLDER (no booking yet)

### Transport
- [x] Flight Zagreb→Basel 9 Jun 15:50–17:20 (from sheet, no ticket)
- [x] Bus Basel→Freiburg 9 Jun 22:40→00:15 · N11 · seats 20C/20D · order 3360574326 · €19.95 (roundtrip)
- [x] Bus Freiburg→Basel 11 Jun 22:20→23:20 · N401 · seats 16A/17A · order 3360574326
- [x] Bus Basel→Nancy 12 Jun 00:25→03:35 · N836 · seats 20C/20E · order 3343047318 · €43.95 (roundtrip)
- [x] Bus Nancy→Basel 13 Jun 22:55→02:00 · N836 · seats 20B/20E · order 3343047318 · BACKUP/superseded
- [x] Bus Nancy→Strasbourg 13 Jun 18:00→20:00 · 834 · seats 7B/8B · order 3360547434 · €11.97
- [x] Bus Strasbourg→Basel EAP 15 Jun 15:05→17:25 · 108 · seats 20E/20C · order 3360584937 · €24.97
- [x] Flight Basel→Zagreb 16 Jun 17:45–19:30 (from sheet, no ticket)

### Events
- [x] Concert 12 Jun 21:00 · Carré Or, Bleu Gradin B109, Rang D, places 92 & 93 · 2×€72.20

## 1. Architecture
- [x] Decide stack: vanilla JS PWA, no build step, offline-first, localStorage (works on phone, installable)
- [x] File layout: index.html, styles.css, app.js, data.js, manifest.webmanifest, service-worker.js, icons/

## 2. Data layer
- [x] data.js — SEED trip dataset (trip meta + items[] with full schema)
- [x] Store: load/save/CRUD on localStorage, export/import JSON, reset-to-seed

## 3. UI
- [x] App shell + bottom tab bar (Plan / Bookings / Info)
- [x] Plan: day sections, date pills, chronological item rows, overnight footer
- [x] Detail bottom-sheet: all fields, action buttons (maps, booking, call, copy), inline notes
- [x] Bookings tab: grouped Stays / Transport / Tickets
- [x] Info tab: countdown, travelers, cost summary, checklist, export/import/reset
- [x] Add/Edit modal form (full CRUD for any item)
- [x] Floating + add button

## 4. Theme & polish
- [x] Clair Obscur dark/gold painterly theme, mobile-first, safe-area insets
- [x] Category colors + icons, smooth sheet/modal animations
- [x] Empty/edge states, confirm on delete

## 5. PWA
- [x] manifest.webmanifest (standalone, theme color, icons)
- [x] service-worker.js (offline cache of all assets)
- [x] Generate app icons (192/512/maskable/apple-touch)
- [x] Register SW + install prompt handling

## 5b. Tickets / QR (added)
- [x] Bundle the 5 boarding-pass / concert PDFs into /tickets
- [x] "Open ticket — scan QR" button on each bus + the concert (jumps to right page)
- [x] Editable ticket field in the add/edit form
- [x] Cache PDFs in the service worker for offline scanning at the gate

## 6. Docs & ship
- [x] README.md (what it is, how to install on phone, how to host, how to edit)
- [x] Commit & push to claude/trip-planner-mobile-app-9k9tiq

## 7. Round 2 — live-trip & QoL upgrade (June 2026)
- [x] "Happening now / Up next" hero card at the top of today, live countdown, refreshes every 30 s
- [x] Auto-scroll to today; past days & items dimmed with ✓; today highlighted in date strip + header
- [x] Per-day weather forecast (Open-Meteo, no key, cached 3 h in localStorage, offline-safe)
- [x] Tap the countdown chip → opens the concert detail sheet
- [x] Android back button / swipe-down / Escape all close the detail sheet (history API + touch drag)
- [x] Bookings: search box (titles, seats, confirmation numbers, addresses, notes…)
- [x] Bookings: gold quick-access ticket-PDF chips strip
- [x] Inline notes editing straight from the detail sheet
- [x] Stays: editable check-in / check-out (datetime) in the form; nights auto-calculated
- [x] Export via native share sheet (falls back to file download)
- [x] Checklist progress bar; "Explore city" link on free days
- [x] Service-worker update toast ("tap to refresh"); offline/online toasts; light haptics
- [x] Fixes: activity prices now counted in budget ("Other" bucket); invalid `--line-soft` CSS removed
- [x] Smoke-tested headless (Plan/Bookings/Info, sheet, search, notes, back button, weather mock)

## Open questions / follow-ups for the user
- Basel apartment (15–16 Jun): add name/address/booking when known (placeholder is in the app)
- Flights have no PDFs — times are from the sheet; add airline/booking refs when known
- Confirm whether the Nancy→Basel 13 Jun bus is truly unused (flagged as Backup)
