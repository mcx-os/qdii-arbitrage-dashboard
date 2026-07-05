// QDII 数据代理 - 解决浏览器 CORS 限制
// 部署到 Cloudflare Workers，免费额度每天 10 万次请求

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
};

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS_HEADERS, 'Content-Type': 'application/json; charset=utf-8' },
  });
}

function errorResponse(msg, status = 500) {
  return jsonResponse({ error: msg }, status);
}

// 浏览器 User-Agent，避免被反爬虫拦截
const BROWSER_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS 预检
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS_HEADERS });
    }

    try {
      // === 路由分发 ===
      if (path === '/api/nav') {
        return await handleNav(url);
      }
      if (path === '/api/quote') {
        return await handleQuote(url);
      }
      if (path === '/api/market') {
        return await handleMarket(url);
      }
      if (path === '/api/fx') {
        return await handleFx(url);
      }
      if (path === '/api/dashboard') {
        return await handleDashboard(url);
      }
      if (path === '/api/health') {
        return jsonResponse({ status: 'ok', time: new Date().toISOString() });
      }

      return errorResponse('Not Found', 404);
    } catch (e) {
      console.error('Worker error:', e);
      return errorResponse(e.message || 'Internal Error');
    }
  },
};

// ───────────────────────────────────────────────
// 1. 天天基金净值
// GET /api/nav?fcodes=161130,160644,501225
// ───────────────────────────────────────────────
async function handleNav(url) {
  const fcodes = url.searchParams.get('fcodes');
  if (!fcodes) return errorResponse('Missing fcodes', 400);

  const target = `https://fundmobapi.eastmoney.com/FundMNewApi/FundMNFInfo?plat=Android&appType=ttjj&product=EFund&Version=1&deviceid=&Fcodes=${fcodes}`;
  const res = await fetch(target, {
    headers: {
      'User-Agent': BROWSER_UA,
      'Referer': 'https://fund.eastmoney.com/',
      'Accept': 'application/json',
    },
  });

  if (!res.ok) return errorResponse(`Eastmoney nav API ${res.status}`, 502);
  const data = await res.json();
  return jsonResponse(data);
}

// ───────────────────────────────────────────────
// 2. 东方财富场内价格
// GET /api/quote?codes=501225,159509,513310
// ───────────────────────────────────────────────
async function handleQuote(url) {
  const codes = url.searchParams.get('codes');
  if (!codes) return errorResponse('Missing codes', 400);

  // 构建 secids: 深圳 0.xxx, 上海 1.xxx
  const codeList = codes.split(',').map(c => c.trim());
  const secids = codeList.map(c => {
    const n = parseInt(c, 10);
    // 上海: 500xxx, 501xxx, 503xxx, 505xxx, 510xxx-513xxx, 518xxx, 580xxx
    const shPrefixes = [500,501,502,503,505,510,511,512,513,518,580];
    const prefix = Math.floor(n / 1000);
    const market = shPrefixes.includes(prefix) ? '1' : '0';
    return `${market}.${c}`;
  }).join(',');

  const target = `https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&invt=2&fields=f2,f3,f4,f12,f14,f18&secids=${secids}`;
  const res = await fetch(target, {
    headers: {
      'User-Agent': BROWSER_UA,
      'Referer': 'https://quote.eastmoney.com/',
      'Accept': 'application/json',
    },
  });

  if (!res.ok) return errorResponse(`Eastmoney quote API ${res.status}`, 502);
  const data = await res.json();
  return jsonResponse(data);
}

// ───────────────────────────────────────────────
// 3. 雅虎财经市场指数
// GET /api/market?symbols=^NDX,^GSPC,^DJI
// ───────────────────────────────────────────────
async function handleMarket(url) {
  const symbols = url.searchParams.get('symbols');
  if (!symbols) return errorResponse('Missing symbols', 400);

  const symList = symbols.split(',').map(s => s.trim());
  const results = {};

  await Promise.all(symList.map(async (sym) => {
    try {
      const target = `https://query1.finance.yahoo.com/v8/finance/chart/${sym}?interval=1d&range=5d`;
      const res = await fetch(target, {
        headers: {
          'User-Agent': BROWSER_UA,
          'Accept': 'application/json',
        },
      });
      if (res.ok) {
        results[sym] = await res.json();
      } else {
        results[sym] = { error: `HTTP ${res.status}` };
      }
    } catch (e) {
      results[sym] = { error: e.message };
    }
  }));

  return jsonResponse(results);
}

