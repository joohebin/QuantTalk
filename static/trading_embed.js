/**
 * QuantTalk v5.0 - 交易内容嵌入与体验升级
 * 排行榜系统 / 成绩单 / 内容嵌入
 */

// ==================== 排行榜模块 ====================

/**
 * 加载交易高手排行榜
 */
async function loadTraderLeaderboard(period = 'daily', category = 'all') {
    try {
        const response = await fetch(`/api/trading-embed/leaderboards/traders?period=${period}&category=${category}`);
        const data = await response.json();
        return data.rankings || [];
    } catch (error) {
        console.error('加载交易高手排行榜失败:', error);
        return [];
    }
}

/**
 * 加载策略收益排行榜
 */
async function loadStrategyLeaderboard(period = 'daily', symbol = null) {
    try {
        const url = `/api/trading-embed/leaderboards/strategies?period=${period}${symbol ? `&symbol=${symbol}` : ''}`;
        const response = await fetch(url);
        const data = await response.json();
        return data.rankings || [];
    } catch (error) {
        console.error('加载策略收益排行榜失败:', error);
        return [];
    }
}

/**
 * 加载社区活跃度排行榜
 */
async function loadActivityLeaderboard(period = 'daily') {
    try {
        const response = await fetch(`/api/trading-embed/leaderboards/activity?period=${period}`);
        const data = await response.json();
        return data.rankings || [];
    } catch (error) {
        console.error('加载活跃度排行榜失败:', error);
        return [];
    }
}

/**
 * 渲染交易高手排行榜
 */
function renderTraderLeaderboard(rankings, containerId = 'trader-leaderboard') {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!rankings || rankings.length === 0) {
        container.innerHTML = '<div class="text-center text-gray-400 py-8">暂无数据</div>';
        return;
    }

    const html = rankings.map((r, i) => `
        <div class="flex items-center gap-3 p-3 rounded-lg hover:bg-white/5 transition-colors cursor-pointer"
             onclick="showLeaderPositions(${r.user_id}, '${r.username}')">
            <div class="w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm
                        ${i === 0 ? 'bg-yellow-500 text-black' : i === 1 ? 'bg-gray-400 text-black' : i === 2 ? 'bg-amber-600 text-white' : 'bg-gray-600 text-white'}">
                ${r.ranking}
            </div>
            <div class="avatar avatar-sm">${r.avatar ? r.avatar[0]?.toUpperCase() : r.username[0]?.toUpperCase() || '?'}</div>
            <div class="flex-1 min-w-0">
                <div class="font-medium text-white truncate">${escapeHtml(r.username)}</div>
                <div class="text-xs text-gray-400">
                    ${r.trade_count}笔交易 · 胜率${r.win_rate?.toFixed(1)}%
                </div>
            </div>
            <div class="text-right">
                <div class="font-bold ${r.change_pct >= 0 ? 'gain' : 'loss'}">
                    ${r.change_pct >= 0 ? '+' : ''}${r.change_pct?.toFixed(2)}%
                </div>
                <div class="text-xs text-gray-400">
                    ${r.is_online ? '<span class="text-green-400">在线</span>' : '<span class="text-gray-500">离线</span>'}
                </div>
            </div>
        </div>
    `).join('');

    container.innerHTML = html;
}

/**
 * 渲染策略排行榜
 */
function renderStrategyLeaderboard(rankings, containerId = 'strategy-leaderboard') {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!rankings || rankings.length === 0) {
        container.innerHTML = '<div class="text-center text-gray-400 py-8">暂无数据</div>';
        return;
    }

    const html = rankings.map((r, i) => `
        <div class="flex items-center gap-3 p-3 rounded-lg hover:bg-white/5 transition-colors cursor-pointer"
             onclick="viewStrategyDetail(${r.strategy_id})">
            <div class="w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm
                        ${i === 0 ? 'bg-yellow-500 text-black' : i === 1 ? 'bg-gray-400 text-black' : i === 2 ? 'bg-amber-600 text-white' : 'bg-gray-600 text-white'}">
                ${r.ranking}
            </div>
            <div class="flex-1 min-w-0">
                <div class="font-medium text-white truncate">${escapeHtml(r.strategy_name)}</div>
                <div class="text-xs text-gray-400">
                    by ${escapeHtml(r.username)} · ${r.views_count}浏览 · ${r.likes_count}赞
                </div>
            </div>
            <div class="text-right">
                <div class="font-bold ${r.total_return_pct >= 0 ? 'gain' : 'loss'}">
                    ${r.total_return_pct >= 0 ? '+' : ''}${r.total_return_pct?.toFixed(2)}%
                </div>
                <div class="text-xs text-gray-400">胜率${r.win_rate?.toFixed(1)}%</div>
            </div>
        </div>
    `).join('');

    container.innerHTML = html;
}

