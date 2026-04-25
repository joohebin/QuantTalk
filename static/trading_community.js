// ==============================================
// 第三阶段：量化交易社区化功能
// ==============================================

// ===== 路由扩展 =====
const originalRenderPage = renderPage;
renderPage = function() {
    const content = document.getElementById('main-content');
    const title = document.getElementById('main-header-title');
    
    switch(S.page) {
        case 'trading-community':
            title.textContent = '🎯 交易社区';
            renderTradingCommunity();
            return;
        case 'portfolio-updates':
            title.textContent = '📊 持仓动态';
            renderPortfolioUpdates();
            return;
        case 'strategies':
            title.textContent = '📈 策略广场';
            renderStrategies();
            return;
        case 'copy-trade':
            title.textContent = '🔄 一键跟单';
            renderCopyTrade();
            return;
        case 'live-trading':
            title.textContent = '🎥 交易直播';
            renderLiveTrading();
            return;
        case 'price-alerts':
            title.textContent = '🔔 行情提醒';
            renderPriceAlerts();
            return;
    }
    
    // 调用原始路由
    originalRenderPage();
};

// ===== 交易社区主页 =====
function renderTradingCommunity() {
    if (!S.user) { showAuth('login'); return; }
    
    const content = document.getElementById('main-content');
    content.innerHTML = `
    <div style="padding:24px">
        <h2 style="font-size:20px;font-weight:600;color:#fff;margin-bottom:20px">🎯 交易社区</h2>
        
        <!-- 快速入口 -->
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;margin-bottom:24px">
            <div class="quote-card" onclick="nav('portfolio-updates')" style="cursor:pointer">
                <div style="font-size:28px;margin-bottom:8px">📊</div>
                <div style="font-weight:600;color:#fff">持仓动态</div>
                <div style="font-size:12px;color:#939ba2;margin-top:4px">分享你的持仓</div>
            </div>
            <div class="quote-card" onclick="nav('strategies')" style="cursor:pointer">
                <div style="font-size:28px;margin-bottom:8px">📈</div>
                <div style="font-weight:600;color:#fff">策略广场</div>
                <div style="font-size:12px;color:#939ba2;margin-top:4px">学习交易策略</div>
            </div>
            <div class="quote-card" onclick="nav('copy-trade')" style="cursor:pointer">
                <div style="font-size:28px;margin-bottom:8px">🔄</div>
                <div style="font-weight:600;color:#fff">一键跟单</div>
                <div style="font-size:12px;color:#939ba2;margin-top:4px">跟随交易高手</div>
            </div>
            <div class="quote-card" onclick="nav('live-trading')" style="cursor:pointer">
                <div style="font-size:28px;margin-bottom:8px">🎥</div>
                <div style="font:600;color:#fff">交易直播</div>
                <div style="font-size:12px;color:#939ba2;margin-top:4px">实时带单复盘</div>
            </div>
            <div class="quote-card" onclick="nav('price-alerts')" style="cursor:pointer">
                <div style="font-size:28px;margin-bottom:8px">🔔</div>
                <div style="font-weight:600;color:#fff">行情提醒</div>
                <div style="font-size:12px;color:#939ba2;margin-top:4px">异动即时推送</div>
            </div>
        </div>
        
        <!-- 正在直播 -->
        <div style="margin-bottom:24px">
            <h3 style="font-size:16px;font-weight:600;color:#fff;margin-bottom:12px">🎥 正在直播</h3>
            <div id="live-streams-list" style="color:#b9bbbe">加载中...</div>
        </div>
        
        <!-- 最新持仓动态 -->
        <div>
            <h3 style="font-size:16px;font-weight:600;color:#fff;margin-bottom:12px">📊 最新持仓动态</h3>
            <div id="community-updates" style="color:#b9bbbe">加载中...</div>
        </div>
    </div>`;
    
    loadLiveStreams();
    loadCommunityUpdates();
}

// ===== 加载直播列表 =====
async function loadLiveStreams() {
    try {
        const res = await api('/trading-community/live-streams');
        const el = document.getElementById('live-streams-list');
        
        if (res && res.length) {
            el.innerHTML = `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px">
                ${res.map(s => `
                <div class="quote-card" onclick="startLiveView('${s.room_id}')" style="cursor:pointer">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
                        <span style="background:#ed4245;color:#fff;font-size:10px;padding:2px 6px;border-radius:4px">● LIVE</span>
                        <span style="color:#b9bbbe;font-size:12px">${s.viewer_count}人在看</span>
                    </div>
                    <div style="font-weight:600;color:#fff">${esc(s.title)}</div>
                    <div style="font-size:12px;color:#939ba2;margin-top:4px">@${s.host_username}</div>
                    ${s.current_symbol ? `<div style="margin-top:8px;font-size:13px">当前品种: <span class="gain">${s.current_symbol}</span></div>` : ''}
                </div>
                `).join('')}
            </div>`;
        } else {
            el.innerHTML = '<p style="color:#72767d">暂无正在直播</p>';
        }
    } catch(e) {
        document.getElementById('live-streams-list').innerHTML = '<p>加载失败</p>';
    }
}

