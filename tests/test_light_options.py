"""Opt-in turn-on options, capability loss and command policy."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from test_time_model import load, backend_scope, settings, Invalid
import test_engine

options = load('light_options')

class LightOptionsTests(unittest.TestCase):
 def test_old_settings_still_valid(self):
  self.assertNotIn('turn_on',backend_scope()['validate_settings'](settings())['devices'][0])
 def test_roundtrip_and_copy(self):
  s=settings();s['devices'][0]['turn_on']={'effect':'Christmas Tree','brightness_pct':50}
  clean=backend_scope()['validate_settings'](s);s['devices'][0]['turn_on']['brightness_pct']=10
  self.assertEqual(clean['devices'][0]['turn_on']['brightness_pct'],50)
 def test_reject_invalid_fields_and_values(self):
  for value in ({'brightness_pct':0},{'brightness_pct':True},{'transition':301},{'color_temp_kelvin':999},
                {'rgb_color':[1,2]},{'rgb_color':[1,2,300]},{'effect':''},{'effect':7},{'entity_id':'light.other'},
                {'effect':'x','rgb_color':[1,2,3]},[],None):
   with self.subTest(value=value),self.assertRaises(ValueError):options.validate_turn_on(value,'light.tree')
 def test_switch_only_on_off(self):
  with self.assertRaises(ValueError):options.validate_turn_on({'brightness_pct':50},'switch.test')
  self.assertEqual(options.validate_turn_on({},'switch.test'),{})
 def test_current_capabilities_validate(self):
  a={'supported_color_modes':['rgb','color_temp'],'supported_features':36,'effect_list':['Christmas Tree'],
     'min_color_temp_kelvin':2000,'max_color_temp_kelvin':9000}
  st=SimpleNamespace(attributes=a)
  for v in ({'effect':'Christmas Tree','brightness_pct':50},{'rgb_color':[1,2,3]},
            {'color_temp_kelvin':2000},{'transition':3}):
   self.assertEqual(options.supported_turn_on(v,'light.tree',st),v)
 def test_removed_capability_is_error(self):
  for v in ({'effect':'removed'},{'brightness_pct':50},{'rgb_color':[1,2,3]},{'color_temp_kelvin':2500},{'transition':3}):
   with self.subTest(value=v),self.assertRaises(ValueError):options.supported_turn_on(v,'light.tree',SimpleNamespace(attributes={}))
 def test_effect_list_and_temperature_limits_rechecked(self):
  st=SimpleNamespace(attributes={'supported_color_modes':['color_temp'],'supported_features':4,'effect_list':['other'],
      'min_color_temp_kelvin':2000,'max_color_temp_kelvin':6500})
  for v in ({'effect':'missing'},{'color_temp_kelvin':7000}):
   with self.assertRaises(ValueError):options.supported_turn_on(v,'light.tree',st)

class TurnOnEngineTests(test_engine.EngineTests):
 # Inherit only the harness; existing engine tests are discovered separately.
 async def test_options_on_only_once_even_when_already_on(self):
  self.actual['light.tree']=SimpleNamespace(state='on',attributes={'supported_color_modes':['rgb'],'supported_features':4,'effect_list':['Christmas Tree']})
  self.config['devices'][0]['turn_on']={'effect':'Christmas Tree','brightness_pct':40}
  self.at(17);await self.engine.enable(True);await self.engine.tick()
  self.assertEqual(len(self.calls),1);self.assertEqual(self.calls[0][2],{'entity_id':'light.tree','effect':'Christmas Tree','brightness_pct':40})
  self.at(23);await self.engine.tick();self.assertEqual(self.calls[-1][2],{'entity_id':'light.tree'})
 async def test_active_option_edit_applies_once(self):
  self.actual['light.tree'].attributes={'supported_color_modes':['brightness']}
  self.at(17);await self.engine.enable(True)
  self.config['devices'][0]['turn_on']={'brightness_pct':30}
  await self.engine.tick();await self.engine.tick();self.assertEqual(len(self.calls),2)
  replacement=self.make();await replacement.load();await replacement.tick();self.assertEqual(len(self.calls),2)
 async def test_bad_capability_does_not_block_off(self):
  self.config['devices'][0]['turn_on']={'effect':'missing'}
  self.at(17);await self.engine.enable(True);self.assertFalse(self.calls);self.assertIn('light.tree',self.engine.errors)
  self.actual['light.tree'].state='on';self.at(23);await self.engine.tick()
  self.assertEqual(self.calls[-1][1],'turn_off');self.assertFalse(self.engine.errors)
 async def test_inactive_option_edit_does_not_replay_phase(self):
  self.at(12);await self.engine.enable(True);self.config['devices'][0]['turn_on']={'brightness_pct':50}
  await self.engine.tick();self.assertFalse(self.calls)

# Avoid counting inherited tests twice; keep the shared setup and helpers.
for name in list(test_engine.EngineTests.__dict__):
 if name.startswith('test_') and name not in TurnOnEngineTests.__dict__:
  setattr(TurnOnEngineTests,name,None)