/**
 * 渲染活跃度排行榜
 */
function renderActivityLeaderboard(rankings, containerId = 'activity-leaderboard') {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!rankings || rankings.length === 0) {
        container.innerHTML = '<div class="text-center text-gray-400 py-8">暂无数据</div>';
        return;
    }

    const html = rankings.map((r, i) => `
        <div class="flex items-center gap-3 p-3 rounded-lg hover:bg-white/5 transition-colors">
            <div class="w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm
                        ${i === 0 ? 'bg-yellow-500 text-black' : i === 1 ? 'bg-gray-400 text-black' : i === 2 ? 'bg-amber-600 text-white' : 'bg-gray-600 text-white'}">
                ${r.ranking}
            </div>
            <div class="avatar avatar-sm">${r.avatar ? r.avatar[0]?.toUpperCase() : r.username[0]?.toUpperCase() || '?'}</div>
            <div class="flex-1 min-w-0">
                <div class="font-medium text-white truncate">${escapeHtml(r.username)}</div>
                <div class="text-xs text-gray-400">
                    ${r.signals_count}信号 · ${r.strategies_count}策略
                </div>
            </div>
            <div class="text-right">
                <div class="font-bold text-blue-400">${r.activity_score}</div>
                <div class="text-xs text-gray-400">活跃分</div>
            </div>
        </div>
    `).join('');

    container.innerHTML = html;
}

/**
 * 显示排行榜页面
 */
async function showLeaderboard(type = 'traders') {
    const period = document.getElementById('leaderboard-period')?.value || 'daily';

    let title, rankings;
    switch (type) {
        case 'strategies':
            title = '策略收益榜';
            rankings = await loadStrategyLeaderboard(period);
            break;
        case 'activity':
            title = '社区活跃榜';
            rankings = await loadActivityLeaderboard(period);
            break;
        default:
            title = '交易高手榜';
            rankings = await loadTraderLeaderboard(period);
    }

    const content = `
        <div class="p-4">
            <h3 class="text-xl font-bold text-white mb-4">${title}</h3>

            <div class="flex gap-2 mb-4">
                <select id="leaderboard-period" class="exchange-select" onchange="showLeaderboard('${type}')">
                    <option value="daily" ${period === 'daily' ? 'selected' : ''}>今日</option>
                    <option value="weekly" ${period === 'weekly' ? 'selected' : ''}>本周</option>
                    <option value="monthly" ${period === 'monthly' ? 'selected' : ''}>本月</option>
                </select>
                <button class="btn btn-ghost" onclick="showLeaderboard('traders')">交易高手</button>
                <button class="btn btn-ghost" onclick="showLeaderboard('strategies')">策略收益</button>
                <button class="btn btn-ghost" onclick="showLeaderboard('activity')">活跃度</button>
            </div>

            <div id="${type}-leaderboard" class="space-y-1">
                <div class="text-center text-gray-400 py-8">加载中...</div>
            </div>
        </div>
    `;

    document.getElementById('main-content').innerHTML = content;

    // 渲染对应类型的排行榜
    switch (type) {
        case 'strategies':
            renderStrategyLeaderboard(rankings, `${type}-leaderboard`);
            break;
        case 'activity':
            renderActivityLeaderboard(rankings, `${type}-leaderboard`);
            break;
        default:
            renderTraderLeaderboard(rankings, `${type}-leaderboard`);
    }
}

/**
 * 显示高手持仓详情
 */