// ===== 加载社区持仓动态 =====
async function loadCommunityUpdates() {
    try {
        const res = await api('/trading-community/portfolio-updates?visibility=public&limit=10');
        const el = document.getElementById('community-updates');
        
        if (res && res.length) {
            el.innerHTML = res.map(u => `
                <div style="background:#36393f;border-radius:8px;padding:16px;margin-bottom:12px">
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
                        <div class="avatar">${u.username[0].toUpperCase()}</div>
                        <div style="flex:1">
                            <div style="font-weight:600;color:#fff">${u.username}</div>
                            <div style="font-size:11px;color:#72767d">${timeAgo(u.created_at)}</div>
                        </div>
                        <div style="font-size:12px;color:${u.direction === 'long' ? '#23a559' : '#ed4245'}">
                            ${u.direction === 'long' ? '📈 做多' : '📉 做空'}
                        </div>
                    </div>
                    <div style="display:flex;gap:16px;margin-bottom:12px">
                        <div>
                            <div style="font-size:11px;color:#72767d">品种</div>
                            <div style="font-weight:600;color:#fff">${u.symbol}</div>
                        </div>
                        <div>
                            <div style="font-size:11px;color:#72767d">入场价</div>
                            <div style="font-weight:600;color:#fff">${u.entry_price}</div>
                        </div>
                        <div>
                            <div style="font-size:11px;color:#72767d">数量</div>
                            <div style="font-weight:600;color:#fff">${u.quantity}</div>
                        </div>
                        <div>
                            <div style="font-size:11px;color:#72767d">盈亏</div>
                            <div style="font-weight:600;color:${u.pnl >= 0 ? '#23a559' : '#ed4245'}">${u.pnl >= 0 ? '+' : ''}${u.pnl.toFixed(2)} (${u.pnl_pct.toFixed(1)}%)</div>
                        </div>
                    </div>
                    ${u.notes ? `<div style="font-size:13px;color:#b9bbbe;margin-bottom:8px">${esc(u.notes)}</div>` : ''}
                    <div style="display:flex;gap:16px;font-size:12px;color:#72767d">
                        <span onclick="likePortfolioUpdate(${u.id})" style="cursor:pointer">❤️ ${u.likes_count}</span>
                        <span onclick="showUpdateComments(${u.id})" style="cursor:pointer">💬 ${u.comments_count}</span>
                        <span class="tag">${u.visibility === 'public' ? '🌐 公开' : u.visibility === 'friends' ? '👥 好友' : '🔒 私密'}</span>
                    </div>
                </div>
            `).join('');
        } else {
            el.innerHTML = '<p style="color:#72767d">暂无持仓动态</p>';
        }
    } catch(e) {
        document.getElementById('community-updates').innerHTML = '<p>加载失败</p>';
    }
}

// ===== 持仓动态页面 =====
function renderPortfolioUpdates() {
    if (!S.user) { showAuth('login'); return; }
    
    const content = document.getElementById('main-content');
    content.innerHTML = `
    <div style="padding:24px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
            <h2 style="font-size:20px;font-weight:600;color:#fff">📊 持仓动态</h2>
            <button onclick="showCreatePortfolioUpdate()" class="btn btn-primary">发布动态</button>
        </div>
        
        <!-- 筛选 -->
        <div style="display:flex;gap:8px;margin-bottom:20px">
            <select class="exchange-select" id="update-visibility" onchange="loadMyPortfolioUpdates()">
                <option value="all">全部</option>
                <option value="public">🌐 公开</option>
                <option value="friends">👥 好友可见</option>
                <option value="private">🔒 私密</option>
            </select>
        </div>
        
        <div id="portfolio-updates-list">加载中...</div>
    </div>`;
    
    loadMyPortfolioUpdates();
}

async function loadMyPortfolioUpdates() {
    try {
        const visibility = document.getElementById('update-visibility')?.value || 'all';
        const res = await api('/trading-community/portfolio-updates?visibility=' + visibility + '&limit=50');
        const el = document.getElementById('portfolio-updates-list');
        
        if (res && res.length) {
            el.innerHTML = res.map(u => renderPortfolioUpdateCard(u)).join('');
        } else {
            el.innerHTML = '<p style="color:#72767d">暂无持仓动态</p>';
        }
    } catch(e) {
        document.getElementById('portfolio-updates-list').innerHTML = '<p>加载失败</p>';
    }
}

function renderPortfolioUpdateCard(u) {
    return `
    <div style="background:#36393f;border-radius:8px;padding:16px;margin-bottom:12px">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
            <div class="avatar">${u.username[0].toUpperCase()}</div>
            <div style="flex:1">
                <div style="font-weight:600;color:#fff">${u.username}</div>
                <div style="font-size:11px;color:#72767d">${timeAgo(u.created_at)}</div>
            </div>
            <div style="font-size:12px;color:${u.direction === 'long' ? '#23a559' : '#ed4245'}">
                ${u.direction === 'long' ? '📈 做多' : '📉 做空'}
            </div>
        </div>
        <div style="display:flex;gap:16px;margin-bottom:12px">
            <div>
                <div style="font-size:11px;color:#72767d">品种</div>
                <div style="font-weight:600;color:#fff;font-size:16px">${u.symbol}</div>
            </div>
            <div>
                <div style="font-size:11px;color:#72767d">入场价</div>
                <div style="font-weight:600;color:#fff">${u.entry_price}</div>
            </div>
            <div>
                <div style="font-size:11px;color:#72767d">数量</div>
                <div style="font-weight:600;color:#fff">${u.quantity}</div>
            </div>
            <div>
                <div style="font-size:11px;color:#72767d">盈亏</div>
                <div style="font-weight:600;color:${u.pnl >= 0 ? '#23a559' : '#ed4245'};font-size:16px">${u.pnl >= 0 ? '+' : ''}${u.pnl.toFixed(2)}</div>
                <div style="font-size:12px;color:${u.pnl_pct >= 0 ? '#23a559' : '#ed4245'}">${u.pnl_pct >= 0 ? '+' : ''}${u.pnl_pct.toFixed(1)}%</div>
            </div>
        </div>
        ${u.notes ? `<div style="font-size:13px;color:#b9bbbe;margin-bottom:12px;padding:8px;background:#404045;border-radius:4px">${esc(u.notes)}</div>` : ''}
        ${u.tags ? `<div style="margin-bottom:12px">${u.tags.split(',').map(t => `<span class="tag" style="margin-right:4px">${t.trim()}</span>`).join('')}</div>` : ''}
        <div style="display:flex;justify-content:space-between;align-items:center">
            <div style="display:flex;gap:16px;font-size:13px;color:#72767d">
                <span onclick="likePortfolioUpdate(${u.id})" style="cursor:pointer">❤️ ${u.likes_count}</span>
                <span onclick="showUpdateComments(${u.id})" style="cursor:pointer">💬 ${u.comments_count}</span>
            </div>
            <span class="tag">${u.visibility === 'public' ? '🌐 公开' : u.visibility === 'friends' ? '👥 好友' : '🔒 私密'}</span>
        </div>
    </div>`;
}

