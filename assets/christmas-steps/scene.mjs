/* One deterministic drawing function shared by the browser lesson and Remotion.
   These are original teaching diagrams, never a screenshot or a sensor reading. */
export const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
export const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const C={ink:'#20372f',muted:'#69776e',board:'#426b5b',gold:'#e6ba61',paper:'#f4f5ef',signal:'#348c77',power:'#b4523c',ground:'#3b4541',off:'#6b7764'};
const text=(x,y,s,size=24,color=C.ink,anchor='start',weight=500)=>`<text x="${x}" y="${y}" font-size="${size}" fill="${color}" text-anchor="${anchor}" font-weight="${weight}">${esc(s)}</text>`;
const line=(d,color=C.ground,width=5,progress=1)=>`<path d="${d}" fill="none" stroke="${color}" stroke-width="${width}" stroke-linecap="round" stroke-linejoin="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="${1-clamp(progress)}"/>`;
const halo=(x,y,p=1,r=20)=>`<circle cx="${x}" cy="${y}" r="${r+4*Math.sin(p*Math.PI)}" fill="${C.gold}" fill-opacity=".16" stroke="${C.gold}" stroke-width="3"/>`;
const tag=(x,y,s,color=C.ink)=>`<rect x="${x}" y="${y-27}" width="${Math.max(92,s.length*23+28)}" height="42" rx="10" fill="white" stroke="#dce3d9"/>${text(x+14,y+2,s,22,color)}`;
const pinsTop=['AREF','GND','13','12','11','10','9','8','7','6','5','4','3','2','1','0'];
export const PINS={D2:[464,145],D6:[392,145],GND:[281,355],V5:[257,355]};
function board({on=false,l=false,usb=false,focus='',p=1}={}){
 let s=`<g aria-label="UNO R3 引脚简化示意"><path d="M107 125 H510 L535 150 V365 L516 385 H107 Q90 385 90 368 V144 Q90 125 107 125Z" fill="${C.board}" stroke="#315044" stroke-width="3"/>`;
 s+=[ [111,146],[510,149],[112,365],[510,365] ].map(([x,y])=>`<circle cx="${x}" cy="${y}" r="7" fill="${C.paper}" stroke="#b6c0ab" stroke-width="3"/>`).join('');
 s+=`<rect x="78" y="175" width="67" height="67" rx="5" fill="#c9cecb" stroke="#76867d" stroke-width="2"/><rect x="82" y="185" width="30" height="47" fill="#3f4943" rx="4"/><rect x="134" y="293" width="45" height="37" rx="4" fill="#243b31"/><circle cx="146" cy="311" r="9" fill="#101e19"/><rect x="277" y="235" width="182" height="55" rx="4" fill="#263e32"/>`;
 for(let i=0;i<14;i++)s+=`<path d="M${284+i*12} 229v6m0 55v7" stroke="#b0b7a8" stroke-width="3"/>`;
 s+=text(370,270,'ATmega328P',17,'#d8dfd4','middle');
 s+=text(380,206,'UNO R3',35,'#f2f3df','middle',700);
 s+=text(187,232,'L',18,'#f6f4dd');s+=`<rect x="168" y="218" width="12" height="12" rx="2" fill="${l?'#ffe39a':C.off}"/>`;
 if(l)s+=`<circle cx="174" cy="224" r="21" fill="#ffd879" opacity=".2"/>`;
 s+=text(187,271,'ON',16,'#f6f4dd');s+=`<rect x="168" y="258" width="12" height="12" rx="2" fill="${on?'#c1ef9b':C.off}"/>`;
 s+=`<rect x="215" y="134" width="296" height="25" rx="3" fill="#233c30"/>`;
 pinsTop.forEach((n,i)=>{let x=230+i*18;s+=`<rect x="${x-4}" y="141" width="8" height="8" fill="#d6c99c"/>`+text(x,174,n,n.length>2?9:12,'#e4e9d8','middle');});
 let low=['IOREF','RST','3V3','5V','GND','GND','VIN'];
 s+=`<rect x="173" y="343" width="171" height="24" rx="3" fill="#233c30"/>`;
 low.forEach((n,i)=>{let x=185+i*24;s+=`<rect x="${x-4}" y="351" width="8" height="8" fill="#d6c99c"/>`+text(x,336,n,n.length>3?8:11,'#e4e9d8','middle');});
 s+=`<rect x="373" y="343" width="132" height="24" rx="3" fill="#233c30"/>`;
 for(let i=0;i<6;i++)s+=`<rect x="${383+i*22}" y="351" width="8" height="8" fill="#d6c99c"/>`+text(387+i*22,336,'A'+i,11,'#e4e9d8','middle');
 if(usb)s+=line('M0 209 H77','#68776d',11)+`<rect x="48" y="189" width="35" height="41" rx="5" fill="#323c36"/>`;
 if(focus==='L')s+=halo(174,224,p,25);
 if(focus==='GND')s+=halo(...PINS.GND,p,18);
 if(focus==='D2')s+=halo(...PINS.D2,p,18);
 if(focus==='D6')s+=halo(...PINS.D6,p,18);
 if(focus==='5V')s+=halo(...PINS.V5,p,18);
 s+='</g>';return s;
}
function button(pressed=false){let y=pressed?8:0;return `<g aria-label="两端子常开按钮"><circle cx="730" cy="264" r="56" fill="#d3d7cd" stroke="#84958a" stroke-width="3"/><circle cx="730" cy="${253+y}" r="42" fill="${pressed?'#4b5b50':'#374a40'}" stroke="#8ca18c" stroke-width="4"/><path d="M695 305 V341 M765 305 V341" stroke="#b9a76f" stroke-width="12"/><circle cx="695" cy="341" r="5" fill="white"/><circle cx="765" cy="341" r="5" fill="white"/>${text(730,365,'端子 A        端子 B',17,C.muted,'middle')}${text(730,168,'两端子 · 常开自复位',24,C.ink,'middle')}${pressed?`<path d="M730 185v29m-8-9 8 9 8-9" stroke="${C.gold}" stroke-width="7" fill="none"/>`:''}</g>`;}
const gndWire=p=>line('M281 355 V435 H765 V341',C.ground,6,p);
const buttonWire=p=>line('M464 145 V85 H695 V341',C.signal,6,p);
function pixelStrip(lit=0){let s=`<g aria-label="四颗 WS2812B，端子位置以实物丝印为准"><rect x="570" y="158" width="260" height="95" rx="10" fill="#3c5d4f"/>`;for(let i=0;i<4;i++){let co=lit===1?'#ffce7a':lit===2?['#8ddbd4','#d3bcf1','#a9dc92','#f1b39a'][i]:'#788778';s+=`<rect x="${585+i*59}" y="173" width="44" height="44" rx="5" fill="#d7d9c9"/><circle cx="${607+i*59}" cy="195" r="15" fill="${co}"/>`;if(lit)s+=`<circle cx="${607+i*59}" cy="195" r="23" fill="${co}" opacity=".19"/>`;}
 [[590,'5V'],[680,'DIN'],[785,'GND']].forEach(([x,n])=>{s+=`<circle cx="${x}" cy="243" r="6" fill="#d5c89f"/>`+text(x,282,n,23,C.ink,'middle',700);});return s+'</g>';}
