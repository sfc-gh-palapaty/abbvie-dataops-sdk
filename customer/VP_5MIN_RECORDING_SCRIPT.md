# AbbVie DataOps SDK — 5-Minute Executive Recording

**Format:** screen-share + voice-over. ~700 words. Pace yourself at ~140 words/min.
**Goal:** Send to AbbVie executives as a leave-behind after the VP demo. Self-contained.

> **Pre-record setup (60 sec before you hit record):**
> - Tabs open in this order in one browser window:
>   1. VS Code on the repo (left half of screen) showing `customer/POC_ARCHITECTURE.md` in preview mode
>   2. GitHub repo `main` page
>   3. GitHub PR #2
>   4. GitHub `snowflake-deploy` run `25831442352`
>   5. DataHub — SuiteCRM mysql source dataset
>   6. Marquez UI
> - Terminal open with the `snow sql` block from `QUICK_REFERENCE.md` ready to paste (just don't paste it on-camera; you'll talk about it via the GitHub view).
> - Camera off, mic on.

---

## [00:00 — 00:30]  Opening + the problem (30 sec)

> "Hi — I'm Phani, a data platform architect at Snowflake working alongside AbbVie's DataOps team. The 5 minutes you're about to see is a working **DataOps Governance SDK** that solves one specific problem: today, every AbbVie data pipeline has its own way of doing schema checks, data quality, sensitive data handling, and lineage. The result is great tools but inconsistent evidence — slow audits, hard to scale.
>
> This PoC proposes a **single small SDK plus a YAML manifest** that any pipeline — GitHub Actions, Azure DevOps, Glue, EMR, application pipelines — invokes when the change touches governed data. Same gate, same evidence, every time. Let me show you."

**On screen:** `POC_ARCHITECTURE.md` Diagram 1 (the wide flowchart). Cursor moving slowly left-to-right.

---

## [00:30 — 01:15]  Architecture in one picture (45 sec)

> "Five lanes, left to right.
>
> First — **Source of change.** A developer picks up a Jira, opens a GitHub PR. That's it. We don't change AbbVie's existing developer flow.
>
> Second — **CI/CD spine.** Five GitHub Actions workflows: one PR-time gate, one per platform — Snowflake, EMR Serverless, the SuiteCRM application — plus the SDK's own CI.
>
> Third — **The SDK in the middle.** Six modules: schema enforcement, data quality, constraints, tokenization, lineage emit, and catalog emit. Three platform adapters: Snowflake, EMR/Glue/Iceberg, and the SuiteCRM app — which stands in for Salesforce in this PoC.
>
> Fourth — **The governance backplane.** DataHub for the catalog — stand-in for Alation. Marquez as the OpenLineage backend. Both deployed on AWS EC2.
>
> Fifth — **The data plane** you already own: S3, Glue, Iceberg, EMR, RDS, Snowflake. The SDK never owns data — it enforces contracts and emits evidence."

**On screen:** Switch to VS Code file tree view.

---

## [01:15 — 02:00]  Repo structure + manifest-first design (45 sec)

> "The repo lives at github.com/sfc-gh-palapaty/abbvie-dataops-sdk. Six folders matter.
>
> **`sdk/`** — the Python package. About 800 lines. Installable from Artifactory in production.
>
> **`manifests/`** — one YAML per service. This is the *only* thing a pipeline author writes. A manifest declares: the service name, owners, classification, which adapter to use — Snowflake, EMR, or the app — and which checks to run. The SDK is *entirely* driven by the manifest. There is no per-pipeline Python.
>
> **`migrations/snowflake/`** — schemachange DDL scripts, the open-source standard for Snowflake DCM.
>
> **`.github/workflows/`** — the five pipelines I described.
>
> **`terraform/`** — Infrastructure as Code for AWS and Snowflake. Everything reproducible.
>
> **`customer/`** — written narrative for stakeholders.
>
> The key idea: **the manifest *is* the contract.** Same shape across all three adapters."

**On screen:** Open `manifests/snowflake-curated.yaml` briefly — point to `schema_enforcement`, `data_quality`, `tokenization` blocks.

---

## [02:00 — 03:00]  The fail-closed gate, live (60 sec)

> "Now the demo. PR #2 in the repo adds a `WEBSITE` column to the curated `ACCOUNTS` table. Two commits, one PR.
>
> **Commit one** — only the schemachange SQL. The developer *forgot* to update the schema contract under `manifests/schemas/snowflake/`. Watch the PR-governance check.
>
> Red. 29 seconds. The bot left this comment: `is_data_change: true`, `must_fail_closed: true`, blocker — *changes under 'migrations/snowflake/' require an updated contract*. The PR is unmergeable. That's the **fail-closed gate** — when in doubt, refuse.
>
> **Commit two** — the developer updates `accounts.json` to add the `WEBSITE` column to the contract. Five-line diff. The gate re-runs.
>
> Green, 45 seconds. Bot comment now reads `must_fail_closed: false`. PR mergeable.
>
> This is the entire policy enforcement loop. Path-based. Free. Runs on every PR, on every adapter. We never asked the developer to install anything special."

