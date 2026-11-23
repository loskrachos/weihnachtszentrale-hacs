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
vm.runInNewContext(fs.readFileSync(__dirname+'/../custom_components/weihnachtszentrale/frontend/weihnachtszentrale-card-v072.js','utf8'),{HTMLElement:Element,document:{createElement:t=>new Element(t)},customElements:{define:(n,c)=>Card=c},window:{},crypto:{randomUUID:()=> 'new-id'},alert:()=>{}});
const all=(e,p)=>[...(p(e)?[e]:[]),...e.children.flatMap(c=>all(c,p))];
(async()=>{
const time={event:'fixed',time:'06:30',offset:0};
const c=new Card();c.config={view:'configuration'};c._root=new Element('shadow');
c.settings={season:'full',times:Object.fromEntries(['morning_on','morning_off','evening_on','evening_off'].map(k=>[k,{...time}])),devices:[{id:'a',entity_id:'light.test_deckenleuchte',name:'Deckenleuchte 1',enabled:true,season:'full',profile:'both',cover:''}]};
c._hass={states:{'light.test_deckenleuchte':{attributes:{friendly_name:'Deckenleuchte 1'}},'switch.other':{attributes:{friendly_name:'Deckenleuchte 1'}},'cover.window':{attributes:{}}}};
const options=()=>all(c._root,e=>e.tag==='select').at(-1).children.map(e=>e.value);
c.render();assert(!options().includes('light.test_deckenleuchte'));assert(options().includes('switch.other'));assert(!options().includes('cover.window'));
c._addDevice('light.test_deckenleuchte');assert.equal(c.settings.devices.length,1);assert(c.error.includes('bereits'));
c._addDevice('switch.other');c._addDevice('switch.other');assert.equal(c.settings.devices.length,2);assert(!options().includes('switch.other'));
c._addDevice('cover.window');c._addDevice('switch.missing');assert.equal(c.settings.devices.length,2);
c.settings.devices=c.settings.devices.filter(d=>d.entity_id!=='switch.other');c.render();assert(options().includes('switch.other'));
console.log('PASS: exact reported entity excluded; duplicate and stale/repeated add blocked; distinct entity with same name allowed; invalid entities rejected; removed entity selectable again.');
})().catch(e=>{console.error(e);process.exit(1)});
