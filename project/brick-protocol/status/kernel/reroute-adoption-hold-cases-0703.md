# reroute 채택 홀드 사례 원본 (0703 새벽 — COO 사실 추출)

Status: support evidence aggregation. 4개 vessel의 raw/link.jsonl에서 자동채택/paused 행 원문 발췌.
질문: closure 제안 reroute가 llm-alias 2~4라운드에선 자동채택됐는데, 이후 4건은 전부
runtime_handoff_address_unresolved_in_ledger(walker_runtime_mail.py:217)로 홀드된 이유.

## llm-alias-0702h(자동채택 성공 라운드 포함)
- 총 27행, 자동채택 2건 발췌, paused 1건

### 자동채택 행
```json
{
 "@context": {
  "bp": "urn:bp:",
  "ce": "https://cloudevents.io/spec/v1.0/",
  "prov": "http://www.w3.org/ns/prov#",
  "xsd": "http://www.w3.org/2001/XMLSchema#"
 },
 "@id": "urn:bp:building:task-statement-2a305f84de5c-node::raw/link.jsonl#18",
 "adopted_by": "template:default-transition",
 "attempt_number": 1,
 "budget_exhausted": false,
 "building_id": "task-statement-2a305f84de5c-node",
 "cascade_depth": 1,
 "datacontenttype": "application/json",
 "dataschema": "urn:bp:schema:graph-ready-v1",
 "generatedAtTime": "2026-07-02T15:24:08Z",
 "id": "urn:bp:building:task-statement-2a305f84de5c-node::raw/link.jsonl#18",
 "movement": "reroute",
 "movement_source": "recorded dynamic_walker_evidence reroute adoption record",
 "node_budget": 5,
 "parent_reroute_ref": "",
 "raw_ref": "raw:link-reroute:01",
 "raw_refs": [
  "raw:link-reroute:01"
 ],
 "recorded_at": "2026-07-02T15:24:08Z",
 "reroute_ref": "reroute-adoption:task-statement-2a305f84de5c-node:01:brick-task-statement-2a305f84de5c-node-work",
 "schema_version": "graph-ready-v1",
 "source": "urn:bp:building:task-statement-2a305f84de5c-node",
 "source_brick_instance_ref": "brick-task-statement-2a305f84de5c-node-review",
 "source_transition_concern_ref": "transition-concern:task-statement-2a305f84de5c-node-d4-and-scope",
 "specversion": "1.0",
 "step_ref": "task-statement-2a305f84de5c-node-review",
 "subject": "task-statement-2a305f84de5c-node-review",
 "target": "brick-task-statement-2a305f84de5c-node-work",
 "target_brick_instance_ref": "brick-task-statement-2a305f84de5c-node-work",
 "target_step_ref": "task-statement-2a305f84de5c-node-work",
 "time": "2026-07-02T15:24:08Z",
 "type": "bp.raw.link"
}
```

### 자동채택 행
```json
{
 "@context": {
  "bp": "urn:bp:",
  "ce": "https://cloudevents.io/spec/v1.0/",
  "prov": "http://www.w3.org/ns/prov#",
  "xsd": "http://www.w3.org/2001/XMLSchema#"
 },
 "@id": "urn:bp:building:task-statement-2a305f84de5c-node::raw/link.jsonl#19",
 "adopted_by": "template:default-transition",
 "attempt_number": 2,
 "budget_exhausted": false,
 "building_id": "task-statement-2a305f84de5c-node",
 "cascade_depth": 2,
 "datacontenttype": "application/json",
 "dataschema": "urn:bp:schema:graph-ready-v1",
 "generatedAtTime": "2026-07-02T15:24:08Z",
 "id": "urn:bp:building:task-statement-2a305f84de5c-node::raw/link.jsonl#19",
 "movement": "reroute",
 "movement_source": "recorded dynamic_walker_evidence reroute adoption record",
 "node_budget": 5,
 "parent_reroute_ref": "reroute-adoption:task-statement-2a305f84de5c-node:01:brick-task-statement-2a305f84de5c-node-work",
 "raw_ref": "raw:link-reroute:02",
 "raw_refs": [
  "raw:link-reroute:02"
 ],
 "recorded_at": "2026-07-02T15:24:08Z",
 "reroute_ref": "reroute-adoption:task-statement-2a305f84de5c-node:02:brick-task-statement-2a305f84de5c-node-work",
 "schema_version": "graph-ready-v1",
 "source": "urn:bp:building:task-statement-2a305f84de5c-node",
 "source_brick_instance_ref": "brick-task-statement-2a305f84de5c-node-closure",
 "source_transition_concern_ref": "transition-concern:task-statement-2a305f84de5c-node-closure-boundary-mismatch",
 "specversion": "1.0",
 "step_ref": "task-statement-2a305f84de5c-node-closure",
 "subject": "task-statement-2a305f84de5c-node-closure",
 "target": "brick-task-statement-2a305f84de5c-node-work",
 "target_brick_instance_ref": "brick-task-statement-2a305f84de5c-node-work",
 "target_step_ref": "task-statement-2a305f84de5c-node-work",
 "time": "2026-07-02T15:24:08Z",
 "type": "bp.raw.link"
}
```

