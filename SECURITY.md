# Sensitive data

Report sensitive findings privately to the repository owner. Do not attach
cookies, API keys, account data or live session information to issues or PRs.

This repo contains Pine indicators and build/verification tooling. It does not
need broker credentials for build or offline tests. Raw TradingView exports
used for parity are local inputs and should remain outside Git.

If a real secret is committed, revoke/rotate it before cleaning Git history.
Deleting it in a later commit does not erase the previous content.

The publication check blocks common sensitive paths and high-confidence secret
patterns. It is a packaging guard, not a full security audit.
