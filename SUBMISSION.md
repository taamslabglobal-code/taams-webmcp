# Devpost submission text — TAAMs Import Sourcing Desk

> Paste-ready copy for the Devpost submission form. Section headings map to the
> form fields; the four judged questions are answered explicitly and in order.

---

## Elevator pitch (one line)

A web page where a person and an AI agent source verified food imports together
— the agent operates the same screen the buyer is looking at, and cannot send
anything without the buyer's approval.

---

## Inspiration

Importing food into a country starts with two questions that have nothing to do
with software: *is this a real supplier, and is this a real price?* Buyers
answer them by hand today — reading government customs portals, cold-calling
trading companies, guessing whether a quoted price is normal. All of that
happens before a single quote is ever sent.

An agent should help with that. But we had already built a remote MCP server for
this data, and watched what happens: the agent gives you a good summary, and
then you go and redo the comparison yourself in the real tool, because sourcing
decisions are made by comparing things on a screen. The summary is not the work.

WebMCP removes that second step. The comparison the agent builds *is* the
comparison you are looking at.

---

## What it does

The page is a sourcing desk for officially imported food entering Korea, backed
by TAAMs — a B2B marketplace where verified, officially imported products are
traded directly with importers, with no middlemen in between.

You search a product, and you get real customs clearance data: the monthly
import unit price in USD/kg broken down by exporting country, the overseas
suppliers actually shipping it, and the Korean companies already buying it. You
pin products side by side, filter down to one supplying country, and draft a
sourcing enquiry to a specific supplier.

Every one of those actions is a button a human can click. Seven of them are also
registered as WebMCP tools, so an agent can reach for the same buttons.

The data behind it, all measured: **1,318,602 customs clearance records**
(2023-01-02 to 2026-07-31), **169,089 overseas manufacturers across 202
countries**, **206,076 Korean import licence registrations** — of which
**21,359 companies** actually appear in clearance records. (Those last two are
different questions; licence registrations are not a headcount of active
importers.)

A concrete example, straight from the live API: mango, 2025 — 4,368 clearance
records, average import price $3.48/kg in June 2025, supplied from nine
countries — Thailand 3,310 (75.8%), Brazil 651, Vietnam 243, Peru 99, Taiwan 34,
Australia 12, Philippines 9, Cambodia 9, India 1 — HS code 0804502000. That is
per-product, per-month, per-country granularity, not an annual national average.

---

## (a) Use case fit — why this problem belongs in WebMCP

B2B sourcing is the case where "agent gives you an answer" is structurally not
enough, for three reasons:

1. **The decision is comparative and visual.** You are not asking one question;
   you are holding three products, six supplying countries and a price trend in
   view at once and deciding between them. Prose in a transcript loses exactly
   the thing that makes the decision possible.
2. **The output is a commitment, not an answer.** The endpoint of the workflow
   is a sourcing enquiry to a named company — an action with commercial
   consequences. That has to happen under the buyer's eye, on the buyer's
   screen, showing the actual text.
3. **The evidence has to stay attached to the claim.** A direct-trade
   marketplace works only if "this supplier is real, at this price" is
   verifiable. When the agent moves the screen instead of summarising it, the
   buyer is always one glance from the underlying record.

Long tail matters too. This is not stock prices or weather — it is a domain with
1.3 million transaction records, per-company granularity, and Korean-language
canonical keys, where a general model has no chance of guessing the numbers.
Precisely the kind of site-specific capability WebMCP is meant to expose.

---

## (b) User experience benefits

- **No re-doing work.** The agent's output lands in the interface, not in a
  transcript you then have to transcribe back into the tool.
- **You keep watching your own screen.** During an agent run, the search box
  fills, the chart redraws, a card appears on the comparison board. You are
  never reading a description of something that happened elsewhere.
- **Nothing irreversible happens silently.** The one tool that can reach the
  outside world stops and shows the draft. Approve, and the email opens from
  your own mail client. Decline, and the draft stays on screen for you to edit
  by hand.
- **The page works with no agent at all.** Search, pin, highlight and RFQ are
  all clickable. Someone who has never heard of WebMCP gets a complete tool. An
  agent makes it faster; it is not a prerequisite.
- **Failures are reported honestly.** The API distinguishes "no data" from
  "price deliberately not offered for this category," and the tools pass that
  distinction through, so the agent says which one it is instead of inventing an
  outage or reporting a gap that is not a gap.

---

## (c) Human–agent collaboration potential

The seven tools are layered so the collaboration boundary is explicit rather
than implied.

**Tier A — lookup (4 tools).** `search_import_products`,
`get_import_price_trend`, `get_top_exporters`, `get_active_importers`. The agent
fetches and the page renders. Division of labour: the agent handles the tedious
part (name resolution, twelve months of history, six countries), the human keeps
the judgement.

