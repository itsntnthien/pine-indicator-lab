"""Parser and false-PASS protections; these CSVs are synthetic, not native evidence."""
import csv
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from check_intraday_parity import compare, read_export


class ExportChecks(unittest.TestCase):
    def fixture(self, folder):
        def row(index, minutes):
            return {'time': 1640995200 + index*minutes*60, 'open': 100, 'high': 101, 'low': 99, 'close': 100,
                    'Audit source index': index, 'Audit feed': 1, 'Audit minutes': minutes,
                    'Audit standard chart': 1, 'Audit build token': 123, 'Audit tick': .01,
                    'Audit close epoch': 1640995200 + (index+1)*minutes*60}
        htf = [row(i, 60) for i in range(21)]
        ltf = []
        for i in range(240):
            item = row(i, 5)
            count = i // 12
            item.update({'Audit HTF source index': count-1 if count else '',
                         'Audit ATR14 LTF': 2 if i >= 13 else '', 'Audit ATR14 HTF': 2 if count >= 14 else '',
                         'Audit hướng HTF': 0, 'Audit signal': 0, 'Audit SL xác nhận': '',
                         'Audit TP xác nhận': '', 'Audit cực trị nhịp': '', 'Audit open nến sau': ''})
            ltf.append(item)
        lp, hp = Path(folder)/'ltf.csv', Path(folder)/'htf.csv'
        self.write(lp, ltf)
        self.write(hp, htf)
        return lp, hp, ltf, htf

    def write(self, path, rows):
        with path.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0])
            writer.writeheader()
            writer.writerows(rows)

    def test_zero_events_cannot_certify_setup_parity(self):
        with tempfile.TemporaryDirectory() as folder:
            lp, hp, _, _ = self.fixture(folder)
            result = compare(lp, hp, 'OANDA:XAUUSD', 5, 123)
            self.assertEqual(result['mismatch_count'], 0)
            self.assertEqual(result['comparisons'], 2160)
            self.assertEqual(result['status'], 'INSUFFICIENT_EVENTS')

    def test_extra_signal_and_wrong_atr_are_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            lp, hp, rows, _ = self.fixture(folder)
            rows[20]['Audit signal'] = 1
            rows[21]['Audit ATR14 LTF'] = 2.5
            self.write(lp, rows)
            result = compare(lp, hp, 'OANDA:XAUUSD', 5, 123)
            self.assertEqual(result['status'], 'FAIL')
            self.assertEqual(result['mismatch_count'], 2)

    def test_feed_build_tick_and_truncated_history_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            lp, hp, rows, htf = self.fixture(folder)
            for feed, token in [('FOREXCOM:NAS100', 123), ('OANDA:XAUUSD', 124)]:
                with self.subTest(feed=feed, token=token), self.assertRaises(ValueError):
                    read_export(lp, feed, 5, token)
            self.write(lp, rows[1:])
            with self.assertRaisesRegex(ValueError, 'source index'):
                compare(lp, hp, 'OANDA:XAUUSD', 5, 123)
            self.write(lp, rows)
            for row in htf:
                row['Audit tick'] = .1
            self.write(hp, htf)
            with self.assertRaisesRegex(ValueError, 'tick metadata'):
                compare(lp, hp, 'OANDA:XAUUSD', 5, 123)


if __name__ == '__main__':
    unittest.main()
