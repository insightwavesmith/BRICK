# G0 Face closure

**status:** EXIT (measured)

**artifacts:**
- deku_core/{catalog,parse,session,trajectory,no_blank,mutex}.py
- deku_server.py rewired
- tests/test_g0_face.py

**evidence:** unittest OK; curl models/healthz/hello under implementer scratch.

**remaining_not_proven:** full Nemotron-loaded paid-worker hello 50× (mock path proven); MPS load not required for G0 schema gates when DEKU_FORCE_MOCK=1.