function pixelWires(level,p){let s='';if(level>=1)s+=line('M281 355 V450 H785 V243',C.ground,5,level===1?p:1);if(level>=2)s+=line('M257 355 V485 H590 V243',C.power,5,level===2?p:1);if(level>=3){s+=`<g opacity="${level===3?clamp(p*2):1}"><rect x="641" y="325" width="63" height="74" rx="8" fill="#405d59"/><ellipse cx="672" cy="326" rx="31" ry="7" fill="#a5b1a5"/><rect x="688" y="330" width="11" height="62" rx="3" fill="#d3dbc8"/>${text(693,365,'−',16,C.ink,'middle')}${text(667,355,'1000',14,'#e5ebde','middle')}${text(667,374,'µF /10V',13,'#e5ebde','middle')}<path d="M653 398v29h-63 M690 398v29h95" fill="none" stroke-width="4" stroke="${C.ground}"/>${text(644,417,'+',21,C.power,'end')}${text(705,417,'−',21,C.ground)}</g>`;}
 if(level>=4){s+=line('M392 145 V73 H680 V111',C.signal,5,level===4?clamp(p*1.8):1);s+=`<rect x="664" y="113" width="32" height="53" rx="5" fill="#d5c6a4" stroke="#9c8b68" stroke-width="2"/><path d="M665 124h30m-30 11h30m-30 20h30" stroke="#8a7053" stroke-width="4"/>${text(707,145,'330Ω',24)}`;s+=line('M680 166 V243',C.signal,5,level===4?clamp((p-.5)*2):1);}
 return s;
}
function ide(mode,p){let isBoard=mode==='ideBoard',isPix=mode==='idePixels',isButton=mode==='ideButton';let name=isBoard?'选择板型与端口':isPix?'ChristmasStar.ino':isButton?'ButtonLamp.ino':'FirstBlink.ino';let s=`<rect x="60" y="60" width="780" height="400" rx="14" fill="#fff" stroke="#ccd6cb" stroke-width="2"/><path d="M60 103h780" stroke="#dce2d8" stroke-width="2"/>`;
 s+=text(82,88,'Arduino IDE · '+name,25,C.ink);s+=`<circle cx="96" cy="132" r="19" fill="#e5ede1"/><path d="m86 132 7 7 13-15" fill="none" stroke="#718670" stroke-width="3"/><circle cx="145" cy="132" r="19" fill="${!isBoard&&p>.25?'#348c77':'#d5e9d8'}"/><path d="M135 132h20m-9-8 9 8-9 8" fill="none" stroke="${!isBoard&&p>.25?'white':'#487355'}" stroke-width="3"/><rect x="186" y="113" width="350" height="38" rx="6" fill="#f3f5ef" stroke="#cdd8cc"/>${text(200,140,isBoard&&p<.5?'选择开发板…':'Arduino Uno · 实际端口',22)}`;
 if(isBoard){s+=`<rect x="186" y="155" width="520" height="223" rx="8" fill="#f6f8f2" stroke="#b9cab6"/>${text(210,192,'开发板支持：Arduino AVR Boards',24)}${text(210,232,'开发板：Arduino Uno（不是 R4）',24)}${text(210,272,'端口：插拔 USB 时新增的那一项',24)}${text(210,323,'每台电脑的端口名字都可能不同',20,C.muted)}`;s+=halo(201+clamp(p)*420,132,p,22);}
 else {let a=isPix?['库管理器 → 安装 Adafruit NeoPixel','同一个文件夹里：','ChristmasStar.ino + controller.h','点击 → 上传到 Arduino Uno']:isButton?['pinMode(2, INPUT_PULLUP);','按下：D2 接地 → LOW','程序：按住时 L 亮，松开时 L 灭','只接 D2 和 GND，不接 5V']:['pinMode(LED_BUILTIN, OUTPUT);','亮一秒：delay(1000);','灭一秒：delay(1000);','注意：上传箭头 ≠ 验证对勾'];a.forEach((v,i)=>s+=text(110,205+i*44,v,24,i?C.muted:C.ink));s+=halo(145,132,p,26);if(p>.58)s+=`<rect x="78" y="395" width="744" height="48" rx="6" fill="#e2ecde"/>${text(95,426,p>.87?'预期：Done uploading / 上传完成':'示意：正在编译并上传…',23,C.ink)}`;}
 s+=text(450,495,'界面操作示意 · 不会操作你的 IDE 或设备',20,C.muted,'middle');return s;}