function showCreatePortfolioUpdate() {
    openModal(`
    <h3>发布持仓动态</h3>
    <form onsubmit="createPortfolioUpdate(event)" style="margin-top:16px">
        <div style="margin-bottom:12px">
            <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">品种</label>
            <input name="symbol" required class="input" placeholder="如 BTCUSDT, EURUSD" style="width:100%">
        </div>
        <div style="display:flex;gap:8px;margin-bottom:12px">
            <div style="flex:1">
                <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">方向</label>
                <select name="direction" class="input" style="width:100%">
                    <option value="long">📈 做多</option>
                    <option value="short">📉 做空</option>
                </select>
            </div>
            <div style="flex:1">
                <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">入场价格</label>
                <input name="entry_price" type="number" step="0.00001" required class="input" placeholder="0.00" style="width:100%">
            </div>
            <div style="flex:1">
                <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">数量</label>
                <input name="quantity" type="number" step="0.0001" required class="input" placeholder="0.00" style="width:100%">
            </div>
        </div>
        <div style="margin-bottom:12px">
            <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">可见性</label>
            <select name="visibility" class="input" style="width:100%">
                <option value="public">🌐 公开 - 所有人可见</option>
                <option value="friends">👥 好友可见</option>
                <option value="private">🔒 私密 - 仅自己可见</option>
            </select>
        </div>
        <div style="margin-bottom:12px">
            <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">备注（可选）</label>
            <textarea name="notes" class="input" rows="2" placeholder="说说你的交易思路..." style="width:100%"></textarea>
        </div>
        <div style="margin-bottom:16px">
            <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">标签（逗号分隔）</label>
            <input name="tags" class="input" placeholder="趋势, 日内交易" style="width:100%">
        </div>
        <button type="submit" class="btn btn-primary w-full">发布</button>
    </form>`);
}

async function createPortfolioUpdate(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = {
        symbol: fd.get('symbol').toUpperCase(),
        direction: fd.get('direction'),
        entry_price: parseFloat(fd.get('entry_price')),
        quantity: parseFloat(fd.get('quantity')),
        visibility: fd.get('visibility'),
        notes: fd.get('notes') || '',
        tags: fd.get('tags') || ''
    };
    
    const res = await api('/trading-community/portfolio-updates', {
        method: 'POST',
        body: JSON.stringify(data)
    });
    
    if (res?.id) {
        closeModal();
        toast('动态发布成功！', 'success');
        loadMyPortfolioUpdates();
    } else {
        toast('发布失败', 'error');
    }
}

async function likePortfolioUpdate(id) {
    const res = await api('/trading-community/portfolio-updates/' + id + '/like', { method: 'POST' });
    if (res?.success) {
        loadMyPortfolioUpdates();
    }
}

function showUpdateComments(id) {
    openModal(`<h3>评论</h3><div id="update-comments-list" style="margin-top:16px;max-height:300px;overflow-y:auto">加载中...</div>
    <form onsubmit="addUpdateComment(event, ${id})" style="margin-top:12px">
        <div style="display:flex;gap:8px">
            <input type="text" id="update-comment-input" class="input" placeholder="写评论..." style="flex:1">
            <button type="submit" class="btn btn-primary">发送</button>
        </div>
    </form>`);
    loadUpdateComments(id);
}

async function loadUpdateComments(id) {
    const res = await api('/trading-community/portfolio-updates/' + id + '/comments');
    const el = document.getElementById('update-comments-list');
    if (res && res.length) {
        el.innerHTML = res.map(c => `
            <div style="padding:8px 0;border-bottom:1px solid #404045">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
                    <div class="avatar avatar-sm">${c.username[0].toUpperCase()}</div>
                    <span style="font-weight:600;color:#fff;font-size:13px">${c.username}</span>
                    <span style="font-size:11px;color:#72767d">${timeAgo(c.created_at)}</span>
                </div>
                <div style="font-size:13px;color:#b9bbbe;margin-left:32px">${esc(c.content)}</div>
            </div>
        `).join('');
    } else {
        el.innerHTML = '<p style="color:#72767d;text-align:center">暂无评论</p>';
    }
}

async function addUpdateComment(e, id) {
    e.preventDefault();
    const input = document.getElementById('update-comment-input');
    const content = input.value.trim();
    if (!content) return;
    
    const res = await api('/trading-community/portfolio-updates/' + id + '/comments?content=' + encodeURIComponent(content), { method: 'POST' });
    if (res?.id) {
        input.value = '';
        loadUpdateComments(id);
    }
}

// ===== 策略广场 =====
function renderStrategies() {
    if (!S.user) { showAuth('login'); return; }
    
    const content = document.getElementById('main-content');
    content.innerHTML = `
    <div style="padding:24px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
            <h2 style="font-size:20px;font-weight:600;color:#fff">📈 策略广场</h2>
            <button onclick="showCreateStrategy()" class="btn btn-primary">发布策略</button>
        </div>
        
        <!-- 筛选 -->
        <div style="display:flex;gap:8px;margin-bottom:20px">
            <select class="exchange-select" id="strategy-type" onchange="loadStrategies()">
                <option value="">全部类型</option>
                <option value="manual">📝 手动交易</option>
                <option value="automated">🤖 自动化策略</option>
                <option value="signal">📡 信号策略</option>
            </select>
            <select class="exchange-select" id="strategy-sort" onchange="loadStrategies()">
                <option value="recent">🕐 最新</option>
                <option value="popular">🔥 最热</option>
            </select>
        </div>
        
        <div id="strategies-list">加载中...</div>
    </div>`;
    
    loadStrategies();
}

async function loadStrategies() {
    try {
        const type = document.getElementById('strategy-type')?.value || '';
        const sort = document.getElementById('strategy-sort')?.value || 'recent';
        let url = '/trading-community/strategies?sort=' + sort;
        if (type) url += '&strategy_type=' + type;
        
        const res = await api(url);
        const el = document.getElementById('strategies-list');
        
        if (res && res.length) {
            el.innerHTML = `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px">
                ${res.map(s => `
                <div class="quote-card" style="cursor:pointer" onclick="showStrategyDetail(${s.id})">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
                        <div class="avatar avatar-sm">${s.username[0].toUpperCase()}</div>
                        <span style="color:#b9bbbe;font-size:13px">@${s.username}</span>
                        <span class="tag" style="margin-left:auto">${s.strategy_type === 'manual' ? '📝 手动' : s.strategy_type === 'automated' ? '🤖 自动' : '📡 信号'}</span>
                    </div>
                    <div style="font-weight:600;color:#fff;font-size:16px;margin-bottom:8px">${esc(s.name)}</div>
                    <div style="font-size:13px;color:#b9bbbe;margin-bottom:12px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">${esc(s.description)}</div>
                    <div style="font-size:12px;color:#72767d;margin-bottom:12px">
                        品种: ${s.symbols || '全部'} | 周期: ${s.timeframe}
                    </div>
                    <div style="display:flex;justify-content:space-between;font-size:12px;color:#72767d">
                        <span>❤️ ${s.likes_count} | 👁️ ${s.views_count}</span>
                        <span>${timeAgo(s.created_at)}</span>
                    </div>
                </div>
                `).join('')}
            </div>`;
        } else {
            el.innerHTML = '<p style="color:#72767d">暂无策略</p>';
        }
    } catch(e) {
        document.getElementById('strategies-list').innerHTML = '<p>加载失败</p>';
    }
}

