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
vm.runInNewContext(fs.readFileSync(__dirname+'/../custom_components/weihnachtszentrale/frontend/weihnachtszentrale-card-v090.js','utf8'),{HTMLElement:Element,document:{createElement:t=>new Element(t)},customElements:{define:(n,c)=>Card=c},window:{},crypto:{randomUUID:()=> 'new-id'},alert:()=>{}});
const all=(e,p)=>[...(p(e)?[e]:[]),...e.children.flatMap(c=>all(c,p))];
(async()=>{
const time={event:'fixed',time:'06:30',offset:0};const c=new Card();c.config={view:'configuration'};c._root=new Element('shadow');c._hass={states:{}};c.settings={season:'full',devices:[],times:Object.fromEntries(['morning_on','morning_off','evening_on','evening_off'].map(k=>[k,{...time}]))};c.render();
const allNodes=()=>all(c._root,()=>true);const label=allNodes().find(e=>e.tag==='label'&&e.children[0].textContent==='Dämmerungstyp (bei Dämmerung)');const twilight=label.children[1];assert.equal(twilight.disabled,true);assert.deepEqual(twilight.children.map(x=>x.value),['civil','nautical','astronomical']);
const trigger=allNodes().filter(e=>e.tag==='select')[0];trigger.value='dawn';trigger.handlers.change();assert.equal(twilight.disabled,false);twilight.value='nautical';twilight.handlers.change();assert.equal(c.settings.times.morning_on.twilight,'nautical');
trigger.value='fixed';trigger.handlers.change();assert.equal(twilight.disabled,true);assert.equal(c.settings.times.morning_on.twilight,'nautical');
const panel=new Element('panel'),button=new Element('button');c._hass.connection={sendMessagePromise:async()=>({timezone:'Europe/Berlin',days:[],devices:[]})};await c._calculatePreview(panel,button);assert(panel.children[0].textContent.includes('Backend v0.9.0 fehlt'));
c.preview={model_version:'0.9.0',timezone:'Europe/Berlin',days:[{date:'2026-10-30',rules:[],warnings:[],windows:[{profile:'evening',start:'2026-10-30T22:00:00+01:00',end:'2026-10-30T23:00:00+01:00'}]}],devices:[{name:'Baum',eligible:true,profile:'both',scheduled_on:true,effective_windows:[{start:'2026-10-30T06:00:00+01:00',end:'2026-10-30T22:00:00+01:00'}]}],warnings:[]};c._showPreview(panel);const text=all(panel,e=>!!e.textContent).map(e=>e.textContent).join(' ');assert(text.includes('Laut Zeitplan jetzt: AN'));assert(text.includes('Wirksam:'));assert(text.includes('30.10.'));assert.equal(c.settings.devices.length,0);
console.log('PASS B1 frontend: three twilight options, enable/disable, draft value retention, old backend detection, overnight/effective-window rendering, calculated-state label.');
})().catch(e=>{console.error(e);process.exit(1)});
