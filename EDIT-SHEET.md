# Edit sheet — cutting the demo to 2:54

Every timestamp below was measured off the actual files, not estimated.

## Source material

| Clip | File | Length |
|---|---|---|
| **A** | `takeA-human-search.mp4` | 19.9s |
| **B** | `ChatGPT 2026-09-01 22-20-16.mp4` | 171.6s |
| **C** | `takeC-human-clicks.mp4` | 28.9s |
| Voice | trimmed narration | **174.3s (2:54.3)** |

Target **2:54**, hard limit **3:00**.

## What happens when, inside clip B

Measured from a contact sheet of the recording:

| Time in B | On screen |
|---|---|
| 0–38s | Agent opens the page, inspects it, answers "what product?" |
| ~40s | Question 1 sent; agent states its plan ("pin both, then highlight") |
| 40–78s | Lookups run: price card, importer list, supplier table fill |
| **78–86s** | **Both cards land on the board** — Thailand $6.47, Brazil $5.16 |
| 86–110s | Thailand chip lit, Brazil dimmed in the table |
| ~118s | Question 2 sent |
| **126s** | **Approval modal opens** and stays up |
| 126–171s | Modal held, then Approve |

Clip B alone is 171.6s against a 174.3s narration — so B has to be cut, not
padded, and everything else has to fit around it.

---

## Cut plan — narration drives, picture follows

Narration paragraph numbers match `VIDEO-SCRIPT.md` §3.

| Out | Narration | Source | In-point | Note |
|---|---|---|---|---|
| **0:00–0:26** | ① ② | Black + text | — | No page yet. Two lines fade in, then three words. |
| **0:26–0:48** | ③ | **A** 0:00–0:20 | — | Person types `mango`, page fills. Hold on `$5.07/kg`. |
| **0:48–1:00** | ④ | **B** 0:30–0:42 | 30s | Badge `Agent tools: 7 ready`, question 1 visible in the panel. |
| **1:00–1:26** | ⑤ | **B** 0:42–1:08 | 42s | Lookups landing. **Cut the agent's 38s of opening chatter** — start after question 1. |
| **1:26–1:52** | ⑥ | **B** 1:14–1:40 | 74s | ⭐ Cards appear ~78s, highlight follows. **Hold 2s on the empty Network tab.** |
| **1:52–2:26** | ⑦ | **B** 1:58–2:32 | 118s | Question 2 → modal at 126s. **Hold 4s on the modal**, then Approve. |
| **2:26–2:42** | ⑧ | **C** 0:08–0:24 | 8s | Person clicks pin / chip / draft by hand. Skip C's own search. |
| **2:42–2:55** | ⑨ | **B** freeze at 1:30 | — | Freeze the two-card board, zoom out slightly, URL caption. |

**Total 2:55.** Clip B contributes about 112s of its 171s; the 38s of opening
chatter and the dead time before question 2 are what get cut.

---

## Three cuts that matter

**1. Drop B's first 30 seconds.** The agent spends them saying it will open the
page and asking which product. The narration is on paragraph ④ by then. Start B
where question 1 is on screen.

**2. Do not cut across 1:14–1:40 of B.** That stretch is the entry: two cards
landing, Thailand lighting up, Brazil dimming. It is the only footage a remote
MCP server could not produce, and it is what paragraph ⑥ is describing.

**3. Hold the modal for a full 4 seconds** at B 2:06. A judge has to be able to
read `Nothing is sent until you click Approve` and the four draft fields. Cutting
away early turns the strongest safety claim into a flash.

---

## Captions — five, no more

| At | Text |
|---|---|
| 0:30 | `Tier A — lookup` |
| 1:28 | `Tier B — screen control` |
| 1:36 | `0 network requests` (arrow to the Network tab) |
| 1:56 | `Tier C — human approval` |
| 2:48 | `taams-sourcing-desk.netlify.app` · `MIT licensed` |

---

## Before upload

- [ ] Length **under 3:00** — measure the export, do not trust the timeline
- [ ] Audio present end to end
- [ ] Both cards legible: `MANGO · Thailand $6.47/kg` / `MANGO · Brazil $5.16/kg`
      — and Brazil reads **5 suppliers**, not 0
- [ ] No personal data in frame (sidebar stays collapsed throughout)
- [ ] Approval modal text readable at full size
- [ ] YouTube visibility **Public**