function showCreateStrategy() {
    openModal(`
    <h3>发布策略</h3>
    <form onsubmit="createStrategy(event)" style="margin-top:16px">
        <div style="margin-bottom:12px">
            <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">策略名称</label>
            <input name="name" required class="input" placeholder="给你的策略起个名字" style="width:100%">
        </div>
        <div style="display:flex;gap:8px;margin-bottom:12px">
            <div style="flex:1">
                <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">类型</label>
                <select name="strategy_type" class="input" style="width:100%">
                    <option value="manual">📝 手动交易</option>
                    <option value="automated">🤖 自动化策略</option>
                    <option value="signal">📡 信号策略</option>
                </select>
            </div>
            <div style="flex:1">
                <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">周期</label>
                <select name="timeframe" class="input" style="width:100%">
                    <option value="1m">1分钟</option>
                    <option value="5m">5分钟</option>
                    <option value="15m">15分钟</option>
                    <option value="1h">1小时</option>
                    <option value="4h">4小时</option>
                    <option value="1d">日线</option>
                </select>
            </div>
        </div>
        <div style="margin-bottom:12px">
            <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">适用品种</label>
            <input name="symbols" class="input" placeholder="如 BTCUSDT, ETHUSDT（留空表示全部）" style="width:100%">
        </div>
        <div style="margin-bottom:12px">
            <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">策略描述</label>
            <textarea name="description" required class="input" rows="3" placeholder="详细描述你的交易策略..." style="width:100%"></textarea>
        </div>
        <div style="margin-bottom:12px">
            <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">入场条件</label>
            <textarea name="entry_conditions" class="input" rows="2" placeholder="什么时候入场？" style="width:100%"></textarea>
        </div>
        <div style="margin-bottom:12px">
            <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">出场条件</label>
            <textarea name="exit_conditions" class="input" rows="2" placeholder="什么时候出场？" style="width:100%"></textarea>
        </div>
        <div style="margin-bottom:12px">
            <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">风险管理</label>
            <textarea name="risk_management" class="input" rows="2" placeholder="止损、仓位管理等..." style="width:100%"></textarea>
        </div>
        <div style="margin-bottom:16px">
            <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">标签（逗号分隔）</label>
            <input name="tags" class="input" placeholder="趋势, 日内, 突破" style="width:100%">
        </div>
        <button type="submit" class="btn btn-primary w-full">发布策略</button>
    </form>`);
}

async function createStrategy(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = {
        name: fd.get('name'),
        description: fd.get('description'),
        strategy_type: fd.get('strategy_type'),
        timeframe: fd.get('timeframe'),
        symbols: fd.get('symbols') || '',
        entry_conditions: fd.get('entry_conditions') || '',
        exit_conditions: fd.get('exit_conditions') || '',
        risk_management: fd.get('risk_management') || '',
        tags: fd.get('tags') || ''
    };
    
    const res = await api('/trading-community/strategies', {
        method: 'POST',
        body: JSON.stringify(data)
    });
    
    if (res?.id) {
        closeModal();
        toast('策略发布成功！', 'success');
        loadStrategies();
    } else {
        toast('发布失败', 'error');
    }
}

async function showStrategyDetail(id) {
    try {
        const res = await api('/trading-community/strategies/' + id);
        if (res) {
            openModal(`
            <div style="max-height:70vh;overflow-y:auto">
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
                    <div class="avatar">${res.username[0].toUpperCase()}</div>
                    <div>
                        <div style="font-weight:600;color:#fff">${esc(res.name)}</div>
                        <div style="font-size:12px;color:#72767d">@${res.username} · ${timeAgo(res.created_at)}</div>
                    </div>
                    <span class="tag" style="margin-left:auto">${res.strategy_type === 'manual' ? '📝 手动' : res.strategy_type === 'automated' ? '🤖 自动' : '📡 信号'}</span>
                </div>
                
                <div style="display:flex;gap:16px;margin-bottom:16px;font-size:13px;color:#939ba2">
                    <span>📊 品种: ${res.symbols || '全部'}</span>
                    <span>⏱️ 周期: ${res.timeframe}</span>
                </div>
                
                <div style="background:#404045;padding:16px;border-radius:8px;margin-bottom:16px">
                    <div style="font-weight:600;color:#fff;margin-bottom:8px">策略描述</div>
                    <div style="color:#b9bbbe">${esc(res.description)}</div>
                </div>
                
                ${res.entry_conditions ? `
                <div style="background:#404045;padding:16px;border-radius:8px;margin-bottom:16px">
                    <div style="font-weight:600;color:#23a559;margin-bottom:8px">✅ 入场条件</div>
                    <div style="color:#b9bbbe">${esc(res.entry_conditions)}</div>
                </div>` : ''}
                
                ${res.exit_conditions ? `
                <div style="background:#404045;padding:16px;border-radius:8px;margin-bottom:16px">
                    <div style="font-weight:600;color:#ed4245;margin-bottom:8px">🚪 出场条件</div>
                    <div style="color:#b9bbbe">${esc(res.exit_conditions)}</div>
                </div>` : ''}
                
                ${res.risk_management ? `
                <div style="background:#404045;padding:16px;border-radius:8px;margin-bottom:16px">
                    <div style="font-weight:600;color:#f9c74f;margin-bottom:8px">⚠️ 风险管理</div>
                    <div style="color:#b9bbbe">${esc(res.risk_management)}</div>
                </div>` : ''}
                
                ${res.backtest_report ? `
                <div style="background:#404045;padding:16px;border-radius:8px;margin-bottom:16px">
                    <div style="font-weight:600;color:#fff;margin-bottom:8px">📊 回测报告</div>
                    <div style="display:flex;gap:16px;font-size:13px">
                        <span>胜率: <span class="gain">${res.backtest_report.win_rate}%</span></span>
                        <span>盈亏比: ${res.backtest_report.profit_factor}</span>
                        <span>最大回撤: <span class="loss">${res.backtest_report.max_drawdown}%</span></span>
                    </div>
                </div>` : ''}
                
                <div style="display:flex;justify-content:space-between;align-items:center;margin-top:16px">
                    <div style="font-size:13px;color:#72767d">❤️ ${res.likes_count} | 👁️ ${res.views_count}</div>
                    <div style="display:flex;gap:8px">
                        <button onclick="likeStrategy(${id})" class="btn ${res.is_liked ? 'btn-primary' : 'btn-ghost'}">❤️ 点赞</button>
                    </div>
                </div>
            </div>`);
        }
    } catch(e) {
        toast('加载失败', 'error');
    }
}

