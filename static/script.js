// ========== 全局状态 ==========
let tvWidget = null;

// ========== TradingView K线加载 ==========
function loadTradingView(symbol, interval) {
  // 清理旧 widget
  if (tvWidget) {
    tvWidget.remove();
    tvWidget = null;
  }
  
  // 等待 TradingView 库加载
  const tryInit = () => {
    if (typeof TradingView === 'undefined') {
      setTimeout(tryInit, 300);
      return;
    }
    
    try {
      tvWidget = new TradingView.widget({
        container_id: "tv-chart-container",
        width: "100%",
        height: "100%",
        symbol: symbol,
        interval: interval,
        timezone: "Asia/Shanghai",
        theme: "dark",
        locale: "zh_CN",
        toolbar_bg: "#161616",
        enable_publishing: false,
        allow_symbol_change: true,
        hide_side_toolbar: false,
        studies: ["MASimple@tv-basicstudies", "RSI@tv-basicstudies"]
      });
    } catch (e) {
      console.warn('TradingView 初始化失败:', e);
    }
  };
  
  tryInit();
}

// ========== 左侧一级导航切换 ==========
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => {
    // 更新选中状态
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    item.classList.add('active');
    
    // 切换右侧面板
    const target = item.dataset.target;
    document.querySelectorAll('.submenu').forEach(m => m.classList.remove('active'));
    const panel = document.getElementById(target);
    if (panel) {
      panel.classList.add('active');
    }
  });
});

// ========== 右侧二级菜单点击 → 切换 K线 ==========
document.querySelectorAll('.sub-item').forEach(item => {
  item.addEventListener('click', () => {
    // 更新选中高亮
    document.querySelectorAll('.sub-item').forEach(i => i.classList.remove('active'));
    item.classList.add('active');
    
    // 加载对应 K线
    const sym = item.dataset.symbol;
    const per = item.dataset.period;
    if (sym && per) {
      loadTradingView(sym, per);
    }
  });
});

// ========== 页面加载完成后：默认加载 BTC K线 ==========
document.addEventListener('DOMContentLoaded', () => {
  loadTradingView("BINANCE:BTCUSDT", "15");
});

// ========== Webhook 复制功能 ==========
function copyWebhook() {
  const input = document.querySelector('.webhook-panel input');
  if (input) {
    input.select();
    document.execCommand('copy');
    alert('✅ Webhook 复制成功！\n\n请在 TradingView Alert 中设置此 Webhook URL');
  }
}

// ========== MetaApi 面板 ==========
function openMetaApiPanel() {
  document.getElementById('metaApiModal').style.display = 'block';
}

function closeMetaApiPanel() {
  document.getElementById('metaApiModal').style.display = 'none';
}

function saveMetaApiToken() {
  const token = document.getElementById('metaApiToken').value.trim();
  if (!token) {
    alert('⚠️ 请输入 MetaApi Token');
    return;
  }
  localStorage.setItem('metaApiToken', token);
  alert('✅ MetaApi 绑定成功！\nToken 已保存到本地存储');
  closeMetaApiPanel();
}

// ========== 量化 Bot 面板 ==========
function openBotPanel() {
  document.getElementById('botModal').style.display = 'block';
}

function closeBotPanel() {
  document.getElementById('botModal').style.display = 'none';
}

function startBot() {
  const symbol = document.getElementById('botSymbol').value;
  const amount = document.getElementById('botAmount').value;
  const strategy = document.getElementById('botStrategy').value;
  
  if (!symbol || !amount) {
    alert('⚠️ 请填写交易对和投入金额');
    return;
  }
  
  document.getElementById('botStatus').innerHTML = `
    <span style="color:#0f0">● 运行中</span><br>
    <small style="color:#888">${symbol} | ${amount}U | ${strategy}</small>
  `;
  alert(`✅ Bot 启动成功！\n交易对: ${symbol}\n投入: ${amount}U\n策略: ${strategy}`);
}

function stopBot() {
  document.getElementById('botStatus').innerText = '状态：已停止';
  alert('🛑 Bot 已停止');
}

// ========== 点击 Modal 外部关闭 ==========
window.onclick = function(e) {
  if (e.target.id === 'metaApiModal') closeMetaApiPanel();
  if (e.target.id === 'botModal') closeBotPanel();
};

// ========== 控制台友好信息 ==========
console.log('%c QuantTalk - 量化交易社交平台 ', 'background:#ffd700;color:#000;font-weight:bold;padding:4px 8px;border-radius:4px');
console.log('%c TradingView 图表已加载 ', 'background:#0f0;color:#000;padding:2px 6px');