### paused 행
```json
{
 "@context": {
  "bp": "urn:bp:",
  "ce": "https://cloudevents.io/spec/v1.0/",
  "prov": "http://www.w3.org/ns/prov#",
  "xsd": "http://www.w3.org/2001/XMLSchema#"
 },
 "@id": "urn:bp:building:task-statement-2a305f84de5c-node::raw/link.jsonl#17",
 "building_id": "task-statement-2a305f84de5c-node",
 "datacontenttype": "application/json",
 "dataschema": "urn:bp:schema:graph-ready-v1",
 "declared_gate_refs": [
  "link-gate:default-transition"
 ],
 "generatedAtTime": "2026-07-02T15:24:08Z",
 "id": "urn:bp:building:task-statement-2a305f84de5c-node::raw/link.jsonl#17",
 "movement": "forward",
 "movement_source": "caller-declared Building Plan Link row",
 "raw_ref": "raw:link:17",
 "raw_refs": [
  "raw:link:17"
 ],
 "recorded_at": "2026-07-02T15:24:08Z",
 "schema_version": "graph-ready-v1",
 "source": "urn:bp:building:task-statement-2a305f84de5c-node",
 "source_brick_instance_ref": "brick-task-statement-2a305f84de5c-node-closure",
 "specversion": "1.0",
 "step_ref": "task-statement-2a305f84de5c-node-closure",
 "subject": "task-statement-2a305f84de5c-node-closure",
 "target": "building-boundary:closed",
 "target_brick_instance_ref": "building-boundary:closed",
 "time": "2026-07-02T15:24:08Z",
 "transition_lifecycle_carry_budget_evidence_ref": "evidence/claim_trace/link/carry_trace.json#carry-budget:task-statement-2a305f84de5c-node:node:brick-task-statement-2a305f84de5c-node-work",
 "transition_lifecycle_from_brick_ref": "brick-task-statement-2a305f84de5c-node-closure",
 "transition_lifecycle_not_proven": [
  "semantic correctness of the agent-proposed reroute",
  "parallel runtime execution (P-walker-2 fan-in/fan-out out of scope here)",
  "scheduler / queue / retry behavior",
  "caller/COO disposition after a HOLD"
 ],
 "transition_lifecycle_paused_at_ref": "link-transition:reroute-hold-task-statement-2a305f84de5c-node-04-brick-task-statement-2a305f84de5c-node-work-src-task-statement-2a305f84de5c-node-closure-depth-0-attempt-3",
 "transition_lifecycle_pending_target_ref": "brick-task-statement-2a305f84de5c-node-work",
 "transition_lifecycle_progress_state": "in_progress",
 "transition_lifecycle_proof_limits": [
  "support evidence only",
  "dynamic walker walks declared gate-adopted agent-proposed routes only",
  "support authors no route or Movement",
  "not source truth",
  "not success judgment",
  "not quality judgment",
  "not Movement authority"
 ],
 "transition_lifecycle_reason_refs": [
  "transition-concern:task-statement-2a305f84de5c-node-closure-bound
```

## resume-ledger-repair-0702b
- 총 21행, 자동채택 2건 발췌, paused 1건

### 자동채택 행
```json
{
 "@context": {
  "bp": "urn:bp:",
  "ce": "https://cloudevents.io/spec/v1.0/",
  "prov": "http://www.w3.org/ns/prov#",
  "xsd": "http://www.w3.org/2001/XMLSchema#"
 },
 "@id": "urn:bp:building:task-statement-d13091a32b10-node::raw/link.jsonl#12",
 "adopted_by": "template:default-transition",
 "attempt_number": 1,
 "budget_exhausted": false,
 "building_id": "task-statement-d13091a32b10-node",
 "cascade_depth": 1,
 "datacontenttype": "application/json",
 "dataschema": "urn:bp:schema:graph-ready-v1",
 "generatedAtTime": "2026-07-02T15:50:09Z",
 "id": "urn:bp:building:task-statement-d13091a32b10-node::raw/link.jsonl#12",
 "movement": "reroute",
 "movement_source": "recorded dynamic_walker_evidence reroute adoption record",
 "node_budget": 5,
 "parent_reroute_ref": "",
 "raw_ref": "raw:link-reroute:01",
 "raw_refs": [
  "raw:link-reroute:01"
 ],
 "recorded_at": "2026-07-02T15:50:09Z",
 "reroute_ref": "reroute-adoption:task-statement-d13091a32b10-node:01:brick-task-statement-d13091a32b10-node-work",
 "schema_version": "graph-ready-v1",
 "source": "urn:bp:building:task-statement-d13091a32b10-node",
 "source_brick_instance_ref": "brick-task-statement-d13091a32b10-node-closure",
 "source_transition_concern_ref": "transition-concern:d1-raise-budget-bridge-increment-mismatch",
 "specversion": "1.0",
 "step_ref": "task-statement-d13091a32b10-node-closure",
 "subject": "task-statement-d13091a32b10-node-closure",
 "target": "brick-task-statement-d13091a32b10-node-work",
 "target_brick_instance_ref": "brick-task-statement-d13091a32b10-node-work",
 "target_step_ref": "task-statement-d13091a32b10-node-work",
 "time": "2026-07-02T15:50:09Z",
 "type": "bp.raw.link"
}
```

