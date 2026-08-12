/* Shared helpers: layout, data store, Notion sync */
const EXAM = "2027-01-22";
const STATUSES = ["Not Started","Theory Started","Theory Done","Practice Started","Practice Done","Mastered","Needs Revision"];
const SUBJ_ICON = {Physics:"⚛️", Chemistry:"🧪", Maths:"📐"};
const W_RANK = {High:3, Medium:2, Low:1};

function daysLeft(){ return Math.max(0, Math.ceil((new Date(EXAM) - new Date()) / 86400000)); }
function fmt(d){ if(!d) return "—"; const x=new Date(d); return x.toLocaleDateString("en-IN",{day:"numeric",month:"short"}); }
function dUntil(d){ if(!d) return null; return Math.ceil((new Date(d) - new Date())/86400000); }
function esc(s){ return (s||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }

/* ---------- progress UI helpers ---------- */
/* injects shared SVG gradient defs once; call before using pring() */
function pgradDefs(){
  if(document.getElementById("pgrad-defs")) return "";
  return `<svg width="0" height="0" style="position:absolute" id="pgrad-defs" aria-hidden="true"><defs>
    <linearGradient id="pg-accent" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7d9bff"/><stop offset="1" stop-color="#a78bfa"/></linearGradient>
    <linearGradient id="pg-phys" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#5aa2ff"/><stop offset="1" stop-color="#8ab8ff"/></linearGradient>
    <linearGradient id="pg-chem" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4ade80"/><stop offset="1" stop-color="#7ee8a8"/></linearGradient>
    <linearGradient id="pg-math" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#c084fc"/><stop offset="1" stop-color="#d4a8fc"/></linearGradient>
  </defs></svg>`;
}
/* progress ring: pring(65) or pring(65,{size:"lg",grad:"pg-phys",cls:"phys"}) */
function pring(pct, opts={}){
  const size = opts.size||"";           // "", "sm", "lg"
  const dim = size==="sm"?40 : size==="lg"?72 : 52;
  const grad = opts.grad||"pg-accent";
  const r = (dim/2)-4, c = 2*Math.PI*r;
  const off = c*(1-Math.max(0,Math.min(100,pct))/100);
  return `<div class="pring ${size}"><svg viewBox="0 0 ${dim} ${dim}">
    <circle class="track" cx="${dim/2}" cy="${dim/2}" r="${r}"/>
    <circle class="fill" cx="${dim/2}" cy="${dim/2}" r="${r}" stroke="url(#${grad})"
      stroke-dasharray="${c.toFixed(1)}" stroke-dashoffset="${off.toFixed(1)}"/>
  </svg><div class="txt">${Math.round(pct)}%</div></div>`;
}
/* progress bar: pbar(65) or pbar(65,{cls:"phys thick"}) */
function pbar(pct, opts={}){
  const cls = opts.cls||"";
  const w = Math.max(0,Math.min(100,pct||0));
  return `<div class="pbar ${cls}"><i style="width:${w}%"></i></div>`;
}

/* ---------- data store ---------- */
const Store = {
  data:null,
  _cacheKey:"jee.cache",
  _cached(){
    try{ return JSON.parse(localStorage.getItem(this._cacheKey)||"null"); }catch(e){ return null; }
  },
  _save(d){
    try{ localStorage.setItem(this._cacheKey, JSON.stringify(d)); }catch(e){}
  },
  async load(force=false){
    // instant paint from the last-known dataset, then revalidate in background
    if(!force && !this.data){
      const c = this._cached();
      if(c && c.syllabus){
        this.data = c;
        this._sig = this._sigOf(c);
        this._revalidate(); // fire and forget
        return this.data;
      }
    }
    const r = await fetch("/api/data"+(force?"?refresh=1":""));
    this.data = await r.json();
    this._sig = this._sigOf(this.data);
    this._save(this.data);
    return this.data;
  },
  // signature ignores server timestamps and the page's own computed _fields,
  // so only a genuine data change counts as "changed"
  _sigOf(o){
    return JSON.stringify(o, (k,v)=>(k==="fetched_at"||k.startsWith("_")) ? undefined : v);
  },
  async _revalidate(){
    try{
      const r = await fetch("/api/data");
      const fresh = await r.json();
      if(!fresh || fresh.error) return;
      const changed = this._sigOf(fresh) !== this._sig;
      this.data = fresh;
      this._sig = this._sigOf(fresh);
      this._save(fresh);
      if(changed && !sessionStorage.getItem("jee.autoreloaded")){
        // data changed elsewhere (Notion/another tab) — repaint once, never loop
        sessionStorage.setItem("jee.autoreloaded","1");
        toast("Updated from Notion ↻");
        setTimeout(()=>location.reload(), 1200);
      }
    }catch(e){/* offline — cached copy is fine */}
  },
  async update(id, field, value, el){
    const st = el ? el.closest("td,tr")?.querySelector(".savestate") : null;
    if(st) st.textContent = "saving…";
    try{
      const r = await fetch("/api/update",{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({id, field, value})});
      const j = await r.json();
      if(!j.ok) throw new Error(j.error);
      if(st){ st.textContent = "synced ✓"; setTimeout(()=>st.textContent="", 2000); }
      this._save(this.data); // keep the instant-paint cache in step with edits
      toast("Synced to Notion ✓");
      return true;
    }catch(e){
      if(st){ st.textContent = "failed ✗"; st.classList.add("err"); }
      toast("Sync failed: "+e.message, true);
      return false;
    }
  }
};

function toast(msg, err=false){
  let t = document.querySelector(".toast");
  if(!t){ t = document.createElement("div"); t.className="toast"; document.body.appendChild(t); }
  t.textContent = msg; t.className = "toast show"+(err?" err":"");
  setTimeout(()=>t.classList.remove("show"), 2600);
}

/* ---------- motivational quotes ---------- */
const QUOTES = [
  ["It always seems impossible until it's done.", "Nelson Mandela"],
  ["The pain you feel today will be the strength you feel tomorrow.", "Unknown"],
  ["Success is the sum of small efforts, repeated day in and day out.", "Robert Collier"],
  ["Don't watch the clock; do what it does. Keep going.", "Sam Levenson"],
  ["The expert in anything was once a beginner.", "Helen Hayes"],
  ["Discipline is choosing between what you want now and what you want most.", "Abraham Lincoln"],
  ["You don't have to be extreme, just consistent.", "Unknown"],
  ["Hard work beats talent when talent doesn't work hard.", "Tim Notke"],
  ["A year from now you'll wish you had started today.", "Karen Lamb"],
  ["IIT is not the dream of the clever, it's the reward of the stubborn.", "Unknown"],
  ["The chapter you avoid is the chapter that decides your rank.", "Unknown"],
  ["Tough times never last, but tough people do.", "Robert H. Schuller"],
  ["Dream is not what you see in sleep; dream is what doesn't let you sleep.", "A.P.J. Abdul Kalam"],
  ["Push yourself, because no one else is going to do it for you.", "Unknown"],
  ["One day or day one. You decide.", "Unknown"],
  ["Your only competition is who you were yesterday.", "Unknown"],
  ["Motivation gets you started. Habit keeps you going.", "Jim Ryun"],
  ["Every PYQ you solve is a rank you climb.", "Unknown"],
  ["The secret of getting ahead is getting started.", "Mark Twain"],
  ["Revision is boring. So is losing. Pick one.", "Unknown"],
  ["Small progress is still progress.", "Unknown"],
  ["If you're going through hell, keep going.", "Winston Churchill"],
  ["The difference between ordinary and extraordinary is that little extra.", "Jimmy Johnson"],
  ["Study while others are sleeping; work while others are loafing.", "William A. Ward"],
  ["It's not about perfect. It's about effort.", "Jillian Michaels"],
  ["Energy and persistence conquer all things.", "Benjamin Franklin"],
  ["You are one mock test away from understanding your weak spots.", "Unknown"],
  ["The rank you want is hiding behind the hours you're avoiding.", "Unknown"],
  ["Fall seven times, stand up eight.", "Japanese proverb"],
  ["January 22 is just a date. What you do until then is the story.", "Unknown"],
  ["जो ख्वाब देखने की हिम्मत करते हैं, वही उन्हें पूरा करते हैं।", "Unknown"],
];
function quoteOfTheMoment(){
  return QUOTES[Math.floor(Math.random()*QUOTES.length)];
}
function flashQuote(){
  let o = document.querySelector(".qoverlay");
  if(!o){
    o = document.createElement("div");
    o.className = "qoverlay";
    o.innerHTML = '<div class="qbig"><div class="qt"></div><div class="qa"></div><div class="qhint">click anywhere to close</div></div>';
    o.addEventListener("click", ()=>o.classList.remove("show"));
    document.body.appendChild(o);
  }
  const [t,a] = quoteOfTheMoment();
  o.querySelector(".qt").textContent = "“"+t+"”";
  o.querySelector(".qa").textContent = a ? "— "+a : "";
  o.classList.add("show");
}
document.addEventListener("keydown", e=>{
  if(e.key.toLowerCase()==="q" && !/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)) flashQuote();
  if(e.key==="Escape") document.querySelector(".qoverlay")?.classList.remove("show");
});

