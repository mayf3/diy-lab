// 由 build_case_viewer.py 生成：G2-0 外壳查看器（勿手改）
const cv=document.getElementById('cv'),ctx=cv.getContext('2d');
const panel=document.getElementById('panel');
const DATA=typeof CASE_DATA!=='undefined'?CASE_DATA:{};
let visible={},rotX=-0.55,rotZ=0.55,zoom=1,NSCALE=1;
function norm(meshes){
  let mn=[1e9,1e9,1e9],mx=[-1e9,-1e9,-1e9];
  for(const k in meshes)for(const t of meshes[k].tris)for(let i=0;i<3;i++){
    const p=[t[i*3],t[i*3+1],t[i*3+2]];
    for(let a=0;a<3;a++){mn[a]=Math.min(mn[a],p[a]);mx[a]=Math.max(mx[a],p[a]);}
  }
  const c=[(mn[0]+mx[0])/2,(mn[1]+mx[1])/2,(mn[2]+mx[2])/2];
  const s=2/Math.max(mx[0]-mn[0],mx[1]-mn[1],mx[2]-mn[2]);
  NSCALE=s;
  for(const k in meshes){
    const z=meshes[k].z=[],nx=meshes[k].nx=[],ny=[],nz=[],tr=meshes[k].tris;
    for(const t of tr){
      const P=[];
      for(let i=0;i<3;i++){
        const x=(t[i*3]-c[0])*s,y=(t[i*3+1]-c[1])*s,zz=(t[i*3+2]-c[2])*s;
        P.push([x,y,zz]);
      }
      z.push((P[0][2]+P[1][2]+P[2][2])/3);
      const u=[P[1][0]-P[0][0],P[1][1]-P[0][1],P[1][2]-P[0][2]],
            v=[P[2][0]-P[0][0],P[2][1]-P[0][1],P[2][2]-P[0][2]];
      nx.push(u[1]*v[2]-u[2]*v[1]);ny.push(u[2]*v[0]-u[0]*v[2]);
      nz.push(u[0]*v[1]-u[1]*v[0]);
    }
    meshes[k].ny=ny;meshes[k].nz=nz;
  }
  return c;
}
const center=norm(DATA);
function render(){
  const dpr=devicePixelRatio||1,W=cv.clientWidth,H=cv.clientHeight;
  if(cv.width!==Math.round(W*dpr)){cv.width=Math.round(W*dpr);cv.height=Math.round(H*dpr);}
  ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.fillStyle='#12131a';ctx.fillRect(0,0,W,H);
  const cx=W/2,cy=H/2,sc=Math.min(W,H)*0.42*zoom,cosX=Math.cos(rotX),sinX=Math.sin(rotX),
        cosZ=Math.cos(rotZ),sinZ=Math.sin(rotZ);
  const faces=[];
  for(const k in DATA){
    if(!visible[k])continue;
    const m=DATA[k],tr=m.tris,nx=m.nx,ny=m.ny,nz=m.nz||[];
    const rgb=[parseInt(m.color.slice(0,2),16),parseInt(m.color.slice(2,4),16),parseInt(m.color.slice(4,6),16)];
    for(let i=0;i<tr.length;i++){
      // 背面剔除：法线随视角旋转后朝向观察者（z2n>0）才绘制
      if(nz.length){
        const x1n=cosZ*nx[i]-sinZ*ny[i],y1n=sinZ*nx[i]+cosZ*ny[i];
        if(sinX*y1n+cosX*nz[i]<=0)continue;
      }
      const t=tr[i];const P=[];
      for(let j=0;j<3;j++){
        let x=(t[j*3]-center[0])*NSCALE,y=(t[j*3+1]-center[1])*NSCALE,zz=(t[j*3+2]-center[2])*NSCALE;
        let x1=cosZ*x-sinZ*y,y1=sinZ*x+cosZ*y;
        let y2=cosX*y1-sinX*zz,z2=sinX*y1+cosX*zz;
        P.push([cx+x1*sc,cy-y2*sc,z2]);
      }
      const depth=(P[0][2]+P[1][2]+P[2][2])/3;
      let nyr=sinZ*nx[i]+cosZ*ny[i];
      let shade=0.55+0.45*Math.abs(nyr)/(Math.hypot(nx[i],ny[i])+1e-9);
      faces.push({depth,p:P,c:rgb.map(v=>Math.max(0,Math.min(255,v*shade)))});
    }
  }
  faces.sort((a,b)=>a.depth-b.depth);
  for(const f of faces){
    ctx.fillStyle=`rgb(${f.c[0]|0},${f.c[1]|0},${f.c[2]|0})`;
    ctx.strokeStyle=ctx.fillStyle;ctx.lineWidth=0.6;
    ctx.beginPath();ctx.moveTo(f.p[0][0],f.p[0][1]);
    ctx.lineTo(f.p[1][0],f.p[1][1]);ctx.lineTo(f.p[2][0],f.p[2][1]);ctx.closePath();
    ctx.fill();ctx.stroke();
  }
}
for(const k in DATA){
  visible[k]=true;
  const b=document.createElement('button');b.textContent=DATA[k].label;
  b.onclick=()=>{visible[k]=!visible[k];b.classList.toggle('off');render();};
  panel.appendChild(b);
}
// 尺寸来源表 + 几何检查表（数据来自 dims.json / checks.json）
(function(){
  const host=document.getElementById('tables');
  const tag={'confirmed-official':['已确认·官方','ok'],'awaiting-measure':['待实物实测','warn'],'placeholder':['视觉占位','hold']};
  const names={'board_outline':'PCB 板框','usb_zone_8mm':'图纸 8.00mm 含义','connector_protrusion':'连接器板外突出','board_envelope':'整板最大包络','usb_types':'接口类型（J2/J4）','usb_ports':'USB 口中心距','usb_opening':'USB 开孔','usb_plug_envelope':'插头通过包络','skirt_usb_clearance':'裙壁避让','body':'主体外形','keys':'键帽机构','boss':'PCB 螺柱'};
  let rows='';
  for(const k in CASE_DIMS){
    const d=CASE_DIMS[k],t=tag[d.status]||[d.status,'hold'];
    rows+=`<tr><th>${names[k]||k}</th><td class='${t[1]}'>${t[0]}</td><td>${d.value||''}`;
    if(d.awaiting)rows+=`<br><span style='opacity:.75'>等：${d.awaiting}</span>`;
    rows+=`<br><span style='opacity:.6'>依据：${d.ref||''}</span></td></tr>`;
  }
  const C=CASE_CHECKS.checks||{};
  let cells='';
  for(const k in C){
    const v=C[k];
    const bad=(typeof v==='boolean')?(!v):(Math.abs(v)>1e-6);
    cells+=`<td class='${bad?'warn':'ok'}'>${k} = ${v}${k.indexOf('interference')>=0?' mm³':''}</td>`;
  }
  let checkRows='';
  const arr=cells.match(/<td[\s\S]*?<\/td>/g)||[];
  for(let i=0;i<arr.length;i+=2)checkRows+='<tr>'+arr.slice(i,i+2).join('')+'</tr>';
  host.innerHTML=
    `<table><caption>哪些尺寸已确定、哪些在等实物（G2-1）</caption>${rows}</table>`+
    `<table><caption>几何检查（每次修改自动重跑）</caption>${checkRows}</table>`;
})();
// 爆炸视图：键帽上移、主体微升、底座不动（G2-3 五视图之一）
const EXPLODE={ 'case-r1-cap-a':22,'case-r1-cap-b':22,'case-r1-cap-c':22,'case-r1-cap-d':22,'case-r1-body':9,'case-r1-base':0 };
const ORIG={}; for(const k in DATA){ ORIG[k]=DATA[k].tris.map(r=>r.slice()); }
let exploded=false;
const xb=document.createElement('button'); xb.textContent='爆炸视图';
xb.onclick=()=>{
  exploded=!exploded;
  for(const k in EXPLODE) if(DATA[k]){
    const off=exploded?EXPLODE[k]:0;
    DATA[k].tris=ORIG[k].map(t2=>[t2[0],t2[1],t2[2]+off,t2[3],t2[4],t2[5]+off,t2[6],t2[7],t2[8]+off]);
  }
  norm(DATA); render();
};
panel.appendChild(xb);
let drag=null;
cv.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY};cv.setPointerCapture(e.pointerId);});
cv.addEventListener('pointermove',e=>{if(!drag)return;
  rotZ+=(e.clientX-drag.x)*0.011;rotX+=(e.clientY-drag.y)*0.011;
  rotX=Math.max(-1.4,Math.min(1.4,rotX));drag={x:e.clientX,y:e.clientY};render();});
cv.addEventListener('pointerup',()=>drag=null);
cv.addEventListener('wheel',e=>{e.preventDefault();
  zoom=Math.max(0.4,Math.min(4,zoom*(e.deltaY<0?1.12:0.9)));render();},{passive:false});
addEventListener('resize',render);
render();
