"""Control policy tests with simulated HA states, services, time and Store."""
import asyncio
from copy import deepcopy
from datetime import datetime
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from test_time_model import settings, solar, TZ

ROOT = Path(__file__).parents[1] / 'custom_components/weihnachtszentrale'
pkg = ModuleType('wz_engine_test'); pkg.__path__ = [str(ROOT)]; sys.modules[pkg.__name__] = pkg
spec = importlib.util.spec_from_file_location('wz_engine_test.engine', ROOT / 'engine.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
Engine = module.LightEngine

class Store:
    def __init__(self, saved=None): self.saved = deepcopy(saved)
    async def async_load(self): return deepcopy(self.saved)
    async def async_save(self, value): self.saved = deepcopy(value)

class EngineTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.config = settings()
        self.now = datetime(2026, 11, 22, 5, tzinfo=TZ)
        self.actual = {'light.tree': SimpleNamespace(state='off')}
        self.calls = []
        self.failure = False
        async def call(domain, action, data, blocking):
            self.calls.append((domain, action, data))
            if self.failure: raise RuntimeError('offline')
            self.actual[data['entity_id']].state = action.removeprefix('turn_')
        self.hass = SimpleNamespace(states=self.actual, config=SimpleNamespace(time_zone='Europe/Berlin'), services=SimpleNamespace(async_call=call))
        self.store = Store()
        self.engine = self.make()
        await self.engine.load()
    def make(self): return Engine(self.hass, lambda: self.config, self.store, solar, lambda: self.now)
    def at(self, hour, minute=0, day=22): self.now = datetime(2026, 11, day, hour, minute, tzinfo=TZ)
    async def test_upgrade_defaults_paused(self):
        await self.engine.tick(); self.assertFalse(self.calls); self.assertFalse(self.engine.status()['enabled'])
    async def test_schedule_and_no_repeat(self):
        await self.engine.enable(True); self.at(6); await self.engine.tick(); await self.engine.tick()
        self.at(9); await self.engine.tick()
        self.assertEqual([c[1] for c in self.calls], ['turn_on', 'turn_off'])
    async def test_manual_change_until_boundary(self):
        self.at(7); await self.engine.enable(True); self.actual['light.tree'].state='off'
        self.at(8); await self.engine.tick(); self.assertEqual(len(self.calls),1)
        self.at(9); await self.engine.tick(); self.at(16); await self.engine.tick()
        self.assertEqual([c[1] for c in self.calls],['turn_on','turn_on'])
    async def test_manual_on_during_gap_cleared_at_next_start_not_early(self):
        self.at(10); await self.engine.enable(True); self.actual['light.tree'].state='on'
        self.at(12); await self.engine.tick(); self.assertFalse(self.calls)
        self.at(16); await self.engine.tick(); self.at(22); await self.engine.tick()
        self.assertEqual(self.calls[-1][1],'turn_off')
    async def test_manual_override_survives_restart_same_phase(self):
        self.at(7); await self.engine.enable(True); self.actual['light.tree'].state='off'
        replacement=self.make(); await replacement.load(); await replacement.tick()
        self.assertEqual(len(self.calls),1)
    async def test_downtime_crossing_boundary_reconciles(self):
        self.at(7); await self.engine.enable(True); self.at(12)
        replacement=self.make(); await replacement.load(); await replacement.tick()
        self.assertEqual(self.calls[-1][1],'turn_off')
    async def test_midnight_does_not_cancel_manual_override(self):
        self.at(23); await self.engine.enable(True); self.actual['light.tree'].state='on'
        self.at(0,day=23); await self.engine.tick(); self.assertFalse(self.calls)
    async def test_mode_off_turns_participants_off(self):
        self.at(17); await self.engine.enable(True); self.config['season']='off'; await self.engine.tick()
        self.assertEqual(self.calls[-1][1],'turn_off')
    async def test_reduced_filters_full_devices(self):
        self.config['devices'][0]['season']='full'; self.config['season']='reduced'
        self.at(17); await self.engine.enable(True); self.assertFalse(self.calls)
        self.config['season']='full'; await self.engine.tick(); self.assertEqual(self.calls[-1][1],'turn_on')
    async def test_disabled_releases_device(self):
        self.at(17); await self.engine.enable(True); self.config['devices'][0]['enabled']=False
        self.at(23); await self.engine.tick(); self.assertEqual(len(self.calls),1)
    async def test_removed_releases_device(self):
        self.at(17); await self.engine.enable(True); self.config['devices']=[]
        self.at(23); await self.engine.tick(); self.assertEqual(len(self.calls),1)
    async def test_pause_no_commands_resume_current_plan(self):
        self.at(17); await self.engine.enable(True); await self.engine.enable(False)
        self.at(23); await self.engine.tick(); self.assertEqual(len(self.calls),1)
        await self.engine.enable(True); self.assertEqual(self.calls[-1][1],'turn_off')
    async def test_no_feedback_unknown_sends_once_and_survives_restart(self):
        self.config['devices'][0]['no_feedback']=True
        self.actual['light.tree'].state='unknown'
        async def transmit(domain, action, data, blocking):
            self.calls.append((domain,action,data))
        self.hass.services.async_call=transmit
        self.at(17); await self.engine.enable(True)
        for _ in range(4): await self.engine.tick()
        replacement=self.make(); await replacement.load(); await replacement.tick()
        self.assertEqual([c[1] for c in self.calls],['turn_on'])
        self.at(23); await replacement.tick(); await replacement.tick()
        self.assertEqual([c[1] for c in self.calls],['turn_on','turn_off'])
        self.assertFalse(replacement.errors)
    async def test_no_feedback_ignores_assumed_matching_state(self):
        self.config['devices'][0]['no_feedback']=True
        self.actual['light.tree'].state='on'
        self.at(17); await self.engine.enable(True)
        self.assertEqual(len(self.calls),1)
    async def test_no_feedback_unavailable_attempts_service(self):
        self.config['devices'][0]['no_feedback']=True
        self.actual['light.tree'].state='unavailable'
        self.at(17); await self.engine.enable(True)
        self.assertEqual(len(self.calls),1)
    async def test_no_feedback_missing_entity_stays_error(self):
        self.config['devices'][0]['no_feedback']=True
        self.actual.clear(); self.at(17); await self.engine.enable(True)
        self.assertFalse(self.calls); self.assertIn('light.tree',self.engine.errors)
    async def test_enable_no_feedback_reconciles_once(self):
        self.at(17); await self.engine.enable(True)
        self.config['devices'][0]['no_feedback']=True
        await self.engine.tick(); await self.engine.tick()
        self.assertEqual(len(self.calls),2)
    async def test_no_feedback_service_failure_is_not_completed(self):
        self.config['devices'][0]['no_feedback']=True
        self.failure=True; self.at(17); await self.engine.enable(True)
        self.assertIn('light.tree',self.engine.errors)
        self.failure=False; await self.engine.tick(); await self.engine.tick()
        self.assertEqual(len(self.calls),2); self.assertFalse(self.engine.errors)
    async def test_unavailable_retry_current_plan(self):
        self.at(17); self.actual['light.tree'].state='unavailable'; await self.engine.enable(True)
        self.assertIn('light.tree',self.engine.errors); self.assertFalse(self.calls)
        self.at(23); self.actual['light.tree'].state='on'; await self.engine.tick()
        self.assertEqual(self.calls[-1][1],'turn_off'); self.assertFalse(self.engine.errors)
    async def test_failure_retried_without_blocking_other_device(self):
        self.config['devices'].append({**self.config['devices'][0], 'id':'2','entity_id':'switch.other'})
        self.actual['switch.other']=SimpleNamespace(state='off')
        async def selective(domain, action, data, blocking):
            if data['entity_id']=='light.tree' and self.failure:
                raise RuntimeError('offline')
            self.calls.append((domain,action,data))
            self.actual[data['entity_id']].state=action.removeprefix('turn_')
        self.hass.services.async_call=selective
        self.at(17); self.failure=True; await self.engine.enable(True)
        self.assertIn('light.tree',self.engine.errors)
        self.assertEqual(self.actual['switch.other'].state,'on')
        self.failure=False; await self.engine.tick()
        self.assertEqual(len(self.calls),2); self.assertFalse(self.engine.errors)
    async def test_two_devices_independent_profiles(self):
        self.config['devices'].append({**self.config['devices'][0], 'id':'2','entity_id':'switch.other','profile':'evening'})
        self.actual['switch.other']=SimpleNamespace(state='off'); self.at(7); await self.engine.enable(True)
        self.assertEqual(len(self.calls),1); self.at(17); await self.engine.tick()
        self.assertEqual(self.calls[-1][0],'switch'); self.assertEqual(self.calls[-1][2]['entity_id'],'switch.other')
    async def test_invalid_evening_no_on(self):
        self.config['times']['evening_off']['time']='02:00'; self.at(17); await self.engine.enable(True)
        self.assertFalse(self.calls)
    async def test_no_repeat_for_unreliable_state_report(self):
        self.at(17); await self.engine.enable(True); self.actual['light.tree'].state='off'
        await self.engine.tick(); self.assertEqual(len(self.calls),1)
    async def test_saved_time_edit_applies_immediately(self):
        self.at(17); await self.engine.enable(True); self.config['times']['evening_on']['time']='18:00'
        await self.engine.tick(); self.assertEqual(self.calls[-1][1],'turn_off')
    async def test_stopped_cannot_switch(self):
        await self.engine.enable(True); await self.engine.stop(); self.at(17); await self.engine.tick()
        self.assertFalse(self.calls)
    async def test_only_configured_ids_no_cover_calls(self):
        self.config['devices'][0]['cover']='cover.livingroom'; self.at(17); await self.engine.enable(True)
        self.assertEqual(self.calls,[('light','turn_on',{'entity_id':'light.tree'})])
    async def test_concurrent_ticks_not_duplicate(self):
        await self.engine.enable(True); self.at(17)
        await asyncio.gather(self.engine.tick(),self.engine.tick(),self.engine.tick())
        self.assertEqual(len(self.calls),1)

if __name__=='__main__': unittest.main()

class BackendLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_startup_waits_unload_stops_and_ws_controls(self):
        from test_time_model import backend_scope
        from unittest.mock import AsyncMock
        env=backend_scope(); config=settings(); callbacks={}; cancelled=[]; calls=[]
        class RuntimeStore(Store):
            def __init__(self,hass,version,key):
                super().__init__(config if key.endswith('.settings') else {'enabled':True,'phases':{}})
        env['Store']=RuntimeStore
        def track(hass, callback, interval):
            callbacks['timer']=callback
            self.assertEqual(interval.total_seconds(),15)
            return lambda:cancelled.append('timer')
        def listen(event, callback):
            callbacks['start']=callback
            return lambda:cancelled.append('start')
        async def call(*args,**kwargs):calls.append(args)
        env['async_track_time_interval']=track
        h=SimpleNamespace(data={},is_running=False,config=SimpleNamespace(time_zone='Europe/Berlin'),
            config_entries=SimpleNamespace(async_forward_entry_setups=AsyncMock(),async_unload_platforms=AsyncMock(return_value=True)),
            bus=SimpleNamespace(async_listen_once=listen,async_listen=lambda *args:lambda:cancelled.append('manual')),states={'light.tree':SimpleNamespace(state='on')},
            services=SimpleNamespace(async_call=call))
        await env['async_setup_entry'](h,object()); await callbacks['timer'](None)
        self.assertFalse(calls)
        h.is_running=True; await callbacks['start'](None)
        self.assertEqual(calls[0][1],'turn_off')
        result=[];conn=SimpleNamespace(send_result=lambda *x:result.append(x),send_error=lambda *x:None)
        await env['ws_enable'](h,conn,{'id':1,'enabled':False})
        self.assertFalse(result[-1][1]['enabled'])
        await env['ws_engine'](h,conn,{'id':2});self.assertEqual(result[-1][1]['model_version'],'0.7.1')
        await env['async_unload_entry'](h,object());self.assertEqual(set(cancelled),{'timer','start','manual'})
        await callbacks['timer'](None);self.assertEqual(len(calls),1)