async function likeStrategy(id) {
    const res = await api('/trading-community/strategies/' + id + '/like', { method: 'POST' });
    if (res?.success) {
        loadStrategies();
    }
}

// ===== 一键跟单 =====
function renderCopyTrade() {
    if (!S.user) { showAuth('login'); return; }
    
    const content = document.getElementById('main-content');
    content.innerHTML = `
    <div style="padding:24px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
            <h2 style="font-size:20px;font-weight:600;color:#fff">🔄 一键跟单</h2>
        </div>
        
        <!-- 我跟单的设置 -->
        <div style="margin-bottom:32px">
            <h3 style="font-size:16px;font-weight:600;color:#fff;margin-bottom:12px">📋 我的跟单设置</h3>
            <div id="my-copy-settings">加载中...</div>
        </div>
        
        <!-- 交易高手榜 -->
        <div>
            <h3 style="font-size:16px;font-weight:600;color:#fff;margin-bottom:12px">🏆 交易高手</h3>
            <div style="margin-bottom:12px">
                <input type="text" id="leader-search" class="input" placeholder="搜索品种..." style="width:200px" oninput="searchLeaders()">
            </div>
            <div id="trade-leaders-list">加载中...</div>
        </div>
    </div>`;
    
    loadMyCopySettings();
    loadTradeLeaders();
}

async function loadMyCopySettings() {
    try {
        const res = await api('/trading-community/copy-trade/settings');
        const el = document.getElementById('my-copy-settings');
        
        if (res && res.length) {
            el.innerHTML = `<div style="display:flex;flex-direction:column;gap:12px">
                ${res.map(s => `
                <div class="quote-card" style="display:flex;align-items:center;gap:16px">
                    <div class="avatar">${s.leader_username[0].toUpperCase()}</div>
                    <div style="flex:1">
                        <div style="font-weight:600;color:#fff">@${s.leader_username}</div>
                        <div style="font-size:12px;color:#72767d">品种: ${s.symbols === 'all' ? '全部' : s.symbols}</div>
                    </div>
                    <div style="font-size:13px">
                        <span style="color:${s.is_active ? '#23a559' : '#72767d'}">${s.is_active ? '● 已开启' : '○ 已关闭'}</span>
                    </div>
                    <div style="display:flex;gap:8px">
                        <button onclick="toggleCopyTrade(${s.id})" class="btn ${s.is_active ? 'btn-ghost' : 'btn-primary'}" style="padding:4px 12px;font-size:12px">
                            ${s.is_active ? '暂停' : '开启'}
                        </button>
                        <button onclick="deleteCopyTrade(${s.id})" class="btn btn-danger" style="padding:4px 12px;font-size:12px">删除</button>
                    </div>
                </div>
                `).join('')}
            </div>`;
        } else {
            el.innerHTML = '<p style="color:#72767d">你还没有跟单设置</p>';
        }
    } catch(e) {
        document.getElementById('my-copy-settings').innerHTML = '<p>加载失败</p>';
    }
}

async function loadTradeLeaders() {
    try {
        const symbol = document.getElementById('leader-search')?.value || '';
        let url = '/trading-community/copy-trade/leaders?limit=20';
        if (symbol) url += '&symbol=' + symbol.toUpperCase();
        
        const res = await api(url);
        const el = document.getElementById('trade-leaders-list');
        
        if (res && res.length) {
            el.innerHTML = `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px">
                ${res.map(l => `
                <div class="quote-card">
                    <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
                        <div class="avatar">${l.username[0].toUpperCase()}</div>
                        <div style="flex:1">
                            <div style="font-weight:600;color:#fff">@${l.username}</div>
                            <div style="font-size:12px;color:${l.is_online ? '#23a559' : '#72767d'}">${l.is_online ? '● 在线' : '○ 离线'}</div>
                        </div>
                    </div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px;font-size:13px">
                        <div>
                            <div style="color:#72767d">总信号</div>
                            <div style="font-weight:600;color:#fff">${l.total_signals}</div>
                        </div>
                        <div>
                            <div style="color:#72767d">胜率</div>
                            <div style="font-weight:600;color:${l.win_rate >= 50 ? '#23a559' : '#ed4245'}">${l.win_rate}%</div>
                        </div>
                        <div>
                            <div style="color:#72767d">平均收益</div>
                            <div style="font-weight:600;color:${l.avg_pnl >= 0 ? '#23a559' : '#ed4245'}">${l.avg_pnl >= 0 ? '+' : ''}${l.avg_pnl}%</div>
                        </div>
                        <div>
                            <div style="color:#72767d">跟单人数</div>
                            <div style="font-weight:600;color:#fff">${l.follower_count}</div>
                        </div>
                    </div>
                    ${l.bio ? `<div style="font-size:12px;color:#939ba2;margin-bottom:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(l.bio)}</div>` : ''}
                    <button onclick="showCopyTradeModal(${l.user_id},'${esc(l.username)}')" class="btn btn-primary w-full" style="padding:8px">一键跟单</button>
                </div>
                `).join('')}
            </div>`;
        } else {
            el.innerHTML = '<p style="color:#72767d">暂无交易高手</p>';
        }
    } catch(e) {
        document.getElementById('trade-leaders-list').innerHTML = '<p>加载失败</p>';
    }
}

