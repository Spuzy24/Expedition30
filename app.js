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
  const WEATHER_KEY = "exp33.weather.v1";

  // Known trip cities → coords for the weather forecast.
  const CITY_COORDS = {
    Zagreb: [45.813, 15.977],
    Basel: [47.5596, 7.5886],
    Freiburg: [47.999, 7.8421],
    Nancy: [48.6921, 6.1844],
    Strasbourg: [48.5734, 7.7521],
  };

  const DEFAULT_CHECKLIST = [
    "Passports / ID cards",
    "Concert tickets (printed + on phone)",
    "All FlixBus tickets saved offline",
    "Hotel confirmation numbers + PINs",
    "Travel insurance / EHIC card",
    "EUR cash + bank cards",
    "Phone chargers + power bank",
    "Check Nancy concert weather (open-air!)",
  ];

  // One-time, non-destructive upgrades for already-installed phones.
  // Each runs once (tracked by state._mv); never clobbers user edits.
  const MIGRATIONS = [
    function fillBaselBooking(s) {
      const it = (s.items || []).find((i) => i.id === "stay-basel");
      // only replace if it's still the original "not booked" placeholder
      if (it && it.place && it.place.name === "Basel accommodation") {
        const seed = (window.EXP33_SEED.items || []).find((i) => i.id === "stay-basel");
        if (seed) Object.assign(it, clone(seed));
      }
      // tick off the now-satisfied checklist item, if it's still there
      (s.checklist || []).forEach((c) => {
        if (/book basel accommodation/i.test(c.label)) c.done = true;
      });
    },
  ];
  function migrate(s) {
    const from = s._mv || 0;
    for (let i = from; i < MIGRATIONS.length; i++) MIGRATIONS[i](s);
    s._mv = MIGRATIONS.length;
    return s;
  }

  /* ---------- state ---------- */
  let state = null;          // { trip, dayMeta, items, checklist }
  let currentTab = "plan";
  let searchQ = "";          // bookings search query
  let weather = null;        // { [city]: { [date]: { code, tmax, tmin } } }
  let didAutoScroll = false; // scroll-to-today only once per session

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

  function toast(msg, opts) {
    const t = el("toast");
    t.textContent = msg;
    t.classList.toggle("tappable", !!(opts && opts.onTap));
    t.onclick = opts && opts.onTap ? opts.onTap : null;
    t.hidden = false;
    requestAnimationFrame(() => t.classList.add("show"));
    if (navigator.vibrate) navigator.vibrate(10);
    clearTimeout(toast._t);
    toast._t = setTimeout(() => {
      t.classList.remove("show");
      setTimeout(() => (t.hidden = true), 220);
    }, (opts && opts.duration) || 1700);
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
  // 'YYYY-MM-DD' + 'HH:MM' → Date (local time)
  function dt(day, time) {
    const [y, m, d] = day.split("-").map(Number);
    const [h, mi] = (time || "00:00").split(":").map(Number);
    return new Date(y, m - 1, d, h, mi);
  }
  function relDayLabel(day) {
    const t = todayStr();
    if (day === t) return "Today";
    const diff = Math.round((ymd(day) - ymd(t)) / 86400000);
    if (diff === 1) return "Tomorrow";
    return `${dow(day)} ${dayNum(day)} ${monName(day)}`;
  }
  // "in 25 min" / "in 3 h 10 min" / "in 2 d 4 h"
  function fmtRel(ms) {
    const m = Math.max(1, Math.round(ms / 60000));
    if (m < 60) return `${m} min`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h} h${m % 60 ? ` ${m % 60} min` : ""}`;
    const d = Math.floor(h / 24);
    return `${d} d${h % 24 ? ` ${h % 24} h` : ""}`;
  }
  function itemEnd(it) {
    if (it.type === "stay" && it.checkOut)
      return dt(it.checkOut.slice(0, 10), it.checkOut.slice(11) || "12:00");
    if (it.end) return dt(it.endDay || it.day, it.end);
    if (it.start) return new Date(dt(it.day, it.start).getTime() + 90 * 60000); // 1.5 h grace
    return new Date(ymd(it.day).getTime() + 86400000);
  }
  const isBackup = (it) => (it.badges || []).some((b) => /backup|not used/i.test(b));
  function itemPast(it, now) { return itemEnd(it) < now; }
  function itemNow(it, now) {
    if (!it.start || it.type === "stay" || isBackup(it)) return false;
    return dt(it.day, it.start) <= now && now < itemEnd(it);
  }
  // What's happening right now / coming up next (transport, events, activities).
  function nowNext() {
    const now = new Date();
    let current = null, next = null;
    state.items.forEach((it) => {
      if (!it.start || it.type === "stay" || it.type === "note" || isBackup(it)) return;
      const s = dt(it.day, it.start);
      if (itemNow(it, now)) {
        if (!current || s > dt(current.day, current.start)) current = it;
      } else if (s > now) {
        if (!next || s < dt(next.day, next.start)) next = it;
      }
    });
    return { current, next };
  }

  function mapsUrl(loc) {
    if (!loc) return "";
    if (loc.coords && loc.coords.length === 2)
      return `https://www.google.com/maps/search/?api=1&query=${loc.coords[0]},${loc.coords[1]}`;
    const q = [loc.name, loc.address].filter(Boolean).join(" ");
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q)}`;
  }

  /* ---------- weather (Open-Meteo, free, no key; cached for offline) ---------- */
  function cityForDay(day) {
    const meta = state.dayMeta[day];
    if (!meta || !meta.city) return null;
    // the LAST city mentioned is where the evening/night happens
    let best = null, pos = -1;
    Object.keys(CITY_COORDS).forEach((k) => {
      const i = meta.city.lastIndexOf(k);
      if (i > pos) { pos = i; best = k; }
    });
    return best;
  }
  function wxEmoji(c) {
    if (c === 0) return "☀️";
    if (c === 1) return "🌤️";
    if (c === 2) return "⛅";
    if (c === 3) return "☁️";
    if (c === 45 || c === 48) return "🌫️";
    if (c >= 51 && c <= 57) return "🌦️";
    if ((c >= 61 && c <= 67) || (c >= 80 && c <= 82)) return "🌧️";
    if ((c >= 71 && c <= 77) || c === 85 || c === 86) return "🌨️";
    if (c >= 95) return "⛈️";
    return "🌡️";
  }
  function wxForDay(day) {
    const city = cityForDay(day);
    if (!weather || !city || !weather[city] || !weather[city][day]) return null;
    return { city, ...weather[city][day] };
  }
  async function refreshWeather() {
    try {
      const cached = JSON.parse(localStorage.getItem(WEATHER_KEY) || "null");
      if (cached && cached.data) weather = cached.data;
      if (cached && Date.now() - cached.ts < 3 * 3600000) return; // fresh enough
      if (!navigator.onLine) return;

      const today = todayStr();
      const start = state.trip.startDate > today ? state.trip.startDate : today;
      if (start > state.trip.endDate) return; // trip is over

      const days = dateRange(state.trip.startDate, state.trip.endDate);
      const cities = [...new Set(days.map(cityForDay).filter(Boolean))];
      if (!cities.length) return;
      const lat = cities.map((c) => CITY_COORDS[c][0]).join(",");
      const lon = cities.map((c) => CITY_COORDS[c][1]).join(",");
      const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}` +
        `&daily=weather_code,temperature_2m_max,temperature_2m_min` +
        `&timezone=Europe%2FBerlin&start_date=${start}&end_date=${state.trip.endDate}`;
      const res = await fetch(url);
      if (!res.ok) return;
      const json = await res.json();
      const list = Array.isArray(json) ? json : [json];
      const data = {};
      list.forEach((loc, i) => {
        const city = cities[i];
        if (!city || !loc.daily) return;
        data[city] = {};
        loc.daily.time.forEach((d, j) => {
          data[city][d] = {
            code: loc.daily.weather_code[j],
            tmax: Math.round(loc.daily.temperature_2m_max[j]),
            tmin: Math.round(loc.daily.temperature_2m_min[j]),
          };
        });
      });
      weather = data;
      localStorage.setItem(WEATHER_KEY, JSON.stringify({ ts: Date.now(), data }));
      if (currentTab === "plan") renderPlan();
    } catch (e) { /* offline / blocked — day headers just skip the forecast */ }
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
        if (parsed && parsed.items) return migrate(parsed);
      }
    } catch (e) { /* ignore */ }
    return migrate(freshFromSeed());
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
    const now = new Date();
    // the hero card lives at the top of today's section (where auto-scroll lands)
    const heroDay = today < state.trip.startDate ? state.trip.startDate : today;
    let html = "";
    days.forEach((day) => {
      const meta = state.dayMeta[day] || {};
      const items = itemsForDay(day);
      const overnight = overnightFor(day);
      const isToday = day === today;
      const isPastDay = day < today;
      const wx = !isPastDay ? wxForDay(day) : null;
      html += `<section class="day-section" id="day-${day}" data-day="${day}">
        <div class="day-head${isToday ? " is-today" : ""}${isPastDay ? " is-past" : ""}">
          <span class="day-head__date">${dayNum(day)} ${monName(day)}</span>
          <span class="day-head__dow">${dow(day)}</span>
          ${isToday ? `<span class="day-head__today">Today</span>` : ""}
          ${wx ? `<span class="day-head__wx" title="${esc(wx.city)}">${wxEmoji(wx.code)} ${wx.tmax}°</span>` : ""}
          ${meta.city ? `<span class="day-head__city">${esc(meta.city)}</span>` : ""}
        </div>
        ${day === heroDay ? `<div id="nowCard">${nowCardHTML()}</div>` : ""}
        <div class="timeline">`;

      if (items.length === 0) {
        const city = meta.city ? meta.city.split("→").pop().trim() : "";
        const exploreUrl = city
          ? `https://www.google.com/maps/search/${encodeURIComponent("things to do near " + city)}`
          : "";
        html += `<div class="freeday"><span>🌤️</span><span>Free day${city ? " in " + esc(city) : ""}</span>
          ${exploreUrl ? `<a href="${esc(exploreUrl)}" target="_blank" rel="noopener">✨ Explore</a>` : ""}</div>`;
      }
      items.forEach((it) => (html += itemCardHTML(it, now)));

      if (overnight) {
        html += `<div class="overnight"><span>🌙</span><span>Overnight · <b>${esc(overnight.place ? overnight.place.name : overnight.title)}</b></span></div>`;
      }
      html += `</div></section>`;
    });
    el("screen").innerHTML = html;
    observeDays();
    autoScrollToToday(today);
  }

  function autoScrollToToday(today) {
    if (didAutoScroll) return;
    didAutoScroll = true;
    if (today <= state.trip.startDate || today > state.trip.endDate) return;
    const sec = el("day-" + today);
    if (sec) requestAnimationFrame(() => sec.scrollIntoView({ block: "start" }));
  }

  function nowCardHTML() {
    const today = todayStr();
    if (today > state.trip.endDate) return "";
    const { current, next } = nowNext();
    const it = current || next;
    if (!it) return "";
    const t = TYPES[it.type] || TYPES.note;
    const styleVars = `--accent:${t.color};--accent-soft:${soft(t.color)};--accent-line:${line(t.color)}`;
    let when;
    if (current) {
      when = it.end
        ? `until <b>${esc(it.end)}</b>${it.endDay && it.endDay !== it.day ? " (+1)" : ""}`
        : "happening now";
    } else {
      const ms = dt(it.day, it.start) - Date.now();
      when = `${esc(relDayLabel(it.day))} · <b>${esc(it.start)}</b> · in <b>${esc(fmtRel(ms))}</b>`;
    }
    let sub = "";
    if (TRANSPORT.has(it.type) && it.from && it.to)
      sub = `${esc(shortName(it.from.name))} → ${esc(shortName(it.to.name))}`;
    else if (it.place) sub = `📍 ${esc(shortName(it.place.name))}`;
    return `<article class="now-card" data-open="${it.id}" style="${styleVars}">
      <div class="now-card__icon">${t.icon}</div>
      <div class="now-card__body">
        <div class="now-card__label">${current ? `<span class="dot"></span>Happening now` : "Up next"}</div>
        <div class="now-card__title">${esc(it.title)}</div>
        <div class="now-card__when">${when}${sub ? ` · ${sub}` : ""}</div>
      </div>
      <span class="item__chev">›</span>
    </article>`;
  }

  function itemCardHTML(it, now) {
    const t = TYPES[it.type] || TYPES.note;
    const badges = (it.badges || []);
    let cls = "item";
    if (badges.some((b) => /backup|not used/i.test(b))) cls += " is-backup";
    if (badges.some((b) => /book/i.test(b))) cls += " is-todo";
    let done = false;
    if (now) {
      if (itemNow(it, now)) cls += " is-now";
      else if (itemPast(it, now)) { cls += " is-past"; done = true; }
    }
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
      <span class="item__chev${done ? " item__chev--done" : ""}">${done ? "✓" : "›"}</span>
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
      .map((day) => {
        let cls = "datepill";
        if (day === today) cls += " is-active is-today";
        else if (day < today) cls += " is-past";
        return `<button class="${cls}" data-jump="${day}">
        <span class="datepill__dow">${dow(day)}</span>
        <span class="datepill__day">${dayNum(day)}</span>
      </button>`;
      }).join("");
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
  function itemMatches(it, q) {
    const hay = [
      it.title, it.subtitle, it.notes,
      (it.badges || []).join(" "),
      ...(it.info || []).flatMap((f) => [f.label, f.value]),
      ...["from", "to", "place"].map((k) => it[k] && `${it[k].name || ""} ${it[k].address || ""}`),
    ].filter(Boolean).join(" ").toLowerCase();
    return hay.includes(q);
  }

  function renderBookings() {
    const ticketed = state.items
      .filter((i) => i.ticketPdf)
      .sort((a, b) => (a.day + (a.start || "")).localeCompare(b.day + (b.start || "")));
    const strip = ticketed.length
      ? `<div class="tickets-strip">${ticketed.map((it) =>
          `<a class="tchip" href="${esc(it.ticketPdf)}" target="_blank" rel="noopener">🎫 ${esc(shortName(it.title))}</a>`
        ).join("")}</div>`
      : "";
    el("screen").innerHTML = `<div class="fade-in">
      ${strip}
      <div class="searchwrap"><input id="searchInput" type="search" placeholder="Search bookings, seats, numbers…" value="${esc(searchQ)}" autocomplete="off" /></div>
      <div id="bkResults"></div>
    </div>`;
    renderBookingResults();
  }

  function renderBookingResults() {
    const groups = [
      { key: "stay", title: "🏨 Stays", types: ["stay"] },
      { key: "transport", title: "🚌 Transport", types: ["flight", "bus"] },
      { key: "tickets", title: "🎟️ Tickets & Events", types: ["event"] },
      { key: "other", title: "📝 Other", types: ["activity", "note"] },
    ];
    const q = searchQ.trim().toLowerCase();
    let html = q ? "" : `<p class="intro" style="margin-top:12px">Every booking in one place. Tap any card for addresses, maps, seats, confirmation numbers and notes.</p>`;
    let found = 0;
    groups.forEach((g) => {
      const items = state.items
        .filter((i) => g.types.includes(i.type) && (!q || itemMatches(i, q)))
        .sort((a, b) => (a.day + (a.start || "")).localeCompare(b.day + (b.start || "")));
      if (!items.length) return;
      found += items.length;
      html += `<h2 class="group-title">${g.title}<span class="count">${items.length}</span></h2>`;
      items.forEach((it) => (html += itemCardHTML(it)));
    });
    if (q && !found) html += `<div class="empty"><div class="big">🔍</div>Nothing matches “${esc(searchQ)}”.</div>`;
    const box = el("bkResults");
    if (box) box.innerHTML = html;
  }

  /* ============================================================
     INFO TAB
     ============================================================ */
  function money(n) { return "€" + n.toFixed(2); }
  function renderInfo() {
    const t = state.trip;
    const days = dateRange(t.startDate, t.endDate).length;
    // cost buckets
    let stays = 0, transport = 0, tickets = 0, other = 0;
    state.items.forEach((i) => {
      if (!i.price) return;
      if (i.type === "stay") stays += i.price;
      else if (TRANSPORT.has(i.type)) transport += i.price;
      else if (i.type === "event") tickets += i.price;
      else other += i.price;
    });
    const total = stays + transport + tickets + other;
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
        ${other ? `<div class="kv"><span class="k">📍 Other</span><span class="v">${money(other)}</span></div>` : ""}
        <div class="cost-total"><span>Total</span><span>${money(total)}</span></div>
        <div class="kv" style="margin-top:6px"><span class="k">Per person</span><span class="v">${money(total / per)}</span></div>
        <p class="form-hint">Flights aren't priced yet — add the fares on each flight to include them. The Nancy→Basel backup bus isn't double-counted.</p>
      </div>

      <div class="card">
        <h3>✅ Checklist</h3>
        ${state.checklist.length ? `<div class="progress-row">
          <div class="progress"><div class="progress__bar" style="width:${Math.round(100 * state.checklist.filter((c) => c.done).length / state.checklist.length)}%"></div></div>
          <span>${state.checklist.filter((c) => c.done).length}/${state.checklist.length} done</span>
        </div>` : ""}
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
  function sheetOpen() { return !el("sheet").hidden; }
  function openSheet(html) {
    const sheet = el("sheet"), scrim = el("scrim");
    const wasOpen = sheetOpen();
    sheet.innerHTML = `<div class="sheet__grab"></div><div class="sheet__scroll">${html}</div>`;
    sheet.hidden = false; scrim.hidden = false;
    requestAnimationFrame(() => { sheet.classList.add("show"); scrim.classList.add("show"); });
    document.body.style.overflow = "hidden";
    // Android back button (and browser back) closes the sheet instead of the app.
    if (!wasOpen) history.pushState({ sheet: true }, "");
  }
  function closeSheet(fromPop) {
    const sheet = el("sheet"), scrim = el("scrim");
    if (sheet.hidden) return;
    sheet.classList.remove("show"); scrim.classList.remove("show");
    document.body.style.overflow = "";
    setTimeout(() => { sheet.hidden = true; scrim.hidden = true; sheet.innerHTML = ""; sheetMode = null; }, 320);
    if (!fromPop && history.state && history.state.sheet) history.back();
  }

  /* swipe-down on the sheet to dismiss */
  function wireSheetDrag() {
    const sheet = el("sheet");
    let startY = null, dragging = false;
    sheet.addEventListener("touchstart", (e) => {
      const sc = sheet.querySelector(".sheet__scroll");
      if (sc && sc.scrollTop > 4) { startY = null; return; }
      startY = e.touches[0].clientY;
      dragging = false;
    }, { passive: true });
    sheet.addEventListener("touchmove", (e) => {
      if (startY == null) return;
      const dy = e.touches[0].clientY - startY;
      if (dy > 8) {
        dragging = true;
        sheet.style.transition = "none";
        sheet.style.transform = `translateY(${dy}px)`;
      }
    }, { passive: true });
    sheet.addEventListener("touchend", (e) => {
      if (startY == null) return;
      const dy = e.changedTouches[0].clientY - startY;
      sheet.style.transition = "";
      sheet.style.transform = "";
      if (dragging && dy > 90) closeSheet();
      startY = null; dragging = false;
    });
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

    // notes — tap to edit in place
    html += `<div class="sheet__section-label">Notes <span class="label-hint">· tap to edit</span></div>`;
    html += it.notes
      ? `<div class="notes-display" data-editnotes="${it.id}">${esc(it.notes)}</div>`
      : `<div class="notes-display notes-empty" data-editnotes="${it.id}">No notes yet — tap to add some.</div>`;

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

  function openNotesEditor(id) {
    const it = getItem(id);
    const disp = el("sheet").querySelector("[data-editnotes]");
    if (!it || !disp) return;
    const wrap = document.createElement("div");
    wrap.innerHTML = `<textarea class="notes-ta" placeholder="Anything to remember…">${esc(it.notes || "")}</textarea>
      <div class="btn-row" style="margin-top:8px">
        <button class="btn btn--ghost" data-notescancel="${it.id}">Cancel</button>
        <button class="btn btn--gold" data-notessave="${it.id}">Save notes</button>
      </div>`;
    disp.replaceWith(wrap);
    const ta = wrap.querySelector("textarea");
    ta.focus();
    ta.setSelectionRange(ta.value.length, ta.value.length);
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
    const stayVals = () => ({
      checkIn: val("f_checkin") || (it.checkIn || "").replace(" ", "T"),
      checkOut: val("f_checkout") || (it.checkOut || "").replace(" ", "T"),
    });

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

      <div id="locFields">${locFieldsHTML(it.type, from, to, place, stayVals())}</div>

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
      $("#locFields").innerHTML = locFieldsHTML(type, readLoc("from"), readLoc("to"), readLoc("place"), stayVals());
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

  function locFieldsHTML(type, from, to, place, stay) {
    if (TRANSPORT.has(type)) {
      return `<div class="field"><label>From — name</label><input id="f_from_name" value="${esc(from.name)}" placeholder="Origin station / airport" /></div>
        <div class="field"><label>From — address</label><input id="f_from_addr" value="${esc(from.address || "")}" placeholder="Street, city" /></div>
        <div class="field"><label>To — name</label><input id="f_to_name" value="${esc(to.name)}" placeholder="Destination" /></div>
        <div class="field"><label>To — address</label><input id="f_to_addr" value="${esc(to.address || "")}" placeholder="Street, city" /></div>`;
    }
    let html = `<div class="field"><label>Place — name</label><input id="f_place_name" value="${esc(place.name)}" placeholder="Hotel / venue / spot" /></div>
      <div class="field"><label>Place — address</label><input id="f_place_addr" value="${esc(place.address || "")}" placeholder="Street, city (used for the map pin)" /></div>`;
    if (type === "stay") {
      html += `<div class="field-2">
        <div class="field"><label>Check-in</label><input type="datetime-local" id="f_checkin" value="${esc((stay && stay.checkIn) || "")}" /></div>
        <div class="field"><label>Check-out</label><input type="datetime-local" id="f_checkout" value="${esc((stay && stay.checkOut) || "")}" /></div>
      </div>`;
    }
    return html;
  }
  function miniPair(kind, i, a, b) {
    return `<div class="mini-row" data-kind="${kind}">
      <input class="mp-a" value="${esc(a || "")}" placeholder="Label" />
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
      if (type === "stay") {
        const ci = val("f_checkin"), co = val("f_checkout");
        item.checkIn = ci ? ci.replace("T", " ") : prev.checkIn;
        item.checkOut = co ? co.replace("T", " ") : prev.checkOut;
        if (item.checkOut) item.endDay = item.checkOut.slice(0, 10);
        else if (prev.endDay != null) item.endDay = prev.endDay;
        if (item.checkIn && item.checkOut) {
          const n = Math.round((ymd(item.checkOut.slice(0, 10)) - ymd(item.checkIn.slice(0, 10))) / 86400000);
          item.nights = Math.max(1, n);
        } else if (prev.nights != null) item.nights = prev.nights;
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
  async function exportData() {
    const json = JSON.stringify(state, null, 2);
    // native share sheet first — easiest way to AirDrop/WhatsApp it to the other phone
    try {
      const file = new File([json], "expedition33-plan.json", { type: "application/json" });
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({ files: [file], title: "Expedition 33 plan" });
        toast("Shared ✓");
        return;
      }
    } catch (e) {
      if (e && e.name === "AbortError") return; // user cancelled the share sheet
    }
    const blob = new Blob([json], { type: "application/json" });
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
    el("scrim").addEventListener("click", () => closeSheet());
    // countdown chip → open the concert details
    el("countdown").addEventListener("click", () => {
      const ev = state.items.find((i) => i.type === "event") || getItem("concert");
      if (ev) showDetail(ev.id);
    });
    // back button / swipe-back closes the sheet instead of leaving the app
    window.addEventListener("popstate", () => { if (sheetOpen()) closeSheet(true); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && sheetOpen()) closeSheet(); });
    wireSheetDrag();
    // connectivity heads-up
    window.addEventListener("offline", () => toast("📴 Offline — everything still works"));
    window.addEventListener("online", () => { toast("📶 Back online"); refreshWeather(); });

    // global click delegation (cards, sheet buttons, info actions)
    document.addEventListener("click", (e) => {
      const open = e.target.closest("[data-open]");
      if (open && !el("sheet").contains(open)) { showDetail(open.dataset.open); return; }

      const copy = e.target.closest("[data-copy]");
      if (copy) { copyText(copy.dataset.copy); return; }

      const edit = e.target.closest("[data-edit]");
      if (edit) { showForm(edit.dataset.edit); return; }

      // inline notes editing in the detail sheet
      const editNotes = e.target.closest("[data-editnotes]");
      if (editNotes) { openNotesEditor(editNotes.dataset.editnotes); return; }
      const notesSave = e.target.closest("[data-notessave]");
      if (notesSave) {
        const it = getItem(notesSave.dataset.notessave);
        const ta = el("sheet").querySelector(".notes-ta");
        if (it && ta) { it.notes = ta.value.trim(); save(); toast("Notes saved ✓"); showDetail(it.id); }
        return;
      }
      const notesCancel = e.target.closest("[data-notescancel]");
      if (notesCancel) { showDetail(notesCancel.dataset.notescancel); return; }

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
    // bookings search (re-renders results only, keeps the input focused)
    el("screen").addEventListener("input", (e) => {
      if (e.target.id !== "searchInput") return;
      searchQ = e.target.value;
      clearTimeout(wireEvents._sq);
      wireEvents._sq = setTimeout(renderBookingResults, 120);
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
    save(); // persist any one-time migrations applied during load
    wireEvents();
    render();
    refreshWeather();
    // keep the countdown + "up next" card live
    setInterval(() => {
      updateCountdown();
      if (currentTab === "plan") {
        const nc = el("nowCard");
        if (nc) nc.innerHTML = nowCardHTML();
      }
    }, 30000);
    // service worker (+ "update ready" prompt)
    if ("serviceWorker" in navigator) {
      window.addEventListener("load", () =>
        navigator.serviceWorker.register("service-worker.js").then((reg) => {
          reg.addEventListener("updatefound", () => {
            const w = reg.installing;
            if (!w) return;
            w.addEventListener("statechange", () => {
              if (w.state === "installed" && navigator.serviceWorker.controller)
                toast("✨ Update ready — tap to refresh", { duration: 8000, onTap: () => location.reload() });
            });
          });
        }).catch(() => {}));
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