async function showLeaderPositions(userId, username) {
    try {
        const response = await fetch(`/api/trading-embed/leaderboards/traders/${userId}/positions`);
        const data = await response.json();

        const positionsHtml = data.positions?.length > 0
            ? data.positions.map(p => `
                <div class="flex items-center justify-between p-2 rounded bg-white/5">
                    <div>
                        <span class="font-bold text-white">${p.symbol}</span>
                        <span class="ml-2 text-xs ${p.direction === 'long' ? 'text-green-400' : 'text-red-400'}">
                            ${p.direction === 'long' ? '多' : '空'}
                        </span>
                    </div>
                    <div class="text-right">
                        <div class="text-sm ${p.pnl >= 0 ? 'gain' : 'loss'}">
                            ${p.pnl >= 0 ? '+' : ''}$${p.pnl?.toFixed(2)}
                        </div>
                        <div class="text-xs text-gray-400">${p.pnl_pct >= 0 ? '+' : ''}${p.pnl_pct?.toFixed(2)}%</div>
                    </div>
                </div>
            `).join('')
            : '<div class="text-center text-gray-400 py-4">暂无持仓</div>';

        showModal(`
            <h3 class="text-lg font-bold text-white mb-2">${escapeHtml(username)} 的持仓</h3>
            <div class="space-y-2 max-h-64 overflow-y-auto">
                ${positionsHtml}
            </div>
            <div class="mt-4 flex gap-2">
                <button class="btn btn-primary flex-1" onclick="copyTrade(${userId})">一键跟单</button>
                <button class="btn btn-ghost" onclick="closeModal()">关闭</button>
            </div>
        `);
    } catch (error) {
        console.error('获取持仓失败:', error);
        showToast('获取持仓失败', 'error');
    }
}

/**
 * 一键跟单
 */
async function copyTrade(leaderId) {
    try {
        const response = await fetch('/api/trading-embed/copy-trade/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                leader_id: leaderId,
                symbols: 'all',
                max_positions: 5
            })
        });
        const data = await response.json();

        if (data.success) {
            showToast('跟单成功', 'success');
            closeModal();
        } else {
            showToast(data.message || '跟单失败', 'error');
        }
    } catch (error) {
        console.error('跟单失败:', error);
        showToast('跟单失败', 'error');
    }
}


// ==================== 成绩单模块 ====================

/**
 * 加载成绩单列表
 */
async function loadReportCards(sort = 'recent') {
    try {
        const response = await fetch(`/api/trading-embed/report-cards?sort=${sort}`);
        return await response.json();
    } catch (error) {
        console.error('加载成绩单失败:', error);
        return [];
    }
}

/**
 * 显示成绩单列表
 */
async function showReportCards() {
    const sort = document.getElementById('reportcard-sort')?.value || 'recent';
    const cards = await loadReportCards(sort);

    const content = `
        <div class="p-4">
            <div class="flex items-center justify-between mb-4">
                <h3 class="text-xl font-bold text-white">交易成绩单</h3>
                <button class="btn btn-primary" onclick="showCreateReportCard()">
                    + 生成成绩单
                </button>
            </div>

            <div class="flex gap-2 mb-4">
                <select id="reportcard-sort" class="exchange-select" onchange="showReportCards()">
                    <option value="recent" ${sort === 'recent' ? 'selected' : ''}>最新</option>
                    <option value="popular" ${sort === 'popular' ? 'selected' : ''}>最热</option>
                    <option value="win_rate" ${sort === 'win_rate' ? 'selected' : ''}>胜率最高</option>
                </select>
            </div>

            <div id="reportcard-list" class="space-y-3">
                <div class="text-center text-gray-400 py-8">加载中...</div>
            </div>
        </div>
    `;

    document.getElementById('main-content').innerHTML = content;
    renderReportCardList(cards);
}

/**
 * 渲染成绩单列表
 */
