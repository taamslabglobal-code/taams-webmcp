/**
 * TAAMs public API client.
 *
 * Every endpoint below is confirmed to answer WITHOUT any Authorization header,
 * verified the only way that actually settles it: by calling the live endpoints
 * from a browser and watching what comes back (test/probe_tools_e2e.py). CORS is
 * open, so this module runs from any static origin — nothing here has privileged
 * access that a third party could not reproduce.
 *
 * Caveats baked in on purpose:
 *  - `구분` (category discriminator) is a literal Korean query key -> must be
 *    percent-encoded. URLSearchParams handles it.
 *  - The server returns HTTP 200 with an empty payload plus a reason flag
 *    instead of 4xx for two cases: `exclusive_blocked` (2 of 6,150 item types)
 *    and `price_eligible:'N'` (price is intentionally not offered). Callers must
 *    branch on those, not on status codes.
 *  - Errors arrive under any of detail|error|message, so normalise them.
 *
 * Two naming traps, both verified the hard way against the live API:
 *
 *  1. Every lookup below is keyed on the Korean canonical product name (e.g.
 *     "망고"), NOT the English label and NOT the item type. `searchProducts`
 *     returns both: show `name_en` to the user, pass `name` to everything else.
 *     Translating the key yourself returns an empty result, never an error.
 *
 *  2. `priceDashboard({item})` also takes that product name and resolves the
 *     item type server-side; the item type comes back as `product_type`. Feed
 *     THAT (not the product name) to `productTariff`. Passing an item type into
 *     `item` yields a 200 with a generic error body.
 */

const BASE = 'https://taamsglobal.com/api/v1';

async function get(path, params = {}) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') qs.set(k, String(v));
  }
  const url = `${BASE}${path}?${qs}`;
  let res;
  try {
    res = await fetch(url, { headers: { Accept: 'application/json' } });
  } catch (e) {
    throw new Error(`TAAMs is unreachable: ${e.message}`);
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const msg = body?.detail || body?.error || body?.message || res.statusText;
    throw new Error(`TAAMs returned ${res.status}: ${msg}`);
  }
  return body;
}

/**
 * Find the most recent month that actually has priced data, walking backwards
 * from the current one.
 *
 * Two reasons this exists rather than just asking for a year:
 *
 *  1. There is no "whole year" option on this endpoint. Month 0 makes the
 *     server build the date "YYYY-00-01" and fail with a 500 — a server error,
 *     not an empty result, so it cannot be treated as "no data".
 *  2. Customs clearance data lands with a lag, and the current month is always
 *     partial. Asking for "this month" on the 1st returns nothing useful, which
 *     looks identical to a product with no trade at all.
 *
 * Walks back up to 8 months, which comfortably covers the publication lag.
 */
async function resolveLatestPricedMonth({ item, gubun, maxBack = 8 }) {
  const now = new Date();
  let year = now.getFullYear();
  let month = now.getMonth() + 1;
  let lastSeen = null;

  for (let i = 0; i < maxBack; i += 1) {
    let payload = null;
    try {
      payload = await get('/price_dashboard', { item, year, month, 구분: gubun });
    } catch {
      payload = null; // a bad month should not abort the search for a good one
    }
    if (payload) {
      lastSeen = payload;
      // A withheld price is a real answer — stop and let the caller report it,
      // rather than walking back and pretending an older month is the truth.
      if (priceWithheldReason(payload)) return { ...payload, year, month };
      if (Number(payload.current_avg) > 0) return { ...payload, year, month };
    }
    month -= 1;
    if (month === 0) { month = 12; year -= 1; }
  }
  return lastSeen ? { ...lastSeen, year, month } : null;
}

export const Taams = {
  /**
   * Resolve free text (English or Korean) to canonical product names.
   * Returns [{ id, name, name_en, totalCount }] — `name` is the key for
   * every other call here, `name_en` is what you show the user.
   */
  searchProducts: ({ query, startDate, endDate, lang = 'en', mode = 'product' }) =>
    get('/product_search', { query, start_date: startDate, end_date: endDate, lang, mode }),

  /**
   * Unit price (USD/kg) + weekly trend + per-country breakdown.
   * `item` is the Korean product name. The response's `product_type` is what
   * `productTariff` wants.
   *
   * `month` must be 1-12. Omit it to get the most recent month that has data —
   * see resolveLatestPricedMonth below for why asking for "the whole year"
   * is not an option here.
   */
  priceDashboard: async ({ item, year, month, gubun }) => {
    if (month) return get('/price_dashboard', { item, year, month, 구분: gubun });
    return resolveLatestPricedMonth({ item, gubun });
  },

  /** Monthly import counts, split by exporting country. */
  productTrend: ({ productName, startDate, endDate, gubun }) =>
    get('/product_trend', {
      product_name: productName, start_date: startDate, end_date: endDate, 구분: gubun,
    }),

  /** Top exporting factories abroad for one item type. */
  topExporters: ({ productName, startDate, endDate, country, gubun }) =>
    get('/product_top_exporters', {
      product_name: productName, start_date: startDate, end_date: endDate, country, 구분: gubun,
    }),

  /** Korean importers already buying this item type. */
  productImporters: ({ productName, startDate, endDate, gubun }) =>
    get('/product_importer_summary', {
      product_name: productName, start_date: startDate, end_date: endDate, 구분: gubun,
    }),

  /** Customs duty rates mapped to the item type's HS codes. */
  productTariff: ({ productType, hsCode, productName }) =>
    get('/product_tariff', { product_type: productType, hs_code: hsCode, product_name: productName }),

  /** Country-level import overview. tab 0=trend 1=products 2=exporters 3=importers */
  countryDetail: ({ country, year, tab = 0, month = 0 }) =>
    get('/country_detail', { country, year, tab, month }),
};

/** True when the server withheld price on purpose (not an error, not "no data"). */
export function priceWithheldReason(payload) {
  if (!payload) return null;
  if (payload.exclusive_blocked) return 'This item type is reserved for exclusive subscribers.';
  if (payload.price_eligible === 'N') {
    return payload.unavailable_reason
      || 'Unit price is not offered for this item type by design.';
  }
  return null;
}
