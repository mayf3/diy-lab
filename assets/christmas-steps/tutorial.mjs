import {renderScene, esc, clamp} from './scene.mjs';
import {COURSE} from './course.generated.mjs';
const root=document.querySelector('[data-maker-course]');
if(root){
 const KEY='maker-christmas-teaching:'+COURSE.version;
 let lessonIndex=0,stepIndex=0,time=0,playing=false,last=0,raf=0,done={},storageError=false;
 const reduced=window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;
 try{const v=JSON.parse(localStorage.getItem(KEY)||'{}');if(v&&typeof v==='object')done=v;}catch{storageError=true;}
 const allSteps=COURSE.lessons.reduce((n,l)=>n+l.steps.length,0);
 const current=()=>COURSE.lessons[lessonIndex];const step=()=>current().steps[stepIndex];
 const stepKey=()=>current().id+':'+step().id;
 const isDone=()=>done[stepKey()]===true;
 const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(done));}catch{storageError=true;}};
 const count=()=>COURSE.lessons.reduce((n,l)=>n+l.steps.filter(s=>done[l.id+':'+s.id]===true).length,0);
 function stop(){playing=false;cancelAnimationFrame(raf);raf=0;last=0;}
 function draw(){const s=step(),duration=s.seconds;root.querySelector('.mk-drawing').innerHTML=renderScene(s,clamp(time/duration),time);let slider=root.querySelector('[data-action=seek]');slider.value=String(time/duration*100);slider.setAttribute('aria-valuetext',`${time.toFixed(1)} / ${duration} 秒`);root.querySelector('.mk-time').textContent=`${Math.floor(time)} / ${duration}s`;let b=root.querySelector('[data-action=play]');b.textContent=playing?'暂停':'播放';b.setAttribute('aria-pressed',String(playing));}
 function frame(t){if(!playing)return;if(!last)last=t;time=Math.min(step().seconds,time+(t-last)/1000);last=t;draw();if(time>=step().seconds){stop();draw();}else raf=requestAnimationFrame(frame);}
 function play(){if(playing){stop();draw();return;}if(time>=step().seconds)time=0;playing=true;last=0;raf=requestAnimationFrame(frame);draw();}
 function persistAndRender(){save();render();}
 function next(preview=false){if(!preview&&!isDone())return;stop();time=0;if(stepIndex+1<current().steps.length)stepIndex++;else if(lessonIndex+1<COURSE.lessons.length){lessonIndex++;stepIndex=0;}else{root.querySelector('.mk-roadmap').scrollIntoView({behavior:reduced?'auto':'smooth'});return;}render();root.querySelector('.mk-stage-head').scrollIntoView({behavior:reduced?'auto':'smooth',block:'start'});}
 function prev(){stop();time=0;if(stepIndex>0)stepIndex--;else if(lessonIndex>0){lessonIndex--;stepIndex=current().steps.length-1;}render();}
 function download(name,content,type){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([content],{type}));a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),30000);}
 function bundle(){const raw=atob(current().bundle_b64);const bytes=Uint8Array.from(raw,c=>c.charCodeAt(0));download(current().id+'-arduino-code.zip',bytes,'application/zip');}
 async function copyCode(index){const code=current().files[index].content;try{await navigator.clipboard.writeText(code);}catch{const el=document.createElement('textarea');el.value=code;document.body.appendChild(el);el.select();document.execCommand('copy');el.remove();}root.querySelector('[data-action=copy][data-file="'+index+'"]').textContent='已复制';}
 function render(){stop();const l=current(),s=step(),complete=count();
 root.innerHTML=`<div class="mk"><header class="mk-header"><div><p class="mk-eyebrow">MAKER LAB / 圣诞魔法小屋 · 动手篇</p><h1>先让第一盏灯，亮起来。</h1><p class="mk-subtitle">拿起材料，看一个动作，做一步，再看实物结果。</p></div><div class="mk-meta"><span>你已自查 <b>${complete}</b> / ${allSteps} 步</span><div class="mk-meter"><span style="width:${complete/allSteps*100}%"></span></div><small>进度只存在此浏览器</small></div></header>
 <nav class="mk-chapters" aria-label="选择制作关卡">${COURSE.lessons.map((x,i)=>`<button type="button" class="mk-chapter" data-lesson="${i}" aria-current="${i===lessonIndex}"><span class="mk-num">${x.number}</span><span><strong>${esc(x.title)}</strong><small>${x.steps.length} 个动作 · ${esc(x.outcome)}</small></span></button>`).join('')}</nav>
 <details class="mk-prep"><summary>本关拿这些 · ${l.materials.length} 项准备</summary><ul>${l.materials.map(m=>'<li>'+esc(m)+'</li>').join('')}</ul><p class="mk-prerequisite">${esc(l.prerequisite)}</p></details>
 <nav class="mk-steps" aria-label="本关步骤">${l.steps.map((x,i)=>`<button class="mk-step" type="button" data-step="${i}" data-done="${done[l.id+':'+x.id]===true}" ${i===stepIndex?'aria-current="step"':''} title="${esc(x.title)}">${done[l.id+':'+x.id]===true?'✓ ':''}${i+1}${i===stepIndex?' · '+esc(x.title):''}</button>`).join('')}</nav>
 <div class="mk-stage-head"><h2>${esc(s.title)}</h2><small>第 ${stepIndex+1} / ${l.steps.length} 步</small></div>
 <div class="mk-workspace"><section class="mk-visual" aria-label="本步操作动画"><div class="mk-drawing">${renderScene(s,time/s.seconds,time)}</div><div class="mk-caption">${esc(s.caption)}</div><div class="mk-playbar"><button type="button" class="mk-btn" data-action="play" aria-pressed="false">播放</button><button type="button" class="mk-btn" data-action="replay">重播</button><input type="range" min="0" max="100" step="0.1" value="0" data-action="seek" aria-label="本步动画进度"><span class="mk-time">0 / ${s.seconds}s</span><button type="button" class="mk-btn" data-action="zoom">放大</button></div><p class="mk-label">动画播完会停住，不会自动跳到下一步。${reduced?'已检测到减少动态效果偏好；按需手动拖动进度。':''}</p></section>
 <section class="mk-action" aria-label="你现在要做的操作"><p class="mk-kicker">现在只做这件事</p><p class="mk-action-text">${esc(s.do)}</p><div class="mk-expect"><h3>做对了，应该看到</h3><p>${esc(s.expected)}</p></div><details class="mk-help"><summary>没出现？或不确定怎么接？</summary><p>${esc(s.stop)}</p></details>${s.detail?'<p class="mk-detail">'+esc(s.detail)+'</p>':''}</section></div>
 <label class="mk-check"><input type="checkbox" data-action="check" ${isDone()?'checked':''}><span>${esc(s.check)}<small>由你观察实物后勾选；观看动画不等于完成，网站不会连接你的板子。</small></span></label>
 <div class="mk-bottom"><button type="button" class="mk-btn" data-action="prev" ${lessonIndex===0&&stepIndex===0?'disabled':''}>← 上一步</button><div class="mk-navright"><button type="button" class="mk-preview" data-action="preview">只预览下一步</button><button type="button" class="mk-btn mk-next" data-action="next" ${!isDone()?'disabled':''}>${stepIndex===l.steps.length-1?(lessonIndex===COURSE.lessons.length-1?'查看后续制作':'完成本关 · 下一关 →'):'做完了，继续 →'}</button></div></div>
 ${storageError?'<p class="mk-storage-note">此浏览器不允许保存进度；本次仍可跟做，关闭后可能丢失自查勾选。</p>':''}
 <section class="mk-resources"><h3>本关的程序与接线依据</h3><div class="mk-code-actions"><button type="button" class="mk-btn" data-action="download">下载本关代码包</button><button type="button" class="mk-btn" data-action="print">打印当前这一步</button></div><p class="mk-code-note">解压后用 Arduino IDE 打开同名文件夹里的 .ino；你不需要去 GitHub 找代码。上传前先同意覆盖旧程序。</p>${l.files.map((f,i)=>`<details class="mk-code"><summary>查看 ${esc(f.name)}</summary><div class="mk-code-actions"><button type="button" class="mk-btn" data-action="copy" data-file="${i}">复制程序</button><button type="button" class="mk-btn" data-action="file" data-file="${i}">保存此文件</button></div><pre><code>${esc(f.content)}</code></pre></details>`).join('')}
 <details class="mk-sources"><summary>官方依据与本版验证边界</summary><p>${esc(COURSE.notice)}</p><ul>${COURSE.references.filter(r=>l.refs.includes(r.id)).map(r=>`<li><a href="${esc(r.url)}" target="_blank" rel="noopener noreferrer">${esc(r.role)}</a> · 核查 ${esc(r.checked)}</li>`).join('')}</ul><p>三关仅适用于已确认的 UNO R3。第三关是四灯板单独桌面练习，不能当作最终 PIR + 音频整机供电图。</p></details></section>
 <section class="mk-roadmap"><h3>做完三关，再进入小屋的实物组装。</h3><p>接下来是帐篷到货验收与拆装 → 可拆布艺 → 真实 PIR / DFPlayer → 独立控制盒与收纳。这些器件专属步骤仍在准备，不把展示片当作已交付的制作课。</p><p>现有帐篷按随箱说明搭建；检查木杆、净尺寸、通风和拆装。灯光与电子装置始终独立于帐篷主体。</p></section>
 <footer class="mk-foot"><span>教学版 ${esc(COURSE.version)} · 原创操作示意 · 非实物录像 / 非安全认证</span><button type="button" data-action="reset">清除本机自查进度</button></footer>
 <dialog class="mk-zoom"><div class="mk-zoom-head"><strong>${esc(s.title)}</strong><button type="button" class="mk-btn" data-action="close">关闭</button></div><div class="mk-zoom-view"></div><p>${esc(s.caption)}（手机可横向拖动查看放大图。）</p></dialog></div>`;
 root.querySelectorAll('[data-lesson]').forEach(b=>b.addEventListener('click',()=>{lessonIndex=Number(b.dataset.lesson);stepIndex=0;time=0;render();}));
 root.querySelectorAll('[data-step]').forEach(b=>b.addEventListener('click',()=>{stepIndex=Number(b.dataset.step);time=0;render();}));
 root.querySelector('[data-action=check]').addEventListener('change',e=>{done[stepKey()]=e.target.checked;save();root.querySelector('[data-action=next]').disabled=!e.target.checked;root.querySelector('.mk-meta b').textContent=count();root.querySelector('.mk-meter span').style.width=count()/allSteps*100+'%';root.querySelector(`[data-step="${stepIndex}"]`).dataset.done=e.target.checked;});
 root.querySelector('[data-action=play]').onclick=play;root.querySelector('[data-action=replay]').onclick=()=>{stop();time=0;play();};
 root.querySelector('[data-action=seek]').addEventListener('input',e=>{stop();time=Number(e.target.value)/100*s.seconds;draw();});
 root.querySelector('[data-action=prev]').onclick=prev;root.querySelector('[data-action=next]').onclick=()=>next();root.querySelector('[data-action=preview]').onclick=()=>next(true);
 root.querySelector('[data-action=download]').onclick=bundle;root.querySelector('[data-action=print]').onclick=()=>window.print();
 root.querySelectorAll('[data-action=copy]').forEach(b=>b.onclick=()=>copyCode(Number(b.dataset.file)));root.querySelectorAll('[data-action=file]').forEach(b=>b.onclick=()=>{let f=l.files[Number(b.dataset.file)];download(f.name,f.content,'text/plain;charset=utf-8');});
 root.querySelector('[data-action=zoom]').onclick=()=>{stop();draw();const d=root.querySelector('dialog');root.querySelector('.mk-zoom-view').innerHTML=renderScene(s,1,s.seconds-1);d.showModal();};root.querySelector('[data-action=close]').onclick=()=>root.querySelector('dialog').close();
 root.querySelector('[data-action=reset]').onclick=()=>{if(window.confirm('只清除这个浏览器的自查勾选，不会影响硬件。继续？')){done={};persistAndRender();}};
 draw();
 }
 render();
 document.addEventListener('visibilitychange',()=>{if(document.hidden){stop();draw();}});
 // Exposed only for deterministic, read-only browser QA, never a hardware bridge.
 window.MakerLessonQA={getState:()=>({lesson:current().id,step:step().id,time,playing,completed:count()}),version:COURSE.version};
}