function renderReportCardList(cards) {
    const container = document.getElementById('reportcard-list');
    if (!container) return;

    if (!cards || cards.length === 0) {
        container.innerHTML = '<div class="text-center text-gray-400 py-8">暂无成绩单</div>';
        return;
    }

    const html = cards.map(card => `
        <div class="glass2 rounded-lg p-4 cursor-pointer hover:border-indigo-500/50 transition-colors"
             onclick="showReportCardDetail(${card.id})">
            <div class="flex items-start gap-3">
                <div class="avatar">${card.avatar ? card.avatar[0]?.toUpperCase() : card.username[0]?.toUpperCase()}</div>
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2">
                        <span class="font-bold text-white">${escapeHtml(card.username)}</span>
                        <span class="text-sm text-gray-400">的${escapeHtml(card.name)}</span>
                    </div>
                    <div class="flex items-center gap-4 mt-2 text-sm">
                        <span class="text-gray-400">${card.total_trades}笔交易</span>
                        <span class="${card.win_rate >= 50 ? 'gain' : 'loss'}">胜率${card.win_rate?.toFixed(1)}%</span>
                        <span class="${card.total_pnl >= 0 ? 'gain' : 'loss'}">
                            ${card.total_pnl >= 0 ? '+' : ''}${card.total_pnl_pct?.toFixed(2)}%
                        </span>
                    </div>
                    <div class="flex items-center gap-4 mt-1 text-xs text-gray-500">
                        <span>最大回撤 ${card.max_drawdown_pct?.toFixed(1)}%</span>
                        <span>盈亏比 ${card.profit_factor?.toFixed(2)}</span>
                    </div>
                </div>
                <div class="text-right">
                    <div class="flex items-center gap-2">
                        <span class="text-gray-400">${card.likes_count}</span>
                        <span>❤️</span>
                    </div>
                    <div class="flex items-center gap-2 mt-1">
                        <span class="text-gray-400">${card.views_count}</span>
                        <span>👁️</span>
                    </div>
                </div>
            </div>
        </div>
    `).join('');

    container.innerHTML = html;
}

/**
 * 显示成绩单详情
 */
async function showReportCardDetail(cardId) {
    try {
        const response = await fetch(`/api/trading-embed/report-cards/${cardId}`);
        const card = await response.json();

        showModal(`
            <div class="p-2">
                <h3 class="text-lg font-bold text-white mb-4">${escapeHtml(card.name)}</h3>

                <!-- 核心指标 -->
                <div class="grid grid-cols-3 gap-3 mb-4">
                    <div class="bg-white/5 rounded-lg p-3 text-center">
                        <div class="text-2xl font-bold ${card.win_rate >= 50 ? 'gain' : 'loss'}">${card.win_rate?.toFixed(1)}%</div>
                        <div class="text-xs text-gray-400">胜率</div>
                    </div>
                    <div class="bg-white/5 rounded-lg p-3 text-center">
                        <div class="text-2xl font-bold ${card.total_pnl >= 0 ? 'gain' : 'loss'}">${card.total_pnl_pct >= 0 ? '+' : ''}${card.total_pnl_pct?.toFixed(1)}%</div>
                        <div class="text-xs text-gray-400">总收益</div>
                    </div>
                    <div class="bg-white/5 rounded-lg p-3 text-center">
                        <div class="text-2xl font-bold loss">${card.max_drawdown_pct?.toFixed(1)}%</div>
                        <div class="text-xs text-gray-400">最大回撤</div>
                    </div>
                </div>

                <!-- 详细数据 -->
                <div class="space-y-2 text-sm">
                    <div class="flex justify-between"><span class="text-gray-400">总交易次数</span><span>${card.total_trades}</span></div>
                    <div class="flex justify-between"><span class="text-gray-400">盈利次数</span><span class="gain">${card.win_trades}</span></div>
                    <div class="flex justify-between"><span class="text-gray-400">亏损次数</span><span class="loss">${card.loss_trades}</span></div>
                    <div class="flex justify-between"><span class="text-gray-400">平均盈利</span><span class="gain">$${card.avg_win?.toFixed(2)}</span></div>
                    <div class="flex justify-between"><span class="text-gray-400">平均亏损</span><span class="loss">$${card.avg_loss?.toFixed(2)}</span></div>
                    <div class="flex justify-between"><span class="text-gray-400">盈亏比</span><span>${card.profit_factor?.toFixed(2)}</span></div>
                    <div class="flex justify-between"><span class="text-gray-400">夏普比率</span><span>${card.sharpe_ratio?.toFixed(2)}</span></div>
                    <div class="flex justify-between"><span class="text-gray-400">最大单笔盈利</span><span class="gain">$${card.best_trade?.toFixed(2)}</span></div>
                    <div class="flex justify-between"><span class="text-gray-400">最大单笔亏损</span><span class="loss">$${card.worst_trade?.toFixed(2)}</span></div>
                    <div class="flex justify-between"><span class="text-gray-400">最大连胜</span><span>${card.consecutive_wins}</span></div>
                    <div class="flex justify-between"><span class="text-gray-400">最大连亏</span><span>${card.consecutive_losses}</span></div>
                </div>

                <!-- 操作按钮 -->
                <div class="flex gap-2 mt-4">
                    <button class="btn btn-primary flex-1" onclick="likeReportCard(${card.id})">
                        ${card.is_liked ? '取消点赞' : '点赞'} (${card.likes_count})
                    </button>
                    <button class="btn btn-ghost" onclick="shareReportCard(${card.id})">分享</button>
                    <button class="btn btn-ghost" onclick="closeModal()">关闭</button>
                </div>
            </div>
        `, 'max-width:500px');
    } catch (error) {
        console.error('加载成绩单详情失败:', error);
        showToast('加载失败', 'error');
    }
}

