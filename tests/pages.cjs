let timerFn;
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
vm.runInNewContext(fs.readFileSync(__dirname+'/../custom_components/weihnachtszentrale/frontend/weihnachtszentrale-card-v072.js','utf8'),{HTMLElement:Element,document:{createElement:t=>new Element(t)},customElements:{define:(n,c)=>Card=c},window:{},crypto:{randomUUID:()=> 'new-id'},alert:()=>{},setInterval:(fn,ms)=>{timerFn=fn;return 1},clearInterval:()=>{timerFn=null}});
const all=(e,p)=>[...(p(e)?[e]:[]),...e.children.flatMap(c=>all(c,p))];
(async()=>{
const c=new Card();c._root=new Element('shadow');c._hass={states:{'light.tree':{state:'on',attributes:{}}}};
const t={event:'fixed',time:'06:00',offset:0,twilight:'civil'};const settings={season:'full',devices:[{id:'1',entity_id:'light.tree',name:'Baum',enabled:true,profile:'both',season:'both',cover:''}],times:Object.fromEntries(['morning_on','morning_off','evening_on','evening_off'].map(k=>[k,{...t}]))};c.settings=structuredClone(settings);
const allText=()=>all(c._root,e=>!!e.textContent).map(e=>e.textContent).join(' ');
const groups=Array.from({length:6},(_,i)=>({at:'2026-10-30T'+String(i+6).padStart(2,'0')+':00:00+01:00',on:[{entity_id:'light.tree',name:'Baum',cover:''}],off:[]}));
const data={model_version:'0.7.2',generated_at:'2026-10-30T05:00:00+01:00',until:'2026-10-31T05:00:00+01:00',timezone:'Europe/Berlin',actions:groups,warnings:[]};
c.setConfig({view:'overview'});c.render();c._actions=data;c._showActions(c._root.querySelector('.action-list'));
assert.equal(all(c._root,e=>e.className==='entry').length,4);assert(allText().includes('Baum'));assert(allText().includes('light.tree'));assert(!allText().includes('Zentrale Zeiten'));assert(allText().includes('Baum: An'));assert.equal(all(c._root,e=>e.tag==='a').length,0);
c.setConfig({view:'actions'});c.render();c._actions=data;c._showActions(c._root.querySelector('.action-list'));assert.equal(all(c._root,e=>e.className==='entry').length,6);assert(!allText().includes('Modus speichern'));
c._actions={...data,actions:[]};c._showActions(c._root.querySelector('.action-list'));assert(allText().includes('Keine weiteren Aktionen geplant'));
c.setConfig({view:'configuration'});c.render();assert(allText().includes('Zentrale Zeiten'));assert(!allText().includes('Nächste vier Aktionen'));
const feedbackField=all(c._root,e=>e.children.some(x=>x.textContent==='Keine Zustandsrückmeldung (z. B. 433 MHz)'))[0];
const feedbackBox=all(feedbackField,e=>e.type==='checkbox')[0];assert(feedbackBox);feedbackBox.checked=true;feedbackBox.handlers.change();assert.equal(c.settings.devices[0].no_feedback,true);
c.setConfig({view:'overview'});c.render();assert(allText().includes('Ohne Zustandsrückmeldung'));assert(!allText().includes('Baum: An'));
c.settings=structuredClone(settings);c.setConfig({view:'configuration'});c.render();
const morning=c._eventOptions('morning_on','fixed').map(x=>x[0]);assert.deepEqual(morning,['fixed','sunrise','dawn']);const evening=c._eventOptions('evening_on','fixed').map(x=>x[0]);assert.deepEqual(evening,['fixed','sunset','dusk']);assert(c._eventOptions('morning_on','sunset').some(x=>x[0]==='sunset'&&x[1].includes('bestehende')));
// Refresh reads latest saved configuration; old responses never replace new ones.
c.setConfig({view:'actions'});c.render();c._dirty=false;const changed={...settings,season:'reduced'};let messages=[];
c._hass.connection={sendMessagePromise:async m=>{messages.push(m);return m.type==='weihnachtszentrale/get'?structuredClone(changed):data}};await c._refreshActions();assert.equal(c.settings.season,'reduced');assert.equal(messages.at(-1).settings.season,'reduced');
c._dirty=true;let finish;c._hass.connection.sendMessagePromise=()=>new Promise(r=>finish=r);const pending=c._refreshActions();c._invalidatePreview();finish(data);await pending;assert.equal(c._actions,null);
// Mode save must preserve newer settings from configuration page.
c.setConfig({view:'overview'});c.settings=structuredClone(settings);c.settings.season='off';c.render();const newest=structuredClone(settings);newest.times.morning_on.time='07:15';let saved;
c._hass.connection.sendMessagePromise=async m=>{if(m.type==='weihnachtszentrale/get')return newest;if(m.type==='weihnachtszentrale/save'){saved=m.settings;return {saved:true}}return data};await c._saveSettings(new Element('button'));assert.equal(saved.season,'off');assert.equal(saved.times.morning_on.time,'07:15');
// Lifecycle timer cleaned up, no device commands sent.
c.settings=null;c.connectedCallback();assert(timerFn);c.disconnectedCallback();assert.equal(timerFn,null);
assert(messages.every(m=>['weihnachtszentrale/get','weihnachtszentrale/actions'].includes(m.type)));
// Backend activation uses a generic command; device IDs stay in dashboard settings.
c.settings=structuredClone(settings);c.setConfig({view:'overview'});
let armed=false,activation=[];
c._hass.connection.sendMessagePromise=async m=>{
  if(m.type==='weihnachtszentrale/enable'){armed=m.enabled;activation.push(m)}
  return {model_version:'0.7.2',enabled:armed,errors:{'light.tree':'Testfehler'},history:[]};
};
c.render();await c._refreshEngine();
assert(allText().includes('Automatik pausiert'));assert(allText().includes('Testfehler'));
let control=all(c._root,e=>e.tag==='button'&&e.textContent==='Automatik aktivieren')[0];
await control.handlers.click();assert(armed);assert(allText().includes('Automatik aktiv'));
assert.deepEqual(JSON.parse(JSON.stringify(activation[0])),{type:'weihnachtszentrale/enable',enabled:true});
control=all(c._root,e=>e.tag==='button'&&e.textContent==='Automatik pausieren')[0];
await control.handlers.click();assert(!armed);assert(allText().includes('Automatik pausiert'));
// Pending cover holds and explicit cancellation are visible and generic.
let pendingCovers=[{cover:'cover.test',position:30,status:'waiting',message:'Wartet auf Licht-Aus',blocked_by:['light.tree']}];
c._hass.callService=async(domain,action,data)=>{
 assert.equal(domain,'weihnachtszentrale');assert.equal(action,'cancel_cover_close');assert.equal(data.cover_entity,'cover.test');pendingCovers=[];
};
c._hass.connection.sendMessagePromise=async()=>({model_version:'0.7.2',enabled:true,covers:{pending:pendingCovers,history:[]},errors:{},history:[]});
await c._refreshEngine();assert(allText().includes('Ausstehende Rollladenfahrten'));assert(allText().includes('Wartet auf Licht-Aus'));
const cancelCover=all(c._root,e=>e.tag==='button'&&e.textContent==='Verwerfen: cover.test')[0];
await cancelCover.handlers.click();assert.equal(pendingCovers.length,0);assert(!allText().includes('Wartet auf Licht-Aus'));
// Separate cover options do not mutate primary lighting settings.
c.setConfig({view:'configuration'});let coverSettings={enabled:false,expiry:'06:00'};
c._hass.connection.sendMessagePromise=async m=>{
 if(m.type==='weihnachtszentrale/cover_options'){
  if(m.options)coverSettings=m.options;
  return {options:structuredClone(coverSettings)};
 }
 return structuredClone(settings);
};
c.render();await c._refreshCoverOptions();assert(allText().includes('Optionale Rollladenkoordination'));
const coverPanel=c._root.querySelector('.cover-options');
const coverEnable=all(coverPanel,e=>e.tag==='input'&&e.type==='checkbox')[0];coverEnable.checked=true;
const coverExpiry=all(coverPanel,e=>e.tag==='input'&&e.type==='time')[0];coverExpiry.value='07:30';
const saveOptions=all(coverPanel,e=>e.tag==='button'&&e.textContent==='Rollladeneinstellungen speichern')[0];
await saveOptions.handlers.click();assert(coverSettings.enabled);assert.equal(coverSettings.expiry,'07:30');
console.log('PASS B2 UI: three page modes, 4 vs all groups, IDs and empty state, event filters/legacy values, latest saved data, stale-response rejection, mode save preserves config, timer cleanup. Simulated DOM only.');
})().catch(e=>{console.error(e);process.exit(1)});
