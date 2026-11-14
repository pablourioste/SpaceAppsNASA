/* Motor independiente de la interfaz. Valores censurados o incompatibles no puntuan. */
window.AnalogComparator = (() => {
 const keys=['slope_deg','roughness_deg','t_mean_K','ice_depth_m'];
 function usable(v){return v && v.status==='value' && Number.isFinite(v.value);}
 function comparable(a,b){return usable(a)&&usable(b)&&a.unit===b.unit&&a.definition===b.definition&&a.scale_m===b.scale_m;}
 function validate(p){
  if(!p||p.schema_version!==1||typeof p.mock!=='boolean')throw Error('Se requiere schema_version: 1 y mock: true/false.');
  if(!Array.isArray(p.targets)||!p.targets.length||!Array.isArray(p.earth)||!p.earth.length)throw Error('Faltan targets o earth.');
  for(const k of keys){const v=p.variables?.[k];if(!v||!Number.isFinite(v.tolerance)||v.tolerance<=0)throw Error('Tolerancia inválida: '+k);}
  for(const group of [p.targets,p.earth]){const ids=new Set();for(const s of group){
   if(typeof s.id!=='string'||!s.id||ids.has(s.id)||typeof s.name!=='string')throw Error('Nombres o identificadores inválidos o duplicados.');ids.add(s.id);
   if(!Number.isFinite(s.lat)||Math.abs(s.lat)>90||!Number.isFinite(s.lon)||Math.abs(s.lon)>180)throw Error('Coordenadas inválidas: '+s.id);
   for(const k of keys){const v=s.features?.[k];if(v==null)continue;
    if(!['value','missing','lower_bound'].includes(v.status))throw Error('Estado inválido: '+k);
    if(v.status!=='missing'&&(!Number.isFinite(v.value)||v.value<0))throw Error('Valor inválido: '+k);
    if(v.status!=='missing'&&(typeof v.unit!=='string'||!v.unit||typeof v.definition!=='string'||!v.definition||typeof v.source!=='string'||!v.source))throw Error('Faltan unidad, definición o fuente: '+k);
    if(v.scale_m!=null&&(!Number.isFinite(v.scale_m)||v.scale_m<=0))throw Error('Escala inválida: '+k);
    if(v.status!=='missing'&&['slope_deg','roughness_deg'].includes(k)&&!Number.isFinite(v.scale_m))throw Error('Falta escala espacial: '+k);
   }
  }}return p;
 }
 function rank(p,target,weights,minCoverage=1){
  const active=keys.filter(k=>Number.isFinite(weights[k])&&weights[k]>0);
  return p.earth.map(site=>{let sum=0,den=0,count=0;const parts={};for(const k of active){const a=target.features?.[k],b=site.features?.[k];if(comparable(a,b)){const score=Math.max(0,1-Math.abs(a.value-b.value)/p.variables[k].tolerance);parts[k]=score;sum+=score*weights[k];den+=weights[k];count++;}else parts[k]=null;}
   return {site,parts,score:den?100*sum/den:null,count,total:active.length,coverage:active.length?count/active.length:0};
  }).filter(r=>r.score!==null&&r.coverage>=minCoverage).sort((a,b)=>b.score-a.score||b.coverage-a.coverage||a.site.id.localeCompare(b.site.id));
 }
 return {keys,usable,comparable,validate,rank};
})();