/**
 * 创建成绩单表单
 */
function showCreateReportCard() {
    showModal(`
        <h3 class="text-lg font-bold text-white mb-4">生成交易成绩单</h3>
        <form id="reportcard-form" class="space-y-4">
            <div>
                <label class="block text-sm text-gray-400 mb-1">成绩单名称</label>
                <input type="text" name="name" class="input" placeholder="例如：2024年第一季度交易报告" required>
            </div>
            <div class="grid grid-cols-2 gap-3">
                <div>
                    <label class="block text-sm text-gray-400 mb-1">开始日期</label>
                    <input type="date" name="period_start" class="input">
                </div>
                <div>
                    <label class="block text-sm text-gray-400 mb-1">结束日期</label>
                    <input type="date" name="period_end" class="input">
                </div>
            </div>
            <div class="grid grid-cols-2 gap-3">
                <div>
                    <label class="block text-sm text-gray-400 mb-1">交易所</label>
                    <select name="exchange" class="input">
                        <option value="">全部</option>
                        <option value="Binance">Binance</option>
                        <option value="OKX">OKX</option>
                        <option value="Bybit">Bybit</option>
                        <option value="MT5">MT5</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm text-gray-400 mb-1">交易品种</label>
                    <input type="text" name="symbol" class="input" placeholder="例如：BTC">
                </div>
            </div>
            <div class="grid grid-cols-3 gap-3">
                <div>
                    <label class="block text-sm text-gray-400 mb-1">总交易次数</label>
                    <input type="number" name="total_trades" class="input" value="50" min="0">
                </div>
                <div>
                    <label class="block text-sm text-gray-400 mb-1">盈利次数</label>
                    <input type="number" name="win_trades" class="input" value="30" min="0">
                </div>
                <div>
                    <label class="block text-sm text-gray-400 mb-1">亏损次数</label>
                    <input type="number" name="loss_trades" class="input" value="20" min="0">
                </div>
            </div>
            <div class="grid grid-cols-2 gap-3">
                <div>
                    <label class="block text-sm text-gray-400 mb-1">总收益(%)</label>
                    <input type="number" name="total_pnl_pct" class="input" value="15.5" step="0.1">
                </div>
                <div>
                    <label class="block text-sm text-gray-400 mb-1">最大回撤(%)</label>
                    <input type="number" name="max_drawdown_pct" class="input" value="8.5" step="0.1">
                </div>
            </div>
            <div class="flex gap-2 mt-4">
                <button type="submit" class="btn btn-primary flex-1">生成成绩单</button>
                <button type="button" class="btn btn-ghost" onclick="closeModal()">取消</button>
            </div>
        </form>
    `);

    document.getElementById('reportcard-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);

        try {
            const response = await fetch('/api/trading-embed/report-cards', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: formData.get('name'),
                    period_start: formData.get('period_start'),
                    period_end: formData.get('period_end'),
                    exchange: formData.get('exchange'),
                    symbol: formData.get('symbol'),
                    total_trades: parseInt(formData.get('total_trades')),
                    win_trades: parseInt(formData.get('win_trades')),
                    loss_trades: parseInt(formData.get('loss_trades')),
                    total_pnl: 0,
                    total_pnl_pct: parseFloat(formData.get('total_pnl_pct')),
                    avg_win: 150,
                    avg_loss: 80,
                    max_drawdown: 850,
                    max_drawdown_pct: parseFloat(formData.get('max_drawdown_pct')),
                    sharpe_ratio: 1.5,
                    best_trade: 500,
                    worst_trade: -200,
                    consecutive_wins: 5,
                    consecutive_losses: 3
                })
            });

            const card = await response.json();
            showToast('成绩单生成成功', 'success');
            closeModal();
            showReportCardDetail(card.id);
        } catch (error) {
            console.error('生成成绩单失败:', error);
            showToast('生成失败', 'error');
        }
    });
}

