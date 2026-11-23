# Contributing

1. Describe the observed problem, script version, symbol/feed and timeframe.
2. Keep Pine and its Python reference consistent. Explain any change to timing,
   confirmation, warmup or lifecycle rules.
3. Rebuild the relevant `dist/` script and run the commands in
   [Verification](docs/VERIFICATION.md).
4. Record native compile/chart/replay separately from Python results. Do not
   label a native gate PASS merely because an offline test passes.
5. Preserve attribution and frozen fixtures. Do not modify a historical
   baseline just to make regression tests pass.
6. Use synthetic fixtures; never commit keys, cookies, account configuration,
   market-data exports or personal session logs.

Keep a change focused. Use the PR template to state behavior, evidence and
remaining limitations. A favorable backtest sample is not a regression test.
