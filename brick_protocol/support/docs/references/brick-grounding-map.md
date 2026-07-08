# Brick 자체의 grounding 지도 (실측·재파생)

_생성 2026-05-30 · HEAD 3f2046c · 앵커 67개 (live grep 재파생 67/67 확인) · workflow wquj6xu7n: catalog→독립 verify→코드 렌더_

_재검증 2026-06-11 · HEAD a000db0 · 67개 재파생 grep 전수 재실행: 48 그대로 / 19 드리프트 수리 — 18개는 토큰 verbatim 그대로 파일만 이사(evidence_assembly 분해 → brick_protocol/support/recording/* ; building_operation → native_dispatch)라 경로·현재 위치만 재지정, 1개(brick_protocol/link/gate.py 결합 게이트)는 게이트 시퀀스 개편(739b6d2)으로 심볼 이동 — 해당 앵커에 드리프트 기록 명시. 수리 후 재파생 67/67 재확인 + 프로젝트 그릇 앵커 1개 추가(아래 9절, live 검증)._

> **이 문서는 검증된 구조 데이터에서 *코드로* 렌더됨(LLM 산문 아님).** 67개 앵커는 각자의 `재파생` grep을 **실제로 다시 돌려** 현재 위치가 잡히는 것만 실렸다. 추측·추론 0.
>
> **읽는 법:** 좌표 = 줄번호가 아니라 **심볼 + 토큰 + grep 레시피**. 코드 고쳐도 안 썩는다. 위치 의심되면 `재파생` grep을 돌려라 — **안 잡히면 그게 드리프트 신호**(미니 체커).
>
> 같은 원리: PyMuPDF `search_for()`(좌표 저장 안 하고 검색해 계산) · Brick contract-derived evidence. 저장하지 말고 파생.

## 1. Brick 관측 비교 (BrickComparisonFact)

- **observe returned-value against required fields** — _anchor_
  - 묶는 것: observed_match_kind + comparison_evidence (the BrickComparisonFact) — i.e. the verdict of whether the agent return matches the declared contract
  - 가리키는 것: the keys present on returned_value (a Mapping) checked against the caller-supplied required_fields set; this factory loops returned_value.keys() and the required fields to compute observed/missing
  - symbol: `BrickComparisonFact.from_returned_value`
  - 토큰: `adapter returned value is available for Brick comparison observation`
  - 재파생: `grep -nF 'adapter returned value is available for Brick comparison observation' brick_protocol/brick/comparison.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/brick/comparison.py:128`  (matches: 1)
  - 근거:
    ```
    comparison_evidence = [
                "adapter returned value is available for Brick comparison observation",
    ```

- **encode required/observed/missing field sets as evidence-line coordinates** — _anchor_
  - 묶는 것: the comparison_evidence string lines 'required_return_fields: ...', 'observed_return_fields: ...', 'missing_return_fields: ...' that name exactly which declared fields were satisfied vs absent
  - 가리키는 것: the computed required tuple, sorted observed_fields (returned_value.keys()), and missing_fields list — rendered into comma-delimited evidence so each named field traces back to the declared contract field and the actual returned key
  - symbol: `BrickComparisonFact.from_returned_value`
  - 토큰: `"missing_return_fields: " + ", ".join(missing_fields)`
  - 재파생: `grep -nF '"missing_return_fields: " + ", ".join(missing_fields)' brick_protocol/brick/comparison.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/brick/comparison.py:140`  (matches: 1)
  - 근거:
    ```
                comparison_evidence.append(
                    "missing_return_fields: " + ", ".join(missing_fields)
    ```

- **decide observed_match_kind from presence of missing fields** — _derive_
  - 묶는 것: the categorical observed_match_kind value ('missing' when any required field absent, 'matched' when required set fully present, 'unknown' when nothing was declared)
  - 가리키는 것: the missing_fields tuple and the required tuple computed just above; the kind is a pure function of whether missing_fields is non-empty and whether required is non-empty — not a success/quality judgment
  - symbol: `BrickComparisonFact.from_returned_value`
  - 토큰: `observed_match_kind = "missing"`
  - 재파생: `grep -nF 'observed_match_kind = "missing"' brick_protocol/brick/comparison.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/brick/comparison.py:145`  (matches: 1)
  - 근거:
    ```
            if missing_fields:
                observed_match_kind = "missing"
    ```

- **made_changes / no_changes_reason satisfaction equivalence** — _derive_
  - 묶는 것: whether the declared field 'made_changes' counts as present (and thus NOT added to missing_return_fields)
  - 가리키는 것: the actual returned_value mapping: the required 'made_changes' field is treated as satisfied when the key 'no_changes_reason' is present instead — a specific contract-equivalence rule tying the declared field to an alternate returned key
  - symbol: `BrickComparisonFact.from_returned_value`
  - 토큰: `if field_name == "made_changes" and "no_changes_reason" in returned_value:`
  - 재파생: `grep -nF 'if field_name == "made_changes" and "no_changes_reason" in returned_value:' brick_protocol/brick/comparison.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/brick/comparison.py:122`  (matches: 1)
  - 근거:
    ```
                    if field_name == "made_changes" and "no_changes_reason" in returned_value:
                        continue
    ```

- **parse evidence line back into field names (reverse grounding accessor)** — _pointer_
  - 묶는 것: required_return_fields() and missing_return_fields() — the machine-readable field tuples downstream Link gates consume
  - 가리키는 것: the comparison_evidence string lines themselves: it finds the item starting with the prefix ('required_return_fields:' / 'missing_return_fields:'), strips it, treats ''/'none' as empty, else splits on commas — so each downstream field traces back to a specific evidence line in this same fact
  - symbol: `BrickComparisonFact.fields_from_evidence`
  - 토큰: `def fields_from_evidence(self, prefix: str) -> tuple[str, ...]:`
  - 재파생: `grep -nF 'def fields_from_evidence(self, prefix: str) -> tuple[str, ...]:' brick_protocol/brick/comparison.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/brick/comparison.py:159`  (matches: 1)
  - 근거:
    ```
            for item in self.comparison_evidence:
                if not item.startswith(prefix):
    ```

- **validate observed_match_kind against the closed vocabulary** — _proof-limit_
  - 묶는 것: the constraint that observed_match_kind is one of a fixed observation vocabulary (matched/missing/mismatched/unknown) or blank — never a pass/fail or success verdict
  - 가리키는 것: the module-level allowed-kinds tuple; _observed_match_kind lowercases the value and raises ValueError if not in this set, bounding the comparison output to pure contract-shape observation (mirrors comparison.yaml allowed_observed_match_kind)
  - symbol: `BrickComparisonFact._observed_match_kind`
  - 토큰: `_OBSERVED_MATCH_KINDS: tuple[str, ...] = ("matched", "missing", "mismatched", "unknown")`
  - 재파생: `grep -nF '_OBSERVED_MATCH_KINDS: tuple[str, ...] = ("matched", "missing", "mismatched", "unknown")' brick_protocol/brick/comparison.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/brick/comparison.py:12`  (matches: 1)
  - 근거:
    ```
    _OBSERVED_MATCH_KINDS: tuple[str, ...] = ("matched", "missing", "mismatched", "unknown")
    ```

- **compute the declared required-field set (Brick shape + Link gate-derived union)** — _anchor_
  - 묶는 것: the required_fields argument fed into BrickComparisonFact.from_returned_value (the 'what was declared' side of the comparison)
  - 가리키는 것: two sources unioned: base = parse_required_return_shape(prepared.brick_work.required_return_shape) (the Brick declaration) plus gate_refs read from prepared.step_rows.link_row[_DECLARED_GATE_REFS_KEY] expanded via Link's gate_required_return_fields — so every required field traces to either the Brick required_return_shape or a declared Link gate ref
  - symbol: `plan_validation._required_agent_return_fields_for_brick_handoff`
  - 토큰: `return gate_required_return_fields(gate_refs, base)`
  - 재파생: `grep -nF 'return gate_required_return_fields(gate_refs, base)' brick_protocol/support/operator/plan_validation.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/operator/plan_validation.py:547`  (matches: 1)
  - 근거:
    ```
        base = _required_return_shape_fields(prepared.brick_work.required_return_shape)
    ...
    ```

- **Link-owned gate->required-fields mapping** — _derive_
  - 묶는 것: the extra required Agent-return fields implied by each declared gate ref, appended onto the Brick base required fields
  - 가리키는 것: the _GATE_REQUIRED_RETURN_FIELDS mapping (ref -> extra fields): base_required_fields come first, then for each gate ref present in gate_refs its fixed extra fields are appended, order preserved and duplicates removed — so a missing gate-derived field in the comparison traces to a specific declared gate ref
  - symbol: `link.gate.gate_required_return_fields`
  - 토큰: `def gate_required_return_fields(`
  - 재파생: `grep -nF 'def gate_required_return_fields(' brick_protocol/link/gate.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/link/gate.py:107`  (matches: 1)
  - 근거:
    ```
        fields = list(base_required_fields)
        refs = tuple(gate_refs)
    ```

- **project comparison fact into the traceable Brick claim-fact evidence record** — _pointer_
  - 묶는 것: the persisted Brick comparison claim fact (fact_ref 'brick-comparison:<building>:<step>') that a reader sees in the run evidence: observed_match_kind, comparison_evidence lines, required_return_shape_evidence
  - 가리키는 것: the live BrickComparisonFact on result.completion.brick_comparison plus raw_refs=[_raw_ref('brick',...), _raw_ref('agent',...)] tying the claim to the raw Brick declaration and raw Agent return rows; the literal label asserts this is contract-shape observation, never a success/quality judgment
  - symbol: `recording.claims_brick._brick_claim_facts (comparison claim block)`
  - 토큰: `"comparison_observation": "contract observation only; not success judgment"`
  - 재파생: `grep -nF '"comparison_observation": "contract observation only; not success judgment",' brick_protocol/support/recording/claims_brick.py`
  - 현재 위치(live 2026-06-11, 재파생 재실행): `brick_protocol/support/recording/claims_brick.py:93`  (matches: 2; also :118)
  - 근거:
    ```
                        "observed_match_kind": result.completion.brick_comparison.observed_match_kind,
    ...
    ```

## 2. raw_refs — 원시 증거 포인터

- **Canonical raw-ref minter (raw:{kind}:NN)** — _anchor_
  - 묶는 것: The literal raw-reference coordinate token itself (e.g. raw:brick:01, raw:agent:01, raw:link:01) that every public fact / raw record points back to.
  - 가리키는 것: A deterministic per-axis, per-step ordinal: the kind (brick|agent|link|agent-received|link-frontier|adapter-error) plus the 1-based step index, zero-padded. This is THE fundamental coordinate string.
  - symbol: `primitives._raw_ref`
  - 토큰: `return f"raw:{kind}:{index:02d}"`
  - 재파생: `grep -nF 'return f"raw:{kind}:{index:02d}"' brick_protocol/support/operator/primitives.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/operator/primitives.py:454`  (matches: 1)
  - 근거:
    ```
    def _raw_ref(kind: str, index: int) -> str:
        return f"raw:{kind}:{index:02d}"
    ```

- **Event-type to axis dispatch (brick_protocol/brick/agent/link)** — _derive_
  - 묶는 것: Which axis namespace a capture event's raw_ref lands in: agent_* events -> raw:agent:NN, link_* events -> raw:link:NN, everything else -> raw:brick:NN.
  - 가리키는 것: The CaptureEvent.event_type prefix; it routes the event to the correct raw:{axis}:NN coordinate so the public capture event ties to the right raw stream.
  - symbol: `primitives._event_raw_ref`
  - 토큰: `def _event_raw_ref(event_type: str, index: int) -> str:`
  - 재파생: `grep -nF 'def _event_raw_ref(event_type: str, index: int) -> str:' brick_protocol/support/operator/primitives.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/operator/primitives.py:457`  (matches: 1)
  - 근거:
    ```
        if event_type.startswith("agent_"):
            return _raw_ref("agent", index)
    ```

- **Graph-edge raw-ref minter (raw:link-graph:NN:<edge-slug>)** — _anchor_
  - 묶는 것: The raw-reference coordinate for each DECLARED graph edge (link-graph axis), e.g. raw:link-graph:01:<edge-ref-slug>, attached to graph link raw records and the accumulated raw manifest.
  - 가리키는 것: A declared graph edge's edge_ref (slugified) plus its 1-based ordinal among declared edges; ties graph-level link facts back to the specific declared edge.
  - symbol: `plan_graph._graph_link_raw_ref`
  - 토큰: `return f"raw:link-graph:{index:02d}:{_resource_slug(`
  - 재파생: `grep -nF 'return f"raw:link-graph:{index:02d}:{_resource_slug(' brick_protocol/support/operator/plan_graph.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/operator/plan_graph.py:385`  (matches: 1)
  - 근거:
    ```
    def _graph_link_raw_ref(index: int, edge_ref: str) -> str:
        return f"raw:link-graph:{index:02d}:{_resource_slug('edge_ref', edge_ref.replace(':', '-'))}"
    ```

- **Attach raw:agent:NN to step-output observation** — _pointer_
  - 묶는 것: Each StepOutputObservation (the agent's received-work + returned-fact record for a step) is stamped with raw_ref = raw:agent:NN.
  - 가리키는 것: The agent raw-return stream coordinate for that step index; alongside received_work_ref / returned_fact_ref it ties the step output back to raw:agent:NN in raw/agent-return.jsonl.
  - symbol: `recording.claims_common._step_output_observations`
  - 토큰: `raw_ref=_raw_ref("agent", index)`
  - 재파생: `grep -nF 'raw_ref=_raw_ref("agent", index)' brick_protocol/support/recording/claims_common.py`
  - 현재 위치(live 2026-06-11, 재파생 재실행): `brick_protocol/support/recording/claims_common.py:92`  (matches: 1)
  - 근거:
    ```
                    raw_ref=_raw_ref("agent", index),
                    task_source_ref=task_source_ref or "",
    ```

- **Brick raw record carries raw:brick:NN (raw_ref + raw_refs)** — _pointer_
  - 묶는 것: Each per-step Brick raw record (work_statement, comparison_rule, required_return_shape, source_facts) is keyed by raw_ref=raw:brick:NN and self-lists raw_refs=[raw:brick:NN].
  - 가리키는 것: The Brick-axis raw coordinate for that step; this is the source-of-record row (persisted to raw/brick-work.jsonl) that downstream Brick public facts cite via raw_refs.
  - symbol: `recording.claims_brick._brick_raw_records`
  - 토큰: `def _brick_raw_records(`
  - 재파생: `grep -nF 'def _brick_raw_records(' brick_protocol/support/recording/claims_brick.py`
  - 현재 위치(live 2026-06-11, 재파생 재실행): `brick_protocol/support/recording/claims_brick.py:26`  (matches: 1)
  - 근거:
    ```
                    "raw_ref": _raw_ref("brick", index),
                    "raw_refs": [_raw_ref("brick", index)],
    ```

- **Link raw record carries raw:link:NN (raw_ref + raw_refs)** — _pointer_
  - 묶는 것: Each per-step Link raw record (source/target brick_instance_ref, movement, route-replay / gate / transition-lifecycle evidence fields) is keyed by raw_ref=raw:link:NN and self-lists raw_refs=[raw:link:NN].
  - 가리키는 것: The Link-axis raw coordinate for that step's crossing (movement comes from result.completion.crossing_record.link_fact.movement); persisted to raw/link.jsonl, cited by Link public facts via raw_refs.
  - symbol: `evidence_assembly._link_raw_records`
  - 토큰: `"raw_ref": _raw_ref("link", index),`
  - 재파생: `grep -rnF '"raw_ref": _raw_ref("link", index),' brick_protocol/support/`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/operator/evidence_assembly.py:1548`  (matches: 1)
  - 근거:
    ```
                "raw_ref": _raw_ref("link", index),
                "raw_refs": [_raw_ref("link", index)],
    ```

- **Stamp capture event with axis-dispatched raw_ref** — _pointer_
  - 묶는 것: Each persisted CaptureEvent (capture/events.jsonl receipt) gets raw_ref = _event_raw_ref(event_type, step_index), i.e. its raw:brick|agent|link:NN coordinate.
  - 가리키는 것: The axis-correct raw stream record for that step (via _event_raw_ref dispatch); this is the field that ties a public capture receipt back to the raw evidence row it summarizes.
  - symbol: `recording.lifecycle_emit._enrich_capture_event`
  - 토큰: `raw_ref=_event_raw_ref(event.event_type, step_index)`
  - 재파생: `grep -nF 'raw_ref=_event_raw_ref(event.event_type, step_index)' brick_protocol/support/recording/lifecycle_emit.py`
  - 현재 위치(live 2026-06-11, 재파생 재실행): `brick_protocol/support/recording/lifecycle_emit.py:160`  (matches: 1)
  - 근거:
    ```
            raw_ref=_event_raw_ref(event.event_type, step_index),
            not_proven=event.not_proven,
    ```

- **Schema-level guarantee: every capture event MUST carry a non-empty raw_ref** — _proof-limit_
  - 묶는 것: Enforces that the raw_ref coordinate is a required, non-blank string on the frozen CaptureEvent dataclass (raw_ref is also a declared field at capture.py:143 and an ENVELOPE_FIELD_KEYS member at line 108).
  - 가리키는 것: _required_text validation: no capture receipt event can exist WITHOUT a raw_ref pointer, so the public-fact-to-raw-source grounding link can never be silently dropped.
  - symbol: `capture.CaptureEvent.__post_init__`
  - 토큰: `object.__setattr__(self, "raw_ref", _required_text("raw_ref", self.raw_ref))`
  - 재파생: `grep -nF 'object.__setattr__(self, "raw_ref", _required_text("raw_ref", self.raw_ref))' brick_protocol/support/recording/capture.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/recording/capture.py:166`  (matches: 1)
  - 근거:
    ```
            object.__setattr__(self, "raw_ref", _required_text("raw_ref", self.raw_ref))
    ```

- **Persist raw records (each carrying raw_ref) to raw/*.jsonl** — _anchor_
  - 묶는 것: The writer that lands the brick_protocol/brick/agent/link raw records (each row embedding its raw:{kind}:NN raw_ref) onto disk at raw/brick-work.jsonl, raw/agent-return.jsonl, raw/link.jsonl under the building root.
  - 가리키는 것: RawClaimTracePacket.{brick,agent,link}_raw_records produced by evidence_assembly; this is the on-disk landing of the raw coordinate so a future reader can open the exact jsonl row a raw_ref names.
  - symbol: `raw_claim_trace.write_raw_and_claim_trace`
  - 토큰: `raw_dir / "agent-return.jsonl",`
  - 재파생: `grep -nF 'raw_dir / "agent-return.jsonl",' brick_protocol/support/recording/raw_claim_trace.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/recording/raw_claim_trace.py:34`  (matches: 1)
  - 근거:
    ```
            raw_dir / "agent-return.jsonl",
            _graph_ready_records(
    ```

## 3. building-map.json — 축 교차 그래프

- **Building-map per-step row producer (wires all axis-crossing refs)** — _anchor_
  - 묶는 것: Each link_edge crossing in building-map.json: its source/target_brick_instance_ref endpoints and its public_fact_refs / input_public_fact_refs / movement_fact_ref / transition_fact_ref. This is the single loop that, per executed step, ties the axis crossing (brick -> next brick) to the facts produced at it.
  - 가리키는 것: The per-step grounding coordinates minted in the same loop: source_brick_instance_ref=prepared.brick_instance_ref, target_brick_instance_ref=prepared.next_brick_instance_ref (the executed Building step's boundaries), and agent_fact_ref/comparison_ref/movement_ref = _step_fact_ref('agent-fact'|'brick-comparison'|'movement-fact', index, step_ref) (the claim_trace fact refs).
  - symbol: `recording.building_map_emit._accumulated_building_map_packet`
  - 토큰: `input_public_fact_refs=[agent_fact_ref, comparison_ref, movement_ref],`
  - 재파생: `grep -nF 'input_public_fact_refs=[agent_fact_ref, comparison_ref, movement_ref],' brick_protocol/support/recording/building_map_emit.py`
  - 현재 위치(live 2026-06-11, 재파생 재실행): `brick_protocol/support/recording/building_map_emit.py:181`  (matches: 1)
  - 근거:
    ```
    input_public_fact_refs=[agent_fact_ref, comparison_ref, movement_ref],
                public_fact_refs=[agent_fact_ref, comparison_ref, movement_ref],
    ```

- **agent_binding -> brick_instance_ref wiring (the agent-to-brick crossing)** — _anchor_
  - 묶는 것: Each agent_bindings[] row in building-map.json: agent_binding_id=binding_ref, brick_instance_ref=prepared.brick_instance_ref (which Brick the Agent performed), agent_performer_ref, produced_public_fact_refs=[agent_fact_ref], step_output_ref. This grounds the Agent->Brick axis crossing.
  - 가리키는 것: binding_ref = _step_fact_ref('binding', index, step_ref); brick_instance_ref = prepared.brick_instance_ref (the step's brick); agent_fact_ref = _step_fact_ref('agent-fact', index, step_ref) (the returned-claim coordinate); step_output_ref = _step_output_manifest_ref(step_ref, attempt) (the raw step output path).
  - symbol: `recording.building_map_emit._accumulated_building_map_packet (build_agent_binding_row call site)`
  - 토큰: `produced_public_fact_refs=[agent_fact_ref],`
  - 재파생: `grep -nF 'produced_public_fact_refs=[agent_fact_ref],' brick_protocol/support/recording/building_map_emit.py`
  - 현재 위치(live 2026-06-11, 재파생 재실행): `brick_protocol/support/recording/building_map_emit.py:155`  (matches: 1)
  - 근거:
    ```
    agent_performer_ref=f"agent-performer:{prepared.agent_object.object_ref}",
                    binding_role="primary",
    ```

- **Contract-derived link_edge emitter (LINK backbone field set)** — _derive_
  - 묶는 것: The exact on-disk shape of every link_edge row (source_brick_instance_ref, target_brick_instance_ref, input_public_fact_refs, public_fact_refs, movement_fact_ref, transition_fact_ref, step_output_ref). Built by iterating the contract field-spec, so a crossing field cannot be silently dropped or an undeclared one added.
  - 가리키는 것: building_map_link_edge_specs() in brick_protocol/support/recording/contracts.py (the LINK-backbone field-spec), iterated by _build_from_specs which raises if a contract-required crossing field is missing or an undeclared key is supplied.
  - symbol: `operator_evidence.build_link_edge_row`
  - 토큰: `record_label="building_map.link_edge",`
  - 재파생: `grep -nF 'record_label="building_map.link_edge",' brick_protocol/support/recording/operator_evidence.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/recording/operator_evidence.py:242`  (matches: 1)
  - 근거:
    ```
        record = _build_from_specs(
            building_map_link_edge_specs(),
    ```

- **LINK-axis crossing field contract (single source of the link_edge shape)** — _anchor_
  - 묶는 것: Declares that every link_edge crossing row carries source_brick_instance_ref + target_brick_instance_ref (the two axis endpoints) and input_public_fact_refs + public_fact_refs + movement_fact_ref + transition_fact_ref (the facts grounding that crossing). This is the ONE home for the link-edge crossing shape.
  - 가리키는 것: Consumed by building_map_link_edge_specs() (same file) which the emitter build_link_edge_row iterates and the ζ6 checker derives from; the field names here are the literal keys that appear in building-map.json link_edges[].
  - symbol: `contracts.BUILDING_MAP_LINK_EDGE_REQUIRED_FIELDS`
  - 토큰: `BUILDING_MAP_LINK_EDGE_REQUIRED_FIELDS: tuple`
  - 재파생: `grep -nF 'BUILDING_MAP_LINK_EDGE_REQUIRED_FIELDS: tuple' brick_protocol/support/recording/contracts.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/recording/contracts.py:365`  (matches: 1)
  - 근거:
    ```
    BUILDING_MAP_LINK_EDGE_REQUIRED_FIELDS: tuple[str, ...] = (
        "link_edge_id",
    ```

- **AGENT-axis crossing field contract (agent_binding.brick_instance_ref declared here)** — _anchor_
  - 묶는 것: Declares the agent_binding crossing row shape: brick_instance_ref (which Brick this Agent performed = the Agent->Brick crossing endpoint), agent_performer_ref, produced_public_fact_refs (the AgentFact refs this binding grounds), and step_output_ref. ONE home for the agent_binding shape.
  - 가리키는 것: Consumed by building_map_agent_binding_specs(), iterated by build_agent_binding_row; the names here are the literal keys in building-map.json agent_bindings[], and brick_instance_ref must resolve to a brick_instance_id (checker enforces).
  - symbol: `contracts.BUILDING_MAP_AGENT_BINDING_REQUIRED_FIELDS`
  - 토큰: `BUILDING_MAP_AGENT_BINDING_REQUIRED_FIELDS: tuple`
  - 재파생: `grep -nF 'BUILDING_MAP_AGENT_BINDING_REQUIRED_FIELDS: tuple' brick_protocol/support/recording/contracts.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/recording/contracts.py:350`  (matches: 1)
  - 근거:
    ```
    BUILDING_MAP_AGENT_BINDING_REQUIRED_FIELDS: tuple[str, ...] = (
        "agent_binding_id",
    ```

- **Crossing-ref coordinate producer (mints the binding/agent-fact/movement-fact tokens)** — _anchor_
  - 묶는 것: The actual grounding-coordinate STRINGS that every crossing field points to: binding:NN:slug (agent_binding_id), agent-fact:NN:slug (produced_public_fact_refs / public_fact_refs), movement-fact:NN:slug (movement_fact_ref), transition-fact:NN:slug, brick-comparison:NN:slug. kind + per-step index + step_ref slug = a deterministic, re-derivable citation key.
  - 가리키는 것: Its inputs (kind, the 1-based step index, and step_ref) tie each ref back to a specific executed Building step; the matching claim_trace fact under evidence/claim_trace/{brick,agent,link}/ carries fact_ref equal to this string, which is what the checker resolves public_fact_refs against.
  - symbol: `primitives._step_fact_ref`
  - 토큰: `return f"{kind}:{index:02d}:{slug}"`
  - 재파생: `grep -nF 'return f"{kind}:{index:02d}:{slug}"' brick_protocol/support/operator/primitives.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/operator/primitives.py:467`  (matches: 1)
  - 근거:
    ```
    def _step_fact_ref(kind: str, index: int, step_ref: str) -> str:
        slug = _resource_slug("step_ref", step_ref.replace(":", "-"))
    ```

- **Checker: agent_binding.brick_instance_ref must resolve to a real brick id** — _proof-limit_
  - 묶는 것: Enforces that the Agent->Brick crossing is grounded: every agent_bindings[].brick_instance_ref must be a member of brick_id_set (the set of declared brick_instance_id values). A dangling crossing ref is a violation.
  - 가리키는 것: brick_id_set, built upstream from text_id(item,'brick_instance_id',...) over brick_instances[]; thus the crossing is checked to point at an actually-declared brick instance, not free text.
  - symbol: `check_building_map_graph.validate_graph_map (agent-binding resolution loop)`
  - 토큰: `agent binding brick_instance_ref does not resolve`
  - 재파생: `grep -nF 'agent binding brick_instance_ref does not resolve' brick_protocol/support/checkers/check_building_map_graph.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/checkers/check_building_map_graph.py:835`  (matches: 1)
  - 근거:
    ```
            ref = item.get("brick_instance_ref")
            if not isinstance(ref, str) or ref not in brick_id_set:
    ```

- **Checker: link_edge source/target_brick_instance_ref endpoints must resolve to brick ids** — _proof-limit_
  - 묶는 것: Enforces that each link_edge axis crossing's two endpoints (source_brick_instance_ref, target_brick_instance_ref) resolve to a brick_instance_id and are NOT an agent ref, agent_binding_id, agent_performer_ref, AgentFact ref, or raw ref. This keeps the crossing brick-to-brick and grounded in declared instances.
  - 가리키는 것: endpoint_problem() checks the value against brick_ids plus the agent_binding_ids / agent_performer_refs / agent_fact_refs / raw_refs exclusion sets; called from validate_link_endpoint_fields over ('source_brick_instance_ref','target_brick_instance_ref') at line 647.
  - symbol: `check_building_map_graph.validate_link_endpoint_fields`
  - 토큰: `endpoint must resolve to brick_instance_id, not prefix-only text`
  - 재파생: `grep -nF 'endpoint must resolve to brick_instance_id, not prefix-only text' brick_protocol/support/checkers/check_building_map_graph.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/checkers/check_building_map_graph.py:338`  (matches: 1)
  - 근거:
    ```
        if value not in brick_ids:
            return "endpoint must resolve to brick_instance_id, not prefix-only text"
    ```

- **Checker: link_edge/binding public_fact_refs must resolve through claim_trace** — _proof-limit_
  - 묶는 것: Enforces that every fact ref a crossing cites (public_fact_refs, input_public_fact_refs, produced_public_fact_refs, movement_fact_ref, transfer/carry/sufficiency refs -- the GRAPH_FACT_REF_KEYS) actually appears as a fact in the building's evidence/claim_trace/*.json. This is the resolution that makes the crossing-to-fact grounding verifiable, not asserted.
  - 가리키는 것: known_claim_refs from evidence_claim_refs(building_root,...), which reads fact_ref/fact_id from the six CLAIM_TRACE_RELATIVE_PATHS files; collect_graph_fact_refs(value) gathers the refs cited in the map under GRAPH_FACT_REF_KEYS (which include 'public_fact_refs','movement_fact_ref', etc.).
  - symbol: `check_building_map_graph.validate_evidence_refs`
  - 토큰: `graph public fact ref does not resolve through claim_trace`
  - 재파생: `grep -nF 'graph public fact ref does not resolve through claim_trace' brick_protocol/support/checkers/check_building_map_graph.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/checkers/check_building_map_graph.py:568`  (matches: 1)
  - 근거:
    ```
            for ref in sorted(graph_fact_refs):
                if ref not in known_claim_refs:
    ```

## 4. AgentFact — 받은 일 / 돌려준 것

- **Closed AgentFact two-field shape** — _anchor_
  - 묶는 것: The entire Agent-axis evidence record: an AgentFact is exactly two public facts — received_work (what came in) and returned (what went out) — with no third field, so every agent output is grounded as 'received vs returned' and nothing else.
  - 가리키는 것: The frozen dataclass fields received_work and returned (lines 120-121); make_agent_fact requires BOTH (raises 'AgentFact requires public fact value(s):' if MISSING), so a fact cannot exist without naming its received source and its returned payload.
  - symbol: `AgentFact (dataclass) / make_agent_fact`
  - 토큰: `Agent records the received work and what was returned.`
  - 재파생: `grep -nF 'Agent records the received work and what was returned.' brick_protocol/agent/return_fact.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/agent/return_fact.py:118`  (matches: 1)
  - 근거:
    ```
    @dataclass(frozen=True)
    class AgentFact:
    ```

- **Concern-kind closed admission set (8 kinds)** — _anchor_
  - 묶는 것: The concern_kind carried inside a returned transition_concern: it is grounded to a closed vocabulary, not free text. Any concern_kind outside the admitted set is rejected at construction time.
  - 가리키는 것: TRANSITION_CONCERN_KINDS frozenset (lines 9-20): design_gap, implementation_gap, upstream_gap, boundary_mismatch, insufficient_input, replay_needed, verification_gap, unknown. The membership test 'if concern_kind not in TRANSITION_CONCERN_KINDS' (line 99) is the source coordinate for what kinds are legal.
  - symbol: `validate_transition_concern_evidence`
  - 토큰: `transition_concern_evidence.concern_kind is not admitted`
  - 재파생: `grep -nF 'transition_concern_evidence.concern_kind is not admitted' brick_protocol/agent/return_fact.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/agent/return_fact.py:100`  (matches: 1)
  - 근거:
    ```
        if concern_kind not in TRANSITION_CONCERN_KINDS:
            raise ValueError("transition_concern_evidence.concern_kind is not admitted")
    ```

- **concern_ref namespace prefix grounding** — _anchor_
  - 묶는 것: The concern_ref identifier on a returned concern: it must be a namespaced coordinate in the 'transition-concern:' space, so each concern traces back to an addressable transition-concern reference rather than an opaque label.
  - 가리키는 것: The prefix check 'if not concern_ref.startswith("transition-concern:")' (line 96), fed by the required-text concern_ref pulled from concern.get('concern_ref') (line 95). The emitter later mints the matching ref 'transition-concern:{slug}:attempt-{n}' in step_outputs.py:136.
  - symbol: `validate_transition_concern_evidence`
  - 토큰: `transition_concern_evidence.concern_ref must start with transition-concern:`
  - 재파생: `grep -nF 'transition_concern_evidence.concern_ref must start with transition-concern:' brick_protocol/agent/return_fact.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/agent/return_fact.py:97`  (matches: 1)
  - 근거:
    ```
        if not concern_ref.startswith("transition-concern:"):
            raise ValueError("transition_concern_evidence.concern_ref must start with transition-concern:")
    ```

- **Concern points back to Brick-boundary coordinates** — _anchor_
  - 묶는 것: The related_boundary_refs list on a returned concern: every boundary a concern points at must resolve to a Brick-axis boundary coordinate (brick:, brick-, brick-boundary:, brick-instance:, building-boundary:), so the concern is grounded to the Brick that owns it instead of free-floating.
  - 가리키는 것: The startswith allow-list on each ref (lines 111-112) iterating related_refs derived from concern.get('related_boundary_refs') (lines 106-109). This is the source coordinate tying an Agent concern to a Brick boundary.
  - symbol: `validate_transition_concern_evidence`
  - 토큰: `transition_concern_evidence.related_boundary_refs must name Brick boundaries`
  - 재파생: `grep -nF 'transition_concern_evidence.related_boundary_refs must name Brick boundaries' brick_protocol/agent/return_fact.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/agent/return_fact.py:112`  (matches: 1)
  - 근거:
    ```
            if not ref.startswith(("brick:", "brick-", "brick-boundary:", "brick-instance:", "building-boundary:")):
                raise ValueError("transition_concern_evidence.related_boundary_refs must name Brick boundaries")
    ```

- **No-judgment guard: forbidden keys on returned** — _proof-limit_
  - 묶는 것: The boundary of what the returned payload may NOT contain: success/failure/quality/movement/credential/route/session judgment keys (approved, complete, done, fail, success, verdict, score, quality_judgment, route_target, secret, status, ...). This is what makes the Agent axis 'no success/failure judgment'.
  - 가리키는 것: The literal frozenset of 35 forbidden keys (lines 32-68), re-exported and consumed by the recording layer as _ROUTE_REQUEST_FORBIDDEN_KEYS (brick_protocol/support/recording/step_outputs.py:11). It is the source-of-truth list a reader checks to see why a judgment field is rejected from returned.
  - symbol: `RETURNED_FORBIDDEN_KEYS`
  - 토큰: `RETURNED_FORBIDDEN_KEYS: frozenset[str] = frozenset(`
  - 재파생: `grep -nF 'RETURNED_FORBIDDEN_KEYS: frozenset[str] = frozenset(' brick_protocol/agent/return_fact.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/agent/return_fact.py:32`  (matches: 1)
  - 근거:
    ```
    RETURNED_FORBIDDEN_KEYS: frozenset[str] = frozenset(
        {
    ```

- **Closed-shape enforcement at record write** — _derive_
  - 묶는 것: agent_returned_claims (and reviewer_returned_claims) recorded into the run record: enforced to have exactly the AgentFact key set and nothing more, so the persisted evidence cannot drift from the closed shape defined in return_fact.py.
  - 가리키는 것: Comparison 'if keys != set(AGENT_FACT_FIELDS)' (line 613), where AGENT_FACT_FIELDS is imported from brick_protocol.agent.return_fact (records.py:14). The shape law lives in return_fact.py; this is the enforcement coordinate that points back to it. Called at records.py:240 and 257.
  - symbol: `_assert_agent_fact_shape`
  - 토큰: `must contain exactly received_work and returned`
  - 재파생: `grep -nF 'must contain exactly received_work and returned' brick_protocol/support/recording/records.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/recording/records.py:614`  (matches: 1)
  - 근거:
    ```
        keys = {field_value.key for field_value in value.fields}
        if keys != set(AGENT_FACT_FIELDS):
    ```

- **Emitter ties received/returned to source refs** — _pointer_
  - 묶는 것: The persisted step-output packet for one agent attempt: the returned payload (observation.returned) is emitted alongside grounding coordinates received_work_ref and returned_fact_ref, so a reader can trace the returned fact back to the exact received-work source and returned-fact source on disk.
  - 가리키는 것: The output_packet dict (lines 54-75) carrying agent_fact_fields=['received_work','returned'] (line 61), received_work_ref (line 62), returned_fact_ref (line 63), plus evidence_refs raw_ref / claim_trace_ref / building_map_ref (lines 67-72) — the source coordinates the returned fact points to.
  - symbol: `write_step_outputs`
  - 토큰: `"returned_fact_ref": observation.returned_fact_ref,`
  - 재파생: `grep -nF '"returned_fact_ref": observation.returned_fact_ref,' brick_protocol/support/recording/step_outputs.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/recording/step_outputs.py:63`  (matches: 1)
  - 근거:
    ```
                "agent_fact_fields": ["received_work", "returned"],
                "received_work_ref": observation.received_work_ref,
    ```

- **Concern is contract-derived FROM returned** — _derive_
  - 묶는 것: The transition-concern evidence packet: it is not invented by the recorder — it is read out of the Agent's own returned payload and then re-validated, so the emitted concern is grounded to what the Agent actually returned.
  - 가리키는 것: returned.get('transition_concern_evidence') (line 294) followed by 'return validate_transition_concern_evidence(concern)' (line 300), which re-applies the return_fact.py contract (concern_ref prefix, concern_kind admission, Brick-boundary refs). The returned payload is the source; the contract validator is the gate.
  - symbol: `_transition_concern_from_returned`
  - 토큰: `concern = returned.get("transition_concern_evidence")`
  - 재파생: `grep -nF 'concern = returned.get("transition_concern_evidence")' brick_protocol/support/recording/step_outputs.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/recording/step_outputs.py:294`  (matches: 1)
  - 근거:
    ```
        concern = returned.get("transition_concern_evidence")
        ...
    ```

## 5. Link 이동·게이트 fact

- **MovementFact grounding fields (gatefact_reference + transition_history_reference)** — _anchor_
  - 묶는 것: A Link movement decision (forward/reroute) as a MovementFact carrying the chosen English literal plus optional pointers tying that decision to its justification.
  - 가리키는 것: gatefact_reference (the GateFact sufficiency verdict that justified the move) and transition_history_reference (the prior transition chain); plus handoff_target_fact (the destination fact). The MovementFact dataclass fields at brick_protocol/link/movement.py:33-35 declare these grounding pointers; make_movement_fact at line 42 forwards them without creating any Gate/runtime authority.
  - symbol: `brick_protocol/link/movement.py :: MovementFact / make_movement_fact`
  - 토큰: `Build a Link Movement fact without creating Gate or runtime authority.`
  - 재파생: `grep -nF 'Build a Link Movement fact without creating Gate or runtime authority.' brick_protocol/link/movement.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/link/movement.py:50`  (matches: 1)
  - 근거:
    ```
    ADMITTED_MOVEMENT_FORWARD = {"movement": "forward"} ... gatefact_reference: str | None = None / transition_history_reference: str | None = None  (MovementFact, lines 12-35); make_movement_fact docstring line 50: "Build a Link Movement fact without creating Gate or runtime authority."
    ```

- **per-gate evaluation names the exact BrickComparisonFact coordinates required/missing** — _anchor_
  - 묶는 것: Gate sufficiency for a movement (sufficient vs missing_required_facts) at the movement stage.
  - 가리키는 것: Named source coordinates inside the Brick comparison handoff: BrickComparisonFact.required_return_shape_evidence, .comparison_evidence, and per-field BrickComparisonFact.comparison_evidence.returned_field.<name>; plus Link.route_decision_basis.human_review_refs / override_refs for link-gate:human / link-gate:coo. Missing coordinates are listed in missing_required_facts, so the verdict is traceable to which exact fact was absent.
  - 드리프트 기록(0611 재검증): 옛 anchor는 evaluate_declared_movement_gate가 좌표 목록을 직접 하드코딩했다(BrickComparisonFact.observed_match_kind 포함, 옛 brick_protocol/link/gate.py:146). 게이트 시퀀스 개편(739b6d2) 후 좌표 명명은 per-gate 평가(evaluate_declared_gate_ref)로 이동했고, evaluate_declared_movement_gate는 ordered per-gate GateFact들에서 결합 GateFact를 파생한다(observed_match_kind 파라미터는 API 호환용으로만 유지). 개념(좌표 단위 추적가능성)은 동일, 심볼만 이동.
  - symbol: `brick_protocol/link/gate.py :: evaluate_declared_gate_ref` (결합: `evaluate_declared_movement_gate` → `derive_movement_gate_fact_from_gate_results`)
  - 토큰: `"BrickComparisonFact.required_return_shape_evidence",`
  - 재파생: `grep -nF '"BrickComparisonFact.required_return_shape_evidence",' brick_protocol/link/gate.py`
  - 현재 위치(live 2026-06-11, 재파생 재실행): `brick_protocol/link/gate.py:176`  (matches: 1)
  - 근거:
    ```
    required_public_facts.extend(( "BrickComparisonFact.required_return_shape_evidence", "BrickComparisonFact.comparison_evidence", )) ... if ref == "link-gate:human": required_public_facts.append("Link.route_decision_basis.human_review_refs")
    ```

- **Runtime GateFact ties sufficiency to one concrete brick-comparison coordinate (checked_public_fact == evidence_reference)** — _anchor_
  - 묶는 것: The computed Link movement-gate GateFact for a specific run step (the gate verdict that authorizes/blocks the forward handoff).
  - 가리키는 것: The exact BrickComparisonFact for that step, addressed as brick-comparison:<building_id>:<step_ref>, passed as BOTH checked_public_fact and evidence_reference into evaluate_declared_movement_gate. The required/missing return fields are pulled from brick_comparison.required_return_fields()/missing_return_fields() (run.py:982-997). Verdict is computed by the Link rule, never hardcoded.
  - symbol: `brick_protocol/support/operator/run.py :: _declared_movement_gate_fact`
  - 토큰: `checked = f"brick-comparison:{prepared.building_id}:{prepared.step_rows.step_ref}"`
  - 재파생: `grep -nF 'checked = f"brick-comparison:{prepared.building_id}:{prepared.step_rows.step_ref}"' brick_protocol/support/operator/run.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/operator/run.py:981`  (matches: 1)
  - 근거:
    ```
    checked = f"brick-comparison:{prepared.building_id}:{prepared.step_rows.step_ref}" / return evaluate_declared_movement_gate( ... checked_public_fact=checked, evidence_reference=checked, )
    ```

- **Reroute-adoption record carries source_transition_concern_ref (the Agent proposal that justified the reroute)** — _anchor_
  - 묶는 것: A runtime reroute decision (an ADOPTED reroute-landing) recorded as a nested dynamic-walker evidence record.
  - 가리키는 것: source_transition_concern_ref (the non-binding Agent transition_concern that proposed the reroute), transition_concern_binding=false, source_step_ref/source_brick_ref (where the proposal arose), adopted_by (the gate authority ref that adopted it), and target_brick/target_step_ref (the destination). Built by ITERATING the contract field-spec (reroute_adoption_field_specs) so a required grounding field cannot be silently dropped (walker_evidence.py:71-125).
  - symbol: `brick_protocol/support/recording/walker_evidence.py :: build_reroute_adoption_record`
  - 토큰: `Emit an ADOPTED reroute-landing record from the contract field-spec.`
  - 재파생: `grep -nF 'Emit an ADOPTED reroute-landing record from the contract field-spec.' brick_protocol/support/recording/walker_evidence.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/recording/walker_evidence.py:94`  (matches: 1)
  - 근거:
    ```
    "source_step_ref": source_step_ref, "source_brick_ref": source_brick_ref, "source_transition_concern_ref": source_transition_concern_ref, "transition_concern_binding": transition_concern_binding, "adopted_by": adopted_by,
    ```

- **building-map link_edge contract declares movement_fact_ref + transition_fact_ref as required grounding pointers** — _anchor_
  - 묶는 것: The on-disk building-map link_edge row (the recorded transition between two Brick instances).
  - 가리키는 것: movement_fact_ref (the MovementFact that decided this edge) and transition_fact_ref (the TransitionFact) are REQUIRED fields of every link_edge row, alongside source_brick_instance_ref / target_brick_instance_ref / input_public_fact_refs. This single canonical contract (contracts.py:365-375) is the one home the emitter builds from and the checker derives from, so the edge always points back to its movement/transition justification.
  - symbol: `brick_protocol/support/recording/contracts.py :: BUILDING_MAP_LINK_EDGE_REQUIRED_FIELDS`
  - 토큰: `"movement_fact_ref",`
  - 재파생: `grep -nF '"movement_fact_ref",' brick_protocol/support/recording/contracts.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/recording/contracts.py:372`  (matches: 1)
  - 근거:
    ```
    "source_brick_instance_ref", "target_brick_instance_ref", "input_public_fact_refs", "public_fact_refs", "movement_fact_ref", "transition_fact_ref",
    ```

- **link_edge emitter wires movement_fact_ref and input_public_fact_refs to the step's concrete fact coordinates** — _anchor_
  - 묶는 것: The emitted building-map link_edge for one walked step (the recorded forward transition).
  - 가리키는 것: movement_ref = _step_fact_ref("movement-fact", index, step_ref) (evidence_assembly.py:1393); the edge's input_public_fact_refs/public_fact_refs are set to [agent_fact_ref, comparison_ref, movement_ref] (lines 1460-1462), so the edge traces back to the AgentFact, the BrickComparisonFact (brick-comparison:...), and the MovementFact that justified it. comparison_ref here uses the same brick-comparison:<id>:<step_ref> scheme as the run.py GateFact evidence_reference.
  - symbol: `brick_protocol/support/operator/evidence_assembly.py :: (building-map assembly) build_link_edge_row call`
  - 토큰: `movement_fact_ref=movement_ref,`
  - 재파생: `grep -nF 'movement_fact_ref=movement_ref,' brick_protocol/support/recording/building_map_emit.py`
  - 현재 위치(live 2026-06-11, 재파생 재실행): `brick_protocol/support/recording/building_map_emit.py:183`  (matches: 1)
  - 근거:
    ```
    input_public_fact_refs=[agent_fact_ref, comparison_ref, movement_ref], public_fact_refs=[agent_fact_ref, comparison_ref, movement_ref], movement_fact_ref=movement_ref, transition_fact_ref=_step_fact_ref("transition-fact", index, step_ref),
    ```

- **HOLD record grounds a non-adopted reroute to the Agent concern_ref and marks disposition_required** — _anchor_
  - 묶는 것: A HOLD (a reroute that was NOT adopted because the target had no Link-assigned budget, budget was exhausted, or a human/coo gate paused), recorded so a caller/COO can later disposition it.
  - 가리키는 것: The Agent transition_concern's concern_ref (the proposal that triggered the hold), pending_target_ref (the would-be reroute target), hold_reason (e.g. target_node_budget_exhausted / human_or_coo_gate_pause / target_node_has_no_link_assigned_budget set at walker_kernel.py:1380/1417/1451), node_budget + attempt_number (the budget evidence), and disposition_required=True. Emitted via the contract-derived build_hold_record (called from _build_hold, walker_hold.py:42-92).
  - symbol: `brick_protocol/support/operator/walker_hold.py :: _build_hold`
  - 토큰: `source_transition_concern_ref=_optional_text_value(concern.get("concern_ref")) or "",`
  - 재파생: `grep -nF 'source_transition_concern_ref=_optional_text_value(concern.get("concern_ref")) or "",' brick_protocol/support/operator/walker_hold.py`
  - 현재 위치(live 2026-06-10, repointed after the dynamic_walker → walker_* decomposition): `brick_protocol/support/operator/walker_hold.py:80`  (matches: 1)
  - 근거:
    ```
    source_transition_concern_ref=_optional_text_value(concern.get("concern_ref")) or "", transition_concern_binding=False, immediate_target_ref=target_brick, target_brick=target_brick, pending_target_ref=target_brick,
    ```

- **caller-supplied MovementFact preserves gatefact_reference + transition_history_reference grounding pointers** — _anchor_
  - 묶는 것: The MovementFact (and paired TransitionFact) built from a caller-supplied plan packet's caller_supplied_link_facts.movement_fact.
  - 가리키는 것: The caller's declared gatefact_reference (the GateFact verdict justifying the move) and transition_history_reference, plus handoff_target_fact, threaded through make_movement_fact so the recorded movement keeps its pointer back to the gate/transition evidence rather than losing it at the plan boundary (plan_validation.py:363-383).
  - symbol: `brick_protocol/support/operator/plan_validation.py :: _caller_link_facts`
  - 토큰: `gatefact_reference=_optional_text_or_none(movement_fact_data.get("gatefact_reference")),`
  - 재파생: `grep -nF 'gatefact_reference=_optional_text_or_none(movement_fact_data.get("gatefact_reference")),' brick_protocol/support/operator/plan_validation.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/operator/plan_validation.py:369`  (matches: 1)
  - 근거:
    ```
    handoff_target_fact=_optional_text_or_none( movement_fact_data.get("handoff_target_fact") ), gatefact_reference=_optional_text_or_none(movement_fact_data.get("gatefact_reference")), transition_history_reference=_optional_text_or_none( movement_fact_data.get("transition_history_reference") ),
    ```

- **native-dispatch close grounds MovementFact.handoff_target_fact to the next Brick instance and computes the gate verdict** — _anchor_
  - 묶는 것: The MovementFact + TransitionFact recorded when closing a native-dispatch Brick (the movement decision for that Building step).
  - 가리키는 것: target_fact = f"brick:{prepared.next_brick_instance_ref}" (building_operation.py:2950) — the next Brick instance the movement hands off to — set as MovementFact.handoff_target_fact and TransitionFact.target_fact. The paired movement-gate GateFact is computed by evaluate_declared_movement_gate via complete_agent_run_from_prepared and is required to be non-None (building_operation.py:2904, 2951-2976); the gate verdict is computed by the Link rule, never a hardcoded pass.
  - symbol: `brick_protocol/support/operator/building_operation.py :: close_native_dispatch_brick`
  - 토큰: `handoff_target_fact=target_fact,`
  - 재파생: `grep -nF 'handoff_target_fact=target_fact,' brick_protocol/support/operator/native_dispatch.py`
  - 현재 위치(live 2026-06-11, 재파생 재실행): `brick_protocol/support/operator/native_dispatch.py:722`  (matches: 1)
  - 근거:
    ```
    target_fact = f"brick:{prepared.next_brick_instance_ref}" / link_fact = make_movement_fact( movement_text, reason=... , handoff_target_fact=target_fact, )
    ```

## 6. proof_limits / not_proven

- **Central frontier not_proven merge (plan + all steps + failed prep + observation)** — _derive_
  - 묶는 것: The not_proven list written into the agent-incomplete (adapter-error) Building lifecycle frontier packet
  - 가리키는 것: Four upstream sources merged in order: the Building Plan's declared plan.get('not_proven'), every completed step result's result.not_proven, the failed step's failed_preparation.not_proven, and the frontier observation.not_proven
  - symbol: `_adapter_error_frontier_lifecycle_packet (brick_protocol/support/operator/evidence_assembly.py)`
  - 토큰: `failed_preparation.not_proven,`
  - 재파생: `grep -nF 'failed_preparation.not_proven,' brick_protocol/support/recording/adapter_error_frontier.py`
  - 현재 위치(live 2026-06-11, 재파생 재실행): `brick_protocol/support/recording/adapter_error_frontier.py:290`  (matches: 1)
  - 근거:
    ```
        not_proven = _merge_texts(
            plan.get("not_proven"),
    ```

- **Accumulated multi-step Building result not_proven/proof_limits roll-up** — _derive_
  - 묶는 것: The not_proven (and adjacent proof_limits at line 388) on the BuildingPlanSupportResult returned for a fully-run multi-step Building
  - 가리키는 것: The lifecycle packet's packet.get('not_proven') unioned with each per-step result r.not_proven across step_results; proof_limits unions checked_proof_limits with each r.proof_limits
  - symbol: `run_building_plan (brick_protocol/support/operator/run.py)`
  - 토큰: `not_proven=_merge_texts(packet.get("not_proven"), *(r.not_proven for r in step_results)),`
  - 재파생: `grep -nF 'not_proven=_merge_texts(packet.get("not_proven")' brick_protocol/support/operator/run.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/operator/run.py:389`  (matches: 1)
  - 근거:
    ```
            proof_limits=_merge_texts(checked_proof_limits, *(r.proof_limits for r in step_results)),
            not_proven=_merge_texts(packet.get("not_proven"), *(r.not_proven for r in step_results)),
    ```

- **Authority-claim normalization: bare authority words rewritten to explicit 'not proven:' anchors** — _derive_
  - 묶는 것: The final not_proven strings placed into evidence/raw manifests (called e.g. at evidence_assembly.py:461 and :798) — the explicit over-claim guard
  - 가리키는 것: Each merged not_proven value; if it lowercases to one of {source truth, success judgment, quality judgment, movement authority} it is rewritten to 'not proven: <value>', otherwise passed through unchanged — turning a bare authority word into an explicit non-claim
  - symbol: `_manifest_not_proven (brick_protocol/support/operator/evidence_assembly.py)`
  - 토큰: `if lowered in exact_authority_claims:`
  - 재파생: `grep -nF 'if lowered in exact_authority_claims:' brick_protocol/support/recording/claims_common.py`
  - 현재 위치(live 2026-06-11, 재파생 재실행): `brick_protocol/support/recording/claims_common.py:67`  (matches: 1)
  - 근거:
    ```
            if lowered in exact_authority_claims:
                adjusted.append(f"not proven: {value}")
    ```

- **Dynamic-walker HOLD/reroute not_proven anchor source constant** — _anchor_
  - 묶는 것: The reroute/HOLD-specific not_proven anchors that get merged into the dynamic walker's BuildingPlanSupportResult.not_proven at walker_kernel.py:1251/1568/1658 (+ _merge_texts at 1684/1690)
  - 가리키는 것: The walker's own hardcoded boundary of what walking a gate-adopted agent-proposed reroute does NOT prove: reroute semantic correctness, parallel runtime execution, scheduler/queue/retry behavior, and caller/COO disposition after a HOLD
  - symbol: `NOT_PROVEN module constant (brick_protocol/support/operator/walker_common.py)`
  - 토큰: `semantic correctness of the agent-proposed reroute`
  - 재파생: `grep -nF 'semantic correctness of the agent-proposed reroute' brick_protocol/support/operator/walker_common.py`
  - 현재 위치(live 2026-06-10, repointed after the dynamic_walker → walker_* decomposition): `brick_protocol/support/operator/walker_common.py:28`  (matches: 1)
  - 근거:
    ```
    NOT_PROVEN: tuple[str, ...] = (
        "semantic correctness of the agent-proposed reroute",
    ```

- **Axis-specific transition_concern not_proven derivation** — _derive_
  - 묶는 것: The not_proven list on a written transition_concern step-output record (Link-axis Agent concern evidence)
  - 가리키는 것: _merge_texts of the Agent observation.not_proven with three fixed Link-axis non-claims: 'transition concern semantic correctness', 'Link disposition correctness', 'automatic repair/replay execution' — anchoring that the recorded concern proves none of these
  - symbol: `write_step_outputs (brick_protocol/support/recording/step_outputs.py)`
  - 토큰: `transition concern semantic correctness`
  - 재파생: `grep -nF 'transition concern semantic correctness' brick_protocol/support/recording/step_outputs.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/recording/step_outputs.py:160`  (matches: 1)
  - 근거:
    ```
                    _merge_texts(
                        observation.not_proven,
    ```

- **Canonical default proof_limits source-of-truth tuple** — _anchor_
  - 묶는 것: The baseline proof_limits anchors ('support evidence only', 'not source truth', 'not success/quality judgment', 'not Movement authority') consumed by building_evidence.py:32 (DEFAULT_PROOF_LIMITS) for packets that declare none
  - 가리키는 것: A hardcoded conservative default tuple — the source coordinate for the 'this is support evidence only' guarantee when no caller-supplied proof_limits exist
  - symbol: `DEFAULT_PROOF_LIMITS module constant (brick_protocol/support/recording/capture.py)`
  - 토큰: `DEFAULT_PROOF_LIMITS = (`
  - 재파생: `grep -nF 'DEFAULT_PROOF_LIMITS = (' brick_protocol/support/recording/capture.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/recording/capture.py:118`  (matches: 1)
  - 근거:
    ```
    DEFAULT_PROOF_LIMITS = (
        "support evidence only",
    ```

- **proof_limits normalizer with conservative default fallback** — _derive_
  - 묶는 것: The normalized proof_limits tuple stored on operator contract dataclasses (e.g. contracts.py:162 __post_init__ runs every proof_limits field through this)
  - 가리키는 것: Caller-supplied values (validated non-blank text), falling back to module _DEFAULT_PROOF_LIMITS when None or empty — guaranteeing every record carries at least the conservative proof-limit anchors and never an empty/unbounded claim
  - symbol: `_proof_limits_tuple (brick_protocol/support/operator/primitives.py)`
  - 토큰: `return tuple(facts) or _DEFAULT_PROOF_LIMITS`
  - 재파생: `grep -nF 'return tuple(facts) or _DEFAULT_PROOF_LIMITS' brick_protocol/support/operator/primitives.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/operator/primitives.py:531`  (matches: 1)
  - 근거:
    ```
        if values is None:
            return _DEFAULT_PROOF_LIMITS
    ```

## 7. recording 계약 — 저장 말고 파생

- **Contract = single canonical evidence-shape source (the search_for() equivalent)** — _anchor_
  - 묶는 것: The meta-grounding guarantee itself: that all recording evidence shape is DERIVED from one source so it cannot silently drift (the PyMuPDF search_for() analogue for agent-work evidence).
  - 가리키는 것: This file (contracts.py) as the ONE home of the shape; the emitter builds FROM the field-spec and the ζ6 checker DERIVES the expected shape FROM the same spec. Quote: '...the evidence shape can NO LONGER drift silently -- only a change to THIS contract moves the shape, and the checker rejects an emitter that drops a required field or adds an undeclared one.'
  - symbol: `module docstring block in brick_protocol/support/recording/contracts.py (DYNAMIC-WALKER EVIDENCE-SHAPE CONTRACT section)`
  - 토큰: `only a change to`
  - 재파생: `grep -nF 'only a change to' brick_protocol/support/recording/contracts.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/recording/contracts.py:88`  (matches: 1)
  - 근거:
    ```
    # changes, the evidence shape can NO LONGER drift silently -- only a change to
    # THIS contract moves the shape, and the checker rejects an emitter that drops a
    ```

- **Per-axis field-spec deriver — capture-event shape computed from declared header+payload, not stored** — _derive_
  - 묶는 것: The ordered field-spec (EvidenceFieldSpec tuple) that fixes the on-disk SHAPE + key order of each of the 8 lifecycle capture events; the emitter supplies only values.
  - 가리키는 것: The declared constants CAPTURE_EVENT_HEADER_FIELDS + CAPTURE_EVENT_PAYLOAD_FIELDS[event_type] in the same file — the canonical key order is computed by concatenation, never hand-written per record. Quote: 'names = CAPTURE_EVENT_HEADER_FIELDS + CAPTURE_EVENT_PAYLOAD_FIELDS[event_type]'.
  - symbol: `capture_event_field_specs`
  - 토큰: `def capture_event_field_specs`
  - 재파생: `grep -nF 'def capture_event_field_specs' brick_protocol/support/recording/contracts.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/recording/contracts.py:318`  (matches: 1)
  - 근거:
    ```
    def capture_event_field_specs(event_type: str) -> tuple[EvidenceFieldSpec, ...]:
        ...
    ```

- **Axis attribution declared ONCE in contract, with an explicit anti-tautology warning** — _anchor_
  - 묶는 것: The axis_attribution FACT label per capture event_type (building_opened->'Support residue', brick_*->'Brick', agent_*->'Agent', link_*->'Link') — the value the emitter stamps onto each event.
  - 가리키는 것: Each axis backbone (Brick/Agent/Link) as the source of the label; and a deliberate instruction that the checker must NOT verify by reading this dict (which would be circular) but via an independent event_type-prefix rule. Quote: 'do NOT verify the emitted value by reading THIS dict (that is circular).'
  - symbol: `CAPTURE_EVENT_AXIS_ATTRIBUTION dict`
  - 토큰: `Declared axis_attribution per event_type`
  - 재파생: `grep -nF 'Declared axis_attribution per event_type' brick_protocol/support/recording/contracts.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/recording/contracts.py:255`  (matches: 1)
  - 근거:
    ```
    # Declared axis_attribution per event_type. NOTE for the ζ6 checker author: do NOT
    # verify the emitted value by reading THIS dict (that is circular). The checker has
    ```

- **Frontier observation proof-limit literals fixed in contract (provenance disclaimer attached at source)** — _proof-limit_
  - 묶는 것: The fixed proof-limit strings attached to every agent-incomplete frontier observation (where a Building stopped after Agent receipt but before the returned AgentFact).
  - 가리키는 것: The contract as the single source of the disclaimer set ('not source truth', 'not success judgment', 'not quality judgment', 'not Movement authority'); the emitter copies FRONTIER_OBSERVATION_PROOF_LIMITS verbatim rather than re-stating limits inline. Bounds what the evidence may be read to prove.
  - symbol: `FRONTIER_OBSERVATION_PROOF_LIMITS`
  - 토큰: `graph support projection only`
  - 재파생: `grep -nF 'graph support projection only' brick_protocol/support/recording/contracts.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/recording/contracts.py:412`  (matches: 1)
  - 근거:
    ```
    FRONTIER_OBSERVATION_PROOF_LIMITS: tuple[str, ...] = (
        "graph support projection only",
    ```

- **Emitter iterates the contract spec — drift-proof builder (operator evidence: capture events + building-map rows + frontier)** — _pointer_
  - 묶는 것: Every accumulated-Building operator evidence record (the 8 capture events, brick_instance/agent_binding/link_edge rows, frontier observation) — built by walking the contract field-spec in order, not by hand-writing dict literals.
  - 가리키는 것: The contract specs (capture_event_field_specs / building_map_*_specs / frontier_observation_specs imported at the top of this file). A missing required field raises ('contract-required field ... was not supplied'); an extra key raises here — so the emitted record is provably tied to the contract source and cannot drift. Replaces the formerly-inline literals in brick_protocol/support/operator/evidence_assembly.py.
  - symbol: `operator_evidence._build_from_specs`
  - 토큰: `values carry undeclared field(s) not in the`
  - 재파생: `grep -nF 'values carry undeclared field(s) not in the' brick_protocol/support/recording/operator_evidence.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/recording/operator_evidence.py:64`  (matches: 1)
  - 근거:
    ```
            raise ValueError(
                f"{record_label}: values carry undeclared field(s) not in the "
    ```

- **Second emitter (dynamic-walker) iterates the SAME contract — reroute-adoption / HOLD / structured-field records** — _pointer_
  - 묶는 것: The dynamic-walker support evidence records — reroute-adoption record, HOLD record, and structured field-set observation — built by iterating reroute_adoption_field_specs() / hold_record_field_specs() / structured_field_observation_specs().
  - 가리키는 것: The same contracts.py field-specs (imported at walker_evidence.py:23-33). build_structured_field_observation (walker_evidence.py:191) additionally computes the missing_from_observed / demanded_beyond_brick deltas MECHANICALLY (set difference), not by judgment — so the deltas trace to the input field sets, not an opinion. The dynamic walker calls these instead of inlining literals.
  - symbol: `walker_evidence._build_from_specs`
  - 토큰: `values carry undeclared field(s) not in the`
  - 재파생: `grep -nF 'values carry undeclared field(s) not in the' brick_protocol/support/recording/walker_evidence.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/recording/walker_evidence.py:54`  (matches: 1)
  - 근거:
    ```
            raise ValueError(
                f"{record_label}: values carry undeclared field(s) not in the "
    ```

- **ζ6 oracle re-derives the shape from the SAME contract and rejects emitter drift (DROPPED / ADDED field)** — _proof-limit_
  - 묶는 것: The verification verdict that every record the REAL walker/run-surface produced (over adapter:local fixtures, no providers) matches the contract field-spec exactly — no dropped required field, no undeclared field.
  - 가리키는 것: The contract's *_REQUIRED_FIELDS / *_OPTIONAL_FIELDS constants imported from contracts.py (check_*.py:137-144, 287-295). The checker compares observed record keys against the contract-derived expected key set, closing the loop: contract -> emitter -> on-disk record -> checker -> contract. This is what makes the grounding non-bypassable.
  - symbol: `check_recording_checker_derived_contract._check_record_against_contract`
  - 토큰: `emitter ADDED undeclared field(s) not in contract`
  - 재파생: `grep -nF 'emitter ADDED undeclared field(s) not in contract' brick_protocol/support/checkers/check_recording_checker_derived_contract.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/checkers/check_recording_checker_derived_contract.py:125`  (matches: 1)
  - 근거:
    ```
        undeclared = sorted(observed_keys - set(required) - set(optional))
        if undeclared:
    ```

- **Anti-tautology independent axis rule — checker derives expected axis from event_type NAME, not the contract dict** — _proof-limit_
  - 묶는 것: The expected axis_attribution for each capture event, derived INDEPENDENTLY from the event_type prefix (brick_->Brick, agent_->Agent, link_->Link, else pinned 'Support residue').
  - 가리키는 것: An independent source (the event_type name) rather than the emitter's source (CAPTURE_EVENT_AXIS_ATTRIBUTION dict in contracts.py). This guards the one place where contract+emitter share a value: if the contract dict were corrupted (e.g. link_movement->'Brick'), the emitted value would diverge from this name-derived expectation and be REJECTED — so the axis grounding cannot collapse into a circular check. Pins '_PINNED_NON_AXIS_ATTRIBUTION = "Support residue"'.
  - symbol: `check_recording_checker_derived_contract._independent_expected_axis`
  - 토큰: `def _independent_expected_axis`
  - 재파생: `grep -nF 'def _independent_expected_axis' brick_protocol/support/checkers/check_recording_checker_derived_contract.py`
  - 현재 위치(live 2026-05-30): `brick_protocol/support/checkers/check_recording_checker_derived_contract.py:82`  (matches: 1)
  - 근거:
    ```
    def _independent_expected_axis(event_type: str) -> str:
        ...
    ```

## 8. evidence_assembly — 공유 writer

- **plan_snapshot content-hash anchor** — _anchor_
  - 묶는 것: The Building evidence root's recorded copy of the declared Building Plan that was walked (plan_ref + plan_hash + plan_rows_copy embedded in every lifecycle/error evidence_manifest)
  - 가리키는 것: The Brick-owned source plan under brick_protocol/brick/building_plans/: the sha256 (plan_hash) is taken over the exact canonical sorted-key JSON string (plan_rows_copy), so a reviewer can re-derive the hash from the recorded copy and confirm exactly which declared plan produced the evidence
  - symbol: `_plan_snapshot`
  - 토큰: `plan_hash_basis`
  - 재파생: `grep -nF '"plan_hash_basis": "canonical sorted-key JSON of the declared plan body",' brick_protocol/support/recording/declaration_packets.py`
  - 현재 위치(live 2026-06-11, 재파생 재실행): `brick_protocol/support/recording/declaration_packets.py:973`  (matches: 1)
  - 근거:
    ```
    plan_hash = hashlib.sha256(plan_rows_copy.encode("utf-8")).hexdigest()
        return {
    ```

- **step-output observation ref binding** — _pointer_
  - 묶는 것: Each executed step's Agent returned value (result.adapter_result.returned_value) written into the per-step StepOutputObservation
  - 가리키는 것: Deterministic source coordinates derived from (kind,index,step_ref): received_work_ref=brick-work:NN:slug, returned_fact_ref=agent-fact:NN:slug, raw_ref=raw:agent:NN -- so the returned value is traceable back to the Brick work row, the closed AgentFact, and the raw:agent jsonl stream
  - symbol: `_step_output_observations`
  - 토큰: `received_work_ref=_step_fact_ref("brick-work", index, step_ref)`
  - 재파생: `grep -nF 'received_work_ref=_step_fact_ref("brick-work", index, step_ref)' brick_protocol/support/recording/claims_common.py`
  - 현재 위치(live 2026-06-11, 재파생 재실행): `brick_protocol/support/recording/claims_common.py:90`  (matches: 1)
  - 근거:
    ```
    returned=result.adapter_result.returned_value,
                    received_work_ref=_step_fact_ref("brick-work", index, step_ref),
    ```

- **central claim-fact ref->raw binding** — _anchor_
  - 묶는 것: Every per-axis claim-trace record (Brick work, brick-comparison, AgentFact, Link transfer/carry/sufficiency/movement, and absence placeholders) produced for the claim_trace files
  - 가리키는 것: Each claim is bound to a stable fact_ref coordinate plus the raw_refs list (e.g. raw:brick:NN, raw:agent:NN, raw:link:NN) that produced it, with proof_limits and not_proven attached -- the single helper that ties a claimed fact to its raw-stream source coordinate
  - symbol: `_claim_fact`
  - 토큰: `"fact_ref": fact_ref,`
  - 재파생: `grep -nF '"fact_ref": fact_ref,' brick_protocol/support/recording/claims_common.py`
  - 현재 위치(live 2026-06-11, 재파생 재실행): `brick_protocol/support/recording/claims_common.py:49`  (matches: 1)
  - 근거:
    ```
    return {
            "axis": axis,
    ```

- **building-map link edge fact anchoring** — _pointer_
  - 묶는 것: Each Link edge row in the accumulated building-map (work/building-map.json) graph projection, one per walked step
  - 가리키는 것: Per-step fact coordinates built via _step_fact_ref: agent_fact_ref (agent-fact:NN:slug), comparison_ref (brick-comparison:NN:slug), movement_ref (movement-fact:NN:slug) plus transition_fact_ref -- so each map edge points back to the exact AgentFact, comparison, and Movement claim records for that step
  - symbol: `_accumulated_building_map_packet`
  - 토큰: `input_public_fact_refs=[agent_fact_ref, comparison_ref, movement_ref]`
  - 재파생: `grep -nF 'input_public_fact_refs=[agent_fact_ref, comparison_ref, movement_ref],' brick_protocol/support/recording/building_map_emit.py`
  - 현재 위치(live 2026-06-11, 재파생 재실행): `brick_protocol/support/recording/building_map_emit.py:181`  (matches: 1)
  - 근거:
    ```
    input_public_fact_refs=[agent_fact_ref, comparison_ref, movement_ref],
                public_fact_refs=[agent_fact_ref, comparison_ref, movement_ref],
    ```

- **raw manifest path->source attribution** — _anchor_
  - 묶는 것: The raw-manifest (raw/raw-manifest.json) entry for the on-disk raw/brick-work.jsonl stream (and parallel agent-return.jsonl / link.jsonl entries)
  - 가리키는 것: Each on-disk raw file path is tied to its producing source string (brick_protocol/support/operator/run.py run_building_plan), its axis_owner (Brick/Agent/Link), and the per-step raw_refs (raw:brick:NN ...) it contains -- so a reader can trace any raw stream back to who wrote it and which step refs it covers
  - symbol: `_accumulated_raw_manifest`
  - 토큰: `"source": "brick_protocol/support/operator/run.py run_building_plan declared Brick rows",`
  - 재파생: `grep -nF '"source": "brick_protocol/support/operator/run.py run_building_plan declared Brick rows",' brick_protocol/support/recording/lifecycle_emit.py`
  - 현재 위치(live 2026-06-11, 재파생 재실행): `brick_protocol/support/recording/lifecycle_emit.py:189`  (matches: 1)
  - 근거:
    ```
    "path": "raw/brick-work.jsonl",
                    "source": "brick_protocol/support/operator/run.py run_building_plan declared Brick rows",
    ```

- **movement claim source attribution** — _derive_
  - 묶는 것: The per-step Link Movement claim fact (movement-fact:NN:slug) recorded in evidence/claim_trace/link/movement_trace.json
  - 가리키는 것: The movement value is taken from result.completion.crossing_record.link_fact.movement and explicitly attributed to the caller-declared Building Plan Link row (movement_source), with public_fact_refs (from _link_movement_public_fact_refs) and target_boundary_ref pointing at the supporting facts -- support records, does not choose, the Movement
  - symbol: `_link_movement_claim_facts`
  - 토큰: `"movement_source": "caller-declared Building Plan Link row",`
  - 재파생: `grep -nF '"movement_source": "caller-declared Building Plan Link row",' brick_protocol/support/recording/claims_link.py`
  - 현재 위치(live 2026-06-11, 재파생 재실행): `brick_protocol/support/recording/claims_link.py:152`  (matches: 2; also :607)
  - 근거:
    ```
    fact_body = {
                "movement": movement,
    ```

- **movement supporting-evidence ref bundle** — _derive_
  - 묶는 것: The public_fact_refs list backing each Link Movement claim (the supporting-evidence coordinates that justify the recorded Movement)
  - 가리키는 것: Assembles the supporting ref bundle from per-step coordinates: agent-fact:NN:slug, brick-comparison:NN:slug, the gate sufficiency-fact refs (transfer/carry/movement stages), plus any route_reason_refs / transition authoring basis refs from the declared Link row -- ties the Movement back to the AgentFact, comparison, and gate facts that support it
  - symbol: `_link_movement_public_fact_refs`
  - 토큰: `refs.extend(_gate_claim_fact_refs(result.completion.crossing_record, index, step_ref))`
  - 재파생: `grep -nF 'refs.extend(_gate_claim_fact_refs(result.completion.crossing_record, index, step_ref))' brick_protocol/support/recording/claims_link.py`
  - 현재 위치(live 2026-06-11, 재파생 재실행): `brick_protocol/support/recording/claims_link.py:573`  (matches: 1)
  - 근거:
    ```
    refs = [
            _step_fact_ref("agent-fact", index, step_ref),
    ```

- **brick comparison observation anchor** — _derive_
  - 묶는 것: The per-step Brick comparison claim fact (brick-comparison:NN:slug) recording the observed_match_kind + comparison_evidence
  - 가리키는 것: Bound to raw:brick:NN and raw:agent:NN raw refs, carries observed_match_kind / comparison_evidence / required_return_shape_evidence taken from result.completion.brick_comparison, and is explicitly labeled 'contract observation only; not success judgment' -- ties the comparison observation to both the Brick work row and the Agent return raw streams without judging success
  - symbol: `_brick_claim_facts`
  - 토큰: `fact_ref=_step_fact_ref("brick-comparison", index, prepared.step_rows.step_ref),`
  - 재파생: `grep -nF 'fact_ref=_step_fact_ref("brick-comparison", index, prepared.step_rows.step_ref),' brick_protocol/support/recording/claims_brick.py`
  - 현재 위치(live 2026-06-11, 재파생 재실행): `brick_protocol/support/recording/claims_brick.py:76`  (matches: 1)
  - 근거:
    ```
    fact_ref=_step_fact_ref("brick-comparison", index, prepared.step_rows.step_ref),
                    raw_refs=[_raw_ref("brick", index), _raw_ref("agent", index)],
    ```


## 9. 프로젝트 그릇 (PROJECT-0, 0611 추가)

- **buildings_root_for — project_ref → 증거 동네 단일 파생 seam** — _anchor_
  - 묶는 것: 빌딩 증거가 쌓이는 물리 루트(`project/<id>/buildings`)와 선언된 프로젝트 그릇(project_ref)의 결합. 경로가 1차 소속 사실이고, ref-less 기본 루트(DEFAULT_BUILDINGS_ROOT)도 이 seam을 통해 project:brick-protocol(1호 그릇)에서 파생된다.
  - 가리키는 것: 선언된 `project:<id>` ref에서 buildings 루트를 파생하는 유일한 함수. slug 법([a-z0-9][-_a-z0-9]*, is_project_id_slug)으로 malformed ref는 ValueError로 거부하고, S3 intake가 이 seam을 소비해 빌딩을 선언된 동네로 보낸다. 병렬 "project/brick-protocol" 경로 join 리터럴은 어디에도 남아있지 않다(check_building_root_anchor가 pin).
  - symbol: `brick_protocol/support/recording/capture.py :: buildings_root_for`
  - 토큰: `return REPO_ROOT / "project" / project_id / "buildings"`
  - 재파생: `grep -nF 'return REPO_ROOT / "project" / project_id / "buildings"' brick_protocol/support/recording/capture.py`
  - 현재 위치(live 2026-06-11): `brick_protocol/support/recording/capture.py:69`  (matches: 1)
  - 근거:
    ```
    def buildings_root_for(project_ref: str) -> Path:
        """PROJECT-0 S1-D: THE single derivation seam from a project_ref to its
        buildings root (one function, one home — pinned by check_building_root_anchor).
    ```
