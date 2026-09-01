/**
 * WebMCP tool registration.
 *
 * This file is the point of the project: it turns a page a human is reading
 * into a set of tools an agent sitting next to them can call.
 *
 * Three tiers, deliberately:
 *   A. Lookup        — fetches from the TAAMs public API.
 *   B. Screen control — changes what the human is looking at. Fetches nothing.
 *                       A remote MCP server cannot do this at all; it has no
 *                       idea a screen exists. This tier is why WebMCP matters.
 *   C. Action         — drafts an outbound request, then stops and waits for a
 *                       human to approve it. Nothing leaves the page otherwise.
 *
 * Note on the approval gate: the WebMCP explainers describe a
 * `requestUserInteraction()` for exactly this. It does not exist in shipping
 * Chrome 151 — the object only carries ontoolchange, executeTool, getTools and
 * registerTool. So the gate is our own in-page modal. That turned out to be the
 * better answer anyway: the human sees the actual draft, not a system prompt.
 */

// Keep the ?v= token in step with index.html — see the note there. Mismatched
// tokens load a second copy of the module with its own state.
import { Taams, priceWithheldReason } from './api.js?v=10';
import { UI } from './ui.js?v=10';

/** Most recent complete calendar year in the dataset (data runs to 2026-07). */
const YEAR = 2025;
const FROM = `${YEAR}-01-01`;
const TO = `${YEAR}-12-31`;

/** What the agent has looked up this session. Tier B reads this, never refetches. */
const session = new Map(); // koreanName -> { nameEn, price, exporters, importers }

/**
 * Korean canonical name -> English label. Only the search endpoint carries the
 * English name; the price and supplier endpoints do not, so it has to be kept
 * from the lookup that resolved the name in the first place. Without this the
 * card headline renders in Korean only.
 */
const englishNames = new Map();

const ok = (text) => ({ content: [{ type: 'text', text }] });
const fail = (text) => ({ content: [{ type: 'text', text }], isError: true });

const hasHangul = (s) => /[ㄱ-힝]/.test(s || '');

/**
 * Agents pass whatever the user typed. Resolve it to the key the API wants.
 *
 * Two rules learned from getting this wrong: search the column that matches the
 * script the user actually typed, and prefer an exact hit over the top-ranked
 * one. Fuzzy search on "망고" against the English column happily returns
 * "썬라이트 망고맛" — a different product, with no error to notice.
 */
async function resolveName(query) {
  if (session.has(query)) return query;

  const hits = await Taams.searchProducts({
    query, startDate: FROM, endDate: TO, lang: hasHangul(query) ? 'ko' : 'en',
  });
  if (!Array.isArray(hits) || !hits.length) return null;

  for (const h of hits) {
    if (h.name_en) englishNames.set(h.name, h.name_en);
  }

  const exact = hits.find((h) => h.name === query)
    || hits.find((h) => (h.name_en || '').toLowerCase() === query.toLowerCase());
  return (exact || hits[0]).name;
}

/**
 * Tier B resolution: session only, never a network call. These tools claim to
 * fetch nothing, and that claim is checked in test/probe_tools_e2e.py.
 */
function resolveLoaded(query) {
  if (session.has(query)) return query;
  const q = (query || '').toLowerCase();
  for (const [name, data] of session) {
    if (name.toLowerCase() === q || (data.nameEn || '').toLowerCase() === q) return name;
  }
  return null;
}

