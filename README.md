# TAAMs Import Sourcing Desk

A single web page where a person and an AI agent source verified food imports
side by side. The agent does not talk *about* the page — it operates the page,
using the same buttons and the same functions a person clicks.

Built for the [OpenAI WebMCP Challenge](https://webmcp.devpost.com/) on top of
[TAAMs](https://taamsglobal.com), a B2B marketplace for officially imported food.

- **Live demo:** https://taams-sourcing-desk.netlify.app
- **Demo video (3 min):** `pending upload`
- **License:** MIT
- **Dependencies:** none. One static page, no build step, no backend of its own.

---

## The problem this page is about

Importing food into Korea starts with two questions that have nothing to do
with software: *is this a real supplier, and is this a real price?*

Today a buyer answers them by hand — digging through a government customs
portal, cold-calling trading companies, and guessing whether a quoted price is
normal. That work happens before a single quote is ever sent, and it is exactly
the kind of work an agent should be able to help with. But a chat window that
answers in prose is not enough: sourcing decisions are made by comparing things
*on a screen*, and the buyer has to stay in control of anything that leaves the
building.

So the goal was not "an agent that answers import questions." It was a working
surface that a human uses normally, that an agent can also drive, where both are
looking at the same thing at the same time.

---

## What TAAMs is

**TAAMs is a B2B marketplace where verified, officially imported food products
are traded directly with importers — no middlemen.** Buyers find products and
request quotes from the company that actually cleared them through customs,
instead of working down a chain of distributors.

Data lookup and analytics exist to *support trust in those transactions*.
Knowing who imported a product, from which exporter, in which country, at what
unit price, is what makes a direct-trade offer verifiable rather than a claim.
The data is the evidence; the marketplace is the product.

TAAMs is operated by TAAMs Global (Hwaseong, Republic of Korea) and is built on
Korean customs clearance records published by the Ministry of Food and Drug
Safety (MFDS), processed and reconstructed by TAAMs.

### Data scale (measured, 2026-08)

| Dataset | Size |
|---|---|
| Customs clearance records | **1,318,602** transactions, 2023-01-02 to 2026-07-31 |
| Overseas manufacturers / exporters on file | **169,089** across **202 countries** |
| Korean import licence registrations | **206,076** |
| Korean companies with actual clearance history | **21,359** |

> A note on the last two rows, because the distinction matters and is easy to
> get wrong: 206,076 is a count of **import licence registrations**, not a count
> of active importers. The number of Korean companies that actually appear in
> clearance records is **21,359**. The two figures answer different questions
> and should never be used interchangeably.

### What a single product looks like

Mango, 2025, as returned by the same public endpoints this page calls:

- **4,368** customs clearance records in 2025
- Average import unit price **$3.48/kg** in June 2025, **$5.07/kg** in August 2026

  Both are real; the price moves month to month, which is the point of asking
  for a month rather than a year. The page defaults to the most recent month
  that has data, so the figure it shows will not match June 2025 — clearance
  data publishes with a lag, and the current month is always partial.

- Nine supplying countries: Thailand 3,310 (75.8%), Brazil 651 (14.9%),
  Vietnam 243 (5.6%), Peru 99, Taiwan 34, Australia 12, Philippines 9,
  Cambodia 9, India 1
- HS code **0804502000**

That is the granularity these tools expose: per product, per month, per
exporting country, per company — not an annual national average.

---

## The seven WebMCP tools

Registered with `document.modelContext.registerTool()` when the page loads.
They are deliberately layered, because the interesting question in WebMCP is not
"can an agent fetch data" but "what can an agent do that only makes sense inside
the page a human is looking at."

### Tier A — Lookup (4 tools)

These call the public TAAMs API and render the result on screen. An agent
calling them changes what the human sees.

| Tool | What it does |
|---|---|
| `search_import_products` | Resolves free text in English or Korean ("frozen mango") to the exact registered product name used in clearance records. Every other tool depends on it. |
| `get_import_price_trend` | Monthly import unit price (USD/kg) for a product, broken down by exporting country, and draws the chart. |
| `get_top_exporters` | Overseas suppliers shipping that product to Korea, ranked by clearance count, with a country breakdown. |
| `get_active_importers` | Korean companies already importing it, with 12-month clearance counts — a direct read on how contested a category already is. |

### Tier B — Screen control (2 tools) — the part a remote MCP server cannot do

These make **zero network requests**. They do not fetch anything. They rearrange
and filter what is already on the human's screen. Open the network tab during
the demo and nothing fires.

| Tool | What it does |
|---|---|
| `pin_to_comparison_board` | Pins an already-loaded product onto the on-screen comparison board, up to three side by side. |
| `highlight_supplier_country` | Filters and highlights the rendered supplier table and price chart down to one exporting country; an empty string clears it. |

A remote MCP server can return better JSON. It cannot decide which row of the
table you are currently staring at should be highlighted, because it has no idea
a table is being displayed at all.

### Tier C — Action, gated by a human (1 tool)

| Tool | What it does |
|---|---|
| `draft_sourcing_request` | Fills in a sourcing enquiry (RFQ) draft on screen — product, supplier, quantity, notes — and then stops. Nothing is sent. An approval dialog shows the human exactly what is about to go out. Only on approval does the page open a pre-filled email from the user's own mail client. |

The design point: this tool's most important behaviour is what it *refuses* to
do. An agent can prepare a commercial enquiry to a real supplier; it cannot send
one. The failure mode is not "nothing happened" — it is "a person had to look at
it first," and that is visible on screen every single time.

### Everything here is clickable by hand

Each tool's execute path calls the same function the page's own controls call.
The search box works by typing. Pin and Highlight are buttons. The RFQ card can
be filled in manually. With no agent present this is a complete, usable sourcing
page — WebMCP makes it reachable by an agent, it is not the reason the page
exists. That claim is checkable from the source: the tool handlers are
one-liners delegating to the UI functions.

---

## Why WebMCP rather than a remote MCP server

TAAMs already runs a remote MCP server for Claude and ChatGPT. Building this
made the difference concrete:

| | Remote MCP server | WebMCP (this page) |
|---|---|---|
| What the agent gets | JSON | JSON **and** the live screen state |
| Where the result lands | In the transcript | In front of the user, in place |
| Shared context | The agent's, described back to you | Literally the same pixels |
| Approving an action | Wherever the client decides to ask | On the page, showing the actual draft |
| Auth | Server-side tokens, set up per client | The user's own browser session |

The practical consequence for a B2B buyer: with a remote server you read the
agent's summary, then go and re-do the comparison yourself in the real tool.
With WebMCP the comparison the agent built *is* the comparison you are looking
at. There is nothing to re-do.

---

## Implementation notes, including where the spec and the browser disagreed

An honest record of what we found building against Chrome 151 with WebMCP
enabled (`chrome://flags/#enable-webmcp-testing`):

1. **The API lives on `document.modelContext`, not `navigator.modelContext`.**
   Plenty of published material still shows `navigator`. The page
   feature-detects both (`document.modelContext ?? navigator.modelContext`) so
   it survives the object moving again.

2. **`requestUserInteraction()` does not exist in Chrome 151.** The human
   approval gate for `draft_sourcing_request` was originally designed around it.
   It is not on the object, so we implemented the gate ourselves with a native
   `<dialog>` that renders the exact draft and requires an explicit click. The
   user-visible guarantee is identical — an agent-initiated action cannot
   complete without a human confirming what it contains — but the page is
   enforcing it, not the browser. When the API ships this is a small swap, and
   the fallback stays either way: a page should not lose its safety gate on a
   browser that lacks the flag.

3. **No agent, no problem.** If neither object exists, the page skips
   registration, shows a status badge explaining that an agent-capable browser
   is needed for the agent half, and otherwise behaves as an ordinary web app.

4. **The API answers HTTP 200 for "deliberately not provided."** TAAMs
   distinguishes *no data* from *unit price not offered for this category by
   design*, and signals the latter with a reason flag on a successful response.
   The client branches on that flag rather than on status codes, so the agent is
   told "this category does not carry a unit price by design" instead of
   inventing an outage. Getting this wrong is how an agent ends up confidently
   reporting a gap that is not a gap.

5. **Korean names are the keys.** Lookups are keyed on the canonical Korean
   product name; the English label is for display only. Passing a translated
   string returns an empty result rather than an error — a quiet failure an
   agent would otherwise narrate as "no imports found." The tool descriptions
   state explicitly that the exact returned name must be passed onward.

---

## Running it

No build step, no dependencies, no keys.

```bash
git clone https://github.com/taamslabglobal-code/taams-webmcp.git
cd taams-webmcp
python -m http.server 8123
# then open http://127.0.0.1:8123/
```

To let an agent drive it, open the same URL in a browser with WebMCP enabled. On
Chrome 151: turn on `chrome://flags/#enable-webmcp-testing`, restart, then use
the browser's agent side panel.

`probe.html` is a standalone environment check — it reports which
`modelContext` object exists, whether `registerTool()` accepts a tool, whether
`requestUserInteraction()` is present, and whether a live TAAMs API call
succeeds from page context. Run it first if the tools do not show up.

`test/probe_webmcp_env.py` drives that probe through Playwright against real
Chrome and exits non-zero if any check fails.

---

## The data, and what it is not

- Source: Korean customs clearance records published by MFDS, processed by
  TAAMs. Everything shown comes from the same public endpoints the live TAAMs
  service uses; there is no static snapshot bundled into this repository.
- Clearance data is published with a lag of about three days, so the correct
  latest date is the most recent complete business day, not today.
- Unit prices are per product category and per exporting country. They are a
  negotiating reference, not a quotation. Some categories deliberately do not
  carry a unit price, and the API says so explicitly rather than returning zero.
- This repository contains no personal data and no customer data.

---

## New work for this challenge

Per the challenge rules, stated plainly:

- **New — created after 2026-08-25, all of it in this repository:** the page
  itself, all seven WebMCP tool definitions and handlers, the comparison board,
  the country highlight logic, the RFQ draft-and-approve flow and its dialog,
  the API client, the environment probe, and the Playwright check.
- **Pre-existing, and not submitted:** the TAAMs platform and its public read
  API, which this page calls as a data source in the same way any third party
  could. No TAAMs server code was written or modified for this entry. TAAMs also
  operates a separate remote MCP server; it is a different product and shares no
  code with this repository.

---

## License and contact

MIT — Copyright (c) 2026 Jongseok Mun (TAAMs). See [LICENSE](LICENSE).

TAAMs Global, Hwaseong, Republic of Korea · support@taamsglobal.com ·
[taamsglobal.com](https://taamsglobal.com)
