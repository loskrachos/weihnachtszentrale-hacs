import ast
import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import re
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parents[1] / 'custom_components/weihnachtszentrale'
TZ = ZoneInfo('Europe/Berlin')
UTC = timezone.utc

def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

preview = load('preview')
solar_module = load('solar')

def settings():
    return {'season':'full', 'devices':[{'id':'1','entity_id':'light.tree','name':'Baum',
            'enabled':True,'season':'both','profile':'both','cover':''}],
            'times':{k:{'event':'fixed','time':v,'offset':0} for k,v in zip(preview.KEYS,['06:00','09:00','16:00','22:00'])}}

def solar(event, day, twilight):
    minutes = {'sunrise':7*60,'sunset':17*60,'dawn':{'civil':6*60,'nautical':5*60,'astronomical':4*60}[twilight],
               'dusk':{'civil':18*60,'nautical':19*60,'astronomical':20*60}[twilight]}[event]
    return datetime(day.year,day.month,day.day,tzinfo=TZ)+timedelta(minutes=minutes)

class TimeTests(unittest.TestCase):
    def run_model(self, s=None, now=None, callback=solar):
        return preview.build_preview(s or settings(),now or datetime(2026,10,30,12,tzinfo=TZ),'Europe/Berlin',callback)
    def test_daytime_windows(self):
        p=self.run_model();self.assertEqual(p['days'][0]['windows'][0]['start'],'2026-10-30T06:00:00+01:00')
        self.assertFalse(p['devices'][0]['scheduled_on'])
    def test_night_window(self):
        s=settings();s['times']['evening_on']['time']='22:00';s['times']['evening_off']['time']='02:00'
        p=self.run_model(s);self.assertEqual(len(p['days'][0]['windows']),1)
        self.assertIn('Partymodus',' '.join(p['days'][0]['warnings']))
    def test_previous_night_active(self):
        s=settings();s['times']['evening_on']['time']='22:00';s['times']['evening_off']['time']='02:00'
        p=self.run_model(s,datetime(2026,10,30,1,tzinfo=TZ));self.assertFalse(p['devices'][0]['scheduled_on'])
        self.assertFalse(any(w['start'].startswith('2026-10-29') for w in p['devices'][0]['effective_windows']))
    def test_boundaries_half_open(self):
        self.assertTrue(self.run_model(now=datetime(2026,10,30,6,tzinfo=TZ))['devices'][0]['scheduled_on'])
        self.assertFalse(self.run_model(now=datetime(2026,10,30,9,tzinfo=TZ))['devices'][0]['scheduled_on'])
    def test_overlap_rejected(self):
        s=settings();s['times']['morning_off']['time']='18:00'
        p=self.run_model(s);w=p['devices'][0]['effective_windows'];self.assertEqual(len(w),2)
        self.assertEqual(w[0]['start'],'2026-10-30T06:00:00+01:00');self.assertEqual(w[0]['end'],'2026-10-30T18:00:00+01:00');self.assertIn('Abend an muss nach Morgen aus',' '.join(p['days'][0]['warnings']))
    def test_touching_union(self):
        s=settings();s['times']['morning_off']['time']='16:00';p=self.run_model(s);self.assertTrue(p['days'][0]['warnings']);self.assertEqual(len(p['days'][0]['windows']),1)
    def test_nested_evening_rejected(self):
        s=settings();s['times']['morning_off']['time']='23:00';w=self.run_model(s)['devices'][0]['effective_windows'];self.assertEqual(len(w),2);self.assertIn('23:00',w[0]['end'])
    def test_profile_isolation(self):
        s=settings();s['times']['morning_off']['time']='18:00';s['devices'][0]['profile']='evening'
        p=self.run_model(s);w=p['devices'][0]['effective_windows'];self.assertEqual(w,[]);self.assertTrue(p['days'][0]['warnings'])
    def test_equal_invalid_not_24h(self):
        s=settings();s['times']['morning_off']['time']='06:00'
        p=self.run_model(s);self.assertTrue(p['days'][0]['warnings']);self.assertEqual(len(p['days'][0]['windows']),1)
    def test_solar_end_recomputed_on_next_day(self):
        s=settings();s['times']['evening_on']['time']='22:00';s['times']['evening_off']['event']='sunrise'
        p=self.run_model(s);self.assertEqual(len(p['days'][0]['windows']),1)
        self.assertFalse(any(w['profile']=='evening' for w in p['days'][1]['windows']))
    def test_solar_offsets(self):
        for offset in (-180,-30,0,30,180):
            s=settings();s['times']['evening_on'].update(event='sunset',offset=offset)
            r=self.run_model(s)['days'][0]['rules'][2]
            self.assertEqual(datetime.fromisoformat(r['at']).hour*60+datetime.fromisoformat(r['at']).minute,17*60+offset)
    def test_fixed_ignores_offset(self):
        s=settings();s['times']['morning_on']['offset']=180;self.assertIn('T06:00',self.run_model(s)['days'][0]['rules'][0]['at'])
    def test_missing_event(self):
        s=settings();s['times']['morning_on']['event']='dawn'
        p=self.run_model(s,callback=lambda *_:None);self.assertIsNone(p['days'][0]['rules'][0]['at']);self.assertEqual(len(p['days'][0]['windows']),1)
    def test_missing_next_day_end(self):
        s=settings();s['times']['evening_on']['time']='22:00';s['times']['evening_off']['event']='sunrise'
        p=self.run_model(s,callback=lambda e,d,t:None if d.day==31 else solar(e,d,t));self.assertEqual(len(p['days'][0]['windows']),1)
    def test_all_twilight_types(self):
        for kind,hour in [('civil',6),('nautical',5),('astronomical',4)]:
            s=settings();s['times']['morning_on'].update(event='dawn',twilight=kind)
            self.assertIn(f'T{hour:02}:00',self.run_model(s)['days'][0]['rules'][0]['at'])
    def test_legacy_defaults_civil(self):
        s=settings();s['times']['morning_on']['event']='dawn';self.assertIn('T06:00',self.run_model(s)['days'][0]['rules'][0]['at'])
    def test_spring_gap(self):
        s=settings();s['times']['morning_on']['time']='02:30'
        p=self.run_model(s,datetime(2026,3,29,12,tzinfo=TZ));self.assertIsNone(p['days'][0]['rules'][0]['at'])
    def test_spring_overnight_actual_duration(self):
        s=settings();s['times']['morning_on']['time']='00:30';s['times']['morning_off']['time']='04:00'
        w=self.run_model(s,datetime(2026,3,29,12,tzinfo=TZ))['days'][0]['windows'][0]
        self.assertEqual((datetime.fromisoformat(w['end'])-datetime.fromisoformat(w['start'])).total_seconds(),2.5*3600)
    def test_spring_night_end_in_gap_not_shifted(self):
        s=settings();s['times']['evening_on']['time']='22:00';s['times']['evening_off']['time']='02:30'
        p=self.run_model(s,datetime(2026,3,28,12,tzinfo=TZ))
        self.assertTrue(all(not any(w['profile']=='evening' for w in day['windows']) for day in p['days']))
    def test_autumn_fold_first(self):
        s=settings();s['times']['morning_on']['time']='02:30'
        r=self.run_model(s,datetime(2026,10,25,12,tzinfo=TZ))['days'][0]['rules'][0];self.assertIn('+02:00',r['at']);self.assertIn('erstes',r['warning'])
    def test_autumn_night_duration(self):
        s=settings();s['times']['morning_on']['time']='00:30';s['times']['morning_off']['time']='04:00'
        w=self.run_model(s,datetime(2026,10,25,12,tzinfo=TZ))['days'][0]['windows'][0]
        self.assertEqual((datetime.fromisoformat(w['end'])-datetime.fromisoformat(w['start'])).total_seconds(),4.5*3600)
    def test_second_fold_active_utc_comparison(self):
        s=settings();s['times']['morning_on']['time']='02:30';s['times']['morning_off']['time']='03:30'
        p=self.run_model(s,datetime(2026,10,25,2,15,tzinfo=TZ,fold=1));self.assertTrue(p['devices'][0]['scheduled_on'])
    def test_offset_crossing_midnight(self):
        s=settings();s['times']['morning_on'].update(event='dawn',offset=-180)
        def midnight(e,d,t):return datetime(d.year,d.month,d.day,1,tzinfo=TZ)
        p=self.run_model(s,callback=midnight);self.assertTrue(p['days'][0]['rules'][0]['at'].startswith('2026-10-29T22:00'));self.assertTrue(p['days'][0]['warnings']);self.assertFalse(any(w['profile']=='morning' for w in p['days'][0]['windows']))
    def test_timezone_day_not_utc(self):
        p=self.run_model(now=datetime(2026,10,29,23,30,tzinfo=UTC));self.assertEqual(p['days'][0]['date'],'2026-10-30')
    def test_modes(self):
        for season,enabled,device_season,eligible in [('off',True,'both',False),('reduced',True,'full',False),('reduced',True,'both',True),('full',False,'both',False),('full',True,'full',True)]:
            s=settings();s['season']=season;s['devices'][0].update(enabled=enabled,season=device_season)
            d=self.run_model(s)['devices'][0];self.assertEqual(d['eligible'],eligible)
            if not eligible:self.assertEqual(d['effective_windows'],[]);self.assertFalse(d['scheduled_on'])
    def test_changes_no_stale_cache(self):
        s=settings();self.run_model(s);s['times']['morning_on']['time']='07:15';self.assertIn('T07:15',self.run_model(s)['days'][0]['rules'][0]['at'])
    def test_no_mutation(self):
        s=settings();before=deepcopy(s);self.run_model(s);self.assertEqual(s,before)
    def test_evening_before_morning_end_by_one_minute(self):
        s=settings();s['times']['evening_on']['time']='08:59'
        p=self.run_model(s);self.assertEqual(len(p['days'][0]['windows']),1);self.assertIn('Abend an muss nach Morgen aus',' '.join(p['days'][0]['warnings']))
    def test_evening_equal_morning_end_rejected(self):
        s=settings();s['times']['evening_on']['time']='09:00'
        p=self.run_model(s);self.assertTrue(p['days'][0]['warnings']);self.assertEqual(len(p['days'][0]['windows']),1)
        self.assertEqual(p['devices'][0]['effective_windows'][0]['end'],'2026-10-30T09:00:00+01:00')
    def test_one_minute_daytime_gap_allowed(self):
        s=settings();s['times']['evening_on']['time']='09:01'
        p=self.run_model(s);self.assertFalse(p['days'][0]['warnings']);self.assertEqual(len(p['days'][0]['windows']),2)
        self.assertEqual(len(p['devices'][0]['effective_windows']),4)
    def test_offset_causes_cross_profile_conflict(self):
        s=settings();s['times']['morning_off']['time']='16:45';s['times']['evening_on'].update(event='sunset',offset=-30)
        p=self.run_model(s);self.assertTrue(p['days'][0]['warnings']);self.assertEqual(len(p['days'][0]['windows']),1)
    def test_missing_morning_end_blocks_evening_order(self):
        s=settings();s['times']['morning_off']['event']='sunrise'
        p=self.run_model(s,callback=lambda *_:None);self.assertEqual(p['days'][0]['windows'],[])
        self.assertIn('Reihenfolge',' '.join(p['days'][0]['warnings']))
    def test_serializable(self):
        import json
        json.dumps(self.run_model())