**Tier B — screen control (2 tools), zero network requests.**
`pin_to_comparison_board` and `highlight_supplier_country` fetch nothing. They
rearrange what is already in front of the human. "Just show me the Vietnamese
suppliers" filters the table you are looking at. This is the part that only
exists inside the page: a remote server can return better JSON, but it cannot
know a table is on screen, let alone which row deserves attention.

**Tier C — action under human approval (1 tool).** `draft_sourcing_request`
fills in a real enquiry to a real supplier and then deliberately stops. The
agent has authority to prepare and no authority to send. Its failure mode is not
"nothing happened" — it is "a person had to look at this first," demonstrated
visibly on every run.

Same functions on both sides. Each tool handler delegates to the very function
the page's own button calls — verifiable in the source. That is what makes the
collaboration real rather than parallel: there is no agent-only code path and no
human-only code path.

---

## (d) WebMCP implementation approach

Deliberately minimal: **zero dependencies, no build step, one static page, no
backend of its own.** Tools are registered with
`document.modelContext.registerTool()` at load, and the page calls the public
TAAMs read API directly from the browser.

Three findings worth stating, because the gap between spec and browser is part
of the result:

1. **The API is on `document.modelContext`, not `navigator.modelContext`.** Much
   published material still shows `navigator`. We feature-detect both
   (`document.modelContext ?? navigator.modelContext`) so the page survives the
   object moving again.

2. **`requestUserInteraction()` does not exist in Chrome 151.** The approval
   gate was designed around it. It is not on the object, so we built the gate
   ourselves with a native `<dialog>` that renders the exact draft and requires
   an explicit click. The user-visible guarantee is unchanged — an
   agent-initiated action cannot complete without human confirmation of its
   contents — but the page enforces it rather than the browser. When the API
   ships it is a small swap, and we keep the fallback regardless: a page should
   not lose its safety gate on a browser without the flag.

3. **Graceful absence.** With no `modelContext`, registration is skipped, a
   status badge explains that an agent-capable browser is needed for the agent
   half, and the page keeps working as a normal web app.

We also shipped `probe.html`, a standalone environment check that reports which
object exists, whether `registerTool()` accepts a tool, whether
`requestUserInteraction()` is present, and whether a live API call succeeds from
page context — plus a Playwright script that runs it against real Chrome and
exits non-zero on failure. It is how we found points 1 and 2, and it is in the
repository for anyone reproducing this on a different build.

---

## How we built it

Plain HTML, CSS and ES modules. An API client module wrapping the public TAAMs
endpoints, a UI layer with all interactions exposed as callable functions, and a
thin WebMCP layer whose handlers delegate to those functions. Verified against
Chrome 151 with the WebMCP flag enabled.

---

## Challenges

- **The spec surface moved under us.** `document` versus `navigator`, and a
  missing `requestUserInteraction()`. Solved by probing the browser first and
  writing that probe down as a test rather than trusting documentation.
- **Writing tool descriptions that prevent quiet wrong answers.** Lookups are
  keyed on the canonical Korean product name; passing a translated string
  returns an empty result rather than an error. An agent would narrate that as
  "no imports found." The descriptions state explicitly that the exact returned
  name must be passed onward.
- **Keeping Tier B honest.** It would have been easier to refetch on pin or
  highlight. Holding those two tools to zero network requests is what makes
  "this could only happen in the page" a demonstrable claim instead of a slogan
  — open the network tab and watch nothing fire.

---

## What we learned

Building the same capability twice — once as a remote MCP server, once as
WebMCP — made the distinction sharp. A remote server is good at answering. A
WebMCP page is good at *working alongside you*. For anything where the human
must approve the outcome, the second is not a nicer version of the first; it is
a different thing.

---

## What's next

Extending screen control to the marketplace side of TAAMs, so an agent can
assemble a shortlist of directly sourced products while the buyer watches, and
replacing our approval dialog with `requestUserInteraction()` once it ships,
keeping the local dialog as a fallback.

---

## Built with

HTML, CSS, vanilla JavaScript (ES modules), WebMCP
(`document.modelContext.registerTool`), the public TAAMs API, Playwright for
environment verification. No frameworks, no build step, no dependencies.

---

## New work statement

Everything in this repository was created after 2026-08-25: the page, all seven
tool definitions and handlers, the comparison board, the country highlight
logic, the RFQ draft-and-approve flow, the API client, the environment probe and
the Playwright check.

Pre-existing and not submitted: the TAAMs platform and its public read API,
which this page calls as a data source in the way any third party could. No
TAAMs server code was written or modified for this entry. TAAMs separately
operates a remote MCP server; it is a different product and shares no code with
this submission.

---

## Links

- Repository: https://github.com/taamslabglobal-code/taams-webmcp
- Live demo: https://taams-sourcing-desk.netlify.app
- Demo video: https://youtu.be/z68JTa_CJrI
- TAAMs: https://taamsglobal.com
- License: MIT — Copyright (c) 2026 Jongseok Mun (TAAMs)
