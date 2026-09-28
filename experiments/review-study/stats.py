import json,statistics as st,collections as C
R=[json.loads(l) for l in open('/home/claude/review-study/sample.jsonl')]
feat=['has_summary','has_personal_context','has_evaluation','has_critique','has_quote','has_structure','has_target_reader','mentions_translation_or_edition','spoiler_or_toc_dump']
def grp(rs,g): return [r for r in rs if r['group']==g]
def row(rs):
    return {'n':len(rs),'len_med':st.median([r['length_chars'] for r in rs]),'para_med':st.median([r['paragraphs'] for r in rs]),
            'likes_med':st.median([r['likes'] for r in rs]),'stars_mean':round(st.mean([r['stars'] for r in rs if r['stars']>0]),2),
            'summ_share_med':st.median([r['summary_share'] for r in rs]),
            **{f:round(100*sum(r[f] for r in rs)/len(rs)) for f in feat},
            'short<300':round(100*sum(r['length_chars']<300 for r in rs)/len(rs)),
            'long>=1500':round(100*sum(r['length_chars']>=1500 for r in rs)/len(rs)),
            'low_star<=3':round(100*sum(0<r['stars']<=3 for r in rs)/len(rs))}
print(C.Counter((r['site'],r['group']) for r in R))
print(C.Counter((r['site'],r['book']) for r in R))
for site in ['all','aladin','yes24']:
    rs=R if site=='all' else [r for r in R if r['site']==site]
    for g in ['top','ordinary']:
        print(site,g,row(grp(rs,g)))
# among long reviews only (>=1000)
for g in ['top','ordinary']:
    rs=[r for r in grp(R,g) if r['length_chars']>=1000]
    print('long>=1000',g,row(rs))
# combo: personal & evaluation & (critique or target)
for g in ['top','ordinary']:
    rs=grp(R,g); print(g,'pers+eval',round(100*sum(r['has_personal_context'] and r['has_evaluation'] for r in rs)/len(rs)),
      'critique_and_long',round(100*sum(r['has_critique'] and r['length_chars']>=1000 for r in rs)/len(rs)),
      'summary>=70',round(100*sum(r['summary_share']>=70 for r in rs)/len(rs)))
# top 15 by likes
for r in sorted(R,key=lambda r:-r['likes'])[:15]: print(r['likes'],r['site'],r['book'][:6],r['length_chars'],r['has_personal_context'],r['has_critique'],r['summary_share'])