### 자동채택 행
```json
{
 "@context": {
  "bp": "urn:bp:",
  "ce": "https://cloudevents.io/spec/v1.0/",
  "prov": "http://www.w3.org/ns/prov#",
  "xsd": "http://www.w3.org/2001/XMLSchema#"
 },
 "@id": "urn:bp:building:task-statement-d13091a32b10-node::raw/link.jsonl#13",
 "adopted_by": "",
 "attempt_number": 1,
 "budget_exhausted": false,
 "building_id": "task-statement-d13091a32b10-node",
 "cascade_depth": 1,
 "datacontenttype": "application/json",
 "dataschema": "urn:bp:schema:graph-ready-v1",
 "generatedAtTime": "2026-07-02T15:50:09Z",
 "id": "urn:bp:building:task-statement-d13091a32b10-node::raw/link.jsonl#13",
 "movement": "reroute",
 "movement_source": "recorded dynamic_walker_evidence reroute adoption record",
 "node_budget": 5,
 "parent_reroute_ref": "reroute-adoption:task-statement-d13091a32b10-node:01:brick-task-statement-d13091a32b10-node-work",
 "raw_ref": "raw:link-reroute:02",
 "raw_refs": [
  "raw:link-reroute:02"
 ],
 "recorded_at": "2026-07-02T15:50:09Z",
 "reroute_ref": "reroute-hold:task-statement-d13091a32b10-node:02:brick-task-statement-d13091a32b10-node-work",
 "schema_version": "graph-ready-v1",
 "source": "urn:bp:building:task-statement-d13091a32b10-node",
 "source_brick_instance_ref": "brick-task-statement-d13091a32b10-node-closure",
 "source_transition_concern_ref": "transition-concern:task-statement-d13091a32b10-node-d2-ledger-cleanliness-partial",
 "specversion": "1.0",
 "step_ref": "task-statement-d13091a32b10-node-closure",
 "subject": "task-statement-d13091a32b10-node-closure",
 "target": "brick-task-statement-d13091a32b10-node-work",
 "target_brick_instance_ref": "brick-task-statement-d13091a32b10-node-work",
 "target_step_ref": "",
 "time": "2026-07-02T15:50:09Z",
 "type": "bp.raw.link"
}
```

