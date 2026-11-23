"""Cover policy with simulated HA; no real movement performed."""
import importlib.util
from copy import deepcopy
from datetime import datetime,timedelta
from pathlib import Path
from types import SimpleNamespace,ModuleType
import sys
import unittest
from test_time_model import settings,solar,TZ
from test_engine import Engine,Store

ROOT=Path(__file__).parents[1]/'custom_components/weihnachtszentrale'
pkg=ModuleType('wz_cover_test');pkg.__path__=[str(ROOT)];sys.modules[pkg.__name__]=pkg
spec=importlib.util.spec_from_file_location('wz_cover_test.covers',ROOT/'covers.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);Coordinator=m.CoverCoordinator

def state(value,position=None,changed=None):
 return SimpleNamespace(state=value,attributes={} if position is None else {'current_position':position},last_changed=changed)

class CoverTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.config=settings();self.config['devices'][0]['cover']='cover.window'
  self.now=datetime(2026,11,22,17,tzinfo=TZ);self.calls=[];self.response={'status':'success'};self.fail=False
  self.states={'light.tree':state('on',changed=self.now-timedelta(hours=1)), 'cover.window':state('open',100)}
  async def call(domain,action,data,**kwargs):
   self.calls.append((domain,action,data))
   if self.fail:raise RuntimeError('test failure')
   return deepcopy(self.response)
  self.hass=SimpleNamespace(config=SimpleNamespace(time_zone='Europe/Berlin'),states=self.states,services=SimpleNamespace(async_call=call))
  self.engine=Engine(self.hass,lambda:self.config,Store(),solar,lambda:self.now)
  self.engine.state={'enabled':True,'phases':{}}
  self.store=Store();self.coord=Coordinator(self.hass,self.engine,self.store,lambda:self.now)
  self.engine.covers=self.coord
  self.coord.options["enabled"]=True
 async def request(self,position=0,script=''):await self.coord.request('cover.window',position,script)
 async def test_on_light_defers_then_manual_off_releases(self):
  await self.request();self.assertFalse(self.calls);self.assertIn('cover.window',self.coord.pending)
  self.states['light.tree']=state('off');await self.coord.process()
  self.assertEqual(self.calls,[('cover','close_cover',{'entity_id':'cover.window'})]);self.assertFalse(self.coord.pending)
 async def test_two_lights_last_off_releases(self):
  self.config['devices'].append({**self.config['devices'][0],'id':'2','entity_id':'light.other'})
  self.states['light.other']=state('on');await self.request();self.states['light.tree']=state('off')
  await self.coord.process();self.assertFalse(self.calls)
  self.states['light.other']=state('off');await self.coord.process();self.assertEqual(len(self.calls),1)
 async def test_unassociated_cover_passes(self):
  self.config['devices'][0]['cover']='cover.other';await self.request();self.assertEqual(len(self.calls),1)
 async def test_disabled_and_reduced_excluded(self):
  for update in ({'enabled':False},{'enabled':True,'season':'full'}):
   self.calls.clear();self.config['season']='reduced';self.config['devices'][0].update(update)
   await self.request();self.assertEqual(len(self.calls),1)
 async def test_manual_evening_on_holds_even_for_morning_profile(self):
  self.config['devices'][0]['profile']='morning';await self.request();self.assertFalse(self.calls)
 async def test_request_never_opens_even_in_morning(self):
  self.now=self.now.replace(hour=8);await self.request();self.assertFalse(self.calls)
 async def test_original_partial_target_preserved(self):
  self.states['light.tree']=state('off');await self.request(position=30)
  self.assertEqual(self.calls,[('cover','set_cover_position',{'entity_id':'cover.window','position':30})])
 async def test_partial_close_never_opens_more_closed_cover(self):
  self.states['light.tree']=state('off');self.states['cover.window']=state('open',20)
  await self.request(position=70);self.assertFalse(self.calls)
 async def test_partial_unknown_position_does_not_move(self):
  self.states['light.tree']=state('off');self.states['cover.window']=state('open')
  await self.request(position=30);self.assertFalse(self.calls);self.assertEqual(self.coord.pending['cover.window']['status'],'review')
 async def test_expiry_no_stale_morning_close(self):
  await self.request();self.now=self.now+timedelta(hours=14);self.states['light.tree']=state('off')
  await self.coord.process();self.assertFalse(self.calls);self.assertFalse(self.coord.pending)
 async def test_manual_partial_movement_keeps_close_request(self):
  await self.request();self.states['cover.window']=state('open',80);await self.coord.process()
  self.assertFalse(self.calls);self.assertIn('cover.window',self.coord.pending)
  self.states['light.tree']=state('off');await self.coord.process();await self.coord.process()
  self.assertEqual(self.calls,[('cover','close_cover',{'entity_id':'cover.window'})])
 async def test_partial_target_after_manual_movement_and_restart(self):
  await self.request(position=30);self.states['cover.window']=state('open',60)
  await self.coord.process();new=Coordinator(self.hass,self.engine,self.store,lambda:self.now);await new.load()
  await new.process();self.assertFalse(self.calls)
  self.states['light.tree']=state('off');await new.process()
  self.assertEqual(self.calls,[('cover','set_cover_position',{'entity_id':'cover.window','position':30})])
 async def test_manual_further_closed_target_does_not_open(self):
  await self.request(position=30);self.states['cover.window']=state('open',10)
  await self.coord.process();self.assertIn('cover.window',self.coord.pending)
  self.states['light.tree']=state('off');await self.coord.process()
  self.assertFalse(self.calls);self.assertFalse(self.coord.pending)
 async def test_manual_reopening_keeps_close_request(self):
  self.states['cover.window']=state('open',50);await self.request()
  self.states['cover.window']=state('open',100);await self.coord.process()
  self.assertIn('cover.window',self.coord.pending);self.assertFalse(self.calls)
  self.states['light.tree']=state('off');await self.coord.process();self.assertEqual(len(self.calls),1)
 async def test_explicit_cancel_does_not_move(self):
  await self.request();await self.coord.cancel('cover.window');self.states['light.tree']=state('off')
  await self.coord.process();self.assertFalse(self.calls)
 async def test_persistence_restores_waiting_request(self):
  await self.request();new=Coordinator(self.hass,self.engine,self.store,lambda:self.now);await new.load()
  await new.process();self.assertFalse(self.calls);self.states['light.tree']=state('off');await new.process()
  self.assertEqual(len(self.calls),1)
 async def test_restart_during_dispatch_requires_review(self):
  await self.request();self.coord.pending['cover.window']['status']='dispatching';await self.coord.save()
  new=Coordinator(self.hass,self.engine,self.store,lambda:self.now);await new.load();self.states['light.tree']=state('off')
  await new.process();self.assertFalse(self.calls);self.assertEqual(new.pending['cover.window']['status'],'review')
 async def test_script_success_uses_only_existing_script(self):
  self.states['light.tree']=state('off');await self.request(script='script.safe_close')
  self.assertEqual(self.calls,[('script','safe_close',{})]);self.assertFalse(self.coord.pending)
 async def test_script_blocked_timeout_no_bypass_or_repeated_movement(self):
  self.states['light.tree']=state('off')
  for result in ('blocked','timeout'):
   self.response={'status':result};self.calls.clear();await self.request(script='script.safe_close')
   await self.coord.process();self.assertEqual(len(self.calls),1)
   self.assertEqual(self.coord.pending['cover.window']['status'],'review')
 async def test_script_nested_response_supported(self):
  self.states['light.tree']=state('off');self.response={'rollladen_ergebnis':{'status':'success'}}
  await self.request(script='script.safe_close');self.assertFalse(self.coord.pending)
 async def test_failure_not_repeated_automatically(self):
  self.states['light.tree']=state('off');self.fail=True;await self.request();await self.coord.process()
  self.assertEqual(len(self.calls),1);self.assertEqual(self.coord.pending['cover.window']['status'],'review')
 async def test_pause_does_not_replay_pending_but_new_request_passes(self):
  await self.request();self.engine.state['enabled']=False;self.states['light.tree']=state('off')
  await self.coord.process();self.assertFalse(self.calls)
  await self.request();self.assertEqual(len(self.calls),1)
 async def test_unknown_light_holds_unless_off_sent(self):
  self.states['light.tree']=state('unavailable');await self.request();self.assertFalse(self.calls)
  self.engine.state['off_releases']={'light.tree':self.now.isoformat()};await self.coord.process()
  self.assertEqual(len(self.calls),1)
 async def test_sent_off_releases_stale_on_report_after_light_call(self):
  await self.request();self.now=self.now.replace(hour=22);await self.engine.tick()
  self.assertEqual([x[:2] for x in self.calls],[('light','turn_off'),('cover','close_cover')])
 async def test_new_manual_on_after_off_release_blocks(self):
  self.engine.state['off_releases']={'light.tree':(self.now-timedelta(minutes=1)).isoformat()}
  self.states['light.tree']=state('on',changed=self.now);await self.request();self.assertFalse(self.calls)
 async def test_failed_light_off_does_not_bypass_independent_script(self):
  await self.request(script='script.safe_close');self.now=self.now.replace(hour=22)
  self.fail=True;await self.engine.tick()
  self.assertEqual([x[0] for x in self.calls],['light','script'])
  self.assertEqual(self.coord.pending['cover.window']['status'],'review')
 async def test_closed_cover_no_command(self):
  self.states['cover.window']=state('closed',0);self.states['light.tree']=state('off')
  await self.request();self.assertFalse(self.calls)
 async def test_unavailable_cover_retries_while_valid(self):
  self.states['cover.window']=state('unavailable');self.states['light.tree']=state('off')
  await self.request();self.assertFalse(self.calls);self.states['cover.window']=state('open',100)
  await self.coord.process();self.assertEqual(len(self.calls),1)
 async def test_no_request_no_cover_movement(self):
  self.now=self.now.replace(hour=22);await self.engine.tick()
  self.assertTrue(all(x[0]=='light' for x in self.calls))

if __name__=='__main__':unittest.main()

class ServiceRoutingTests(unittest.IsolatedAsyncioTestCase):
 async def test_registered_action_routes_original_target_and_cancel(self):
  import ast,asyncio
  from unittest.mock import AsyncMock
  tree=ast.parse((ROOT/'services.py').read_text())
  fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='async_setup_services');fn.decorator_list=[]
  class Marker:
   def __init__(self,value,**kwargs): self.value=value
  vol=SimpleNamespace(Required=Marker,Optional=Marker,All=lambda *args:None,Range=lambda **kwargs:None,Match=lambda *args:None,Schema=lambda value:value)
  error=type('HAError',(Exception,),{})
  scope={'vol':vol,'COVER':None,'DOMAIN':'weihnachtszentrale','HomeAssistantError':error}
  exec(compile(ast.Module(body=[fn],type_ignores=[]),str(ROOT/'services.py'),'exec'),scope)
  registered={};coord=SimpleNamespace(request=AsyncMock(),cancel=AsyncMock())
  hass=SimpleNamespace(data={'weihnachtszentrale':{'lock':asyncio.Lock(),'covers':coord}},
   services=SimpleNamespace(async_register=lambda domain,name,handler,**kwargs:registered.update({name:handler})))
  scope['async_setup_services'](hass)
  await registered['request_cover_close'](SimpleNamespace(data={'cover_entity':'cover.test','position':30,'source':'Evening'}))
  coord.request.assert_awaited_once_with('cover.test',30,'','Evening')
  await registered['cancel_cover_close'](SimpleNamespace(data={'cover_entity':'cover.test'}));coord.cancel.assert_awaited_once_with('cover.test')
  with self.assertRaises(error):
   await registered['request_cover_close'](SimpleNamespace(data={'cover_entity':'cover.test','position':30,'safety_script':'script.safe','source':'Evening'}))
  hass.data.clear()
  with self.assertRaises(error):
   await registered['cancel_cover_close'](SimpleNamespace(data={'cover_entity':'cover.test'}))

