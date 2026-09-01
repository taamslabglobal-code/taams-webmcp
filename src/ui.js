/**
 * TAAMs Import Sourcing Desk -- display layer.
 *
 * This module owns every pixel that changes on screen. It is deliberately
 * the ONLY place that touches the DOM for product/comparison/supplier/RFQ
 * state, so that a human clicking a button and an agent calling a WebMCP
 * tool run through the exact same functions -- there is no second code
 * path. index.html wires the search box to renderProduct; a WebMCP
 * tool file wires registerTool handlers to the rest of this object.
 *
 * State lives only in this module (a Map cache + a couple of arrays), not
 * scattered across the page -- so both the human click-path and the agent
 * tool-path always see the same truth.
 */

const KR_TO_EN = {
  '\uBCA0\uD2B8\uB0A8': 'vietnam', '\uD0DC\uAD6D': 'thailand', '\uC911\uAD6D': 'china', '\uBBF8\uAD6D': 'united states',
  '\uD398\uB8E8': 'peru', '\uCE60\uB808': 'chile', '\uD544\uB9AC\uD540': 'philippines', '\uC778\uB3C4\uB124\uC2DC\uC544': 'indonesia',
  '\uC778\uB3C4': 'india', '\uB300\uB9CC': 'taiwan', '\uC77C\uBCF8': 'japan', '\uD638\uC8FC': 'australia',
  '\uB274\uC9C8\uB79C\uB4DC': 'new zealand', '\uBA55\uC2DC\uCF54': 'mexico', '\uBE0C\uB77C\uC9C8': 'brazil', '\uCE90\uB098\uB2E4': 'canada',
  '\uC774\uD0C8\uB9AC\uC544': 'italy', '\uD504\uB791\uC2A4': 'france', '\uB3C5\uC77C': 'germany', '\uC2A4\uD398\uC778': 'spain',
  '\uB124\uB35C\uB780\uB4DC': 'netherlands', '\uC5D0\uCFA4\uB3C4\uB974': 'ecuador', '\uC544\uB974\uD5E8\uD2F0\uB098': 'argentina',
  '\uB9D0\uB808\uC774\uC2DC\uC544': 'malaysia', '\uBBF8\uC580\uB9C8': 'myanmar', '\uCE84\uBCF4\uB514\uC544': 'cambodia', '\uB7EC\uC2DC\uC544': 'russia',
  '\uB178\uB974\uC6E8\uC774': 'norway', '\uB0A8\uC544\uACF5': 'south africa', '\uC774\uC9D1\uD2B8': 'egypt', '\uD130\uD0A4': 'turkey',
  '\uC6B0\uC988\uBCA0\uD0A4\uC2A4\uD0C4': 'uzbekistan', '\uD30C\uD0A4\uC2A4\uD0C4': 'pakistan', '\uC2A4\uB9AC\uB791\uCE74': 'sri lanka',
  '\uBC29\uAE00\uB77C\uB370\uC2DC': 'bangladesh', '\uC2F1\uAC00\uD3EC\uB974': 'singapore', '\uC601\uAD6D': 'united kingdom',
};

const cache = new Map();
let pinned = [];
let focusName = null;
let currentHighlight = '';

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
    var map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
    return map[c];
  });
}

function titleCase(s) {
  return s.replace(/\b\w/g, function (c) { return c.toUpperCase(); });
}

function countryKey(raw) {
  var t = String(raw || '').trim();
  if (!t) return '';
  if (KR_TO_EN[t]) return KR_TO_EN[t];
  var low = t.toLowerCase();
  if (low === 'usa' || low === 'us' || low === 'u.s.a.') return 'united states';
  if (low === 'uk') return 'united kingdom';
  return low;
}

/**
 * English first, Korean in parentheses. The data arrives keyed on Korean names
 * and those stay the lookup key everywhere, but this page is read in English —
 * so the English label leads and the Korean one is kept alongside rather than
 * dropped, since it is what the customs records actually say.
 */
function countryLabel(raw) {
  var en = KR_TO_EN[raw];
  return en ? (titleCase(en) + ' (' + raw + ')') : String(raw || '');
}

function moneyPerKg(v) {
  var n = Number(v);
  return (isFinite(n) && n > 0) ? ('$' + n.toFixed(2) + '/kg') : '\u2014';
}