/**
 * 点赞成绩单
 */
async function likeReportCard(cardId) {
    try {
        const response = await fetch(`/api/trading-embed/report-cards/${cardId}/like`, { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            showToast(data.action === 'liked' ? '已点赞' : '已取消点赞', 'success');
            closeModal();
            showReportCardDetail(cardId);
        }
    } catch (error) {
        console.error('点赞失败:', error);
    }
}

/**
 * 分享成绩单
 */
async function shareReportCard(cardId) {
    try {
        await fetch(`/api/trading-embed/report-cards/${cardId}/share`, { method: 'POST' });
        showToast('成绩单链接已复制', 'success');
    } catch (error) {
        console.error('分享失败:', error);
    }
}


// ==================== 内容嵌入模块 ====================

/**
 * 在消息中嵌入K线
 */
function embedKlineInMessage(symbol, period = '1h') {
    const input = document.getElementById('message-input');
    if (!input) return;

    const embedCode = `[KLINE:${symbol}:${period}]`;
    input.value += embedCode;
    input.focus();
    showToast(`已添加K线嵌入: ${symbol} ${period}`, 'success');
}

/**
 * 在消息中嵌入行情
 */
function embedQuoteInMessage(symbol) {
    const input = document.getElementById('message-input');
    if (!input) return;

    const embedCode = `[QUOTE:${symbol}]`;
    input.value += embedCode;
    input.focus();
    showToast(`已添加行情嵌入: ${symbol}`, 'success');
}

/**
 * 在消息中嵌入策略
 */
function embedStrategyInMessage(strategyId) {
    const input = document.getElementById('message-input');
    if (!input) return;

    const embedCode = `[STRATEGY:${strategyId}]`;
    input.value += embedCode;
    input.focus();
    showToast('已添加策略嵌入', 'success');
}

/**
 * 解析消息中的嵌入代码
 */
function parseEmbedCodes(message) {
    const embedPattern = /\[(KLINE|QUOTE|STRATEGY|REPORT|SIGNAL):([^\]]+)\]/g;
    const embeds = [];
    let match;

    while ((match = embedPattern.exec(message)) !== null) {
        const [fullMatch, type, params] = match;
        const [primary, secondary] = params.split(':');

        embeds.push({
            type,
            symbol: primary,
            period: secondary || '1h',
            fullMatch
        });
    }

    return embeds;
}


// ==================== 行情分析模块 ====================

/**
 * 加载行情异动
 */
async function loadPriceMovements(category = 'all') {
    try {
        const response = await fetch(`/api/trading-embed/price-movements?category=${category}`);
        return await response.json();
    } catch (error) {
        console.error('加载行情异动失败:', error);
        return [];
    }
}

/**
 * 显示行情分析页面
 */
async function showMarketAnalysis() {
    const movements = await loadPriceMovements();
    const cryptoMovements = movements.filter(m => m.category === 'crypto').slice(0, 10);
    const forexMovements = movements.filter(m => m.category === 'forex').slice(0, 5);

    const content = `
        <div class="p-4">
            <h3 class="text-xl font-bold text-white mb-4">行情异动监控</h3>

            <div class="grid grid-cols-2 gap-4 mb-6">
                <div class="glass2 rounded-lg p-4">
                    <h4 class="font-bold text-white mb-2">🔥 涨幅榜</h4>
                    <div class="space-y-1" id="gainers-list">
                        ${renderGainersLossers(cryptoMovements.filter(m => m.change_pct > 0).sort((a, b) => b.change_pct - a.change_pct).slice(0, 5), 'rise')}
                    </div>
                </div>
                <div class="glass2 rounded-lg p-4">
                    <h4 class="font-bold text-white mb-2">💹 跌幅榜</h4>
                    <div class="space-y-1" id="losers-list">
                        ${renderGainersLossers(cryptoMovements.filter(m => m.change_pct < 0).sort((a, b) => a.change_pct - b.change_pct).slice(0, 5), 'fall')}
                    </div>
                </div>
            </div>

            <h4 class="font-bold text-white mb-3">实时异动监控</h4>
            <div class="space-y-2" id="movements-list">
                ${movements.slice(0, 15).map(m => `
                    <div class="flex items-center justify-between p-2 rounded bg-white/5 hover:bg-white/10 transition-colors">
                        <div class="flex items-center gap-3">
                            <span class="font-bold text-white">${m.symbol}</span>
                            <span class="text-xs text-gray-400">${m.exchange}</span>
                        </div>
                        <div class="flex items-center gap-4">
                            <span class="text-sm ${m.change_type === 'rise' ? 'gain' : 'loss'}">
                                ${m.change_pct >= 0 ? '+' : ''}${m.change_pct?.toFixed(2)}%
                            </span>
                            <span class="text-xs text-gray-400">量比 ${m.volume_ratio?.toFixed(1)}x</span>
                            <button class="btn btn-ghost text-xs py-1 px-2" onclick="embedQuoteInMessage('${m.symbol}')">
                                嵌入
                            </button>
                        </div>
                    </div>
                `).join('')}
            </div>

            <div class="mt-4 text-center">
                <button class="btn btn-ghost" onclick="refreshPriceMovements()">🔄 刷新</button>
            </div>
        </div>
    `;

    document.getElementById('main-content').innerHTML = content;
}