class SolarAdapterTests(unittest.TestCase):
    def test_observer_depression_and_timezone(self):
        calls=[]
        def event(observer,**kwargs):calls.append((observer,kwargs));return datetime(2026,10,30,6,tzinfo=UTC)
        astral=SimpleNamespace(Observer=lambda *args:args,sun=SimpleNamespace(dawn=event,dusk=event,sunrise=event,sunset=event))
        hass=SimpleNamespace(config=SimpleNamespace(latitude=49,longitude=11,elevation=300,time_zone='Europe/Berlin'))
        with patch.dict(sys.modules,{'astral':astral}):
            callback=solar_module.make_solar_event(hass)
            for kind,angle in [('civil',6),('nautical',12),('astronomical',18)]:
                for e in ('dawn','dusk'):
                    callback(e,datetime(2026,10,30).date(),kind);self.assertEqual(calls[-1][1]['depression'],angle)
            callback('sunrise',datetime(2026,10,30).date(),'astronomical');self.assertNotIn('depression',calls[-1][1])
            self.assertEqual(calls[-1][0],(49,11,300));self.assertEqual(str(calls[-1][1]['tzinfo']),'Europe/Berlin')
    def test_absent_event_handled(self):
        def missing(*args,**kwargs):raise ValueError('polar night')
        with patch.dict(sys.modules,{'astral':SimpleNamespace(Observer=lambda *args:args,sun=SimpleNamespace(sunrise=missing))}):
            h=SimpleNamespace(config=SimpleNamespace(latitude=80,longitude=0,elevation=0,time_zone='UTC'))
            self.assertIsNone(solar_module.make_solar_event(h)('sunrise',datetime(2026,12,1).date(),'civil'))

