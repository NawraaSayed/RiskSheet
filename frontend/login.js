// Script extracted from login.html
document.getElementById('loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;
  const errorMsg = document.getElementById('errorMsg');

  try {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    if (res.ok) {
      window.location.href = '/';
    } else {
      errorMsg.style.display = 'block';
    }
  } catch (err) {
    errorMsg.textContent = 'An error occurred. Please try again.';
    errorMsg.style.display = 'block';
  }
});

// --- Floating sprites generator (code snippets, stock ticks, astro formulas) ---
(function(){
  const pythonSnippets = [
    "import numpy as np",
    "pd.read_csv('prices.csv')",
    "def calc_risk(portfolio):",
    "np.log(1+returns).mean()",
    "with open('data.csv') as f:"
  ];

  const jsSnippets = [
    "const price = await fetch('/api/price')",
    "chart.update(series)",
    "const gain = (close-open)/open * 100",
    "fetch('/api/tick').then(r=>r.json())"
  ];

  const javaSnippets = [
    "public class Trader {",
    "List<Double> prices = new ArrayList<>()",
    "BigDecimal pnl = new BigDecimal(0)",
    "System.out.println(\"tick\")"
  ];

  const goSnippets = [
    "func calcRisk(p []float64) float64 {",
    "resp, _ := http.Get(\"/price\")",
    "defer resp.Body.Close()",
  ];

  const asmSnippets = [
    "mov eax, [ebp+8]",
    "push ebx",
    "call _calculate",
  ];

  const stockSnippets = [
    "AAPL  172.34 ▲0.6%",
    "TSLA  412.12 ▼1.4%",
    "NVDA  642.50 ▲2.1%",
    "SPY   472.10 ▲0.3%"
  ];

  const snippets = []
    .concat(pythonSnippets.map(s=>({text:s,lang:'py'})))
    .concat(jsSnippets.map(s=>({text:s,lang:'js'})))
    .concat(javaSnippets.map(s=>({text:s,lang:'java'})))
    .concat(goSnippets.map(s=>({text:s,lang:'go'})))
    .concat(asmSnippets.map(s=>({text:s,lang:'asm'})))
    .concat(stockSnippets.map(s=>({text:s,lang:'stock'})));

  function rand(min, max){ return Math.random() * (max - min) + min; }
  function pick(){ return snippets[Math.floor(Math.random() * snippets.length)]; }

  const container = document.getElementById('codeSprites');
  if(!container) return;

  const formulas = [
    'E = mc^2',
    'F = ma',
    '∇·E = ρ/ε0',
    'ψ(x,t) = e^{i(kx-ωt)}',
    'H = -∑ p log p',
    'λ = h/p',
    'c = 299792458 m/s',
    'Δx·Δp ≥ ħ/2',
    '∇×E = -∂B/∂t',
    '∇×B = μ0(J + ε0 ∂E/∂t)',
    'E_k = 1/2 mv^2',
    'V = IR',
    'p = mv',
    'S = k_B ln Ω',
    'z = (x-μ)/σ',
    'r = ρ/(1-ρ^2)^(1/2)',
    'PV = nRT',
    'a^2 + b^2 = c^2',
    'T = 2π sqrt(l/g)',
    'I = ∫ E·dA'
  ];

  function pickFormula(){ return formulas[Math.floor(Math.random() * formulas.length)]; }

  function makeSprite(obj, options = {}){
    const el = document.createElement('span');
    const langClass = obj.lang || '';
    // small chance to be highlight or warn
    const extra = Math.random() < 0.08 ? ' highlight' : (Math.random() < 0.06 ? ' warn' : '');
    el.className = 'code-sprite ' + langClass + extra;
    // inner rotator so rotation animation doesn't override translation transforms
    const rotWrap = document.createElement('span');
    rotWrap.className = 'rot';
    rotWrap.textContent = obj.text;
    el.appendChild(rotWrap);
    // fully random position across viewport
    const left = rand(0, 98);
    const top = rand(0, 98);
    el.style.left = left + '%';
    el.style.top = top + '%';
    el.style.fontSize = Math.floor(rand(12, 22)) + 'px';
    // random drift amounts and base rotation via CSS vars
    const dx = (Math.floor(rand(-40,40))) + 'px';
    const dy = (Math.floor(rand(-30,30))) + 'px';
    const rot = (Math.floor(rand(-12,12))) + 'deg';
    el.style.setProperty('--dx', dx);
    el.style.setProperty('--dy', dy);
    el.style.setProperty('--rot', rot);
    // assign float + drift animations with randomized durations
    const floatDur = (rand(8, 22)).toFixed(2);
    const driftDur = (rand(10, 40)).toFixed(2);
    el.style.animation = `floaty ${floatDur}s ease-in-out infinite, drift ${driftDur}s linear infinite`;
    // slight animation delay staggering
    el.style.animationDelay = (rand(0, 6)).toFixed(2) + 's, ' + (rand(0, 6)).toFixed(2) + 's';
    container.appendChild(el);

    if (!options.sequential) {
      // fade-in slowly (when not controlled by sequence)
      requestAnimationFrame(()=>{
        setTimeout(()=> el.classList.add('visible'), rand(80, 450));
      });

      // safety removal for non-sequential sprites
      setTimeout(()=>{ if(el.parentNode) el.classList.remove('visible'); setTimeout(()=> el.remove(), 3500); }, 70000 + rand(0,50000));
    }

    return el;
  }

  // Sequential one-by-one snippet loop: show one snippet at a time
  function delay(ms){ return new Promise(res=>setTimeout(res, ms)); }

  async function showSequentialSnippet(obj){
    const el = makeSprite(obj, { sequential: true });
    // ensure element is in DOM and layout applied
    await new Promise(r => requestAnimationFrame(r));

    // Stage 1: appear (lite)
    el.classList.add('visible');
    await delay(1200 + Math.random()*900); // lite duration

    // Stage 2: brighten a little
    el.classList.add('bright');
    await delay(700 + Math.random()*800);

    // Stage 3: back to lite
    el.classList.remove('bright');
    await delay(900 + Math.random()*1100);

    // Stage 4: fade out
    el.classList.remove('visible');
    // allow CSS fade-out to complete
    await delay(900);
    if(el.parentNode) el.remove();
  }

  async function sequentialLoop(){
    // small warm-up delay
    await delay(600 + Math.random()*800);
    while(true){
      const item = pick();
      try{
        await showSequentialSnippet(item);
      } catch(e){ /* ignore and continue */ }
      // brief pause between snippets
      await delay(300 + Math.random()*900);
    }
  }

  sequentialLoop();

  // --- formula sprites (less frequent, randomized positions) ---
  function makeFormula(text){
    const el = document.createElement('span');
    el.className = 'formula-sprite';
    const rotWrap = document.createElement('span');
    rotWrap.className = 'rot';
    rotWrap.textContent = text;
    el.appendChild(rotWrap);
    // allow anywhere in viewport
    el.style.left = rand(0, 96) + '%';
    el.style.top = rand(0, 96) + '%';
    el.style.fontSize = Math.floor(rand(14, 26)) + 'px';
    const rot = (Math.floor(rand(-10,10))) + 'deg';
    const dx = (Math.floor(rand(-60,60))) + 'px';
    const dy = (Math.floor(rand(-40,40))) + 'px';
    el.style.setProperty('--dx', dx);
    el.style.setProperty('--dy', dy);
    el.style.setProperty('--rot', rot);
    const floatDur = (rand(12, 28)).toFixed(2);
    const driftDur = (rand(18, 46)).toFixed(2);
    el.style.animation = `floaty ${floatDur}s ease-in-out infinite, drift ${driftDur}s linear infinite`;
    container.appendChild(el);

    // slow fade in
    requestAnimationFrame(()=>{
      setTimeout(()=> el.classList.add('visible'), rand(120, 600));
    });

    // rotation disabled (kept static)

    // visible duration then fade out slowly
    const visibleFor = Math.floor(rand(4200, 9000));
    setTimeout(()=>{
      el.classList.remove('visible');
      setTimeout(()=> el.remove(), 3200);
    }, visibleFor);

    // safety remove after a long time
    setTimeout(()=>{ if(el.parentNode) el.remove(); }, 120000);
    return el;
  }

  // initial spread of formula sprites (more numerous)
  for(let i=0;i<10;i++){ makeFormula(pickFormula()); }

  // spawn multiple formulas periodically, but limit simultaneous count
  const maxFormulas = 18;
  setInterval(()=>{
    const existing = container.querySelectorAll('.formula-sprite').length;
    const toSpawn = Math.min(3, Math.max(1, Math.floor(rand(1,4))));
    if(existing < maxFormulas){
      for(let i=0;i<toSpawn;i++) makeFormula(pickFormula());
    }
  }, 1400 + Math.random()*800);

  // on resize, add a few to reposition density
  let resizeTimeout;
  window.addEventListener('resize', ()=>{
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(()=>{ for(let i=0;i<8;i++) makeSprite(pick()); }, 250);
  });

})();

