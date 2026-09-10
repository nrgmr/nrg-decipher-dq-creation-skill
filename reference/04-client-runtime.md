# The client runtime: CSS, selectors, loaders, media

The previous knowledge base had no chapter here. A gap analysis of 23 behaviours
learned the hard way scored 5 documented, 9 partial, 9 absent — and the absences
were not random. Everything documented concerned XML structure and governance;
everything absent concerned the browser. Every entry below cost at least one
server round trip.

## The page your DQ lands on is not empty

The survey theme is already there, and it owns names you will reach for.

**VERIFIED-55C 2026-09-10.** The Forsta theme defines `.grid`, `.cell`, `.hidden`,
`.modal` and `.close`, and a DQ's own `question.left` override may itself emit
`class="cell ..."`. An unscoped `$('.cell').css({...})` therefore writes inline
styles to every grid cell on the page. On a page carrying 719 capture inputs and 51
question rows that is hundreds of elements and thousands of style mutations, at
`window.load`, exactly when the first frame should be rendering.

Worse than slow: **index-based selection addresses the wrong element.**
`$('.cell').eq(3)` was meant to hide the fourth watermark tile. The question's row
cells precede the watermark cells in document order, so it hid a row label and the
watermark showed all nine tiles instead of three. The bug was invisible because the
symptom was "the watermark looks a bit wrong".

Scope every selector to the host element. `#overlay .cell`, never `.cell`.

## Specificity you cannot win

**VERIFIED-55C 2026-09-10.** Rules inherited from a ported stylesheet that combine
`!important` with **ID** selectors cannot be reliably overridden by class
selectors, however many `!important` flags you add. Count IDs, not exclamation
marks.

Four consecutive passes on one package were specificity fights against inherited
overlay rules, and twice a fix broke something an earlier pass had set: an
`!important` white added to beat an inherited grey also beat the selected-state
colours, which had none.

**The durable fix is not to inherit the rules at all.** Deleting the inherited
block took a 26.8 KB stylesheet to 17.1 KB and left exactly three `!important`
declarations in the whole overlay, all of them `pointer-events: auto` where the
theme genuinely competes. Overriding rule by rule never converged; deleting
converged immediately.

Corollary: when you port a stylesheet from a working survey, port only the rules
you need. A wholesale copy brings its cascade with it.

## Suppressing the question title

**VERIFIED-55C 2026-09-10.** Hiding it with
`#question_<label> .question-text { display: none !important }` depends on the
theme naming that class. Production instead put the title inside
`<div id="question_text_<label>" style="display:none">`, which depends on nothing.
Prefer the markup approach.

Separately: an embedded third-party player may render its own title dock
(`vjs-dock-text`, `vjs-title-bar`). That is the player's chrome, not the survey's,
and needs suppressing separately. A production script did so; the DQ port
classified that script as dead and dropped it, so a title sat above the video for
nine versions and was worked around with a 42-pixel nudge.

## Selector engines

**VERIFIED-55C 2026-09-10.** `input:text` is a jQuery/Sizzle **extension**
selector, not CSS. `querySelectorAll` throws on it, so Sizzle walks the subtree in
JavaScript. Use `input[type="text"]` or a class.

This matters when it is hot. An uncached helper doing one id lookup plus two full
subtree traversals per call, invoked about twelve times a second from a
`timeupdate` handler, is on the order of ten thousand subtree traversals per
respondent — competing with video decode on exactly the low-end handsets where
smoothness is already worst. Memoise lookups whose target cannot change.

## Script loading

**VERIFIED-55C 2026-09-10.** `jQuery.getScript(url)` is
`$.ajax({dataType: "script"})`, and jQuery's script prefilter forces
`cache: false`, appending a cache-busting parameter. A large third-party bundle is
therefore re-downloaded for every respondent and every page view. It is also
fetched by XHR, so the URL is invisible to the browser's preload scanner and its
DNS, TCP and TLS handshakes cannot begin early.

Use a plain `<script>` element with `onload`/`onerror`, and start the download
during page parse with `<link rel="preload" as="script">` plus a `preconnect` for
the origin.

Do not guess a hostname for a `preconnect`. A guessed Playback API host was
correctly rejected by the origin allowlist; the real one is compiled into a vendor
bundle and is not discoverable from the repository. Expose it as a parameter and
have a human confirm it in the network panel.

## Media and autoplay

**VERIFIED-55C 2026-09-10.** Browsers block **unmuted** autoplay without a prior
user gesture. `play()` returns a promise that rejects, and a rejection swallowed by
an empty `catch` produces a frozen first frame with no console error, no capture
written, and nothing in the export to distinguish it from a respondent who did not
watch.

This is the worst failure shape in the whole corpus: it works on the machine of
whoever tests most, because a high media-engagement score for the origin permits
unmuted autoplay, and it fails for a share of real respondents.

Two acceptable designs:

- **A tap-to-start gate.** One full-screen tap before the stimulus. The tap is the
  gesture, so sound is legal from the first frame, and it is also what makes a
  muted `play()`/`pause()` priming pass legal for any second player. This is
  correct for research validity: a respondent who never unmutes would otherwise
  watch the whole stimulus silently while the data looks complete.
- **Muted autoplay with an explicit unmute affordance**, only when silent exposure
  is acceptable — and capture the mute state per stimulus so those sessions can be
  identified.

Never swallow the rejection. Log it and write it to a capture field.

Test this in a **fresh profile or private window**. On a browser that has already
played video on the origin, the broken version appears to work and the test
produces a false pass.

## Layout thrash and mid-animation resize

Reading a geometry property (`.width()`, `.height()`, `offsetHeight`,
`getBoundingClientRect`) forces synchronous layout. Reading one into a variable
that is never used is a forced reflow for nothing — one watermark engine did this
at `window.load`.

If a custom property drives the size of an animating element, re-setting it during
the animation resizes mid-flight. On mobile, browser chrome collapsing during a
swipe fires `visualViewport resize` and does exactly that. Debounce it, ignore
sub-pixel changes, and defer while a transition is in flight.

A cover panel held over an asynchronous handover needs a token guard: the deferred
cleanup belonging to advance N must not run during advance N+1. And it needs a
watchdog, or a stalled source leaves a black panel over the content forever.

## Cleanup and idempotence

- Strict mode; declare every variable. The official training example's undeclared
  loop index is teaching material, not production practice.
- Initialise from a host element unique to the adopting question; scope DOM queries
  and continue-button discovery to its form. Never fall through to a generic
  `button[type=submit]`, which on a multi-question page resolves to the wrong
  control.
- Make initialisation idempotent, and clean up listeners, timers and media on page
  exit.
- Lock competing navigation paths — click, swipe, wheel, `ended` — behind one
  guard, or one gesture fires two advances.
- Escape untrusted text before HTML insertion; prefer `textContent`.
- Support keyboard, focus and `prefers-reduced-motion` when the UI is interactive.
- Do not put a respondent identifier in `sessionStorage` or `localStorage`.

## Dead code has a cost

Commented-out blocks, unreferenced vendored assets and unused config files all ship
to every respondent, in every version, because packages are self-contained. Check
before carrying something forward: of 1,515 vendored Bootstrap rules in one
package, four matched anything the package used, and all four were already
redefined. One of them — `.close { opacity: .2 }` — was silently making a modal
dismiss button nearly invisible.
