"""Automatic resource migration against the HA2026.11.2 collection contract."""
import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import unittest
from urllib.parse import urlsplit

ROOT=Path(__file__).parents[1]
COMPONENT=ROOT/'custom_components/weihnachtszentrale'

def scope():
 tree=ast.parse((COMPONENT/'frontend.py').read_text())
 env={'Path':Path,'urlsplit':urlsplit,'StaticPathConfig':lambda *args:args,
      '__file__':str(COMPONENT/'frontend.py'),'LOVELACE_DATA':'lovelace',
      'HomeAssistantError':RuntimeError,'DOMAIN':'weihnachtszentrale','VERSION':'0.7.2'}
 nodes=[n for n in tree.body if isinstance(n,(ast.Assign,ast.FunctionDef,ast.AsyncFunctionDef))]
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(COMPONENT/'frontend.py'),'exec'),env)
 return env

class Resources:
 def __init__(self,items):self.items=items;self.loaded=False;self.loads=0
 async def async_load(self):self.loads+=1
 def async_items(self):return list(self.items)
 async def async_update_item(self,item_id,updates):
  for item in self.items:
   if item['id']==item_id:item.update(url=updates['url'],type=updates['res_type'])
 async def async_delete_item(self,item_id):self.items=[x for x in self.items if x['id']!=item_id]
 async def async_create_item(self,item):self.items.append({'id':'new','url':item['url'],'type':item['res_type']})

class FrontendTests(unittest.IsolatedAsyncioTestCase):
 async def test_migrate_old_version_and_duplicate_only(self):
  env=scope();foreign={'id':'foreign','url':'/local/other.js','type':'module'}
  collection=Resources([{'id':'old','url':'/local/weihnachtszentrale-card-v061.js?v=1','type':'module'},
    foreign,{'id':'dup','url':'/local/weihnachtszentrale-card.js?v=2','type':'module'}])
  h=SimpleNamespace(data={'lovelace':SimpleNamespace(resource_mode='storage',resources=collection)},http=SimpleNamespace(async_register_static_paths=AsyncMock()))
  await env['async_setup_frontend'](h);await env['async_setup_frontend'](h)
  self.assertEqual(collection.loads,1);self.assertEqual(len(collection.items),2)
  self.assertEqual(collection.items[0]['id'],'old');self.assertEqual(collection.items[0]['url'],env['RESOURCE_URL'])
  self.assertIn(foreign,collection.items);self.assertEqual(h.http.async_register_static_paths.await_count,1)
 async def test_first_install_creates_one_module(self):
  env=scope();collection=Resources([])
  h=SimpleNamespace(data={'lovelace':SimpleNamespace(resource_mode='storage',resources=collection)},http=SimpleNamespace(async_register_static_paths=AsyncMock()))
  await env['async_setup_frontend'](h);self.assertEqual(len(collection.items),1);self.assertEqual(collection.items[0]['type'],'module')
 async def test_do_not_claim_remote_or_similar_names(self):
  owns=scope()['owned_resource']
  for url in ('https://example.com/local/weihnachtszentrale-card-v061.js','/local/weihnachtszentrale-card-v061-other.js','/local/other-card.js','/local/weihnachtszentrale-card-v.js'):
   self.assertFalse(owns(url))
 async def test_yaml_resources_not_silently_overwritten(self):
  env=scope();h=SimpleNamespace(data={'lovelace':SimpleNamespace(resource_mode='yaml')},http=SimpleNamespace(async_register_static_paths=AsyncMock()))
  with self.assertRaises(RuntimeError):await env['async_setup_frontend'](h)
 def test_all_runtime_assets_in_component(self):
  import json
  manifest=json.loads((COMPONENT/'manifest.json').read_text())
  self.assertEqual(manifest['version'],'0.7.2')
  self.assertTrue((COMPONENT/'frontend/weihnachtszentrale-card-v072.js').is_file())
  self.assertTrue((ROOT/'hacs.json').is_file())
  self.assertIn('frontend',manifest['dependencies'])

if __name__=='__main__':unittest.main()