class CoverOptionTests(unittest.IsolatedAsyncioTestCase):
 async def test_default_disabled_and_configurable_expiry(self):
  config=settings();now=datetime(2026,11,23,18,tzinfo=TZ);calls=[]
  async def call(*args,**kwargs):calls.append(args)
  hass=SimpleNamespace(config=SimpleNamespace(time_zone='Europe/Berlin'),states={'cover.test':state('open',100)},services=SimpleNamespace(async_call=call))
  engine=Engine(hass,lambda:config,Store(),solar,lambda:now);engine.state['enabled']=True
  coordinator=Coordinator(hass,engine,Store(),lambda:now)
  self.assertFalse(coordinator.options['enabled'])
  await coordinator.request('cover.test');self.assertEqual(calls[0][1],'close_cover')
  await coordinator.update_options({'enabled':True,'expiry':'07:45'})
  config['devices'][0]['cover']='cover.test';hass.states['light.tree']=state('on')
  await coordinator.request('cover.test')
  self.assertIn('T07:45',coordinator.pending['cover.test']['expires_at'])
  calls.clear();await coordinator.update_options({'enabled':False,'expiry':'07:45'})
  self.assertFalse(coordinator.pending);self.assertFalse(calls)
 def test_invalid_options_rejected(self):
  for value in ({'enabled':True,'expiry':'25:00'},{'enabled':'yes','expiry':'06:00'},{'enabled':False}):
   with self.assertRaises(ValueError):Coordinator.validate_options(value)

