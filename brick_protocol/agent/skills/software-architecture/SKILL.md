---
name: software-architecture
description: Use when slicing implementation by module boundary, dependency order, write scope, and integration risk — and when implementing an admitted change with existing modules and checker-first boundaries (absorbed scoped-implementation).
---

# Software Architecture

Prepare implementation handoffs:

```text
worker_assignments
module_boundaries
write_scope_notes
dependency_order
integration_risks
verification_requests
```

Leads coordinate. Workers implement only when the Building Plan and Brick
write_scope assign that work.

## Scoped implementation (구 scoped-implementation)

구현할 때: governing checker/fixture를 먼저 읽는다. 새 표면을 더하기 전에 기존 모듈과
support 헬퍼를 재사용한다. 편집은 admitted 파일에 한정하고, 무관한 dirty 작업은 건드리지
않는다.
