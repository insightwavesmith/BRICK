# Repository Invite Issuance

This is support documentation for customer repository access. It is not source
truth, not a success judgment, not a quality judgment, and not Movement
authority.

## Scope

Customer distribution uses this repository invitation path. There is no separate
hosted installer channel in the current operating packet. The issuer is Smith.

The invite gives repository access only. It does not store credentials in this
repository, prove customer environment readiness, prove provider authentication,
or approve any Building outcome.

## Procedure

1. Smith identifies the customer's GitHub org/user that will receive access.
2. Smith sends the repository invitation through GitHub repository access
   settings.
3. The customer accepts the GitHub invitation with their own account.
4. The customer clones the invited clean distribution repository with their own
   GitHub authentication. The owner is always the deploy repository owner they
   were invited to (for example, `{OWNER}/BRICK-dist`), never the customer's own
   account; a non-invited or wrong-owner clone returns a not-found error:
   `gh repo clone {OWNER}/BRICK-dist ~/BRICK`.
5. The customer runs `sh ~/BRICK/support/onboarding/install.sh`.
6. The installer performs its local installation check and prints
   `5) 설치 점검 완료` only after that check exits cleanly.
7. The customer can run `brick doctor` for readiness diagnostics and
   `brick verify` for checker evidence.
8. The customer starts work through `brick build --task ...` or a declared DSL
   graph when graph-shaped work is needed.

## Issuer Duties

1. Confirm the GitHub account or org/user before sending the invite.
2. Send access only through the repository invitation path.
3. Do not distribute setup tokens, credentials, provider session bodies, or
   private auth material through docs, chat, Building evidence, Agent returns,
   Link records, or support projections.
4. Tell the customer to use their own `gh auth login` or git credential flow.
5. Point the customer at `README.md`, this quickstart path, and
   `support/docs/references/setup.md` rather than a separate install channel.
6. Preserve the literal success signal `5) 설치 점검 완료` across docs,
   installer output, and checker evidence.
7. Treat `brick doctor`, `brick verify`, and checker output as support evidence
   only, not as source truth, success judgment, quality judgment, or Movement
   authority.
8. Record any exception, failed invite, or customer-specific installation gap as
   support evidence without embedding credential bodies or provider runtime
   state.

## Proof Limits

This procedure does not prove that a given invitation was accepted, that a fresh
machine can install without manual help, that provider credentials are present
or valid, or that a later Building is complete. Those require separate recorded
evidence.
