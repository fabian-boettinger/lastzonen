const fs = require('fs');
const src = fs.readFileSync(process.argv[2], 'utf8');
const part = src.slice(src.indexOf('/* ---------- Namensabgleich'), src.indexOf('function quelle'));
global.ZONEN = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
eval(part.replace(/^const /gm, 'var ').replace(/^function (\w+)/gm, 'global.$1 = function $1'));
const T = [
  ['Coburg Stadt mit AGS', {land:'BY',kf:true,kreis:'Coburg',gem:'Coburg',ags:'09463000',regbez:'Oberfranken'}],
  ['Coburg Stadt ohne AGS', {land:'BY',kf:true,kreis:'Coburg',gem:'Coburg',regbez:'Oberfranken'}],
  ['Rödental LK Coburg', {land:'BY',kf:false,kreis:'Landkreis Coburg',gem:'Rödental',regbez:'Oberfranken'}],
  ['Braunlage', {land:'NI',kf:false,kreis:'Landkreis Goslar',gem:'Braunlage'}],
  ['Balje', {land:'NI',kf:false,kreis:'Landkreis Stade',gem:'Balje'}],
  ['Freiburg i.Br.', {land:'BW',kf:true,kreis:'Freiburg im Breisgau',gem:'Freiburg im Breisgau',regbez:'Regierungsbezirk Freiburg'}],
  ['Isny', {land:'BW',kf:false,kreis:'Landkreis Ravensburg',gem:'Isny im Allgäu',regbez:'Regierungsbezirk Tübingen'}],
  ['Sebnitz', {land:'SN',kf:false,kreis:'Landkreis Sächsische Schweiz-Osterzgebirge',gem:'Sebnitz'}],
  ['Darmstadt', {land:'HE',kf:true,kreis:'Darmstadt',gem:'Darmstadt',ags:'06411000'}],
  ['Wernigerode', {land:'ST',kf:false,kreis:'Landkreis Harz',gem:'Wernigerode'}],
  ['Springe', {land:'NI',kf:false,kreis:'Region Hannover',gem:'Springe'}],
  ['Gladbeck', {land:'NW',kf:false,kreis:'Kreis Recklinghausen',gem:'Gladbeck',ags:'05562014'}],
  ['Kleve Stadt', {land:'NW',kf:false,kreis:'Kreis Kleve',gem:'Kleve',ags:'05154036'}],
  ['Garmisch', {land:'BY',kf:false,kreis:'Landkreis Garmisch-Partenkirchen',gem:'Garmisch-Partenkirchen',regbez:'Oberbayern'}],
  ['Miesbach Bayrischzell', {land:'BY',kf:false,kreis:'Landkreis Miesbach',gem:'Bayrischzell',regbez:'Oberbayern'}],
  ['Gera', {land:'TH',kf:true,kreis:'Gera',gem:'Gera'}],
  ['Rostock', {land:'MV',kf:true,kreis:'Rostock',gem:'Rostock'}],
  ['Berlin', {land:'BE',kf:true,kreis:'Berlin',gem:'Berlin'}],
];
for (const [n, loc] of T) {
  const out = ['schnee','wind','erdbeben'].map(t => { const r = lookup(t, loc); return r && r.best ? `${t[0]}=${r.best.zone}${r.best.sk?'(sk '+r.best.sk+')':''}${r.best.tiefland?'T':''}[${r.score}]${r.alts.length?'+'+r.alts.length+'alt':''}` : `${t[0]}=?`; });
  console.log(n.padEnd(24), out.join('  '));
}
