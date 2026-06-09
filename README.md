# Expedition 33 — Trip Planner 🎵

An interactive, mobile-first trip planner for **Sebastijan & Mia**'s June 2026 trip
through **Basel → Freiburg → Nancy → Strasbourg**, built around the
*Clair Obscur: Expedition 33 — "A Painted Symphony"* concert in Nancy.

It's a **Progressive Web App (PWA)**: open it on your phone, **Add to Home Screen**,
and it runs like a real app — fullscreen, offline, with all your bookings,
addresses, maps, tickets and notes in one place. No app store, no accounts.

<p align="center"><i>Plan · Bookings · Info — tap anything for the full details.</i></p>

---

## ✨ What it does

- **Plan** — a day-by-day timeline (9–16 June). Tap any item for a detail sheet with:
  - 📍 one-tap **Google Maps** links for every address (incl. the exact **bus stop**),
  - 🎫 a big **Open ticket — scan QR** button that opens the actual boarding-pass
    PDF (jumps to the right page on round-trip tickets) — cached offline for the gate,
  - booking numbers, PINs, seats, prices, routes,
  - 📞 tap-to-call the hotel, ⧉ tap-to-copy confirmation numbers,
  - 🔗 deep links to FlixBus tracking / rebooking and Booking.com,
  - 📝 free-text **notes** on every item.
- **Bookings** — all stays, transport and tickets grouped for quick reference.
- **Info** — live **countdown** to the concert, traveller list, a running **budget**,
  an editable **packing/documents checklist**, and **Export / Import / Reset**.
- **Add & edit anything** — the `+` button adds new plans as you decide them;
  every item is editable so you can drop in info as bookings firm up.
- **Saves on your phone** — all edits persist locally (offline-first). Use
  **Export** to back up or move your plan to the other phone, **Import** to load it.

Everything was pre-loaded from your boarding passes, Booking.com confirmations,
the concert ticket, and the master spreadsheet — so it's ready to use on day one.

---

## 📲 Get it on your phone (recommended: GitHub Pages)

The repo is already set up to be hosted as-is (static files, no build step).

1. On GitHub, go to **Settings → Pages**.
2. Under **Build and deployment → Source**, choose **Deploy from a branch**.
3. Select branch **`claude/trip-planner-mobile-app-9k9tiq`** (or `main` after you merge),
   folder **`/ (root)`**, and **Save**.
4. After a minute GitHub gives you a URL like
   `https://spuzy24.github.io/expedition30/`.
5. Open that URL **on your phone**:
   - **iPhone (Safari):** Share → **Add to Home Screen**.
   - **Android (Chrome):** ⋮ menu → **Install app** / **Add to Home screen**.
6. Launch it from the home-screen icon. It now works **fullscreen and offline**.

> Both of you can install it from the same URL. Edits live on each phone separately —
> use **Export → Import** (Info tab) to sync a plan between phones.

### Run it locally instead

Because a PWA service worker needs a web server (not `file://`), serve the folder:

```bash
# from the project folder
python3 -m http.server 8000
# then open http://localhost:8000 on a device on the same network
```

---

## 🗺️ The trip at a glance

| Date | Plan | Sleep |
|------|------|-------|
| Tue 9 Jun | ✈️ Zagreb→Basel 15:50 · 🚌 Basel→Freiburg 22:40 | Freiburg |
| Wed 10 Jun | Free day in Freiburg | Freiburg |
| Thu 11 Jun | 🚌 Freiburg→Basel 22:20 | _(night bus)_ |
| Fri 12 Jun | 🚌 Basel→Nancy 00:25 · 🎵 **Concert 21:00** | Nancy |
| Sat 13 Jun | 🚌 Nancy→Strasbourg 18:00 | Strasbourg |
| Sun 14 Jun | Free day in Strasbourg | Strasbourg |
| Mon 15 Jun | 🚌 Strasbourg→Basel airport 15:05 | Basel _(to book)_ |
| Tue 16 Jun | ✈️ Basel→Zagreb 17:45 | — |

**Stays:** Hotel Libertas elements pure (Freiburg) · ibis budget Nancy Centre ·
Montagne Verte & Restaurant Louisiane (Strasbourg) · Basel _(placeholder — add when booked)_.

> Notes baked into the app: the **Basel SBB bus stop is relocated** (construction —
> walk to near the skate-park); the **Nancy→Basel 22:55 bus is a backup** (the real
> route goes via Strasbourg); the **flights and the Basel night** still need their
> details — tap **Edit** on those to fill them in.

---

## 🛠️ How it's built

Plain **HTML + CSS + vanilla JavaScript** — no framework, no build step, no dependencies.

| File | Purpose |
|------|---------|
| `index.html` | App shell (header, tabs, sheet, toast) |
| `styles.css` | Clair Obscur dark/gold theme, mobile-first |
| `data.js` | The seeded trip data (the original plan) |
| `app.js` | Store (localStorage), rendering, detail sheet, full add/edit CRUD |
| `manifest.webmanifest` | PWA metadata (installable, standalone) |
| `service-worker.js` | Offline caching of all assets |
| `icons/` | App icons (home-screen / maskable) |

**Editing the original plan in code:** change `SEED_ITEMS` in `data.js`. Then bump
the `CACHE` name in `service-worker.js` and `STORE_KEY` in `app.js` if you want
existing installs to pick up the new seed (otherwise their saved copy stays).
Day-to-day changes are easier done **in the app itself** (the `+` and Edit buttons).

---

## 💾 Your data & privacy

Everything stays **on your device** (browser `localStorage`) — nothing is uploaded
anywhere. Back it up any time with **Export** (Info tab). **Reset** restores the
original plan from `data.js`.

Made for the Expedition. ✨
