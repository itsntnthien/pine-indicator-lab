import csv
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from check_intraday_logs import check


class NativeLogChecks(unittest.TestCase):
    def run_rows(self, rows):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'logs.csv'
            f = path.open('w', newline='', encoding='utf-8')
            writer = csv.writer(f)
            writer.writerow(['Date', 'Message'])
            writer.writerows(rows)
            f.close()
            return check(path, 'OANDA:XAUUSD', 5, .01)

    def rows(self):
        ident = 'OANDA:XAUUSD:60>5:1794579000000:1'
        return [['2026-11-13T21:05:00+07:00', f'SETUP|{ident}|101|2|99|98.8|105|OANDA:XAUUSD:60:OB:1:1794574800000:1794578400000'],
                ['2026-11-13T21:10:00+07:00', f'OPEN|{ident}|1794579000000|102|0.9375|false']]

    def test_valid_and_missing_target(self):
        self.assertEqual(self.run_rows(self.rows())['setups'], 1)
        rows = self.rows()
        rows[0][1] = rows[0][1].replace('|105|', '|NaN|')
        rows[1][1] = rows[1][1].replace('|0.9375|', '|NaN|')
        self.assertEqual(self.run_rows(rows)['coverage']['missing_tp'], 1)

    def test_duplicate_future_stop_and_rr_fail(self):
        base = self.rows()
        cases = [base + [base[0]],
                 [[base[0][0], base[0][1].replace('1794578400000', '1794582000000')], base[1]],
                 [[base[0][0], base[0][1].replace('|98.8|', '|99.8|')], base[1]],
                 [base[0], [base[1][0], base[1][1].replace('|0.9375|', '|2|')]]]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.run_rows(rows)

    def test_adverse_gap_is_observation_not_profit(self):
        rows = self.rows()
        rows[1][1] = rows[1][1].replace('|102|0.9375|false', '|98|NaN|true')
        self.assertEqual(self.run_rows(rows)['coverage']['adverse_open'], 1)


if __name__ == '__main__':
    unittest.main()
