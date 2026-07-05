import requests, json, re, html, datetime, time

FUND_LIST = [
    {'code':'513100','name':'纳指ETF国泰','track':'纳指100','type':'ETF'},
    {'code':'513300','name':'纳斯达克ETF华夏','track':'纳斯达克','type':'ETF'},
    {'code':'513500','name':'标普500ETF博时','track':'标普500','type':'ETF'},
    {'code':'159941','name':'纳指ETF广发','track':'纳指100','type':'ETF'},
    {'code':'159509','name':'纳指科技ETF景顺','track':'纳指科技','type':'ETF'},
    {'code':'159612','name':'标普500ETF','track':'标普500','type':'ETF'},
    {'code':'501018','name':'南方原油LOF','track':'原油','type':'LOF'},
    {'code':'501225','name':'全球芯片LOF','track':'全球芯片','type':'LOF'},
    {'code':'160644','name':'纳指100LOF','track':'纳指100','type':'LOF'},
    {'code':'513310','name':'中韩半导体ETF','track':'半导体','type':'ETF'},
    {'code':'513180','name':'标普500信息科技ETF','track':'标普500信息科技','type':'ETF'},
    {'code':'513650','name':'标普500ETF南方','track':'标普500','type':'ETF'},
    {'code':'159696','name':'纳指ETF易方达','track':'纳指100','type':'ETF'},
    {'code':'159660','name':'纳指ETF汇添富','track':'纳指100','type':'ETF'},
    {'code':'159659','name':'纳斯达克100ETF','track':'纳指100','type':'ETF'},
    {'code':'159513','name':'纳斯达克100ETF大成','track':'纳指100','type':'ETF'},
    {'code':'159501','name':'纳指ETF嘉实','track':'纳指100','type':'ETF'},
    {'code':'513870','name':'纳指ETF富国','track':'纳指100','type':'ETF'},
    {'code':'513390','name':'纳指100ETF博时','track':'纳指100','type':'ETF'},
    {'code':'513110','name':'纳斯达克100ETF','track':'纳指100','type':'ETF'},
    {'code':'161130','name':'纳斯达克100LOF','track':'纳指100','type':'LOF'},
    {'code':'161226','name':'国投白银LOF','track':'白银','type':'LOF'},
    {'code':'160723','name':'嘉实原油LOF','track':'原油','type':'LOF'},
    {'code':'159985','name':'豆粕ETF华夏','track':'豆粕','type':'ETF'},
]

STATUS = {"501225":"暂停申购","501018":"暂停申购","159509":"多次暂停","161226":"限额100元","159696":"7/6恢复","513310":"曾暂停"}

def get_nav(c):
    try:
        r=requests.get(f"http://fundf10.eastmoney.com/F10DataApi.aspx?type=lsjz&code={c}&page=1&per=3",timeout=15,headers={'User-Agent':'Mozilla/5.0'})
        t=r.text
        if 'apidata=' in t:
            m=re.search(r'content:"([^"]*)"',t,re.DOTALL)
            if m:
                content=m.group(1)
                rows=re.findall(r'<tr>(.*?)</tr>',content,re.DOTALL)
                data=[]
                for row in rows:
                    cells=re.findall(r'<td[^>]*>(.*?)</td>',row,re.DOTALL)
                    if len(cells)>=4:
                        nav=html.unescape(cells[1].strip()).replace(',','')
                        data.append({'date':html.unescape(cells[0].strip()),'nav':float(nav) if nav else 0})
                return data
    except Exception as e:
        print(f"nav error {c}: {e}")
    return None

