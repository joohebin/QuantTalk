/**
 * QuantTalk 第四阶段：加密货币钱包和好友转账
 */

// ============================================
// 钱包管理模块
// ============================================

const WalletModule = {
    // 当前显示的标签页
    currentTab: 'balances',
    
    // 初始化钱包UI
    init() {
        this.loadBalances();
        this.loadWallets();
        this.loadTransferHistory();
        this.loadNotifications();
    },
    
    // 加载余额
    async loadBalances() {
        try {
            const balances = await api('/wallet/balances');
            this.renderBalances(balances);
        } catch (e) {
            console.error('加载余额失败:', e);
        }
    },
    
    // 渲染余额列表
    renderBalances(balances) {
        const container = document.getElementById('wallet-balances');
        if (!container) return;
        
        container.innerHTML = balances.map(b => `
            <div class="wallet-balance-card" data-currency="${b.currency}">
                <div class="balance-currency">${b.currency}</div>
                <div class="balance-amount">
                    <span class="available">${b.available.toFixed(4)}</span>
                    ${b.locked > 0 ? `<span class="locked">锁定: ${b.locked.toFixed(4)}</span>` : ''}
                </div>
                <div class="balance-actions">
                    <button class="btn-small" onclick="WalletModule.showTransferModal('${b.currency}')">转账</button>
                    <button class="btn-small" onclick="WalletModule.showDepositModal('${b.currency}')">充值</button>
                    <button class="btn-small" onclick="WalletModule.showWithdrawModal('${b.currency}')">提现</button>
                </div>
            </div>
        `).join('');
    },
    
    // 加载已绑定钱包
    async loadWallets() {
        try {
            const wallets = await api('/wallet/wallets');
            this.renderWallets(wallets);
        } catch (e) {
            console.error('加载钱包失败:', e);
        }
    },
    
    // 渲染钱包列表
    renderWallets(wallets) {
        const container = document.getElementById('wallet-list');
        if (!container) return;
        
        if (wallets.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>还没有绑定钱包</p>
                    <button class="btn-primary" onclick="WalletModule.showBindModal()">绑定钱包</button>
                </div>
            `;
            return;
        }
        
        container.innerHTML = wallets.map(w => `
            <div class="wallet-card">
                <div class="wallet-header">
                    <span class="wallet-currency">${w.currency}</span>
                    ${w.is_primary ? '<span class="badge-primary">主钱包</span>' : ''}
                    ${w.is_verified ? '<span class="badge-verified">已验证</span>' : '<span class="badge-unverified">未验证</span>'}
                </div>
                <div class="wallet-address">${w.address}</div>
                <div class="wallet-label">${w.label || '无标签'}</div>
                <div class="wallet-actions">
                    <button class="btn-small btn-danger" onclick="WalletModule.unbindWallet(${w.id})">解绑</button>
                </div>
            </div>
        `).join('');
    },
    
    // 显示绑定钱包弹窗
    showBindModal(currency = 'USDT') {
        const modal = document.getElementById('wallet-modal') || this.createModal();
        
        modal.innerHTML = `
            <div class="modal-header">
                <h3>绑定钱包</h3>
                <button class="close-btn" onclick="WalletModule.closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <form id="bind-wallet-form">
                    <div class="form-group">
                        <label>币种</label>
                        <select name="currency" required>
                            <option value="USDT" ${currency === 'USDT' ? 'selected' : ''}>USDT</option>
                            <option value="BTC" ${currency === 'BTC' ? 'selected' : ''}>BTC</option>
                            <option value="ETH" ${currency === 'ETH' ? 'selected' : ''}>ETH</option>
                            <option value="USDC" ${currency === 'USDC' ? 'selected' : ''}>USDC</option>
                            <option value="BNB" ${currency === 'BNB' ? 'selected' : ''}>BNB</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>钱包地址</label>
                        <input type="text" name="address" required placeholder="请输入钱包地址" />
                    </div>
                    <div class="form-group">
                        <label>标签（可选）</label>
                        <input type="text" name="label" placeholder="如：主钱包、冷钱包" />
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" name="is_primary" /> 设为主钱包
                        </label>
                    </div>
                    <div class="form-actions">
                        <button type="submit" class="btn-primary">确认绑定</button>
                        <button type="button" class="btn-secondary" onclick="WalletModule.closeModal()">取消</button>
                    </div>
                </form>
            </div>
        `;
        
        modal.classList.add('active');
        
        document.getElementById('bind-wallet-form').onsubmit = async (e) => {
            e.preventDefault();
            const form = e.target;
            const data = {
                currency: form.currency.value,
                address: form.address.value,
                label: form.label.value,
                is_primary: form.is_primary.checked
            };
            
            try {
                await api('/wallet/wallets', { method: 'POST', body: data });
                toast('钱包绑定成功');
                this.closeModal();
                this.loadWallets();
            } catch (err) {
                toast(err.detail || '绑定失败', 'error');
            }
        };
    },
    
    // 解绑钱包
    async unbindWallet(walletId) {
        if (!confirm('确定要解绑这个钱包吗？')) return;
        
        try {
            await api(`/wallet/wallets/${walletId}`, { method: 'DELETE' });
            toast('钱包已解绑');
            this.loadWallets();
        } catch (err) {
            toast(err.detail || '解绑失败', 'error');
        }
    },
    
    // 显示充值弹窗
    async showDepositModal(currency) {
        try {
            const deposit = await api(`/wallet/deposit-address/${currency}`);
            
            const modal = document.getElementById('wallet-modal') || this.createModal();
            modal.innerHTML = `
                <div class="modal-header">
                    <h3>充值 ${currency}</h3>
                    <button class="close-btn" onclick="WalletModule.closeModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <p class="text-center text-muted">向以下地址转入 ${currency} 完成充值</p>
                    <div class="deposit-address-box">
                        <div class="address-label">充值地址</div>
                        <div class="address-value">${deposit.address}</div>
                        <button class="btn-small" onclick="copyToClipboard('${deposit.address}')">复制地址</button>
                    </div>
                    <div class="deposit-warning">
                        <strong>注意：</strong>
                        <ul>
                            <li>仅接收 ${currency} 代币</li>
                            <li>请确认转账网络正确</li>
                            <li>充值需要网络确认后到账</li>
                        </ul>
                    </div>
                </div>
            `;
            modal.classList.add('active');
        } catch (e) {
            toast('获取充值地址失败', 'error');
        }
    },
    
    // 显示提现弹窗
    showWithdrawModal(currency) {
        const modal = document.getElementById('wallet-modal') || this.createModal();
        
        modal.innerHTML = `
            <div class="modal-header">
                <h3>提现 ${currency}</h3>
                <button class="close-btn" onclick="WalletModule.closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <form id="withdraw-form">
                    <p class="text-muted">提现到您绑定的钱包地址</p>
                    <div class="form-group">
                        <label>数量</label>
                        <input type="number" name="amount" required step="0.0001" min="0.0001" placeholder="请输入提现数量" />
                    </div>
                    <div class="form-group">
                        <label>到账地址</label>
                        <input type="text" name="to_address" required placeholder="接收方钱包地址" />
                    </div>
                    <div class="form-actions">
                        <button type="submit" class="btn-primary">确认提现</button>
                        <button type="button" class="btn-secondary" onclick="WalletModule.closeModal()">取消</button>
                    </div>
                </form>
            </div>
        `;
        
        modal.classList.add('active');
        
        document.getElementById('withdraw-form').onsubmit = async (e) => {
            e.preventDefault();
            const form = e.target;
            const data = {
                currency: currency,
                amount: parseFloat(form.amount.value),
                to_address: form.to_address.value
            };
            
            try {
                const result = await api('/wallet/withdraw', { method: 'POST', body: data });
                toast(`提现成功！交易哈希: ${result.tx_hash}`);
                this.closeModal();
                this.loadBalances();
            } catch (err) {
                toast(err.detail || '提现失败', 'error');
            }
        };
    },
    
    // 显示转账弹窗
    showTransferModal(currency) {
        const modal = document.getElementById('wallet-modal') || this.createModal();
        
        modal.innerHTML = `
            <div class="modal-header">
                <h3>向好友转账</h3>
                <button class="close-btn" onclick="WalletModule.closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <form id="transfer-form">
                    <div class="form-group">
                        <label>币种</label>
                        <select name="currency" required>
                            <option value="${currency}" selected>${currency}</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>好友用户名</label>
                        <input type="text" name="receiver" required placeholder="输入好友用户名" />
                    </div>
                    <div class="form-group">
                        <label>数量</label>
                        <input type="number" name="amount" required step="0.0001" min="0.0001" placeholder="请输入转账数量" />
                    </div>
                    <div class="form-group">
                        <label>备注（可选）</label>
                        <textarea name="note" placeholder="给好友留言" rows="2"></textarea>
                    </div>
                    <div class="form-actions">
                        <button type="submit" class="btn-primary">确认转账</button>
                        <button type="button" class="btn-secondary" onclick="WalletModule.closeModal()">取消</button>
                    </div>
                </form>
            </div>
        `;
        
        modal.classList.add('active');
        
        document.getElementById('transfer-form').onsubmit = async (e) => {
            e.preventDefault();
            const form = e.target;
            const data = {
                currency: form.currency.value,
                receiver_username: form.receiver.value,
                amount: parseFloat(form.amount.value),
                note: form.note.value
            };
            
            try {
                const result = await api('/wallet/transfer', { method: 'POST', body: data });
                toast(`转账成功！交易哈希: ${result.tx_hash.substring(0, 16)}...`);
                this.closeModal();
                this.loadBalances();
                this.loadTransferHistory();
            } catch (err) {
                toast(err.detail || '转账失败', 'error');
            }
        };
    },
    
    // 加载转账历史
    async loadTransferHistory() {
        try {
            const transfers = await api('/wallet/transfers');
            this.renderTransferHistory(transfers);
        } catch (e) {
            console.error('加载转账记录失败:', e);
        }
    },
    
    // 渲染转账历史
    renderTransferHistory(transfers) {
        const container = document.getElementById('transfer-history');
        if (!container) return;
        
        if (transfers.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>暂无转账记录</p></div>';
            return;
        }
        
        container.innerHTML = transfers.map(t => {
            const isSent = t.sender_id === S.user?.id;
            return `
                <div class="transfer-item ${isSent ? 'sent' : 'received'}">
                    <div class="transfer-icon">${isSent ? '↑' : '↓'}</div>
                    <div class="transfer-info">
                        <div class="transfer-user">${isSent ? `发送给 ${t.receiver?.username || '用户'}` : `收到 ${t.sender?.username || '用户'} 转账`}</div>
                        <div class="transfer-meta">
                            <span class="transfer-amount ${isSent ? 'negative' : 'positive'}">
                                ${isSent ? '-' : '+'}${t.amount} ${t.currency}
                            </span>
                            <span class="transfer-date">${formatTime(t.created_at)}</span>
                        </div>
                        ${t.note ? `<div class="transfer-note">${t.note}</div>` : ''}
                    </div>
                    <div class="transfer-status">
                        <span class="status-${t.status}">${t.status}</span>
                    </div>
                </div>
            `;
        }).join('');
    },
    
    // 加载通知
    async loadNotifications() {
        try {
            const notifications = await api('/wallet/notifications');
            this.renderNotifications(notifications);
            
            const count = await api('/wallet/notifications/unread-count');
            this.updateUnreadBadge(count.unread_count);
        } catch (e) {
            console.error('加载通知失败:', e);
        }
    },
    
    // 渲染通知
    renderNotifications(notifications) {
        const container = document.getElementById('wallet-notifications');
        if (!container) return;
        
        if (notifications.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>暂无通知</p></div>';
            return;
        }
        
        container.innerHTML = notifications.map(n => `
            <div class="notification-item ${n.is_read ? '' : 'unread'}" data-id="${n.id}">
                <div class="notification-icon">${this.getNotificationIcon(n.type)}</div>
                <div class="notification-content">
                    <div class="notification-title">${n.title}</div>
                    <div class="notification-text">${n.content}</div>
                    <div class="notification-time">${formatTime(n.created_at)}</div>
                </div>
            </div>
        `).join('');
        
        // 绑定点击事件
        container.querySelectorAll('.notification-item.unread').forEach(item => {
            item.onclick = () => this.markAsRead(item.dataset.id);
        });
    },
    
    // 获取通知图标
    getNotificationIcon(type) {
        const icons = {
            transfer_received: '💰',
            transfer_sent: '📤',
            confirmation: '✅'
        };
        return icons[type] || '🔔';
    },
    
    // 标记通知为已读
    async markAsRead(notificationId) {
        try {
            await api(`/wallet/notifications/${notificationId}/read`, { method: 'POST' });
            this.loadNotifications();
        } catch (e) {
            console.error('标记已读失败:', e);
        }
    },
    
    // 更新未读徽章
    updateUnreadBadge(count) {
        const badge = document.getElementById('wallet-unread-badge');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline' : 'none';
        }
    },
    
    // 创建模态框
    createModal() {
        const modal = document.createElement('div');
        modal.id = 'wallet-modal';
        modal.className = 'modal';
        document.body.appendChild(modal);
        return modal;
    },
    
    // 关闭模态框
    closeModal() {
        const modal = document.getElementById('wallet-modal');
        if (modal) modal.classList.remove('active');
    },
    
    // 切换标签页
    switchTab(tab) {
        this.currentTab = tab;
        
        // 更新标签按钮状态
        document.querySelectorAll('.wallet-tabs .tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });
        
        // 显示对应内容
        document.querySelectorAll('.wallet-tab-content').forEach(content => {
            content.style.display = content.id === `wallet-${tab}` ? 'block' : 'none';
        });
    }
};


// ============================================
// 渲染钱包页面
// ============================================

function renderWalletPage() {
    return `
        <div class="wallet-container">
            <div class="wallet-header">
                <h2>💰 我的钱包</h2>
                <button class="btn-primary" onclick="WalletModule.showBindModal()">绑定钱包</button>
            </div>
            
            <!-- 标签切换 -->
            <div class="wallet-tabs">
                <button class="tab-btn active" data-tab="balances" onclick="WalletModule.switchTab('balances')">余额</button>
                <button class="tab-btn" data-tab="history" onclick="WalletModule.switchTab('history')">转账记录</button>
                <button class="tab-btn" data-tab="wallets" onclick="WalletModule.switchTab('wallets')">钱包管理</button>
                <button class="tab-btn" data-tab="notifications" onclick="WalletModule.switchTab('notifications')">
                    通知 <span id="wallet-unread-badge" class="badge"></span>
                </button>
            </div>
            
            <!-- 余额标签页 -->
            <div id="wallet-balances" class="wallet-tab-content" id="wallet-balances">
                <div class="loading">加载中...</div>
            </div>
            
            <!-- 转账记录标签页 -->
            <div id="wallet-history" class="wallet-tab-content" style="display:none;">
                <div id="transfer-history" class="transfer-list">
                    <div class="loading">加载中...</div>
                </div>
            </div>
            
            <!-- 钱包管理标签页 -->
            <div id="wallet-wallets" class="wallet-tab-content" style="display:none;">
                <div id="wallet-list" class="wallet-grid">
                    <div class="loading">加载中...</div>
                </div>
            </div>
            
            <!-- 通知标签页 -->
            <div id="wallet-notifications" class="wallet-tab-content" style="display:none;">
                <div class="notification-list">
                    <div class="loading">加载中...</div>
                </div>
            </div>
        </div>
        
        <style>
            .wallet-container {
                max-width: 900px;
                margin: 0 auto;
                padding: 20px;
            }
            .wallet-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }
            .wallet-tabs {
                display: flex;
                gap: 10px;
                border-bottom: 1px solid #333;
                margin-bottom: 20px;
            }
            .wallet-tabs .tab-btn {
                padding: 10px 20px;
                background: none;
                border: none;
                color: #888;
                cursor: pointer;
                border-bottom: 2px solid transparent;
            }
            .wallet-tabs .tab-btn.active {
                color: #00d4ff;
                border-bottom-color: #00d4ff;
            }
            .wallet-balance-card {
                background: #1a1a2e;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 15px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .balance-currency {
                font-size: 24px;
                font-weight: bold;
                color: #ffd700;
            }
            .balance-amount {
                text-align: center;
            }
            .balance-amount .available {
                font-size: 28px;
                display: block;
            }
            .balance-amount .locked {
                font-size: 12px;
                color: #f39c12;
            }
            .balance-actions {
                display: flex;
                gap: 8px;
            }
            .btn-small {
                padding: 6px 12px;
                font-size: 12px;
                background: #2d4a6f;
                border: none;
                border-radius: 6px;
                color: #fff;
                cursor: pointer;
            }
            .btn-small:hover {
                background: #3d5a7f;
            }
            .btn-small.btn-danger {
                background: #c0392b;
            }
            .wallet-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                gap: 15px;
            }
            .wallet-card {
                background: #1a1a2e;
                border-radius: 12px;
                padding: 15px;
            }
            .wallet-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }
            .wallet-currency {
                font-size: 18px;
                font-weight: bold;
            }
            .wallet-address {
                font-family: monospace;
                font-size: 12px;
                color: #888;
                word-break: break-all;
                margin-bottom: 8px;
            }
            .transfer-list {
                display: flex;
                flex-direction: column;
                gap: 10px;
            }
            .transfer-item {
                display: flex;
                align-items: center;
                background: #1a1a2e;
                border-radius: 8px;
                padding: 12px;
                gap: 12px;
            }
            .transfer-icon {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 20px;
            }
            .transfer-item.sent .transfer-icon {
                background: #c0392b;
            }
            .transfer-item.received .transfer-icon {
                background: #27ae60;
            }
            .transfer-info {
                flex: 1;
            }
            .transfer-user {
                font-weight: bold;
                margin-bottom: 4px;
            }
            .transfer-meta {
                display: flex;
                gap: 12px;
                font-size: 12px;
            }
            .transfer-amount {
                font-weight: bold;
            }
            .transfer-amount.negative {
                color: #e74c3c;
            }
            .transfer-amount.positive {
                color: #2ecc71;
            }
            .transfer-note {
                font-size: 12px;
                color: #888;
                margin-top: 4px;
            }
            .transfer-status span {
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
            }
            .status-confirmed {
                background: #27ae60;
                color: white;
            }
            .status-pending {
                background: #f39c12;
                color: white;
            }
            .deposit-address-box {
                background: #1a1a2e;
                border-radius: 8px;
                padding: 20px;
                text-align: center;
                margin: 20px 0;
            }
            .deposit-address-box .address-value {
                font-family: monospace;
                font-size: 14px;
                word-break: break-all;
                margin: 10px 0;
            }
            .deposit-warning {
                background: rgba(243, 156, 18, 0.1);
                border: 1px solid #f39c12;
                border-radius: 8px;
                padding: 15px;
                font-size: 13px;
            }
            .deposit-warning ul {
                margin: 8px 0 0 0;
                padding-left: 20px;
            }
            .notification-list {
                display: flex;
                flex-direction: column;
                gap: 10px;
            }
            .notification-item {
                display: flex;
                gap: 12px;
                background: #1a1a2e;
                border-radius: 8px;
                padding: 12px;
                cursor: pointer;
            }
            .notification-item.unread {
                border-left: 3px solid #00d4ff;
            }
            .notification-icon {
                font-size: 24px;
            }
            .notification-title {
                font-weight: bold;
                margin-bottom: 4px;
            }
            .notification-text {
                font-size: 13px;
                color: #aaa;
            }
            .notification-time {
                font-size: 11px;
                color: #666;
                margin-top: 6px;
            }
            .empty-state {
                text-align: center;
                padding: 40px;
                color: #666;
            }
            .badge {
                background: #e74c3c;
                color: white;
                padding: 2px 6px;
                border-radius: 10px;
                font-size: 11px;
                margin-left: 5px;
            }
            .badge-primary {
                background: #3498db;
            }
            .badge-verified {
                background: #27ae60;
            }
            .badge-unverified {
                background: #95a5a6;
            }
            .modal {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0,0,0,0.8);
                z-index: 1000;
                align-items: center;
                justify-content: center;
            }
            .modal.active {
                display: flex;
            }
            .modal-content {
                background: #1a1a2e;
                border-radius: 12px;
                max-width: 500px;
                width: 90%;
                max-height: 90vh;
                overflow-y: auto;
            }
            .modal-header {
                display: flex;
                justify-content: space-between;
                padding: 15px 20px;
                border-bottom: 1px solid #333;
            }
            .modal-header h3 {
                margin: 0;
            }
            .close-btn {
                background: none;
                border: none;
                color: #888;
                font-size: 24px;
                cursor: pointer;
            }
            .modal-body {
                padding: 20px;
            }
            .form-group {
                margin-bottom: 15px;
            }
            .form-group label {
                display: block;
                margin-bottom: 5px;
                color: #888;
            }
            .form-group input,
            .form-group select,
            .form-group textarea {
                width: 100%;
                padding: 10px;
                background: #0d0d1a;
                border: 1px solid #333;
                border-radius: 6px;
                color: #fff;
            }
            .form-actions {
                display: flex;
                gap: 10px;
                margin-top: 20px;
            }
            .btn-primary {
                flex: 1;
                padding: 12px;
                background: #00d4ff;
                border: none;
                border-radius: 6px;
                color: #000;
                font-weight: bold;
                cursor: pointer;
            }
            .btn-secondary {
                flex: 1;
                padding: 12px;
                background: #333;
                border: none;
                border-radius: 6px;
                color: #fff;
                cursor: pointer;
            }
            .text-center { text-align: center; }
            .text-muted { color: #888; }
            .text-danger { color: #e74c3c; }
        </style>
    `;
}


// ============================================
// 快捷转账：好友列表弹窗
// ============================================

const QuickTransfer = {
    async show() {
        try {
            const friends = await api('/wallet/friends');
            
            const modal = document.createElement('div');
            modal.className = 'modal active';
            modal.id = 'quick-transfer-modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>快捷转账</h3>
                        <button class="close-btn" onclick="this.closest('.modal').remove()">&times;</button>
                    </div>
                    <div class="modal-body">
                        <p class="text-muted">选择好友进行转账</p>
                        <div class="friend-list">
                            ${friends.map(f => `
                                <div class="friend-item" onclick="QuickTransfer.selectFriend('${f.username}')">
                                    <img src="${f.avatar || '/default-avatar.png'}" class="friend-avatar" />
                                    <div class="friend-info">
                                        <div class="friend-name">${f.username}</div>
                                        <div class="friend-status">
                                            ${f.is_online ? '<span class="online">在线</span>' : '<span class="offline">离线</span>'}
                                        </div>
                                    </div>
                                    ${f.primary_balance ? `<div class="friend-balance">${f.primary_amount.toFixed(2)} ${f.primary_balance}</div>` : ''}
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            
            modal.onclick = (e) => {
                if (e.target === modal) modal.remove();
            };
        } catch (e) {
            toast('加载好友列表失败', 'error');
        }
    },
    
    selectFriend(username) {
        document.getElementById('quick-transfer-modal')?.remove();
        WalletModule.showTransferModal('USDT');
        setTimeout(() => {
            document.querySelector('#transfer-form input[name="receiver"]').value = username;
        }, 100);
    }
};


// ============================================
// 工具函数
// ============================================

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        toast('地址已复制');
    }).catch(() => {
        // 降级方案
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        toast('地址已复制');
    });
}


// ============================================
// 更新主页面导航
// ============================================

function addWalletNavButton() {
    // 在导航栏添加钱包按钮
    const nav = document.querySelector('.main-nav');
    if (nav && !document.getElementById('nav-wallet')) {
        const walletBtn = document.createElement('button');
        walletBtn.id = 'nav-wallet';
        walletBtn.className = 'nav-btn';
        walletBtn.innerHTML = '💰 钱包';
        walletBtn.onclick = () => {
            S.page = 'wallet';
            renderAll();
        };
        nav.appendChild(walletBtn);
    }
}


// ============================================
// 初始化
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // 添加钱包导航
    addWalletNavButton();
});
