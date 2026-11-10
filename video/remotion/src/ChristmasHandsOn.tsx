import React from 'react';
import {AbsoluteFill,interpolate,useCurrentFrame} from 'remotion';
// The website and video share one versioned process and one vector scene renderer.
// @ts-ignore -- source-owned ESM module in the repository's plain-browser package.
import {COURSE} from '../../../assets/christmas-steps/course.generated.mjs';
// @ts-ignore -- source-owned SVG renderer reused unchanged across both outputs.
import {renderScene} from '../../../assets/christmas-steps/scene.mjs';

type Step = {
  id: string;title:string;scene:string;seconds:number;do:string;expected:string;caption:string
};
type Lesson = {number:string;title:string;outcome:string;steps:Step[]};

export const LESSON = COURSE.lessons[0] as Lesson;
export const HANDS_ON_FPS = 24;
export const DURATION = LESSON.steps.reduce((n,s)=>n+Math.round(s.seconds*HANDS_ON_FPS),0);
const F='PingFang SC, Noto Sans SC, Heiti SC, Microsoft YaHei, sans-serif';
const INK='#223b30', MINT='#4f896d', PAPER='#f3f5ee';

export const ChristmasHandsOn:React.FC = () => {
  const frame=useCurrentFrame();
  let index=0,offset=0;
  for(let i=0;i<LESSON.steps.length;i++){
    const frames=Math.round(LESSON.steps[i].seconds*HANDS_ON_FPS);
    if(frame<offset+frames){index=i;break;}
    offset+=frames;
  }
  const s=LESSON.steps[index];
  const localFrame=frame-offset;
  const progress=Math.min(1,localFrame/(s.seconds*HANDS_ON_FPS));
  const fade=interpolate(localFrame,[0,10,Math.round(s.seconds*HANDS_ON_FPS)-10,Math.round(s.seconds*HANDS_ON_FPS)],[0,1,1,.6],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const svg=renderScene(s,progress,localFrame/HANDS_ON_FPS);
  return <AbsoluteFill style={{background:PAPER,color:INK,fontFamily:F,overflow:'hidden',padding:40,boxSizing:'border-box'}}>
    <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',height:45}}>
      <div style={{fontSize:18,fontWeight:800,color:MINT,letterSpacing:2}}>MAKER LAB / 一步一步动手做</div>
      <div style={{fontSize:18,color:'#6b7f71'}}>圣诞魔法小屋 · {LESSON.number} / {String(index+1).padStart(2,'0')}</div>
    </div>
    <div style={{height:98,display:'flex',alignItems:'center'}}>
      <div style={{fontSize:42,fontWeight:800,lineHeight:1.25}}>{s.title}</div>
    </div>
    <div style={{display:'flex',gap:25,height:450,opacity:fade}}>
      <div style={{width:760,height:444,flexShrink:0,borderRadius:18,overflow:'hidden',border:'2px solid #d9e2d7',background:'#fff'}} dangerouslySetInnerHTML={{__html:svg}}/>
      <div style={{flex:1,display:'flex',flexDirection:'column',justifyContent:'center',gap:27}}>
        <div>
          <div style={{color:MINT,fontSize:20,fontWeight:800,marginBottom:12}}>现在只做这一件</div>
          <div style={{fontSize:25,fontWeight:700,lineHeight:1.48,wordBreak:'break-word'}}>{s.do}</div>
        </div>
        <div style={{background:'#e5eee1',padding:'19px 20px',borderLeft:'5px solid #82a77e',borderRadius:10}}>
          <div style={{fontSize:19,fontWeight:800,marginBottom:6}}>做对了，应该看到</div>
          <div style={{fontSize:21,lineHeight:1.45}}>{s.expected}</div>
        </div>
      </div>
    </div>
    <div style={{height:12,background:'#e0e8de',borderRadius:9,marginTop:25,overflow:'hidden'}}>
      <div style={{width:`${(frame+1)/DURATION*100}%`,height:12,background:MINT}}/>
    </div>
    <div style={{display:'flex',justifyContent:'space-between',fontSize:15,color:'#6a8070',marginTop:13}}>
      <span>原创矢量示意 · 不是实物录像 · 动手前请先断开电源</span>
      <span>{index+1} / {LESSON.steps.length} 步 · 完整可暂停版见网站</span>
    </div>
  </AbsoluteFill>;
};