class CoverOptionsCommandTests(unittest.IsolatedAsyncioTestCase):
 async def test_actual_get_save_and_invalid_options(self):
  import ast,asyncio
  from copy import deepcopy
  tree=ast.parse((ROOT/'__init__.py').read_text())
  node=next(x for x in tree.body if isinstance(x,ast.AsyncFunctionDef) and x.name=='ws_cover_options');node.decorator_list=[]
  env={'DOMAIN':'weihnachtszentrale','deepcopy':deepcopy}
  exec(compile(ast.Module(body=[node],type_ignores=[]),str(ROOT/'__init__.py'),'exec'),env)
  config=settings();now=datetime(2026,11,23,18,tzinfo=TZ)
  hass=SimpleNamespace(data={});engine=SimpleNamespace(settings=lambda:config)
  covers=Coordinator(hass,engine,Store(),lambda:now)
  hass.data['weihnachtszentrale']={'covers':covers,'lock':asyncio.Lock()}
  results=[];errors=[];conn=SimpleNamespace(send_result=lambda *x:results.append(x),send_error=lambda *x:errors.append(x))
  await env['ws_cover_options'](hass,conn,{'id':1});self.assertFalse(results[-1][1]['options']['enabled'])
  await env['ws_cover_options'](hass,conn,{'id':2,'options':{'enabled':True,'expiry':'08:00'}})
  self.assertTrue(results[-1][1]['options']['enabled'])
  await env['ws_cover_options'](hass,conn,{'id':3,'options':{'enabled':True,'expiry':'99:00'}})
  self.assertEqual(errors[-1][1],'invalid_settings')
  hass.data.clear();await env['ws_cover_options'](hass,conn,{'id':4});self.assertEqual(errors[-1][1],'not_loaded')
