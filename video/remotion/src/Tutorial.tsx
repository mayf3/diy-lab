import React from 'react';
import {AbsoluteFill, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

export type Scene={
 id:string;seconds:number;label:string;title:string;bullets:string[];narration:string;
 evidence:string;action_ref:string;evidence_ref:string;diagram?:string;image_src?:string
};
export type Tutorial={
 project:string;title:string;video_id:string;width:number;height:number;fps:number;
 kind:'digital-simulation'|'technical-schematic';disclosure:string;source_page:string;scenes:Scene[]
};

const COLOR={bg:'#101b29',light:'#f6f7f7',mint:'#76d7bd',secondary:'#b7c7d2',gold:'#ffd08b',card:'#213447'};
const font='PingFang SC, Heiti SC, Microsoft YaHei, Noto Sans CJK SC, sans-serif';

const Diagram:React.FC<{mode:string}>=({mode})=>{
 const line={stroke:COLOR.mint,strokeWidth:5,fill:'none',strokeLinecap:'round' as const};
 const label=(x:number,y:number,text:string,size=24)=> <text x={x} y={y} fill={COLOR.light} fontFamily={font} fontSize={size} fontWeight={600} textAnchor="middle">{text}</text>;
 return <svg viewBox="0 0 600 400" style={{width:'100%',height:'100%',filter:'drop-shadow(0 12px 18px rgba(0,0,0,.2))'}} role="img" aria-label={'抽象示意图：'+mode}>
 {mode==='device'&&<><rect x="150" y="48" width="300" height="305" rx="42" fill="#294355" stroke={COLOR.mint} strokeWidth="7"/><rect x="190" y="75" width="218" height="205" rx="18" fill="#0d1d2d"/><ellipse cx="294" cy="170" rx="78" ry="55" fill="#8fd8c4"/><circle cx="260" cy="159" r="8" fill="#203646"/><circle cx="330" cy="159" r="8" fill="#203646"/><path d="M260 197 Q300 218 336 194" {...line}/><g fill="#8ac9b4"><circle cx="230" cy="314" r="13"/><circle cx="290" cy="314" r="13"/><circle cx="350" cy="314" r="13"/></g></>}
 {mode==='chip'&&<><rect x="175" y="90" width="250" height="210" rx="15" fill="#305063" stroke={COLOR.mint} strokeWidth="6"/>{Array.from({length:7},(_,i)=><g key={i} stroke={COLOR.gold} strokeWidth="7"><path d={`M${155} ${115+i*27}h20`}/><path d={`M425 ${115+i*27}h20`}/></g>)}{label(300,186,'ESP32-P4',34)}{label(300,235,'v1  /  v3 ?',32)}</>}
 {mode==='ribbon'&&<><rect x="28" y="126" width="180" height="145" rx="12" fill="#305266"/><rect x="390" y="126" width="180" height="145" rx="12" fill="#305266"/>{Array.from({length:11},(_,i)=><path key={i} d={`M208 ${145+i*10}C275 ${145+i*10} 335 ${170+i*10} 390 ${170+i*10}`} stroke={i%2===0?COLOR.gold:COLOR.mint} strokeWidth="4" fill="none"/>)}{label(115,309,'ESP32-P4',22)}{label(482,309,'MIPI-DSI',22)}{label(300,87,'22P · FFC ?',30)}</>}
 {mode==='pcb'&&<><rect x="94" y="42" width="420" height="310" rx="16" fill="#265b52" stroke="#87d7ab" strokeWidth="5"/><path d="M135 75h320v230H135z" stroke="#a6b98b" strokeWidth="2" fill="none"/>{[170,278,384].map(x=><g key={x}><rect x={x} y="110" width="66" height="66" rx="7" fill="#b4cbba" stroke="#e6eee1" strokeWidth="4"/><rect x={x+12} y="122" width="42" height="42" rx="6" fill="#6c9980"/></g>)}<circle cx="306" cy="256" r="53" fill="#354d5a" stroke="#d1e9ce" strokeWidth="4"/><circle cx="306" cy="256" r="22" fill="#759d9b"/>{label(310,385,'PCB_V1.2 · 待核对',22)}</>}
 {mode==='route'&&<><rect x="60" y="66" width="480" height="75" rx="18" fill="#285c54"/>{label(300,112,'获得可装配的外壳',28)}{['自有打印机','借用设备','代打印服务'].map((s,i)=><g key={s}><rect x={24+i*198} y="225" width="175" height="95" rx="15" fill="#294357" stroke={COLOR.mint} strokeWidth="3"/>{label(111+i*198,281,s,22)}<path d={`M300 141 L300 180 L${111+i*198} 180 L${111+i*198} 225`} {...line}/></g>)}</>}
 {mode==='gate'&&<><rect x="165" y="173" width="270" height="151" rx="23" fill="#4d4644" stroke={COLOR.gold} strokeWidth="6"/><path d="M223 173v-55a77 77 0 01154 0v55" stroke={COLOR.gold} strokeWidth="16" fill="none"/>{label(300,257,'HOLD',49)}</>}
 {mode==='check'&&<><rect x="134" y="54" width="338" height="312" rx="16" fill="#2b4152" stroke={COLOR.mint} strokeWidth="5"/>{[113,195,277].map((y,i)=><g key={y}><rect x="164" y={y-25} width="38" height="38" rx="4" {...line}/><path d={`M169 ${y-7}l11 10 20-25`} stroke={COLOR.mint} fill="none" strokeWidth="5"/><path d={`M225 ${y-2}h196`} stroke={COLOR.secondary} strokeWidth="9" strokeLinecap="round"/></g>)}</>}
 </svg>;
};

const Stage:React.FC<{scene:Scene;index:number;total:number;frames:number;tutorial:Tutorial}>=({scene,index,total,frames,tutorial})=>{
 const frame=useCurrentFrame();
 const {fps}=useVideoConfig();
 const intro=spring({frame,fps,config:{damping:17,stiffness:100}});
 const fade=interpolate(frame,[0,8,Math.max(9,frames-10),frames],[0,1,1,0],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
 const pan=interpolate(frame,[0,frames],[1.015,1.075],{extrapolateRight:'clamp'});
 const isFirst=index===0;
 return <AbsoluteFill style={{background:COLOR.bg,color:COLOR.light,fontFamily:font,opacity:fade,overflow:'hidden'}}>
  <AbsoluteFill style={{background:'radial-gradient(circle at 78% 18%, rgba(45,106,103,.28),transparent 44%)'}}/>
  <div style={{position:'absolute',left:52,top:38,background:'#1d5550',borderRadius:50,padding:'9px 24px',fontSize:21,letterSpacing:2,color:COLOR.mint}}>MAKER LAB  /  {tutorial.kind==='digital-simulation'?'BLENDER G0':'HACHIMODOCK'}</div>
  <div style={{position:'absolute',right:54,top:42,fontSize:23,color:COLOR.secondary}}>{String(index+1).padStart(2,'0')} / {String(total).padStart(2,'0')}</div>
  <div style={{position:'absolute',left:55,top:115,right:50,fontSize:isFirst?57:46,lineHeight:1.18,fontWeight:800,transform:`translateY(${(1-intro)*22}px)`,opacity:intro}}>{scene.title}</div>
  <div style={{position:'absolute',left:54,top:218,width:760,height:388,background:'#e7ebec',borderRadius:22,overflow:'hidden',display:'flex',alignItems:'center',justifyContent:'center',boxShadow:'0 18px 45px rgba(0,0,0,.25)'}}>
    {scene.image_src?<Img src={staticFile('images/'+scene.image_src)} style={{width:'100%',height:'100%',objectFit:'contain',transform:`scale(${pan})`}}/>:<div style={{width:'94%',height:'96%',background:'#182939',borderRadius:16,display:'flex',alignItems:'center',justifyContent:'center'}}><Diagram mode={scene.diagram||'device'}/></div>}
    <div style={{position:'absolute',bottom:13,left:14,fontSize:18,background:'#162838',color:COLOR.gold,padding:'6px 13px',borderRadius:10}}>{tutorial.kind==='digital-simulation'?'G0 数字模型 · 非实物':'原创结构示意 · 非实物'}</div>
  </div>
  <div style={{position:'absolute',left:837,top:218,right:52,bottom:114,background:COLOR.card,borderRadius:22,padding:'24px 25px',boxSizing:'border-box'}}>
   <div style={{fontSize:23,color:COLOR.mint,marginBottom:26}}>{scene.label}</div>
   {scene.bullets.map((bullet,i)=>{const ease=spring({frame:Math.max(0,frame-i*7),fps,config:{damping:20,stiffness:130}});return <div key={i} style={{display:'flex',alignItems:'flex-start',gap:14,marginBottom:26,opacity:ease,transform:`translateX(${(1-ease)*20}px)`,fontSize:25,lineHeight:1.37}}><span style={{color:COLOR.mint,fontWeight:800}}>•</span><span>{bullet}</span></div>;})}
  </div>
  <div style={{position:'absolute',left:58,top:615,right:62,display:'flex',justifyContent:'space-between',fontSize:18,color:COLOR.secondary}}><span>依据：{scene.evidence}</span><span>{tutorial.kind==='digital-simulation'?'数字模拟':'上游资料与兼容性疑点'} · {scene.action_ref}</span></div>
  <div style={{position:'absolute',left:54,right:54,bottom:22,height:8,borderRadius:5,background:'#35505a',overflow:'hidden'}}><div style={{height:'100%',width:`${((index+1)/total)*100}%`,background:COLOR.mint,borderRadius:5}}/></div>
  <div style={{position:'absolute',bottom:41,left:57,right:55,color:COLOR.gold,fontSize:16}}>{tutorial.disclosure}</div>
 </AbsoluteFill>;
};

export const TutorialVideo:React.FC<{tutorial:Tutorial}>=({tutorial})=>{
 let offset=0;
 return <AbsoluteFill style={{background:COLOR.bg}}>
  {tutorial.scenes.map((scene,i)=>{
    const frames=Math.round(scene.seconds*tutorial.fps);
    const start=offset;
    offset+=frames;
    return <Sequence key={scene.id} from={start} durationInFrames={frames}><Stage scene={scene} index={i} total={tutorial.scenes.length} frames={frames} tutorial={tutorial}/></Sequence>;
  })}
 </AbsoluteFill>;
};
