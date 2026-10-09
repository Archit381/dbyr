"""Unit tests. Run from code/: python -m unittest discover -s tests -v"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from backtest.score import score_case  # noqa: E402
from dbyr import check_notices  # noqa: E402
from tabletop.run import run as run_tabletop  # noqa: E402
from tabletop.scenarios import SCENARIOS  # noqa: E402
from dbyr.validate import conduct  # noqa: E402
from dbyr import (all_views, check_lineage, check_opening, errors, linked_groups,  # noqa: E402
                  reconcile, schema_hash, validate_record)
from dbyr.ledger import Ledger  # noqa: E402

CASE = ROOT / "backtest" / "cases" / "hf-2026"


def load(name: str) -> dict:
    return json.loads((CASE / name).read_text(encoding="utf-8"))


def codes(findings) -> set[str]:
    return {f.code for f in findings}


class SchemaAndRules(unittest.TestCase):
    def setUp(self):
        self.intent = load("intent_run_a.json")
        self.closeout = load("closeout_run_a.json")

    def test_reconstructed_filings_pass_v01_rules(self):
        for name in ("intent_run_a.json", "intent_run_b.json", "closeout_run_a.json", "notice_n1.json", "notice_n2.json"):
            with self.subTest(name=name):
                self.assertEqual(errors(validate_record(load(name), profile="baseline")), [])

    def test_intake_review_rejects_reconstruction_for_dead_comms_criterion(self):
        # v0.3: every intake error traces to one first-party fact, that nothing could observe
        # agent-to-agent activity or tampering on the shared proxy.
        found = codes(errors(validate_record(self.intent)))
        self.assertEqual(found, {"dead_criterion", "comms_unmonitored", "shared_surface_floor"})

    def test_unknown_field_rejected(self):
        bad = copy.deepcopy(self.intent)
        bad["surprise"] = 1
        self.assertIn("schema", codes(validate_record(bad)))

    def test_bad_timestamp_rejected(self):
        bad = copy.deepcopy(self.intent)
        bad["filed_at"] = "7 May 2026"
        self.assertIn("schema", codes(validate_record(bad)))

    def test_safeguards_off_requires_t4(self):
        bad = copy.deepcopy(self.intent)
        bad["trigger_basis"] = ["T2"]
        self.assertIn("t4_missing", codes(validate_record(bad)))

    def test_safeguards_off_requires_signer(self):
        bad = copy.deepcopy(self.intent)
        del bad["safeguards_disabled"]["signer_role"]
        self.assertIn("schema", codes(validate_record(bad)))

    def test_pause_authority_must_be_declared_role(self):
        bad = copy.deepcopy(self.intent)
        bad["pause_criteria"][0]["authority_role"] = "R-nobody"
        self.assertIn("unknown_role", codes(validate_record(bad)))

    def test_scope_expansion_cannot_be_withheld(self):
        bad = copy.deepcopy(self.intent)
        bad["investigator_scope_expansion"]["committed"] = False
        self.assertIn("schema", codes(validate_record(bad)))

    def test_affected_party_must_be_accounted_for(self):
        bad = copy.deepcopy(self.closeout)
        bad["third_party_notifications"] = []
        self.assertIn("affected_party_unaccounted", codes(validate_record(bad)))

    def test_unnotified_party_needs_reason(self):
        bad = copy.deepcopy(self.closeout)
        bad["third_party_notifications"][0] = {"party": "Hugging Face", "affected_by": ["E6"], "notified": False}
        self.assertIn("schema", codes(validate_record(bad)))
        bad["third_party_notifications"][0]["not_notified_reason"] = "law enforcement hold"
        self.assertEqual(errors(validate_record(bad)), [])

    def test_notification_cannot_predate_event(self):
        bad = copy.deepcopy(self.closeout)
        bad["third_party_notifications"][0]["notified_at"] = "2026-07-01T00:00:00Z"
        self.assertIn("notified_before_event", codes(validate_record(bad)))

    def test_silent_scope_narrowing_rejected(self):
        bad = copy.deepcopy(self.closeout)
        bad["scope_requested_vs_granted"][0]["refusals"] = []
        self.assertIn("silent_scope_narrowing", codes(validate_record(bad)))

    def test_attested_absence_contradiction(self):
        bad = copy.deepcopy(self.closeout)
        bad["attested_absence"] = True
        self.assertIn("absence_contradicted", codes(validate_record(bad)))

    def test_undeclared_surface_is_flagged(self):
        self.assertIn("undeclared_surface", codes(validate_record(self.closeout)))


class Reconciliation(unittest.TestCase):
    def setUp(self):
        self.intent = load("intent_run_a.json")
        self.closeout = load("closeout_run_a.json")

    def test_reconstruction_reconciles(self):
        found = reconcile(self.intent, self.closeout)
        self.assertEqual(errors(found), [])
        # The lost tenth of trajectories is a recorded breach, not a reason to refuse the filing.
        self.assertEqual(codes(conduct(found)), {"retention_below_floor"})

    def test_honest_admission_is_never_refused(self):
        # A closeout that truthfully reports a reset during an open incident, with no snapshot,
        # lodges and carries a conduct finding. Refusing it would pay the filer to omit the reset.
        honest = copy.deepcopy(self.closeout)
        honest["surface_resets"][0]["snapshot_retained"] = False
        found = validate_record(honest)
        self.assertEqual(errors(found), [])
        self.assertIn("evidence_destroyed", codes(conduct(found)))

    def test_weak_monitoring_run_can_still_close_out(self):
        # No events and monitoring too weak to attest absence: lodges if the reason is stated.
        quiet = copy.deepcopy(self.closeout)
        for k in ("security_events", "pause_events", "containment_exceptions", "third_party_notifications",
                  "notice_ids", "internal_incidents", "config_changes", "surface_resets"):
            quiet[k] = []
        quiet["attested_absence"] = False
        self.assertIn("absence_basis_missing", codes(errors(validate_record(quiet))))
        quiet["absence_basis"] = "monitoring could not observe inter-agent activity, so absence is not attested"
        self.assertEqual(errors(validate_record(quiet)), [])

    def test_matched_event_without_pause_is_error(self):
        bad = copy.deepcopy(self.closeout)
        bad["pause_events"][1]["triggering_event_ids"] = ["E6"]  # drop E1, E2, E5
        self.assertIn("criterion_matched_no_pause_event", codes(reconcile(self.intent, bad)))

    def test_restart_by_wrong_role_is_error(self):
        bad = copy.deepcopy(self.closeout)
        bad["pause_events"][0]["restart"]["approved_by_role"] = "R-train"
        self.assertIn("restart_wrong_approver", codes(reconcile(self.intent, bad)))

    def test_amendment_required_on_restart(self):
        strict = copy.deepcopy(self.intent)
        strict["restart_protocol"]["intent_amendment_required"] = True
        self.assertIn("restart_without_amendment", codes(reconcile(strict, self.closeout)))

    def test_retention_floor_warning(self):
        self.assertIn("retention_below_floor", codes(reconcile(self.intent, self.closeout)))


class Lineage(unittest.TestCase):
    def setUp(self):
        self.a = load("intent_run_a.json")
        self.b = load("intent_run_b.json")
        self.c = load("closeout_run_a.json")

    def test_reconstruction_passes(self):
        self.assertEqual(errors(check_lineage([self.a, self.b], [self.c])), [])

    def test_missing_lineage_citation(self):
        b = copy.deepcopy(self.b)
        b["egress_topology"]["shared_surface_lineage"] = []
        self.assertIn("lineage_not_cited", codes(check_lineage([self.a, b], [self.c])))

    def test_open_exception_on_record_must_be_inherited(self):
        # A rolling closeout filed before run B, with an open exception on the shared surface.
        early = copy.deepcopy(self.c)
        early["filed_at"] = "2026-06-06T00:00:00Z"
        x1 = early["containment_exceptions"][0]
        x1["status"] = "open"
        x1.pop("closed_at")
        early["containment_exceptions"] = [x1]  # only what a 6 Jun closeout could contain
        found = check_lineage([self.a, self.b], [early])
        self.assertIn("inherited_exception_not_cited", codes(found))
        b = copy.deepcopy(self.b)
        b["egress_topology"]["inherited_exceptions"] = [{"run_id": "exploitgym-rl-a", "exception_id": "X1"}]
        self.assertNotIn("inherited_exception_not_cited", codes(check_lineage([self.a, b], [early])))

    def test_exception_filed_later_is_not_required(self):
        # The real closeout was filed after run B started, so B could not have cited it.
        self.assertNotIn("inherited_exception_not_cited", codes(check_lineage([self.a, self.b], [self.c])))

    def test_linked_groups(self):
        self.assertEqual(linked_groups([self.a, self.b]), [{"exploitgym-rl-a", "exploitgym-rl-b"}])


class Redaction(unittest.TestCase):
    def setUp(self):
        self.intent = load("intent_run_a.json")
        self.views = all_views(self.intent)

    def test_public_hides_restricted_and_sealed(self):
        pub = self.views["public"]
        self.assertIn("$commitment", pub["egress_topology"])
        self.assertIn("$commitment", pub["pause_criteria"])
        self.assertIn("$commitment", pub["safeguards_disabled"]["relaxed"])
        self.assertEqual(pub["safeguards_disabled"]["disabled"], True)
        self.assertEqual(pub["roles"][0]["title"], "Training run lead")

    def test_restricted_sees_restricted_not_sealed(self):
        res = self.views["restricted"]
        surface = res["egress_topology"]["writable_surfaces"][0]
        self.assertEqual(surface["persistence"], "cross_run")
        self.assertIn("$commitment", surface["detail"])

    def test_every_commitment_can_be_opened(self):
        # Sealed detail nested inside a restricted object: public commits to the whole
        # object, restricted to the detail alone. Both must be openable by the developer.
        res_detail = self.views["restricted"]["egress_topology"]["writable_surfaces"][0]["detail"]["$commitment"]
        salt = self.views["openings"]["/egress_topology/writable_surfaces/0/detail"]
        self.assertTrue(check_opening(res_detail, self.intent["egress_topology"]["writable_surfaces"][0]["detail"], salt))

    def test_opening_checks(self):
        commitment = self.views["public"]["egress_topology"]["$commitment"]
        salt = self.views["openings"]["/egress_topology"]
        self.assertTrue(check_opening(commitment, self.intent["egress_topology"], salt))
        tampered = copy.deepcopy(self.intent["egress_topology"])
        tampered["inter_agent_comms_permitted"] = not tampered["inter_agent_comms_permitted"]
        self.assertFalse(check_opening(commitment, tampered, salt))

    def test_closeout_notifications_public_counts_restricted_names(self):
        views = all_views(load("closeout_run_a.json"))
        n = views["public"]["third_party_notifications"][0]
        self.assertTrue(n["notified"])
        self.assertIn("$commitment", n["party"])
        self.assertEqual(views["restricted"]["third_party_notifications"][0]["party"], "Hugging Face")


class LedgerChain(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "record.jsonl"
        self.key = Ed25519PrivateKey.generate()
        self.ledger = Ledger(self.path)
        for name in ("intent_run_a.json", "intent_run_b.json", "closeout_run_a.json"):
            self.ledger.append(load(name), self.key, filed_at="2026-07-21T00:00:00Z", profile="baseline")

    def tearDown(self):
        self.dir.cleanup()

    def _rewrite(self, entries):
        self.path.write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in entries), encoding="utf-8")

    def test_clean_chain_verifies(self):
        self.assertEqual(self.ledger.verify(), [])

    def test_edit_detected(self):
        entries = self.ledger.entries()
        entries[0]["record"]["safeguards_disabled"]["disabled"] = False
        self._rewrite(entries)
        self.assertIn("record_altered", codes(self.ledger.verify()))

    def test_deletion_detected(self):
        entries = self.ledger.entries()
        del entries[1]
        self._rewrite(entries)
        self.assertTrue({"seq_gap", "chain_broken"} & codes(self.ledger.verify()))

    def test_reorder_detected(self):
        entries = self.ledger.entries()
        entries[0], entries[1] = entries[1], entries[0]
        self._rewrite(entries)
        self.assertIn("chain_broken", codes(self.ledger.verify()))

    def test_untrusted_key_detected(self):
        self.assertIn("untrusted_key", codes(self.ledger.verify(trusted_keys={})))

    def test_noncompliant_filing_refused(self):
        bad = load("intent_run_a.json")
        bad["trigger_basis"] = ["T2"]
        with self.assertRaises(ValueError):
            self.ledger.append(bad, self.key, profile="baseline")

    def test_inadequate_filing_refused_by_default(self):
        with self.assertRaises(ValueError):
            self.ledger.append(load("intent_run_a.json"), self.key)  # dead comms criterion


class FreezeAndBacktest(unittest.TestCase):
    def test_schema_hash_is_stable(self):
        self.assertEqual(schema_hash(), schema_hash())
        self.assertTrue(schema_hash().startswith("sha256:"))

    def test_backtest_results(self):
        r = score_case(CASE)
        self.assertTrue(r["filings_compliant"], r["integrity"])
        d, b = r["variants"]["diligent"], r["variants"]["as_believed"]
        self.assertEqual(d["recorded_before"], 6)
        self.assertEqual(b["recorded_before"], 4)
        self.assertEqual(d["changes_decision_yes"], 0)
        dp5 = next(x for x in d["rows"] if x["id"] == "DP5")
        self.assertEqual(dp5["changes_decision"], "No")  # the decisive negative finding


class Adequacy(unittest.TestCase):
    """v0.2 minimum-content checks, on the honest synthetic S2 filing set."""

    def setUp(self):
        self.f = SCENARIOS["S2"]()
        self.intent, self.closeout = self.f["intent:A"], self.f["closeout:A"]

    def test_honest_sets_pass_both_profiles(self):
        for sid, build in SCENARIOS.items():
            for key, rec in build().items():
                for profile in ("baseline", "adequacy"):
                    with self.subTest(sid=sid, key=key, profile=profile):
                        self.assertEqual(errors(validate_record(rec, profile=profile)), [])

    def test_dead_criterion(self):
        self.intent["monitoring_instruments"] = [{"kind": "egress_alerting", "coverage": "all"}]
        self.assertIn("dead_criterion", codes(validate_record(self.intent)))

    def test_writability_must_be_declared(self):
        del self.intent["egress_topology"]["permitted_paths"][0]["agent_writable"]
        self.assertIn("writability_undeclared", codes(validate_record(self.intent)))

    def test_writable_path_needs_surface(self):
        self.intent["egress_topology"]["permitted_paths"][0]["agent_writable"] = True
        self.assertIn("writable_path_without_surface", codes(validate_record(self.intent)))

    def test_forecast_requires_t3(self):
        self.intent["trigger_basis"] = ["T2", "T4"]
        self.assertIn("t3_missing", codes(validate_record(self.intent)))

    def test_evaluation_window_capped(self):
        self.intent["start_window"]["end"] = "2026-12-31"
        self.assertIn("standing_intent", codes(validate_record(self.intent)))

    def test_run_kind_required(self):
        del self.intent["run_kind"]
        self.assertIn("run_kind_undeclared", codes(validate_record(self.intent)))

    def test_detection_time_required(self):
        del self.closeout["security_events"][0]["detected_at"]
        self.assertIn("detection_time_missing", codes(validate_record(self.closeout)))

    def test_late_notification_needs_reason(self):
        n = self.closeout["third_party_notifications"][0]
        n["notified_at"] = "2026-09-20T00:00:00Z"
        self.assertIn("late_notification", codes(validate_record(self.closeout)))
        n["delay_reason"] = "law-enforcement request to delay"
        self.assertNotIn("late_notification", codes(validate_record(self.closeout)))

    def test_notice_deadline(self):
        notices = [self.f["notice:N1"]]
        self.assertEqual(errors(check_notices(self.intent, self.closeout, notices)), [])
        notices[0]["filed_at"] = "2026-09-10T00:00:00Z"
        self.assertIn("notice_late", codes(check_notices(self.intent, self.closeout, notices)))
        self.assertIn("notice_missing", codes(check_notices(self.intent, self.closeout, [])))

    def test_baseline_ignores_adequacy_rules(self):
        self.intent["monitoring_instruments"] = []
        self.assertEqual(errors(validate_record(self.intent, profile="baseline")), [])


class Tabletop(unittest.TestCase):
    def test_results(self):
        r = run_tabletop()
        self.assertEqual(r["false_positives"], {})
        self.assertEqual(r["n_attacks"], 20)
        self.assertEqual(r["round1_caught"], 2)
        self.assertEqual(set(r["residual"]), {"T11", "T12", "T14", "T15", "T16", "T17"})
        self.assertEqual(r["residual_without_account"], [])


class Versions(unittest.TestCase):
    """v0.3 handling of amendments and closeout cadence. [R1 judge item 9; S3-E2]"""

    def _eval(self, filed, start, end, amends=None, changes=None):
        from tabletop.scenarios import SCENARIOS
        i = copy.deepcopy(SCENARIOS["S2"]()["intent:A"])
        i.update({"filed_at": filed, "start_window": {"start": start, "end": end}})
        if amends is not None:
            i.update({"amends": amends, "changes": changes or ["window extended"]})
        return i

    def test_chained_amendments_cannot_make_a_standing_evaluation(self):
        from dbyr.check import check_set
        first = self._eval("2026-08-20T00:00:00Z", "2026-09-01", "2026-09-30")
        second = self._eval("2026-09-25T00:00:00Z", "2026-09-01", "2026-10-30", amends=0)
        found = {f.code for _, f in check_set({"a": first, "b": second}) if f.severity == "error"}
        self.assertIn("standing_intent", found)
        found_single = {f.code for _, f in check_set({"a": first}) if f.severity == "error"}
        self.assertNotIn("standing_intent", found_single)

    def test_closeout_reconciled_against_version_in_force(self):
        from dbyr.check import _in_force
        a = self._eval("2026-08-20T00:00:00Z", "2026-09-01", "2026-09-14")
        b = self._eval("2026-09-10T00:00:00Z", "2026-09-01", "2026-09-20", amends=0)
        self.assertIs(_in_force([a, b], "2026-09-05T00:00:00Z"), a)
        self.assertIs(_in_force([a, b], "2026-09-21T00:00:00Z"), b)

    def test_overdue_closeout_is_conduct_not_error(self):
        from dbyr.check import check_set
        filings = {n: load(n) for n in ("intent_run_a.json", "closeout_run_a.json", "notice_n1.json", "notice_n2.json")}
        found = check_set(filings)
        self.assertIn("closeout_overdue", {f.code for _, f in found if f.severity == "conduct"})
        self.assertNotIn("closeout_overdue", {f.code for _, f in found if f.severity == "error"})


if __name__ == "__main__":
    unittest.main()
