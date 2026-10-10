#!/usr/bin/env python3
"""公式SEIKOの種目別結果PDFを照合し、予選・決勝を種目内に保存する。
--today: 当日の種目のみ。変更なし=3、照合エラー時は書き込まない。
"""
from pathlib import Path
import re,json,unicodedata,datetime,urllib.request,urllib.error,concurrent.futures,io,sys
import pdfplumber
ROOT=Path(__file__).resolve().parent.parent
HTML=ROOT/'index.html'
BASE='https://swim.seiko.co.jp/2026/S70702/'
JST=datetime.timezone(datetime.timedelta(hours=9))
MAPS=[{'gender': '男子', 'classGrade': '小学生の部', 'distance': '50m', 'stroke': '自由形', 'final': 'ranking/03R111.pdf', 'prelim': 'ranking/03R091.pdf'}, {'gender': '男子', 'classGrade': '中学生の部', 'distance': '50m', 'stroke': '自由形', 'final': 'ranking/03R113.pdf', 'prelim': 'ranking/03R091.pdf'}, {'gender': '男子', 'classGrade': '中学生の部', 'distance': '100m', 'stroke': '自由形', 'final': 'ranking/02R071.pdf', 'prelim': 'ranking/02R052.pdf'}, {'gender': '男子', 'classGrade': '小学生の部', 'distance': '50m', 'stroke': '背泳ぎ', 'final': 'ranking/03R105.pdf', 'prelim': 'ranking/03R089.pdf'}, {'gender': '男子', 'classGrade': '中学生の部', 'distance': '50m', 'stroke': '背泳ぎ', 'final': 'ranking/03R107.pdf', 'prelim': 'ranking/03R089.pdf'}, {'gender': '男子', 'classGrade': '中学生の部', 'distance': '100m', 'stroke': '背泳ぎ', 'final': 'ranking/01R018.pdf', 'prelim': 'ranking/01R006.pdf'}, {'gender': '男子', 'classGrade': '小学生の部', 'distance': '50m', 'stroke': '平泳ぎ', 'final': 'ranking/02R061.pdf', 'prelim': 'ranking/02R046.pdf'}, {'gender': '男子', 'classGrade': '中学生の部', 'distance': '50m', 'stroke': '平泳ぎ', 'final': 'ranking/02R063.pdf', 'prelim': 'ranking/02R046.pdf'}, {'gender': '男子', 'classGrade': '中学生の部', 'distance': '100m', 'stroke': '平泳ぎ', 'final': 'ranking/01R022.pdf', 'prelim': 'ranking/01R008.pdf'}, {'gender': '男子', 'classGrade': '小学生の部', 'distance': '50m', 'stroke': 'バタフライ', 'final': 'ranking/02R055.pdf', 'prelim': 'ranking/02R044.pdf'}, {'gender': '男子', 'classGrade': '中学生の部', 'distance': '50m', 'stroke': 'バタフライ', 'final': 'ranking/02R057.pdf', 'prelim': 'ranking/02R044.pdf'}, {'gender': '男子', 'classGrade': '中学生の部', 'distance': '100m', 'stroke': 'バタフライ', 'final': 'ranking/03R119.pdf', 'prelim': 'ranking/03R095.pdf'}, {'gender': '男子', 'classGrade': '小学生の部', 'distance': '100m', 'stroke': '個人メドレー', 'final': 'ranking/01R026.pdf', 'prelim': 'ranking/01R010.pdf'}, {'gender': '男子', 'classGrade': '小学生の部', 'distance': '200m', 'stroke': '個人メドレー', 'final': 'ranking/03R099.pdf', 'prelim': 'ranking/03R087.pdf'}, {'gender': '男子', 'classGrade': '中学生の部', 'distance': '100m', 'stroke': '個人メドレー', 'final': 'ranking/01R028.pdf', 'prelim': 'ranking/01R010.pdf'}, {'gender': '男子', 'classGrade': '中学生の部', 'distance': '200m', 'stroke': '個人メドレー', 'final': 'ranking/03R101.pdf', 'prelim': 'ranking/03R087.pdf'}, {'gender': '女子', 'classGrade': '小学生の部', 'distance': '50m', 'stroke': '自由形', 'final': 'ranking/03R110.pdf', 'prelim': 'ranking/03R090.pdf'}, {'gender': '女子', 'classGrade': '中学生の部', 'distance': '50m', 'stroke': '自由形', 'final': 'ranking/03R112.pdf', 'prelim': 'ranking/03R090.pdf'}, {'gender': '女子', 'classGrade': '中学生の部', 'distance': '100m', 'stroke': '自由形', 'final': 'ranking/02R070.pdf', 'prelim': 'ranking/02R051.pdf'}, {'gender': '女子', 'classGrade': '小学生の部', 'distance': '50m', 'stroke': '背泳ぎ', 'final': 'ranking/03R104.pdf', 'prelim': 'ranking/03R088.pdf'}, {'gender': '女子', 'classGrade': '中学生の部', 'distance': '50m', 'stroke': '背泳ぎ', 'final': 'ranking/03R106.pdf', 'prelim': 'ranking/03R088.pdf'}, {'gender': '女子', 'classGrade': '中学生の部', 'distance': '100m', 'stroke': '背泳ぎ', 'final': 'ranking/01R017.pdf', 'prelim': 'ranking/01R005.pdf'}, {'gender': '女子', 'classGrade': '小学生の部', 'distance': '50m', 'stroke': '平泳ぎ', 'final': 'ranking/02R060.pdf', 'prelim': 'ranking/02R045.pdf'}, {'gender': '女子', 'classGrade': '中学生の部', 'distance': '50m', 'stroke': '平泳ぎ', 'final': 'ranking/02R062.pdf', 'prelim': 'ranking/02R045.pdf'}, {'gender': '女子', 'classGrade': '中学生の部', 'distance': '100m', 'stroke': '平泳ぎ', 'final': 'ranking/01R021.pdf', 'prelim': 'ranking/01R007.pdf'}, {'gender': '女子', 'classGrade': '小学生の部', 'distance': '50m', 'stroke': 'バタフライ', 'final': 'ranking/02R054.pdf', 'prelim': 'ranking/02R043.pdf'}, {'gender': '女子', 'classGrade': '中学生の部', 'distance': '50m', 'stroke': 'バタフライ', 'final': 'ranking/02R056.pdf', 'prelim': 'ranking/02R043.pdf'}, {'gender': '女子', 'classGrade': '中学生の部', 'distance': '100m', 'stroke': 'バタフライ', 'final': 'ranking/03R118.pdf', 'prelim': 'ranking/03R094.pdf'}, {'gender': '女子', 'classGrade': '小学生の部', 'distance': '100m', 'stroke': '個人メドレー', 'final': 'ranking/01R025.pdf', 'prelim': 'ranking/01R009.pdf'}, {'gender': '女子', 'classGrade': '小学生の部', 'distance': '200m', 'stroke': '個人メドレー', 'final': 'ranking/03R098.pdf', 'prelim': 'ranking/03R086.pdf'}, {'gender': '女子', 'classGrade': '中学生の部', 'distance': '100m', 'stroke': '個人メドレー', 'final': 'ranking/01R027.pdf', 'prelim': 'ranking/01R009.pdf'}, {'gender': '女子', 'classGrade': '中学生の部', 'distance': '200m', 'stroke': '個人メドレー', 'final': 'ranking/03R100.pdf', 'prelim': 'ranking/03R086.pdf'}]
pdfs={}
def norm(s):return re.sub(r'\s+','',unicodedata.normalize('NFKC',s)).replace('﨑','崎').replace('髙','高')
def parse(url,cl):
 raw=pdfs.get(url)
 if not raw:return []
 rows=[]
 with pdfplumber.open(io.BytesIO(raw)) as doc:
  for page in doc.pages:
   words=page.extract_words(); head=''.join(w['text'] for w in words if w['top']<155)
   if '九州Jr.（'+cl.replace('の部','')+'）' not in head:continue
   starts=[w for w in words if re.fullmatch(r'\d+/\d+',w['text']) and 60<w['x0']<100 and 180<w['top']<780]
   for i,w in enumerate(starts):
    y=w['top']; end=starts[i+1]['top']-2 if i+1<len(starts) else 780
    row=[v for v in words if y-2<=v['top']<end]
    name=' '.join(v['text'] for v in row if 145<=v['x0']<213 and v['top']<y+4)
    team=''.join(v['text'] for v in row if 213<=v['x0']<310 and v['top']<y+4)
    ranks=[v['text'] for v in row if v['x0']<55 and v['top']<y+4]
    times=[v['text'] for v in row if 435<=v['x0']<515 and re.fullmatch(r'(?:\d+:)?\d+\.\d\d',v['text'])]
    notes=[v['text'] for v in row if v['text'] in ['棄権','失格','途中棄権']]
    assert len(times)<=1,(url,name,times)
    assert len(times)==1 or notes,(url,name,[v['text'] for v in row])
    r={'name':name,'team':team,'rank':int(ranks[0]) if ranks else None,'time':times[0] if times else None,'heat':int(w['text'].split('/')[0]),'lane':int(w['text'].split('/')[1]),'sourceUrl':'https://swim.seiko.co.jp/2026/S70702/'+url}
    if notes:r['note']=notes[0]
    rows.append(r)
 return rows

