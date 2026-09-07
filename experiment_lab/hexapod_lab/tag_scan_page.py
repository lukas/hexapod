"""Mobile-first browser surface for the Robot Lab tag walk-around."""

from html import escape


def tag_scan_page(*, available: bool, message: str = "") -> str:
    availability = "true" if available else "false"
    unavailable = escape(message or "Tag analysis is not configured on this host")
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="theme-color" content="#090d10">
  <title>Tag walk-around · Hexapod Lab</title>
  <style>
    :root{color-scheme:dark;--bg:#090d10;--panel:#10171c;--ink:#f5f7f2;--muted:#9ba9ae;--line:#28343a;--cyan:#69e5ee;--orange:#ffb13b;--good:#8df07b;--bad:#ff6d68;--safe:env(safe-area-inset-bottom,0px)}
    *{box-sizing:border-box}html,body{margin:0;min-height:100%;background:var(--bg);color:var(--ink);font:16px/1.4 -apple-system,BlinkMacSystemFont,"SF Pro Text",Inter,system-ui,sans-serif}button,.file-button{font:inherit}button{border:0}.app{min-height:100dvh;display:grid;grid-template-rows:auto 1fr;background:radial-gradient(circle at 80% 0,#15252a 0,transparent 34%),var(--bg)}
    .topbar{position:relative;z-index:5;display:flex;align-items:center;justify-content:space-between;padding:calc(14px + env(safe-area-inset-top,0px)) 18px 12px;border-bottom:1px solid rgba(255,255,255,.08);background:rgba(9,13,16,.9);backdrop-filter:blur(18px)}.brand{display:flex;align-items:center;gap:10px;font-weight:750;letter-spacing:-.02em}.mark{width:19px;height:19px;border:2px solid var(--cyan);box-shadow:inset 0 0 0 4px var(--bg);background:var(--cyan);transform:rotate(12deg)}.safe-pill{font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;color:var(--good);border:1px solid rgba(141,240,123,.35);border-radius:99px;padding:6px 9px}
    .intro{width:min(640px,100%);margin:auto;padding:38px 22px calc(32px + var(--safe))}.kicker{color:var(--cyan);font-size:.75rem;font-weight:800;letter-spacing:.13em;text-transform:uppercase}.intro h1{font-size:clamp(2.35rem,10vw,4.6rem);line-height:.94;letter-spacing:-.065em;margin:13px 0 20px}.intro .lead{font-size:1.08rem;color:#cad3d4;max-width:34rem}.steps{display:grid;gap:1px;margin:30px 0;background:var(--line);border:1px solid var(--line);border-radius:18px;overflow:hidden}.step{display:grid;grid-template-columns:34px 1fr;gap:11px;background:var(--panel);padding:15px}.step b{display:grid;place-items:center;width:28px;height:28px;border-radius:50%;background:#1c292f;color:var(--cyan)}.step strong{display:block;margin-bottom:2px}.step span{color:var(--muted);font-size:.9rem}.primary{width:100%;min-height:58px;border-radius:16px;background:var(--orange);color:#171006;font-weight:800;font-size:1.05rem;box-shadow:0 10px 34px rgba(255,177,59,.18)}.primary:disabled{opacity:.45}.quiet{margin:13px 5px 0;color:var(--muted);font-size:.82rem;text-align:center}.unavailable{padding:14px;border:1px solid rgba(255,109,104,.45);border-radius:14px;background:rgba(255,109,104,.08);color:#ffd0ce;margin:18px 0}
    .scanner{position:relative;display:none;min-height:0;overflow:hidden;background:#020304}.scanner.active{display:block}.camera{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;background:#020304}.shade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.22),transparent 22%,transparent 48%,rgba(0,0,0,.76) 82%);pointer-events:none}.reticle{position:absolute;left:10%;right:10%;top:12%;height:42%;border:1.5px solid rgba(255,255,255,.72);border-radius:22px;box-shadow:0 0 0 999px rgba(0,0,0,.08);pointer-events:none}.reticle:before,.reticle:after{content:"";position:absolute;width:42px;height:42px;border-color:var(--cyan)}.reticle:before{left:-2px;top:-2px;border-left:4px solid var(--cyan);border-top:4px solid var(--cyan);border-radius:20px 0 0}.reticle:after{right:-2px;bottom:-2px;border-right:4px solid var(--cyan);border-bottom:4px solid var(--cyan);border-radius:0 0 20px}.flash{position:absolute;inset:0;background:rgba(105,229,238,.24);opacity:0;pointer-events:none}.flash.go{animation:flash .26s ease-out}@keyframes flash{40%{opacity:1}to{opacity:0}}
    .sheet{position:absolute;left:0;right:0;bottom:0;padding:16px 16px calc(14px + var(--safe));border-top:1px solid rgba(255,255,255,.12);border-radius:24px 24px 0 0;background:rgba(9,13,16,.91);backdrop-filter:blur(20px)}.scan-state{display:flex;align-items:center;gap:8px;color:var(--muted);font-size:.75rem;font-weight:800;text-transform:uppercase;letter-spacing:.1em}.pulse{width:8px;height:8px;border-radius:50%;background:var(--orange)}.scanning .pulse{background:var(--good);box-shadow:0 0 0 0 rgba(141,240,123,.4);animation:pulse 1.5s infinite}@keyframes pulse{70%{box-shadow:0 0 0 8px rgba(141,240,123,0)}}.instruction{font-size:1.08rem;font-weight:720;line-height:1.25;margin:9px 0 14px;min-height:2.7em}.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}.metric{padding:10px;border:1px solid var(--line);border-radius:12px;background:rgba(18,26,31,.75)}.metric b{display:block;font-size:1.08rem}.metric span{display:block;color:var(--muted);font-size:.68rem;text-transform:uppercase;letter-spacing:.06em}.bar{height:3px;margin-top:7px;border-radius:4px;background:#273238;overflow:hidden}.bar i{display:block;height:100%;width:0;background:var(--cyan);transition:width .3s}.last{height:20px;margin:8px 2px 0;color:var(--muted);font-size:.78rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.actions{display:grid;grid-template-columns:1fr 1.4fr;gap:9px;margin-top:9px}.secondary,.finish,.file-button{min-height:50px;border-radius:14px;font-weight:780;text-align:center}.secondary{background:#1a242a;color:var(--ink);border:1px solid #34434a}.finish{background:var(--orange);color:#171006}.file-button{display:none;align-items:center;justify-content:center;margin-top:8px;background:#182127;border:1px solid var(--line);color:var(--ink)}.file-button.show{display:flex}.file-button input{position:absolute;opacity:0;pointer-events:none}.tiny{display:flex;justify-content:space-between;margin-top:9px;color:var(--muted);font-size:.7rem}.error{position:absolute;z-index:8;top:16px;left:16px;right:16px;padding:12px 14px;border:1px solid rgba(255,109,104,.55);border-radius:13px;background:rgba(40,10,12,.92);color:#ffd9d7;display:none}.error.show{display:block}.done{display:none;width:min(620px,100%);margin:auto;padding:34px 22px}.done.active{display:block}.done h1{font-size:2.6rem;letter-spacing:-.05em}.done a{display:block;text-align:center;text-decoration:none;padding:17px;border-radius:15px;background:var(--orange);color:#171006;font-weight:800}.done p{color:var(--muted)}
    @media(min-width:700px){.scanner{width:min(760px,100%);margin:auto;border-inline:1px solid var(--line)}.sheet{left:18px;right:18px;bottom:18px;border:1px solid rgba(255,255,255,.14);border-radius:24px;padding-bottom:16px}.reticle{top:10%;height:48%}}
    @media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
  </style>
</head>
<body>
<div class="app">
  <header class="topbar"><div class="brand"><i class="mark"></i> Hexapod Tag Scan</div><span class="safe-pill">camera only · no motion</span></header>
  <main class="intro" id="intro">
    <div class="kicker">Robot Lab · Hexapod 1</div>
    <h1>One slow lap.<br>Every tag checked.</h1>
    <p class="lead">Set the robot down with its legs straight and radial. Start above it, then lower the phone and walk one slow circle. Useful views save automatically.</p>
    <div class="steps">
      <div class="step"><b>1</b><div><strong>Start overhead</strong><span>Fit the whole robot and at least four floor cards in the frame.</span></div></div>
      <div class="step"><b>2</b><div><strong>Circle at tag height</strong><span>Pause briefly at each leg so its two lid tags stay visible.</span></div></div>
      <div class="step"><b>3</b><div><strong>Finish and save</strong><span>Robot Lab records the photos, annotations, and proposed rotations for review.</span></div></div>
    </div>
    <div class="unavailable" id="unavailable" hidden>__UNAVAILABLE__</div>
    <button class="primary" id="start">Start rear camera</button>
    <p class="quiet">If a numbered tag moved to a different part, the scan records it but leaves that mount assignment for review.</p>
  </main>
  <main class="scanner" id="scanner">
    <video class="camera" id="camera" autoplay muted playsinline></video>
    <div class="shade"></div><div class="reticle"></div><div class="flash" id="flash"></div>
    <div class="error" id="error"></div>
    <section class="sheet">
      <div class="scan-state" id="scanState"><i class="pulse"></i><span id="scanLabel">Starting camera</span></div>
      <div class="instruction" id="instruction">Hold the whole robot in frame.</div>
      <div class="metrics">
        <div class="metric"><b id="tagsValue">0/37</b><span>tags found</span><div class="bar"><i id="tagsBar"></i></div></div>
        <div class="metric"><b id="poseValue">0/37</b><span>oriented</span><div class="bar"><i id="poseBar"></i></div></div>
        <div class="metric"><b id="floorValue">0/7</b><span>floor refs</span><div class="bar"><i id="floorBar"></i></div></div>
      </div>
      <div class="last" id="last">Waiting for the first useful view…</div>
      <div class="actions"><button class="secondary" id="pause">Pause</button><button class="finish" id="finish">Finish &amp; save</button></div>
      <label class="file-button" id="fallback">Take one photo instead<input id="file" type="file" accept="image/*" capture="environment"></label>
      <div class="tiny"><span id="photos">0 useful photos</span><span>advisory record only</span></div>
    </section>
  </main>
  <main class="done" id="done"><div class="kicker">Saved to Robot Lab</div><h1 id="doneHeading">Scan saved.</h1><p id="doneText"></p><a id="resultLink" href="/">Open the orientation record</a></main>
</div>
<canvas id="canvas" hidden></canvas>
<script>
(() => {
  const AVAILABLE = __AVAILABLE__;
  const $ = (id) => document.getElementById(id);
  const intro=$('intro'), scanner=$('scanner'), done=$('done'), video=$('camera'), canvas=$('canvas');
  let stream=null, scan=null, running=false, sending=false, starting=false, loopToken=0;
  const request = async (path, options={}) => {
    const response = await fetch(path,{cache:'no-store',...options,headers:{'X-Hexapod-Scan':'1',...(options.headers||{})}});
    let body={}; try{body=await response.json()}catch(_error){}
    if(!response.ok) throw new Error(body.detail||body.error||`${response.status} ${response.statusText}`);
    return body;
  };
  const pct=(a,b)=>`${b?Math.round(100*a/b):0}%`;
  function render(next){
    scan=next; localStorage.setItem('hexapod-tag-scan',scan.id);
    $('tagsValue').textContent=`${scan.robot_tags.seen}/${scan.robot_tags.total}`;
    $('poseValue').textContent=`${scan.orientations.measured}/${scan.orientations.total}`;
    $('floorValue').textContent=`${scan.floor_reference.seen}/${scan.floor_reference.total}`;
    $('tagsBar').style.width=pct(scan.robot_tags.seen,scan.robot_tags.total);
    $('poseBar').style.width=pct(scan.orientations.measured,scan.orientations.total);
    $('floorBar').style.width=pct(scan.floor_reference.seen,scan.floor_reference.total);
    $('instruction').textContent=scan.instruction;
    $('photos').textContent=`${scan.photo_count} useful photo${scan.photo_count===1?'':'s'}`;
    if(scan.last_capture){
      $('last').textContent=`${scan.last_capture.kept?'Saved':'Skipped'} · ${scan.last_capture.message}`;
      if(scan.last_capture.kept){$('flash').classList.remove('go');void $('flash').offsetWidth;$('flash').classList.add('go');if(navigator.vibrate)navigator.vibrate(35)}
    }
  }
  function showError(message){$('error').textContent=message;$('error').classList.add('show');window.setTimeout(()=>$('error').classList.remove('show'),5000)}
  async function ensureScan(){
    if(scan) return scan;
    const saved=localStorage.getItem('hexapod-tag-scan');
    if(saved){try{scan=await request(`/api/tag-scans/${saved}`);if(scan.status==='capturing'){render(scan);return scan}}catch(_error){localStorage.removeItem('hexapod-tag-scan')}}
    scan=await request('/api/tag-scans',{method:'POST'});render(scan);return scan;
  }
  async function startCamera(){
    if(!AVAILABLE||starting||running)return;
    starting=true;$('start').disabled=true;$('pause').disabled=true;
    try{
      await ensureScan();
      stream=await navigator.mediaDevices.getUserMedia({audio:false,video:{facingMode:{ideal:'environment'},width:{ideal:1920},height:{ideal:1440}}});
      video.srcObject=stream;await video.play();running=true;loopToken+=1;
      intro.style.display='none';done.classList.remove('active');scanner.classList.add('active');
      $('scanState').classList.add('scanning');$('scanLabel').textContent='Scanning';$('pause').textContent='Pause';$('fallback').classList.remove('show');
      captureLoop(loopToken);
    }catch(error){
      intro.style.display='none';scanner.classList.add('active');$('fallback').classList.add('show');$('scanLabel').textContent='Camera unavailable';
      showError(`${error.message||error}. Use “Take one photo instead.”`);
    }finally{starting=false;$('start').disabled=false;$('pause').disabled=false}
  }
  function stopCamera(){running=false;loopToken+=1;if(stream){stream.getTracks().forEach(track=>track.stop());stream=null}video.srcObject=null;$('scanState').classList.remove('scanning');$('scanLabel').textContent='Paused';$('pause').textContent='Resume';$('fallback').classList.add('show')}
  const delay=(ms)=>new Promise(resolve=>setTimeout(resolve,ms));
  async function jpegFromVideo(){
    if(!video.videoWidth)throw new Error('Camera is still warming up');
    const scale=Math.min(1,2400/video.videoWidth);canvas.width=Math.round(video.videoWidth*scale);canvas.height=Math.round(video.videoHeight*scale);
    canvas.getContext('2d',{alpha:false}).drawImage(video,0,0,canvas.width,canvas.height);
    return await new Promise((resolve,reject)=>canvas.toBlob(blob=>blob?resolve(blob):reject(new Error('Could not capture frame')),'image/jpeg',.9));
  }
  async function upload(blob){
    sending=true;try{render(await request(`/api/tag-scans/${scan.id}/photos`,{method:'POST',headers:{'Content-Type':'image/jpeg'},body:blob}))}finally{sending=false}
  }
  async function captureLoop(token){
    await delay(700);
    while(running&&token===loopToken){
      try{await upload(await jpegFromVideo())}catch(error){showError(error.message||String(error));await delay(1500)}
      await delay(850);
    }
  }
  async function fileToJpeg(file){
    const bitmap=await createImageBitmap(file,{imageOrientation:'from-image'});const scale=Math.min(1,2400/bitmap.width);canvas.width=Math.round(bitmap.width*scale);canvas.height=Math.round(bitmap.height*scale);canvas.getContext('2d',{alpha:false}).drawImage(bitmap,0,0,canvas.width,canvas.height);bitmap.close();
    return await new Promise((resolve,reject)=>canvas.toBlob(blob=>blob?resolve(blob):reject(new Error('Could not prepare photo')),'image/jpeg',.9));
  }
  $('start').addEventListener('click',startCamera);
  $('pause').addEventListener('click',()=>{if(running)stopCamera();else startCamera()});
  $('file').addEventListener('change',async(event)=>{const file=event.target.files&&event.target.files[0];if(!file)return;try{await ensureScan();await upload(await fileToJpeg(file))}catch(error){showError(error.message||String(error))}finally{event.target.value=''}});
  $('finish').addEventListener('click',async()=>{
    if(sending){showError('Saving the current view—tap Finish again in a moment.');return}stopCamera();$('finish').disabled=true;$('finish').textContent='Analyzing…';
    try{
      const result=await request(`/api/tag-scans/${scan.id}/finish`,{method:'POST'});localStorage.removeItem('hexapod-tag-scan');scanner.classList.remove('active');done.classList.add('active');
      const complete=Boolean(result.experiment.parameters.ready_for_human_review);$('doneHeading').textContent=complete?'Complete scan saved.':'Partial scan saved.';
      $('doneText').textContent=complete?`${result.scan.orientations.measured}/${result.scan.orientations.total} orientations measured. The canonical robot config is unchanged until review.`:`${result.scan.orientations.measured}/${result.scan.orientations.total} orientations measured. Robot Lab saved the evidence and flagged missing or ambiguous views.`;
      $('resultLink').href=`/experiments/${result.experiment.id}`;
    }catch(error){showError(error.message||String(error));$('finish').disabled=false;$('finish').textContent='Finish & save'}
  });
  window.addEventListener('pagehide',stopCamera);
  if(!AVAILABLE){$('unavailable').hidden=false;$('start').disabled=true}
})();
</script>
</body></html>""".replace("__AVAILABLE__", availability).replace("__UNAVAILABLE__", unavailable)