**On screen:** Show PR #2 — Conversation tab, scroll to first bot comment (red), then second bot comment (green). Then Checks tab showing the run history.

---

## [03:00 — 04:00]  Merge, deploy, audit (60 sec)

> "PR is merged. Watch the `snowflake-deploy` workflow.
>
> Step one — GitHub Actions authenticates to AWS and Snowflake using **OIDC**. No static passwords. No API keys. Nothing to rotate or steal.
>
> Step two — `schemachange` applies `V1.3.0__add_website.sql` to the live Snowflake database.
>
> Step three — the SDK runs in **promote profile**: schema enforcement, DQ, constraints, tokenization policy review, OpenLineage emission, DataHub registration. Evidence bundle uploaded as a workflow artifact.
>
> Total: 50 seconds, end to end.
>
> If I drop to a terminal right now and query Snowflake — three things have changed since the PR was opened: the `ACCOUNTS` table has the new column at ordinal 9, the BI-safe view `V_ACCOUNTS_GOVERNED` exposes `WEBSITE_DOMAIN_ONLY` because the repeatable view migration replayed in the same deploy, and the `SCHEMACHANGE.CHANGE_HISTORY` audit table shows the change with `INSTALLED_BY = GH_CICD_USER`.
>
> That `GH_CICD_USER` row is the regulator answer. No human ran this DDL. GitHub Actions authenticated via OIDC, the gate passed, schemachange applied the change, and Snowflake wrote the audit row in the same transaction."

**On screen:** Click into `snowflake-deploy` run `25831442352`. Walk through the step names in the left sidebar. Then briefly flash the bottom of the talk track that has the `snow sql` query result (paste into VS Code as a markdown if needed) showing the new `WEBSITE` column and the `CHANGE_HISTORY` row.

---

## [04:00 — 04:45]  Lineage in DataHub + Marquez (45 sec)

> "Last stop — what does an auditor see?
>
> Open DataHub. The SuiteCRM Accounts table on RDS MySQL. Click the lineage tab. Expand four times.
>
> **MySQL → S3 raw zone → Glue/Iceberg curated → Snowflake curated → Snowflake governance view.** Five platforms, one lineage graph. Every edge here was emitted by the SDK during the CI run — nothing hand-curated. Click the governance view on the right: `EMAIL_TOKENIZED`, `PHONE_TOKENIZED`, `WEBSITE_DOMAIN_ONLY`, `ANNUAL_REVENUE_BUCKETED`. Sensitive columns masked. Audit-ready.
>
> Now Marquez — the run history. Same flow, different lens. Every job execution is a `START` and `COMPLETE` event tagged to a commit. DataHub answers *what exists and who owns it*. Marquez answers *what ran, when, did it succeed, which run produced this row*. Together, they are the one auditable view your CDO has been asking for."

**On screen:** Quick DataHub lineage expand to 5 nodes, then click governance view → schema panel → highlight the tokenized columns. Then switch to Marquez, click through 2 namespaces.

---

## [04:45 — 05:00]  Close (15 sec)

> "Net: AbbVie gets a thin, configuration-driven SDK that turns every governed-data PR into an auditable, reversible event. Failures are uniform. Evidence is uniform. Lineage is automatic. And we did it without replacing a single tool you already own.
>
> Happy to take this deeper with your team whenever you're ready. Thanks for watching."

**On screen:** Back to the architecture diagram, slow zoom out.

---

## Word count + timing notes

| Segment | Words | Target sec |
|---|---|---|
| 1. Opening + problem | 95 | 30 |
| 2. Architecture | 160 | 45 |
| 3. Repo + manifest | 165 | 45 |
| 4. Fail-closed gate | 175 | 60 |
| 5. Merge + deploy + audit | 215 | 60 |
| 6. Lineage | 165 | 45 |
| 7. Close | 55 | 15 |
| **Total** | **~1030** | **300 (5:00)** |

At 140 wpm you'll land at 4:25, leaving ~30 sec breathing room — good for natural pauses, screen transitions, and a slightly more reflective opening line if you want.

---

## Recording tips (Loom / QuickTime / Zoom local recording)

1. **Practice the screen choreography twice** before hitting record — tab order is the most error-prone part.
2. **Record audio in a single take.** Re-record only if a sentence dies mid-word. Editing voice-over against screen capture is painful.
3. **Use a wired headset** if possible — Loom's built-in mic picks up keyboard noise during the live demo segments.
4. **Hide the menu bar / dock** (`Cmd+Opt+D` to hide dock on macOS). Clutter ages a demo video badly.
5. **Cursor visibility** — Loom has an option for a yellow highlight ring around the cursor; turn it on.
6. **Export at 1080p**, not 4K. Faster upload, no executive will notice.
7. **Set the thumbnail** to the architecture diagram or the green PR — first impression matters when execs share the link.

---

## Two natural cutting points if you run long

- Cut Step 3 ("Repo structure") from 45s → 25s by skipping the per-folder enumeration. Just say *"sdk, manifests, migrations, workflows, terraform — that's the whole repo."*
- Cut Step 6 ("Lineage") DataHub expand from 4 clicks to 2, then verbally say *"…and so on for the remaining hops."*

These two cuts buy you 30 seconds total without losing the headline message.