function searchLeaders() {
    loadTradeLeaders();
}

function showCopyTradeModal(userId, username) {
    openModal(`
    <h3>跟单 @${username}</h3>
    <form onsubmit="createCopyTrade(event, ${userId})" style="margin-top:16px">
        <div style="margin-bottom:12px">
            <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">跟单品种</label>
            <input name="symbols" class="input" placeholder="留空表示全部品种" style="width:100%">
        </div>
        <div style="display:flex;gap:8px;margin-bottom:12px">
            <div style="flex:1">
                <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">最大持仓数</label>
                <input name="max_positions" type="number" value="5" class="input" style="width:100%">
            </div>
            <div style="flex:1">
                <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">止损 (%)</label>
                <input name="stop_loss_pct" type="number" step="0.1" placeholder="可选" class="input" style="width:100%">
            </div>
        </div>
        <div style="margin-bottom:16px">
            <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">止盈 (%)</label>
            <input name="take_profit_pct" type="number" step="0.1" placeholder="可选" class="input" style="width:100%">
        </div>
        <button type="submit" class="btn btn-primary w-full">确认跟单</button>
    </form>`);
}

async function createCopyTrade(e, leaderId) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = {
        leader_id: leaderId,
        symbols: fd.get('symbols') || 'all',
        max_positions: parseInt(fd.get('max_positions')) || 5,
        stop_loss_pct: fd.get('stop_loss_pct') ? parseFloat(fd.get('stop_loss_pct')) : null,
        take_profit_pct: fd.get('take_profit_pct') ? parseFloat(fd.get('take_profit_pct')) : null
    };
    
    const res = await api('/trading-community/copy-trade/settings', {
        method: 'POST',
        body: JSON.stringify(data)
    });
    
    if (res?.success) {
        closeModal();
        toast('跟单成功！', 'success');
        loadMyCopySettings();
    } else {
        toast('跟单失败', 'error');
    }
}

async function toggleCopyTrade(id) {
    const res = await api('/trading-community/copy-trade/settings/' + id + '/toggle', { method: 'POST' });
    if (res?.success) {
        loadMyCopySettings();
    }
}

async function deleteCopyTrade(id) {
    if (!confirm('确定删除此跟单设置？')) return;
    const res = await api('/trading-community/copy-trade/settings/' + id, { method: 'DELETE' });
    if (res?.success) {
        toast('已删除', 'success');
        loadMyCopySettings();
    }
}

// ===== 交易直播 =====
function renderLiveTrading() {
    if (!S.user) { showAuth('login'); return; }
    
    const content = document.getElementById('main-content');
    content.innerHTML = `
    <div style="padding:24px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
            <h2 style="font-size:20px;font-weight:600;color:#fff">🎥 交易直播</h2>
            <button onclick="showStartLiveModal()" class="btn btn-primary">开始直播</button>
        </div>
        
        <!-- 正在直播 -->
        <h3 style="font-size:16px;font-weight:600;color:#fff;margin-bottom:12px">● 正在直播</h3>
        <div id="live-trading-list" style="margin-bottom:32px">加载中...</div>
        
        <!-- 我的直播 -->
        <h3 style="font-size:16px;font-weight:600;color:#fff;margin-bottom:12px">我的直播</h3>
        <div id="my-live-info">加载中...</div>
    </div>`;
    
    loadLiveTradingList();
    checkMyLiveStatus();
}

async function loadLiveTradingList() {
    try {
        const res = await api('/trading-community/live-streams');
        const el = document.getElementById('live-trading-list');
        
        if (res && res.length) {
            el.innerHTML = `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px">
                ${res.map(s => `
                <div class="quote-card" onclick="joinLiveStream('${s.room_id}')" style="cursor:pointer">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
                        <span style="background:#ed4245;color:#fff;font-size:10px;padding:2px 6px;border-radius:4px">● LIVE</span>
                        <span style="font-size:12px;color:#72767d">${s.viewer_count}人在看</span>
                    </div>
                    <div style="font-weight:600;color:#fff;font-size:16px;margin-bottom:8px">${esc(s.title)}</div>
                    <div style="font-size:13px;color:#b9bbbe;margin-bottom:8px">@${s.host_username}</div>
                    ${s.current_symbol ? `
                    <div style="background:#404045;padding:8px;border-radius:4px;margin-bottom:8px">
                        <span style="color:#72767d;font-size:12px">当前品种: </span>
                        <span style="font-weight:600;color:#fff">${s.current_symbol}</span>
                        ${s.is_screen_sharing ? '<span class="tag" style="margin-left:8px">📺 投屏中</span>' : ''}
                    </div>` : ''}
                    <button class="btn btn-primary w-full" style="padding:8px">进入观看</button>
                </div>
                `).join('')}
            </div>`;
        } else {
            el.innerHTML = '<p style="color:#72767d">暂无正在直播</p>';
        }
    } catch(e) {
        document.getElementById('live-trading-list').innerHTML = '<p>加载失败</p>';
    }
}

async function checkMyLiveStatus() {
    try {
        const res = await api('/trading-community/live-streams');
        const myLive = res?.find(s => s.host_id === S.user?.id && s.status === 'live');
        const el = document.getElementById('my-live-info');
        
        if (myLive) {
            el.innerHTML = `
            <div class="quote-card">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
                    <span style="background:#ed4245;color:#fff;font-size:10px;padding:2px 6px;border-radius:4px">● LIVE</span>
                    <span style="font-weight:600;color:#fff">${esc(myLive.title)}</span>
                </div>
                <div style="display:flex;gap:16px;margin-bottom:16px">
                    <div>
                        <div style="color:#72767d;font-size:12px">当前品种</div>
                        <input type="text" id="live-symbol-input" class="input" value="${myLive.current_symbol || ''}" placeholder="如 BTCUSDT" style="width:120px;margin-top:4px">
                    </div>
                    <div style="flex:1"></div>
                    <div>
                        <div style="color:#72767d;font-size:12px">观看人数</div>
                        <div style="font-size:24px;font-weight:700;color:#fff;margin-top:4px">${myLive.viewer_count}</div>
                    </div>
                </div>
                <div style="display:flex;gap:8px">
                    <button onclick="updateLiveSymbol(${myLive.id})" class="btn btn-primary" style="padding:8px 16px">更新品种</button>
                    <button onclick="toggleLiveScreenShare(${myLive.id})" class="btn ${myLive.is_screen_sharing ? 'btn-primary' : 'btn-ghost'}" style="padding:8px 16px">📺 ${myLive.is_screen_sharing ? '停止投屏' : '开始投屏'}</button>
                    <button onclick="endLiveStream(${myLive.id})" class="btn btn-danger" style="padding:8px 16px">结束直播</button>
                </div>
            </div>`;
        } else {
            el.innerHTML = '<p style="color:#72767d">你当前没有进行中的直播</p>';
        }
    } catch(e) {
        document.getElementById('my-live-info').innerHTML = '<p>加载失败</p>';
    }
}

