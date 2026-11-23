"""Independent configuration saves and command-free field selection."""
import asyncio
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock
import unittest
from test_time_model import backend_scope,settings,Invalid
from test_engine import Store,module,solar,TZ
targets=module.targets
from datetime import datetime

class ConfigurationTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.env=backend_scope();self.config=settings();self.store=Store(self.config);self.tick=AsyncMock()
  self.runtime={'settings':deepcopy(self.config),'store':self.store,'lock':asyncio.Lock(),'engine':SimpleNamespace(_tick=self.tick)}
  self.hass=SimpleNamespace(data={'weihnachtszentrale':self.runtime});self.results=[];self.errors=[]
  self.conn=SimpleNamespace(send_result=lambda *x:self.results.append(x),send_error=lambda *x:self.errors.append(x))
 async def test_field_selection_does_not_apply_values(self):
  self.runtime['settings']['devices'][0]['turn_on']={'effect':'Christmas Tree'}
  before=targets(self.runtime['settings'],datetime(2026,11,22,17,tzinfo=TZ),'Europe/Berlin',solar)
  await self.env['ws_device_fields'](self.hass,self.conn,{'id':1,'entity_id':'light.tree','fields':['brightness_pct']})
  self.assertFalse(self.errors);self.tick.assert_not_awaited()
  self.assertEqual(self.store.saved['devices'][0]['turn_on'],{'effect':'Christmas Tree'})
  self.assertEqual(targets(self.runtime['settings'],datetime(2026,11,22,17,tzinfo=TZ),'Europe/Berlin',solar),before)
 async def test_selection_validates_conflicts_duplicates_and_types(self):
  for fields in (['effect','rgb_color'],['effect','effect'],['invalid'],[3]):
   await self.env['ws_device_fields'](self.hass,self.conn,{'id':1,'entity_id':'light.tree','fields':fields})
   self.assertTrue(self.errors);self.assertNotIn('fields',self.runtime['settings']['devices'][0])
 async def test_new_unsaved_device_rejected(self):
  await self.env['ws_device_fields'](self.hass,self.conn,{'id':1,'entity_id':'light.new','fields':[]})
  self.assertEqual(self.errors[-1][1],'device_not_saved');self.tick.assert_not_awaited()
 async def test_failed_selection_save_does_not_change_runtime(self):
  self.store.async_save=AsyncMock(side_effect=RuntimeError('storage'))
  with self.assertRaises(RuntimeError):await self.env['ws_device_fields'](self.hass,self.conn,{'id':1,'entity_id':'light.tree','fields':['effect']})
  self.assertNotIn('fields',self.runtime['settings']['devices'][0]);self.tick.assert_not_awaited()
 async def test_times_save_preserves_newer_devices_and_season(self):
  stale=settings();stale['times']['morning_on']['time']='07:15'
  self.runtime['settings']['devices'][0]['name']='New name';self.runtime['settings']['season']='reduced'
  await self.env['ws_save'](self.hass,self.conn,{'id':1,'settings':stale,'scope':'times'})
  self.assertEqual(self.store.saved['devices'][0]['name'],'New name');self.assertEqual(self.store.saved['season'],'reduced')
  self.assertEqual(self.store.saved['times']['morning_on']['time'],'07:15')
 async def test_device_save_preserves_newer_times_and_season(self):
  stale=settings();stale['devices'][0]['name']='New device name'
  self.runtime['settings']['times']['evening_off']['time']='23:00';self.runtime['settings']['season']='off'
  await self.env['ws_save'](self.hass,self.conn,{'id':1,'settings':stale,'scope':'devices'})
  self.assertEqual(self.store.saved['times']['evening_off']['time'],'23:00');self.assertEqual(self.store.saved['season'],'off')
 async def test_empty_fields_and_old_configuration_valid(self):
  self.env['validate_settings'](settings());s=settings();s['devices'][0]['fields']=[];self.env['validate_settings'](s)
 async def test_invalid_scope_does_not_save(self):
  await self.env['ws_save'](self.hass,self.conn,{'id':1,'settings':settings(),'scope':'bad'})
  self.assertTrue(self.errors);self.tick.assert_not_awaited()
