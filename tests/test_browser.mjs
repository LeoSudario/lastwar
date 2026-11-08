// Integration smoke test in an isolated browser profile; no user data is touched.
import { spawn } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import assert from 'node:assert/strict';

const edge = process.env.EDGE_BINARY || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
if (!existsSync(edge) || typeof WebSocket !== 'function') {
  console.log('Teste de navegador ignorado: Edge ou Node com WebSocket indisponível.');
  process.exit(0);
}
const root = resolve('.');
const profile = mkdtempSync(join(tmpdir(), 'lastwar-browser-test-'));
const port = 18000 + Math.floor(Math.random() * 1000);
const debugPort = port + 2000;
const server = spawn(process.env.PYTHON || 'python', ['-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', String(port)], {cwd: root, stdio: 'ignore'});
const browser = spawn(edge, ['--headless=new', '--disable-gpu', '--no-first-run', '--remote-allow-origins=*', `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, 'about:blank'], {stdio: 'ignore'});
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
let socket, id = 0;
const pending = new Map();
async function call(method, params = {}) {
  const n = ++id;
  socket.send(JSON.stringify({id: n, method, params}));
  return new Promise((resolve, reject) => pending.set(n, {resolve, reject}));
}
async function evaluate(expression) {
  const response = await call('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true});
  if (response.exceptionDetails) throw Error(JSON.stringify(response.exceptionDetails));
  return response.result.value;
}
try {
  let targets;
  for (let i = 0; i < 100; i++) {
    try { targets = await (await fetch(`http://127.0.0.1:${debugPort}/json`)).json(); if (targets.some(t => t.type === 'page')) break; } catch {}
    await wait(100);
  }
  assert.ok(targets?.some(t => t.type === 'page'), 'O navegador não iniciou');
  socket = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
  socket.onmessage = event => { const message = JSON.parse(event.data); if (message.id && pending.has(message.id)) { const p = pending.get(message.id); pending.delete(message.id); message.error ? p.reject(Error(message.error.message)) : p.resolve(message.result); } };
  await call('Page.enable'); await call('Runtime.enable');
  for (let i = 0; i < 100; i++) { try { if ((await fetch(`http://127.0.0.1:${port}/`)).ok) break; } catch {} await wait(100); }
  await call('Page.navigate', {url: `http://127.0.0.1:${port}/`}); await wait(1500);
  const b64 = readFileSync(join(root, 'exemplos/ranking-ficticio.png')).toString('base64');
  const upload = await evaluate(`(async()=>{
    const zone=document.getElementById('uploadZone');
    if(!zone)return {exists:false};
    let opened=false;const original=document.getElementById('images').click;document.getElementById('images').click=()=>opened=true;zone.click();document.getElementById('images').click=original;
    let blob=await (await fetch('data:image/png;base64,${b64}')).blob();let transfer=new DataTransfer();
    transfer.items.add(new File([blob],'um.png',{type:'image/png'}));transfer.items.add(new File([blob],'dois.png',{type:'image/png'}));
    const drag=new DragEvent('dragover',{bubbles:true,cancelable:true,dataTransfer:transfer});zone.dispatchEvent(drag);const highlighted=document.getElementById('imageViewport').classList.contains('is-dragging');
    zone.dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:transfer}));
    for(let i=0;i<50&&images.length<2;i++)await new Promise(r=>setTimeout(r,100));
    const viewport=document.getElementById('imageViewport');let more=new DataTransfer();more.items.add(new File([blob],'tres.png',{type:'image/png'}));viewport.dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:more}));
    for(let i=0;i<50&&images.length<3;i++)await new Promise(r=>setTimeout(r,100));
    document.getElementById('playerName').value='Jogador teste';document.getElementById('playerForm').requestSubmit();
    let invalid=new DataTransfer();invalid.items.add(new File(['texto'],'invalido.txt',{type:'text/plain'}));viewport.dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:invalid}));await new Promise(r=>setTimeout(r,100));
    return {exists:true,opened,count:images.length,names:images.map(i=>i.name),highlighted,prevented:drag.defaultPrevented,error:document.getElementById('message').textContent,addPlayerVisible:document.getElementById('playerForm').getBoundingClientRect().height>0,added:store.players.some(p=>p.name==='Jogador teste')};
  })()`);
  assert.equal(upload.exists, true);assert.equal(upload.opened, true);assert.equal(upload.count, 3);assert.deepEqual(upload.names, ['um.png','dois.png','tres.png']);assert.equal(upload.highlighted,true);assert.equal(upload.prevented,true);assert.match(upload.error,/PNG ou JPEG/);  assert.equal(upload.addPlayerVisible, true);assert.equal(upload.added, true);
  const multiSelect = await evaluate(`(async()=>{store.players=[{id:'p1',name:'DragonBR'},{id:'p2',name:'ShadowX'}];store.battles=[];rows={};multi.clear();let url='data:image/png;base64,${b64}';let file=new File([await (await fetch(url)).blob()],'ranking.png',{type:'image/png'});images=[{id:'im1',name:'ranking.png',url,file}];render();return {bulkHidden:document.getElementById('bulkBar').hidden,checkP1:!!document.querySelector('[data-player="p1"] [data-multi]'),checkP2:!!document.querySelector('[data-player="p2"] [data-multi]')};})()`);
  assert.equal(multiSelect.bulkHidden, true);assert.equal(multiSelect.checkP1, true);assert.equal(multiSelect.checkP2, true);
  const bulkSelect = await evaluate(`(async()=>{document.querySelector('[data-player="p1"] [data-multi]').checked = true;document.querySelector('[data-player="p1"] [data-multi]').dispatchEvent(new Event('change',{bubbles:true}));document.querySelector('[data-player="p2"] [data-multi]').checked = true;document.querySelector('[data-player="p2"] [data-multi]').dispatchEvent(new Event('change',{bubbles:true}));return {hidden:document.getElementById('bulkBar').hidden,count:document.getElementById('bulkCount').textContent};})()`);
  assert.equal(bulkSelect.hidden, false);assert.match(bulkSelect.count,/2/);
  const bulkApply = await evaluate(`(()=>{document.getElementById('bulkAusente').click();return {hidden:document.getElementById('bulkBar').hidden,s1:rows.p1?.status,s2:rows.p2?.status};})()`);
  assert.equal(bulkApply.hidden, true);assert.equal(bulkApply.s1,'Ausente');assert.equal(bulkApply.s2,'Ausente');
  const importVisible = await evaluate(`(()=>{const input=document.getElementById('csv');return {exists:!!input,inDetails:!!input?.closest('details'),outsideDetails:!input?.closest('details')};})()`);
  assert.equal(importVisible.exists, true);assert.equal(importVisible.inDetails, false);
  const initial = await evaluate(`(async()=>{
    store.players=[{id:'p1',name:'DragonBR'},{id:'p2',name:'ShadowX'}];store.battles=[];rows={};
    let url='data:image/png;base64,${b64}';let file=new File([await (await fetch(url)).blob()],'ranking.png',{type:'image/png'});
    images=[{id:'im1',name:'ranking.png',url,file}];render();
    document.getElementById('analyze').click();for(let i=0;i<200&&busy;i++)await new Promise(r=>setTimeout(r,100));
    return {busy,score:rows.p2?.score,summary:document.getElementById('summary').textContent};
  })()`);
  assert.equal(initial.busy, false); assert.equal(initial.score, 0);
  const highlighting=await evaluate(`(()=>{let row=document.querySelector('[data-player="p2"]');let absence=getComputedStyle(row).backgroundColor;document.querySelector('[data-player="p1"] [data-status="Revisar"]').click();let review=getComputedStyle(document.querySelector('[data-player="p1"]')).backgroundColor;document.querySelector('[data-player="p1"] [data-status="Presente"]').click();return {absence,review};})()`);
  assert.equal(highlighting.absence,'rgba(220, 55, 65, 0.3)');assert.equal(highlighting.review,'rgba(245, 140, 40, 0.16)');
  const state = await evaluate(`(async()=>{
    document.querySelector('[data-player="p2"] [data-status="Ausente"]').click();
    let input=document.querySelector('[data-player="p2"] [data-score]');input.value='0';input.dispatchEvent(new Event('change',{bubbles:true}));
    document.getElementById('aliasPlayer').value='p1';document.getElementById('aliasNames').value='Dr4gonBR';document.getElementById('aliasForm').requestSubmit();
    document.getElementById('saveBattle').click();let battle=battleId;
    document.getElementById('analyze').click();for(let i=0;i<200&&busy;i++)await new Promise(r=>setTimeout(r,100));
    download=(name,content)=>window.testCsv=content;document.getElementById('exportAttendance').click();
    return {battle,manual:rows.p2.manual_status,score:rows.p2.score,status:rows.p2.status,summary:document.getElementById('summary').textContent,csv:window.testCsv};
  })()`);
  assert.equal(state.manual, true); assert.equal(state.score, 0); assert.equal(state.status, 'Ausente');
  assert.match(state.summary, /1 ausentes/); assert.ok(state.csv.includes('"ShadowX";"0";"Ausente"'));
  await call('Page.reload'); await wait(1500);
  const persisted = await evaluate(`(async()=>{document.querySelector('[data-open="${state.battle}"]').click();await new Promise(r=>setTimeout(r,400));return {status:rows.p2?.status,score:rows.p2?.score,aliases:store.players[0].aliases};})()`);
  assert.deepEqual(persisted, {status: 'Ausente', score: 0, aliases: ['Dr4gonBR']});
  const formation = await evaluate(`(()=>{document.querySelector('[data-page="teams"]').click();document.querySelector('[data-team-player="p1"] [data-team="Titular"]').click();let displayed=document.getElementById('formation').textContent.includes('DragonBR');document.querySelector('[data-formation-remove="p1"]').click();return {displayed,role:team().p1};})()`);
  assert.equal(formation.displayed, true); assert.equal(formation.role, 'Fora');
  const addedFromTeams = await evaluate(`(()=>{let form=document.getElementById('teamPlayerForm'),input=document.getElementById('teamPlayerName');if(!form||!input)return {exists:false};input.value='Novo jogador';form.requestSubmit();let player=store.players.find(p=>p.name==='Novo jogador');let inTeams=!!document.querySelector('[data-team-player="'+player?.id+'"]');input.value='NOVO JOGADOR';form.requestSubmit();let count=store.players.filter(p=>p.name.toLowerCase()==='novo jogador').length;document.querySelector('[data-page="attendance"]').click();return {exists:true,inTeams,count,inAttendance:!!document.querySelector('[data-player="'+player?.id+'"]')};})()`);
  assert.deepEqual(addedFromTeams,{exists:true,inTeams:true,count:1,inAttendance:true});
  await call('Page.reload');await wait(1500);
  assert.equal(await evaluate("store.players.some(p=>p.name==='Novo jogador')"),true);
  console.log('Navegador: OCR, correção, histórico, aliases, contadores e CSV OK');
} finally { socket?.close(); browser.kill(); server.kill(); }
