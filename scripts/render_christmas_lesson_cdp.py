#!/usr/bin/env python3
"""Optional fast video encoder for the first hands-on lesson.

Author-only tool; no browser automation or Node required for ordinary learners.
Run 'python3 -m http.server 8137 --directory dist' in repo, and start a
separate Chrome/Brave instance with --remote-debugging-port=9222.
Requires python websockets + system ffmpeg. Only a new tab is created/closed.
Uses the same course.generated.mjs and scene.mjs as the actual interactive lesson.
"""
import asyncio,json,urllib.request,base64,os,pathlib,time,subprocess
import websockets

PORT=int(os.environ.get('MAKER_CDP_PORT','9222'))
BASE=os.environ.get('MAKER_PREVIEW_URL','http://127.0.0.1:8137/projects/christmas-magic-tent/hands-on/')
OUTPUT=os.environ.get('MAKER_VIDEO_OUTPUT','/tmp/christmas-hands-on-lesson1.mp4')
FRAME_DIR=pathlib.Path(os.environ.get('MAKER_VIDEO_FRAMES','/tmp/christmas-frames'))
FRAME_DIR.mkdir(exist_ok=True)
FPS=8
DURATION_PER=8
TOTAL=5*DURATION_PER*FPS

async def main():
    endpoint=json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/version'))['webSocketDebuggerUrl']
    async with websockets.connect(endpoint,proxy=None) as browser:
        await browser.send(json.dumps({'id':1,'method':'Target.createTarget','params':{'url':BASE}}))
        while True:
            msg=json.loads(await browser.recv())
            if msg.get('id')==1:target=msg['result']['targetId'];break
    for _ in range(40):
        all_tabs=json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json'))
        tab=next((t for t in all_tabs if t.get('id')==target),None)
        if tab and tab.get('webSocketDebuggerUrl'):break
        await asyncio.sleep(.1)
    assert tab and tab.get('webSocketDebuggerUrl')
    async with websockets.connect(tab['webSocketDebuggerUrl'],proxy=None,max_size=30*1024*1024) as ws:
        next_id=20
        async def call(method,params=None):
            nonlocal next_id
            next_id+=1
            await ws.send(json.dumps({'id':next_id,'method':method,'params':params or {}},ensure_ascii=False))
            while True:
                obj=json.loads(await ws.recv())
                if obj.get('id')==next_id:
                    if obj.get('error'):raise Exception(obj['error'])
                    return obj.get('result',{})
        async def ev(expr,ret=False):
            r=await call('Runtime.evaluate',{'expression':expr,'returnByValue':ret,'awaitPromise':True})
            if r.get('exceptionDetails'):raise Exception(str(r['exceptionDetails']))
            return r.get('result',{}).get('value')
        for _ in range(60):
            if await ev("document.readyState==='complete'") : break
            await asyncio.sleep(.1)
        await call('Emulation.setDeviceMetricsOverride',{'width':1280,'height':720,'deviceScaleFactor':1,'mobile':False})
        setup="""(async()=>{
          window._S=await import('http://127.0.0.1:8137/assets/christmas-steps/scene.mjs');
          window._C=(await import('http://127.0.0.1:8137/assets/christmas-steps/course.generated.mjs')).COURSE;
          document.head.innerHTML='<meta charset="utf-8"><style>*{box-sizing:border-box}html,body{width:1280px;height:720px;margin:0;background:#f3f5ef;color:#203a30;font-family:PingFang SC,Microsoft YaHei,sans-serif}.head{height:105px;padding:30px 44px 14px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #dde4db}.brand{color:#3d8064;font-size:19px;font-weight:800;letter-spacing:2px}.progress{font-size:20px;color:#6a7d70}.title{font-size:36px;font-weight:800;padding:18px 44px 17px;height:96px;line-height:1.4}.layout{display:flex;gap:26px;padding:0 40px;height:432px}.scene{width:752px;height:429px;flex:0 0 752px;border:1px solid #d9e3d8;background:white;border-radius:16px;overflow:hidden}.scene svg{display:block;width:100%;height:100%}.side{flex:1;padding:12px 0}.kicker{color:#3e8265;font-weight:750;font-size:18px;margin-bottom:10px}.body{font-size:24px;font-weight:700;line-height:1.57;margin-bottom:28px}.expect{padding:15px 17px;border-left:5px solid #73a281;background:#e6efe3;border-radius:0 10px 10px 0;font-size:20px;line-height:1.5}.expect b{display:block;font-size:17px;margin-bottom:4px}.footer{padding:0 44px;display:flex;justify-content:space-between;align-items:center;font-size:15px;color:#6d8072;height:53px}.track{height:8px;border-radius:8px;background:#d8e4d9;margin:0 44px}.fill{background:#55896b;height:8px;border-radius:8px;width:0}</style>';
          document.body.innerHTML='<header class="head"><div class="brand">MAKER LAB · 圣诞魔法小屋</div><div class="progress"></div></header><div class="title"></div><main class="layout"><div class="scene"></div><section class="side"><div class="kicker">现在只做这一件</div><div class="body"></div><div class="expect"><b>做对了，应该看到</b><span></span></div></section></main><div class="track"><div class="fill"></div></div><footer class="footer"><span>原创操作示意 · 非实物录像 · 断电后接线</span><span>详细可暂停版见 Maker Lab 分步教程</span></footer>';
          window._renderLesson=(i,p)=>{const s=window._C.lessons[0].steps[i];document.querySelector('.progress').textContent='第 1 关 · '+(i+1)+' / 5 步';document.querySelector('.title').textContent=s.title;document.querySelector('.body').textContent=s.do;document.querySelector('.expect span').textContent=s.expected;document.querySelector('.scene').innerHTML=window._S.renderScene(s,p,p*s.seconds);document.querySelector('.fill').style.width=((i+p)/5*100)+'%';};
          window._renderLesson(0,0);return true;
        })()"""
        assert await ev(setup,True) is True
        start=time.perf_counter()
        for frame in range(TOTAL):
            idx=frame//(FPS*DURATION_PER)
            p=(frame%(FPS*DURATION_PER))/(FPS*DURATION_PER-1)
            await ev(f'window._renderLesson({idx},{p:.6f})')
            snap=await call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False,'optimizeForSpeed':True})
            (FRAME_DIR/f'frame-{frame:04d}.png').write_bytes(base64.b64decode(snap['data']))
            if frame%80==0:print('FRAMES',frame,'/',TOTAL,'seconds',round(time.perf_counter()-start,1),flush=True)
        print('CAPTURE_DONE',round(time.perf_counter()-start,1),flush=True)
    async with websockets.connect(endpoint,proxy=None) as browser:
        await browser.send(json.dumps({'id':2,'method':'Target.closeTarget','params':{'targetId':target}}))
        await browser.recv()
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(FPS),'-i',str(FRAME_DIR/'frame-%04d.png'),'-c:v','libx264','-preset','veryfast','-crf','22','-pix_fmt','yuv420p','-movflags','+faststart',OUTPUT]
    subprocess.run(cmd,check=True,timeout=240)
    print('VIDEO_READY',OUTPUT,'bytes',os.stat(OUTPUT).st_size,flush=True)
asyncio.run(main())
