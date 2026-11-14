const C=AnalogComparator,$=id=>document.getElementById(id);
let data=C.validate(structuredClone(window.REPOSITORY_DATA || DEMO)),weights={},selected=null,rows=[];
const escapeHTML=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=v=>!v||v.status==='missing'?'Sin dato':`${v.status==='lower_bound'?'> ':''}${v.value.toLocaleString('es-ES')} ${v.unit==='deg'?'°':v.unit}`;
function download(name,value){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function setup(){
 $('target').replaceChildren(...data.targets.map(t=>new Option(t.name,t.id)));
 $('weights').innerHTML=C.keys.map(k=>`<label for="w_${k}" class="weight"><span>${escapeHTML(data.variables[k].label||k)}</span><output id="o_${k}">1</output></label><input id="w_${k}" type="range" min="0" max="2" step="0.1" value="1"><div class="hint">Tolerancia: ${data.variables[k].tolerance}</div>`).join('');
 for(const k of C.keys){weights[k]=1;$('w_'+k).oninput=e=>{weights[k]=Number(e.target.value);$('o_'+k).value=e.target.value;render();};}
 $('badge').textContent=data.mock?'DEMOSTRACIÓN · DATOS FICTICIOS':'DATOS IMPORTADOS · NO VALIDADOS';
 $('profile').value='balanced';selected=null;render();
}
function render(){
 if ($('provenance')) $('provenance').textContent=data.provenance?'Origen: '+data.provenance.repository+' · revisión '+data.provenance.revision.slice(0,12)+' · '+data.targets.length+' zonas / '+data.earth.length+' celdas.':'Demo manual: 3 zonas / 6 terrenos.';
 const target=data.targets.find(t=>t.id===$('target').value);rows=C.rank(data,target,weights,Number($('coverage').value));
 if(!rows.some(r=>r.site.id===selected))selected=rows[0]?.site.id;
 const active=C.keys.filter(k=>weights[k]>0).length;
 $('heading').textContent=`${rows.length} lugares comparables · mostrando ${Math.min(rows.length,30)}`;
 $('summary').innerHTML=`<span class="chip">${active} variables activas</span><span class="chip">${data.earth.length} lugares evaluados</span><span class="chip">${data.mock?'Cifras simuladas':'Paquete importado'}</span>`;
 $('warning').textContent=data.mock?'Todos los valores son inventados para probar el comparador. El orden no es una conclusión científica.':'Resultados provisionales: verifica fuentes, definiciones y tolerancias con el equipo de datos.';
 $('results').replaceChildren();
 for(const r of rows.slice(0,30)){const b=document.createElement('button');b.className='result'+(r.site.id===selected?' active':'');b.innerHTML=`<span><strong>${escapeHTML(r.site.name)}</strong><br><small>${r.count} de ${r.total} variables · ${Math.round(r.coverage*100)} % de cobertura</small></span><span class="score">${r.score.toFixed(1)}<small> / 100</small></span>`;b.onclick=()=>{selected=r.site.id;render();};$('results').append(b);}
 if(!rows.length)$('results').innerHTML='<div class="empty">No hay resultados con estos filtros. Activa algún peso o reduce la cobertura mínima para explorar comparaciones parciales.</div>';
 const chosen=rows.find(r=>r.site.id===selected);
 $('detail').hidden=!chosen;if(!chosen)return;
 $('detail').innerHTML=`<h2>${escapeHTML(chosen.site.name)}</h2><p class="hint">Comparado con ${escapeHTML(target.name)}. Las notas se calculan solo con variables compatibles y activas.</p><div class="scroll"><table><thead><tr><th>Variable</th><th>Luna</th><th>Tierra</th><th>Similitud</th></tr></thead><tbody>${C.keys.map(k=>{const a=target.features?.[k],b=chosen.site.features?.[k],s=chosen.parts[k];return `<tr><td>${escapeHTML(data.variables[k].label||k)}</td><td>${escapeHTML(fmt(a))}</td><td>${escapeHTML(fmt(b))}</td><td>${weights[k]===0?'Excluida':s==null?'No comparable':`${Math.round(s*100)} %<br><span class="bar" style="width:${s*90}px"></span>`}</td></tr>`;}).join('')}</tbody></table></div><p class="hint">Faltantes, límites de profundidad o metadatos incompatibles no puntúan. La cobertura es la fracción de variables activas comparables; la nota es su media ponderada.</p><details><summary>Ver fuentes y definiciones</summary>${C.keys.map(k=>`<p class="hint"><strong>${escapeHTML(data.variables[k].label||k)}</strong><br>Luna: ${escapeHTML(target.features?.[k]?.source||'Sin fuente')}<br>Tierra: ${escapeHTML(chosen.site.features?.[k]?.source||'Sin fuente')}<br>Definiciones: ${escapeHTML(target.features?.[k]?.definition||'—')} / ${escapeHTML(chosen.site.features?.[k]?.definition||'—')}<br>Escala espacial: ${escapeHTML(target.features?.[k]?.scale_m??'No indicada')} / ${escapeHTML(chosen.site.features?.[k]?.scale_m??'No indicada')} m</p>`).join('')}</details>`;
}
$('target').onchange=()=>{selected=null;render();};$('coverage').onchange=render;
$('profile').onchange=()=>{const values=$('profile').value==='terrain'?[1,1,0,0]:$('profile').value==='cold'?[0,0,1,1]:[1,1,1,1];C.keys.forEach((k,i)=>{weights[k]=values[i];$('w_'+k).value=values[i];$('o_'+k).value=values[i];});render();};
$('reset').onclick=()=>{data=structuredClone(DEMO);$('coverage').value='1';$('upload').value='';$('import-status').textContent='';setup();};
$('example').onclick=()=>download('analogos-ejemplo.json',DEMO);
$('export').onclick=()=>download('resultados-comparador.json',{schema_version:1,mock:data.mock,provenance:data.provenance||null,target_id:$('target').value,weights,minimum_coverage:Number($('coverage').value),variables:data.variables,results:rows.map(r=>({id:r.site.id,name:r.site.name,index:r.score,coverage:r.coverage,compared:r.count,active:r.total,scores:r.parts}))});
$('upload').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size>20*1024*1024)throw Error('El paquete supera 20 MB.');const candidate=C.validate(JSON.parse(await file.text()));data=candidate;setup();$('import-status').textContent='Paquete cargado. '+(data.mock?'Contiene datos ficticios.':'Procedencia pendiente de validación científica.');}catch(err){$('import-status').textContent='No se ha cargado: '+err.message;}};
setup();

if ($('repository')) $('repository').onclick=()=>{if(window.REPOSITORY_DATA){data=C.validate(structuredClone(window.REPOSITORY_DATA));$('coverage').value='1';$('import-status').textContent='';setup();}};


