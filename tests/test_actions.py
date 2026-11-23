import importlib.util
from pathlib import Path
from datetime import datetime, timedelta, timezone
from copy import deepcopy
import sys
from types import ModuleType, SimpleNamespace
import unittest
from test_time_model import settings, solar, TZ, backend_scope

ROOT=Path(__file__).parents[1]/'custom_components/weihnachtszentrale'
package=ModuleType('wz_action_test');package.__path__=[str(ROOT)];sys.modules['wz_action_test']=package
spec=importlib.util.spec_from_file_location('wz_action_test.actions',ROOT/'actions.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
build=module.build_actions
UTC=timezone.utc

def iso(value):return datetime.fromisoformat(value).astimezone(UTC)

class ActionsTests(unittest.TestCase):
    def run_actions(self,s=None,now=None,callback=solar):
        return build(s or settings(),now or datetime(2026,10,30,5,tzinfo=TZ),'Europe/Berlin',callback)
    def test_four_daily_groups(self):
        p=self.run_actions();self.assertEqual(len(p['actions']),4)
        self.assertEqual([iso(a['at']).astimezone(TZ).hour for a in p['actions']],[6,9,16,22])
        self.assertEqual(p['actions'][0]['on'][0]['entity_id'],'light.tree');self.assertEqual(p['actions'][1]['off'][0]['entity_id'],'light.tree')
    def test_group_devices_same_instant(self):
        s=settings();s['devices'].append({**s['devices'][0],'id':'2','entity_id':'light.other','name':'Andere'})
        a=self.run_actions(s)['actions'];self.assertEqual(len(a),4);self.assertEqual([d['entity_id'] for d in a[0]['on']],['light.other','light.tree'])
    def test_profile_mapping(self):
        s=settings();s['devices'][0]['profile']='morning';s['devices'].append({**s['devices'][0],'id':'2','entity_id':'switch.evening','profile':'evening'})
        a=self.run_actions(s)['actions'];self.assertEqual(len(a),4);self.assertEqual(a[0]['on'][0]['entity_id'],'light.tree');self.assertEqual(a[2]['on'][0]['entity_id'],'switch.evening')
    def test_no_past_start_but_future_end(self):
        a=self.run_actions(now=datetime(2026,10,30,7,tzinfo=TZ))['actions'];self.assertIn('T09:00',a[0]['at']);self.assertEqual(a[0]['on'],[]);self.assertEqual(len(a[0]['off']),1)
    def test_midnight_rolls_next_day(self):
        a=self.run_actions(now=datetime(2026,10,30,23,tzinfo=TZ))['actions'];self.assertEqual(len(a),4);self.assertTrue(all(x['at'].startswith('2026-10-31') for x in a))
    def test_modes_and_disabled(self):
        for mode,enabled,device_mode in [('off',True,'both'),('reduced',True,'full'),('full',False,'both')]:
            s=settings();s['season']=mode;s['devices'][0].update(enabled=enabled,season=device_mode);self.assertEqual(self.run_actions(s)['actions'],[])
    def test_no_devices(self):
        s=settings();s['devices']=[];self.assertEqual(self.run_actions(s)['actions'],[])
    def test_reduced_eligible(self):
        s=settings();s['season']='reduced';self.assertEqual(len(self.run_actions(s)['actions']),4)
    def test_exact_now_included(self):
        a=self.run_actions(now=datetime(2026,10,30,6,tzinfo=TZ))['actions'];self.assertIn('2026-10-30T06:00',a[0]['at'])
    def test_exclusive_24h_end(self):
        p=self.run_actions(now=datetime(2026,10,30,6,tzinfo=TZ));self.assertFalse(any(x['at'].startswith('2026-10-31T06:00') for x in p['actions']))
    def test_fall_actual_24hours(self):
        p=self.run_actions(now=datetime(2026,10,24,23,30,tzinfo=TZ));self.assertEqual((iso(p['until'])-iso(p['generated_at'])).total_seconds(),86400);self.assertIn('2026-10-25T22:30',p['until'])
    def test_spring_third_local_day(self):
        s=settings();s['times']['morning_on']['time']='00:15';s['times']['morning_off']['time']='00:20'
        p=self.run_actions(s,datetime(2026,3,28,23,30,tzinfo=TZ));self.assertIn('2026-03-30T00:30',p['until']);self.assertTrue(any(x['at'].startswith('2026-03-30T00:15') for x in p['actions']))
        self.assertEqual((iso(p['until'])-iso(p['generated_at'])).total_seconds(),86400)
    def test_invalid_evening_excluded(self):
        s=settings();s['times']['evening_on']['time']='08:00';p=self.run_actions(s);self.assertTrue(p['warnings']);self.assertEqual(len(p['actions']),2)
    def test_solar_offset_recomputed(self):
        s=settings();s['times']['evening_on'].update(event='sunset',offset=-30)
        a=self.run_actions(s)['actions'];self.assertTrue(any('T16:30' in x['at'] for x in a))
    def test_name_and_cover_kept(self):
        s=settings();s['devices'][0]['cover']='cover.tree';d=self.run_actions(s)['actions'][0]['on'][0];self.assertEqual(d['cover'],'cover.tree');self.assertEqual(d['name'],'Baum')
    def test_unique_entries(self):
        a=self.run_actions()['actions'];ids=[(g['at'],k,d['entity_id']) for g in a for k in ('on','off') for d in g[k]];self.assertEqual(len(ids),len(set(ids)))
    def test_sorted_by_real_time(self):
        a=self.run_actions()['actions'];self.assertEqual([iso(x['at']) for x in a],sorted(iso(x['at']) for x in a))
    def test_no_mutation(self):
        s=settings();before=deepcopy(s);self.run_actions(s);self.assertEqual(s,before)
    def test_live_change_rebuilds(self):
        s=settings();self.run_actions(s);s['times']['morning_on']['time']='07:15';self.assertIn('T07:15',self.run_actions(s)['actions'][0]['at'])
    def test_missing_sun_no_fake_actions(self):
        s=settings();s['times']['morning_on']['event']='dawn';p=self.run_actions(s,callback=lambda *_:None);self.assertTrue(p['warnings']);self.assertEqual(len(p['actions']),2)

class ActionCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_command_success_and_rejection(self):
        import ast
        scope=backend_scope();scope['build_actions']=build
        tree=ast.parse((ROOT/'__init__.py').read_text());node=next(x for x in tree.body if isinstance(x,ast.AsyncFunctionDef) and x.name=='ws_actions');node.decorator_list=[]
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(ROOT/'__init__.py'),'exec'),scope)
        result=[];errors=[];conn=SimpleNamespace(send_result=lambda *x:result.append(x),send_error=lambda *x:errors.append(x));h=SimpleNamespace(data={'weihnachtszentrale':{}},config=SimpleNamespace(time_zone='Europe/Berlin'))
        await scope['ws_actions'](h,conn,{'id':1,'settings':settings()});self.assertFalse(errors);self.assertEqual(result[-1][1]['model_version'],'0.7.1');self.assertTrue(result[-1][1]['read_only'])
        bad=settings();bad['devices'].append(deepcopy(bad['devices'][0]));await scope['ws_actions'](h,conn,{'id':2,'settings':bad});self.assertEqual(errors[-1][1],'invalid_settings')
        h.data.clear();await scope['ws_actions'](h,conn,{'id':3,'settings':settings()});self.assertEqual(errors[-1][1],'not_loaded')

if __name__=='__main__':unittest.main()
