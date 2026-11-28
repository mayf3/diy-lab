#!/usr/bin/env python3
"""从 G2-0 输出的 STL 生成自包含可旋转查看页（纯标准库，产物零依赖）。

读取 source-data/agent-button-deck/pcba-v1/cad/renders/case-r1/*.stl，
写入 workbench/web/case-r1-viewer.html（内嵌网格数据 + 原生 canvas 渲染）。
运行：python3 workbench/build_case_viewer.py
"""
from __future__ import annotations

import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "source-data/agent-button-deck/pcba-v1/cad/renders/case-r1"
TARGET = ROOT / "workbench/web/case-r1-viewer.html"

PARTS = [  # (STL 名, 显示名, 十六进制颜色)
    ("case-r1-body", "主体 · 奶油白", "fff9e9"),
    ("case-r1-base", "底座 · 薰衣草紫", "b7a4e3"),
    ("case-r1-cap-a", "键帽 K1 · 珊瑚橙", "ff8f7a"),
    ("case-r1-cap-b", "键帽 K2 · 星空蓝", "6f9cdf"),
    ("case-r1-cap-c", "键帽 K3 · 薄荷绿", "8ad9b2"),
    ("case-r1-cap-d", "键帽 K4 · 暖黄", "ffd45e"),
]


def read_stl(path: Path) -> list:
    """返回三角面 [(ax,ay,az,bx,by,bz,cx,cy,cz), ...]；支持二进制/ASCII。"""
    data = path.read_bytes()
    if len(data) - 84 >= 84:
        n = struct.unpack("<I", data[80:84])[0]
        if 84 + n * 50 == len(data) and n > 0:
            tris = []
            for i in range(n):
                off = 84 + i * 50
                v = struct.unpack("<12f", data[off:off + 48])
                tris.append(v[3:])
            return tris
    verts, tris = [], []
    cur = []
    for line in data.decode("utf-8", "ignore").splitlines():
        t = line.split()
        if t[:1] == ["vertex"]:
            cur.append(tuple(float(x) for x in t[1:4]))
            if len(cur) == 3:
                tris.append(cur[0] + cur[1] + cur[2])
                cur = []
    del verts
    return tris


def build() -> None:
    meshes = {}
    for name, label, color in PARTS:
        stl = SRC / f"{name}.stl"
        if not stl.is_file():
            raise SystemExit(f"缺少 {stl}（先运行 freecadcmd g2-case-r1.py）")
        tris = read_stl(stl)
        if not tris:
            raise SystemExit(f"{stl} 没有解析到三角面")
        xs = [v for t in tris for v in (t[0], t[3], t[6])]
        ys = [v for t in tris for v in (t[1], t[4], t[7])]
        meshes[name] = {"label": label, "color": color, "tris": tris,
                        "extent": [min(xs), max(xs), min(ys), max(ys)]}
        print(f"{name}: {len(tris)} faces")

    placeholders = (SRC / "placeholders.json")
    place_note = json.loads(placeholders.read_text())["rule"] if placeholders.is_file() else ""
    dims = json.loads((SRC / "dims.json").read_text()) if (SRC / "dims.json").is_file() else {}
    checks = json.loads((SRC / "checks.json").read_text()) if (SRC / "checks.json").is_file() else {}

    # 工作台静态服务对页面启用 script-src 'self'，内联脚本会被拦——
    # 因此数据与渲染逻辑必须是同源外链文件。
    data_path = TARGET.with_name("case-r1-viewer-data.js")
    js_path = TARGET.with_name("case-r1-viewer.js")
    data_path.write_text(
        "// 由 build_case_viewer.py 生成：外壳网格/尺寸来源/检查结果（勿手改）\n"
        "const CASE_DATA=" + json.dumps(meshes, separators=(",", ":")) + ";\n"
        "const CASE_DIMS=" + json.dumps(dims.get("sources", {}), ensure_ascii=False, separators=(",", ":")) + ";\n"
        "const CASE_CHECKS=" + json.dumps(checks, separators=(",", ":")) + ";\n")
    js_path.write_text(RENDERER_JS.replace("__PLACE__", place_note))
    page = TEMPLATE.replace("__PLACE__", place_note)
    TARGET.write_text(page)
    print(f"Built {TARGET} ({TARGET.stat().st_size} bytes) + "
          f"{data_path.name} ({data_path.stat().st_size}) + {js_path.name} ({js_path.stat().st_size})")


TEMPLATE = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Space Buddy R1 · G2-0 外壳第一版（可旋转查看）</title>
<style>
:root{--bg:#12131a;--panel:#1d1f2b;--ink:#f2f1ec;--dim:#9aa0b5;--line:#33364a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.6 system-ui,-apple-system,"PingFang SC",sans-serif}
header{padding:18px 22px 10px}h1{font-size:19px;margin:0 0 4px}
.note{color:var(--dim);font-size:13px}
#stage{position:relative;height:70vh;min-height:420px;cursor:grab;touch-action:none}
#stage:active{cursor:grabbing}canvas{width:100%;height:100%;display:block}
#hud{position:absolute;left:14px;bottom:12px;color:var(--dim);font-size:12px}
#panel{padding:12px 22px 24px;display:flex;flex-wrap:wrap;gap:10px;background:var(--panel);
border-top:1px solid var(--line)}
button{background:#262a3d;color:var(--ink);border:1px solid var(--line);border-radius:9px;
padding:7px 12px;font-size:13px;cursor:pointer}
button.off{opacity:.35;text-decoration:line-through}
#tables{padding:0 22px 28px;display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media (max-width:900px){#tables{grid-template-columns:1fr}}
table{border-collapse:collapse;width:100%;font-size:13px;background:var(--panel);border-radius:10px;overflow:hidden}
caption{text-align:left;font-weight:600;padding:10px 12px 6px;color:var(--ink)}
th,td{text-align:left;padding:7px 10px;border-top:1px solid var(--line);vertical-align:top;color:var(--dim)}
th{color:var(--ink);white-space:nowrap;font-weight:600}
td.ok{color:#7fd39a}td.warn{color:#e8b96d}td.hold{color:#9aa0b5}
@media print{#stage{height:auto}}
</style>
</head>
<body>
<header>
<h1>Space Buddy R1 · 外壳第一版（G2-0）</h1>
<p class="note">拖动旋转 · 滚轮/双指缩放 · 点击下方按钮显隐零件。占位说明：__PLACE__</p>
</header>
<div id="stage"><canvas id="cv"></canvas><div id="hud">鼠标拖动旋转，滚轮缩放</div></div>
<div id="panel"></div>
<div id="tables"></div>
<script src="case-r1-viewer-data.js"></script>
<script src="case-r1-viewer.js"></script>
</body></html>
"""

RENDERER_JS = """// 由 build_case_viewer.py 生成：G2-0 外壳查看器（勿手改）
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
  const arr=cells.match(/<td[\\s\\S]*?<\\/td>/g)||[];
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
"""

if __name__ == "__main__":
    build()