function normalizeExporter(item) {
  item = item || {};
  return {
    // The field is `supplier`. It was worth checking rather than guessing: a
    // fallback chain like this never throws, so a wrong key renders as a page
    // full of "Unknown supplier" — which is what shipped until someone looked
    // at the screen. Keep the alternatives, but keep the real one first.
    name: item.supplier || item.exporter || item.name || item.factory
      || item.factory_name || item.company || 'Unknown supplier',
    country: item.country || item.exporter_country || '',
    count: Number(item.cnt != null ? item.cnt : (item.count != null ? item.count : (item.clearance_count != null ? item.clearance_count : (item.clearances || 0)))) || 0,
    hasLocation: !!(item.has_location || item.hasLocation),
  };
}

function normalizeImporter(item) {
  item = item || {};
  return {
    name: item.importer || item.name || 'Unknown importer',
    nameEn: item.importer_en || item.name_en || '',
    country: item.country || '',
    count: Number(item.cnt != null ? item.cnt : (item.count || 0)) || 0,
  };
}

/**
 * Accept the data shape two different ways: the flat contract shape
 * ({nameEn, price:Number, trend:Array, exporters:Array, importers:Array})
 * that index.html's own search wiring builds, OR raw TAAMs API responses
 * passed straight through (price = full priceDashboard() object, exporters
 * = full topExporters() object with .items/.country_totals/.exporter_total).
 * A WebMCP tool file may reasonably do the latter to avoid re-shaping
 * server responses -- this module must not crash either way.
 */
function normalizeProductData(raw) {
  raw = raw || {};
  var priceObj = (raw.price && typeof raw.price === 'object') ? raw.price : null;
  var exportersRaw = raw.exporters;
  var exportersWrapped = exportersRaw && !Array.isArray(exportersRaw) && typeof exportersRaw === 'object';
  var exportersArr = Array.isArray(exportersRaw) ? exportersRaw : (exportersWrapped ? (exportersRaw.items || []) : []);

  var priceNum = priceObj ? Number(priceObj.current_avg) : (raw.price != null ? Number(raw.price) : NaN);
  var trend = Array.isArray(raw.trend) ? raw.trend : ((priceObj && Array.isArray(priceObj.weekly)) ? priceObj.weekly : []);
  var nameEn = raw.nameEn || (priceObj && priceObj.item_en) || '';
  var priceEligible = raw.priceEligible || (priceObj && priceObj.price_eligible) || null;
  var countries = Array.isArray(raw.countries) ? raw.countries : ((priceObj && Array.isArray(priceObj.countries)) ? priceObj.countries : []);
  var countryTotals = (raw.countryTotals && Object.keys(raw.countryTotals).length)
    ? raw.countryTotals
    : ((exportersWrapped && exportersRaw.country_totals) || {});
  var exporterTotal = raw.exporterTotal != null
    ? raw.exporterTotal
    : ((exportersWrapped && exportersRaw.exporter_total != null) ? exportersRaw.exporter_total : exportersArr.length);

  return {
    nameEn: nameEn,
    price: (isFinite(priceNum) && priceNum > 0) ? priceNum : null,
    priceEligible: priceEligible,
    priceWithheldReason: raw.priceWithheldReason || null,
    trend: trend,
    countries: countries,
    exporters: exportersArr,
    countryTotals: countryTotals,
    exporterTotal: exporterTotal,
    importers: Array.isArray(raw.importers) ? raw.importers : [],
  };
}

