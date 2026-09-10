# Asking the human for exactly one thing

You cannot upload, compile, clone, change survey state, export or delete. Every one
of those is a round trip through a person, and a round trip is the most expensive
thing in this workflow. The request is therefore an engineered artifact, not a
sentence you improvise.

`dq.py handoff <action>` renders these templates with real paths. The
`<host>`, `<company>` and `<server_root>` placeholders below are filled from
`config.json`, so a template never carries a guessed value.

## Rules

1. **One action per request.** If two things are needed, say `(1 of 2)` and send
   the second only after the first returns. A person given three tasks does two.
2. **Name the artifact you need back**, explicitly. "Send back: the new numeric
   survey ID." Without this you get "done" and still cannot proceed.
3. **Ask for error text verbatim.** A paraphrased compiler message costs another
   round trip. Say so in the request.
4. **State the reason in one line.** A person who understands the constraint stops
   working around it. A person who does not will helpfully edit the source survey.
5. **Say what not to touch**, when there is something adjacent and tempting.
6. **Give absolute local paths and absolute server paths.** Never "the lib folder".
7. **Never ask for a judgement you should have made.** If a decision is yours,
   make it and say what you chose.

## Templates

### `clone` — a survey to test in

```
ACTION NEEDED (1 of 1)

In Decipher, duplicate survey <company>/<source>.
Do not edit <source> itself.

Download the untouched duplicate to:
    incoming/<new-id>/

Send back: the new numeric survey ID.

Why: /lib/<dq>/vN is not compiled as a survey. A DQ can only run through a
sibling numeric survey that references its version.
```

### `upload-package` — the DQ itself

```
ACTION NEEDED (1 of 2)

Upload as a whole directory, not file by file:
    local   test_environment/lib/<name>/v<N>/
    server  <server_root>/<company>/lib/<name>/v<N>/

<n> files, <bytes> bytes. Checksums below — compare after upload.
Do not create a lib directory under any other company.

Send back: confirmation, or any error text verbatim.

<sha256 manifest>
```

### `upload-survey` — the numeric survey

```
ACTION NEEDED (2 of 2)

Upload only this file:
    local   test_environment/<id>/survey.xml
    server  <server_root>/<company>/<id>/survey.xml

Also upload these static assets the demo needs:
    <list, or "none">

Do not upload uids.bin, original.bin, the pickles, or any log — those are the
server's, not ours.

Send back: confirmation, or any error text verbatim.
```

### `compile` — and what to look at

```
ACTION NEEDED (1 of 1)

Compile survey <id> in Decipher.

If it compiles, open it with a record assigned:
    https://<host>/survey/selfserve/<company>/<id>?list=<n>&<params>

Look for, and tell me about any of these:
    - <archetype-specific list, e.g. "the first video plays with sound on tap">
    - radio buttons or text inputs visible anywhere on the page
    - any red configuration-error panel
    - anything in the browser console

Send back: the compiler output verbatim if it failed, or the console text
verbatim if anything appeared there. Not a summary.

Why: the compiler names the exact element and attribute it rejected. A summary
loses the part I need.
```

`compile` for a media archetype adds:

```
    Please use a fresh profile or a private window.
    A browser that has already played video on this origin is allowed to
    autoplay with sound, so it will hide the very failure this checks for.
```

### `state` — moving to testing

```
ACTION NEEDED (1 of 1)

Set survey <id> to state="testing".

Why: dev mode does not create respondent records, so no exported data exists to
check against. Data acceptance needs testing state.

Send back: confirmation.
```

### `export` — the only real acceptance evidence

```
ACTION NEEDED (1 of 1)

After running the fixture below, export the data for survey <id> and send the
row for that respondent.

Fixture:
    <exact ordered actions>

Send back: the exported row, or the file.

Why: a correct screen does not prove a correct dataset. Hidden inputs can look
right and still be discarded on submit, so the export is the only evidence that
settles it.
```

### `confirm` — a fact only the human can supply

```
QUESTION (1 of 1)

<one question>

Why I cannot determine it: <one line>
```

Use this for things genuinely outside the repository — a vendor account setting, a
CDN hostname, whether a study accepts silent exposure. Not for decisions you should
make yourself.

## After the result comes back

Say plainly which evidence class you now have, and what is still missing:

> Compiled, and a respondent has been through it. Not yet proven: exported data,
> and the iOS journey. `verify` is clean, which is structural only — it does not
> execute the DQ.

Never let "it compiled" become "it works".
