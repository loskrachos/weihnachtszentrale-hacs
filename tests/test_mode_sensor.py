"""Native mode entity behavior with simulated HA entity/dispatcher interfaces."""
import ast
import asyncio
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock
from test_time_model import backend_scope, settings

ROOT=Path(__file__).parents[1]/'custom_components/weihnachtszentrale'

class FakeBinarySensor:
 async def async_added_to_hass(self):pass
 def async_on_remove(self,fn):self.remove_callback=fn
 def async_write_ha_state(self):self.written=self.is_on

def load_sensor(listeners):
 def connect(hass,signal,callback):
  listeners.append(callback)
  return lambda:listeners.remove(callback)
 scope={'BinarySensorEntity':FakeBinarySensor,'callback':lambda fn:fn,
        'async_dispatcher_connect':connect,'DOMAIN':'weihnachtszentrale',
        'SIGNAL_SETTINGS_CHANGED':'weihnachtszentrale_settings_changed'}
 tree=ast.parse((ROOT/'binary_sensor.py').read_text())
 nodes=[x for x in tree.body if isinstance(x,(ast.ClassDef,ast.AsyncFunctionDef))]
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(ROOT/'binary_sensor.py'),'exec'),scope)
 return scope

class ModeEntityTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.listeners=[];self.scope=load_sensor(self.listeners)
  self.hass=SimpleNamespace(data={'weihnachtszentrale':{'settings':settings()}})
  self.entity=self.scope['ChristmasModeActive'](self.hass)
 async def test_three_seasons_and_pause_independence(self):
  for season,expected in [('off',False),('reduced',True),('full',True)]:
   self.hass.data['weihnachtszentrale']['settings']['season']=season
   self.hass.data['weihnachtszentrale']['engine']=SimpleNamespace(state={'enabled':False})
   self.assertEqual(self.entity.is_on,expected)
   self.assertEqual(self.entity.extra_state_attributes['season'],season)
 async def test_no_polling_and_stable_unique_id(self):
  self.assertFalse(self.entity._attr_should_poll)
  self.assertEqual(self.entity._attr_unique_id,'weihnachtszentrale_season_active')
 async def test_unloaded_entity_unavailable_not_false_off(self):
  self.hass.data.clear();self.assertFalse(self.entity.available);self.assertIsNone(self.entity.is_on)
 async def test_setup_adds_single_entity_and_listener_cleans_up(self):
  added=[];await self.scope['async_setup_entry'](self.hass,None,added.extend)
  self.assertEqual(len(added),1);await self.entity.async_added_to_hass()
  self.assertEqual(len(self.listeners),1)
  self.entity.remove_callback();self.assertFalse(self.listeners)
 async def test_dashboard_save_immediately_updates_native_entity(self):
  await self.entity.async_added_to_hass()
  env=backend_scope();saved=[]
  async def save(value):saved.append(deepcopy(value))
  runtime=self.hass.data['weihnachtszentrale'];runtime.update(store=SimpleNamespace(async_save=save),lock=asyncio.Lock())
  def dispatch(hass,signal):
   self.assertEqual(signal,'weihnachtszentrale_settings_changed')
   for listener in self.listeners:listener()
  env['async_dispatcher_send']=dispatch
  results=[];conn=SimpleNamespace(send_result=lambda *args:results.append(args),send_error=lambda *args:self.fail(str(args)))
  new=settings();new['season']='off';await env['ws_save'](self.hass,conn,{'id':1,'settings':new})
  self.assertFalse(self.entity.written)
  new['season']='reduced';await env['ws_save'](self.hass,conn,{'id':2,'settings':new})
  self.assertTrue(self.entity.written);self.assertEqual(saved[-1]['season'],'reduced')
 async def test_failed_save_does_not_publish_new_mode(self):
  env=backend_scope();runtime=self.hass.data['weihnachtszentrale']
  runtime.update(store=SimpleNamespace(async_save=AsyncMock(side_effect=OSError('disk'))),lock=asyncio.Lock())
  sent=[];env['async_dispatcher_send']=lambda *args:sent.append(args)
  new=settings();new['season']='off'
  with self.assertRaises(OSError):await env['ws_save'](self.hass,None,{'id':1,'settings':new})
  self.assertFalse(sent);self.assertEqual(runtime['settings']['season'],'full')
 async def test_platform_unload_failure_keeps_runtime(self):
  env=backend_scope();self.hass.config_entries=SimpleNamespace(async_unload_platforms=AsyncMock(return_value=False))
  self.assertFalse(await env['async_unload_entry'](self.hass,None))
  self.assertIn('weihnachtszentrale',self.hass.data)

if __name__=='__main__':unittest.main()
