# Writing `decision_points.json`

Decision points belong to the backtest, not to the DBYR protocol. **They are never filed.** A lab
using DBYR files Intents, Notices, Closeouts and runtime records, and nothing else. Decision points
are written only when someone tests the protocol against an incident: they are the questions an
investigator asks afterwards, and the backtest counts how many the lab's records would have answered.

**Who writes them.** For a past incident, researchers working from the public account of it, and
not the person who reconstructed the filings. Never the lab whose incident it is: a lab could leave
out the decisions that make it look bad. If DBYR were used to review a real incident, the
independent investigator would write them, and the lab could propose additions but not remove any.

`decision_points.json` is a case's scoring plan. **You write it; dbyr does not generate it.** It
says which decisions shaped the incident and, for each, what a filing should have recorded before
the decision and what the Closeout should show after it. dbyr then scores each decision point
against the filings.

It is pre-registered: write it before you score, and do not edit it afterwards. To keep the
scoring independent, the person who writes it should not be the person who wrote the filings.

## How to start one

| Situation | What to do |
|---|---|
| New case | `dbyr backtest init cases/my-case` copies a complete example case, including an example `decision_points.json` with `case` and `schema_hash` filled in. Replace the example decision points with yours. |
| You already have the filings | Run `init` in a scratch folder, copy its `decision_points.json` next to your filings, and edit it. Set `schema_hash` to what `dbyr freeze` prints. |

Check it at any point with `dbyr backtest check <case>`. It reports missing keys, record keys that
are not among the filings, tests that read a field the schema does not have, and tests that read a
placeholder value.

## The file at a glance

```jsonc
{
  "case": "my-case",                         // required: the case's name
  "title": "Lab X safeguards-off evaluation", // optional: a longer name for reports
  "is_derivation_case": false,               // optional: true for the case the protocol was written from
  "schema_hash": "sha256:…",                 // optional, recommended: the frozen schema (dbyr freeze)

  "records": { "intent:A": "intent_A.json", "closeout:A": "closeout_A.json" },  // where the filings are:
  // or "filings": "../filings/my-case/"                                        // exactly one of the two

  "closes": { "closeout:A": "intent:A" },    // required: each Closeout's key -> its Intent's key

  "variants": {                              // required: at least one filer variant
    "diligent":    { "description": "States what was actually true." },
    "as_believed": { "description": "Leaves out what the filer did not know.",
                     "remove_surfaces": { "intent:A": ["scratch-dir"] } }
  },

  "decision_points": [ { … }, { … } ]        // required: at least one
}
```

## Top-level keys

| Key | Required | What it holds |
|---|---|---|
| `case` | yes | The case's name, used in reports and results. |
| `title` | no | A longer name for reports. |
| `is_derivation_case` | no | `true` for the case the protocol was designed from. Its verdict reads "reference", because it passes by construction. |
| `schema_hash` | no, recommended | The hash `dbyr freeze` printed before the filings were written. If the schema changes, `check` fails and `score` refuses. |
| `records` | one of these two | The filings, one by one: `{"KEY": "file.json"}`, paths relative to this file. You choose the keys; `intent:A`, `closeout:A`, `notice:N1` is the convention. |
| `filings` | one of these two | A path to a filing set: a folder or its `manifest.json`, the same thing `dbyr run` takes. Keys are then the manifest's keys, or the file names if there is no manifest. |
| `closes` | yes | Maps each Closeout's key to the key of the Intent it closes. |
| `variants` | yes | The filer variants, described below. |
| `decision_points` | yes | The decision points, described below. |

## Filer variants

A variant is the same filings as a particular filer would have written them. Each variant edits a
copy of the Intent before scoring; a variant with no edits scores the filings as they are.

| Key | What it does |
|---|---|
| `description` | Says who this filer is. |
| `remove_surfaces` | `{"intent:A": ["surface-id", …]}`: leaves those writable surfaces out, as a filer who did not know them would. |
| `remove_paths` | `{"intent:A": ["path-id", …]}`: leaves those network paths out. |
| `path_writable` | `{"intent:A": {"path-id": false}}`: states a path's writability as the filer believed it. |

The usual pair is `diligent` (what was true) and `as_believed` (what the filer plausibly
believed). Report both.

## A decision point

```jsonc
{
  "id": "DP1",                                   // required, unique
  "date": "5 Sep",                               // optional, shown in reports
  "decision": "The run is paused when an agent reaches an allowlisted host.",  // required
  "field": "agent_surface.permitted_paths, pause_criteria",  // optional: the fields that should capture it
  "developer_aware": "yes",                      // required: yes | no | unclear
  "aware_source": "closeout_A.json: detected an hour after it happened",     // the evidence for awareness
  "recorded_before": { … },                      // required: a test on a filing made before the event
  "checkable_after": { …, "evidence": [ … ] },   // required: a test on the Closeout, and the evidence needed
  "decision_rule": { "rule": "pause_criterion", "event_kind": "sandbox_escape" }  // required
}
```