function showStartLiveModal() {
    openModal(`
    <h3>开始交易直播</h3>
    <form onsubmit="startLiveStream(event)" style="margin-top:16px">
        <div style="margin-bottom:12px">
            <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">直播标题</label>
            <input name="title" required class="input" placeholder="如：BTC日内交易实盘" style="width:100%">
        </div>
        <div style="margin-bottom:12px">
            <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">直播类型</label>
            <select name="stream_type" class="input" style="width:100%">
                <option value="trading">📊 交易实盘</option>
                <option value="analysis">📈 行情分析</option>
                <option value="review">🔍 复盘讲解</option>
            </select>
        </div>
        <button type="submit" class="btn btn-primary w-full">开始直播</button>
    </form>`);
}

async function startLiveStream(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const roomId = 'live_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    
    const res = await api('/trading-community/live-streams', {
        method: 'POST',
        body: JSON.stringify({
            room_id: roomId,
            title: fd.get('title'),
            stream_type: fd.get('stream_type')
        })
    });
    
    if (res?.id) {
        closeModal();
        toast('直播已开始！', 'success');
        renderLiveTrading();
    } else {
        toast('开播失败', 'error');
    }
}

async function updateLiveSymbol(streamId) {
    const symbol = document.getElementById('live-symbol-input')?.value;
    if (symbol) {
        await api('/trading-community/live-streams/' + streamId + '/symbol?symbol=' + symbol.toUpperCase(), { method: 'PUT' });
        toast('品种已更新', 'success');
    }
}

async function toggleLiveScreenShare(streamId) {
    const res = await api('/trading-community/live-streams/' + streamId + '/screen-share?is_sharing=true', { method: 'PUT' });
    if (res?.success) {
        toast('屏幕共享已开启', 'success');
        checkMyLiveStatus();
    }
}

async function endLiveStream(streamId) {
    if (!confirm('确定结束直播？')) return;
    const res = await api('/trading-community/live-streams/' + streamId + '/end', { method: 'POST' });
    if (res?.success) {
        toast('直播已结束', 'success');
        renderLiveTrading();
    }
}

function joinLiveStream(roomId) {
    toast('正在加入直播...', 'info');
    // 实际实现中，这里应该跳转到直播观看页面
}

// ===== 行情提醒 =====
function renderPriceAlerts() {
    if (!S.user) { showAuth('login'); return; }
    
    const content = document.getElementById('main-content');
    content.innerHTML = `
    <div style="padding:24px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
            <h2 style="font-size:20px;font-weight:600;color:#fff">🔔 行情提醒</h2>
            <button onclick="showCreateAlertModal()" class="btn btn-primary">添加提醒</button>
        </div>
        
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;margin-bottom:24px">
            <div class="quote-card" style="background:#2d4a6f">
                <div style="font-size:12px;color:#939ba2;margin-bottom:4px">活跃提醒</div>
                <div id="active-alerts-count" style="font-size:32px;font-weight:700;color:#fff">--</div>
            </div>
            <div class="quote-card" style="background:#1d4a2f">
                <div style="font-size:12px;color:#939ba2;margin-bottom:4px">已触发</div>
                <div id="triggered-alerts-count" style="font-size:32px;font-weight:700;color:#23a559">--</div>
            </div>
        </div>
        
        <h3 style="font-size:16px;font-weight:600;color:#fff;margin-bottom:12px">我的提醒</h3>
        <div id="price-alerts-list">加载中...</div>
    </div>`;
    
    loadPriceAlerts();
}

async function loadPriceAlerts() {
    try {
        const res = await api('/trading-community/price-alerts');
        const el = document.getElementById('price-alerts-list');
        const activeCount = document.getElementById('active-alerts-count');
        const triggeredCount = document.getElementById('triggered-alerts-count');
        
        if (res && res.length) {
            const active = res.filter(a => a.is_active && !a.is_triggered).length;
            const triggered = res.filter(a => a.is_triggered).length;
            activeCount.textContent = active;
            triggeredCount.textContent = triggered;
            
            el.innerHTML = `<div style="display:flex;flex-direction:column;gap:12px">
                ${res.map(a => `
                <div class="quote-card" style="display:flex;align-items:center;gap:16px">
                    <div style="flex:1">
                        <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
                            <span style="font-weight:600;color:#fff;font-size:16px">${a.symbol}</span>
                            <span class="tag">${a.condition === 'above' ? '📈 高于' : a.condition === 'below' ? '📉 低于' : '⚡ 波动'}</span>
                            ${a.is_triggered ? '<span style="color:#23a559;font-size:12px">● 已触发</span>' : ''}
                            ${a.notify_friends ? '<span class="tag" style="background:rgba(34,197,94,.12);color:#22c55e;border-color:rgba(34,197,94,.2)">👥 通知好友</span>' : ''}
                        </div>
                        <div style="font-size:13px;color:#b9bbbe">
                            触发条件: <span style="font-weight:600;color:#fff">${a.threshold}</span>
                            ${a.condition === 'change_pct' ? '%' : ''}
                        </div>
                    </div>
                    <button onclick="deletePriceAlert(${a.id})" class="btn btn-danger" style="padding:6px 12px;font-size:12px">删除</button>
                </div>
                `).join('')}
            </div>`;
        } else {
            activeCount.textContent = '0';
            triggeredCount.textContent = '0';
            el.innerHTML = '<p style="color:#72767d">你还没有设置任何提醒</p>';
        }
    } catch(e) {
        document.getElementById('price-alerts-list').innerHTML = '<p>加载失败</p>';
    }
}