const TOOLS = [
  // ─────────────────────────────────────────────── Tier A — lookup
  {
    name: 'search_import_products',
    description:
      'Search for an imported food product by name (English or Korean) and get '
      + 'the exact product name used in Korean customs clearance records. Call '
      + 'this FIRST whenever the user names any food product ("frozen mango", '
      + '"olive oil", "kimchi"). The other tools need the exact name returned '
      + 'here, not the user\'s wording — passing free-form text to them returns '
      + 'an empty result rather than an error, so do not skip this step. '
      + `Returns matching products with their ${YEAR} clearance counts. If `
      + 'several match, take the one with the highest count unless the user\'s '
      + 'wording clearly points at another. If nothing matches, say so and ask '
      + 'the user to rephrase — do not guess a name and pass it on, because the '
      + 'other tools answer a wrong name with an empty result, not an error, and '
      + 'that reads as "this product is never imported" when it is not.',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Product name in English or Korean. Partial match is fine, e.g. "mango".',
        },
      },
      required: ['query'],
    },
    async execute({ query }) {
      UI.agentSays(`Searching products for "${query}"`);
      const hits = await Taams.searchProducts({ query, startDate: FROM, endDate: TO });
      if (!Array.isArray(hits) || !hits.length) {
        return fail(`No product in the customs records matches "${query}".`);
      }
      const top = hits.slice(0, 8);
      UI.agentSays(`Found ${hits.length} matches, top: ${top[0].name_en || top[0].name}`);
      return ok(
        `Matching products (use the exact "name" value in other tools):\n`
        + top.map((h) => `- name: ${h.name} (${h.name_en || 'no English label'}) — `
          + `${h.totalCount.toLocaleString()} clearances in ${YEAR}`).join('\n'),
      );
    },
  },

  {
    name: 'get_import_price_trend',
    description:
      'Get the average import unit price (USD/kg) for a product, plus how that '
      + 'price breaks down by exporting country. This is the landed customs '
      + 'price actually paid by Korean importers, not a retail or listing price. '
      + 'Renders a price card on screen for the user as a side effect. Use it '
      + 'when the user asks what something costs to import, whether a price is '
      + 'reasonable, or which country is cheapest. Requires the exact product '
      + 'name from search_import_products.',
    inputSchema: {
      type: 'object',
      properties: {
        product_name: {
          type: 'string',
          description: 'Exact product name from search_import_products, e.g. "망고".',
        },
        month: {
          type: 'integer',
          description: 'Month, 1-12. Omit this to get the most recent month that '
            + 'has data, which is what you want unless the user named a month.',
        },
      },
      required: ['product_name'],
    },
    async execute({ product_name, month }) {
      const name = await resolveName(product_name);
      if (!name) return fail(`"${product_name}" is not a product in the customs records.`);

      UI.setBusy(true);
      UI.agentSays(`Loading import price for ${name}`);
      try {
        // No month means "latest month with data"; the client resolves it and
        // tells us which month it landed on.
        const price = await Taams.priceDashboard({ item: name, year: YEAR, month });
        if (!price) return fail(`No priced month found for ${name} in recent records.`);
        const withheld = priceWithheldReason(price);
        if (withheld) {
          UI.agentSays(`Price not available for ${name}`);
          return ok(`No unit price for ${name}. ${withheld} This is a deliberate `
            + 'exclusion, not missing data — other tools still work for this product.');
        }
        const prev = session.get(name) || {};
        const next = { ...prev, nameEn: englishNames.get(name) || prev.nameEn || '', price };
        session.set(name, next);
        UI.renderProduct(name, next);

        const countries = (price.countries || [])
          .slice(0, 6)
          .map((c) => `  ${c.name}: $${Number(c.avg_price).toFixed(2)}/kg`)
          .join('\n');
        UI.agentSays(`${name} — $${Number(price.current_avg).toFixed(2)}/kg average`);
        return ok(
          `${name} (item type: ${price.product_type})\n`
          + `Average import price: $${Number(price.current_avg).toFixed(2)}/kg`
          + ` in ${price.year}-${String(price.month).padStart(2, '0')}\n`
          + (countries ? `By exporting country:\n${countries}\n` : '')
          + 'Now shown on screen. Chart it if the user wants to see the trend.',
        );
      } finally {
        UI.setBusy(false);
      }
    },
  },

  {
    name: 'get_top_exporters',
    description:
      'List the overseas manufacturers and exporters actually shipping a product '
      + 'into Korea. Returns named companies — one row per exporting company, '
      + 'with its country and clearance count — plus a per-country total. These '
      + 'are real registered suppliers from clearance records, not a directory '
      + 'listing. Renders a supplier table on screen. Use it when the user asks '
      + 'who supplies a product, where it comes from, or wants to find a source. '
      + 'For a country-versus-country decision, call get_import_price_trend '
      + 'first for the price side, then this tool for the supplier side. '
      + 'Requires the exact product name from search_import_products.',
    inputSchema: {
      type: 'object',
      properties: {
        product_name: { type: 'string', description: 'Exact product name.' },
        country: {
          type: 'string',
          description: 'Optional. Restrict to one exporting country, e.g. "베트남" or "Vietnam".',
        },
      },
      required: ['product_name'],
    },
    async execute({ product_name, country }) {
      const name = await resolveName(product_name);
      if (!name) return fail(`"${product_name}" is not a product in the customs records.`);

      UI.setBusy(true);
      UI.agentSays(`Loading suppliers for ${name}`);
      try {
        // Always fetch the whole list, even when one country was asked for.
        // Keeping a filtered list stood on screen as the whole truth: a card
        // scoped to any *other* country then counted zero suppliers in it —
        // Brazil showed "0 suppliers" when it has five. Narrowing to a country
        // is a view concern, so it is done by highlighting instead.
        const exporters = await Taams.topExporters({
          productName: name, startDate: FROM, endDate: TO,
        });
        const prev = session.get(name) || {};
        const next = { ...prev, nameEn: englishNames.get(name) || prev.nameEn || '', exporters };
        session.set(name, next);
        UI.renderProduct(name, next);

        const totals = Object.entries(exporters.country_totals || {})
          .sort((a, b) => b[1] - a[1]);
        if (!totals.length) return ok(`No exporters on record for ${name}.`);

        let focus = '';
        if (country) {
          const hl = UI.highlightCountry(country);
          focus = hl.ok && hl.matched
            ? `\nHighlighted ${country} on screen (${hl.matched} rows); the others are dimmed.`
            : `\n"${country}" has no suppliers on record for ${name}.`;
        }

        UI.agentSays(`${totals.length} supplying countries for ${name}`);
        return ok(
          `Exporting countries for ${name} (${exporters.exporter_total.toLocaleString()} clearances in ${YEAR}):\n`
          + totals.slice(0, 8).map(([c, n]) => `  ${c}: ${n.toLocaleString()}`).join('\n')
          + focus
          + '\nSupplier table is now on screen. Use highlight_supplier_country to focus one.',
        );
      } finally {
        UI.setBusy(false);
      }
    },
  },

  {
    name: 'get_active_importers',
    description:
      'List Korean companies already importing this product, with clearance '
      + 'counts and which country they buy from. Useful for gauging whether a '
      + 'product has an established market, who the incumbent buyers are, and '
      + 'how concentrated the trade is. When the user is choosing between two '
      + 'sourcing countries this is the proof check: a country established '
      + 'Korean buyers already import from is a proven lane, one with no active '
      + 'buyers is not — so call it after get_top_exporters whenever the user '
      + 'asks who to buy from. Renders on screen. Requires the exact product '
      + 'name from search_import_products.',
    inputSchema: {
      type: 'object',
      properties: {
        product_name: { type: 'string', description: 'Exact product name.' },
      },
      required: ['product_name'],
    },
    async execute({ product_name }) {
      const name = await resolveName(product_name);
      if (!name) return fail(`"${product_name}" is not a product in the customs records.`);

      UI.setBusy(true);
      UI.agentSays(`Loading active importers for ${name}`);
      try {
        const importers = await Taams.productImporters({
          productName: name, startDate: FROM, endDate: TO,
        });
        const prev = session.get(name) || {};
        const next = { ...prev, nameEn: englishNames.get(name) || prev.nameEn || '', importers };
        session.set(name, next);
        UI.renderProduct(name, next);

        if (!Array.isArray(importers) || !importers.length) {
          return ok(`No Korean importer on record for ${name} in ${YEAR}.`);
        }
        UI.agentSays(`${importers.length} active importers for ${name}`);
        return ok(
          `${importers.length} Korean companies imported ${name} in ${YEAR}. Top buyers:\n`
          + importers.slice(0, 6).map((i) => `  ${i.importer_en || i.importer} `
            + `— ${i.cnt} clearances, sourcing from ${i.country}`).join('\n'),
        );
      } finally {
        UI.setBusy(false);
      }
    },
  },

  // ────────────────────────────────── Tier B — screen control (no fetching)
  {
    name: 'pin_to_comparison_board',
    description:
      'Pin one card onto the on-screen comparison board, up to three. A card is '
      + 'a product, optionally narrowed to a single sourcing country — so '
      + '{product_name:"망고", country:"Thailand"} and {product_name:"망고", '
      + 'country:"Brazil"} are two different cards, each showing that country\'s '
      + 'own price, trend and supplier count. Call this whenever the user weighs '
      + 'two or more named options against each other, even if they never say '
      + 'the word "compare" — "A or B?", "which is better", "should I go with X '
      + 'or Y" all mean compare. Pin each option as its own card BEFORE you give '
      + 'your recommendation, so the user can see what you are weighing. This '
      + 'changes the user\'s screen and fetches nothing; it reuses data already '
      + 'loaded. Call get_import_price_trend for the product first if it is not '
      + 'on screen yet.',
    inputSchema: {
      type: 'object',
      properties: {
        product_name: {
          type: 'string',
          description: 'Exact product name, already loaded on screen this session.',
        },
        country: {
          type: 'string',
          description: 'Optional. Narrow this card to one sourcing country, English or '
            + 'Korean, e.g. "Thailand". Omit for a card covering every country.',
        },
      },
      required: ['product_name'],
    },
    async execute({ product_name, country = '' }) {
      const name = resolveLoaded(product_name);
      if (!name) {
        return fail(`${product_name} has not been looked up yet. `
          + 'Call get_import_price_trend or get_top_exporters for it first, then pin it.');
      }
      const res = UI.pinToBoard(name, country);
      if (!res.ok) {
        return fail(res.reason || 'The comparison board is full — unpin something first.');
      }
      const label = country ? `${name} (${country})` : name;
      UI.agentSays(`Pinned ${label} to the comparison board`);
      return ok(`Pinned ${label}. Board now shows: ${res.pinned.join(', ')}. `
        + 'The user can see the cards side by side; say what stands out between them.');
    },
  },

  {
    name: 'highlight_supplier_country',
    description:
      'Filter and visually highlight the supplier table already on screen down '
      + 'to one exporting country, so the user immediately sees that country\'s '
      + 'suppliers instead of re-reading the whole list. This only restyles what '
      + 'is already displayed — it fetches nothing, and the other countries are '
      + 'dimmed rather than removed. Call it when the user asks to focus on, '
      + 'highlight, or "just show me" one country. ALSO call it on your own, '
      + 'without being asked, once you have settled on a recommendation: '
      + 'highlight the country you are recommending so the user is looking at '
      + 'those suppliers while you explain why. If no supplier table is on '
      + 'screen yet, call get_top_exporters first. Use get_top_exporters with a '
      + 'country only for the first fetch; use this tool for every narrowing '
      + 'after that. Pass an empty string to clear the highlight.',
    inputSchema: {
      type: 'object',
      properties: {
        country: {
          type: 'string',
          description: 'Country name, English or Korean, e.g. "Vietnam" or "베트남". '
            + 'Empty string clears the highlight.',
        },
      },
      required: ['country'],
    },
    async execute({ country }) {
      const res = UI.highlightCountry(country);
      if (!country) {
        UI.agentSays('Cleared country highlight');
        return ok('Highlight cleared — the full supplier list is visible again.');
      }
      if (!res.ok || !res.matched) {
        return fail(`Nothing on screen matches "${country}". `
          + 'Load suppliers with get_top_exporters first, or check the country name.');
      }
      UI.agentSays(`Highlighted ${country} (${res.matched} rows)`);
      return ok(`Highlighted ${res.matched} ${country} rows on screen. `
        + 'The rest are dimmed, not removed. Tell the user what this narrows to.');
    },
  },

  // ────────────────────────────── Tier C — action, gated on a human approving
  {
    name: 'draft_sourcing_request',
    description:
      'Fill in a sourcing inquiry (RFQ) on screen for a product and supplier, '
      + 'then stop and ask the user to approve it. This tool NEVER sends '
      + 'anything on its own: it opens an approval dialog showing the draft, and '
      + 'only if the user clicks Approve does the page open a pre-filled email. '
      + 'If the user cancels, nothing happens. Call it when the user asks to '
      + 'contact a supplier, request a quote, or draft an inquiry about '
      + 'something already on screen. Tell the user you are preparing a draft '
      + 'for their approval — do not claim anything was sent.',
    inputSchema: {
      type: 'object',
      properties: {
        product_name: { type: 'string', description: 'Exact product name.' },
        supplier_name: {
          type: 'string',
          description: 'The exporting company name exactly as get_top_exporters '
            + 'returned it — a company, not a country. If the user asked you to '
            + 'pick one, use the top exporter from that list and say in your '
            + 'reply which one you chose and why. Leave empty only when the user '
            + 'has explicitly said they want to decide later.',
        },
        quantity: {
          type: 'string',
          description: 'Quantity in the user\'s own words, e.g. "2 x 20ft containers".',
        },
        notes: {
          type: 'string',
          description: 'Target price, delivery timing, certification needs, and so on.',
        },
      },
      required: ['product_name', 'quantity'],
    },
    async execute({ product_name, supplier_name = '', quantity, notes = '' }) {
      const name = await resolveName(product_name);
      if (!name) return fail(`"${product_name}" is not a product in the customs records.`);

      const draft = { productName: name, supplierName: supplier_name, quantity, notes };
      UI.agentSays(`Drafted an RFQ for ${name} — waiting for your approval`);

      const approved = await UI.confirmRfq(draft);
      if (!approved) {
        UI.agentSays('RFQ cancelled by the user');
        return ok('The user reviewed the draft and cancelled it. Nothing was sent. '
          + 'Ask what they would like changed rather than resending.');
      }

      const subject = `Sourcing inquiry: ${name}`;
      const body = [
        `Product: ${name}`,
        supplier_name ? `Supplier of interest: ${supplier_name}` : null,
        `Quantity: ${quantity}`,
        notes ? `Notes: ${notes}` : null,
        '',
        'Sent from the TAAMs Import Sourcing Desk.',
      ].filter(Boolean).join('\n');

      window.open(
        `mailto:support@taamsglobal.com?subject=${encodeURIComponent(subject)}`
        + `&body=${encodeURIComponent(body)}`,
        '_blank',
      );
      UI.markRfqSent(draft);
      UI.agentSays(`RFQ approved and handed to the user's email client`);
      return ok(`The user approved the draft. Their email client opened with the `
        + `inquiry for ${name} pre-filled — they still send it themselves. `
        + 'Confirm that to the user; do not say it has been delivered.');
    },
  },
];

/**
 * Register every tool. Returns a function that unregisters them all —
 * unregisterTool() was removed from the spec, so an AbortSignal is the way.
 */
export async function registerTools() {
  const mc = document.modelContext ?? navigator.modelContext;
  if (!mc || !('registerTool' in mc)) {
    UI.agentSays('WebMCP is not available in this browser — running in manual mode.');
    return { supported: false, names: [], dispose: () => {} };
  }

  const controller = new AbortController();
  const names = [];
  for (const tool of TOOLS) {
    await mc.registerTool(tool, { signal: controller.signal });
    names.push(tool.name);
  }
  UI.agentSays(`${names.length} tools registered — an agent on this page can now use them.`);
  return { supported: true, names, dispose: () => controller.abort() };
}

/** Exposed so the page can drive tools itself when no agent is attached. */
export const toolIndex = Object.fromEntries(TOOLS.map((t) => [t.name, t]));