export function renderScene(scene,progress=0,seconds=0,options={}){
 const p=clamp(progress),mode=typeof scene==='string'?scene:scene.scene;let s='';
 if(mode.startsWith('ide'))s=ide(mode,p);
 else if(mode==='usb'){
  s+=`<rect x="48" y="130" width="210" height="146" rx="14" fill="#cdd7ce" stroke="#7d9181" stroke-width="2"/><rect x="60" y="142" width="186" height="118" rx="6" fill="#edf3e8"/><path d="M29 288h249l-20 17H49Z" fill="#a9b9ab"/>${text(154,208,'Mac',30,C.ink,'middle')}`;
  s+=`<g transform="translate(588 97) scale(.51)">${board({on:p>.8,usb:false})}</g>`;
  s+=line('M265 240 H584',C.ground,9,p);
  s+=`<g transform="translate(${315-28*(1-p)} 224)"><rect width="80" height="32" rx="10" fill="#708a77"/><rect x="-20" y="9" width="24" height="14" rx="6" fill="#bdc7bc"/><rect x="75" y="4" width="12" height="24" rx="2" fill="#e4e6da"/></g>`;
  s+=`<g transform="translate(${580-55*(1-p)} 225)"><rect width="50" height="31" rx="5" fill="#3d5044"/><path d="M50 5h18l7 7v8l-7 7H50Z" fill="#c7cec4"/></g>`;
  s+=tag(290,175,'C 公 → A 母');s+=text(678,344,'USB-B 方口',25,C.ink,'middle');s+=text(450,420,'USB-A 插头插进转接头的 A 母口',25,C.ink,'middle');s+=text(450,459,'Mac 自带 USB-A 时，省略转接头',22,C.muted,'middle');
 }
 else if(mode==='parts'){
  s+=board({focus:'L',p});s+=`<rect x="610" y="177" width="160" height="56" rx="13" fill="#dce5d7"/>`+text(690,213,'USB 数据线',24,C.ink,'middle');s+=text(690,300,'外部电源',24,C.muted,'middle')+line('M615 278 L770 309',C.power,4)+text(690,355,'PIR · 音频 · 灯板',22,C.muted,'middle');s+=text(300,435,'只留下板子，先完成一个小成果',25,C.ink,'middle');
 }
 else if(['pixelParts','pixelGround','pixelPower','capacitor','pixelData','pixelCheck','pixelTest'].includes(mode)){
  const level={pixelParts:0,pixelGround:1,pixelPower:2,capacitor:3,pixelData:4,pixelCheck:4,pixelTest:4}[mode];
  let phase=mode==='pixelTest'?(seconds<2?0:seconds<4?1:seconds<6?2:seconds<9?3:seconds<12?4:5):0;let lit=mode==='pixelTest'?(phase===1||phase===4?1:phase===2?2:0):0;
  s+=board({on:mode==='pixelTest'||(mode==='pixelCheck'&&p>.8),usb:mode==='pixelTest'||(mode==='pixelCheck'&&p>.8),focus:mode==='pixelGround'?'GND':mode==='pixelPower'?'5V':mode==='pixelData'?'D6':'',p});s+=pixelStrip(lit);s+=pixelWires(level,p);
  s+=text(700,129,'4 颗 · 5V WS2812B',25,C.ink,'middle');
  if(mode==='pixelParts')s+=halo(680,243,p,25)+tag(584,342,'认 DIN，不接 DOUT');
  if(mode==='pixelGround')s+=tag(592,335,'GND ↔ GND');
  if(mode==='pixelPower')s+=tag(592,335,'5V → 灯板 5V',C.power);
  if(mode==='capacitor')s+=tag(584,308,'正极到 5V，负极到 GND');
  if(mode==='pixelData')s+=text(353,54,'D6 → 330Ω → DIN',25,C.signal);
  if(mode==='pixelCheck')s+=text(300,57,'检查五项后，才插回 USB',26,C.ink,'middle');
  if(mode==='pixelTest'){s+=text(290,57,['上电：熄灭','第一次短按：暖色','第二次短按：彩色','第三次短按：熄灭','第四次短按：暖色','长按 >1.2秒：关闭'][phase],25,C.ink,'middle');s+=text(694,74,'D2 按钮沿用上一关接线',20,C.muted,'middle');}
 }
 else {
  let isTest=mode==='buttonTest';let pressed=isTest?(options.pressed??((seconds%4)>1&&(seconds%4)<2.7)):false;
  let on=mode==='blink'||isTest||(mode==='buttonCheck'&&p>.78)||(mode==='unplug'&&p<.35);
  let l=mode==='blink'?Math.floor(seconds)%2===0:pressed;
  let usb=on;s+=board({on,l,usb,focus:mode==='blink'?'L':mode==='wireGround'?'GND':mode==='wireButton'?'D2':'',p});
  if(mode==='blink'){s+=text(666,215,l?'亮一秒':'灭一秒',43,C.ink,'middle',700);s+=text(666,265,'看 L，不是 ON',25,C.muted,'middle');s+=line('M206 221 C360 215 470 225 530 225',C.gold,3);}
  else if(mode==='unplug'){s+=`<g transform="translate(${-65*clamp((p-.1)*2)} 0)"><path d="M10 209h55" stroke="#728275" stroke-width="10"/><rect x="48" y="188" width="30" height="43" rx="5" fill="#394b40"/></g>`;s+=text(686,227,p>.4?'电源已拔开':'握住插头，向外拔',29,C.ink,'middle');s+=text(686,276,'先确认 ON 灯熄灭',24,C.muted,'middle');}
  else {s+=button(pressed);if(['wireGround','wireButton','buttonCheck','buttonTest'].includes(mode))s+=gndWire(mode==='wireGround'?p:1);if(['wireButton','buttonCheck','buttonTest'].includes(mode))s+=buttonWire(mode==='wireButton'?p:1);if(mode==='wireGround')s+=tag(352,415,'GND → 端子 B');if(mode==='wireButton')s+=tag(512,61,'D2 → 端子 A',C.signal);if(mode==='buttonCheck')s+=text(300,57,'只有 D2 和 GND 两根线',26,C.ink,'middle');if(isTest)s+=text(300,57,pressed?'按住 → L 灯亮':'松开 → L 灯灭',29,C.ink,'middle',700);}
 }
 return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 525" role="img" aria-label="${esc(mode)} 操作示意" style="font-family:system-ui,-apple-system,'PingFang SC','Microsoft YaHei',sans-serif"><rect width="900" height="525" rx="18" fill="${C.paper}"/>${s}<text x="24" y="515" font-size="15" fill="#79847a">原创教学示意 · 按实物丝印认接口，不按图数孔位 · 动画不是实物反馈</text></svg>`;
}
