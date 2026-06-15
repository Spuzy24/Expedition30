/*
 * Expedition 33 — seed trip data.
 * Everything extracted from the boarding passes, Booking.com confirmations,
 * the concert ticket and the Google Sheet master plan.
 *
 * This is the ORIGINAL plan. The app copies it into localStorage on first run;
 * after that your edits live on the phone. "Reset" on the Info tab restores this.
 *
 * Item schema (all fields optional except id, type, day, title):
 *   id      unique string
 *   type    'flight' | 'bus' | 'stay' | 'event' | 'activity' | 'note'
 *   day     'YYYY-MM-DD'  (which day section it shows under)
 *   start   'HH:MM'       (used for ordering + display)
 *   end     'HH:MM'
 *   endDay  'YYYY-MM-DD'  (for things that finish on a later day)
 *   title   short name
 *   subtitle one-line summary
 *   from    { name, address, coords:[lat,lng] }   (transport origin)
 *   to      { name, address, coords:[lat,lng] }   (transport destination)
 *   place   { name, address, coords:[lat,lng] }   (single-location: stay/event)
 *   checkIn / checkOut  'YYYY-MM-DD HH:MM' display strings (stays)
 *   nights  number
 *   info    [{ label, value, copy?:true }]  key facts
 *   links   [{ label, url }]
 *   price   number (EUR) — counted in the cost summary
 *   priceNote string
 *   badges  [string]
 *   notes   free text (editable)
 */

const TRIP = {
  title: "Expedition 33",
  subtitle: "A Painted Symphony · France & beyond",
  travelers: ["Sebastijan Koščak", "Mia Mohač"],
  startDate: "2026-06-09",
  endDate: "2026-06-16",
  // The moment everything is built around — drives the countdown.
  countdownTo: "2026-06-12T21:00:00",
  countdownLabel: "Clair Obscur · Expedition 33 concert",
  currency: "EUR",
};

// Per-day headers shown on the Plan timeline.
const DAY_META = {
  "2026-06-09": { city: "Zagreb → Basel → Freiburg", note: "Travel day" },
  "2026-06-10": { city: "Freiburg im Breisgau", note: "Full day" },
  "2026-06-11": { city: "Freiburg → Basel", note: "Night bus south" },
  "2026-06-12": { city: "Basel → Nancy", note: "🎵 Concert night" },
  "2026-06-13": { city: "Nancy → Strasbourg", note: "Travel day" },
  "2026-06-14": { city: "Strasbourg", note: "Full day" },
  "2026-06-15": { city: "Strasbourg → Basel", note: "Travel day" },
  "2026-06-16": { city: "Basel → Zagreb", note: "Going home" },
};

