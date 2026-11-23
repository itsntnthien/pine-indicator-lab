import csv
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from check_lux_native import FIELDS,check


class NativeWitnessTests(unittest.TestCase):
    def witness(self,path,mutation=None):
        with path.open('w',encoding='utf-8',newline='') as file:
            writer=csv.DictWriter(file,fieldnames=['Date','Message'])
            writer.writeheader()
            for i in range(20):
                row=dict.fromkeys(FIELDS,'0')
                row.update(tag='O1',token='123',feed='OANDA:XAUUSD',tf='5',tick='0.001',index=str(i),
                           time=str(1800000000000+i*300000),end=str(1800000000000+(i+1)*300000),
                           open='100',high='102',low='98',close='100',atr='NaN' if i<13 else '4',
                           standard='true',assessment='Hướng HTF chưa xác lập',regions='',pools='',
                           snapshot='true' if i%50==0 else 'false')
                if mutation:
                    mutation(row,i)
                writer.writerow({'Date':'unused','Message':'|'.join(row[k] for k in FIELDS)})

    def test_flat_prices_and_warmup(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'w.csv';self.witness(p)
            result=check(p,123)
            self.assertEqual(result['status'],'PASS_NATIVE_PARITY')
            self.assertEqual(result['rows'],20)

    def test_corrupted_atr_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'w.csv';self.witness(p,lambda r,i:r.update(atr='5') if i==19 else None)
            result=check(p,123)
            self.assertEqual(result['difference_count'],1)
            self.assertEqual(result['differences_first_30'][0]['field'],'atr')

    def test_truncated_snapshot_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'w.csv';self.witness(p,lambda r,i:r.update(regions='FVG,1,100') if i==19 else None)
            with self.assertRaisesRegex(ValueError,'Truncated'):
                check(p,123)

    def test_missing_history_or_wrong_build_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'w.csv';self.witness(p)
            with self.assertRaisesRegex(ValueError,'build token'):
                check(p,124)
            self.witness(p,lambda r,i:r.update(index=str(i+1)))
            with self.assertRaisesRegex(ValueError,'complete history'):
                check(p,123)

    def test_future_htf_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'w.csv';self.witness(p,lambda r,i:r.update(h1_end=str(int(r['time'])+1)))
            result=check(p,123)
            self.assertEqual(result['difference_count'],20)

    def test_identical_duplicate_requires_explicit_option_and_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'w.csv'
            self.witness(p)
            lines=p.read_text('utf-8').splitlines()
            p.write_text('\n'.join(lines+[lines[-1]])+'\n',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'duplicate'):
                check(p,123)
            result=check(p,123,True)
            self.assertEqual(result['exact_duplicate_logs'],1)
            self.assertEqual(result['log_uniqueness'],'FAIL')
            self.assertEqual(result['difference_count'],0)
            lines[-1]=lines[-1].replace('|4|','|5|',1)
            p.write_text('\n'.join(lines+[p.read_text('utf-8').splitlines()[-1]])+'\n',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Conflicting'):
                check(p,123,True)


if __name__=='__main__':
    unittest.main()
