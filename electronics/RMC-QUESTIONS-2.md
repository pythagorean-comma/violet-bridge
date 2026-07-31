# Questions for RMC since round one

Follows `RMC-QUESTIONS.md` (round one, seven questions). Answers and their
consequences live in `STATE.md`; this file holds the outgoing wording.

---

## Round two — sent 2026-07-30, answered

One question only: does freeing DIN pins 7 & 8 require the Poly-Drive II to be
modified, and could a battery pack instead be connected to those pins — at the
PD2 end, or between the instrument socket and our board?

**Answered.** RMC perform the modification themselves when they assemble our
Poly-Drive II; the PD2 supplies the rails; power management stays in the PD2
with the instrument electronics slaved to it. Verbatim reply in `STATE.md`.

That closed the modification scope, the reversibility and warranty questions,
and the battery-life question in one go — see "What the third reply changed".

---

## Round three — to send

**No attachments.** Still no new drawing; the schematic on file is the
superseded ±9 V charge-pump design.

**Subject: Pizz/arco board — two things, and one number we still need**

That's clear, thank you — and good to know pins 7 & 8 will be handled at
assembly. Your battery arithmetic tallies with ours: a 1350 mAh cell at 3.7 V
is about 5 Wh, which through a boost converter to 9 V lands almost exactly on
your 420 mAh, so the 70 hours looks right rather than optimistic.

**1. The USB socket — one thing to check before you fit one.**

Charging is fine. What we want to be sure about is leaving it *powered* from
USB, as you suggest for keeping the battery topped up.

As we understand the supply, the battery's negative terminal is the −4.5 V
rail, because the splitter's midpoint is signal ground. So if the USB socket's
ground is common with the battery negative, and it's fed from an earthed source
— a computer, or a class-I supply — while the Poly-Drive's output is connected
to an earthed mixer, the −4.5 V rail would be tied to earth through the audio
ground. That's a short across the lower half of the splitter.

Occasional charging can always be done with everything unplugged, so it only
really bites in the permanently-powered case. Is the charging circuit isolated,
or is running it continuously from USB something to avoid?

**2. Do the elements ever exceed about 4 V peak on a hard pizzicato?**

This is the last thing we need before laying out the board, and I don't think
it's got through the previous two rounds, so here it is on its own.

Your drawing specified 12 V, giving ±6 V rails and about ±5.85 V of swing.
±4.5 V gives about ±4.35 V. There's no gain anywhere on our board — the buffer
is unity and the all-pass is ±1 — so the limit is simply the white element's
own open-circuit peak into your 3M3.

What concerns us isn't clipping as such, but *which* element clips. The red
element runs straight to the DIN and never passes through an op-amp; only the
white one is buffered. So if the white one runs out of headroom on a hard
attack, the two elements stop summing at equal weight — differently on each
string, and only at high level. That's precisely the string balance the matched
capacitors exist to protect.

If they stay well under 4 V we'll build it exactly as you've described. If they
can reach it, there's nothing on the board to trim — with no gain in the path
there's no gain to reduce — so we'd need to talk about the supply again, which
we'd rather not do if we can avoid it.

Behind that: was the 12 V in your drawing chosen for headroom, or simply what
the wallwart happened to supply?

**3. Confirming the polarity.** We'll print pin 7 = +4.5 V, pin 8 = −4.5 V on
the board and build the loom to match. Since you're wiring the Poly-Drive end,
just say if you'd rather it were the other way round.

---

## Why it is worded this way

- **The USB question leads even though the element peak is the blocker**,
  because it is time-critical in a way the other is not: they are about to
  assemble the unit, and fitting the socket is a decision being made now.
- **It is asked, not asserted.** They designed the Poly-Drive and may already
  isolate the charging circuit. Stating our reasoning lets them correct the
  premise rather than just the conclusion.
- **It separates charging from powering.** Without that distinction the answer
  is "of course you can charge it", which is true and not the question.
- **Question 2 keeps the framing that took the most work**: no gain in the
  path, so the limit is the element's own peak; and *which* element clips,
  which connects it to string balance — something they have twice said they
  care about. "Will it clip?" invites "should be fine."
- **It states the consequence without naming the fallback.** Earlier drafts
  mentioned the charge-pump board. That was right when the supply was still
  open; now that RMC have recommended keeping power management in the
  Poly-Drive, offering an alternative in the same breath as asking their advice
  reads as arguing. "We'd need to talk about the supply again" says the same
  thing and leaves the next move theirs.
- **It acknowledges their arithmetic by checking it**, not by thanking them for
  it. The 1/3 derating looks like caution and is actually the boost-conversion
  loss; showing that we followed it is worth more than agreement.
- **Question 3 is a statement with an exit**, not a question. They called the
  polarity arbitrary, so the useful thing is to fix it and let them object.

## Settled, and already acted on

- **1.8 nF C0G/NP0**, specified ±2% rather than the ±5% they accepted, all six
  from a single reel so the channel-to-channel spread is far tighter than the
  tolerance band.
- **Shell/shield as the single ground**, carrying audio only; no DC path from
  either rail to ground anywhere on the board.
- **Switch closed = elements in phase = pizz**, open = arco; rest position is
  arco.
- The abrasive-trimming tip: unusable on a machine-assembled board, kept as a
  field-service note.