function showCreateAlertModal() {
    openModal(`
    <h3>添加行情提醒</h3>
    <form onsubmit="createPriceAlert(event)" style="margin-top:16px">
        <div style="display:flex;gap:8px;margin-bottom:12px">
            <div style="flex:1">
                <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">品种</label>
                <input name="symbol" required class="input" placeholder="如 BTCUSDT" style="width:100%">
            </div>
            <div style="flex:1">
                <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">条件</label>
                <select name="condition" class="input" style="width:100%">
                    <option value="above">📈 高于</option>
                    <option value="below">📉 低于</option>
                    <option value="change_pct">⚡ 波动百分比</option>
                </select>
            </div>
        </div>
        <div style="margin-bottom:12px">
            <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">触发值</label>
            <input name="threshold" type="number" step="0.01" required class="input" placeholder="价格或百分比" style="width:100%">
        </div>
        <div style="margin-bottom:16px">
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
                <input type="checkbox" name="notify_friends"> 
                <span style="font-size:13px;color:#b9bbbe">通知好友（触发时自动推送）</span>
            </label>
        </div>
        <button type="submit" class="btn btn-primary w-full">创建提醒</button>
    </form>`);
}

async function createPriceAlert(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = {
        symbol: fd.get('symbol').toUpperCase(),
        condition: fd.get('condition'),
        threshold: parseFloat(fd.get('threshold')),
        notify_friends: fd.get('notify_friends') === 'on'
    };
    
    const res = await api('/trading-community/price-alerts', {
        method: 'POST',
        body: JSON.stringify(data)
    });
    
    if (res?.id) {
        closeModal();
        toast('提醒已创建！', 'success');
        loadPriceAlerts();
    } else {
        toast('创建失败', 'error');
    }
}

async function deletePriceAlert(id) {
    if (!confirm('确定删除此提醒？')) return;
    const res = await api('/trading-community/price-alerts/' + id, { method: 'DELETE' });
    if (res?.success) {
        toast('已删除', 'success');
        loadPriceAlerts();
    }
}

// ===== 文字频道嵌入K线功能 =====
function showChannelKlineEmbed(channelId) {
    openModal(`
    <h3>📊 嵌入K线</h3>
    <form onsubmit="embedKlineInChannel(event, '${channelId}')" style="margin-top:16px">
        <div style="margin-bottom:12px">
            <label style="font-size:13px;color:#b9bbbe;margin:block">品种</label>
            <input name="symbol" required class="input" placeholder="如 BTCUSDT, EURUSD" style="width:100%">
        </div>
        <div style="margin-bottom:16px">
            <label style="font-size:13px;color:#b9bbbe;margin-bottom:4px;display:block">周期</label>
            <select name="period" class="input" style="width:100%">
                <option value="1m">1分钟</option>
                <option value="5m">5分钟</option>
                <option value="15m">15分钟</option>
                <option value="1h" selected>1小时</option>
                <option value="4h">4小时</option>
                <option value="1d">日线</option>
            </select>
        </div>
        <button type="submit" class="btn btn-primary w-full">嵌入K线</button>
    </form>`);
}

async function embedKlineInChannel(e, channelId) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const symbol = fd.get('symbol').toUpperCase();
    const period = fd.get('period');
    
    // 在频道消息中发送K线嵌入
    const msgContent = `[KLINE_EMBED:${symbol}:${period}]`;
    
    // 这里应该调用发送消息的API
    closeModal();
    toast('K线已嵌入频道！', 'success');
}

// ===== 更新首页导航 =====
function updateHomeNavigation() {
    const channelsList = document.getElementById('channels-list');
    if (channelsList) {
        channelsList.innerHTML = `
        <div class="channel-group">
            <div class="channel-group-header">快速访问</div>
            <div class="channel-item" onclick="nav('trading')"><span class="ch-icon">📊</span>交易大厅</div>
            <div class="channel-item" onclick="nav('market')"><span class="ch-icon">📈</span>行情分析</div>
            <div class="channel-item" onclick="nav('crypto')"><span class="ch-icon">🪙</span>加密货币</div>
            <div class="channel-item" onclick="nav('forex')"><span class="ch-icon">💱</span>外汇贵金属</div>
            <div class="channel-item" onclick="nav('kline')"><span class="ch-icon">📊</span>K线分析</div>
        </div>
        <div class="channel-group">
            <div class="channel-group-header">🎯 交易社区</div>
            <div class="channel-item" onclick="nav('trading-community')"><span class="ch-icon">🎯</span>交易社区</div>
            <div class="channel-item" onclick="nav('portfolio-updates')"><span class="ch-icon">📊</span>持仓动态</div>
            <div class="channel-item" onclick="nav('strategies')"><span class="ch-icon">📈</span>策略广场</div>
            <div class="channel-item" onclick="nav('copy-trade')"><span class="ch-icon">🔄</span>一键跟单</div>
            <div class="channel-item" onclick="nav('live-trading')"><span class="ch-icon">🎥</span>交易直播</div>
        </div>
        <div class="channel-group">
            <div class="channel-group-header">💬 社交</div>
            <div class="channel-item" onclick="nav('friends')"><span class="ch-icon">👥</span>好友</div>
            <div class="channel-item" onclick="nav('messages')"><span class="ch-icon">✉️</span>私信</div>
            <div class="channel-item" onclick="nav('groups')"><span class="ch-icon">👥</span>群聊</div>
            <div class="channel-item" onclick="nav('chat')"><span class="ch-icon">🌐</span>公共聊天室</div>
        </div>
        <div class="channel-group">
            <div class="channel-group-header">🔔 提醒</div>
            <div class="channel-item" onclick="nav('price-alerts')"><span class="ch-icon">🔔</span>行情提醒</div>
        </div>
        <div class="channel-group">
            <div class="channel-group-header">📜 成绩单</div>
            <div class="channel-item" onclick="nav('portfolio')"><span class="ch-icon">📊</span>我的成绩单</div>
        </div>`;
    }
}

// 页面加载完成后更新导航
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(updateHomeNavigation, 500);
});

// 重新定义showHome函数以包含新导航
const originalShowHome = showHome;
showHome = function() {
    originalShowHome();
    updateHomeNavigation();
};
