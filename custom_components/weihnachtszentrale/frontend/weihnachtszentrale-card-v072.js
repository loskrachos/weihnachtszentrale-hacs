/* v0.7.2: configurable backend light control; no device IDs embedded. */
class WeihnachtszentraleCard extends HTMLElement {
  setConfig(config) {
    this.config=config||{};
    if(!['overview','configuration','actions'].includes(this.config.view||'overview'))throw new Error('Unbekannte Weihnachtszentrale-Ansicht.');
  }
  _view(){return this.config?.view||'overview'}
  connectedCallback(){
    if(this.settings&&this._hass)this._load();
    if(!this._timer)this._timer=setInterval(()=>{if(this._hass&&this.settings&&this._view()!=='configuration')this._refreshActions()},60000);
  }
  disconnectedCallback(){clearInterval(this._timer);this._timer=null;this._actionRequest=(this._actionRequest||0)+1}

  set hass(value) {
    this._hass = value;
    if(this._root&&this._view()==='overview')this._showDeviceStates();
    if (!this._root) {
      this._root = this.attachShadow({mode:'open'});
      this._load();
    }
  }
  async _load() {
    try {
      this._invalidatePreview();
      this.settings = await this._hass.connection.sendMessagePromise({type:'weihnachtszentrale/get'});
      this.error = '';this._dirty=false;
    } catch (e) { this.error = String(e.message || e); }
    this.render();
    if(this.settings&&this._view()!=='configuration')await this._refreshActions();
  }
  _el(tag, props={}, children=[]) {
    const e=document.createElement(tag);
    for (const [k,v] of Object.entries(props)) {
      if(k==='text') e.textContent=v;
      else if(k==='className') e.className=v;
      else e[k]=v;
    }
    if(['input','select'].includes(tag))e.addEventListener('change',()=>{this._dirty=true;this._invalidatePreview()});
    for(const child of children) e.append(child);
    return e;
  }
  _field(label, control) {
    const wrapper=this._el('label',{},[this._el('span',{text:label}),control]);
    return wrapper;
  }
  _select(values, current, onChange) {
    const e=this._el('select');
    for(const [value,label] of values) {
      const o=this._el('option',{value,text:label});o.selected=value===current;e.append(o);
    }
    e.addEventListener('change',()=>onChange(e.value));return e;
  }
  _invalidatePreview() {
    this._previewRequest=(this._previewRequest||0)+1;
    this.preview=null;this._actionRequest=(this._actionRequest||0)+1;this._actions=null;
    const panel=this._root?.querySelector('.preview');
    if(panel)panel.replaceChildren(this._el('p',{className:'small',text:'Vorschau nach Änderungen neu berechnen.'}));
  }
  async _calculatePreview(panel, button) {
    const request=(this._previewRequest||0)+1;this._previewRequest=request;
    button.disabled=true;
    panel.replaceChildren(this._el('p',{text:'Berechne Zeiten …'}));
    try {
      const result=await this._hass.connection.sendMessagePromise({type:'weihnachtszentrale/preview',settings:JSON.parse(JSON.stringify(this.settings))});
      if(request!==this._previewRequest)return;
      if(result.model_version!=='0.7.2')throw new Error('Backend v0.7.2 fehlt. Python-Dateien aktualisieren und Home Assistant neu starten.');
      this.preview=result;this._showPreview(panel);
    } catch(e) {
      if(request===this._previewRequest)panel.replaceChildren(this._el('p',{className:'error',text:String(e.message||e)}));
    } finally {button.disabled=false}
  }
  _showPreview(panel) {
    panel.replaceChildren();if(!this.preview)return;
    const p=this.preview;
    panel.append(this._el('p',{className:'small',text:'Vorschau der aktuellen Eingaben · Zeitzone '+p.timezone+' · keine Gerätebefehle. Rollladensperre wird über die gespeicherten Zuordnungen und angebundenen Schließaktionen ausgewertet. Zeitpunkte zeigen Regeln; Zeitfenster zeigen ihre Zuordnung innerhalb eines Tages. Noch keine Gerätebefehle.'}));
    const names={morning_on:'Morgen an',morning_off:'Morgen aus',evening_on:'Abend an',evening_off:'Abend aus'};
    const format=new Intl.DateTimeFormat('de-DE',{timeZone:p.timezone,day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit',timeZoneName:'short'});
    for(const day of p.days){
      panel.append(this._el('h3',{text:day.date.split('-').reverse().join('.')}));
      const grid=this._el('div',{className:'grid'});
      for(const rule of day.rules){
        const box=this._el('div',{className:'entry'},[this._el('strong',{text:names[rule.key]}),this._el('p',{text:rule.at?format.format(new Date(rule.at)):'Nicht berechenbar'})]);
        if(rule.warning)box.append(this._el('p',{className:'error',text:rule.warning}));grid.append(box);
      }
      panel.append(grid);
      if(day.windows?.length){
        panel.append(this._el('p',{className:'small',text:'Zeitfenster nach Startdatum:'}));
        for(const w of day.windows)panel.append(this._el('p',{className:'small',text:(w.profile==='morning'?'Morgens':'Abends')+': '+format.format(new Date(w.start))+' → '+format.format(new Date(w.end))}));
      }
      for(const warning of day.warnings)panel.append(this._el('p',{className:'error',text:warning.replace('morning:','Morgens:').replace('evening:','Abends:')}));
    }
    panel.append(this._el('h3',{text:'Geräteteilnahme'}));
    if(!p.devices.length)panel.append(this._el('p',{text:'Noch keine Dekoelemente eingerichtet.'}));
    const profiles={morning:'Morgens',evening:'Abends',both:'Morgens und abends'};
    for(const d of p.devices){
      panel.append(this._el('p',{className:'small',text:(d.name||d.entity_id)+': '+(d.eligible?profiles[d.profile]:d.reason)}));
      if(d.eligible){
        panel.append(this._el('p',{className:'small',text:'Laut Zeitplan jetzt: '+(d.scheduled_on?'AN':'AUS')+' (berechnet, kein Gerätestatus)'}));
        if(!d.effective_windows?.length)panel.append(this._el('p',{className:'small',text:'Keine berechenbaren Zeitfenster.'}));
        for(const w of d.effective_windows||[])panel.append(this._el('p',{className:'small',text:'Wirksam: '+format.format(new Date(w.start))+' → '+format.format(new Date(w.end))}));
      }
    }
    for(const warning of p.warnings||[])panel.append(this._el('p',{className:'error',text:'Vorheriger Starttag: '+warning.replace('morning:','Morgens:').replace('evening:','Abends:')}));
  }
  _addDevice(entityId) {
    if(!entityId)return;
    if(this.settings.devices.some(d=>d.entity_id===entityId)) {
      this.error='Dieses Gerät ist bereits eingetragen: '+entityId;
      this.render();return;
    }
    if(!this._hass.states[entityId]||!['switch','light'].includes(entityId.split('.')[0])) {
      this.error='Bitte einen vorhandenen Schalter oder eine Leuchte auswählen.';
      this.render();return;
    }
    this._dirty=true;this._invalidatePreview();this.error='';
    this.settings.devices.push({id:(crypto.randomUUID?crypto.randomUUID():String(Date.now())),entity_id:entityId,name:this._hass.states[entityId]?.attributes?.friendly_name||entityId,enabled:true,season:'full',profile:'evening',cover:''});
    this.render();
  }
  _eventOptions(key,current){
    const all={fixed:'Uhrzeit',sunrise:'Sonnenaufgang',sunset:'Sonnenuntergang',dawn:'Morgendämmerung',dusk:'Abenddämmerung'};
    const values=key.startsWith('morning')?['fixed','sunrise','dawn']:['fixed','sunset','dusk'];
    if(!values.includes(current))values.push(current);
    return values.map(x=>[x,all[x]+((key.startsWith('morning')?['fixed','sunrise','dawn']:['fixed','sunset','dusk']).includes(x)?'':' (bestehende Regel)')]);
  }
  async _saveSettings(button){
    button.disabled=true;
    try{
      let payload=JSON.parse(JSON.stringify(this.settings));
      if(this._view()==='overview'){
        const latest=await this._hass.connection.sendMessagePromise({type:'weihnachtszentrale/get'});
        payload={...latest,season:payload.season};
      }
      await this._hass.connection.sendMessagePromise({type:'weihnachtszentrale/save',settings:payload});
      this.settings=payload;
      this.error='';this._dirty=false;alert('Gespeichert');
      if(this._view()!=='configuration')await this._refreshActions();
    }catch(e){this.error=String(e.message||e);this.render()}
    finally{button.disabled=false}
  }
  async _refreshEngine(){
    const panel=this._root?.querySelector('.engine-status');if(!panel)return;
    try{
      const data=await this._hass.connection.sendMessagePromise({type:'weihnachtszentrale/engine'});
      if(data.model_version!=='0.7.2')throw new Error('Backend v0.7.2 fehlt.');
      panel.replaceChildren(this._el('p',{text:data.enabled?'Automatik aktiv · läuft auch ohne geöffnetes Dashboard.':'Automatik pausiert · es werden keine Schaltbefehle gesendet.'}));
      panel.append(this._el('p',{className:'small',text:'Aktivieren wendet den gespeicherten Zeitplan sofort auf alle Geräte mit aktiver Teilnahme an. Pausieren stoppt die Automatik und lässt die Lichter unverändert. Modus Aus schaltet bei aktiver Automatik die teilnehmenden Lichter aus.'}));
      const button=this._el('button',{text:data.enabled?'Automatik pausieren':'Automatik aktivieren',className:'primary'});
      button.addEventListener('click',async()=>{
        button.disabled=true;
        try{await this._hass.connection.sendMessagePromise({type:'weihnachtszentrale/enable',enabled:!data.enabled});await this._refreshEngine()}
        catch(e){panel.append(this._el('p',{className:'error',text:String(e.message||e)}))}
        finally{button.disabled=false}
      });panel.append(button);
      for(const [entity,error] of Object.entries(data.errors||{}))panel.append(this._el('p',{className:'error',text:entity+': '+error}));
      panel.append(this._el('p',{className:'small',text:(data.covers?.enabled?'Rollladenkoordination aktiv. ':'Rollladenkoordination deaktiviert. ')+'Rollladensperre: nur abendliche Schließanforderungen über Weihnachtszentrale; morgens keine Änderung. „Keiner“ deaktiviert die Zuordnung. Pausierte Automatik hält neue automatische Schließanforderungen nicht zurück.'}));
      if(data.covers?.pending?.length){
        panel.append(this._el('h3',{text:'Ausstehende Rollladenfahrten'}));
        for(const item of data.covers.pending){
          panel.append(this._el('p',{className:item.status==='waiting'?'small':'error',text:item.cover+' → '+item.position+' % · '+(item.message||item.status)+(item.blocked_by?.length?' · '+item.blocked_by.join(', '):'')}));
          const cancel=this._el('button',{text:'Verwerfen: '+item.cover});
          cancel.addEventListener('click',async()=>{
            cancel.disabled=true;
            try{await this._hass.callService('weihnachtszentrale','cancel_cover_close',{cover_entity:item.cover});await this._refreshEngine()}
            catch(e){panel.append(this._el('p',{className:'error',text:String(e.message||e)}));cancel.disabled=false}
          });panel.append(cancel);
        }
      }
      for(const item of data.covers?.history||[])panel.append(this._el('p',{className:'small',text:item.cover+' · '+item.result}));
      if(data.history?.length){
        panel.append(this._el('h3',{text:'Letzte Schaltbefehle'}));
        for(const item of data.history.slice(-5).reverse())panel.append(this._el('p',{className:'small',text:new Date(item.at).toLocaleString('de-DE')+' · '+item.entity_id+' · '+(item.action==='on'?'AN':'AUS')+' · '+item.result}));
      }
    }catch(e){panel.replaceChildren(this._el('p',{className:'error',text:String(e.message||e)}))}
  }
  async _refreshCoverOptions(){
    const panel=this._root?.querySelector('.cover-options');if(!panel)return;
    try{
      const data=await this._hass.connection.sendMessagePromise({type:'weihnachtszentrale/cover_options'});
      if(typeof data?.options?.enabled!=='boolean')throw new Error('Rollladenoptionen konnten nicht geladen werden.');
      const enabled=document.createElement('input');enabled.type='checkbox';enabled.checked=data.options.enabled;
      const expiry=document.createElement('input');expiry.type='time';expiry.value=data.options.expiry;
      const message=this._el('p',{className:'small'});
      const save=this._el('button',{text:'Rollladeneinstellungen speichern'});
      save.addEventListener('click',async()=>{
        save.disabled=true;
        try{await this._hass.connection.sendMessagePromise({type:'weihnachtszentrale/cover_options',options:{enabled:enabled.checked,expiry:expiry.value}});message.textContent='Gespeichert.'}
        catch(e){message.textContent=String(e.message||e)}finally{save.disabled=false}
      });
      panel.replaceChildren(this._el('h3',{text:'Optionale Rollladenkoordination'}),
        this._field('Abendliche Rollladenkoordination aktiv',enabled),
        this._field('Ausstehende Schließungen spätestens verwerfen um',expiry),
        this._el('p',{className:'small',text:'Standardmäßig aus. Deaktivieren verwirft wartende Fahrten ohne Bewegung. Neue Schließanfragen laufen dann direkt durch. Die Ablaufzeit ist keine Öffnungszeit. Vorhandene Sicherheitsprüfungen bleiben erforderlich.'}),save,message);
    }catch(e){panel.replaceChildren(this._el('p',{className:'error',text:String(e.message||e)}))}
  }
  _renderOverview(card){
    card.append(this._el('p',{className:'small',text:'Automatische Lichtsteuerung nach gespeicherten Einstellungen. Abendliche Rollladensperre nur über angebundene Schließaktionen. Partymodus ist noch nicht aktiv.'}));
    card.append(this._el('div',{className:'engine-status'}));
    this._refreshEngine();
    card.append(this._field('Weihnachtsmodus',this._select([['off','Aus'],['reduced','Reduziert'],['full','Vollbetrieb']],this.settings.season,v=>{this.settings.season=v;this._refreshActions()})));
    const save=this._el('button',{text:'Modus speichern',className:'primary'});save.addEventListener('click',()=>this._saveSettings(save));card.append(save);
    card.append(this._el('h3',{text:'Aktuelle Gerätestände'}));const states=this._el('div',{className:'device-states'});card.append(states);this._showDeviceStates();
    card.append(this._el('h3',{text:'Nächste vier Aktionen'}));
    const panel=this._el('div',{className:'action-list'});card.append(panel);
    this._actionControls(card);

  }
  _renderActionsPage(card){
    card.append(this._el('p',{className:'small',text:'Zeitplan der kommenden 24 Stunden. Die Liste bestätigt keine ausgeführten Schaltbefehle; Automatikstatus auf der Übersicht beachten.'}));
    card.append(this._el('div',{className:'action-list'}));this._actionControls(card);
  }
  _actionControls(card){
    const refresh=this._el('button',{text:'Aktionen aktualisieren'});refresh.addEventListener('click',()=>this._refreshActions());card.append(refresh);
    const reload=this._el('button',{text:'Gespeicherte Einstellungen neu laden'});reload.addEventListener('click',()=>this._load());card.append(reload);
  }
  _showDeviceStates(){
    const panel=this._root?.querySelector('.device-states');if(!panel||!this.settings)return;
    panel.replaceChildren();
    if(!this.settings.devices.length)panel.append(this._el('p',{text:'Noch keine Dekoelemente eingerichtet.'}));
    const names={on:'An',off:'Aus',unavailable:'Nicht erreichbar',unknown:'Unbekannt'};
    for(const d of this.settings.devices){
      const state=this._hass.states[d.entity_id];
      panel.append(this._el('p',{text:(d.name||d.entity_id)+': '+(d.no_feedback&&state&&state.state!=='unavailable'?'Ohne Zustandsrückmeldung – tatsächlicher Zustand unbekannt':(state?(names[state.state]||state.state):'Entität nicht vorhanden'))+' · '+d.entity_id}));
    }
  }
  async _refreshActions(){
    if(!this.settings||!this._root)return;
    if(this._view()==='overview')this._refreshEngine();
    const request=(this._actionRequest||0)+1;this._actionRequest=request;
    let panel=this._root.querySelector('.action-list');if(!panel)return;
    panel.replaceChildren(this._el('p',{text:'Aktionen werden berechnet …'}));
    try{
      if(!this._dirty){
        const latest=await this._hass.connection.sendMessagePromise({type:'weihnachtszentrale/get'});
        if(request!==this._actionRequest)return;
        if(JSON.stringify(latest)!==JSON.stringify(this.settings)){
          this.settings=latest;this.render();panel=this._root.querySelector('.action-list');
        }
      }
      const result=await this._hass.connection.sendMessagePromise({type:'weihnachtszentrale/actions',settings:JSON.parse(JSON.stringify(this.settings))});
      if(request!==this._actionRequest)return;
      if(result.model_version!=='0.7.2')throw new Error('Backend v0.7.2 fehlt. Python-Dateien aktualisieren und Home Assistant neu starten.');
      this._actions=result;this._showActions(panel);
    }catch(e){if(request===this._actionRequest)panel.replaceChildren(this._el('p',{className:'error',text:String(e.message||e)}))}
  }
  _showActions(panel){
    panel.replaceChildren();if(!this._actions)return;
    const data=this._actions;
    const format=new Intl.DateTimeFormat('de-DE',{timeZone:data.timezone,day:'2-digit',month:'2-digit',year:'2-digit',hour:'2-digit',minute:'2-digit',timeZoneName:'short'});
    panel.append(this._el('p',{className:'small',text:(this._dirty?'Vorschau ungespeicherter Eingaben. ':'Gespeicherte Regeln. ')+'Berechnet: '+format.format(new Date(data.generated_at))+' · bis '+format.format(new Date(data.until))}));
    const groups=this._view()==='overview'?data.actions.slice(0,4):data.actions;
    if(!groups.length)panel.append(this._el('p',{text:'Keine weiteren Aktionen geplant'}));
    for(const group of groups){
      const box=this._el('div',{className:'entry'});box.append(this._el('strong',{text:format.format(new Date(group.at))}));
      for(const key of ['on','off'])if(group[key]?.length){
        box.append(this._el('p',{text:(key==='on'?'Einschalten: ':'Ausschalten: ')+group[key].map(d=>(d.name||d.entity_id)+' ('+d.entity_id+')').join(', ')}));
        const covers=[...new Set(group[key].map(d=>d.cover).filter(Boolean))];
        if(covers.length)box.append(this._el('p',{className:'small',text:'Rollladenbezug: '+covers.join(', ')+' – Sperre nur bei angebundener Schließautomation.'}));
      }
      panel.append(box);
    }
    for(const warning of data.warnings||[])panel.append(this._el('p',{className:'error',text:warning.replace('morning:','Morgens:').replace('evening:','Abends:')}));
  }
  render() {
    if(!this._root)return;
    this._root.innerHTML=`<style>
      :host{display:block;width:100%;min-width:0;max-width:none;box-sizing:border-box;color:var(--primary-text-color);container-type:inline-size}
      *,*::before,*::after{box-sizing:border-box}
      ha-card{display:block;width:100%;min-width:0;max-width:none;padding:16px}
      h2{font-size:1.15rem;margin:0 0 12px}h3{font-size:1rem;margin:18px 0 8px}
      .grid{display:grid;width:100%;min-width:0;grid-template-columns:minmax(0,1fr);gap:10px}
      .grid>*{min-width:0}
      label{display:flex;min-width:0;flex-direction:column;gap:5px;font-size:.84rem;color:var(--secondary-text-color)}
      select,input,button{font:inherit;min-width:0;max-width:100%;padding:9px;border-radius:7px;background:var(--card-background-color);color:var(--primary-text-color);border:1px solid var(--divider-color)}
      label>select,label>input:not([type="checkbox"]){display:block;width:100%}
      input[type="checkbox"]{align-self:flex-start;width:auto}
      .entry{min-width:0;border:1px solid var(--divider-color);padding:12px;border-radius:10px;margin:8px 0;overflow-wrap:anywhere}
      .times>.entry{margin:0}
      .entry label{margin-top:8px}
      .entry button{margin-top:10px}
      .actions{display:flex;flex-wrap:wrap;gap:10px;align-items:center;min-width:0;margin-top:15px}
      .device-actions>select{flex:1 1 220px;width:0;min-width:0;max-width:640px}
      button{cursor:pointer;white-space:normal} .primary{background:var(--primary-color);color:white;border:0}
      .small{font-size:.8rem;color:var(--secondary-text-color);overflow-wrap:anywhere} .error{color:var(--error-color);overflow-wrap:anywhere}
      @container (min-width:600px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
      @container (min-width:1000px){.grid{grid-template-columns:repeat(4,minmax(0,1fr))}}
      @container (max-width:599px){.actions{align-items:stretch;flex-direction:column}.actions>select,.actions>button{width:100%;flex:none;max-width:100%}}
    </style>`;
    const card=this._el('ha-card');this._root.append(card);
    const titles={overview:'Übersicht',configuration:'Konfiguration',actions:'Kommende Aktionen'};
    card.append(this._el('h2',{text:'🎄 Weihnachtszentrale v0.7.2 – '+titles[this._view()]}));
    if(this.error)card.append(this._el('p',{className:'error',text:this.error}));
    if(!this.settings)return;
    if(this._view()==='overview'){this._renderOverview(card);return}
    if(this._view()==='actions'){this._renderActionsPage(card);return}
    card.append(this._el('p',{className:'small',text:'Änderungen werden mit „Speichern“ dauerhaft und bei aktiver Automatik unmittelbar angewendet.'}));
    card.append(this._field('Weihnachtsmodus',this._select([['off','Aus'],['reduced','Reduziert'],['full','Vollbetrieb']],this.settings.season,v=>this.settings.season=v)));
    card.append(this._el('h3',{text:'Zentrale Zeiten'}));
    const times=this._el('div',{className:'grid times'});
    for(const [key,name] of [['morning_on','Morgen an'],['morning_off','Morgen aus'],['evening_on','Abend an'],['evening_off','Abend aus']]) {
      const t=this.settings.times[key];t.twilight=t.twilight||'civil';const cell=this._el('div',{className:'entry'});
      cell.append(this._el('strong',{text:name}));
      cell.append(this._field('Auslöser',this._select(this._eventOptions(key,t.event),t.event,v=>{t.event=v;twilight.disabled=!['dawn','dusk'].includes(v)})));
      const twilight=this._select([['civil','Bürgerlich (6°)'],['nautical','Nautisch (12°)'],['astronomical','Astronomisch (18°)']],t.twilight,v=>t.twilight=v);
      twilight.disabled=!['dawn','dusk'].includes(t.event);
      cell.append(this._field('Dämmerungstyp (bei Dämmerung)',twilight));
      const ti=this._el('input',{type:'time',value:t.time});ti.addEventListener('change',()=>t.time=ti.value);
      cell.append(this._field('Uhrzeit (bei fester Zeit)',ti));
      const off=this._el('input',{type:'number',min:-180,max:180,value:String(t.offset)});off.addEventListener('change',()=>t.offset=Number(off.value));
      cell.append(this._field('Sonnen-Offset (Minuten)',off));times.append(cell);
    }card.append(times);
    card.append(this._el('h3',{text:'Dekoelemente'}));
    for(const d of this.settings.devices){
      const box=this._el('div',{className:'entry'});
      const title=this._el('strong',{text:d.name||d.entity_id});box.append(title);
      box.append(this._el('p',{className:'small',text:d.entity_id}));
      const grid=this._el('div',{className:'grid'});
      grid.append(this._field('Zeitprofil',this._select([['morning','Morgens'],['evening','Abends'],['both','Beides']],d.profile,v=>d.profile=v)));
      grid.append(this._field('Saison',this._select([['full','Nur Vollbetrieb'],['both','Auch reduziert']],d.season,v=>d.season=v)));
      const covers=[['','Keiner'],...Object.keys(this._hass.states).filter(x=>x.startsWith('cover.')).sort().map(x=>[x,x])];
      grid.append(this._field('Abends offen halten: Rollladen (optional)',this._select(covers,d.cover,v=>d.cover=v)));
      const enabled=this._el('input',{type:'checkbox',checked:d.enabled});enabled.addEventListener('change',()=>d.enabled=enabled.checked);
      grid.append(this._field('Teilnahme aktiv',enabled));
      const noFeedback=this._el('input',{type:'checkbox',checked:d.no_feedback===true});
      noFeedback.addEventListener('change',()=>{d.no_feedback=noFeedback.checked});
      grid.append(this._field('Keine Zustandsrückmeldung (z. B. 433 MHz)',noFeedback));box.append(grid);
      const rm=this._el('button',{text:'Entfernen'});rm.addEventListener('click',()=>{this._dirty=true;this._invalidatePreview();this.settings.devices=this.settings.devices.filter(x=>x.id!==d.id);this.render()});box.append(rm);card.append(box);
    }
    const registered=new Set(this.settings.devices.map(d=>d.entity_id));
    const choices=Object.keys(this._hass.states).filter(x=>['switch','light'].includes(x.split('.')[0])&&!registered.has(x)).sort();
    const row=this._el('div',{className:'actions device-actions'});
    const picker=this._select([['','Gerät auswählen'],...choices.map(x=>[x,(this._hass.states[x]?.attributes?.friendly_name||x)+' ('+x+')'])],'',()=>{});
    const add=this._el('button',{text:'Gerät hinzufügen'});
    add.addEventListener('click',()=>this._addDevice(picker.value));
    row.append(picker,add);card.append(row);
    const actions=this._el('div',{className:'actions'});const save=this._el('button',{text:'Einstellungen speichern',className:'primary'});const reload=this._el('button',{text:'Neu laden'});
    save.addEventListener('click',()=>this._saveSettings(save));
    reload.addEventListener('click',()=>this._load());actions.append(save,reload);card.append(actions);
    card.append(this._el('div',{className:'cover-options'}));this._refreshCoverOptions();
    card.append(this._el('h3',{text:'Zeitvorschau – heute und morgen'}));
    const previewButton=this._el('button',{text:'Vorschau berechnen'});
    const panel=this._el('div',{className:'preview'});
    previewButton.addEventListener('click',()=>this._calculatePreview(panel,previewButton));
    card.append(previewButton,panel);
    if(this.preview)this._showPreview(panel);
  }
  // Spanned HA sections can contain more than twelve grid columns.
  // "full" follows the complete section width; height follows the content.
  getGridOptions(){return {columns:'full',rows:'auto'}}
  getCardSize(){return 8}
}
if(!customElements.get||!customElements.get('weihnachtszentrale-card'))customElements.define('weihnachtszentrale-card',WeihnachtszentraleCard);
window.customCards=window.customCards||[];
window.customCards.push({type:'weihnachtszentrale-card',name:'Weihnachtszentrale (Prototyp)',description:'Konfiguration von Dekoelementen und Zeitregeln'});