function renderGainersLossers(items, type) {
    if (!items || items.length === 0) {
        return '<div class="text-gray-400 text-sm">暂无数据</div>';
    }

    return items.map((item, i) => `
        <div class="flex items-center justify-between py-1 cursor-pointer" onclick="embedQuoteInMessage('${item.symbol}')">
            <div class="flex items-center gap-2">
                <span class="text-lg">${type === 'rise' ? '📈' : '📉'}</span>
                <span class="font-medium">${item.symbol}</span>
            </div>
            <span class="${type === 'rise' ? 'gain' : 'loss'} font-bold">
                ${item.change_pct >= 0 ? '+' : ''}${item.change_pct?.toFixed(2)}%
            </span>
        </div>
    `).join('');
}

/**
 * 刷新行情异动
 */
async function refreshPriceMovements() {
    showMarketAnalysis();
    showToast('已刷新', 'success');
}


// ==================== 工具函数 ====================

/**
 * HTML转义
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 工具栏按钮 - 排行榜入口
 */
function addLeaderboardToolbar() {
    const toolbar = document.querySelector('.trading-selector');
    if (!toolbar) return;

    const leaderboardBtn = document.createElement('button');
    leaderboardBtn.className = 'btn btn-ghost';
    leaderboardBtn.innerHTML = '🏆 排行榜';
    leaderboardBtn.onclick = () => showLeaderboard('traders');
    toolbar.appendChild(leaderboardBtn);
}

/**
 * 工具栏按钮 - 成绩单入口
 */
function addReportCardToolbar() {
    const toolbar = document.querySelector('.trading-selector');
    if (!toolbar) return;

    const reportBtn = document.createElement('button');
    reportBtn.className = 'btn btn-ghost';
    reportBtn.innerHTML = '📊 成绩单';
    reportBtn.onclick = () => showReportCards();
    toolbar.appendChild(reportBtn);
}

/**
 * 工具栏按钮 - 行情分析入口
 */
function addMarketAnalysisToolbar() {
    const toolbar = document.querySelector('.trading-selector');
    if (!toolbar) return;

    const analysisBtn = document.createElement('button');
    analysisBtn.className = 'btn btn-ghost';
    analysisBtn.innerHTML = '📈 行情异动';
    analysisBtn.onclick = () => showMarketAnalysis();
    toolbar.appendChild(analysisBtn);
}

// 页面加载完成后添加工具栏按钮
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        addLeaderboardToolbar();
        addReportCardToolbar();
        addMarketAnalysisToolbar();
    }, 1000);
});

// 导出公共API
window.QuantTalkEmbed = {
    showLeaderboard,
    showReportCards,
    showMarketAnalysis,
    loadTraderLeaderboard,
    loadStrategyLeaderboard,
    loadActivityLeaderboard,
    loadReportCards,
    loadPriceMovements,
    showLeaderPositions,
    copyTrade,
    embedKlineInMessage,
    embedQuoteInMessage,
    embedStrategyInMessage,
    parseEmbedCodes,
    showReportCardDetail,
    showCreateReportCard,
    likeReportCard,
    shareReportCard,
    refreshPriceMovements
};