function buildSparkline(trend, opts) {
  var width = (opts && opts.width) || 280;
  var height = (opts && opts.height) || 64;
  var showAvg = !opts || opts.showAvg !== false;
  var pts = (trend || [])
    .map(function (p) { return { value: Number(p && p.avg_price) }; })
    .filter(function (p) { return isFinite(p.value) && p.value > 0; });

  if (pts.length < 2) {
    return '<svg viewBox="0 0 ' + width + ' ' + height + '" width="' + width + '" height="' + height + '" class="spark spark-empty">'
      + '<text x="8" y="' + (height / 2) + '" fill="#94a3b8" font-size="11">Not enough price data yet</text></svg>';
  }

  var values = pts.map(function (p) { return p.value; });
  var min = Math.min.apply(null, values);
  var max = Math.max.apply(null, values);
  var span = (max - min) || 1;
  var pad = 8;
  var stepX = (width - pad * 2) / (pts.length - 1);
  var toY = function (v) { return height - pad - ((v - min) / span) * (height - pad * 2); };
  var coords = pts.map(function (p, i) { return [pad + i * stepX, toY(p.value)]; });
  var path = coords.map(function (c, i) { return (i === 0 ? 'M' : 'L') + c[0].toFixed(1) + ',' + c[1].toFixed(1); }).join(' ');
  var avg = values.reduce(function (a, b) { return a + b; }, 0) / values.length;
  var last = coords[coords.length - 1];

  var svg = '<svg viewBox="0 0 ' + width + ' ' + height + '" width="' + width + '" height="' + height + '" class="spark">';
  if (showAvg) {
    var avgY = toY(avg).toFixed(1);
    svg += '<line x1="' + pad + '" y1="' + avgY + '" x2="' + (width - pad) + '" y2="' + avgY + '" stroke="#dc2626" stroke-width="1" stroke-dasharray="3,3" />';
  }
  svg += '<path d="' + path + '" fill="none" stroke="#1d4ed8" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />';
  svg += '<circle cx="' + last[0].toFixed(1) + '" cy="' + last[1].toFixed(1) + '" r="3.2" fill="#1d4ed8" />';
  svg += '</svg>';
  return svg;
}

function logLine(text, kind) {
  var log = document.getElementById('activityLog');
  if (!log) return;
  var li = document.createElement('li');
  li.className = 'log-entry log-' + kind;
  // Pin the locale. Left to the browser default this renders in whatever
  // language the viewer's machine is set to, dropping e.g. Korean AM/PM markers
  // into an otherwise English page depending on who is looking at it.
  var time = new Date().toLocaleTimeString('en-GB', {
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  });
  var icon = kind === 'agent' ? '\u{1F916}' : '\u{1F5B1}\uFE0F';
  li.innerHTML = '<span class="log-icon">' + icon + '</span><span class="log-time">' + time + '</span><span class="log-text">' + esc(text) + '</span>';
  log.appendChild(li);
  log.scrollTop = log.scrollHeight;
  var dot = document.getElementById('activityDot');
  if (dot) {
    dot.classList.remove('pulse');
    void dot.offsetWidth;
    dot.classList.add('pulse');
  }
}
function agentSays(text) { logLine(text, 'agent'); }
function humanLog(text) { logLine(text, 'human'); }

function setBusy(on) {
  document.body.classList.toggle('is-busy', !!on);
  var bar = document.getElementById('busyBar');
  if (bar) bar.classList.toggle('active', !!on);
  var input = document.getElementById('searchInput');
  if (input) input.disabled = !!on;
}

function paintProductCard(name, data) {
  var emptyEl = document.getElementById('productEmpty');
  if (emptyEl) emptyEl.classList.add('hidden');
  var card = document.getElementById('productCard');
  if (!card) return;
  card.classList.remove('hidden');

  // Primary slot carries the English label when there is one; the Korean
  // canonical sits beside it. Falls back to Korean alone rather than showing an
  // empty headline for a product with no English name on record.
  document.getElementById('productNamePrimary').textContent = data.nameEn || name;
  document.getElementById('productNameSecondary').textContent = data.nameEn ? name : '';
  document.getElementById('productPrice').textContent = moneyPerKg(data.price);

  var note = document.getElementById('priceNote');
  if (note) {
    if (data.priceWithheldReason) {
      note.textContent = data.priceWithheldReason;
      note.classList.remove('hidden');
    } else {
      note.textContent = '';
      note.classList.add('hidden');
    }
  }

  var spark = document.getElementById('priceSparkline');
  if (spark) spark.innerHTML = buildSparkline(data.trend, { width: 300, height: 72 });

  var pinBtn = document.getElementById('pinBtn');
  if (pinBtn) {
    // The button pins the product as a whole; a country-scoped card for the
    // same product does not make it look already-pinned.
    if (pinned.some(function (p) { return p.name === name && !p.country; })) {
      pinBtn.textContent = 'Pinned \u2713';
      pinBtn.disabled = true;
    } else {
      pinBtn.textContent = '+ Pin to comparison board';
      pinBtn.disabled = false;
    }
  }

  var list = document.getElementById('importerList');
  if (list) {
    var importers = (data.importers || []).map(normalizeImporter);
    if (importers.length) {
      list.innerHTML = importers.slice(0, 12).map(function (imp) {
        return '<li><span class="imp-name">' + esc(imp.nameEn || imp.name)
          + (imp.nameEn ? '<span class="imp-name-en">' + esc(imp.name) + '</span>' : '')
          + '</span><span class="imp-country">' + esc(countryLabel(imp.country)) + '</span>'
          + '<span class="imp-count">' + imp.count + '</span></li>';
      }).join('');
    } else {
      list.innerHTML = '<li class="empty-row">No Korean importers found in the last 12 months.</li>';
    }
  }
}