def main():
 global pdfs
 html=HTML.read_text(); marker=re.search(r'/\*__DATA__\*/(.*?)/\*__DATA_END__\*/',html,re.S)
 data=json.loads(marker.group(1)); before=json.dumps(data,ensure_ascii=False,sort_keys=True)
 now=datetime.datetime.now(JST)
 selected=[p for p in data['program'] if not p.get('live') and ('--today' not in sys.argv or p.get('day','').startswith(f'{now.month}/{now.day}('))]
 pairs=[]
 for p in selected:
  mp=next(x for x in MAPS if all(x[k]==p[k] for k in ['gender','classGrade','distance','stroke']))
  pairs.append((p,mp))
 urls={mp[k] for _,mp in pairs for k in ('prelim','final')}
 def get(url):
  try:
   with urllib.request.urlopen(BASE+url,timeout=25) as r:raw=r.read()
   if not raw.startswith(b'%PDF'):raise RuntimeError('PDFではありません: '+url)
   return url,raw
  except urllib.error.HTTPError as e:
   if e.code==404:return url,None
   raise
 pdfs=dict(concurrent.futures.ThreadPoolExecutor(max_workers=4).map(get,sorted(urls)))
 audit=[]
 for p,mp in pairs:
  entries=[e for e in data['entries'] if p['no'] in e['programNos'] and not e.get('live')]
  p['resultSources']={rd:BASE+mp[k] for rd,k in [('予選','prelim'),('決勝','final')]}
  for rd,k in [('予選','prelim'),('決勝','final')]:
   rows=parse(mp[k],p['classGrade'])
   if not rows:continue
   matched=[]
   for r in rows:
    hits=[e for e in entries if norm(e['name'])==norm(r['name']) and norm(e['team'])==norm(r['team'])]
    if len(hits)!=1:raise RuntimeError(f"照合できません: No.{p['no']} {rd} {r['name']} {r['team']}")
    e=hits[0];result={kk:vv for kk,vv in r.items() if kk not in ['name','team'] and vv is not None};result['round']=rd
    matched.append((e,result))
   assert len({e['id'] for e,_ in matched})==len(rows)
   # Replace one complete official round together, including corrections / withdrawals.
   for e in entries:e.setdefault('results',{}).pop(rd,None)
   for e,r in matched:e['results'][rd]=r
   p.setdefault('resultCounts',{})[rd]=len(rows)
   audit.append({'no':p['no'],'round':rd,'officialRows':len(rows),'matchedRows':len(matched)})
  for e in entries:
   if e.get('results'):e['result']=e['results'].get('決勝',e['results'].get('予選'))
 counts=data['summary']['counts']
 assert len([e for e in data['entries'] if not e.get('live')])==counts['individualEntries']
 assert len({e['id'] for e in data['entries'] if not e.get('live')})==counts['swimmers']
 assert len(data['program'])==counts['programItems']
 data['meta'].setdefault('pdfResultSchema',1)
 data['meta']['source']='実施日は日本水泳連盟の公式競技日程による ／ 結果は公式SEIKO種目別結果PDFによる'
 if json.dumps(data,ensure_ascii=False,sort_keys=True)==before:
  print('変更なし（公式PDFとの全件照合済み）');return 3
 total=sum(len(e.get('results',{})) for e in data['entries'])
 pre=sum('予選' in e.get('results',{}) for e in data['entries']);fin=sum('決勝' in e.get('results',{}) for e in data['entries'])
 events=sum(bool(p.get('resultCounts',{}).get('予選')) for p in data['program'])
 stamp=now.strftime('%Y-%m-%d %H:%M JST')
 data['meta']['resultsUpdatedAt']=stamp
 data['meta']['liveLabel']=f'速報 {now.month}/{now.day} {now:%H:%M}'
 data['meta']['notice']=f'{events}種目：予選{pre}件・決勝{fin}件を反映。\n公式SEIKO種目別結果PDFより。予選と決勝は切り替えて確認できます。\n記録確認：{stamp}。最新の記録は公式速報をご確認ください。'
 new=json.dumps(data,ensure_ascii=False,separators=(',',':'))
 HTML.write_text(html[:marker.start(1)]+new+html[marker.end(1):])
 (ROOT/'live.json').write_text(json.dumps({'n':total,'v':data['meta']['liveLabel'],'updated':now.strftime('%Y-%m-%d %H:%M:%S'),'source':'SEIKO official result PDFs','audit':audit},ensure_ascii=False)+'\n')
 print(f'更新しました：{events}種目・予選{pre}件・決勝{fin}件、公式行数と照合済み');return 0
if __name__=='__main__':sys.exit(main())