const SEED_ITEMS = [
  /* ───────────────── Tue 9 June ───────────────── */
  {
    id: "fl-zag-bsl",
    type: "flight",
    day: "2026-06-09",
    start: "15:50",
    end: "17:20",
    title: "Zagreb → Basel",
    subtitle: "Flight · arrive EuroAirport (BSL/MLH)",
    from: { name: "Zagreb Airport (ZAG)", address: "Franjo Tuđman Airport, 10150 Zagreb, Croatia", coords: [45.7429, 16.0688] },
    to: { name: "EuroAirport Basel-Mulhouse-Freiburg (BSL)", address: "EuroAirport, 68300 Saint-Louis, France", coords: [47.5896, 7.5299] },
    info: [
      { label: "Departs", value: "Tue 9 Jun · 15:50" },
      { label: "Arrives", value: "Tue 9 Jun · 17:20" },
    ],
    notes: "No e-ticket PDF yet — times are from the master plan. Add the airline + booking reference here once you have them.",
  },
  {
    id: "bus-bsl-fre",
    type: "bus",
    day: "2026-06-09",
    start: "22:40",
    end: "00:15",
    endDay: "2026-06-10",
    title: "Basel → Freiburg",
    subtitle: "FlixBus N11 · dir. Duisburg",
    ticketPdf: "tickets/flix-basel-freiburg-roundtrip.pdf#page=1",
    from: {
      name: "Basel SBB (Meret-Oppenheim-Strasse)",
      address: "Meret-Oppenheim-Strasse 80, 4053 Basel, Switzerland",
      coords: [47.5455, 7.5905],
    },
    to: {
      name: "Freiburg (im Breisgau) Hauptbahnhof",
      address: "Bismarckallee 1A, 79098 Freiburg im Breisgau, Germany",
      coords: [47.9978, 7.8417],
    },
    info: [
      { label: "Route", value: "N11 · dir. Duisburg" },
      { label: "Seats", value: "20C · 20D" },
      { label: "Booking no.", value: "336 057 4326", copy: true },
      { label: "Price", value: "€19.95 (round trip incl. return)" },
    ],
    links: [
      { label: "Track this bus", url: "https://www.flixbus.com/track/order/3360574326" },
      { label: "Manage booking (rebooking)", url: "https://shop.flixbus.com/rebooking" },
    ],
    price: 19.95,
    priceNote: "Round trip — also covers the Freiburg → Basel return",
    badges: ["Round trip"],
    notes:
      "⚠️ Construction at Basel SBB: the bus stop is RELOCATED — still on Meret-Oppenheim-Strasse but near Solothurnerstrasse, next to the skate-park. Walk ~5 min east. Be there 15 min early.",
  },

  /* ───────────────── Wed 10 June ───────────────── */
  {
    id: "stay-freiburg",
    type: "stay",
    day: "2026-06-09",
    start: "15:00",
    title: "Hotel Libertas elements pure",
    subtitle: "Freiburg · 2 nights",
    place: {
      name: "Hotel Libertas elements pure",
      address: "Freiburger Tor 1, 79249 Freiburg (Merzhausen), Germany",
      coords: [47.97225, 7.828067],
    },
    checkIn: "2026-06-09 15:00",
    checkOut: "2026-06-11 12:00",
    endDay: "2026-06-11",
    nights: 2,
    info: [
      { label: "Check-in", value: "Tue 9 Jun · from 15:00" },
      { label: "Check-out", value: "Thu 11 Jun · until 12:00" },
      { label: "Confirmation", value: "6742.104.160", copy: true },
      { label: "PIN", value: "7828", copy: true },
      { label: "Phone", value: "+49 761 76995300", copy: true },
      { label: "Guests", value: "2 adults · 1 room" },
      { label: "Price", value: "€205.09 (incl. 7% tax)" },
    ],
    links: [{ label: "Booking.com", url: "https://www.booking.com" }],
    price: 205.09,
    notes:
      "Bus from Basel arrives Freiburg Hbf 00:15 — hotel is in Merzhausen, just south of Freiburg, so plan a taxi/tram for the late arrival. Note: postcode 79249 is Merzhausen.",
  },

  /* ───────────────── Thu 11 June ───────────────── */
  {
    id: "bus-fre-bsl",
    type: "bus",
    day: "2026-06-11",
    start: "22:20",
    end: "23:20",
    title: "Freiburg → Basel",
    subtitle: "FlixBus N401 · dir. Venezia Mestre",
    ticketPdf: "tickets/flix-basel-freiburg-roundtrip.pdf#page=2",
    from: {
      name: "Freiburg (im Breisgau) Hauptbahnhof",
      address: "Bismarckallee 1A, 79098 Freiburg im Breisgau, Germany",
      coords: [47.9978, 7.8417],
    },
    to: {
      name: "Basel SBB (Meret-Oppenheim-Strasse)",
      address: "Meret-Oppenheim-Strasse 80, 4053 Basel, Switzerland",
      coords: [47.5455, 7.5905],
    },
    info: [
      { label: "Route", value: "N401 · dir. Venezia Mestre" },
      { label: "Seats", value: "16A · 17A" },
      { label: "Booking no.", value: "336 057 4326", copy: true },
      { label: "Price", value: "Included in round trip" },
    ],
    links: [
      { label: "Track this bus", url: "https://www.flixbus.com/track/order/3360574326" },
      { label: "Manage booking (rebooking)", url: "https://shop.flixbus.com/rebooking" },
    ],
    badges: ["Round trip"],
    notes:
      "Departs from bus platform 3 at Freiburg Hbf. The airport line CDE3207 leaves from there too — no entry to the bus station by private car. Then a tight connection in Basel for the 00:25 Nancy bus.",
  },

  /* ───────────────── Fri 12 June ───────────────── */
  {
    id: "bus-bsl-ncy",
    type: "bus",
    day: "2026-06-12",
    start: "00:25",
    end: "03:35",
    title: "Basel → Nancy",
    subtitle: "FlixBus N836 · dir. Amsterdam Sloterdijk",
    ticketPdf: "tickets/flix-basel-nancy-roundtrip.pdf#page=1",
    from: {
      name: "Basel SBB (Meret-Oppenheim-Strasse)",
      address: "Meret-Oppenheim-Strasse, 4053 Basel, Switzerland",
      coords: [47.5455, 7.5905],
    },
    to: {
      name: "Nancy (Quai Sainte-Catherine)",
      address: "4710 Quai Sainte-Catherine, 54000 Nancy, France",
      coords: [48.6906, 6.1899],
    },
    info: [
      { label: "Route", value: "N836 · dir. Amsterdam Sloterdijk" },
      { label: "Seats", value: "20C · 20E" },
      { label: "Booking no.", value: "334 304 7318", copy: true },
      { label: "Price", value: "€43.95 (round trip)" },
    ],
    links: [
      { label: "Track this bus", url: "https://www.flixbus.com/track/order/3343047318" },
      { label: "Manage booking (rebooking)", url: "https://shop.flixbus.com/rebooking" },
    ],
    price: 43.95,
    priceNote: "Round trip — the unused return is the 13 Jun 22:55 Nancy → Basel",
    badges: ["Round trip", "Overnight"],
    notes: "Night bus — bring your ID/passport. Drop-off in Nancy is by the Sainte-Catherine roundabout.",
  },
  {
    id: "stay-nancy",
    type: "stay",
    day: "2026-06-11",
    start: "12:00",
    title: "ibis budget Nancy Centre",
    subtitle: "Nancy · 2 nights",
    place: {
      name: "Hotel ibis budget Nancy Centre",
      address: "4 Allée du Chanoine Drioton, 54000 Nancy, France",
      coords: [48.692667, 6.195233],
    },
    checkIn: "2026-06-11 12:00",
    checkOut: "2026-06-13 12:00",
    endDay: "2026-06-13",
    nights: 2,
    info: [
      { label: "Check-in", value: "Thu 11 Jun · from 12:00" },
      { label: "Check-out", value: "Sat 13 Jun · until 12:00" },
      { label: "Confirmation", value: "5054.678.868", copy: true },
      { label: "PIN", value: "6809", copy: true },
      { label: "Phone", value: "+33 3 83 32 37 19", copy: true },
      { label: "Guests", value: "2 adults · 1 room" },
      { label: "Price", value: "€111.52 (incl. 10% tax)" },
    ],
    links: [{ label: "Booking.com", url: "https://www.booking.com" }],
    price: 111.52,
    notes:
      "Room is booked from the night of Thu 11 Jun, but the Basel night bus only gets you in around 03:35 on Fri 12 — message the hotel about the very late/early arrival so the room is ready.",
  },
  {
    id: "concert",
    type: "event",
    day: "2026-06-12",
    start: "21:00",
    title: "Clair Obscur: Expedition 33",
    subtitle: '"A Painted Symphony" — live concert',
    ticketPdf: "tickets/clair-obscur-concert.pdf",
    place: {
      name: "Zénith de Nancy — Amphithéâtre Plein Air",
      address: "Rue du Zénith, 54320 Maxéville (Zénith de Nancy), France",
      coords: [48.7156, 6.1611],
    },
    info: [
      { label: "Doors / Start", value: "Fri 12 Jun · 21:00" },
      { label: "Category", value: "Carré Or" },
      { label: "Block", value: "Bleu Gradin B109 · Rang D" },
      { label: "Seats", value: "Place 92 · Place 93" },
      { label: "Ticket holder", value: "Mia Mohač" },
      { label: "Price", value: "2 × €72.20 = €144.40" },
    ],
    price: 144.40,
    badges: ["⭐ Main event"],
    notes:
      "Open-air amphitheatre at the Zénith de Nancy. Bring the tickets (barcodes 0201576020331068 / 0201574720331067) and ID. Check the weather — it's outdoors.",
  },

  /* ───────────────── Sat 13 June ───────────────── */
  {
    id: "bus-ncy-str",
    type: "bus",
    day: "2026-06-13",
    start: "18:00",
    end: "20:00",
    title: "Nancy → Strasbourg",
    subtitle: "FlixBus 834 · dir. Strasbourg",
    ticketPdf: "tickets/flix-nancy-strasbourg.pdf",
    from: {
      name: "Nancy (Quai Sainte-Catherine)",
      address: "4710 Quai Sainte-Catherine, 54000 Nancy, France",
      coords: [48.6906, 6.1899],
    },
    to: {
      name: "Strasbourg (Place de l'Étoile)",
      address: "Place de l'Étoile, 67076 Strasbourg, France",
      coords: [48.5736, 7.7521],
    },
    info: [
      { label: "Route", value: "834 · dir. Strasbourg" },
      { label: "Seats", value: "7B · 8B" },
      { label: "Booking no.", value: "336 054 7434", copy: true },
      { label: "Price", value: "€11.97" },
    ],
    links: [
      { label: "Track this bus", url: "https://www.flixbus.com/track/order/3360547434" },
      { label: "Manage booking (rebooking)", url: "https://shop.flixbus.com/rebooking" },
    ],
    price: 11.97,
    notes: "Drop-off at Place de l'Étoile, Strasbourg's main bus terminal.",
  },
  {
    id: "bus-ncy-bsl-backup",
    type: "bus",
    day: "2026-06-13",
    start: "22:55",
    end: "02:00",
    endDay: "2026-06-14",
    title: "Nancy → Basel (backup)",
    subtitle: "FlixBus N836 · unused return leg",
    ticketPdf: "tickets/flix-basel-nancy-roundtrip.pdf#page=2",
    from: {
      name: "Nancy (Quai Sainte-Catherine)",
      address: "4710 Quai Sainte-Catherine, 54000 Nancy, France",
      coords: [48.6906, 6.1899],
    },
    to: {
      name: "Basel SBB (Meret-Oppenheim-Strasse)",
      address: "Meret-Oppenheim-Strasse, 4053 Basel, Switzerland",
      coords: [47.5455, 7.5905],
    },
    info: [
      { label: "Route", value: "N836 · dir. Milano Lampugnano" },
      { label: "Seats", value: "20B · 20E" },
      { label: "Booking no.", value: "334 304 7318", copy: true },
    ],
    links: [
      { label: "Track this bus", url: "https://www.flixbus.com/track/order/3343047318" },
      { label: "Manage booking (rebooking)", url: "https://shop.flixbus.com/rebooking" },
    ],
    badges: ["Backup · not used"],
    notes:
      "This is the return half of the Basel↔Nancy round trip. The plan instead goes Nancy → Strasbourg, so this ticket is a fallback only. Keep it in case Strasbourg plans change.",
  },
  {
    id: "stay-strasbourg",
    type: "stay",
    day: "2026-06-13",
    start: "14:30",
    title: "Montagne Verte & Rest. Louisiane",
    subtitle: "Strasbourg · 2 nights",
    place: {
      name: "Hotel Strasbourg — Montagne Verte & Restaurant Louisiane",
      address: "14 rue des Corroyeurs, 67200 Strasbourg, France",
      coords: [48.5727, 7.728717],
    },
    checkIn: "2026-06-13 14:30",
    checkOut: "2026-06-15 12:00",
    endDay: "2026-06-15",
    nights: 2,
    info: [
      { label: "Check-in", value: "Sat 13 Jun · 14:30 – 00:00" },
      { label: "Check-out", value: "Mon 15 Jun · 07:00 – 12:00" },
      { label: "Confirmation", value: "6761.153.084", copy: true },
      { label: "PIN", value: "8402", copy: true },
      { label: "Phone", value: "+33 3 88 29 06 06", copy: true },
      { label: "Guests", value: "2 adults · 1 room" },
      { label: "Price", value: "€140.00 (incl. 10% tax)" },
    ],
    links: [{ label: "Booking.com", url: "https://www.booking.com" }],
    price: 140.0,
    notes: "Bus from Nancy arrives Strasbourg 20:00 — easy same-evening check-in (reception open until midnight).",
  },

  /* ───────────────── Mon 15 June ───────────────── */
  {
    id: "bus-str-eap",
    type: "bus",
    day: "2026-06-15",
    start: "15:05",
    end: "17:25",
    title: "Strasbourg → Basel Airport",
    subtitle: "FlixBus 108 · dir. Zürich",
    ticketPdf: "tickets/flix-strasbourg-basel-eap.pdf",
    from: {
      name: "Strasbourg (Place de l'Étoile)",
      address: "Place de l'Étoile, 67076 Strasbourg, France",
      coords: [48.5736, 7.7521],
    },
    to: {
      name: "EuroAirport Basel (EAP)",
      address: "EuroAirport Basel Mulhouse Freiburg, 68304 Saint-Louis, France",
      coords: [47.5896, 7.5299],
    },
    info: [
      { label: "Route", value: "108 · dir. Zürich" },
      { label: "Seats", value: "20E · 20C" },
      { label: "Booking no.", value: "336 058 4937", copy: true },
      { label: "Price", value: "€24.97" },
    ],
    links: [
      { label: "Track this bus", url: "https://www.flixbus.com/track/order/3360584937" },
      { label: "Manage booking (rebooking)", url: "https://shop.flixbus.com/rebooking" },
    ],
    price: 24.97,
    notes: "Boards at Place de l'Étoile. Drops right at EuroAirport — handy if the Basel stay is near the airport.",
  },
  {
    id: "stay-basel",
    type: "stay",
    day: "2026-06-15",
    start: "19:00",
    title: "Hotel du Village",
    subtitle: "Village-Neuf · 1 night · ★★★",
    place: {
      name: "Hotel du Village",
      address: "6a Rue de Rosenau, 68128 Village-Neuf, France",
    },
    checkIn: "2026-06-15 19:00",
    checkOut: "2026-06-16 11:00",
    endDay: "2026-06-16",
    nights: 1,
    info: [
      { label: "Check-in", value: "Mon 15 Jun · 19:00 (approved)" },
      { label: "Arrival window", value: "19:00 – 20:00" },
      { label: "Check-out", value: "Tue 16 Jun · 08:00 – 11:00" },
      { label: "Phone", value: "+33 9 61 06 18 74", copy: true },
      { label: "Guests", value: "2 adults · 1 room" },
    ],
    links: [{ label: "Booking.com", url: "https://www.booking.com" }],
    notes:
      "Last night before the flight home — in Village-Neuf (FR), right by EuroAirport Basel, so the 17:45 flight on 16 Jun is an easy hop. Bus from Strasbourg drops at the airport (EAP) at 17:25; reception takes arrivals until 21:00. Add the confirmation number, PIN and price here once you have them.",
  },

  /* ───────────────── Tue 16 June ───────────────── */
  {
    id: "fl-bsl-zag",
    type: "flight",
    day: "2026-06-16",
    start: "17:45",
    end: "19:30",
    title: "Basel → Zagreb",
    subtitle: "Flight home",
    from: { name: "EuroAirport Basel (BSL)", address: "EuroAirport, 68300 Saint-Louis, France", coords: [47.5896, 7.5299] },
    to: { name: "Zagreb Airport (ZAG)", address: "Franjo Tuđman Airport, 10150 Zagreb, Croatia", coords: [45.7429, 16.0688] },
    info: [
      { label: "Departs", value: "Tue 16 Jun · 17:45" },
      { label: "Arrives", value: "Tue 16 Jun · 19:30" },
    ],
    notes: "No e-ticket PDF yet — times are from the master plan. Add the airline + booking reference here once you have them.",
  },
];

// Exposed for app.js (kept as plain globals so there's no build step).
window.EXP33_SEED = { trip: TRIP, dayMeta: DAY_META, items: SEED_ITEMS };