function paintSupplierPanel(name, data) {
  var label = document.getElementById('supplierProductLabel');
  if (label) label.textContent = data.nameEn ? (data.nameEn + ' \u00B7 ' + name) : name;

  var exporters = (data.exporters || []).map(normalizeExporter);
  var totals = (data.countryTotals && Object.keys(data.countryTotals).length)
    ? data.countryTotals
    : exporters.reduce(function (acc, e) {
      if (e.country) acc[e.country] = (acc[e.country] || 0) + e.count;
      return acc;
    }, {});

  var chips = document.getElementById('countryChips');
  if (chips) {
    var sorted = Object.entries(totals).sort(function (a, b) { return b[1] - a[1]; });
    chips.innerHTML = '<button class="chip chip-all" data-action="clear-highlight">All countries</button>'
      + sorted.map(function (pair) {
        var country = pair[0], count = pair[1];
        return '<button class="chip" data-action="highlight" data-country="' + esc(country) + '">'
          + esc(countryLabel(country)) + ' <span class="chip-count">' + count + '</span></button>';
      }).join('');
  }

  var tbody = document.getElementById('exporterTableBody');
  if (tbody) {
    if (exporters.length) {
      // Mango alone has 125 suppliers. Rendering every one turns the page into
      // a wall nobody scrolls and pushes the comparison board off screen, so
      // show the head of the ranked list and say plainly how many were cut.
      // Highlighting still runs over the rows that are here.
      var VISIBLE = 25;
      var shown = exporters.slice(0, VISIBLE);
      tbody.innerHTML = shown.map(function (e) {
        return '<tr data-country="' + esc(e.country) + '">'
          + '<td class="td-country">' + esc(countryLabel(e.country)) + '</td>'
          + '<td class="td-name">' + esc(e.name) + (e.hasLocation ? '<span class="loc-badge" title="Verified factory location on file">[loc]</span>' : '') + '</td>'
          + '<td class="td-count">' + e.count + '</td>'
          + '<td class="td-action"><button class="btn-mini" data-action="request-quote" data-supplier="' + esc(e.name) + '">Quote</button></td>'
          + '</tr>';
      }).join('');
      if (exporters.length > VISIBLE) {
        tbody.innerHTML += '<tr class="more-row"><td colspan="4">Showing the top '
          + VISIBLE + ' of ' + exporters.length + ' suppliers, ranked by clearances.'
          + '</td></tr>';
      }
    } else {
      tbody.innerHTML = '<tr><td colspan="4" class="empty-row">No supplier data for this product.</td></tr>';
    }
  }
}

