/* ============================================================
   Expedition 33 — app logic (vanilla JS, no build step)
   Store → localStorage. Renders Plan / Bookings / Info.
   Tap items for a detail sheet; add & edit anything.
   ============================================================ */
(function () {
  "use strict";

  /* ---------- type metadata ---------- */
  const TYPES = {
    flight:   { icon: "✈️", color: "#7fb2e6", label: "Flight" },
    bus:      { icon: "🚌", color: "#e0b25c", label: "Bus" },
    stay:     { icon: "🏨", color: "#66c5b4", label: "Stay" },
    event:    { icon: "🎵", color: "#d98aa6", label: "Event" },
    activity: { icon: "📍", color: "#97c97a", label: "Activity" },
    note:     { icon: "📝", color: "#b3a6d6", label: "Note" },
  };
  const TRANSPORT = new Set(["flight", "bus"]);
  const STORE_KEY = "exp33.state.v4";

  const DEFAULT_CHECKLIST = [
    "Passports / ID cards",
    "Concert tickets (printed + on phone)",
    "All FlixBus tickets saved offline",
    "Hotel confirmation numbers + PINs",
    "Travel insurance / EHIC card",
    "EUR cash + bank cards",
    "Phone chargers + power bank",
    "Check Nancy concert weather (open-air!)",
    "Book Basel accommodation (15–16 Jun)",
  ];

  /* ---------- state ---------- */
  let state = null;          // { trip, dayMeta, items, checklist }
  let currentTab = "plan";

  /* ---------- tiny utils ---------- */
  const $ = (sel, root) => (root || document).querySelector(sel);
  const el = (id) => document.getElementById(id);
  const clone = (o) => JSON.parse(JSON.stringify(o));
  const esc = (s) =>
    String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );
  const soft = (hex) => hex + "22";
  const line = (hex) => hex + "55";

  function toast(msg) {
    const t = el("toast");
    t.textContent = msg;
    t.hidden = false;
    requestAnimationFrame(() => t.classList.add("show"));
    clearTimeout(toast._t);
    toast._t = setTimeout(() => {
      t.classList.remove("show");
      setTimeout(() => (t.hidden = true), 220);
    }, 1700);
  }

  /* ---------- date helpers (parse YYYY-MM-DD without TZ surprises) ---------- */
  const DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  function ymd(str) {
    const [y, m, d] = str.split("-").map(Number);
    return new Date(y, m - 1, d);
  }
  const dow = (str) => DOW[ymd(str).getDay()];
  const dayNum = (str) => ymd(str).getDate();
  const monName = (str) => MON[ymd(str).getMonth()];
  function dateRange(a, b) {
    const out = [];
    const cur = ymd(a), end = ymd(b);
    while (cur <= end) {
      out.push(`${cur.getFullYear()}-${String(cur.getMonth() + 1).padStart(2, "0")}-${String(cur.getDate()).padStart(2, "0")}`);
      cur.setDate(cur.getDate() + 1);
    }
    return out;
  }
  const todayStr = () => {
    const n = new Date();
    return `${n.getFullYear()}-${String(n.getMonth() + 1).padStart(2, "0")}-${String(n.getDate()).padStart(2, "0")}`;
  };

  function mapsUrl(loc) {
    if (!loc) return "";
    if (loc.coords && loc.coords.length === 2)
      return `https://www.google.com/maps/search/?api=1&query=${loc.coords[0]},${loc.coords[1]}`;
    const q = [loc.name, loc.address].filter(Boolean).join(" ");
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q)}`;
  }

  /* ---------- store ---------- */
  function freshFromSeed() {
    const s = window.EXP33_SEED;
    return {
      trip: clone(s.trip),
      dayMeta: clone(s.dayMeta),
      items: clone(s.items),
      checklist: DEFAULT_CHECKLIST.map((t, i) => ({ id: "c" + i, label: t, done: false })),
    };
  }
  function load() {
    try {
      const raw = localStorage.getItem(STORE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed && parsed.items) return parsed;
      }
    } catch (e) { /* ignore */ }
    return freshFromSeed();
  }
  function save() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(state)); }
    catch (e) { toast("⚠️ Could not save"); }
  }
  const uid = () => "u" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

  function getItem(id) { return state.items.find((i) => i.id === id); }
  function upsertItem(item) {
    const idx = state.items.findIndex((i) => i.id === item.id);
    if (idx >= 0) state.items[idx] = item;
    else state.items.push(item);
    save();
  }
  function deleteItem(id) {
    state.items = state.items.filter((i) => i.id !== id);
    save();
  }

  /* ---------- item ordering & overnight ---------- */
  function startMins(it) {
    if (!it.start) return 99999;
    const [h, m] = it.start.split(":").map(Number);
    return h * 60 + m;
  }
  function itemsForDay(day) {
    return state.items
      .filter((i) => i.day === day)
      .sort((a, b) => startMins(a) - startMins(b));
  }
  function overnightFor(day) {
    // find a stay covering the NIGHT of `day` (checkIn <= day < checkOut)
    const d = ymd(day);
    return state.items.find((i) => {
      if (i.type !== "stay" || !i.checkIn) return null;
      const ci = ymd(i.checkIn.slice(0, 10));
      const co = i.checkOut ? ymd(i.checkOut.slice(0, 10)) : null;
      return d >= ci && (!co || d < co);
    });
  }

  /* ---------- badge helper ---------- */
  function badgeHTML(b) {
    const low = b.toLowerCase();
    let cls = "badge";
    if (low.includes("main") || b.includes("⭐")) cls += " badge--star";
    else if (low.includes("backup") || low.includes("not used") || low.includes("book")) cls += " badge--warn";
    return `<span class="${cls}">${esc(b)}</span>`;
  }

  /* ============================================================
     PLAN TAB
     ============================================================ */
  function renderPlan() {
    const days = dateRange(state.trip.startDate, state.trip.endDate);
    const today = todayStr();
    let html = "";
    days.forEach((day) => {
      const meta = state.dayMeta[day] || {};
      const items = itemsForDay(day);
      const overnight = overnightFor(day);
      const isToday = day === today;
      html += `<section class="day-section" id="day-${day}" data-day="${day}">
        <div class="day-head">
          <span class="day-head__date">${dayNum(day)} ${monName(day)}</span>
          <span class="day-head__dow">${dow(day)}${isToday ? " · today" : ""}</span>
          ${meta.city ? `<span class="day-head__city">${esc(meta.city)}</span>` : ""}
        </div>
        <div class="timeline">`;

      if (items.length === 0) {
        html += `<div class="overnight" style="border-style:solid;background:rgba(255,255,255,.03);border-color:var(--line)">
          <span>🌤️</span><span>Free day${meta.city ? " in " + esc(meta.city.split("→").pop().trim()) : ""}</span></div>`;
      }
      items.forEach((it) => (html += itemCardHTML(it)));

      if (overnight) {
        html += `<div class="overnight"><span>🌙</span><span>Overnight · <b>${esc(overnight.place ? overnight.place.name : overnight.title)}</b></span></div>`;
      }
      html += `</div></section>`;
    });
    el("screen").innerHTML = html;
    observeDays();
  }

  function itemCardHTML(it) {
    const t = TYPES[it.type] || TYPES.note;
    const badges = (it.badges || []);
    let cls = "item";
    if (badges.some((b) => /backup|not used/i.test(b))) cls += " is-backup";
    if (badges.some((b) => /book/i.test(b))) cls += " is-todo";
    const styleVars = `--accent:${t.color};--accent-soft:${soft(t.color)};--accent-line:${line(t.color)}`;
    const sub = it.type === "stay" && it.nights
      ? `${esc(it.subtitle || "")}`
      : esc(it.subtitle || "");
    let routeLine = "";
    if (TRANSPORT.has(it.type) && it.from && it.to) {
      routeLine = `<div class="item__route">${esc(shortName(it.from.name))} <span style="color:var(--accent)">→</span> ${esc(shortName(it.to.name))}</div>`;
    } else if (it.place && it.place.name) {
      routeLine = `<div class="item__route">📍 ${esc(shortName(it.place.name))}</div>`;
    }
    return `<article class="${cls}" data-open="${it.id}" style="${styleVars}">
      <div class="item__time">
        <span class="item__start">${it.start ? esc(it.start) : "—"}</span>
        ${it.end ? `<span class="item__end">${esc(it.end)}${it.endDay && it.endDay !== it.day ? " +1" : ""}</span>` : ""}
      </div>
      <div class="item__icon">${t.icon}</div>
      <div class="item__body">
        <div class="item__title">${esc(it.title)}</div>
        ${sub ? `<div class="item__sub">${sub}</div>` : ""}
        ${routeLine}
        ${badges.length ? `<div class="badges">${badges.map(badgeHTML).join("")}</div>` : ""}
      </div>
      <span class="item__chev">›</span>
    </article>`;
  }
  function shortName(n) { return n ? n.split("(")[0].split(",")[0].trim() : ""; }

  /* date strip */
  function renderDateStrip() {
    const strip = el("datestrip");
    if (currentTab !== "plan") { strip.hidden = true; return; }
    strip.hidden = false;
    const today = todayStr();
    strip.innerHTML = dateRange(state.trip.startDate, state.trip.endDate)
      .map((day) => `<button class="datepill${day === today ? " is-active" : ""}" data-jump="${day}">
        <span class="datepill__dow">${dow(day)}</span>
        <span class="datepill__day">${dayNum(day)}</span>
      </button>`).join("");
  }
  let dayObserver = null;
  function observeDays() {
    if (dayObserver) dayObserver.disconnect();
    if (currentTab !== "plan") return;
    dayObserver = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) setActivePill(e.target.dataset.day);
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    document.querySelectorAll(".day-section").forEach((s) => dayObserver.observe(s));
  }
  function setActivePill(day) {
    document.querySelectorAll(".datepill").forEach((p) =>
      p.classList.toggle("is-active", p.dataset.jump === day));
  }

  /* ============================================================
     BOOKINGS TAB
     ============================================================ */
  function renderBookings() {
    const groups = [
      { key: "stay", title: "🏨 Stays", types: ["stay"] },
      { key: "transport", title: "🚌 Transport", types: ["flight", "bus"] },
      { key: "tickets", title: "🎟️ Tickets & Events", types: ["event"] },
      { key: "other", title: "📝 Other", types: ["activity", "note"] },
    ];
    let html = `<p class="intro" style="margin-top:14px">Every booking in one place. Tap any card for addresses, maps, seats, confirmation numbers and notes.</p>`;
    groups.forEach((g) => {
      const items = state.items
        .filter((i) => g.types.includes(i.type))
        .sort((a, b) => (a.day + (a.start || "")).localeCompare(b.day + (b.start || "")));
      if (!items.length) return;
      html += `<h2 class="group-title">${g.title}<span class="count">${items.length}</span></h2>`;
      items.forEach((it) => (html += itemCardHTML(it)));
    });
    el("screen").innerHTML = `<div class="fade-in">${html}</div>`;
  }

  /* ============================================================
     INFO TAB
     ============================================================ */
  function money(n) { return "€" + n.toFixed(2); }
  function renderInfo() {
    const t = state.trip;
    const days = dateRange(t.startDate, t.endDate).length;
    // cost buckets
    let stays = 0, transport = 0, tickets = 0;
    state.items.forEach((i) => {
      if (!i.price) return;
      if (i.type === "stay") stays += i.price;
      else if (TRANSPORT.has(i.type)) transport += i.price;
      else if (i.type === "event") tickets += i.price;
    });
    const total = stays + transport + tickets;
    const per = state.trip.travelers.length || 1;

    const travelersHTML = t.travelers.map((name) => {
      const initials = name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();
      return `<div class="traveler"><span class="av">${esc(initials)}</span>${esc(name)}</div>`;
    }).join("");

    const checklistHTML = state.checklist.map((c) =>
      `<div class="check-row${c.done ? " done" : ""}" data-check="${c.id}">
        <div class="check-box">✓</div>
        <div class="check-label">${esc(c.label)}</div>
        <button class="check-del" data-checkdel="${c.id}" aria-label="Delete">×</button>
      </div>`).join("");

    el("screen").innerHTML = `<div class="fade-in">
      <div class="card">
        <h3>🧭 The trip</h3>
        <div class="kv"><span class="k">Route</span><span class="v">Basel · Freiburg · Nancy · Strasbourg</span></div>
        <div class="kv"><span class="k">Dates</span><span class="v">${dayNum(t.startDate)} ${monName(t.startDate)} – ${dayNum(t.endDate)} ${monName(t.endDate)} 2026</span></div>
        <div class="kv"><span class="k">Duration</span><span class="v">${days} days</span></div>
        <div class="kv"><span class="k">Travellers</span><span class="v">${per}</span></div>
        <div style="margin-top:12px" class="travelers">${travelersHTML}</div>
      </div>

      <div class="card">
        <h3>💶 Budget so far</h3>
        <div class="kv"><span class="k">🏨 Stays</span><span class="v">${money(stays)}</span></div>
        <div class="kv"><span class="k">🚌 Transport (buses)</span><span class="v">${money(transport)}</span></div>
        <div class="kv"><span class="k">🎟️ Concert tickets</span><span class="v">${money(tickets)}</span></div>
        <div class="cost-total"><span>Total</span><span>${money(total)}</span></div>
        <div class="kv" style="margin-top:6px"><span class="k">Per person</span><span class="v">${money(total / per)}</span></div>
        <p class="form-hint">Flights aren't priced yet — add the fares on each flight to include them. The Nancy→Basel backup bus isn't double-counted.</p>
      </div>

      <div class="card">
        <h3>✅ Checklist</h3>
        ${checklistHTML || '<p class="form-hint">Nothing yet.</p>'}
        <div class="mini-row" style="margin-top:12px">
          <input id="newCheck" placeholder="Add a checklist item…" />
          <button class="rm" id="addCheck" style="color:var(--gold-soft)">+</button>
        </div>
      </div>

      <div class="card">
        <h3>💾 Your data</h3>
        <p class="form-hint" style="margin-top:0">Everything you add or edit is saved on this phone. Back it up or move it to another phone with export / import.</p>
        <div class="btn-row">
          <button class="btn" id="exportBtn">⬇️ Export</button>
          <button class="btn" id="importBtn">⬆️ Import</button>
        </div>
        <button class="btn btn--ghost btn--danger" id="resetBtn" style="margin-top:10px">↺ Reset to original plan</button>
        <input type="file" id="importFile" accept="application/json,.json" hidden />
      </div>

      <p class="intro" style="text-align:center;margin:18px 4px 4px">Expedition 33 · made for Sebastijan & Mia ✨<br/>Add to Home Screen to use it like an app, offline.</p>
    </div>`;
  }

  /* ============================================================
     DETAIL SHEET
     ============================================================ */
  let sheetMode = null; // 'detail' | 'form'
  function openSheet(html) {
    const sheet = el("sheet"), scrim = el("scrim");
    sheet.innerHTML = `<div class="sheet__grab"></div><div class="sheet__scroll">${html}</div>`;
    sheet.hidden = false; scrim.hidden = false;
    requestAnimationFrame(() => { sheet.classList.add("show"); scrim.classList.add("show"); });
    document.body.style.overflow = "hidden";
  }
  function closeSheet() {
    const sheet = el("sheet"), scrim = el("scrim");
    sheet.classList.remove("show"); scrim.classList.remove("show");
    document.body.style.overflow = "";
    setTimeout(() => { sheet.hidden = true; scrim.hidden = true; sheet.innerHTML = ""; sheetMode = null; }, 320);
  }

  function showDetail(id) {
    const it = getItem(id);
    if (!it) return;
    sheetMode = "detail";
    const t = TYPES[it.type] || TYPES.note;
    const styleVars = `--accent:${t.color};--accent-soft:${soft(t.color)};--accent-line:${line(t.color)}`;
    const whenStr = it.start
      ? `${dow(it.day)} ${dayNum(it.day)} ${monName(it.day)} · ${it.start}${it.end ? " – " + it.end : ""}${it.endDay && it.endDay !== it.day ? " (+1)" : ""}`
      : `${dow(it.day)} ${dayNum(it.day)} ${monName(it.day)}`;

    let html = `<div class="sheet__head" style="${styleVars}">
      <div class="sheet__icon">${t.icon}</div>
      <div style="min-width:0">
        <div class="sheet__title">${esc(it.title)}</div>
        ${it.subtitle ? `<div class="sheet__sub">${esc(it.subtitle)}</div>` : ""}
        <div class="sheet__when">${esc(whenStr)}</div>
      </div>
    </div>`;

    if (it.badges && it.badges.length)
      html += `<div class="badges" style="${styleVars};margin-bottom:4px">${it.badges.map(badgeHTML).join("")}</div>`;

    // ticket / boarding pass — prominent, for quick QR scan at the gate
    if (it.ticketPdf) {
      const label = it.type === "event" ? "Open tickets — scan QR" : "Open ticket — scan QR";
      html += `<a class="btn btn--gold ticket-btn" href="${esc(it.ticketPdf)}" target="_blank" rel="noopener">🎫 ${label}</a>`;
    }

    // route (transport) or place (single)
    if (TRANSPORT.has(it.type) && (it.from || it.to)) {
      html += `<div class="sheet__section-label">Route</div><div class="routebox">`;
      if (it.from) html += routePointHTML(it.from, "from", it.start);
      if (it.to) html += routePointHTML(it.to, "to", it.end);
      html += `</div>`;
    } else if (it.place) {
      html += `<div class="sheet__section-label">Location</div><div class="routebox">${routePointHTML(it.place, "to")}</div>`;
    }

    // facts
    if (it.info && it.info.length) {
      html += `<div class="sheet__section-label">Details</div><div class="facts">`;
      it.info.forEach((f) => {
        const v = f.copy
          ? `<span class="fact__v copyable" data-copy="${esc(f.value)}">${esc(f.value)}</span>`
          : `<span class="fact__v">${esc(f.value)}</span>`;
        html += `<div class="fact"><span class="fact__k">${esc(f.label)}</span>${v}</div>`;
      });
      html += `</div>`;
    }

    // actions: phone + links
    const phone = (it.info || []).find((f) => /phone/i.test(f.label));
    const acts = [];
    if (phone) acts.push(`<a class="action" href="tel:${esc(phone.value.replace(/\s+/g, ""))}"><span class="action__i">📞</span>Call</a>`);
    (it.links || []).forEach((l) => {
      const icon = /track/i.test(l.label) ? "📡" : /booking\.com/i.test(l.label) ? "🛏️" : /rebook|manage/i.test(l.label) ? "🔧" : "🔗";
      acts.push(`<a class="action" href="${esc(l.url)}" target="_blank" rel="noopener"><span class="action__i">${icon}</span>${esc(l.label)}</a>`);
    });
    if (acts.length) html += `<div class="sheet__section-label">Open</div><div class="actions">${acts.join("")}</div>`;

    // notes
    html += `<div class="sheet__section-label">Notes</div>`;
    html += it.notes
      ? `<div class="notes-display">${esc(it.notes)}</div>`
      : `<div class="notes-display notes-empty">No notes yet — tap Edit to add some.</div>`;

    // footer
    html += `<div class="sheet__foot">
      <button class="btn btn--gold" data-edit="${it.id}">✎ Edit</button>
      <button class="btn btn--danger" data-del="${it.id}">Delete</button>
    </div>`;

    openSheet(html);
  }

  function routePointHTML(loc, dir, time) {
    const url = mapsUrl(loc);
    return `<div class="routepoint routepoint--${dir}">
      <div class="routepoint__dot"><i></i></div>
      <div class="routepoint__body">
        <div class="routepoint__name">${esc(loc.name || "")}</div>
        ${loc.address ? `<div class="routepoint__addr">${esc(loc.address)}</div>` : ""}
        ${url ? `<div class="routepoint__map"><a class="maplink" href="${esc(url)}" target="_blank" rel="noopener">📍 Open in Google Maps</a></div>` : ""}
      </div>
    </div>`;
  }

  /* ============================================================
     ADD / EDIT FORM
     ============================================================ */
  function showForm(id) {
    sheetMode = "form";
    const isEdit = !!id;
    const it = isEdit ? clone(getItem(id)) : {
      id: uid(), type: "activity", day: defaultDay(), start: "", end: "",
      title: "", subtitle: "", info: [], links: [], notes: "", badges: [],
    };
    it.info = it.info || []; it.links = it.links || [];
    const isTransport = TRANSPORT.has(it.type);

    const typePicker = Object.entries(TYPES).map(([k, v]) =>
      `<button type="button" class="type-opt${it.type === k ? " sel" : ""}" data-type="${k}">
        <span class="e">${v.icon}</span>${v.label}</button>`).join("");

    const loc = (l) => l || { name: "", address: "" };
    const from = loc(it.from), to = loc(it.to), place = loc(it.place);

    const infoRows = it.info.map((f, i) => miniPair("info", i, f.label, f.value)).join("");
    const linkRows = it.links.map((l, i) => miniPair("link", i, l.label, l.url)).join("");

    const html = `
      <div class="sheet__head">
        <div class="sheet__icon">${(TYPES[it.type] || TYPES.note).icon}</div>
        <div><div class="sheet__title">${isEdit ? "Edit" : "Add"} item</div>
        <div class="sheet__sub">${isEdit ? "Update the details below" : "Add a stop, booking, plan or note"}</div></div>
      </div>

      <div class="field"><label>Type</label><div class="type-picker" id="typePicker">${typePicker}</div></div>

      <div class="field"><label>Title</label><input id="f_title" value="${esc(it.title)}" placeholder="e.g. Dinner in Strasbourg" /></div>
      <div class="field"><label>Subtitle</label><input id="f_subtitle" value="${esc(it.subtitle || "")}" placeholder="short summary (optional)" /></div>

      <div class="field-2">
        <div class="field"><label>Date</label><input type="date" id="f_day" value="${esc(it.day)}" /></div>
        <div class="field"><label>Start</label><input type="time" id="f_start" value="${esc(it.start || "")}" /></div>
        <div class="field"><label>End</label><input type="time" id="f_end" value="${esc(it.end || "")}" /></div>
      </div>

      <div id="locFields">${locFieldsHTML(isTransport, from, to, place)}</div>

      <div class="field-2">
        <div class="field"><label>Price €</label><input type="number" inputmode="decimal" step="0.01" id="f_price" value="${it.price != null ? it.price : ""}" placeholder="0.00" /></div>
        <div class="field"><label>Tags (comma sep.)</label><input id="f_badges" value="${esc((it.badges || []).join(", "))}" placeholder="Backup, Overnight…" /></div>
      </div>

      <div class="field"><label>Details (label · value)</label>
        <div id="infoRows">${infoRows}</div>
        <button type="button" class="add-mini" data-add="info">+ Add detail</button>
      </div>

      <div class="field"><label>Links (label · url)</label>
        <div id="linkRows">${linkRows}</div>
        <button type="button" class="add-mini" data-add="link">+ Add link</button>
      </div>

      <div class="field"><label>🎫 Ticket PDF / link (optional)</label><input id="f_ticket" value="${esc(it.ticketPdf || "")}" placeholder="tickets/…  or  https://… (opens for QR scan)" /></div>

      <div class="field"><label>Notes</label><textarea id="f_notes" placeholder="Anything to remember…">${esc(it.notes || "")}</textarea></div>

      <div class="sheet__foot">
        <button class="btn btn--ghost" data-cancel="1">Cancel</button>
        <button class="btn btn--gold" data-save="${it.id}">Save</button>
      </div>`;
    openSheet(html);

    // wire type picker → swap loc fields + icon
    $("#typePicker").addEventListener("click", (e) => {
      const b = e.target.closest("[data-type]"); if (!b) return;
      const type = b.dataset.type;
      $$(".type-opt").forEach((o) => o.classList.toggle("sel", o.dataset.type === type));
      el("sheet").querySelector(".sheet__icon").textContent = TYPES[type].icon;
      $("#locFields").innerHTML = locFieldsHTML(TRANSPORT.has(type), readLoc("from"), readLoc("to"), readLoc("place"));
    });
  }

  function defaultDay() {
    const t = todayStr();
    const days = dateRange(state.trip.startDate, state.trip.endDate);
    return days.includes(t) ? t : days[0];
  }
  const $$ = (sel) => Array.from(el("sheet").querySelectorAll(sel));
  function val(id) { const e = $("#" + id); return e ? e.value.trim() : ""; }
  function readLoc(which) {
    return { name: val(`f_${which}_name`), address: val(`f_${which}_addr`) };
  }
  function selectedType() {
    const sel = $(".type-opt.sel"); return sel ? sel.dataset.type : "activity";
  }

  function locFieldsHTML(isTransport, from, to, place) {
    if (isTransport) {
      return `<div class="field"><label>From — name</label><input id="f_from_name" value="${esc(from.name)}" placeholder="Origin station / airport" /></div>
        <div class="field"><label>From — address</label><input id="f_from_addr" value="${esc(from.address || "")}" placeholder="Street, city" /></div>
        <div class="field"><label>To — name</label><input id="f_to_name" value="${esc(to.name)}" placeholder="Destination" /></div>
        <div class="field"><label>To — address</label><input id="f_to_addr" value="${esc(to.address || "")}" placeholder="Street, city" /></div>`;
    }
    return `<div class="field"><label>Place — name</label><input id="f_place_name" value="${esc(place.name)}" placeholder="Hotel / venue / spot" /></div>
      <div class="field"><label>Place — address</label><input id="f_place_addr" value="${esc(place.address || "")}" placeholder="Street, city (used for the map pin)" /></div>`;
  }
  function miniPair(kind, i, a, b) {
    return `<div class="mini-row" data-kind="${kind}">
      <input class="mp-a" value="${esc(a || "")}" placeholder="${kind === "link" ? "Label" : "Label"}" />
      <input class="mp-b" value="${esc(b || "")}" placeholder="${kind === "link" ? "https://…" : "Value"}" />
      <button type="button" class="rm" data-rm="1">×</button>
    </div>`;
  }

  function collectForm(id) {
    const type = selectedType();
    const isTransport = TRANSPORT.has(type);
    const prev = getItem(id) || {};
    const item = {
      id,
      type,
      day: val("f_day") || defaultDay(),
      start: val("f_start"),
      end: val("f_end"),
      title: val("f_title") || "Untitled",
      subtitle: val("f_subtitle"),
      notes: $("#f_notes") ? $("#f_notes").value.trim() : "",
    };
    // end day +1 if end < start
    if (item.start && item.end && item.end < item.start) {
      const d = ymd(item.day); d.setDate(d.getDate() + 1);
      item.endDay = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    }
    const price = val("f_price");
    if (price !== "") item.price = parseFloat(price);
    const ticket = val("f_ticket");
    if (ticket) item.ticketPdf = ticket;
    const badges = val("f_badges");
    if (badges) item.badges = badges.split(",").map((s) => s.trim()).filter(Boolean);

    // locations — preserve coords only if address unchanged
    function buildLoc(which, prevLoc) {
      const name = val(`f_${which}_name`), address = val(`f_${which}_addr`);
      if (!name && !address) return null;
      const lo = { name, address };
      if (prevLoc && prevLoc.coords && prevLoc.address === address) lo.coords = prevLoc.coords;
      return lo;
    }
    if (isTransport) {
      item.from = buildLoc("from", prev.from);
      item.to = buildLoc("to", prev.to);
    } else {
      item.place = buildLoc("place", prev.place);
      // carry stay metadata if it was a stay
      if (type === "stay") {
        ["checkIn", "checkOut", "nights", "endDay"].forEach((k) => { if (prev[k] != null) item[k] = prev[k]; });
      }
    }

    // info & links from dynamic rows
    item.info = [];
    $$('.mini-row[data-kind="info"]').forEach((r) => {
      const a = $(".mp-a", r).value.trim(), b = $(".mp-b", r).value.trim();
      if (a || b) {
        const f = { label: a, value: b };
        const prevF = (prev.info || []).find((x) => x.label === a && x.value === b);
        if (prevF && prevF.copy) f.copy = true;
        else if (/conf|pin|booking|phone|ref|number/i.test(a)) f.copy = true;
        item.info.push(f);
      }
    });
    item.links = [];
    $$('.mini-row[data-kind="link"]').forEach((r) => {
      const a = $(".mp-a", r).value.trim(); let b = $(".mp-b", r).value.trim();
      if (b && !/^https?:\/\//i.test(b) && !/^tel:/.test(b)) b = "https://" + b;
      if (a || b) item.links.push({ label: a || b, url: b });
    });
    return item;
  }

  /* ============================================================
     EXPORT / IMPORT / RESET
     ============================================================ */
  function exportData() {
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "expedition33-plan.json";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast("Exported ✓");
  }
  function importData(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const data = JSON.parse(reader.result);
        if (!data.items) throw new Error("bad");
        state = {
          trip: data.trip || state.trip,
          dayMeta: data.dayMeta || state.dayMeta,
          items: data.items,
          checklist: data.checklist || state.checklist,
        };
        save(); render();
        toast("Imported ✓");
      } catch (e) { toast("⚠️ Invalid file"); }
    };
    reader.readAsText(file);
  }

  /* ============================================================
     COUNTDOWN
     ============================================================ */
  function updateCountdown() {
    const t = state.trip;
    const numEl = el("countdownNum"), labEl = el("countdownLabel");
    if (!t.countdownTo) { numEl.textContent = "✦"; labEl.textContent = ""; return; }
    const target = new Date(t.countdownTo).getTime();
    const now = Date.now();
    const diff = target - now;
    const dayMs = 86400000;
    if (diff > dayMs) { numEl.textContent = Math.ceil(diff / dayMs); labEl.textContent = "days to go"; }
    else if (diff > 3600000) { numEl.textContent = Math.ceil(diff / 3600000); labEl.textContent = "hours"; }
    else if (diff > 0) { numEl.textContent = Math.ceil(diff / 60000); labEl.textContent = "minutes"; }
    else if (diff > -4 * 3600000) { numEl.textContent = "♪"; labEl.textContent = "now live"; }
    else {
      // after the concert → days until trip end, else done
      const end = ymd(t.endDate).getTime() + dayMs;
      if (now < end) { numEl.textContent = "✦"; labEl.textContent = "on trip"; }
      else { numEl.textContent = "✓"; labEl.textContent = "memories"; }
    }
  }

  /* ============================================================
     RENDER + EVENTS
     ============================================================ */
  function render() {
    el("tripTitle").textContent = state.trip.title;
    el("tripSubtitle").textContent = state.trip.subtitle || "";
    renderDateStrip();
    if (currentTab === "plan") renderPlan();
    else if (currentTab === "bookings") renderBookings();
    else renderInfo();
    el("fab").hidden = currentTab === "info";
    updateCountdown();
  }

  function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll(".tabbar__btn").forEach((b) =>
      b.classList.toggle("is-active", b.dataset.tab === tab));
    el("screen").scrollTop = 0;
    window.scrollTo(0, 0);
    render();
  }

  function wireEvents() {
    // tab bar
    el("tabbar").addEventListener("click", (e) => {
      const b = e.target.closest(".tabbar__btn"); if (b) switchTab(b.dataset.tab);
    });
    // date strip jump
    el("datestrip").addEventListener("click", (e) => {
      const b = e.target.closest(".datepill"); if (!b) return;
      const sec = el("day-" + b.dataset.jump);
      if (sec) sec.scrollIntoView({ behavior: "smooth", block: "start" });
      setActivePill(b.dataset.jump);
    });
    // FAB
    el("fab").addEventListener("click", () => showForm(null));
    // scrim closes sheet
    el("scrim").addEventListener("click", closeSheet);

    // global click delegation (cards, sheet buttons, info actions)
    document.addEventListener("click", (e) => {
      const open = e.target.closest("[data-open]");
      if (open && !el("sheet").contains(open)) { showDetail(open.dataset.open); return; }

      const copy = e.target.closest("[data-copy]");
      if (copy) { copyText(copy.dataset.copy); return; }

      const edit = e.target.closest("[data-edit]");
      if (edit) { showForm(edit.dataset.edit); return; }

      const del = e.target.closest("[data-del]");
      if (del) {
        if (confirm("Delete this item?")) { deleteItem(del.dataset.del); closeSheet(); render(); toast("Deleted"); }
        return;
      }
      const cancel = e.target.closest("[data-cancel]");
      if (cancel) { closeSheet(); return; }

      const saveBtn = e.target.closest("[data-save]");
      if (saveBtn) {
        const item = collectForm(saveBtn.dataset.save);
        upsertItem(item); closeSheet(); render(); toast("Saved ✓");
        return;
      }
      const addMini = e.target.closest("[data-add]");
      if (addMini) {
        const kind = addMini.dataset.add;
        const wrap = el(kind === "info" ? "infoRows" : "linkRows");
        wrap.insertAdjacentHTML("beforeend", miniPair(kind, wrap.children.length, "", ""));
        return;
      }
      const rm = e.target.closest("[data-rm]");
      if (rm) { rm.closest(".mini-row").remove(); return; }

      // info tab buttons
      if (e.target.closest("#exportBtn")) return exportData();
      if (e.target.closest("#importBtn")) return el("importFile").click();
      if (e.target.closest("#resetBtn")) {
        if (confirm("Reset everything back to the original plan? Your edits will be lost.")) {
          state = freshFromSeed(); save(); render(); toast("Reset to original ✓");
        }
        return;
      }
      if (e.target.closest("#addCheck")) return addCheckItem();
      const chk = e.target.closest("[data-check]");
      if (chk && !e.target.closest("[data-checkdel]")) {
        const c = state.checklist.find((x) => x.id === chk.dataset.check);
        if (c) { c.done = !c.done; save(); renderInfo(); }
        return;
      }
      const chkDel = e.target.closest("[data-checkdel]");
      if (chkDel) {
        state.checklist = state.checklist.filter((x) => x.id !== chkDel.dataset.checkdel);
        save(); renderInfo(); return;
      }
    });

    // import file
    el("screen").addEventListener("change", (e) => {
      if (e.target.id === "importFile" && e.target.files[0]) importData(e.target.files[0]);
    });
    // enter key on new checklist
    el("screen").addEventListener("keydown", (e) => {
      if (e.target.id === "newCheck" && e.key === "Enter") { e.preventDefault(); addCheckItem(); }
    });
  }

  function addCheckItem() {
    const inp = el("newCheck"); if (!inp) return;
    const v = inp.value.trim(); if (!v) return;
    state.checklist.push({ id: uid(), label: v, done: false });
    save(); renderInfo();
    setTimeout(() => { const n = el("newCheck"); if (n) n.focus(); }, 30);
  }

  function copyText(text) {
    const done = () => toast("Copied: " + text);
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done).catch(() => fallbackCopy(text, done));
    } else fallbackCopy(text, done);
  }
  function fallbackCopy(text, done) {
    const ta = document.createElement("textarea");
    ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
    document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); done(); } catch (e) { toast("Copy failed"); }
    ta.remove();
  }

  /* ---------- boot ---------- */
  function init() {
    state = load();
    wireEvents();
    render();
    setInterval(updateCountdown, 60000);
    // service worker
    if ("serviceWorker" in navigator) {
      window.addEventListener("load", () =>
        navigator.serviceWorker.register("service-worker.js").catch(() => {}));
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
