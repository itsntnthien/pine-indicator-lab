# Sources and attribution

| Component | Source record | Terms recorded in the workspace |
|---|---|---|
| SMC / ICT Observer | [Seven LuxAlgo scripts, hashes and changes](docs/LUX_CUSTOM_ATTRIBUTION.json) | © LuxAlgo; CC BY-NC-SA 4.0 |
| VSA presentation | [Six LuxAlgo UI sources and adapted portions](docs/VSA_OBSERVER_LUX_UI_SOURCES.json) | © LuxAlgo; CC BY-NC-SA 4.0 |
| Original VSA attachment | [Original provenance](research/vsa-observer-20261117/provenance.json) | User supplied; no license grant assumed |
| Legacy feature/type/resampling helpers | `references/workspace/TradingView/SMC-PRO-XAUUSD/calibration/pivot/` | Preserved internal code; no new license grant |
| Time-zone database for Python tests | `tzdata==2026.2` in `requirements-test.txt` | Installed as a dependency; its own notices apply |

The external LuxAlgo source collections are not bundled. Original URLs, versions,
SHA-256 hashes and descriptions of modified portions are retained. Fields named
`original` and `local_source` refer to historical workspace paths; those complete
collections are outside the export.

The VSA v2 baseline is retained because existing regression tests assert its
bytes. It is frozen, not a second actively maintained indicator. The original
notices and provenance apply.

For the adapted portions, preserve attribution and the applicable
[CC BY-NC-SA 4.0 terms](https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.en).
No whole-repository license is inferred from a third-party component; see
[LICENSE.md](LICENSE.md).

TradingView screenshots illustrate the indicators running on that platform.
TradingView and LuxAlgo names remain their respective owners' names. This is an
independent private research project, not an official product of either.
