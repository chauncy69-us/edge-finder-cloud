import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import refresh_data as r

class RefreshTests(unittest.TestCase):
    def test_normalize_greco_and_no_contest(self):
        fights='EVENT,BOUT,OUTCOME,METHOD\nUFC 100,Amy A vs. Betty B,W/L,KO\nUFC 100,Cara C vs. Dina D,L/W,Decision\nUFC 100,E E vs. F F,NC/NC,NC\n'
        ev='EVENT,DATE,URL\nUFC 100,"October 20, 2026",abc\n'
        out=r.normalize_ufc(fights,ev)
        self.assertEqual(len(out),2)
        self.assertEqual(out[0][2],'Amy A')
        self.assertEqual(out[0][3],'2026-10-20')
        self.assertEqual(out[1][2],'Dina D')
    def test_normalize_second_format(self):
        fights='r_fighter,b_fighter,winner,event_url,method\nJoe Doe,Mark Doe,Joe Doe,foo,submission\n'
        ev='event_name,event_date,event_url\nX,2026-10-20,foo\n'
        out=r.normalize_ufc(fights,ev)
        self.assertEqual(out[0][2],'Joe Doe')
        self.assertEqual(out[0][3],'2026-10-20')
    def test_greco_current_source_headers(self):
        fights='EVENT,BOUT,OUTCOME,WEIGHTCLASS,METHOD,ROUND,TIME,TIME FORMAT,REFEREE,DETAILS,URL\nUFC Fight Night: Buckley vs. Malott ,Joaquin Buckley vs. Mike Malott,L/W,Welterweight Bout,KO/TKO,2,2:32,X,X,X,https://example.com/fight\n'
        events='EVENT,URL,DATE,LOCATION\nUFC Fight Night: Buckley vs. Malott,https://example.com/event,"October 17, 2026",Canada\n'
        results=r.normalize_ufc(fights,events)
        self.assertEqual(len(results),1)
        self.assertEqual(results[0][2],'Mike Malott')
        self.assertEqual(results[0][3],'2026-10-17')
        self.assertIn('ufc_event_details.csv',Path(r.__file__).read_text())
    def test_reject_html(self):
        self.assertFalse(r.check_csv(b'<html>'+b'x'*1000+b'</html>','nfl'))
    def test_valid_minimal_nfl(self):
        x=('season,week,player_display_name,passing_yards\n'+''.join(f'2026,{i},Test Player,230\n' for i in range(1,18))).encode()
        self.assertTrue(r.check_csv(x,'nfl'))
    def test_json_payload_is_safe_js(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'feed.js'
            r.write_bundle({'ufc':'</script><script>alert(1)</script>'},p)
            self.assertNotIn('</script>',p.read_text())

if __name__=='__main__':unittest.main()
