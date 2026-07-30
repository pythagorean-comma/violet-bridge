# Questions for RMC — the message as sent

This is the outward-facing wording, ready to paste. The **reasoning** behind
each question, and what we will do with each answer, lives in `NOTES.md` under
"Questions for RMC". Numbering matches between the two.

**Attach these three:**

- `fab/rmc-pizz-arco-schematic.pdf` — **essential.** Their channel circuit six
  times over, plus everything built around it that their drawing leaves
  undefined: supply, switching, protection, decoupling, connectors. The DIN
  pinout, pizz/arco and capacitor-pair questions all point at things visible
  on it.
- `fab/rmc-pizz-arco-bom.csv` — shows the part substitutions, which the body
  of the message also states outright.
- `build/board-top.png` — courtesy. It answers their original offer to have us
  do the layout. Decorative, not reviewable; expect nothing from it.

**Offer, do not attach** (one line in the message): the layout PDF
(`fab/rmc-pizz-arco-layout.pdf` — layered copper with reference designators,
the asset worth commenting on if they want to look at the layout), the netlist
(`build/verify.net`), and the gerbers.

**Never send the gerber zip unsolicited.** It is fabrication output, not
design: copper polygons with no nets, values or references. It needs a viewer
and ten files loaded, makes "did you implement my circuit correctly"
effectively uncheckable, and asks the wrong thing of the person who designed
the circuit.

The tiering is about making the message easy to answer, not about imposing.
Five attachments dilutes attention across all of them; three, each of which
supports a question being asked, is likelier to get every one opened. The rest
is one line away if they want it.

---

**Subject: Pizz/arco board — layout done; can it run on 9 V?**

The PCB layout is done. Six channels of your 2026-07-29 schematic, four
layers, 88 × 112 mm, all SMD, DRC clean and ready to fabricate. Schematic PDF,
bill of materials and a render of the board attached.

**Context, so the answers land in the right place:** we're mounting the board
*inside the instrument*, run from a regulated 9 V rechargeable pack rather
than a wallwart, so the instrument stays self-contained. It draws about
2.1 mA. The six channels leave on the DIN-8 to the Poly-Drive II.

**Where to look on the schematic.** Your channel signal path is unchanged, bar
one substitution: we used **OPA2191** rather than OPA191 — same family, but
dual, which halves the package count over six channels.

The rest of the sheet is ours, and none of it appears in your drawing:

- the mid-rail supply that generates the bipolar ground your schematic assumes
- the six analog switches and their control line
- input protection and bulk decoupling
- per-package decoupling
- the connectors: six saddle inputs, the DIN-8, the toggle and the supply

That's where all seven questions below land, so it's the part worth your time.

The switching is worth singling out. Your schematic shows a switch per
channel; bussing six channels to one mechanical switch would short them
together when open, so each channel gets its own CD4066B cell driven from a
single control line — three packages, using only the cells whose signal pins
are on the side the channels arrive from. Say if you'd rather we did any of
this differently.

Seven questions, but **question 1 is the one we really need** — if you answer
only one, please make it that. Happy to send the board layout, a netlist or
the gerbers if you'd like to look at any of those.

**1. Can this run on 9 V?**

Our reading is that only PZT 2 passes through the amplifiers — PZT 1 goes
straight to the output, so rail voltage doesn't affect it. At 9 V our rails
are ±4.5 V, giving about ±4.4 V of swing before the buffer and all-pass clip.
At your 12 V it would be ±5.9 V.

**Do the elements ever exceed about 4 V peak on a hard pizzicato?** If they
do, we'll fit an inline 9→12 V converter; if not, we'll stay at 9 V and keep
it simple.

And behind that: was the 12 V chosen for headroom, or simply what a wallwart
happened to supply? Were you perhaps picturing this in an outboard box near
the Poly-Drive rather than inside the instrument — in which case 12 V would
have cost you nothing, and we may have taken the design somewhere you didn't
intend. We'd rather know now than after it's installed.

**2. DIN-8 pinout.** We currently have pins 1–6 as channels 1–6, pin 7 as
ground, pin 8 unassigned. Can you confirm what the Poly-Drive II expects? We
need this before making the loom.

**3. DIN pin 8 — is it used?** Ground, shield, or something else? If it
carries a supply we could draw from, we could only use it if that supply is
*isolated from DIN ground*: our audio ground sits at the mid-rail, so a rail
referenced to pin 7 would give us a positive supply with no negative side for
signals to swing into. We need only ~2.1 mA, so it's worth asking.

**4. Element capacitance?** It sets the input high-pass corner against your
3M3. For the bottom string of a gamba (D2, 73 Hz) we'd want it comfortably
over 1 nF.

**5. Which switch position is pizz and which is arco?** Your drawing labels it
`[Space]`. On our board, switch closed grounds the all-pass, inverting PZT 2
relative to PZT 1.

**6. 220 pF ‖ 1.5 nF.** Is one of these meant to be select-on-test, or is the
pair simply how 1.72 nF was made up? We've fitted both as drawn.

**7. Does your DIN-8S socket have a switching contact?** There's no power
switch on the board, so a pack left connected would go flat in about ten days.
A switched socket would break the battery on unplugging, the way a guitar's
TRS jack does. If not, we'll fit a switch in the battery lead.

---

## Why it is worded this way

Kept here so the shape survives editing:

- **The pivotal question leads, and is in the subject line.** Ordering by what
  blocks the wiring loom put it third, buried inside a compound question. The
  right ordering is by what changes most if the answer surprises us: a wrong
  DIN pinout is a rewiring job at the socket, whereas a wrong supply
  assumption changes the battery, the compartment, the switch arrangement and
  whether the instrument can be self-contained at all.
- **Question 1 gives a threshold, not an open question.** "Does it exceed
  about 4 V?" is answerable from memory; "what is the peak output?" sends them
  to look something up. The 4 V leaves margin below our real 4.4 V limit.
- **"Why 12 V?" and "were you assuming an outboard box?" sit inside question 1**,
  because they are the same conversation. Split across a "Related:" and a
  postscript, as they were, both read as afterthoughts.
- **Questions 5 and 6 state our reading back**, so a misunderstanding on our
  part is cheap for them to correct before anything is fabricated.
- **It does not lead the witness.** Nowhere does it say "we think 9 V is fine,
  do you agree?" — that invites a rubber stamp instead of their actual view.
