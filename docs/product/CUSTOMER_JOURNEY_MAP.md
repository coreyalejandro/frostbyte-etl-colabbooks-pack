# Customer Persona + Journey Map (Vendor Rollout)

## Persona
**Dana (Vendor Data Operations Lead)**
- Accountable for sending documents/data to the buyer on schedule
- Limited engineering support
- High risk sensitivity: “Where does our data go? Who can see it?”

## Illustrated pain points
- [P1] Ambiguous requirements → repeated rework, missed deadlines
- [P2] Black-box ingestion → “What did you parse? What did you drop?”
- [P3] Sovereignty anxiety → “Did this go to external APIs?”
- [P4] Retrieval mismatch → “Your system answers wrong because retrieval is wrong”
- [P5] Offline installs break → Docker/GPU/deps/updates

## Journey map

| Stage | Dana’s goal | Dana’s action | System behavior | Failure to prevent | Required artifact |
|---|---|---|---|---|---|
| Trust framing | Confirm sovereignty | asks where data flows | clear boundary statement | vague claims | Data boundary contract |
| Onboarding | Connect sources | provides SFTP/API creds | least privilege + rotation | over-permission | scoped connector config |
| Upload | Ship documents | sends batch + manifest | receipts + checksums | missing/duplicate files | intake receipt |
| Parsing | Preserve structure | waits | parse preview + diffs | silent loss | parse diff report |
| Enrichment | Validate categories | approves taxonomy | human-in-loop gate | misclassification | review UI/report |
| Storage | Confirm isolation | asks about tenancy | tenant-only namespaces/keys | cross-tenant bleed | isolation evidence |
| Retrieval QA | Trust results | runs test queries | source slices + offsets | “fluent wrong” | retrieval proof report |
| Operations | Reduce burden | schedules deltas | idempotent deltas | drift/unseen fails | observability dashboard |
| Incident | Contain blast radius | reports issue | tenant kill-switch | lateral movement | immutable audit log |

