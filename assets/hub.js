/* TechNext Marketing Hub - shared behaviour.
   index.html: renders the APPS array into cards + live search/filter.
   branding.html: copy buttons, swatch copy, sub-nav scroll-spy.
   Edit the APPS array at the bottom of index.html to add or change a tool. */
(function(){
  'use strict';
  var $=function(s,r){return (r||document).querySelector(s);};
  var $$=function(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s));};
  var esc=function(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});};

  var ICON={
    open:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17 17 7M8 7h9v9"/></svg>',
    link:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/><path d="M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/></svg>',
    copy:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
    down:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4v12m0 0 5-5m-5 5-5-5M4 20h16"/></svg>'
  };

  /* ---------- clipboard ---------- */
  function copyText(text,btn){
    var done=function(){
      if(!btn)return;
      var old=btn.innerHTML;
      btn.classList.add('copied');
      if(btn.classList.contains('btn'))btn.innerHTML=ICON.copy+' Copied';
      setTimeout(function(){btn.classList.remove('copied');if(btn.classList.contains('btn'))btn.innerHTML=old;},1400);
    };
    if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(text).then(done,function(){fallback();});}
    else fallback();
    function fallback(){
      var ta=document.createElement('textarea');ta.value=text;ta.setAttribute('readonly','');
      ta.style.position='fixed';ta.style.top='-1000px';document.body.appendChild(ta);ta.select();
      try{document.execCommand('copy');done();}catch(e){}
      document.body.removeChild(ta);
    }
  }
  document.addEventListener('click',function(e){
    var b=e.target.closest('[data-copy]');
    if(b){e.preventDefault();copyText(b.getAttribute('data-copy'),b);return;}
    var s=e.target.closest('[data-copy-from]');
    if(s){e.preventDefault();var src=$(s.getAttribute('data-copy-from'));if(src)copyText((src.innerText||src.textContent).trim(),s);}
  });

  /* ---------- reveal on scroll (IO with fallback) ---------- */
  function reveal(){
    var els=$$('.rv');
    if(!('IntersectionObserver' in window)){els.forEach(function(el){el.classList.add('in');});return;}
    var io=new IntersectionObserver(function(ents){ents.forEach(function(en){if(en.isIntersecting){en.target.classList.add('in');io.unobserve(en.target);}});},{rootMargin:'0px 0px -8% 0px',threshold:.05});
    els.forEach(function(el,i){el.style.transitionDelay=Math.min(i%6*60,300)+'ms';io.observe(el);});
    setTimeout(function(){els.forEach(function(el){if(!el.classList.contains('in')&&el.getBoundingClientRect().top<innerHeight)el.classList.add('in');});},800);
  }

  /* ---------- hub cards ---------- */
  function renderApps(){
    var grid=$('#apps');if(!grid||!window.APPS)return;
    grid.innerHTML=window.APPS.map(function(a,i){
      var links=(a.links||[]).map(function(l,j){
        var cls='btn'+(j===0?' p':'');
        var ic=l.icon==='down'?ICON.down:(j===0?ICON.open:ICON.link);
        return '<a class="'+cls+'" href="'+esc(l.href)+'"'+(/^https?:/.test(l.href)?' target="_blank" rel="noopener"':'')+(l.title?' title="'+esc(l.title)+'"':'')+'>'+ic+esc(l.label)+'</a>';
      }).join('');
      var badges=(a.badges||[]).map(function(b){return '<span class="badge '+esc(b.k||'')+'">'+esc(b.t)+'</span>';}).join('');
      var first=(a.links&&a.links[0])?a.links[0].href:'#';
      return '<article class="app rv" data-tags="'+esc((a.tags||[]).join(' ').toLowerCase()+' '+a.name.toLowerCase()+' '+(a.desc||'').toLowerCase())+'" data-cat="'+esc(a.cat||'')+'">'
        +'<div class="shot"><img src="'+esc(a.img)+'" alt="'+esc(a.name)+' screenshot" loading="'+(i<3?'eager':'lazy')+'" width="960" height="600"><div class="tag">'+badges+'</div></div>'
        +'<div class="body"><div class="num">0'+(i+1)+'</div>'
        +'<h3><a href="'+esc(first)+'"'+(/^https?:/.test(first)?' target="_blank" rel="noopener"':'')+'>'+esc(a.name)+'</a></h3>'
        +'<p>'+a.desc+'</p>'
        +(a.use?'<div class="use"><b>Use it for</b><span>'+a.use+'</span></div>':'')
        +'<div class="links">'+links+'</div></div></article>';
    }).join('');
  }
  function search(){
    var inp=$('#q');var grid=$('#apps');if(!inp||!grid)return;
    var chips=$$('.chip[data-cat]');var cat='';
    var count=$('#count');var empty=$('#empty');
    function apply(){
      var q=inp.value.trim().toLowerCase();var n=0;
      $$('.app',grid).forEach(function(c){
        var ok=(!q||c.getAttribute('data-tags').indexOf(q)>-1)&&(!cat||c.getAttribute('data-cat')===cat);
        c.classList.toggle('is-hidden',!ok);if(ok){n++;c.classList.add('in');}
      });
      if(count)count.textContent=n+' of '+$$('.app',grid).length+' tools';
      if(empty)empty.classList.toggle('show',n===0);
      $$('.row[data-tags]').forEach(function(r){r.style.display=(!q||r.getAttribute('data-tags').toLowerCase().indexOf(q)>-1)?'':'none';});
    }
    inp.addEventListener('input',apply);
    chips.forEach(function(ch){ch.addEventListener('click',function(){
      var on=ch.getAttribute('aria-pressed')==='true';
      chips.forEach(function(c){c.setAttribute('aria-pressed','false');});
      cat=on?'':ch.getAttribute('data-cat');ch.setAttribute('aria-pressed',on?'false':'true');apply();
    });});
    document.addEventListener('keydown',function(e){
      if(e.key==='/'&&document.activeElement!==inp&&!/input|textarea/i.test(document.activeElement.tagName)){e.preventDefault();inp.focus();}
      if(e.key==='Escape'&&document.activeElement===inp){inp.value='';apply();inp.blur();}
    });
    apply();
  }

  /* ---------- branding sub-nav scroll spy ---------- */
  function spy(){
    var links=$$('.subnav a[href^="#"]');if(!links.length)return;
    var secs=links.map(function(a){return $(a.getAttribute('href'));}).filter(Boolean);
    function upd(){
      var y=scrollY+140,cur=secs[0];
      secs.forEach(function(s){if(s.offsetTop<=y)cur=s;});
      links.forEach(function(a){a.classList.toggle('on',a.getAttribute('href')==='#'+cur.id);});
    }
    addEventListener('scroll',upd,{passive:true});upd();
  }

  /* ---------- responsive tables: give each cell of a table.rt its column name (shown as a label on phones) ---------- */
  function labelTables(){
    $$('table.rt').forEach(function(t){
      var hs=$$('thead th',t).map(function(th){return th.textContent.trim();});if(!hs.length)return;
      $$('tbody tr',t).forEach(function(tr){$$('td',tr).forEach(function(td,i){if(hs[i]&&!td.hasAttribute('data-label'))td.setAttribute('data-label',hs[i]);});});
    });
  }

  document.addEventListener('DOMContentLoaded',function(){renderApps();search();reveal();spy();labelTables();});
})();