function paintComparisonBoard() {
  var board = document.getElementById('comparisonBoard');
  if (!board) return;
  board.innerHTML = '';

  pinned.forEach(function (p) {
    var name = p.name;
    var data = cache.get(name) || {};
    var row = countryOf(name, p.country);          // null for a whole-product card
    var key = pinKey(name, p.country);

    // exporterTotal is the clearance count, not a headcount of suppliers. Using
    // it here labelled "suppliers" claimed 4,368 companies where there are 125.
    var supplierCount, clearanceTotal, price, trend, title;
    if (row) {
      var want = countryKey(p.country);
      supplierCount = (data.exporters || []).filter(function (e) {
        return countryKey(normalizeExporter(e).country) === want;
      }).length;
      clearanceTotal = (data.countryTotals || {})[row.name];
      price = row.avg_price;
      // Per-country weekly prices come as bare numbers, sometimes with nulls
      // for weeks that country shipped nothing.
      trend = (row.weekly_prices || [])
        .filter(function (v) { return v != null; })
        .map(function (v) { return { avg_price: v }; });
      title = (data.nameEn || name) + ' &middot; ' + esc(titleCase(want));
    } else {
      supplierCount = data.exporters ? data.exporters.length : 0;
      clearanceTotal = data.exporterTotal != null ? data.exporterTotal : null;
      price = data.price;
      trend = data.trend;
      title = esc(data.nameEn || name)
        + (data.nameEn ? '<span class="compare-name-en">' + esc(name) + '</span>' : '');
    }

    var card = document.createElement('div');
    card.className = 'compare-card' + (name === focusName ? ' is-focused' : '');
    card.dataset.action = 'focus-pinned';
    card.dataset.name = name;
    card.dataset.key = key;
    card.tabIndex = 0;
    card.setAttribute('role', 'button');
    card.innerHTML = '<button class="compare-remove" data-action="unpin" data-key="' + esc(key) + '" title="Remove" aria-label="Remove">x</button>'
      + '<div class="compare-name">' + title + '</div>'
      + '<div class="compare-price">' + moneyPerKg(price) + '</div>'
      + '<div class="compare-spark">' + buildSparkline(trend, { width: 160, height: 40, showAvg: false }) + '</div>'
      + '<div class="compare-suppliers">' + supplierCount + ' supplier' + (supplierCount === 1 ? '' : 's')
      + (clearanceTotal ? ' &middot; ' + clearanceTotal.toLocaleString() + ' clearances' : '') + '</div>';
    board.appendChild(card);
  });

  var remaining = Math.max(0, 3 - pinned.length);
  for (var i = 0; i < remaining; i++) {
    var slot = document.createElement('div');
    slot.className = 'compare-slot-empty';
    if (pinned.length === 0 && i === 0) slot.textContent = 'Pinned products will appear here (up to 3).';
    board.appendChild(slot);
  }
}

/** Stable key for one card: a product, optionally narrowed to one country. */
function pinKey(name, country) {
  return name + '|' + countryKey(country || '');
}

/** Human-readable card labels, for tool replies. */
function pinnedLabels() {
  return pinned.map(function (p) {
    var d = cache.get(p.name) || {};
    var base = d.nameEn || p.name;
    return p.country ? (base + ' (' + titleCase(countryKey(p.country)) + ')') : base;
  });
}

/** The country row inside a product's price breakdown, matched across scripts. */
function countryOf(name, country) {
  var d = cache.get(name);
  if (!d || !country) return null;
  var want = countryKey(country);
  return (d.countries || []).find(function (c) { return countryKey(c.name) === want; }) || null;
}

function unpin(key) {
  pinned = pinned.filter(function (p) { return pinKey(p.name, p.country) !== key; });
  paintComparisonBoard();
  if (focusName) {
    var data = cache.get(focusName);
    if (data) paintProductCard(focusName, data);
  }
}

function paint(name) {
  focusName = name;
  var data = cache.get(name);
  if (!data) return;
  paintProductCard(name, data);
  paintSupplierPanel(name, data);
  currentHighlight = '';
  paintComparisonBoard();
}

function setRfqStatus(text, cls) {
  var el = document.getElementById('rfqStatus');
  if (!el) return;
  el.textContent = text;
  el.className = 'rfq-status ' + (cls || '');
}

function ensureRfqSendButton(show) {
  var card = document.getElementById('rfqCard');
  if (!card) return;
  var btn = document.getElementById('rfqSendBtn');
  if (show) {
    if (!btn) {
      btn = document.createElement('button');
      btn.id = 'rfqSendBtn';
      btn.className = 'btn btn-primary rfq-send-btn';
      btn.dataset.action = 'rfq-review-send';
      btn.textContent = 'Review & send';
      card.appendChild(btn);
    }
    btn.classList.remove('hidden');
  } else if (btn) {
    btn.classList.add('hidden');
  }
}

function showRfqCard(draft, statusText, statusClass) {
  var card = document.getElementById('rfqCard');
  if (!card) return;
  card.classList.remove('hidden');
  document.getElementById('rfqProduct').textContent = draft.productName || '\u2014';
  document.getElementById('rfqSupplier').textContent = draft.supplierName || 'Not specified';
  document.getElementById('rfqQty').textContent = draft.quantity || '\u2014';
  document.getElementById('rfqNotes').textContent = draft.notes || '\u2014';
  ensureRfqSendButton(false);
  setRfqStatus(statusText, statusClass || 'pending');
}