// ───────────────────────────────────────────────
// 4. 汇率 (USDCNH)
// GET /api/fx
// ───────────────────────────────────────────────
async function handleFx(url) {
  const sources = [
    { name: 'yahoo', url: 'https://query1.finance.yahoo.com/v8/finance/chart/CNY=X?interval=1d&range=5d' },
  ];

  for (const src of sources) {
    try {
      const res = await fetch(src.url, {
        headers: { 'User-Agent': BROWSER_UA, 'Accept': 'application/json' },
      });
      if (res.ok) {
        const data = await res.json();
        return jsonResponse({ source: src.name, data });
      }
    } catch (e) {
      // try next source
    }
  }
  return errorResponse('All fx sources failed', 502);
}

// ───────────────────────────────────────────────
// 5. 聚合看板数据（一键拉取）
// GET /api/dashboard?fcodes=...&codes=...&symbols=...
// ───────────────────────────────────────────────
async function handleDashboard(url) {
  const fcodes = url.searchParams.get('fcodes') || '';
  const codes = url.searchParams.get('codes') || '';
  const symbols = url.searchParams.get('symbols') || '^NDX,^GSPC,^DJI,^GDAXI,CL=F';

  const [navData, quoteData, marketData, fxData] = await Promise.allSettled([
    fcodes ? fetchNav(fcodes) : Promise.resolve(null),
    codes ? fetchQuote(codes) : Promise.resolve(null),
    fetchMarket(symbols),
    fetchFx(),
  ]);

  return jsonResponse({
    nav: navData.status === 'fulfilled' ? navData.value : { error: navData.reason?.message },
    quote: quoteData.status === 'fulfilled' ? quoteData.value : { error: quoteData.reason?.message },
    market: marketData.status === 'fulfilled' ? marketData.value : { error: marketData.reason?.message },
    fx: fxData.status === 'fulfilled' ? fxData.value : { error: fxData.reason?.message },
    server_time: new Date().toISOString(),
  });
}

// ── 内部辅助函数 ──
async function fetchNav(fcodes) {
  const target = `https://fundmobapi.eastmoney.com/FundMNewApi/FundMNFInfo?plat=Android&appType=ttjj&product=EFund&Version=1&deviceid=&Fcodes=${fcodes}`;
  const res = await fetch(target, {
    headers: { 'User-Agent': BROWSER_UA, 'Referer': 'https://fund.eastmoney.com/', 'Accept': 'application/json' },
  });
  if (!res.ok) throw new Error(`nav ${res.status}`);
  return await res.json();
}

async function fetchQuote(codes) {
  const codeList = codes.split(',').map(c => c.trim());
  const secids = codeList.map(c => {
    const n = parseInt(c, 10);
    const shPrefixes = [500,501,502,503,505,510,511,512,513,518,580];
    const prefix = Math.floor(n / 1000);
    return `${shPrefixes.includes(prefix) ? '1' : '0'}.${c}`;
  }).join(',');

  const target = `https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&invt=2&fields=f2,f3,f4,f12,f14,f18&secids=${secids}`;
  const res = await fetch(target, {
    headers: { 'User-Agent': BROWSER_UA, 'Referer': 'https://quote.eastmoney.com/', 'Accept': 'application/json' },
  });
  if (!res.ok) throw new Error(`quote ${res.status}`);
  return await res.json();
}

async function fetchMarket(symbols) {
  const symList = symbols.split(',').map(s => s.trim());
  const results = {};
  await Promise.all(symList.map(async (sym) => {
    try {
      const res = await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${sym}?interval=1d&range=5d`, {
        headers: { 'User-Agent': BROWSER_UA, 'Accept': 'application/json' },
      });
      results[sym] = res.ok ? await res.json() : { error: `HTTP ${res.status}` };
    } catch (e) {
      results[sym] = { error: e.message };
    }
  }));
  return results;
}

async function fetchFx() {
  const res = await fetch('https://query1.finance.yahoo.com/v8/finance/chart/CNY=X?interval=1d&range=5d', {
    headers: { 'User-Agent': BROWSER_UA, 'Accept': 'application/json' },
  });
  if (!res.ok) throw new Error(`fx ${res.status}`);
  return await res.json();
}