class Invalid(Exception):pass

def backend_scope():
    from test_engine import Engine
    from test_covers import Coordinator
    tree=ast.parse((ROOT/'__init__.py').read_text())
    names={'validate_settings','async_setup_entry','async_unload_entry','ws_get','ws_save','ws_preview','ws_engine','ws_enable'}
    nodes=[]
    for n in tree.body:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id.startswith('_') for t in n.targets):nodes.append(n)
        elif isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names:
            n.decorator_list=[];nodes.append(n)
    env={'re':re,'vol':SimpleNamespace(Invalid=Invalid),'HomeAssistant':object,'ConfigEntry':object,
         'deepcopy':deepcopy,'asyncio':asyncio,'DOMAIN':'weihnachtszentrale','STORE_VERSION':1,'STORE_KEY':'weihnachtszentrale.settings',
         'DEFAULT_SETTINGS':settings(),'build_preview':preview.build_preview,'dt_util':SimpleNamespace(now=lambda:datetime(2026,10,30,12,tzinfo=TZ)),
         'make_solar_event':lambda h:solar, 'LightEngine':Engine, 'CoverCoordinator':Coordinator,
         'timedelta':timedelta, 'EVENT_HOMEASSISTANT_STARTED':'homeassistant_started',
         'async_track_time_interval':lambda *args:lambda:None,
         'Platform':SimpleNamespace(BINARY_SENSOR='binary_sensor'),
         'SIGNAL_SETTINGS_CHANGED':'weihnachtszentrale_settings_changed',
         'async_dispatcher_send':lambda *args:None}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(ROOT/'__init__.py'),'exec'),env)
    return env