/* ---------- layout ---------- */
function shell(active, content){
  const nav = [
    ["index.html","Overview"],["chapters.html","Chapters"],["timeline.html","Timeline"],
    ["log.html","Daily Log"],["mocks.html","Mock Tests"],["revision.html","Revision"],["reports/latest.html","📊 Weekly"]
  ].map(([h,l])=>`<button class="${h===active?"on":""}" onclick="location.href='${h}'">${l}</button>`).join("");
  document.body.innerHTML = `
  <header class="top">
    <div class="topin">
      <div class="logo"><em>JEE 2027</em> · Command Center</div>
      <div class="qline" id="qline" title="click for another · press Q for fullscreen"></div>
      <button class="ghost" onclick="Store.load(true).then(()=>location.reload())">↻ Sync from Notion</button>
      <div class="countdown"><b id="cd"></b><span>days to Mains · 22 Jan 2027</span></div>
    </div>
    <nav>${nav}</nav>
  </header>
  <div class="wrap" id="main">${content}</div>
  <footer>Data source: Notion · JEE 2027 Dashboard · marks sync both ways</footer>`;
  const tick = ()=>{ const el=document.getElementById("cd"); if(el) el.textContent = daysLeft(); };
  tick();
  const ql = document.getElementById("qline");
  const setQ = ()=>{ const [t,a] = quoteOfTheMoment();
    ql.innerHTML = `“${esc(t)}”${a?` <span>— ${esc(a)}</span>`:""}`; };
  setQ();
  ql.addEventListener("click", setQ);

  /* smooth page transitions + eager preloading of sibling pages */
  requestAnimationFrame(()=>requestAnimationFrame(()=>document.body.classList.add("ready")));
  document.querySelectorAll("nav button").forEach(b=>{
    const href = b.getAttribute("onclick")?.match(/'([^']+)'/)?.[1];
    if(!href) return;
    fetch(href, {priority:"low"}).catch(()=>{}); // warm browser cache
    b.addEventListener("click", e=>{
      if(href===active) return;
      e.preventDefault(); e.stopPropagation();
      document.body.classList.add("leaving");
      setTimeout(()=>location.href=href, 150);
    }, {capture:true});
  });
}

/* ---------- shared transforms ---------- */
function chapters(){
  return (Store.data.syllabus||[]).map(c=>{
    const left = dUntil(c["Target Date"]);
    const done = c.Status==="Mastered" || c.Status==="Practice Done";
    const overdue = !done && left!==null && left<0;
    // priority score: weightage rank * urgency factor
    const urg = left===null ? 0.5 : (left<0 ? 3 : left<7 ? 2 : left<21 ? 1.4 : 1);
    c._prio = +( (W_RANK[c.Weightage]||1) * urg ).toFixed(2);
    c._left = left; c._done = done; c._overdue = overdue;
    return c;
  });
}
function statusClass(s){ return "s"+Math.max(0, STATUSES.indexOf(s)); }
