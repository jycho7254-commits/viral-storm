# -*- coding: utf-8 -*-
"""
정적 사이트 빌더 — GitHub Pages 배포용
- viral_site.html을 정적 버전으로 변환 (localStorage DB + seed 데이터 내장)
- AI 생성 API는 localStorage의 서버 URL로 프록시 (기본 localhost:8100)
"""
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
SRC = BASE / "src" / "web" / "viral_site.html"
OUT_DIR = BASE / "site"
OUT_DIR.mkdir(exist_ok=True)

html = SRC.read_text(encoding="utf-8")
seed = json.load(open(BASE / "data" / "learning" / "seed_for_static.json", encoding="utf-8"))
# 테이블명 통일 — 로컬 DB 스키마는 metrics_daily
if "metrics" in seed and "metrics_daily" not in seed:
    seed["metrics_daily"] = seed.pop("metrics")

# ── 1. API 레이어 교체: fetch → localStorage DB ──
STATIC_JS = """
// ═══════════ 정적 사이트 전용 — localStorage DB ═══════════
const SEED = __SEED__;
const LS_KEY = 'viral_storm_db_v1';
const SERVER_URL_KEY = 'viral_server_url';

// 서버 URL (AI 생성용)
function serverUrl(){
  let u = localStorage.getItem(SERVER_URL_KEY);
  if(u === null){ u = 'http://localhost:8100'; localStorage.setItem(SERVER_URL_KEY, u); }
  return u;
}

function loadDB(){
  let db = localStorage.getItem(LS_KEY);
  if(!db){ db = JSON.stringify(SEED); localStorage.setItem(LS_KEY, db); }
  return JSON.parse(db);
}
function saveDB(db){ localStorage.setItem(LS_KEY, JSON.stringify(db)); }
function resetDB(){ localStorage.removeItem(LS_KEY); location.reload(); }

let _nextId = null;
function nextId(db, table){
  if(_nextId === null){
    let mx = 0;
    for(const t of ['campaigns','contents','metrics_daily']){
      for(const r of (db[t]||[])) mx = Math.max(mx, r.id||0);
    }
    _nextId = mx + 1;
  }
  return _nextId++;
}

function computeKpis(rows){
  const s = k => rows.reduce((a,r)=>a+(+r[k]||0),0);
  const views=s('views'),likes=s('likes'),comments=s('comments'),clicks=s('clicks');
  const imp=s('impressions'),inst=s('installs'),spend=s('spend'),rev=s('revenue');
  return {views,likes,comments,clicks,impressions:imp,installs:inst,spend,revenue:rev,
    ctr: imp?+(clicks/imp*100).toFixed(2):null,
    vtr: imp?+(views/imp*100).toFixed(2):null,
    cvr: clicks?+(inst/clicks*100).toFixed(2):null,
    cpc: (clicks&&spend)?Math.round(spend/clicks):null,
    cpi: (inst&&spend)?Math.round(spend/inst):null,
    cpm: (imp&&spend)?Math.round(spend/imp*1000):null,
    roas: (spend&&rev)?Math.round(rev/spend*100):null,
    engagement: views?+((likes+comments)/views*100).toFixed(2):null};
}

// api() 오버라이드 — 경로별 로컬 처리, AI 생성만 서버 프록시
const _api = api;
api = async function(path, opts){
  const db = loadDB();
  const M = (opts&&opts.method)||'GET';
  let m;
  // ── 캠페인 목록 ──
  if(M==='GET' && (m=path.match(/^\\/api\\/campaigns$/))){
    return db.campaigns.map(c=>{
      const cs = db.contents.filter(x=>x.campaign_id===c.id);
      const mt = db.metrics_daily.filter(x=>x.campaign_id===c.id);
      return {...c, content_count:cs.length, posted_count:cs.filter(x=>x.status==='posted').length,
              total_views:mt.reduce((a,b)=>a+(+b.views||0),0)};
    }).reverse();
  }
  // ── 캠페인 생성 ──
  if(M==='POST' && (m=path.match(/^\\/api\\/campaigns$/))){
    const b = JSON.parse(opts.body);
    const c = {id:nextId(db), name:b.name||b.product_name, product_name:b.product_name,
      description:b.description||'', category:b.category||'game', target_age:b.target_age||'20-30',
      platforms:JSON.stringify(b.platforms||['naver']), start_date:b.start_date||'', end_date:b.end_date||'',
      status:'active', created_at:new Date().toISOString().slice(0,19).replace('T',' ')};
    db.campaigns.push(c); saveDB(db);
    return {id:c.id, ok:true};
  }
  // ── 캠페인 상세 ──
  if(M==='GET' && (m=path.match(/^\\/api\\/campaigns\\/(\\d+)$/))){
    const id=+m[1];
    const c=db.campaigns.find(x=>x.id===id); if(!c) throw new Error('404');
    const contents=db.contents.filter(x=>x.campaign_id===id).sort((a,b)=>b.id-a.id);
    const metrics=db.metrics_daily.filter(x=>x.campaign_id===id).sort((a,b)=>a.date<b.date?-1:1);
    return {...c, platforms:JSON.parse(c.platforms||'[]'), contents, metrics, kpis:computeKpis(metrics)};
  }
  // ── 캠페인 삭제 ──
  if(M==='DELETE' && (m=path.match(/^\\/api\\/campaigns\\/(\\d+)$/))){
    const id=+m[1];
    db.campaigns=db.campaigns.filter(x=>x.id!==id);
    db.contents=db.contents.filter(x=>x.campaign_id!==id);
    db.metrics_daily=db.metrics_daily.filter(x=>x.campaign_id!==id);
    saveDB(db); return {ok:true};
  }
  // ── 콘텐츠 생성 (서버 프록시) ──
  if(M==='POST' && (m=path.match(/^\\/api\\/campaigns\\/(\\d+)\\/generate.*$/))){
    const id=+m[1];
    const c=db.campaigns.find(x=>x.id===id); if(!c) throw new Error('404');
    try{
      const r = await fetch(serverUrl()+path, {method:'POST', timeout:60000}).then(x=>x.json());
      // 서버 성공 → 로컬 DB에도 반영
      const q = new URLSearchParams(path.split('?')[1]||'');
      const plat=q.get('platform')||'blog';
      if(r.generated && r.generated[0]){
        db.contents.push({id:nextId(db), campaign_id:id, platform:plat,
          kind: plat.includes('youtube')||plat.includes('shorts')?'shorts':'post',
          title:r.generated[0].title||'', body:'', status:'pending',
          created_at:new Date().toISOString().slice(0,19).replace('T',' ')});
        // 본문도 서버에서 가져오기
        const det = await fetch(serverUrl()+`/api/campaigns/${id}`).then(x=>x.json());
        const sv = det.contents.find(x=>x.title===(r.generated[0].title||''));
        const local = db.contents[db.contents.length-1];
        if(sv){ local.body = sv.body||''; local.title = sv.title||local.title; local.id = local.id; }
        saveDB(db);
      }
      return r;
    }catch(e){
      throw new Error('AI 서버 연결 실패 — 로컬 서버(' + serverUrl() + ')가 켜져 있는지 확인. ' + e.message);
    }
  }
  // ── 영상 생성 (서버 프록시) ──
  if(M==='POST' && (m=path.match(/^\\/api\\/contents\\/(\\d+)\\/make_video$/))){
    try{
      const r = await fetch(serverUrl()+path, {method:'POST', timeout:300000}).then(x=>x.json());
      if(r.ok){
        const cid=+m[1];
        const c=db.contents.find(x=>x.id===cid);
        if(c){ c.status='rendered'; c.post_url=r.video; saveDB(db); }
      }
      return r;
    }catch(e){
      throw new Error('AI 서버 연결 실패 — ' + e.message);
    }
  }
  // ── 지표 등록 ──
  if(M==='POST' && (m=path.match(/^\\/api\\/campaigns\\/(\\d+)\\/metrics.*$/))){
    const id=+m[1];
    const q=new URLSearchParams(path.split('?')[1]);
    const date=q.get('date')||new Date().toISOString().slice(0,10);
    let row=db.metrics_daily.find(x=>x.campaign_id===id&&x.date===date);
    if(!row){ row={id:nextId(db),campaign_id:id,date,views:0,likes:0,comments:0,clicks:0,impressions:0,installs:0,spend:0,revenue:0}; db.metrics_daily.push(row); }
    for(const k of ['views','likes','comments','clicks','impressions','installs']) row[k]=(+row[k]||0)+(+q.get(k)||0);
    for(const k of ['spend','revenue']) row[k]=(+row[k]||0)+(+q.get(k)||0);
    saveDB(db); return {ok:true};
  }
  // ── 개요 ──
  if(M==='GET' && path==='/api/stats/overview'){
    const counts={campaigns:db.campaigns.length, contents:db.contents.length,
      posted:db.contents.filter(x=>x.status==='posted').length,
      pending:db.contents.filter(x=>x.status==='pending').length};
    return {...counts, ...computeKpis(db.metrics_daily)};
  }
  return _api(path, opts);
};

// 서버 URL 설정 UI (상단바에 추가)
(function(){
  const pill = document.getElementById('enginePill');
  if(pill){
    pill.style.cursor='pointer';
    pill.title='클릭해서 AI 서버 주소 변경';
    pill.onclick=()=>{
      const u=prompt('AI 생성 서버 주소 (글/영상 생성용. Pages에는 AI 서버가 없으니 PC 서버 주소 입력)', serverUrl());
      if(u!==null){ localStorage.setItem(SERVER_URL_KEY, u.trim()); location.reload(); }
    };
  }
  // 리셋 버튼 topbar에
  const topbar=document.querySelector('.topbar-inner');
  const rst=document.createElement('button');
  rst.className='btn ghost small'; rst.textContent='초기화';
  rst.onclick=()=>{ if(confirm('데모 데이터로 초기화할까요?')) resetDB(); };
  rst.style.marginLeft='8px';
  topbar.appendChild(rst);
})();
"""

seed_json = json.dumps(seed, ensure_ascii=False)
static_js = STATIC_JS.replace("__SEED__", seed_json)

# ── 2. 삽입: api 함수 정의 직후에 오버라이드 배치 ──
anchor = "async function api(path, opts){"
idx = html.find(anchor)
if idx < 0:
    raise SystemExit("api 함수 앵커 못 찾음")
# 함수 끝(다음 // ── 대시보드 ── 주석) 찾기
end_marker = "// ── KPI 렌더 헬퍼 ──"
end_idx = html.find(end_marker)
if end_idx < 0:
    raise SystemExit("끝 앵커 못 찾음")

new_html = html[:end_idx] + static_js + "\n" + html[end_idx:]

# 타이틀 표시 — 정적 배포 판
new_html = new_html.replace("<title>Viral Storm — 종합 바이럴 운영</title>",
                            "<title>Viral Storm — 종합 바이럴 운영 (GitHub Pages)</title>")

out = OUT_DIR / "index.html"
out.write_text(new_html, encoding="utf-8")
print(f"정적 사이트 빌드: {out} ({out.stat().st_size//1024}KB)")