class SchemaTests(unittest.TestCase):
    def setUp(self):self.validate=backend_scope()['validate_settings']
    def test_legacy_migration(self):
        s=settings();n=self.validate(s);self.assertTrue(all(t['twilight']=='civil' for t in n['times'].values()));self.assertNotIn('twilight',s['times']['morning_on'])
    def test_all_types_persist(self):
        for kind in ('civil','nautical','astronomical'):
            s=settings();s['times']['morning_on']['twilight']=kind;self.assertEqual(self.validate(s)['times']['morning_on']['twilight'],kind)
    def test_invalid_type(self):
        s=settings();s['times']['morning_on']['twilight']='wrong'
        with self.assertRaises(Invalid):self.validate(s)
    def test_extra_field(self):
        s=settings();s['times']['morning_on']['typo']=1
        with self.assertRaises(Invalid):self.validate(s)
    def test_missing_field(self):
        s=settings();del s['times']['morning_on']['time']
        with self.assertRaises(Invalid):self.validate(s)
    def test_duplicate_entity(self):
        s=settings();s['devices'].append({**s['devices'][0],'id':'2'})
        with self.assertRaises(Invalid):self.validate(s)
    def test_invalid_offset(self):
        for value in (181,-181,True,1.5):
            s=settings();s['times']['morning_on']['offset']=value
            with self.assertRaises(Invalid):self.validate(s)

class BackendFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_migrate_save_reload_preview(self):
        env=backend_scope();saved=settings()
        class Store:
            def __init__(self,*args):pass
            async def async_load(self):return deepcopy(saved)
            async def async_save(self,value):saved.clear();saved.update(deepcopy(value))
        from unittest.mock import AsyncMock
        env['Store']=Store;h=SimpleNamespace(data={},config=SimpleNamespace(time_zone='Europe/Berlin'),
            config_entries=SimpleNamespace(async_forward_entry_setups=AsyncMock(),async_unload_platforms=AsyncMock(return_value=True)),
            is_running=False,bus=SimpleNamespace(async_listen_once=lambda *args:lambda:None,async_listen=lambda *args:lambda:None))
        await env['async_setup_entry'](h,object())
        self.assertEqual(h.data['weihnachtszentrale']['settings']['times']['morning_on']['twilight'],'civil')
        config=deepcopy(h.data['weihnachtszentrale']['settings']);config['times']['morning_on'].update(event='dawn',twilight='astronomical')
        results=[];errors=[]
        conn=SimpleNamespace(send_result=lambda *a:results.append(a),send_error=lambda *a:errors.append(a))
        await env['ws_save'](h,conn,{'id':1,'settings':config});self.assertFalse(errors)
        h.data.clear();await env['async_setup_entry'](h,object())
        self.assertEqual(h.data['weihnachtszentrale']['settings']['times']['morning_on']['twilight'],'astronomical')
        await env['ws_preview'](h,conn,{'id':2,'settings':config});self.assertFalse(errors);self.assertEqual(results[-1][1]['model_version'],'0.7.0')
        self.assertIn('T04:00',results[-1][1]['days'][0]['rules'][0]['at'])
    async def test_invalid_preview_and_unloaded(self):
        env=backend_scope();errors=[];conn=SimpleNamespace(send_error=lambda *a:errors.append(a))
        h=SimpleNamespace(data={});await env['ws_preview'](h,conn,{'id':1,'settings':settings()});self.assertEqual(errors[-1][1],'not_loaded')
        h.data['weihnachtszentrale']={};bad=settings();bad['times']['morning_on']['twilight']='wrong'
        await env['ws_preview'](h,conn,{'id':2,'settings':bad});self.assertEqual(errors[-1][1],'invalid_settings')

if __name__=='__main__':unittest.main()