def get_quotes(codes):
    results={}
    for c in codes:
        secid=f"1.{c}" if c.startswith(('5','6')) else f"0.{c}"
        try:
            r=requests.get(f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f58,f60",timeout=10,headers={'User-Agent':'Mozilla/5.0'})
            d=r.json().get('data',{})
            if d and d.get('f43') and d.get('f60'):
                results[c]={'close':float(d['f43'])/100,'pre_close':float(d['f60'])/100,'name':d.get('f58','')}
        except Exception as e:
            print(f"quote error {c}: {e}")
        time.sleep(0.1)
    return results

def get_yahoo(sym):
    try:
        r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=5d",timeout=15,headers={'User-Agent':'Mozilla/5.0'})
        d=r.json().get('chart',{}).get('result',[None])[0]
        if not d: return None
        ts=d.get('timestamp',[])
        cl=d['indicators']['quote'][0].get('close',[])
        v=[(ts[i],c) for i,c in enumerate(cl) if c is not None]
        if len(v)>=2:
            return {'latest':v[-1][1],'prev':v[-2][1],'chg':round((v[-1][1]/v[-2][1]-1)*100,2)}
    except Exception as e:
        print(f"yahoo error {sym}: {e}")
    return None

def get_markets():
    syms={'道琼斯':'DIA','标普500':'SPY','纳斯达克100':'QQQ','德国DAX':'EWG','WTI原油':'USO','USDCNH':'USDCNH=X'}
    r={}
    for n,s in syms.items():
        d=get_yahoo(s)
        if d:
            r[n]={'close':round(d['latest'],4),'chg':d['chg']}
        time.sleep(0.5)
    return r

def gen_html(m, fd, td):
    market_json=json.dumps(m,ensure_ascii=False)
    fund_json=json.dumps(fd,ensure_ascii=False)
    now=datetime.datetime.now()
    dn=['周一','周二','周三','周四','周五','周六','周日'][now.weekday()]
    
    mc=[]
    for n,c in [('道琼斯','red-600'),('标普500','slate-600'),('纳斯达克100','green-600'),('德国DAX','red-600'),('WTI原油','green-600'),('USDCNH','slate-700')]:
        d=m.get(n,{}); chg=d.get('chg',0); sg='+' if chg>0 else ''
        mc.append(f'<div class="bg-white rounded-xl p-4 border border-slate-200"><p class="text-xs text-slate-500 mb-1">{n}</p><p class="text-lg font-bold text-{c}">{sg}{chg}%</p></div>')
    mc_s=''.join(mc)
    
    tf=[f for f in fd if f['premium']>5][:3]
    tc=[]
    for r in tf:
        s=STATUS.get(r['code'],"需确认")
        st_c="tag-suspended" if "暂停" in s else "tag-limited" if "限额" in s else "tag-open"
        tc.append(f'<div class="bg-white rounded-xl border border-slate-200 p-5"><div class="flex justify-between mb-2"><span class="text-xs text-slate-500 font-mono">{r["code"]}</span><span class="tag {"tag-etf" if r["type"]=="ETF" else "tag-lof"}">{r["type"]}</span></div><h3 class="font-bold text-slate-900 mb-1">{r["name"]}</h3><p class="text-xs text-slate-500 mb-3">跟踪：{r["track"]}</p><div class="flex justify-between"><div><p class="text-3xl font-bold {"premium-high" if r["premium"]>15 else "premium-mid" if r["premium"]>5 else "premium-low"}">+{r["premium"]:.2f}%</p><p class="text-xs text-slate-500">估算溢价率</p></div><div class="text-right"><span class="tag {st_c} text-xs">{s}</span></div></div><div class="mt-3 pt-3 border-t flex justify-between text-xs text-slate-500"><span>收盘价:{r["close"]:.3f}</span><span>净值:{r["latest_nav"]:.4f}</span></div></div>')
    tc_s=''.join(tc)
    
    trs=[]
    for r in fd:
        s=STATUS.get(r['code'],"需确认")
        st_c="tag-suspended" if "暂停" in s else "tag-limited" if "限额" in s else "tag-open"
        ac='text-red-600' if r['a_chg']>0 else 'text-green-600' if r['a_chg']<0 else 'text-slate-600'
        acs='+' if r['a_chg']>0 else ''
        pc="premium-high" if r['premium']>15 else "premium-mid" if r['premium']>5 else "premium-low" if r['premium']<0 else "text-slate-600"
        pb="bg-premium-high" if r['premium']>15 else "bg-premium-mid" if r['premium']>5 else "bg-premium-low" if r['premium']<0 else ""
        trs.append(f'<tr class="hover:bg-slate-50"><td class="py-3 px-2 font-mono text-slate-900">{r["code"]}</td><td class="py-3 px-2 font-medium text-slate-900">{r["name"]}</td><td class="py-3 px-2"><span class="tag {"tag-etf" if r["type"]=="ETF" else "tag-lof"}">{r["type"]}</span></td><td class="py-3 px-2 text-slate-600">{r["track"]}</td><td class="py-3 px-2 text-right font-mono">{r["close"]:.3f}</td><td class="py-3 px-2 text-right font-mono {ac}">{acs}{r["a_chg"]:.2f}%</td><td class="py-3 px-2 text-right font-mono text-slate-600">{r["latest_nav"]:.4f}</td><td class="py-3 px-2 text-right"><span class="inline-block px-2 py-0.5 rounded text-sm font-bold {pb} {pc}">+{r["premium"]:.2f}%</span></td><td class="py-3 px-2"><span class="tag {st_c}">{s}</span></td><td class="py-3 px-2 text-xs font-medium">{"高溢价卖出" if r["premium"]>15 else "底仓套利" if r["premium"]>8 else "LOF申购" if r["premium"]>3 and r["type"]=="LOF" else "折价买入" if r["premium"]<0 else "关注" if r["premium"]>3 else "持有"}</td></tr>')
    tr_s=''.join(trs)
    
    return f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>QDII ETF/LOF 套利分析看板</title><script src="https://cdn.tailwindcss.com"></script><script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script><style>body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,'Noto Sans SC',sans-serif}}.glass{{background:rgba(255,255,255,0.85);backdrop-filter:blur(12px)}}.card-hover{{transition:all 0.2s ease}}.card-hover:hover{{transform:translateY(-2px);box-shadow:0 10px 25px -5px rgba(0,0,0,0.1)}}.premium-high{{color:#dc2626}}.premium-mid{{color:#ea580c}}.premium-low{{color:#16a34a}}.bg-premium-high{{background:#fef2f2;border:1px solid #fecaca}}.bg-premium-mid{{background:#fff7ed;border:1px solid #fed7aa}}.bg-premium-low{{background:#f0fdf4;border:1px solid #bbf7d0}}.tag{{font-size:0.75rem;padding:0.125rem 0.5rem;border-radius:9999px;font-weight:500}}.tag-etf{{background:#eff6ff;color:#1e40af;border:1px solid #dbeafe}}.tag-lof{{background:#f5f3ff;color:#5b21b6;border:1px solid #e9d5ff}}.tag-suspended{{background:#fef2f2;color:#991b1b;border:1px solid #fecaca}}.tag-limited{{background:#fff7ed;color:#9a3412;border:1px solid #fed7aa}}.tag-open{{background:#f0fdf4;color:#166534;border:1px solid #bbf7d0}}</style></head>
<body class="bg-slate-50 text-slate-800 min-h-screen">
<header class="sticky top-0 z-50 glass border-b border-slate-200"><div class="max-w-7xl mx-auto px-4 py-4 flex justify-between"><div class="flex gap-3"><div class="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold">Q</div><div><h1 class="text-xl font-bold text-slate-900">QDII ETF/LOF 套利分析看板</h1><p class="text-xs text-slate-500">基于底层持仓与海外市场涨跌幅估算</p></div></div><div class="text-right"><p class="text-sm font-semibold text-slate-900">{td} {dn}</p><p class="text-xs text-slate-500">更新 {now.strftime("%H:%M")}</p></div></div></header>
<main class="max-w-7xl mx-auto px-4 py-6 space-y-6">
<section><div class="flex justify-between mb-3"><h2 class="text-lg font-bold text-slate-900">海外市场概况</h2></div><div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">{mc_s}</div></section>
<section><h2 class="text-lg font-bold text-slate-900 mb-3">重点套利机会</h2><div class="grid grid-cols-1 md:grid-cols-3 gap-4">{tc_s}</div></section>
<section class="bg-white rounded-xl border border-slate-200 p-5"><h2 class="text-lg font-bold text-slate-900 mb-4">估算溢价率分布</h2><div id="chart-premium" style="width:100%;height:420px"></div></section>
<section class="grid grid-cols-1 lg:grid-cols-3 gap-4">
<div class="bg-white rounded-xl border border-slate-200 p-5"><div class="flex gap-2 mb-3"><span class="w-8 h-8 rounded-full bg-red-100 text-red-600 flex items-center justify-center text-sm font-bold">1</span><h3 class="font-bold text-slate-900">底仓高溢价卖出</h3></div><p class="text-sm text-slate-600 mb-3">已持有高溢价品种的投资者，可在二级市场卖出高溢价ETF/LOF，同时买入低溢价或折价同类基金。</p><ul class="text-sm space-y-1.5 text-slate-600"><li class="flex justify-between"><span class="text-slate-500">卖出高溢价ETF</span><span class="font-medium text-red-600">溢价 > 15%</span></li><li class="flex justify-between"><span class="text-slate-500">买入低溢价品种</span><span class="font-medium text-green-600">溢价 < 3%</span></li></ul></div>
<div class="bg-white rounded-xl border border-slate-200 p-5"><div class="flex gap-2 mb-3"><span class="w-8 h-8 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center text-sm font-bold">2</span><h3 class="font-bold text-slate-900">LOF申购套利</h3></div><p class="text-sm text-slate-600 mb-3">场内申购LOF，T+2日到账后卖出，赚取溢价差。需扣除申购费（1.0-1.5%）与交易佣金。</p><div class="space-y-2"><div class="flex justify-between p-2 rounded bg-slate-50"><span class="text-sm">161226 国投白银LOF</span><span class="text-xs tag tag-limited">限额100元</span></div><div class="flex justify-between p-2 rounded bg-red-50"><span class="text-sm">501225 全球芯片LOF</span><span class="text-xs tag tag-suspended">暂停申购</span></div><div class="flex justify-between p-2 rounded bg-red-50"><span class="text-sm">501018 南方原油LOF</span><span class="text-xs tag tag-suspended">暂停申购</span></div></div></div>
<div class="bg-white rounded-xl border border-slate-200 p-5"><div class="flex gap-2 mb-3"><span class="w-8 h-8 rounded-full bg-green-100 text-green-600 flex items-center justify-center text-sm font-bold">3</span><h3 class="font-bold text-slate-900">折价买入</h3></div><p class="text-sm text-slate-600 mb-3">二级市场交易价格低于估算净值时，可直接场内买入，等待溢价回归。</p><div class="p-3 rounded-lg bg-green-50 border border-green-200"><p class="font-medium text-green-800">关注折价品种</p><p class="text-sm text-green-700 mt-1">估算折价 <span class="font-bold">-0.5%</span> 以下</p><p class="text-xs text-green-600 mt-1">适合长期看好对应市场的投资者直接配置</p></div></div>
</section>
<section class="bg-white rounded-xl border border-slate-200 p-5"><div class="flex justify-between mb-4"><h2 class="text-lg font-bold text-slate-900">完整基金数据</h2></div><div class="overflow-x-auto"><table class="w-full text-sm"><thead><tr class="border-b border-slate-200 text-slate-500 text-xs uppercase"><th class="text-left py-3 px-2">代码</th><th class="text-left py-3 px-2">名称</th><th class="text-left py-3 px-2">类型</th><th class="text-left py-3 px-2">跟踪标的</th><th class="text-right py-3 px-2">收盘价</th><th class="text-right py-3 px-2">A股涨跌</th><th class="text-right py-3 px-2">最新净值</th><th class="text-right py-3 px-2">估算溢价率</th><th class="text-left py-3 px-2">申购状态</th><th class="text-left py-3 px-2">策略</th></tr></thead><tbody class="divide-y divide-slate-100">{tr_s}</tbody></table></div></section>
<section class="bg-amber-50 rounded-xl border border-amber-200 p-5"><h2 class="text-lg font-bold text-amber-900 mb-3">风险提示</h2><div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm text-amber-800"><div class="space-y-1"><p><strong>T+2时间差：</strong>LOF申购T+2日到账，期间美股可能大幅波动，侵蚀套利空间。</p><p><strong>外汇额度限制：</strong>501225、501018等已暂停申购；多数LOF限额100元/日。</p><p><strong>交易所停牌：</strong>159509、513310等高溢价品种可能盘中临时停牌。</p></div><div class="space-y-1"><p><strong>汇率侵蚀：</strong>人民币升值持续侵蚀美元资产回报。</p><p><strong>流动性风险：</strong>501225日成交仅约4500万，大额卖出可能冲击价格。</p><p><strong>数据偏差：</strong>估算净值基于公开数据，实际基金公司公布净值可能略有差异。</p></div></div><p class="text-xs text-amber-700 mt-3 pt-3 border-t border-amber-200">免责声明：本看板基于公开市场数据估算，不构成投资建议。</p></section>
</main>
<footer class="max-w-7xl mx-auto px-4 py-6 text-center text-xs text-slate-400"><p>数据来源：天天基金网、东方财富、Yahoo Finance | 仅用于研究参考</p></footer>
<script>const fundData={fund_json};const statusMap={{"501225":"暂停申购","501018":"暂停申购","159509":"多次暂停","161226":"限额100元","159696":"7/6恢复","513310":"曾暂停"}};function getStatus(c){{return statusMap[c]||"需确认"}}function premClass(p){{if(p>15)return"premium-high";if(p>5)return"premium-mid";if(p<0)return"premium-low";return"text-slate-600"}}function premBg(p){{if(p>15)return"bg-premium-high";if(p>5)return"bg-premium-mid";if(p<0)return"bg-premium-low";return""}}function renderTable(){{const tbody=document.getElementById("fund-table-body");tbody.innerHTML="";fundData.forEach(r=>{{const s=getStatus(r.code);const ac=r.a_chg>0?"text-red-600":r.a_chg<0?"text-green-600":"text-slate-600";const acs=r.a_chg>0?"+":"";const pc=premClass(r.premium);const pb=premBg(r.premium);const tr=document.createElement("tr");tr.className="hover:bg-slate-50";tr.innerHTML=`<td class="py-3 px-2 font-mono text-slate-900">${{r.code}}</td><td class="py-3 px-2 font-medium text-slate-900">${{r.name}}</td><td class="py-3 px-2"><span class="tag ${{r.type==="ETF"?"tag-etf":"tag-lof"}}">${{r.type}}</span></td><td class="py-3 px-2 text-slate-600">${{r.track}}</td><td class="py-3 px-2 text-right font-mono">${{r.close.toFixed(3)}}</td><td class="py-3 px-2 text-right font-mono ${{ac}}">${{acs}}${{r.a_chg.toFixed(2)}}%</td><td class="py-3 px-2 text-right font-mono text-slate-600">${{r.latest_nav.toFixed(4)}}</td><td class="py-3 px-2 text-right"><span class="inline-block px-2 py-0.5 rounded text-sm font-bold ${{pb}} ${{pc}}">${{r.premium>0?"+":""}}${{r.premium.toFixed(2)}}%</span></td><td class="py-3 px-2"><span class="tag ${{s.includes("暂停")?"tag-suspended":s.includes("限额")?"tag-limited":"tag-open"}}">${{s}}</span></td><td class="py-3 px-2 text-xs font-medium">${{r.premium>15?"高溢价卖出":r.premium>8?"底仓套利":r.premium>3&&r.type==="LOF"?"LOF申购":r.premium<0?"折价买入":r.premium>3?"关注":"持有"}}</td>`;tbody.appendChild(tr)}})}}function renderChart(){{const myChart=echarts.init(document.getElementById("chart-premium"));const data=[...fundData].sort((a,b)=>b.premium-a.premium);const option={{{tooltip:{{trigger:"axis",formatter:p=>{{const d=p[0].data;return`<div><b>${{d.name}}</b>(${{d.code}})<br>收盘价:${{d.close}}<br>净值:${{d.latest_nav}}<br><b>溢价:${{d.premium>0?"+":""}}${{d.premium}}%</b></div>`}}}},grid:{{left:"3%",right:"4%",bottom:"15%",top:"10%",containLabel:true}},xAxis:{{type:"category",data:data.map(d=>d.name),axisLabel:{{rotate:45,fontSize:11,color:"#64748b"}}}},yAxis:{{type:"value",name:"溢价率(%)",axisLabel:{{formatter:"{{value}}%",color:"#64748b"}},splitLine:{{lineStyle:{{color:"#f1f5f9"}}}}}},series:[{{type:"bar",data:data.map(d=>({{value:d.premium,itemStyle:{{color:d.premium>15?"#dc2626":d.premium>5?"#ea580c":d.premium<0?"#16a34a":"#3b82f6"}},name:d.name,code:d.code,close:d.close,latest_nav:d.latest_nav}})),barWidth:"60%",label:{{show:true,position:"top",formatter:"{{c}}%",fontSize:11,color:"#64748b"}}}}]}};myChart.setOption(option);window.addEventListener("resize",()=>myChart.resize())}}renderTable();renderChart();</script>
</body></html>'''

def main():
    today=datetime.datetime.now().strftime('%Y-%m-%d')
    print(f"Updating for {today}")
    
    print("Fetching NAVs...")
    nav={}
    for f in FUND_LIST:
        n=get_nav(f['code'])
        if n:
            nav[f['code']]=n
            print(f"  {f['code']}: {n[0]['date']} nav={n[0]['nav']}")
        else:
            print(f"  {f['code']}: failed")
        time.sleep(0.3)
    
    print("Fetching quotes...")
    q=get_quotes([f['code'] for f in FUND_LIST])
    print(f"  Got {len(q)} quotes")
    
    print("Fetching market data...")
    m=get_markets()
    print(f"  Got {len(m)} markets")
    
    print("Calculating...")
    fd=[]
    for f in FUND_LIST:
        c=f['code']
        n=nav.get(c)
        qq=q.get(c)
        if not n or not qq:
            continue
        ln=n[0]['nav']
        close=qq['close']
        pre=qq['pre_close']
        p=(close/ln-1)*100 if ln else 0
        ac=(close/pre-1)*100 if pre else 0
        fd.append({'code':c,'name':f['name'],'track':f['track'],'type':f['type'],'close':round(close,3),'a_chg':round(ac,2),'nav_date':n[0]['date'],'latest_nav':round(ln,4),'est_nav':round(ln,4),'premium':round(p,2)})
    
    fd.sort(key=lambda x:x['premium'],reverse=True)
    
    print("Generating HTML...")
    html=gen_html(m,fd,today)
    with open('index.html','w',encoding='utf-8') as f:
        f.write(html)
    print(f"Done: {len(fd)} funds updated")

if __name__=='__main__':
    main()
