"""Build a test-only Pine Logs witness without changing the delivered indicator."""
import json
from workspace import ROOT, sha
from build_lux_custom import build, OUTPUT

AUDIT = r'''
// Test-only instrumentation: capture closed-bar inputs and complete chart state.
f_auditNumber(float value) =>
    str.tostring(value, "#.############")

[auditH1Open, auditH1High, auditH1Low] = request.security(syminfo.tickerid, h1Request, [open[1], high[1], low[1]], lookahead = barmerge.lookahead_on)
[auditH4Open, auditH4High, auditH4Low] = request.security(syminfo.tickerid, h4Request, [open[1], high[1], low[1]], lookahead = barmerge.lookahead_on)
if barstate.isconfirmed
    string regions = ""
    if bar_index % 50 == 0
        for z in lxRegions
            regions += (regions == "" ? "" : ";") + z.kind + "," + str.tostring(z.side) + "," + f_auditNumber(z.lo) + "," + f_auditNumber(z.hi) + "," + str.tostring(z.anchor) + "," + str.tostring(z.born) + "," + str.tostring(z.available) + "," + str.tostring(z.stage)
    string pools = ""
    if bar_index % 50 == 0
        for p in lxPools
            pools += (pools == "" ? "" : ";") + f_auditNumber(p.level) + "," + str.tostring(p.side) + "," + str.tostring(p.anchor) + "," + str.tostring(p.born) + "," + str.tostring(p.equalLevel)
    array<string> fields = array.from("O1", str.tostring(BUILD_TOKEN), syminfo.tickerid, timeframe.period, f_auditNumber(tick), str.tostring(bar_index), str.tostring(time), str.tostring(time_close), f_auditNumber(open), f_auditNumber(high), f_auditNumber(low), f_auditNumber(close), f_auditNumber(ltfAtr), str.tostring(lxInternalBreak), str.tostring(lxInternalType), str.tostring(lxSwingBreak), str.tostring(lxSwingType), str.tostring(lxSweepMask), str.tostring(lxEqualMask), str.tostring(lxInversionCount), str.tostring(lxInternal.bias), str.tostring(lxSwing.bias), str.tostring(h1Bias), str.tostring(h4Bias), str.tostring(h1Time), str.tostring(h1CloseTime), str.tostring(h4Time), str.tostring(h4CloseTime), str.tostring(standardChart), lxAssessment, regions, pools, f_auditNumber(auditH1Open), f_auditNumber(auditH1High), f_auditNumber(auditH1Low), f_auditNumber(h1Close), f_auditNumber(auditH4Open), f_auditNumber(auditH4High), f_auditNumber(auditH4Low), f_auditNumber(h4Close), str.tostring(array.size(lxRegions)), str.tostring(array.size(lxPools)), str.tostring(bar_index % 50 == 0))
    log.info(array.join(fields, "|"))
'''

if __name__ == '__main__':
    manifest = build()
    directory = ROOT / 'output/playwright/lux-observer-20261116'
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / 'OBSERVER_AUDIT.pine'
    target.write_text(OUTPUT.read_text(encoding='utf-8') + '\n' + AUDIT, encoding='utf-8', newline='\n')
    result = {'base_sha256': manifest['sha256'], 'build_token': manifest['build_token'],
              'instrumented_sha256': sha(target), 'path': target.relative_to(ROOT).as_posix(),
              'change': 'Append read-only closed-bar logging and offset HTF OHLC requests only'}
    target.with_suffix('.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result))