| Key | What it is |
|---|---|
| `developer_aware` | Whether the developer knew the relevant fact at the time: `yes`, `no` or `unclear`. A decision on an event nobody saw cannot be changed by any rule. |
| `recorded_before` | Test (a): did a filing made **before** the event record the fact? Usually a test on the Intent. |
| `checkable_after` | Test (b): does the Closeout record the event? `evidence` lists the evidence classes a later check would need (e.g. `["network_logs", "trajectories"]`); each must be among the Intent's `log_retention.retained`, or the test scores "No". |
| `decision_rule` | Test (c): would the filing have changed the decision? `{"rule": "pause_criterion", "event_kind": KIND}` asks whether a declared pause criterion matching that event kind required an action that was not taken; add `"closeout": KEY` when a case has several Closeouts. `{"rule": "record_obligation"}` is for decisions the protocol only requires to be recorded, not acted on. |

A decision point is **attributable** when (a) holds and (b) is not "No". A case passes when at
least half its decision points are attributable.

## Writing the tests

A test reads one filing, named by its key. There are four forms:

| Form | Holds when |
|---|---|
| `{"record": "intent:A", "pointer": "/run_kind", "equals": "evaluation"}` | the field at that JSON pointer equals the value |
| `{"record": "intent:A", "pointer": "/eval_plan", "exists": true}` | the field is present (not missing or null) |
| `{"record": "closeout:A", "any": "/security_events", "where": {"kind": "sandbox_escape"}}` | at least one item of the list matches every condition in `where` |
| `{"all": [TEST, TEST, …]}` | every test inside holds |

Conditions in `where`:

| Condition | Matches an item when |
|---|---|
| `"kind": "sandbox_escape"` | the item's field equals the value |
| `"kind": ["sandbox_escape", "credential_misuse"]` | the item's field is one of the values |
| `"matches": {"contains": "third_party_compromise"}` | the item's field is a list containing the value |
| `"evidence": {"nonempty": true}` | the item's field is present and not empty |

Pointers follow the record's field names, as listed in [docs/records/](../records/README.md):
`/agent_surface/permitted_paths`, `/pause_criteria`, `/security_events`. A pointer that does not
exist in a filing reads as missing, so the test is "No"; `dbyr backtest check` warns when a
pointer names a field the schema does not have at all.

**Do not test a placeholder value.** If `sources.json` marks a value as a placeholder (something
made up to complete the filing), a test on it measures nothing. `check` warns if one does.

## A complete example

The example case that `dbyr backtest init` writes has two decision points. The first: the Intent
declared the path the agent used as read-only, and the Closeout records the escape, with the
evidence to check it kept. The second: the Intent had a criterion for third-party compromise, and
the Closeout records that the affected party was told.

```json
{
  "case": "lab-x",
  "title": "Template: synthetic safeguards-off cyber evaluation (Lab X)",
  "is_derivation_case": false,
  "schema_hash": "sha256:…",
  "records": {
    "intent:A": "intent_A.json",
    "closeout:A": "closeout_A.json",
    "notice:N1": "notice_N1.json",
    "runtime:S1": "runtime_S1.json"
  },
  "closes": {"closeout:A": "intent:A"},
  "variants": {
    "diligent": {"description": "Filer declares every writable surface as it actually was."},
    "as_believed": {
      "description": "Filer leaves out the scratch surface, as an operator who believed it was not writable might.",
      "remove_surfaces": {"intent:A": ["eval-scratch"]}
    }
  },
  "decision_points": [
    {
      "id": "DP1",
      "date": "5 Sep",
      "decision": "An agent reaches an allowlisted host by request smuggling; the run is paused for review.",
      "field": "agent_surface.permitted_paths, pause_criteria",
      "developer_aware": "yes",
      "aware_source": "closeout_A.json: the escape was detected an hour after it happened",
      "recorded_before": {
        "record": "intent:A", "any": "/agent_surface/permitted_paths",
        "where": {"path_id": "web-ro", "agent_writable": false}
      },
      "checkable_after": {
        "record": "closeout:A", "any": "/security_events",
        "where": {"kind": "sandbox_escape"},
        "evidence": ["network_logs", "trajectories"]
      },
      "decision_rule": {"rule": "pause_criterion", "event_kind": "sandbox_escape"}
    },
    {
      "id": "DP2",
      "date": "5 Sep",
      "decision": "The hosting provider reached by the escape is notified the same day.",
      "field": "pause_criteria, third_party_notifications",
      "developer_aware": "yes",
      "aware_source": "closeout_A.json: notified at 20:00 on the day of detection",
      "recorded_before": {
        "record": "intent:A", "any": "/pause_criteria",
        "where": {"matches": {"contains": "third_party_compromise"}}
      },
      "checkable_after": {
        "record": "closeout:A", "any": "/third_party_notifications",
        "where": {"party": "Example Hosting Ltd", "notified": true},
        "evidence": []
      },
      "decision_rule": {"rule": "record_obligation"}
    }
  ]
}
```

## Checklist

1. List every decision that shaped the incident, including decisions not to act.
2. For each, find the field that should have captured it before the event, and write
   `recorded_before` against it.
3. Write `checkable_after` against the Closeout, and list the evidence a check would need.
4. Choose the `decision_rule`, and record `developer_aware` with its source.
5. Run `dbyr backtest check`, fix every error, and read every warning.
6. Freeze: record `schema_hash`, and do not edit the file after scoring.
