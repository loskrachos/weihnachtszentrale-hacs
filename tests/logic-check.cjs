const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Element {
constructor(tag){this.tag=tag;this.children=[];this.handlers={};this.value='';}
append(...children){this.children.push(...children)}
addEventListener(name,fn){const old=this.handlers[name];this.handlers[name]=()=>{if(old)old();return fn()}}
querySelector(selector){return all(this,e=>selector.startsWith('.')&&e.className===selector.slice(1))[0]||null}
replaceChildren(...children){this.children=children}
set innerHTML(v){this.html=v;this.children=[]}
attachShadow(){return new Element('shadow')}
}
let Card;
vm.runInNewContext(fs.readFileSync(__dirname+'/../custom_components/weihnachtszentrale/frontend/weihnachtszentrale-card-v070.js','utf8'),{HTMLElement:Element,document:{createElement:t=>new Element(t)},customElements:{define:(n,c)=>Card=c},window:{},crypto:{randomUUID:()=> 'new-id'},alert:()=>{}});
const all=(e,p)=>[...(p(e)?[e]:[]),...e.children.flatMap(c=>all(c,p))];
(async()=>{
const time={event:'fixed',time:'06:30',offset:0};
const data={season:'full',times:Object.fromEntries(['morning_on','morning_off','evening_on','evening_off'].map(k=>[k,{...time}])),devices:[{id:'1',entity_id:'light.tree',name:'Baum',profile:'both',season:'full',cover:'',enabled:true}]};
const calls=[];const c=new Card();c.setConfig({view:'configuration'});c.config={view:'configuration'};c._root=new Element('shadow');c._hass={states:{'light.tree':{attributes:{friendly_name:'Baum'}},'switch.star':{attributes:{friendly_name:'Stern'}},'cover.window':{attributes:{}}},connection:{sendMessagePromise:async m=>{calls.push(structuredClone(m));return structuredClone(data)}}};
await c._load();
const find=p=>all(c._root,p),button=t=>find(x=>x.tag==='button'&&x.textContent===t)[0];
const change=(e,v)=>{e.value=v;e.handlers.change()};
change(find(x=>x.type==='time')[0],'07:45');change(find(x=>x.type==='number')[0],'-20');change(find(x=>x.tag==='select')[0],'reduced');
const check=find(x=>x.type==='checkbox')[0];check.checked=false;check.handlers.change();
const selects=find(x=>x.tag==='select');change(selects.at(-1),'switch.star');button('Gerät hinzufügen').handlers.click();
await button('Einstellungen speichern').handlers.click();
const saved=calls.find(x=>x.type==='weihnachtszentrale/save').settings;
assert.equal(saved.times.morning_on.time,'07:45');assert.equal(saved.times.morning_on.offset,-20);assert.equal(saved.season,'reduced');assert.equal(saved.devices.length,2);assert.equal(saved.devices[0].enabled,false);
button('Entfernen').handlers.click();assert.equal(c.settings.devices.length,1);
await c._load();assert.equal(c.settings.season,'full');
c._hass.connection.sendMessagePromise=async()=>{throw Error('Testfehler')};await c._load();assert.equal(c.error,'Testfehler');
// Preview uses unsaved values and does not save; stale requests are ignored.
const payload={model_version:'0.7.0',timezone:'Europe/Berlin',days:[{date:'2026-10-29',rules:[{key:'morning_on',at:'2026-10-29T06:30:00+01:00',warning:null}],warnings:[]}],devices:[]};
c._hass.connection.sendMessagePromise=async m=>{calls.push(structuredClone(m));return payload};
c.error='';c.render();const panel=c._root.querySelector('.preview');const previewButton=button('Vorschau berechnen');
await c._calculatePreview(panel,previewButton);assert.equal(c.preview,payload);assert.equal(calls.at(-1).type,'weihnachtszentrale/preview');assert.equal(calls.at(-1).settings.season,'full');
c._invalidatePreview();assert.equal(c.preview,null);
let finish;c._hass.connection.sendMessagePromise=()=>new Promise(r=>finish=r);
const pending=c._calculatePreview(panel,previewButton);c._invalidatePreview();finish(payload);await pending;assert.equal(c.preview,null);assert.equal(previewButton.disabled,false);
c._hass.connection.sendMessagePromise=async()=>{throw Error('Preview error')};await c._calculatePreview(panel,previewButton);assert.equal(panel.children[0].textContent,'Preview error');
assert.equal(c.getGridOptions().columns,'full');assert.equal(c.getGridOptions().rows,'auto');
assert(c._root.html.includes('width:100%'));assert(c._root.html.includes('repeat(4,minmax(0,1fr))'));assert(c._root.html.includes('@container (max-width:599px)'));
console.log('PASS: JS parsing; load, time, offset, season, checkbox, add, save, remove, reload, error rendering; full-width sizing API and responsive CSS present. Preview request, rendering, invalidation, stale response and error handling passed. Layout not browser-verified.');
})().catch(e=>{console.error(e);process.exit(1)});
