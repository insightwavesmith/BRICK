# ACTIVE GOAL — 순수 개발 큐 구현 완료 (≤3KB)

| | |
|---|---|
| **Status** | **ACTIVE** · 2026-07-09 |
| **Authority** | BRICK COO · pure-dev |
| **Proof** | support only · not success/quality/Movement |

## 한 줄
```text
D1→D4 를 공식 Building 구현 land 로 development-complete.
문서/결정/dogfood-only DONE 무효. D5=OUT_OF_SCOPE.
```

## Board

| # | Item | Disp | Pointer |
|---|---|---|---|
| D1=R5 | Route V2 beyond A min slice | **PENDING** | — |
| D2=R6 | vessel physical split | **PENDING** | — |
| D3=R7 | token-forgery harden | **PENDING** | — |
| D4=R4 | G2-c ship-copy | **PENDING** | — |
| D5=R11 | Deku | **OUT_OF_SCOPE** | not opened |

## Exit (each DONE)
```text
graph-decl build complete + write land + probe + building_id+sha
NOT doc/decision/dogfood-only/live-only
```

## Order
```text
D1 → D2 → D3 → D4
```

## Route
```text
brick build --graph-decl <decl> --forward
brick resume --decl <resume.json>
```

## COO
```text
ACTIVE pure-dev. NOT residual document DONE.
```
