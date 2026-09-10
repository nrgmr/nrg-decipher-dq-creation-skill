#!/usr/bin/env python3
"""Tests for the verify suite.

Two kinds, and both matter:

1. MUTATION tests. Scaffold a clean package, break exactly one thing, assert the
   check that owns that failure fires. One fixture per check, so a refactor
   cannot silently disable part of the safety net. These always run.

2. CORPUS tests. Run verify over a real DQ library and assert it reports defects
   you already know are there. A suite that passes everything proves nothing.
   These are opt-in, because the corpus is your library, not this repository's:

       export DECIPHER_DQ_CORPUS=/path/to/test_environment/lib
       cp tests/corpus_expectations.example.json tests/corpus_expectations.json
       # edit it to name packages, checks and expected substrings
       python3 tests/test_verify.py

   Without both the env var and the file, the corpus class skips and says so.

    python3 tests/test_verify.py
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from checks import run as run_checks                                # noqa: E402

FAILED = 2


def build_spec(name="choice_cards"):
    archetype = json.loads(
        (ROOT / "archetypes" / "basic" / "archetype.json").read_text())
    spec = archetype["spec_template"]
    spec.update({"name": name, "title": "Choice Cards",
                 "owner": "tests@example.invalid", "scope": "radio"})
    return json.loads(json.dumps(spec).replace("__DQ_UPPER__", name.upper()))


def dq(*args):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "dq.py")] + list(args),
        capture_output=True, text=True, cwd=str(ROOT))


class ScaffoldBase(unittest.TestCase):
    """Fixture only: a fresh, clean package per test, plus helpers.

    Deliberately holds no tests. Classes that only need the fixture inherit this
    rather than Scaffolded, so the mutation suite is not re-executed once per
    consumer.
    """

    name = "choice_cards"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dqtest-"))
        spec_path = self.tmp / "spec.json"
        spec_path.write_text(json.dumps(build_spec(self.name), indent=2))
        result = dq("new", "--archetype", "basic", "--spec", str(spec_path),
                    "--into", str(self.tmp / "lib"), "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.pkg = self.tmp / "lib" / self.name / "v1"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # helpers

    def findings(self):
        _, found = run_checks(self.pkg)
        return found

    def checks_firing(self, severity="error"):
        return {f.check for f in self.findings() if f.severity == severity}

    def edit(self, rel, old, new, count=1):
        path = self.pkg / rel
        text = path.read_text()
        self.assertIn(old, text, "fixture anchor missing in %s" % rel)
        path.write_text(text.replace(old, new, count))

    def assertFires(self, check, severity="error"):
        firing = self.checks_firing(severity)
        self.assertIn(check, firing,
                      "expected %s to fire; %s fired instead"
                      % (check, sorted(firing) or "nothing"))


class Scaffolded(ScaffoldBase):
    """One mutation per check: break exactly one thing, assert its owner fires."""

    # baseline

    def test_scaffold_is_clean(self):
        found = self.findings()
        problems = [str(f) for f in found]
        self.assertEqual([], problems,
                         "a fresh scaffold must verify clean:\n" +
                         "\n".join(problems))

    def test_scaffold_exercises_capture(self):
        """A scaffold whose demo cannot capture defers the riskiest test."""
        spec = json.loads((self.pkg / "spec.json").read_text())
        self.assertTrue(spec.get("capture"),
                        "the archetype must ship at least one capture field")
        survey = (self.pkg / "survey.xml").read_text()
        self.assertIn('dq:block id="capture"', survey)
        js = (self.pkg / "static" / ("%s_v1.js" % self.name)).read_text()
        self.assertIn("verifyCapture", js,
                      "the archetype must ship a startup handshake")

    def test_scaffold_demonstrates_two_instances_and_a_failure(self):
        survey = (self.pkg / "survey.xml").read_text()
        self.assertIn("Q_TWO_A", survey)
        self.assertIn("Q_TWO_B", survey)
        self.assertIn("Q_INVALID", survey)

    # structure

    def test_missing_required_file(self):
        (self.pkg / "spec.json").unlink()
        self.assertFires("required_files")

    def test_malformed_xml(self):
        self.edit("meta.xml", "</meta>", "</met>")
        self.assertFires("xml_wellformed")

    def test_broken_builder_template(self):
        self.edit("meta.xml", "<title>New Choice Cards question</title>",
                  "<title>Unclosed")
        self.assertFires("template_cdata")

    def test_server_owned_file_in_package(self):
        (self.pkg / "uids.bin").write_bytes(b"\x00")
        self.assertFires("forbidden_files")

    def test_include_wrong_case(self):
        self.edit("styles.xml", "choice_cards_v1.css", "Choice_Cards_V1.css")
        self.assertFires("include_case")

    def test_include_missing(self):
        self.edit("styles.xml", 'href="choice_cards_v1.css"',
                  'href="nope.css"')
        self.assertFires("include_targets")

    # styles

    def test_stylevar_default_of_two_quotes(self):
        self.edit("styles.xml",
                  'desc="Colour of the selected card border and its check mark.">#2bbdb9<',
                  'desc="Colour of the selected card border and its check mark.">""<')
        self.assertFires("stylevar_default_quotes")

    def test_unclassified_stylevar(self):
        spec = json.loads((self.pkg / "spec.json").read_text())
        spec["parameters"] = [p for p in spec["parameters"]
                              if p["name"] != "accent"]
        (self.pkg / "spec.json").write_text(json.dumps(spec, indent=2))
        self.assertFires("stylevar_classification")

    def test_template_reads_undeclared_stylevar(self):
        self.edit("styles.xml", "this.styles.choice_cards.accent or '#2bbdb9'",
                  "this.styles.choice_cards.nonexistent or '#2bbdb9'")
        self.assertFires("stylevar_reachability")

    def test_unbalanced_javascript(self):
        path = self.pkg / "static" / ("%s_v1.js" % self.name)
        path.write_text(path.read_text() + "\nfunction broken() {\n")
        self.assertFires("js_balance")

    def test_unbalanced_css(self):
        path = self.pkg / "static" / ("%s_v1.css" % self.name)
        path.write_text(path.read_text() + "\n.oops {\n")
        self.assertFires("css_balance")

    # demo

    def test_demo_sets_undeclared_attribute(self):
        """The v6/v7/v8 video_length defect."""
        self.edit("survey.xml", 'choice_cards:accent="#2bbdb9"',
                  'choice_cards:accent="#2bbdb9" choice_cards:not_a_thing="1"')
        self.assertFires("demo_attrs")

    def test_demo_invokes_wrong_version(self):
        self.edit("survey.xml", 'uses="choice_cards.1"', 'uses="choice_cards.2"')
        self.assertFires("demo_uses")

    def test_block_with_title_attribute(self):
        self.edit("survey.xml", "<suspend/>",
                  '<block label="B1" title="nope"><suspend/></block>', 1)
        self.assertFires("survey_grammar")

    def test_exec_variable_starting_with_underscore(self):
        self.edit("survey.xml", "<suspend/>",
                  "<exec>_rec = 1</exec>\n  <suspend/>", 1)
        self.assertFires("survey_grammar")

    def test_row_level_namespaced_attribute(self):
        self.edit("survey.xml", '<row label="r1">The first option</row>',
                  '<row label="r1" choice_cards:accent="#fff">The first option</row>')
        self.assertFires("survey_grammar")

    def test_unmet_requires(self):
        self.edit("survey.xml",
                  "<!-- dq:requires survey-attr extraVariables contains record -->",
                  "<!-- dq:requires survey-attr extraVariables contains showreview -->")
        self.assertFires("demo_requires")

    def test_demo_names_missing_asset(self):
        self.edit("survey.xml", "<title>Which of these appeals to you most?</title>",
                  "<title>See ghost.png</title>")
        self.assertFires("demo_assets")

    def test_unfenced_demo_is_a_warning_not_an_error(self):
        text = (self.pkg / "survey.xml").read_text()
        text = re.sub(r"<!--\s*dq:(block|endblock)[^>]*-->", "", text)
        (self.pkg / "survey.xml").write_text(text)
        ctx, found = run_checks(self.pkg)
        self.assertTrue(ctx.legacy)
        self.assertIn("demo_fences",
                      {f.check for f in found if f.severity == "warning"})

    # capture

    def test_suspend_between_question_and_capture(self):
        self.edit("survey.xml", "<!-- dq:block id=\"capture\"",
                  "<suspend/>\n\n  <!-- dq:block id=\"capture\"")
        self.assertFires("capture_same_page")

    def test_capture_row_count_disagrees_with_spec(self):
        self.edit("survey.xml", '    <row label="r10">Row 10</row>\n', "")
        self.assertFires("capture_contract")

    def test_capture_field_missing_from_demo(self):
        spec = json.loads((self.pkg / "spec.json").read_text())
        spec["capture"].append({"label": "GHOST", "type": "text", "rows": 0,
                                "desc": "never declared"})
        (self.pkg / "spec.json").write_text(json.dumps(spec, indent=2))
        self.assertFires("capture_contract")

    def test_number_capture_type_is_flagged(self):
        self.edit("survey.xml", '<text label="CHOICE_CARDS_ORDER" size="12"',
                  '<number label="CHOICE_CARDS_ORDER" size="12"')
        self.edit("survey.xml", "</text>\n  <!-- dq:endblock -->",
                  "</number>\n  <!-- dq:endblock -->")
        self.assertFires("capture_number_type", severity="warning")

    def test_hand_edited_generated_fragment(self):
        path = self.pkg / "capture_block.xml"
        path.write_text(path.read_text() + '\n<text label="SNEAKY"/>\n')
        self.assertFires("generated_sync")

    def test_generated_header_removed(self):
        path = self.pkg / "capture_block.xml"
        text = path.read_text().split("\n", 1)[1]
        path.write_text(text)
        self.assertFires("generated_sync")

    def test_extract_is_idempotent(self):
        before = (self.pkg / "capture_block.xml").read_bytes(), \
                 (self.pkg / "IMPORT.md").read_bytes()
        result = dq("extract", str(self.pkg), "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        after = (self.pkg / "capture_block.xml").read_bytes(), \
                (self.pkg / "IMPORT.md").read_bytes()
        self.assertEqual(before, after)

    # runtime

    def test_unscoped_theme_selector(self):
        path = self.pkg / "static" / ("%s_v1.js" % self.name)
        path.write_text(path.read_text().replace(
            '    var MIN_ROWS = 2;',
            '    var MIN_ROWS = 2;\n    function bad() { $(".cell").eq(3).css({}); }'))
        self.assertFires("unscoped_selectors")

    def test_swallowed_promise_rejection(self):
        path = self.pkg / "static" / ("%s_v1.js" % self.name)
        path.write_text(path.read_text().replace(
            '    var MIN_ROWS = 2;',
            '    var MIN_ROWS = 2;\n'
            '    function bad(p) { p.play().catch(function () {}); }'))
        self.assertFires("swallowed_rejection")

    def test_getscript_loader(self):
        path = self.pkg / "static" / ("%s_v1.js" % self.name)
        path.write_text(path.read_text().replace(
            '    var MIN_ROWS = 2;',
            '    var MIN_ROWS = 2;\n'
            '    function bad() { jQuery.getScript("https://x.decipherinc.com/a.js"); }'))
        self.assertFires("script_loader")

    def test_unsafe_evaluation(self):
        path = self.pkg / "static" / ("%s_v1.js" % self.name)
        path.write_text(path.read_text().replace(
            '    var MIN_ROWS = 2;',
            '    var MIN_ROWS = 2;\n    function bad(t) { return eval(t); }'))
        self.assertFires("unsafe_evaluation")

    def test_unapproved_origin(self):
        path = self.pkg / "static" / ("%s_v1.css" % self.name)
        path.write_text(path.read_text() +
                        '\n.x { background: url(https://evil.example.com/a.png); }\n')
        self.assertFires("external_origins")

    def test_production_company_reference(self):
        path = self.pkg / "static" / ("%s_v1.js" % self.name)
        path.write_text(path.read_text().replace(
            '    var MIN_ROWS = 2;',
            '    var MIN_ROWS = 2;\n    var root = "/home/hermes/v2/selfserve/53b";'))
        self.assertFires("external_origins")

    def test_hardcoded_survey_id(self):
        path = self.pkg / "static" / ("%s_v1.js" % self.name)
        path.write_text(path.read_text().replace(
            '    var MIN_ROWS = 2;',
            '    var MIN_ROWS = 2;\n'
            '    var base = "https://host.example.invalid'
            '/survey/selfserve/55c/990001";'))
        self.assertFires("hardcoded_survey")

    def test_undefined_method_call(self):
        path = self.pkg / "static" / ("%s_v1.js" % self.name)
        path.write_text(path.read_text().replace(
            "        this.build();", "        this.buidl();"))
        self.assertFires("call_graph")

    # version

    def test_filename_version_disagrees(self):
        old = self.pkg / "static" / ("%s_v1.js" % self.name)
        old.rename(self.pkg / "static" / ("%s_v2.js" % self.name))
        self.edit("styles.xml", "%s_v1.js" % self.name, "%s_v2.js" % self.name)
        self.assertFires("version_coherence")

    def test_stale_version_in_user_facing_string(self):
        path = self.pkg / "static" / ("%s_v1.js" % self.name)
        path.write_text(path.read_text().replace(
            '"This question is not available."',
            '"This v9 question is not available."'))
        self.assertFires("stale_version_strings")


class Bump(ScaffoldBase):
    def test_bump_rewrites_only_anchored_sites(self):
        marker = "// keep v1 in prose, it is not a version site\n"
        path = self.pkg / "static" / ("%s_v1.js" % self.name)
        path.write_text(marker + path.read_text())
        result = dq("bump", str(self.pkg), "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        v2 = self.pkg.parent / "v2"
        self.assertTrue(v2.is_dir())
        moved = (v2 / "static" / ("%s_v2.js" % self.name)).read_text()
        self.assertIn(marker.strip(), moved,
                      "bump must not rewrite an incidental v1 in prose")
        _, found = run_checks(v2)
        self.assertEqual([], [str(f) for f in found if f.severity == "error"])

    def test_bump_leaves_the_source_untouched(self):
        before = sorted(p.name for p in (self.pkg / "static").iterdir())
        dq("bump", str(self.pkg), "--apply")
        after = sorted(p.name for p in (self.pkg / "static").iterdir())
        self.assertEqual(before, after)

    def test_bump_refuses_an_existing_target(self):
        dq("bump", str(self.pkg), "--apply")
        again = dq("bump", str(self.pkg), "--apply")
        self.assertEqual(3, again.returncode, again.stdout + again.stderr)


class Bundle(ScaffoldBase):
    """The chat-runtime delivery path: a zip the user can actually act on."""

    def zip_names(self, path):
        import zipfile
        with zipfile.ZipFile(path) as archive:
            return archive.namelist()

    def test_bundle_mirrors_the_server_layout(self):
        out = self.tmp / "dist"
        result = dq("bundle", str(self.pkg), "--out", str(out), "--apply")
        self.assertEqual(0, result.returncode, result.stderr)
        target = out / ("%s_v1.zip" % self.name)
        self.assertTrue(target.is_file())
        names = self.zip_names(target)
        self.assertIn("UPLOAD.md", names)
        self.assertIn("lib/%s/v1/meta.xml" % self.name, names)

    def test_upload_instructions_name_the_destination(self):
        import zipfile
        out = self.tmp / "dist"
        dq("bundle", str(self.pkg), "--out", str(out), "--apply")
        with zipfile.ZipFile(out / ("%s_v1.zip" % self.name)) as archive:
            text = archive.read("UPLOAD.md").decode("utf-8")
        self.assertIn("lib/%s/v1/" % self.name, text)
        self.assertIn("/lib/%s/v1/" % self.name, text,
                      "UPLOAD.md must give the absolute server path")
        self.assertIn("uids.bin", text,
                      "UPLOAD.md must say which server-owned files not to upload")

    def test_bundle_refuses_a_package_with_errors(self):
        self.edit("styles.xml", "<stylevar", "<bogus", count=1)
        out = self.tmp / "dist"
        result = dq("bundle", str(self.pkg), "--out", str(out), "--apply")
        self.assertEqual(FAILED, result.returncode,
                         "a red gate must block the download")
        self.assertFalse((out / ("%s_v1.zip" % self.name)).exists())

    def test_force_overrides_but_says_so(self):
        self.edit("styles.xml", "<stylevar", "<bogus", count=1)
        out = self.tmp / "dist"
        result = dq("bundle", str(self.pkg), "--out", str(out), "--apply", "--force")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("--force", result.stdout)

    def test_survey_file_gets_its_own_destination(self):
        import zipfile
        survey = self.tmp / "990123" / "survey.xml"
        survey.parent.mkdir(parents=True)
        survey.write_text("<survey/>\n")
        out = self.tmp / "dist"
        result = dq("bundle", str(self.pkg), "--out", str(out), "--apply",
                    "--survey-file", str(survey), "--survey", "990123")
        self.assertEqual(0, result.returncode, result.stderr)
        with zipfile.ZipFile(out / ("%s_v1.zip" % self.name)) as archive:
            names = archive.namelist()
            text = archive.read("UPLOAD.md").decode("utf-8")
        self.assertIn("surveys/990123/survey.xml", names)
        self.assertIn("/990123/survey.xml", text)


class ClaudeZip(unittest.TestCase):
    """claude.ai rejects a zip whose SKILL.md is not inside a folder."""

    def test_archive_nests_the_skill_folder(self):
        import zipfile
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_claude_zip.py")],
            capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(0, result.returncode, result.stderr)
        target = ROOT / "dist" / ("%s.zip" % ROOT.name)
        self.assertTrue(target.is_file())
        with zipfile.ZipFile(target) as archive:
            names = archive.namelist()
        self.assertIn("%s/SKILL.md" % ROOT.name, names)
        self.assertEqual([], [n for n in names if "/" not in n],
                         "no entry may sit at the archive root")

    def test_personal_config_is_never_packaged(self):
        import zipfile
        local = ROOT / "config.local.json"
        created = not local.is_file()
        if created:
            local.write_text('{"host": "secret.internal.example"}\n')
        try:
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "build_claude_zip.py")],
                capture_output=True, text=True, cwd=str(ROOT))
            with zipfile.ZipFile(ROOT / "dist" / ("%s.zip" % ROOT.name)) as archive:
                names = archive.namelist()
        finally:
            if created:
                local.unlink()
        self.assertEqual(
            [], [n for n in names if n.endswith("/config.local.json")],
            "config.local.json holds one team's host and must not be shipped")

    def test_frontmatter_fits_the_documented_limits(self):
        import re
        block = (ROOT / "SKILL.md").read_text().split("---", 2)[1]
        name = re.search(r"^name:\s*(.+)$", block, re.M).group(1).strip()
        desc = re.search(r"^description:\s*(.+)$", block, re.M).group(1).strip()
        self.assertRegex(name, r"^[a-z0-9-]{1,64}$")
        self.assertNotIn("claude", name)
        self.assertNotIn("anthropic", name)
        self.assertEqual(ROOT.name, name,
                         "claude.ai takes the skill name from the folder")
        self.assertLessEqual(len(desc), 200, "claude.ai description limit")
        self.assertNotIn("<", desc)


class Guards(unittest.TestCase):
    def test_production_path_is_refused(self):
        result = dq("verify", "/tmp/prod_environment/whatever")
        self.assertEqual(3, result.returncode)
        self.assertIn("production", result.stderr)

    def test_handoff_names_a_return_artifact(self):
        for action, extra in (("clone", ["--source", "990001"]),
                              ("compile", ["--survey", "990002"]),
                              ("state", ["--survey", "990002"]),
                              ("export", ["--survey", "990002"]),
                              ("upload-survey", ["--survey", "990002"])):
            result = dq("handoff", action, *extra)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("ACTION NEEDED", result.stdout)
            self.assertIn("Send back:", result.stdout,
                          "%s must name the artifact it needs back" % action)

    def test_handoff_media_warns_about_a_warm_browser(self):
        result = dq("handoff", "compile", "--survey", "1", "--media")
        self.assertIn("fresh profile", result.stdout)

    def test_interview_available_for_every_archetype(self):
        for path in sorted((ROOT / "archetypes").iterdir()):
            if not path.is_dir():
                continue
            doc = json.loads((path / "archetype.json").read_text())
            self.assertTrue(doc.get("questions"),
                            "%s ships no interview" % path.name)
            for question in doc["questions"]:
                self.assertTrue(question.get("why"),
                                "%s: every question needs a why" % path.name)

    def test_templateless_archetype_redirects_to_basic(self):
        result = dq("new", "--archetype", "media-player", "--spec", "/dev/null",
                    "--into", "/tmp/nope", "--apply")
        self.assertIn("Scaffold from 'basic'", result.stderr)


CORPUS = os.environ.get("DECIPHER_DQ_CORPUS", "").strip()
EXPECTATIONS = ROOT / "tests" / "corpus_expectations.json"


class Corpus(unittest.TestCase):
    """Calibration against a real library, opt-in.

    A check suite that only ever runs against its own fixtures measures itself.
    Point this at a library whose defects you already know and it measures the
    suite instead. See the module docstring for the two things it needs.
    """

    @classmethod
    def setUpClass(cls):
        if not CORPUS:
            raise unittest.SkipTest("DECIPHER_DQ_CORPUS is not set")
        cls.lib = Path(CORPUS).expanduser().resolve()
        if not cls.lib.is_dir():
            raise unittest.SkipTest("%s is not a directory" % cls.lib)
        cls.expected = (json.loads(EXPECTATIONS.read_text())
                        if EXPECTATIONS.is_file() else {})

    def packages(self):
        """Every <name>/vN directory under the corpus root."""
        for name in sorted(self.lib.iterdir()):
            if not name.is_dir():
                continue
            for version in sorted(name.iterdir()):
                if version.is_dir() and re.fullmatch(r"v\d+", version.name):
                    yield version

    def test_no_check_crashes_on_real_input(self):
        """The one assertion that needs no expectations file.

        Real packages contain shapes no fixture anticipates. A check that
        raises is a check that silently stops defending anything.
        """
        seen = 0
        for package in self.packages():
            seen += 1
            _, found = run_checks(package)
            crashed = [str(f) for f in found if f.check == "check_crashed"]
            self.assertEqual([], crashed, "a check crashed on %s" % package)
        self.assertTrue(seen, "no <name>/vN packages found under %s" % self.lib)

    def test_known_defects_are_reported(self):
        """Each expectation names a defect you already know is in the corpus.

        corpus_expectations.json:

            {"<name>/<vN>": [{"check": "demo_attrs", "contains": "some_param"}]}
        """
        if not self.expected:
            self.skipTest("tests/corpus_expectations.json is absent or empty")
        for relative, wanted in sorted(self.expected.items()):
            if relative.startswith("_"):
                continue
            package = self.lib / relative
            if not package.is_dir():
                self.fail("%s names %s, which is not in the corpus"
                          % (EXPECTATIONS.name, relative))
            _, found = run_checks(package)
            for item in wanted:
                hits = [f for f in found if f.check == item["check"]]
                self.assertTrue(
                    hits, "%s: expected %s to fire and it did not"
                          % (relative, item["check"]))
                needle = item.get("contains", "")
                if needle:
                    self.assertTrue(
                        any(needle in f.message or needle in f.where
                            for f in hits),
                        "%s: %s fired but not about %r"
                        % (relative, item["check"], needle))


if __name__ == "__main__":
    unittest.main(verbosity=2)