function revealRfqDraftForm(productName, supplierName) {
  var card = document.getElementById('rfqCard');
  if (!card) return;
  card.classList.remove('hidden');
  document.getElementById('rfqProduct').textContent = productName || '\u2014';
  document.getElementById('rfqSupplier').textContent = supplierName || 'Not specified yet';
  document.getElementById('rfqQty').innerHTML = '<input type="text" id="rfqQtyInput" placeholder="e.g. 2 x 20ft containers">';
  document.getElementById('rfqNotes').innerHTML = '<textarea id="rfqNotesInput" rows="2" placeholder="Target price, delivery timing, certifications..."></textarea>';
  ensureRfqSendButton(true);
  setRfqStatus('Fill in the details, then review.', 'editing');
  card.dataset.productName = productName || '';
  card.dataset.supplierName = supplierName || '';
  card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function openMailto(draft) {
  var subject = 'Sourcing inquiry: ' + (draft.productName || '');
  var body = [
    'Product: ' + (draft.productName || '-'),
    'Supplier: ' + (draft.supplierName || '(not specified)'),
    'Quantity: ' + (draft.quantity || '-'),
    'Notes: ' + (draft.notes || '-'),
    '',
    '-- sent from TAAMs Import Sourcing Desk',
  ].join('\n');
  var url = 'mailto:support@taamsglobal.com?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
  window.open(url, '_blank');
}

function submitRfqDraftForm() {
  var card = document.getElementById('rfqCard');
  if (!card) return;
  var qtyInput = document.getElementById('rfqQtyInput');
  var notesInput = document.getElementById('rfqNotesInput');
  var draft = {
    productName: card.dataset.productName || '',
    supplierName: card.dataset.supplierName || '',
    quantity: ((qtyInput && qtyInput.value) || '').trim(),
    notes: ((notesInput && notesInput.value) || '').trim(),
  };
  confirmRfq(draft).then(function (approved) {
    if (approved) {
      openMailto(draft);
      markRfqSent(draft);
      humanLog('You approved the sourcing request for "' + draft.productName + '".');
    } else {
      humanLog('You cancelled the sourcing request.');
    }
  });
}

function openRfqModal(draft, cb) {
  var overlay = document.getElementById('rfqModal');
  if (!overlay) { cb(false); return; }
  document.getElementById('rfqModalProduct').textContent = draft.productName || '\u2014';
  document.getElementById('rfqModalSupplier').textContent = draft.supplierName || 'Not specified yet';
  document.getElementById('rfqModalQty').textContent = draft.quantity || '\u2014';
  document.getElementById('rfqModalNotes').textContent = draft.notes || '\u2014';
  overlay.classList.remove('hidden');
  overlay.setAttribute('aria-hidden', 'false');

  var approveBtn = document.getElementById('rfqApprove');
  var cancelBtn = document.getElementById('rfqCancel');

  function cleanup(result) {
    overlay.classList.add('hidden');
    overlay.setAttribute('aria-hidden', 'true');
    approveBtn.removeEventListener('click', onApprove);
    cancelBtn.removeEventListener('click', onCancel);
    overlay.removeEventListener('click', onOverlay);
    document.removeEventListener('keydown', onKey);
    cb(result);
  }
  function onApprove() { cleanup(true); }
  function onCancel() { cleanup(false); }
  function onOverlay(e) { if (e.target === overlay) cleanup(false); }
  function onKey(e) { if (e.key === 'Escape') cleanup(false); }

  approveBtn.addEventListener('click', onApprove);
  cancelBtn.addEventListener('click', onCancel);
  overlay.addEventListener('click', onOverlay);
  document.addEventListener('keydown', onKey);
  approveBtn.focus();
}

function renderProduct(name, data) {
  cache.set(name, normalizeProductData(data));
  paint(name);
}

function isLoaded(name) {
  return cache.has(name);
}

/**
 * Pin one card. A card is a product, optionally narrowed to a single sourcing
 * country -- so ("망고", "Thailand") and ("망고", "Brazil") are two cards.
 *
 * That second argument exists because the most ordinary question a buyer asks
 * is "this origin or that one?", and a board keyed on product alone cannot
 * hold that question at all: you would be pinning the same product twice.
 */
function pinToBoard(name, country) {
  country = country || '';
  if (!cache.has(name)) {
    return { ok: false, pinned: pinnedLabels(), reason: '"' + name + '" has not been loaded yet -- load its price trend first.' };
  }
  if (country && !countryOf(name, country)) {
    return { ok: false, pinned: pinnedLabels(),
      reason: '"' + country + '" is not one of the sourcing countries on record for ' + name + '.' };
  }
  if (pinned.some(function (p) { return p.name === name && countryKey(p.country) === countryKey(country); })) {
    return { ok: true, pinned: pinnedLabels() };
  }
  if (pinned.length >= 3) {
    return { ok: false, pinned: pinnedLabels(), reason: 'Comparison board is full (max 3) -- unpin one first.' };
  }
  pinned.push({ name: name, country: country });
  paintComparisonBoard();
  if (name === focusName) {
    var data = cache.get(name);
    if (data) paintProductCard(name, data);
  }
  return { ok: true, pinned: pinnedLabels() };
}

function highlightCountry(country) {
  currentHighlight = (country || '').trim();
  var rows = document.querySelectorAll('#exporterTableBody tr[data-country]');
  var matched = 0;
  rows.forEach(function (tr) {
    if (!currentHighlight) {
      tr.classList.remove('row-highlight', 'row-dim');
      return;
    }
    if (countryKey(tr.dataset.country) === countryKey(currentHighlight)) {
      tr.classList.add('row-highlight');
      tr.classList.remove('row-dim');
      matched++;
    } else {
      tr.classList.add('row-dim');
      tr.classList.remove('row-highlight');
    }
  });
  document.querySelectorAll('#countryChips .chip[data-country]').forEach(function (c) {
    var active = !!currentHighlight && countryKey(c.dataset.country) === countryKey(currentHighlight);
    c.classList.toggle('chip-active', active);
  });
  return { ok: true, matched: matched };
}

function confirmRfq(draft) {
  showRfqCard(draft, 'Waiting for your approval\u2026', 'pending');
  return new Promise(function (resolve) {
    openRfqModal(draft, function (approved) {
      if (!approved) setRfqStatus('Cancelled \u2014 nothing was sent.', 'cancelled');
      resolve(approved);
    });
  });
}

function markRfqSent(draft) {
  showRfqCard(draft, 'Sent \u2014 a pre-filled email opened in your mail client.', 'sent');
}

export const UI = {
  agentSays: agentSays,
  setBusy: setBusy,
  renderProduct: renderProduct,
  isLoaded: isLoaded,
  pinToBoard: pinToBoard,
  highlightCountry: highlightCountry,
  confirmRfq: confirmRfq,
  markRfqSent: markRfqSent,
};

document.addEventListener('click', function (e) {
  var el = e.target.closest('[data-action]');
  if (!el) return;
  var action = el.dataset.action;

  if (action === 'pin') {
    if (!focusName) return;
    var r = pinToBoard(focusName);
    humanLog(r.ok ? ('You pinned "' + focusName + '" to the comparison board.') : ('Could not pin: ' + r.reason));
  } else if (action === 'unpin') {
    var key = el.dataset.key;
    unpin(key);
    humanLog('You removed a card from the comparison board.');
  } else if (action === 'highlight') {
    var country = el.dataset.country;
    var hr = highlightCountry(country);
    humanLog('You focused on ' + country + ' \u2014 ' + hr.matched + ' supplier' + (hr.matched === 1 ? '' : 's') + ' matched.');
  } else if (action === 'clear-highlight') {
    highlightCountry('');
    humanLog('You cleared the country focus.');
  } else if (action === 'focus-pinned') {
    var pname = el.dataset.name;
    if (cache.has(pname)) { paint(pname); humanLog('You switched focus to "' + pname + '".'); }
  } else if (action === 'request-quote') {
    if (!focusName) return;
    revealRfqDraftForm(focusName, el.dataset.supplier || '');
  } else if (action === 'draft-rfq') {
    if (!focusName) return;
    revealRfqDraftForm(focusName, '');
  } else if (action === 'rfq-review-send') {
    submitRfqDraftForm();
  }
});

document.addEventListener('keydown', function (e) {
  if ((e.key === 'Enter' || e.key === ' ') && e.target && e.target.dataset && e.target.dataset.action === 'focus-pinned') {
    e.preventDefault();
    e.target.click();
  }
});
