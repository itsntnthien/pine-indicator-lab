import csv
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import indicator_readiness as audit


class ReadinessChecks(unittest.TestCase):
    def test_wilder_seed_recurrence_and_causality(self):
        values = [2.0, 4.0, 6.0, 12.0, 3.0]
        result = audit.wilder_atr(values, 3)
        self.assertEqual(result[:3], [None, None, 4.0])
        self.assertAlmostEqual(result[3], 20 / 3)
        self.assertAlmostEqual(result[4], 49 / 9)
        self.assertEqual(audit.wilder_atr(values[:4], 3), audit.wilder_atr(values, 3)[:4])
        self.assertEqual(audit.wilder_atr([2.0], 3), [None])
        for bad in ([float('nan')], [float('inf')], [-1.0]):
            with self.assertRaises(ValueError):
                audit.wilder_atr(bad)

    def test_inclusive_percentiles(self):
        self.assertEqual(audit.distribution([0.0, 10.0]), {'p10': 1.0, 'p50': 5.0, 'p90': 9.0, 'p95': 9.5})

    def test_reject_invalid_data_and_protected_window(self):
        base = dict(timestamp='2022-01-03T00:05:00+00:00', open=100, high=102, low=99, close=101,
                    provider='DUPOIN', provider_instrument='XAUUSD.v', timeframe='M5', timezone='UTC',
                    price_semantics='MT5_BROKER_CHART_BARS', component_count=5, session_closed_component_count=0,
                    expected_open_component_count=5, completeness_status='COMPLETE_OPEN_SESSION', spread=20)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'bars.csv'
            def write(rows):
                with path.open('w', newline='', encoding='utf-8') as handle:
                    writer = csv.DictWriter(handle, fieldnames=base)
                    writer.writeheader()
                    writer.writerows(rows)
            rows = []
            stamp = audit.datetime.fromisoformat(base['timestamp'])
            for i in range(110):
                rows.append(dict(base, timestamp=(stamp + audit.timedelta(minutes=5*i)).isoformat()))
            write(rows)
            self.assertEqual(len(audit.read_bars(path, 'M5')[0]), 110)
            for change, message in [({'high': 'nan'}, 'OHLC'), ({'low': 105}, 'OHLC'),
                                    ({'timestamp': '2025-01-03T00:05:00+00:00'}, '2022'),
                                    ({'timestamp': '2022-01-03T00:05:00'}, 'UTC'),
                                    ({'provider_instrument': 'NAS100'}, 'feed'),
                                    ({'component_count': 4}, 'component'),
                                    ({'completeness_status': 'UNKNOWN'}, 'Incomplete')]:
                with self.subTest(change=change):
                    write([dict(rows[0], **change), *rows[1:]])
                    with self.assertRaisesRegex(ValueError, message):
                        audit.read_bars(path, 'M5')
            write([rows[0], *rows])
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                audit.read_bars(path, 'M5')


if __name__ == '__main__':
    unittest.main()