### paused 행
```json
{
 "@context": {
  "bp": "urn:bp:",
  "ce": "https://cloudevents.io/spec/v1.0/",
  "prov": "http://www.w3.org/ns/prov#",
  "xsd": "http://www.w3.org/2001/XMLSchema#"
 },
 "@id": "urn:bp:building:task-statement-d13091a32b10-node::raw/link.jsonl#11",
 "building_id": "task-statement-d13091a32b10-node",
 "datacontenttype": "application/json",
 "dataschema": "urn:bp:schema:graph-ready-v1",
 "declared_gate_refs": [
  "link-gate:default-transition"
 ],
 "generatedAtTime": "2026-07-02T15:50:09Z",
 "id": "urn:bp:building:task-statement-d13091a32b10-node::raw/link.jsonl#11",
 "movement": "forward",
 "movement_source": "caller-declared Building Plan Link row",
 "raw_ref": "raw:link:11",
 "raw_refs": [
  "raw:link:11"
 ],
 "recorded_at": "2026-07-02T15:50:09Z",
 "schema_version": "graph-ready-v1",
 "source": "urn:bp:building:task-statement-d13091a32b10-node",
 "source_brick_instance_ref": "brick-task-statement-d13091a32b10-node-closure",
 "specversion": "1.0",
 "step_ref": "task-statement-d13091a32b10-node-closure",
 "subject": "task-statement-d13091a32b10-node-closure",
 "target": "building-boundary:closed",
 "target_brick_instance_ref": "building-boundary:closed",
 "time": "2026-07-02T15:50:09Z",
 "transition_lifecycle_carry_budget_evidence_ref": "evidence/claim_trace/link/carry_trace.json#carry-budget:task-statement-d13091a32b10-node:node:brick-task-statement-d13091a32b10-node-work",
 "transition_lifecycle_from_brick_ref": "brick-task-statement-d13091a32b10-node-closure",
 "transition_lifecycle_not_proven": [
  "semantic correctness of the agent-proposed reroute",
  "parallel runtime execution (P-walker-2 fan-in/fan-out out of scope here)",
  "scheduler / queue / retry behavior",
  "caller/COO disposition after a HOLD"
 ],
 "transition_lifecycle_paused_at_ref": "link-transition:reroute-hold-task-statement-d13091a32b10-node-02-brick-task-statement-d13091a32b10-node-work-src-task-statement-d13091a32b10-node-closure-depth-1-attempt-1",
 "transition_lifecycle_pending_target_ref": "brick-task-statement-d13091a32b10-node-work",
 "transition_lifecycle_progress_state": "in_progress",
 "transition_lifecycle_proof_limits": [
  "support evidence only",
  "dynamic walker walks declared gate-adopted agent-proposed routes only",
  "support authors no route or Movement",
  "not source truth",
  "not success judgment",
  "not quality judgment",
  "not Movement authority"
 ],
 "transition_lifecycle_reason_refs": [
  "transition-concern:task-statement-d13091a32b10-node-d2-ledger-cle
```

## d2-ledger-cleanliness-0703a(v1)
- 총 11행, 자동채택 0건 발췌, paused 0건

## result-summary-packet-0703a
- 총 11행, 자동채택 0건 발췌, paused 1건

### paused 행
```json
{
 "@context": {
  "bp": "urn:bp:",
  "ce": "https://cloudevents.io/spec/v1.0/",
  "prov": "http://www.w3.org/ns/prov#",
  "xsd": "http://www.w3.org/2001/XMLSchema#"
 },
 "@id": "urn:bp:building:task-statement-d211877b95e0-node::raw/link.jsonl#4",
 "building_id": "task-statement-d211877b95e0-node",
 "datacontenttype": "application/json",
 "dataschema": "urn:bp:schema:graph-ready-v1",
 "declared_gate_refs": [
  "link-gate:default-transition"
 ],
 "generatedAtTime": "2026-07-02T22:44:37Z",
 "id": "urn:bp:building:task-statement-d211877b95e0-node::raw/link.jsonl#4",
 "movement": "forward",
 "movement_source": "caller-declared Building Plan Link row",
 "raw_ref": "raw:link:04",
 "raw_refs": [
  "raw:link:04"
 ],
 "recorded_at": "2026-07-02T22:44:37Z",
 "schema_version": "graph-ready-v1",
 "source": "urn:bp:building:task-statement-d211877b95e0-node",
 "source_brick_instance_ref": "brick-task-statement-d211877b95e0-node-review",
 "specversion": "1.0",
 "step_ref": "task-statement-d211877b95e0-node-review",
 "subject": "task-statement-d211877b95e0-node-review",
 "target": "brick-task-statement-d211877b95e0-node-closure",
 "target_brick_instance_ref": "brick-task-statement-d211877b95e0-node-closure",
 "time": "2026-07-02T22:44:37Z",
 "transition_lifecycle_carry_budget_evidence_ref": "evidence/claim_trace/link/carry_trace.json#carry-budget:task-statement-d211877b95e0-node:node:brick-task-statement-d211877b95e0-node-work",
 "transition_lifecycle_from_brick_ref": "brick-task-statement-d211877b95e0-node-review",
 "transition_lifecycle_not_proven": [
  "semantic correctness of the agent-proposed reroute",
  "parallel runtime execution (P-walker-2 fan-in/fan-out out of scope here)",
  "scheduler / queue / retry behavior",
  "caller/COO disposition after a HOLD"
 ],
 "transition_lifecycle_paused_at_ref": "link-transition:reroute-hold-task-statement-d211877b95e0-node-01-brick-task-statement-d211877b95e0-node-work-src-task-statement-d211877b95e0-node-review-depth-0-attempt-0",
 "transition_lifecycle_pending_target_ref": "brick-task-statement-d211877b95e0-node-work",
 "transition_lifecycle_progress_state": "in_progress",
 "transition_lifecycle_proof_limits": [
  "support evidence only",
  "dynamic walker walks declared gate-adopted agent-proposed routes only",
  "support authors no route or Movement",
  "not source truth",
  "not success judgment",
  "not quality judgment",
  "not Movement authority"
 ],
 "transition_lifecycle_reason_refs": [
  "transition-concern:task-stat
```
