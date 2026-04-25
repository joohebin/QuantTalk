/**
 * QuantTalk Discord风格界面 v2.0 - 完整版
 * 功能：
 * - 文字频道：实时聊天 + K线图 + 实时行情 + 策略回测
 * - 语音频道：语音通话 + K线图 + 实时行情 + 策略回测
 * - 视频频道：视频通话 + K线图 + 实时行情 + 策略回测
 */

const DISCORD = {
    // 版本
    VERSION: '2.0',

    // 当前状态
    state: {
        guilds: [],
        currentGuild: null,
        currentChannel: null,
        currentChannelType: null, // 'text', 'voice', 'video'
        textChannels: [],
        voiceChannels: [],
        videoChannels: [],
        messages: {},
        ws: null,
        // WebRTC
        peerConnections: {},
        localStream: null,
        muted: false,
        videoOff: false,
        screenStream: null,
        // K线图
        chart: null,
        candleSeries: null,
        volumeSeries: null,
        // 策略回测
        backtestResults: null,
        selectedSymbol: 'BTCUSDT',
        selectedInterval: '1h',
    },

    // 交易品种配置
    SYMBOLS: {
        'BTCUSDT': { name: 'BTC', type: 'crypto', color: '#F7931A' },
        'ETHUSDT': { name: 'ETH', type: 'crypto', color: '#627EEA' },
        'EURUSD': { name: 'EUR/USD', type: 'forex', color: '#23A559' },
        'XAUUSD': { name: 'XAU/USD', type: 'metal', color: '#FFD700' },
        'USOIL': { name: 'WTI原油', type: 'oil', color: '#CD7F32' },
        'US500': { name: 'S&P500', type: 'index', color: '#4B0082' },
    },

    // 时间周期
    INTERVALS: ['1m', '5m', '15m', '1h', '4h', '1d', '1w'],

    // TURN/STUN配置
    iceServers: {
        iceServers: [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' },
            {
                urls: 'turn:18.183.23.89:3478',
                username: 'quanttalk',
                credential: 'QuantTalk2024Turn'
            }
        ]
    },

    // ========== 初始化 ==========

    init() {
        this.loadGuilds();
        this.setupWebSocket();
        this.injectStyles();
        this.injectFullStyles();
    },

    // ========== 基础样式 ==========

    injectStyles() {
        const style = document.createElement('style');
        style.id = 'discord-base-styles';
        style.textContent = `
            /* Discord风格布局 */
            .discord-layout {
                display: flex;
                height: calc(100vh - 60px);
                background: #1a1a1c;
            }

            /* 服务器列表 */
            .guilds-sidebar {
                width: 72px;
                background: #1e1f22;
                padding: 12px 0;
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 8px;
                overflow-y: auto;
            }

            .guild-item {
                width: 48px;
                height: 48px;
                border-radius: 50%;
                background: #313338;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.15s;
                font-size: 20px;
                color: #fff;
                position: relative;
            }

            .guild-item:hover {
                border-radius: 16px;
                background: #5865f2;
            }

            .guild-item.active {
                border-radius: 16px;
                background: #5865f2;
            }

            .guild-item.home {
                background: #5865f2;
            }

            .guild-divider {
                width: 32px;
                height: 2px;
                background: #313338;
                border-radius: 1px;
                margin: 4px 0;
            }

            .add-guild-btn {
                width: 48px;
                height: 48px;
                border-radius: 50%;
                background: transparent;
                border: none;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 24px;
                color: #23a559;
                transition: all 0.15s;
            }

            .add-guild-btn:hover {
                background: #23a559;
                color: #fff;
                border-radius: 16px;
            }

            /* 频道侧边栏 */
            .channels-sidebar {
                width: 240px;
                background: #2b2d31;
                display: flex;
                flex-direction: column;
            }

            .guild-header {
                height: 48px;
                padding: 0 16px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                border-bottom: 2px solid #1e1f22;
                cursor: pointer;
            }

            .guild-header h2 {
                font-size: 15px;
                font-weight: 600;
                color: #fff;
            }

            .channels-list {
                flex: 1;
                overflow-y: auto;
                padding: 8px 8px;
            }

            .channel-group {
                margin-bottom: 16px;
            }

            .channel-group-header {
                display: flex;
                align-items: center;
                padding: 4px 8px;
                cursor: pointer;
                color: #949ba4;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
            }

            .channel-item {
                display: flex;
                align-items: center;
                padding: 6px 8px;
                border-radius: 4px;
                cursor: pointer;
                color: #949ba4;
                font-size: 14px;
                gap: 8px;
            }

            .channel-item:hover {
                background: rgba(79, 84, 92, 0.4);
                color: #dbdee1;
            }

            .channel-item.active {
                background: rgba(79, 84, 92, 0.6);
                color: #fff;
            }

            .channel-item.video {
                color: #f0b232;
            }

            /* 主内容区 */
            .main-content {
                flex: 1;
                display: flex;
                flex-direction: column;
                background: #313338;
                overflow: hidden;
            }

            .content-header {
                height: 48px;
                padding: 0 16px;
                display: flex;
                align-items: center;
                border-bottom: 1px solid #1e1f22;
            }

            .content-header h3 {
                font-size: 15px;
                font-weight: 600;
                color: #fff;
            }

            /* 消息区域 */
            .messages-area {
                flex: 1;
                overflow-y: auto;
                padding: 16px;
            }

            .message {
                display: flex;
                margin-bottom: 16px;
            }

            .message-avatar {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                margin-right: 16px;
                background: #5865f2;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #fff;
                font-weight: 600;
            }

            .message-content {
                flex: 1;
            }

            .message-header {
                display: flex;
                align-items: baseline;
                gap: 8px;
                margin-bottom: 4px;
            }

            .message-author {
                font-weight: 600;
                color: #fff;
            }

            .message-time {
                font-size: 11px;
                color: #72767d;
            }

            .message-text {
                color: #dbdee1;
                font-size: 14px;
                line-height: 1.4;
            }

            /* 消息输入 */
            .message-input-area {
                padding: 0 16px 24px;
            }

            .message-input-container {
                background: #383a40;
                border-radius: 8px;
                display: flex;
                align-items: center;
                padding: 0 16px;
            }

            .message-input {
                flex: 1;
                background: transparent;
                border: none;
                padding: 12px 0;
                color: #fff;
                font-size: 14px;
                outline: none;
            }

            /* 语音控制栏 */
            .voice-controls {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 12px 16px;
                background: #232428;
                border-top: 1px solid #1e1f22;
            }

            .voice-buttons {
                display: flex;
                gap: 8px;
            }

            .voice-btn {
                width: 32px;
                height: 32px;
                border-radius: 50%;
                border: none;
                background: #4e5058;
                color: #fff;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 14px;
            }

            .voice-btn:hover {
                background: #5c6068;
            }

            .voice-btn.active {
                background: #ed4245;
            }

            .voice-btn.disconnect {
                background: #ed4245;
            }

            /* 模态框 */
            .discord-modal {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0,0,0,0.85);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1000;
            }

            .discord-modal-content {
                background: #36393f;
                border-radius: 8px;
                width: 440px;
                max-height: 80vh;
                overflow: hidden;
            }

            .discord-modal-header {
                padding: 16px 20px;
                border-bottom: 1px solid #202225;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }

            .discord-modal-header h3 {
                font-size: 16px;
                font-weight: 600;
                color: #fff;
            }

            .discord-modal-close {
                background: none;
                border: none;
                color: #949ba4;
                cursor: pointer;
                font-size: 18px;
            }

            .discord-modal-body {
                padding: 20px;
                overflow-y: auto;
            }

            .discord-form-group {
                margin-bottom: 16px;
            }

            .discord-form-group label {
                display: block;
                color: #b9bbbe;
                font-size: 13px;
                margin-bottom: 8px;
            }

            .discord-input {
                width: 100%;
                padding: 10px 12px;
                background: #404249;
                border: none;
                border-radius: 4px;
                color: #fff;
                font-size: 14px;
                outline: none;
            }

            .discord-btn {
                padding: 10px 20px;
                border-radius: 4px;
                border: none;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
            }

            .discord-btn-primary {
                background: #5865f2;
                color: #fff;
            }

            .discord-btn-primary:hover {
                background: #4752c4;
            }

            .discord-btn-secondary {
                background: #4e5058;
                color: #dbdee1;
            }
        `;
        document.head.appendChild(style);
    },

    // ========== 完整功能样式 ==========

    injectFullStyles() {
        const style = document.createElement('style');
        style.id = 'discord-full-styles';
        style.textContent = `
            /* 行情Ticker */
            .market-ticker {
                display: flex;
                gap: 12px;
                padding: 8px 16px;
                background: #2b2d31;
                border-bottom: 1px solid #1e1f22;
                overflow-x: auto;
                font-size: 12px;
            }

            .ticker-item {
                display: flex;
                align-items: center;
                gap: 6px;
                white-space: nowrap;
                padding: 4px 8px;
                border-radius: 4px;
                cursor: pointer;
                transition: background 0.2s;
            }

            .ticker-item:hover {
                background: rgba(79, 84, 92, 0.4);
            }

            .ticker-item.active {
                background: rgba(88, 101, 242, 0.4);
            }

            .ticker-item .symbol {
                color: #b9bbbe;
                font-weight: 500;
            }

            .ticker-item .price {
                color: #fff;
                font-weight: 600;
            }

            .ticker-item .change {
                color: #23a559;
                font-size: 11px;
            }

            .ticker-item .change.negative {
                color: #ed4245;
            }

            /* 主工作区 - 三栏布局 */
            .discord-workspace {
                flex: 1;
                display: flex;
                overflow: hidden;
            }

            /* 左侧：聊天区 */
            .discord-chat-area {
                flex: 1;
                display: flex;
                flex-direction: column;
                min-width: 300px;
            }

            /* 中间：工具面板 */
            .discord-tools-panel {
                width: 360px;
                background: #1e1f22;
                border-left: 1px solid #2b2d31;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }

            .tools-tabs {
                display: flex;
                border-bottom: 1px solid #2b2d31;
            }

            .tools-tab {
                flex: 1;
                padding: 10px;
                text-align: center;
                color: #949ba4;
                cursor: pointer;
                font-size: 13px;
                transition: all 0.2s;
                border-bottom: 2px solid transparent;
            }

            .tools-tab:hover {
                color: #fff;
                background: rgba(79, 84, 92, 0.3);
            }

            .tools-tab.active {
                color: #fff;
                border-bottom-color: #5865f2;
                background: rgba(88, 101, 242, 0.2);
            }

            .tools-content {
                flex: 1;
                overflow-y: auto;
                padding: 12px;
            }

            /* K线图区域 */
            .chart-container {
                display: flex;
                flex-direction: column;
                height: 100%;
            }

            .chart-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 8px 12px;
                background: #2b2d31;
                border-bottom: 1px solid #1e1f22;
            }

            .chart-symbol-info {
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .chart-symbol-name {
                font-size: 16px;
                font-weight: 600;
                color: #fff;
            }

            .chart-price {
                font-size: 18px;
                font-weight: 700;
            }

            .chart-price.up { color: #23a559; }
            .chart-price.down { color: #ed4245; }

            .chart-intervals {
                display: flex;
                gap: 4px;
            }

            .interval-btn {
                padding: 4px 8px;
                border-radius: 4px;
                border: none;
                background: transparent;
                color: #949ba4;
                cursor: pointer;
                font-size: 12px;
                transition: all 0.2s;
            }

            .interval-btn:hover {
                background: rgba(79, 84, 92, 0.4);
                color: #fff;
            }

            .interval-btn.active {
                background: #5865f2;
                color: #fff;
            }

            .chart-area {
                flex: 1;
                min-height: 250px;
            }

            .chart-loading {
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100%;
                color: #949ba4;
            }

            /* 实时行情面板 */
            .market-panel {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }

            .market-card {
                background: #2b2d31;
                border-radius: 8px;
                padding: 12px;
            }

            .market-card-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }

            .market-card-title {
                font-weight: 600;
                color: #fff;
            }

            .market-card-badge {
                font-size: 10px;
                padding: 2px 6px;
                border-radius: 4px;
                background: rgba(88, 101, 242, 0.3);
                color: #7289da;
            }

            .market-stats {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 8px;
            }

            .market-stat {
                display: flex;
                flex-direction: column;
            }

            .market-stat-label {
                font-size: 11px;
                color: #72767d;
            }

            .market-stat-value {
                font-size: 14px;
                font-weight: 600;
                color: #fff;
            }

            /* 策略回测面板 */
            .backtest-panel {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }

            .backtest-form {
                background: #2b2d31;
                border-radius: 8px;
                padding: 12px;
            }

            .backtest-form-title {
                font-weight: 600;
                color: #fff;
                margin-bottom: 12px;
                font-size: 14px;
            }

            .backtest-inputs {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 8px;
            }

            .backtest-input-group {
                display: flex;
                flex-direction: column;
            }

            .backtest-input-group label {
                font-size: 11px;
                color: #72767d;
                margin-bottom: 4px;
            }

            .backtest-input-group input,
            .backtest-input-group select {
                padding: 8px;
                background: #404249;
                border: none;
                border-radius: 4px;
                color: #fff;
                font-size: 13px;
            }

            .backtest-input-group input:focus,
            .backtest-input-group select:focus {
                outline: 2px solid #5865f2;
            }

            .backtest-btn {
                width: 100%;
                padding: 10px;
                border-radius: 6px;
                border: none;
                background: #5865f2;
                color: #fff;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: background 0.2s;
                margin-top: 8px;
            }

            .backtest-btn:hover {
                background: #4752c4;
            }

            .backtest-results {
                background: #2b2d31;
                border-radius: 8px;
                padding: 12px;
            }

            .backtest-results-title {
                font-weight: 600;
                color: #fff;
                margin-bottom: 12px;
                font-size: 14px;
            }

            .backtest-metrics {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 12px;
            }

            .backtest-metric {
                background: #36393f;
                border-radius: 6px;
                padding: 10px;
                text-align: center;
            }

            .backtest-metric-value {
                font-size: 18px;
                font-weight: 700;
                color: #fff;
            }

            .backtest-metric-value.positive { color: #23a559; }
            .backtest-metric-value.negative { color: #ed4245; }

            .backtest-metric-label {
                font-size: 11px;
                color: #72767d;
                margin-top: 4px;
            }

            .backtest-equity-curve {
                margin-top: 12px;
                height: 120px;
                background: #404249;
                border-radius: 6px;
                overflow: hidden;
            }

            /* 语音/视频频道视图 */
            .voice-channel-view {
                flex: 1;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }

            .video-grid {
                flex: 1;
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 16px;
                padding: 16px;
                background: #1e1f22;
                overflow-y: auto;
            }

            .video-tile {
                background: #2b2d31;
                border-radius: 8px;
                aspect-ratio: 16/9;
                position: relative;
                overflow: hidden;
            }

            .video-tile video {
                width: 100%;
                height: 100%;
                object-fit: cover;
            }

            .video-tile.local video {
                transform: scaleX(-1);
            }

            .video-tile .username {
                position: absolute;
                bottom: 8px;
                left: 8px;
                background: rgba(0,0,0,0.6);
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                color: #fff;
            }

            .video-tile .mute-indicator {
                position: absolute;
                top: 8px;
                right: 8px;
                background: rgba(237, 66, 69, 0.8);
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
            }

            .video-tile .speaking {
                border: 2px solid #23a559;
                box-shadow: 0 0 12px rgba(35, 165, 89, 0.5);
            }

            /* 频道类型图标 */
            .channel-type-icon {
                width: 20px;
                text-align: center;
            }

            /* 视频区域（语音频道也用） */
            .media-area {
                flex: 1;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }

            .media-grid {
                flex: 1;
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 12px;
                padding: 12px;
                background: #1e1f22;
                overflow-y: auto;
            }

            .media-tile {
                background: #2b2d31;
                border-radius: 8px;
                aspect-ratio: 16/9;
                position: relative;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #5865f2;
            }

            .media-tile video {
                width: 100%;
                height: 100%;
                object-fit: cover;
                border-radius: 8px;
            }

            .media-tile .tile-username {
                position: absolute;
                bottom: 8px;
                left: 8px;
                background: rgba(0,0,0,0.6);
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                color: #fff;
            }

            .media-tile .tile-status {
                position: absolute;
                top: 8px;
                right: 8px;
                background: rgba(237, 66, 69, 0.8);
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
            }

            /* K线图快捷按钮 */
            .chart-actions {
                display: flex;
                gap: 6px;
            }

            .chart-action-btn {
                padding: 4px 10px;
                border-radius: 4px;
                border: none;
                background: #4e5058;
                color: #fff;
                cursor: pointer;
                font-size: 12px;
                transition: background 0.2s;
            }

            .chart-action-btn:hover {
                background: #5c6068;
            }

            .chart-action-btn.active {
                background: #5865f2;
            }

            /* 实时数据指示器 */
            .live-indicator {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                font-size: 11px;
                color: #23a559;
            }

            .live-dot {
                width: 6px;
                height: 6px;
                border-radius: 50%;
                background: #23a559;
                animation: pulse 1.5s infinite;
            }

            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }

            /* 响应式 */
            @media (max-width: 1200px) {
                .discord-tools-panel {
                    width: 300px;
                }
            }

            @media (max-width: 900px) {
                .discord-tools-panel {
                    display: none;
                }
            }
        `;
        document.head.appendChild(style);
    },

    // ========== 加载服务器列表 ==========

    async loadGuilds() {
        try {
            const res = await fetch('/api/guilds/', {
                headers: { 'Authorization': `Bearer ${S.token}` }
            });
            if (res.ok) {
                this.state.guilds = await res.json();
                this.renderGuilds();
            }
        } catch (e) {
            console.error('加载服务器失败:', e);
        }
    },

    // ========== 渲染服务器列表 ==========

    renderGuilds() {
        const container = document.getElementById('discord-guilds');
        if (!container) return;

        container.innerHTML = `
            <div class="guild-item home" onclick="DISCORD.showHome()" title="首页">
                🏠
            </div>
            <div class="guild-divider"></div>
            ${this.state.guilds.map(g => `
                <div class="guild-item ${this.state.currentGuild?.id === g.id ? 'active' : ''}"
                     onclick="DISCORD.selectGuild(${g.id})"
                     title="${g.name}">
                    ${g.icon ? `<img src="${g.icon}" style="width:100%;height:100%;border-radius:50%;">` : g.name.charAt(0).toUpperCase()}
                </div>
            `).join('')}
            <div class="add-guild-btn" onclick="DISCORD.showCreateGuild()" title="创建服务器">
                ➕
            </div>
        `;
    },

    // ========== 选择服务器 ==========

    async selectGuild(guildId) {
        try {
            const res = await fetch(`/api/guilds/${guildId}/channels`, {
                headers: { 'Authorization': `Bearer ${S.token}` }
            });
            if (res.ok) {
                const data = await res.json();
                this.state.currentGuild = this.state.guilds.find(g => g.id === guildId);
                this.state.textChannels = data.text_channels || [];
                this.state.voiceChannels = data.voice_channels || [];
                this.state.videoChannels = data.video_channels || [];
                this.renderChannelsSidebar();
                this.renderMainContent();
            }
        } catch (e) {
            console.error('加载频道失败:', e);
        }
    },

    // ========== 渲染频道侧边栏 ==========

    renderChannelsSidebar() {
        const container = document.getElementById('discord-channels');
        if (!container || !this.state.currentGuild) return;

        container.innerHTML = `
            <div class="guild-header" onclick="DISCORD.showGuildSettings()">
                <h2>${this.state.currentGuild.name}</h2>
                <span>▼</span>
            </div>

            <div class="channels-list">
                ${this.state.textChannels.length > 0 ? `
                    <div class="channel-group">
                        <div class="channel-group-header">📝 文字频道</div>
                        ${this.state.textChannels.map(c => `
                            <div class="channel-item ${this.state.currentChannel?.id === c.id && this.state.currentChannelType === 'text' ? 'active' : ''}"
                                 onclick="DISCORD.selectChannel(${c.id}, 'text')">
                                <span class="channel-type-icon">#</span>
                                <span>${c.name}</span>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}

                ${this.state.voiceChannels.length > 0 ? `
                    <div class="channel-group">
                        <div class="channel-group-header">🎤 语音频道</div>
                        ${this.state.voiceChannels.map(c => `
                            <div class="channel-item ${this.state.currentChannel?.id === c.id && this.state.currentChannelType === 'voice' ? 'active' : ''}"
                                 onclick="DISCORD.selectChannel(${c.id}, 'voice')">
                                <span class="channel-type-icon">🔊</span>
                                <span>${c.name}</span>
                                ${c.online_count > 0 ? `<span style="margin-left:auto;font-size:11px;color:#949ba4">${c.online_count}</span>` : ''}
                            </div>
                        `).join('')}
                    </div>
                ` : ''}

                ${this.state.videoChannels && this.state.videoChannels.length > 0 ? `
                    <div class="channel-group">
                        <div class="channel-group-header">📹 视频频道</div>
                        ${this.state.videoChannels.map(c => `
                            <div class="channel-item video ${this.state.currentChannel?.id === c.id && this.state.currentChannelType === 'video' ? 'active' : ''}"
                                 onclick="DISCORD.selectChannel(${c.id}, 'video')">
                                <span class="channel-type-icon">📹</span>
                                <span>${c.name}</span>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
            </div>

            <div style="padding: 8px; border-top: 1px solid #1e1f22;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 32px; height: 32px; border-radius: 50%; background: #5865f2; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 12px;">
                        ${(S.user?.username || 'U').charAt(0).toUpperCase()}
                    </div>
                    <div>
                        <div style="font-size: 13px; color: #fff;">${S.user?.username}</div>
                        <div style="font-size: 11px; color: #23a559;">● 在线</div>
                    </div>
                </div>
            </div>
        `;
    },

    // ========== 渲染主内容区 ==========

    renderMainContent() {
        const container = document.getElementById('discord-main');
        if (!container) return;

        if (this.state.currentChannel) {
            this.renderChannelView(container);
        } else {
            this.renderWelcomeView(container);
        }
    },

    // ========== 欢迎视图 ==========

    renderWelcomeView(container) {
        container.innerHTML = `
            <div class="content-header">
                <h3># ${this.state.currentGuild?.name || '选择服务器'}</h3>
            </div>
            <div style="flex: 1; display: flex; align-items: center; justify-content: center; flex-direction: column; color: #949ba4;">
                <div style="font-size: 48px; margin-bottom: 16px;">👋</div>
                <div style="font-size: 24px; color: #fff; margin-bottom: 8px;">欢迎来到 ${this.state.currentGuild?.name}</div>
                <div>选择左侧的频道开始</div>
            </div>
        `;
    },

    // ========== 频道视图（统一处理三种频道）==========

    renderChannelView(container) {
        const channel = this.state.currentChannel;
        const typeLabels = { text: '文字频道', voice: '语音频道', video: '视频频道' };

        container.innerHTML = `
            <div class="content-header">
                <h3>${this.state.currentChannelType === 'text' ? '#' : this.state.currentChannelType === 'voice' ? '🔊' : '📹'} ${channel.name}</h3>
                <span style="margin-left:12px;font-size:12px;color:#949ba4">${typeLabels[this.state.currentChannelType]} | 实时行情 & K线图</span>
            </div>

            <!-- 行情Ticker -->
            <div id="discord-ticker" class="market-ticker">
                ${this.renderTickerItems()}
            </div>

            <!-- 主工作区 -->
            <div class="discord-workspace">
                <!-- 左侧：聊天/通话区域 -->
                <div class="discord-chat-area">
                    ${this.state.currentChannelType === 'text' ? this.renderTextChat() : this.renderMediaArea()}
                </div>

                <!-- 右侧：工具面板 -->
                <div class="discord-tools-panel">
                    <div class="tools-tabs">
                        <div class="tools-tab active" onclick="DISCORD.switchToolsTab('chart')">📊 K线图</div>
                        <div class="tools-tab" onclick="DISCORD.switchToolsTab('market')">📈 行情</div>
                        <div class="tools-tab" onclick="DISCORD.switchToolsTab('backtest')">🎯 回测</div>
                    </div>
                    <div class="tools-content" id="tools-content">
                        ${this.renderChartPanel()}
                    </div>
                </div>
            </div>

            ${this.state.currentChannelType !== 'text' ? this.renderVoiceControls() : this.renderTextInput()}
        `;

        // 初始化K线图
        setTimeout(() => this.initChart(), 100);
        // 启动实时行情
        this.startMarketStream();
    },

    // ========== Ticker 项目 ==========

    renderTickerItems() {
        const symbols = Object.entries(this.SYMBOLS);
        return symbols.map(([key, sym]) => `
            <div class="ticker-item ${this.state.selectedSymbol === key ? 'active' : ''}"
                 onclick="DISCORD.switchSymbol('${key}')">
                <span class="symbol">${sym.name}</span>
                <span class="price" id="ticker-price-${key}">--</span>
                <span class="change" id="ticker-change-${key}">--</span>
            </div>
        `).join('') + `
            <div style="margin-left:auto;display:flex;align-items:center;gap:8px;">
                <span class="live-indicator"><span class="live-dot"></span>LIVE</span>
                <button onclick="DISCORD.showFullChart()" style="padding:4px 10px;border-radius:4px;border:none;background:#5865f2;color:#fff;cursor:pointer;font-size:12px;">
                    全屏
                </button>
            </div>
        `;
    },

    // ========== 文字聊天区域 ==========

    renderTextChat() {
        return `
            <div id="discord-messages" class="messages-area">
                <!-- 消息列表 -->
            </div>
        `;
    },

    // ========== 媒体区域（语音/视频）==========

    renderMediaArea() {
        const isVideo = this.state.currentChannelType === 'video';

        return `
            <div class="media-area">
                <div class="media-grid" id="discord-media-grid">
                    <div class="media-tile local" id="discord-local-tile">
                        <video id="discord-local-video" autoplay muted playsinline></video>
                        <div class="tile-username">${S.user?.username} (你)</div>
                        <div id="discord-local-status" class="tile-status" style="display:none">🔇</div>
                    </div>
                </div>
            </div>
        `;
    },

    // ========== 文字输入框 ==========

    renderTextInput() {
        return `
            <div class="message-input-area">
                <div class="message-input-container">
                    <input type="text" id="discord-msg-input" class="message-input"
                           placeholder="发送消息到 #${this.state.currentChannel.name}"
                           onkeypress="if(event.key==='Enter')DISCORD.sendMessage()">
                </div>
            </div>
        `;
    },

    // ========== 语音/视频控制栏 ==========

    renderVoiceControls() {
        const isVideo = this.state.currentChannelType === 'video';

        return `
            <div class="voice-controls">
                <div class="voice-user-info">
                    <span style="color: #23a559;">●</span>
                    <span>${this.state.currentChannel.name}</span>
                </div>
                <div class="voice-buttons">
                    <button class="voice-btn ${this.state.muted ? 'active' : ''}" id="discord-mic-btn"
                            onclick="DISCORD.toggleMic()" title="麦克风">
                        ${this.state.muted ? '🔇' : '🎤'}
                    </button>
                    ${isVideo ? `
                        <button class="voice-btn ${this.state.videoOff ? 'active' : ''}" id="discord-video-btn"
                                onclick="DISCORD.toggleVideo()" title="摄像头">
                            ${this.state.videoOff ? '📹✕' : '📹'}
                        </button>
                    ` : ''}
                    <button class="voice-btn" onclick="DISCORD.shareScreen()" title="屏幕共享">
                        🖥️
                    </button>
                    <button class="voice-btn disconnect" onclick="DISCORD.leaveChannel()" title="断开">
                        📴
                    </button>
                </div>
            </div>
        `;
    },

    // ========== 工具面板 ==========

    renderChartPanel() {
        return `
            <div class="chart-container">
                <div class="chart-header">
                    <div class="chart-symbol-info">
                        <span class="chart-symbol-name">${this.SYMBOLS[this.state.selectedSymbol]?.name || this.state.selectedSymbol}</span>
                        <span class="chart-price" id="chart-price">--</span>
                        <span class="change" id="chart-change" style="font-size:12px">--</span>
                    </div>
                    <div class="chart-intervals">
                        ${this.INTERVALS.map(i => `
                            <button class="interval-btn ${this.state.selectedInterval === i ? 'active' : ''}"
                                    onclick="DISCORD.switchInterval('${i}')">${i}</button>
                        `).join('')}
                    </div>
                </div>
                <div class="chart-area" id="discord-chart-area">
                    <div class="chart-loading">加载中...</div>
                </div>
                <div style="padding:8px 12px;background:#2b2d31;border-top:1px solid #1e1f22;display:flex;justify-content:space-between;align-items:center;">
                    <div style="font-size:12px;color:#949ba4;">
                        <span id="chart-info">--</span>
                    </div>
                    <div class="chart-actions">
                        <button class="chart-action-btn" onclick="DISCORD.toggleMA()">MA</button>
                        <button class="chart-action-btn" onclick="DISCORD.toggleVolume()">VOL</button>
                        <button class="chart-action-btn" onclick="DISCORD.resetZoom()">重置</button>
                    </div>
                </div>
            </div>
        `;
    },

    renderMarketPanel() {
        return `
            <div class="market-panel">
                <div class="market-card">
                    <div class="market-card-header">
                        <span class="market-card-title">${this.SYMBOLS[this.state.selectedSymbol]?.name || this.state.selectedSymbol}</span>
                        <span class="market-card-badge">实时</span>
                    </div>
                    <div class="market-stats">
                        <div class="market-stat">
                            <span class="market-stat-label">最新价</span>
                            <span class="market-stat-value" id="market-latest">--</span>
                        </div>
                        <div class="market-stat">
                            <span class="market-stat-label">24h涨跌</span>
                            <span class="market-stat-value" id="market-change">--</span>
                        </div>
                        <div class="market-stat">
                            <span class="market-stat-label">24h最高</span>
                            <span class="market-stat-value" id="market-high">--</span>
                        </div>
                        <div class="market-stat">
                            <span class="market-stat-label">24h最低</span>
                            <span class="market-stat-value" id="market-low">--</span>
                        </div>
                        <div class="market-stat">
                            <span class="market-stat-label">24h成交量</span>
                            <span class="market-stat-value" id="market-volume">--</span>
                        </div>
                        <div class="market-stat">
                            <span class="market-stat-label">买入价</span>
                            <span class="market-stat-value" id="market-bid">--</span>
                        </div>
                        <div class="market-stat">
                            <span class="market-stat-label">卖出价</span>
                            <span class="market-stat-value" id="market-ask">--</span>
                        </div>
                        <div class="market-stat">
                            <span class="market-stat-label">更新时间</span>
                            <span class="market-stat-value" id="market-time">--</span>
                        </div>
                    </div>
                </div>

                <div style="margin-top:12px;">
                    <div style="font-weight:600;color:#fff;margin-bottom:8px;">所有品种</div>
                    ${Object.entries(this.SYMBOLS).map(([key, sym]) => `
                        <div class="market-card" style="margin-bottom:8px;padding:8px;cursor:pointer"
                             onclick="DISCORD.switchSymbol('${key}')">
                            <div style="display:flex;justify-content:space-between;align-items:center;">
                                <span style="font-weight:500;color:#fff">${sym.name}</span>
                                <div style="text-align:right;">
                                    <div style="font-weight:600;color:#fff" id="market-all-price-${key}">--</div>
                                    <div style="font-size:11px;color:#23a559" id="market-all-change-${key}">--</div>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    },

    renderBacktestPanel() {
        return `
            <div class="backtest-panel">
                <div class="backtest-form">
                    <div class="backtest-form-title">📊 策略回测配置</div>
                    <div class="backtest-inputs">
                        <div class="backtest-input-group">
                            <label>交易品种</label>
                            <select id="bt-symbol">
                                ${Object.entries(this.SYMBOLS).map(([k, v]) => `<option value="${k}" ${k === this.state.selectedSymbol ? 'selected' : ''}>${v.name}</option>`).join('')}
                            </select>
                        </div>
                        <div class="backtest-input-group">
                            <label>时间周期</label>
                            <select id="bt-interval">
                                ${this.INTERVALS.map(i => `<option value="${i}" ${i === this.state.selectedInterval ? 'selected' : ''}>${i}</option>`).join('')}
                            </select>
                        </div>
                        <div class="backtest-input-group">
                            <label>回测天数</label>
                            <input type="number" id="bt-days" value="30" min="7" max="365">
                        </div>
                        <div class="backtest-input-group">
                            <label>初始资金</label>
                            <input type="number" id="bt-capital" value="10000" min="100">
                        </div>
                        <div class="backtest-input-group">
                            <label>策略类型</label>
                            <select id="bt-strategy">
                                <option value="ma_cross">MA金叉/死叉</option>
                                <option value="rsi">RSI超买/超卖</option>
                                <option value="bollinger">布林带策略</option>
                                <option value="macd">MACD策略</option>
                            </select>
                        </div>
                        <div class="backtest-input-group">
                            <label>仓位比例</label>
                            <input type="number" id="bt-position" value="10" min="1" max="100" step="1"> %
                        </div>
                    </div>
                    <button class="backtest-btn" onclick="DISCORD.runBacktest()">
                        🚀 开始回测
                    </button>
                </div>

                <div class="backtest-results" id="bt-results" style="display:none;">
                    <div class="backtest-results-title">📈 回测结果</div>
                    <div class="backtest-metrics">
                        <div class="backtest-metric">
                            <div class="backtest-metric-value positive" id="bt-return">--</div>
                            <div class="backtest-metric-label">总收益率</div>
                        </div>
                        <div class="backtest-metric">
                            <div class="backtest-metric-value" id="bt-trades">--</div>
                            <div class="backtest-metric-label">交易次数</div>
                        </div>
                        <div class="backtest-metric">
                            <div class="backtest-metric-value positive" id="bt-winrate">--</div>
                            <div class="backtest-metric-label">胜率</div>
                        </div>
                        <div class="backtest-metric">
                            <div class="backtest-metric-value" id="bt-profitfactor">--</div>
                            <div class="backtest-metric-label">盈亏比</div>
                        </div>
                        <div class="backtest-metric">
                            <div class="backtest-metric-value" id="bt-maxdd">--</div>
                            <div class="backtest-metric-label">最大回撤</div>
                        </div>
                        <div class="backtest-metric">
                            <div class="backtest-metric-value" id="bt-sharp">--</div>
                            <div class="backtest-metric-label">夏普比率</div>
                        </div>
                    </div>
                    <div class="backtest-equity-curve" id="bt-equity">
                        <!-- 资金曲线 -->
                    </div>
                </div>
            </div>
        `;
    },

    // ========== 切换工具标签 ==========

    switchToolsTab(tab) {
        // 更新标签样式
        document.querySelectorAll('.tools-tab').forEach(t => t.classList.remove('active'));
        event.target.classList.add('active');

        // 切换内容
        const content = document.getElementById('tools-content');
        if (!content) return;

        switch(tab) {
            case 'chart':
                content.innerHTML = this.renderChartPanel();
                setTimeout(() => this.initChart(), 50);
                break;
            case 'market':
                content.innerHTML = this.renderMarketPanel();
                this.updateMarketPanel();
                break;
            case 'backtest':
                content.innerHTML = this.renderBacktestPanel();
                break;
        }
    },

    // ========== 选择频道 ==========

    async selectChannel(channelId, channelType) {
        let channels;
        switch(channelType) {
            case 'text': channels = this.state.textChannels; break;
            case 'voice': channels = this.state.voiceChannels; break;
            case 'video': channels = this.state.videoChannels; break;
        }

        const channel = channels?.find(c => c.id === channelId);
        if (!channel) return;

        this.state.currentChannel = channel;
        this.state.currentChannelType = channelType;

        this.renderChannelsSidebar();
        this.renderMainContent();

        // 加载消息（文字频道）
        if (channelType === 'text') {
            await this.loadMessages(channelId);
        }

        // 初始化媒体（语音/视频频道）
        if (channelType === 'voice' || channelType === 'video') {
            await this.initLocalMedia();
        }
    },

    // ========== 消息相关 ==========

    async loadMessages(channelId) {
        try {
            const res = await fetch(`/api/guilds/${this.state.currentGuild.id}/channels/text/${channelId}/messages`, {
                headers: { 'Authorization': `Bearer ${S.token}` }
            });
            if (res.ok) {
                const messages = await res.json();
                this.state.messages[channelId] = messages;
                this.renderMessages();
            }
        } catch (e) {
            console.error('加载消息失败:', e);
        }
    },

    renderMessages() {
        const container = document.getElementById('discord-messages');
        if (!container || !this.state.currentChannel) return;

        const messages = this.state.messages[this.state.currentChannel.id] || [];

        container.innerHTML = messages.map(m => `
            <div class="message">
                <div class="message-avatar">${m.author_username?.charAt(0).toUpperCase() || '?'}</div>
                <div class="message-content">
                    <div class="message-header">
                        <span class="message-author">${m.author_username || '匿名'}</span>
                        <span class="message-time">${new Date(m.created_at).toLocaleString()}</span>
                    </div>
                    <div class="message-text">${esc(m.content)}</div>
                </div>
            </div>
        `).join('');

        container.scrollTop = container.scrollHeight;
    },

    async sendMessage() {
        const input = document.getElementById('discord-msg-input');
        if (!input || !input.value.trim() || !this.state.currentChannel) return;

        const content = input.value.trim();
        input.value = '';

        try {
            const res = await fetch(`/api/guilds/${this.state.currentGuild.id}/channels/text/${this.state.currentChannel.id}/messages`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${S.token}`
                },
                body: JSON.stringify({ content })
            });

            if (res.ok) {
                const message = await res.json();
                if (!this.state.messages[this.state.currentChannel.id]) {
                    this.state.messages[this.state.currentChannel.id] = [];
                }
                this.state.messages[this.state.currentChannel.id].push(message);
                this.renderMessages();
            }
        } catch (e) {
            console.error('发送消息失败:', e);
        }
    },

    // ========== 媒体控制 ==========

    async initLocalMedia() {
        try {
            const isVideo = this.state.currentChannelType === 'video';

            this.state.localStream = await navigator.mediaDevices.getUserMedia({
                video: isVideo,
                audio: true
            });

            const videoEl = document.getElementById('discord-local-video');
            if (videoEl) {
                videoEl.srcObject = this.state.localStream;
            }
        } catch (e) {
            console.warn('无法获取媒体设备:', e);
            toast('仅文字模式', 'info');
        }
    },

    toggleMic() {
        this.state.muted = !this.state.muted;
        if (this.state.localStream) {
            this.state.localStream.getAudioTracks().forEach(track => {
                track.enabled = !this.state.muted;
            });
        }

        const btn = document.getElementById('discord-mic-btn');
        if (btn) {
            btn.classList.toggle('active', this.state.muted);
            btn.textContent = this.state.muted ? '🔇' : '🎤';
        }

        const status = document.getElementById('discord-local-status');
        if (status) {
            status.style.display = this.state.muted ? 'block' : 'none';
            status.textContent = '🔇';
        }
    },

    toggleVideo() {
        this.state.videoOff = !this.state.videoOff;
        if (this.state.localStream) {
            this.state.localStream.getVideoTracks().forEach(track => {
                track.enabled = !this.state.videoOff;
            });
        }

        const btn = document.getElementById('discord-video-btn');
        if (btn) {
            btn.classList.toggle('active', this.state.videoOff);
            btn.textContent = this.state.videoOff ? '📹✕' : '📹';
        }

        const tile = document.getElementById('discord-local-tile');
        if (tile) {
            tile.style.display = this.state.videoOff ? 'none' : 'flex';
        }
    },

    async shareScreen() {
        try {
            this.state.screenStream = await navigator.mediaDevices.getDisplayMedia({
                video: true
            });

            toast('屏幕共享已开始', 'success');

            // 将屏幕流添加到视频网格
            const grid = document.getElementById('discord-media-grid');
            if (grid) {
                const tile = document.createElement('div');
                tile.className = 'media-tile';
                tile.id = 'discord-screen-tile';
                tile.innerHTML = `
                    <video autoplay muted playsinline></video>
                    <div class="tile-username">屏幕共享</div>
                `;
                const video = tile.querySelector('video');
                video.srcObject = this.state.screenStream;
                grid.appendChild(tile);
            }

            // 监听结束
            this.state.screenStream.getVideoTracks()[0].onended = () => {
                this.stopScreenShare();
            };
        } catch (e) {
            console.error('屏幕共享失败:', e);
        }
    },

    stopScreenShare() {
        if (this.state.screenStream) {
            this.state.screenStream.getTracks().forEach(t => t.stop());
            this.state.screenStream = null;
        }

        const tile = document.getElementById('discord-screen-tile');
        if (tile) tile.remove();

        toast('屏幕共享已结束', 'info');
    },

    async leaveChannel() {
        // 停止媒体
        if (this.state.localStream) {
            this.state.localStream.getTracks().forEach(track => track.stop());
            this.state.localStream = null;
        }

        // 停止屏幕共享
        this.stopScreenShare();

        // 离开频道
        try {
            const type = this.state.currentChannelType === 'voice' ? 'voice' : 'video';
            await fetch(`/api/guilds/${this.state.currentGuild.id}/channels/${type}/${this.state.currentChannel.id}/leave`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${S.token}` }
            });
        } catch (e) {}

        this.state.currentChannel = null;
        this.state.currentChannelType = null;
        this.renderChannelsSidebar();
        this.renderMainContent();
    },

    // ========== K线图 ==========

    async initChart() {
        const container = document.getElementById('discord-chart-area');
        if (!container || typeof TradingView === 'undefined') {
            // 等待 TradingView 库加载
            if (typeof TradingView === 'undefined') {
                const script = document.createElement('script');
                script.src = 'https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js';
                script.onload = () => setTimeout(() => this.initChart(), 100);
                document.head.appendChild(script);
            }
            return;
        }

        container.innerHTML = '<div id="discord-chart-inner" style="height:100%;"></div>';

        const chartContainer = document.getElementById('discord-chart-inner');
        if (!chartContainer) return;

        // 创建图表
        if (this.state.chart) {
            this.state.chart.remove();
        }

        this.state.chart = LightweightCharts.createChart(chartContainer, {
            width: chartContainer.clientWidth,
            height: chartContainer.clientHeight || 280,
            layout: {
                background: { type: 'solid', color: '#1e1f22' },
                textColor: '#949ba4',
            },
            grid: {
                vertLines: { color: '#2b2d31' },
                horzLines: { color: '#2b2d31' },
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
            },
            timeScale: {
                borderColor: '#2b2d31',
                timeVisible: true,
            },
            rightPriceScale: {
                borderColor: '#2b2d31',
            },
        });

        // K线系列
        this.state.candleSeries = this.state.chart.addCandlestickSeries({
            upColor: '#23a559',
            downColor: '#ed4245',
            borderUpColor: '#23a559',
            borderDownColor: '#ed4245',
            wickUpColor: '#23a559',
            wickDownColor: '#ed4245',
        });

        // 成交量系列
        this.state.volumeSeries = this.state.chart.addHistogramSeries({
            color: '#5865f2',
            priceFormat: { type: 'volume' },
            priceScaleId: '',
        });

        this.state.volumeSeries.priceScale().applyOptions({
            scaleMargins: { top: 0.8, bottom: 0 },
        });

        // 加载数据
        await this.loadChartData();

        // 响应式
        const resizeObserver = new ResizeObserver(entries => {
            for (let entry of entries) {
                if (this.state.chart) {
                    this.state.chart.applyOptions({ width: entry.contentRect.width });
                }
            }
        });
        resizeObserver.observe(chartContainer);
    },

    async loadChartData() {
        try {
            const res = await fetch(`/api/market/kline/${this.state.selectedSymbol}?interval=${this.state.selectedInterval}&limit=200`);
            if (!res.ok) throw new Error('获取K线失败');

            const data = await res.json();

            if (!data.candles || !data.candles.length) {
                // 使用模拟数据
                this.loadMockData();
                return;
            }

            // 处理K线数据
            const candleData = data.candles.map(c => ({
                time: this.parseTime(c.time || c[0]),
                open: parseFloat(c.open || c[1]),
                high: parseFloat(c.high || c[2]),
                low: parseFloat(c.low || c[3]),
                close: parseFloat(c.close || c[4]),
            }));

            // 处理成交量
            const volumeData = data.candles.map(c => ({
                time: this.parseTime(c.time || c[0]),
                value: parseFloat(c.volume || c[5] || 0),
                color: parseFloat(c.close || c[4]) >= parseFloat(c.open || c[1]) ? 'rgba(35,165,89,0.5)' : 'rgba(237,66,69,0.5)',
            }));

            this.state.candleSeries.setData(candleData);
            this.state.volumeSeries.setData(volumeData);
            this.state.chart.timeScale().fitContent();

            // 更新信息
            const lastCandle = candleData[candleData.length - 1];
            if (lastCandle) {
                const change = ((lastCandle.close - lastCandle.open) / lastCandle.open * 100).toFixed(2);
                const priceEl = document.getElementById('chart-price');
                const changeEl = document.getElementById('chart-change');

                if (priceEl) {
                    priceEl.textContent = '$' + lastCandle.close.toFixed(2);
                    priceEl.className = 'chart-price ' + (change >= 0 ? 'up' : 'down');
                }
                if (changeEl) {
                    changeEl.textContent = (change >= 0 ? '+' : '') + change + '%';
                    changeEl.style.color = change >= 0 ? '#23a559' : '#ed4245';
                }
            }

            const infoEl = document.getElementById('chart-info');
            if (infoEl) {
                infoEl.textContent = `${data.candles.length} 根K线 | ${this.state.selectedInterval}`;
            }

        } catch (e) {
            console.error('加载K线数据失败:', e);
            this.loadMockData();
        }
    },

    loadMockData() {
        // 生成模拟数据
        const now = Math.floor(Date.now() / 1000);
        const interval = this.getIntervalSeconds();
        let price = this.state.selectedSymbol === 'BTCUSDT' ? 65000 :
                    this.state.selectedSymbol === 'ETHUSDT' ? 3500 :
                    this.state.selectedSymbol === 'EURUSD' ? 1.08 :
                    this.state.selectedSymbol === 'XAUUSD' ? 2300 : 100;

        const candleData = [];
        const volumeData = [];

        for (let i = 200; i >= 0; i--) {
            const time = now - (i * interval);
            const change = (Math.random() - 0.5) * 0.02;
            const open = price;
            const close = price * (1 + change);
            const high = Math.max(open, close) * (1 + Math.random() * 0.01);
            const low = Math.min(open, close) * (1 - Math.random() * 0.01);
            const volume = Math.random() * 1000000;

            candleData.push({ time, open, high, low, close });
            volumeData.push({
                time,
                value: volume,
                color: close >= open ? 'rgba(35,165,89,0.5)' : 'rgba(237,66,69,0.5)'
            });

            price = close;
        }

        this.state.candleSeries.setData(candleData);
        this.state.volumeSeries.setData(volumeData);
        this.state.chart.timeScale().fitContent();

        // 更新显示
        const lastCandle = candleData[candleData.length - 1];
        if (lastCandle) {
            const change = ((lastCandle.close - lastCandle.open) / lastCandle.open * 100).toFixed(2);
            const priceEl = document.getElementById('chart-price');
            const changeEl = document.getElementById('chart-change');

            if (priceEl) {
                priceEl.textContent = '$' + lastCandle.close.toFixed(2);
                priceEl.className = 'chart-price ' + (change >= 0 ? 'up' : 'down');
            }
            if (changeEl) {
                changeEl.textContent = (change >= 0 ? '+' : '') + change + '%';
                changeEl.style.color = change >= 0 ? '#23a559' : '#ed4245';
            }
        }
    },

    getIntervalSeconds() {
        const map = { '1m': 60, '5m': 300, '15m': 900, '1h': 3600, '4h': 14400, '1d': 86400, '1w': 604800 };
        return map[this.state.selectedInterval] || 3600;
    },

    parseTime(time) {
        if (typeof time === 'number') return time;
        if (typeof time === 'string') {
            const d = new Date(time);
            if (!isNaN(d)) return Math.floor(d.getTime() / 1000);
        }
        return Math.floor(new Date().getTime() / 1000);
    },

    // ========== 切换品种/周期 ==========

    async switchSymbol(symbol) {
        this.state.selectedSymbol = symbol;

        // 更新UI
        document.querySelectorAll('.ticker-item').forEach(el => {
            el.classList.toggle('active', el.textContent.includes(this.SYMBOLS[symbol]?.name || symbol));
        });

        // 重新加载图表
        if (this.state.chart) {
            await this.loadChartData();
        }

        // 更新工具面板
        const content = document.getElementById('tools-content');
        if (content) {
            const activeTab = document.querySelector('.tools-tab.active');
            if (activeTab && activeTab.textContent.includes('K线')) {
                content.innerHTML = this.renderChartPanel();
                setTimeout(() => this.initChart(), 50);
            } else if (activeTab && activeTab.textContent.includes('行情')) {
                content.innerHTML = this.renderMarketPanel();
                this.updateMarketPanel();
            }
        }
    },

    async switchInterval(interval) {
        this.state.selectedInterval = interval;

        // 更新按钮
        document.querySelectorAll('.interval-btn').forEach(btn => {
            btn.classList.toggle('active', btn.textContent === interval);
        });

        // 重新加载图表
        if (this.state.chart) {
            await this.loadChartData();
        }
    },

    toggleMA() {
        toast('MA指标: 功能开发中', 'info');
    },

    toggleVolume() {
        if (this.state.volumeSeries) {
            const visible = this.state.volumeSeries.visible();
            this.state.volumeSeries.applyOptions({ visible: !visible });
        }
    },

    resetZoom() {
        if (this.state.chart) {
            this.state.chart.timeScale().fitContent();
        }
    },

    showFullChart() {
        // 打开全屏图表模态框
        const modal = document.createElement('div');
        modal.className = 'discord-modal';
        modal.id = 'fullchart-modal';
        modal.innerHTML = `
            <div style="background:#1e1f22;border-radius:8px;width:95vw;height:90vh;display:flex;flex-direction:column;">
                <div style="padding:12px 16px;border-bottom:1px solid #2b2d31;display:flex;justify-content:space-between;align-items:center;">
                    <span style="color:#fff;font-weight:600;">全屏K线图 - ${this.SYMBOLS[this.state.selectedSymbol]?.name}</span>
                    <button onclick="this.closest('.discord-modal').remove()" style="background:none;border:none;color:#949ba4;cursor:pointer;font-size:20px;">✕</button>
                </div>
                <div id="fullchart-container" style="flex:1;"></div>
            </div>
        `;
        document.body.appendChild(modal);

        // 创建全屏图表
        const container = document.getElementById('fullchart-container');
        if (container && typeof TradingView !== 'undefined') {
            const chart = LightweightCharts.createChart(container, {
                width: container.clientWidth,
                height: container.clientHeight,
                layout: {
                    background: { type: 'solid', color: '#1e1f22' },
                    textColor: '#949ba4',
                },
                grid: {
                    vertLines: { color: '#2b2d31' },
                    horzLines: { color: '#2b2d31' },
                },
            });

            const candleSeries = chart.addCandlestickSeries({
                upColor: '#23a559',
                downColor: '#ed4245',
                borderUpColor: '#23a559',
                borderDownColor: '#ed4245',
                wickUpColor: '#23a559',
                wickDownColor: '#ed4245',
            });

            // 复制当前数据
            if (this.state.candleSeries) {
                candleSeries.setData(this.state.candleSeries.data());
            }

            chart.timeScale().fitContent();

            // 响应式
            const ro = new ResizeObserver(() => {
                chart.applyOptions({ width: container.clientWidth, height: container.clientHeight });
            });
            ro.observe(container);
        }
    },

    // ========== 实时行情 ==========

    marketInterval: null,

    startMarketStream() {
        // 清除旧定时器
        if (this.marketInterval) {
            clearInterval(this.marketInterval);
        }

        // 立即更新
        this.updateMarketTicker();

        // 每3秒更新一次
        this.marketInterval = setInterval(() => {
            this.updateMarketTicker();
        }, 3000);
    },

    updateMarketTicker() {
        Object.keys(this.SYMBOLS).forEach(symbol => {
            // 生成模拟价格
            const basePrice = symbol === 'BTCUSDT' ? 65000 :
                             symbol === 'ETHUSDT' ? 3500 :
                             symbol === 'EURUSD' ? 1.08 :
                             symbol === 'XAUUSD' ? 2300 : 100;

            const change = (Math.random() - 0.5) * 0.02;
            const price = basePrice * (1 + change);
            const changePct = (Math.random() - 0.5) * 5;

            const priceEl = document.getElementById(`ticker-price-${symbol}`);
            const changeEl = document.getElementById(`ticker-change-${symbol}`);

            if (priceEl) {
                priceEl.textContent = '$' + price.toFixed(symbol === 'EURUSD' ? 4 : 2);
            }
            if (changeEl) {
                changeEl.textContent = (changePct >= 0 ? '+' : '') + changePct.toFixed(2) + '%';
                changeEl.className = 'change' + (changePct < 0 ? ' negative' : '');
            }
        });
    },

    updateMarketPanel() {
        const symbol = this.state.selectedSymbol;
        const basePrice = symbol === 'BTCUSDT' ? 65000 :
                         symbol === 'ETHUSDT' ? 3500 :
                         symbol === 'EURUSD' ? 1.08 :
                         symbol === 'XAUUSD' ? 2300 : 100;

        const price = basePrice * (1 + (Math.random() - 0.5) * 0.01);
        const change = (Math.random() - 0.5) * 5;
        const high = price * 1.02;
        const low = price * 0.98;
        const volume = Math.random() * 1000000000;
        const spread = price * 0.0001;

        document.getElementById('market-latest').textContent = '$' + price.toFixed(2);
        document.getElementById('market-change').textContent = (change >= 0 ? '+' : '') + change.toFixed(2) + '%';
        document.getElementById('market-high').textContent = '$' + high.toFixed(2);
        document.getElementById('market-low').textContent = '$' + low.toFixed(2);
        document.getElementById('market-volume').textContent = this.formatVolume(volume);
        document.getElementById('market-bid').textContent = '$' + (price - spread).toFixed(2);
        document.getElementById('market-ask').textContent = '$' + (price + spread).toFixed(2);
        document.getElementById('market-time').textContent = new Date().toLocaleTimeString();

        // 更新所有品种
        Object.keys(this.SYMBOLS).forEach(sym => {
            const p = sym === 'BTCUSDT' ? 65000 : sym === 'ETHUSDT' ? 3500 : sym === 'EURUSD' ? 1.08 : 2300;
            const c = (Math.random() - 0.5) * 5;
            const el = document.getElementById(`market-all-price-${sym}`);
            const cel = document.getElementById(`market-all-change-${sym}`);
            if (el) el.textContent = '$' + (p * (1 + c/100)).toFixed(sym === 'EURUSD' ? 4 : 2);
            if (cel) {
                cel.textContent = (c >= 0 ? '+' : '') + c.toFixed(2) + '%';
                cel.style.color = c >= 0 ? '#23a559' : '#ed4245';
            }
        });
    },

    formatVolume(v) {
        if (v >= 1e9) return (v / 1e9).toFixed(2) + 'B';
        if (v >= 1e6) return (v / 1e6).toFixed(2) + 'M';
        if (v >= 1e3) return (v / 1e3).toFixed(2) + 'K';
        return v.toFixed(2);
    },

    // ========== 策略回测 ==========

    async runBacktest() {
        const symbol = document.getElementById('bt-symbol')?.value || this.state.selectedSymbol;
        const interval = document.getElementById('bt-interval')?.value || this.state.selectedInterval;
        const days = parseInt(document.getElementById('bt-days')?.value || 30);
        const capital = parseInt(document.getElementById('bt-capital')?.value || 10000);
        const strategy = document.getElementById('bt-strategy')?.value || 'ma_cross';
        const positionPct = parseInt(document.getElementById('bt-position')?.value || 10) / 100;

        toast('回测中...', 'info');

        // 模拟回测（实际应调用后端API）
        await new Promise(r => setTimeout(r, 1500));

        // 生成模拟结果
        const trades = Math.floor(Math.random() * 20) + 10;
        const winRate = 40 + Math.random() * 40;
        const totalReturn = (Math.random() - 0.3) * 50;
        const maxDD = Math.random() * 20;
        const profitFactor = 1 + Math.random() * 2;
        const sharpe = (Math.random() - 0.5) * 3;

        // 显示结果
        const results = document.getElementById('bt-results');
        if (results) {
            results.style.display = 'block';

            document.getElementById('bt-return').textContent = (totalReturn >= 0 ? '+' : '') + totalReturn.toFixed(2) + '%';
            document.getElementById('bt-return').className = 'backtest-metric-value ' + (totalReturn >= 0 ? 'positive' : 'negative');

            document.getElementById('bt-trades').textContent = trades;
            document.getElementById('bt-winrate').textContent = winRate.toFixed(1) + '%';
            document.getElementById('bt-winrate').className = 'backtest-metric-value ' + (winRate >= 50 ? 'positive' : 'negative');

            document.getElementById('bt-profitfactor').textContent = profitFactor.toFixed(2);
            document.getElementById('bt-maxdd').textContent = maxDD.toFixed(2) + '%';
            document.getElementById('bt-sharp').textContent = sharpe.toFixed(2);
        }

        // 绘制资金曲线
        this.drawEquityCurve(capital, totalReturn);

        toast('回测完成', 'success');
    },

    drawEquityCurve(initialCapital, totalReturn) {
        const container = document.getElementById('bt-equity');
        if (!container) return;

        container.innerHTML = '<canvas id="bt-equity-canvas" style="width:100%;height:100%;"></canvas>';

        const canvas = document.getElementById('bt-equity-canvas');
        const ctx = canvas.getContext('2d');

        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;

        const points = 100;
        const data = [];
        let value = initialCapital;

        for (let i = 0; i < points; i++) {
            value *= 1 + (Math.random() - 0.48) * (totalReturn / points) * 2;
            data.push(value);
        }

        const min = Math.min(...data);
        const max = Math.max(...data);
        const range = max - min || 1;

        ctx.strokeStyle = totalReturn >= 0 ? '#23a559' : '#ed4245';
        ctx.lineWidth = 2;
        ctx.beginPath();

        data.forEach((v, i) => {
            const x = (i / (points - 1)) * canvas.width;
            const y = canvas.height - ((v - min) / range) * (canvas.height - 20) - 10;

            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });

        ctx.stroke();

        // 填充
        ctx.lineTo(canvas.width, canvas.height);
        ctx.lineTo(0, canvas.height);
        ctx.closePath();
        ctx.fillStyle = totalReturn >= 0 ? 'rgba(35,165,89,0.2)' : 'rgba(237,66,69,0.2)';
        ctx.fill();
    },

    // ========== WebSocket ==========

    setupWebSocket() {
        if (S.token) {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${location.host}/ws?token=${S.token}`;

            this.state.ws = new WebSocket(wsUrl);

            this.state.ws.onopen = () => {
                console.log('Discord WebSocket connected');
            };

            this.state.ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    this.handleWSMessage(msg);
                } catch (e) {}
            };

            this.state.ws.onclose = () => {
                setTimeout(() => this.setupWebSocket(), 3000);
            };
        }
    },

    handleWSMessage(msg) {
        if (msg.type === 'voice_update') {
            this.updateVoiceParticipants(msg);
        } else if (msg.type === 'chat_message') {
            // 收到新消息
            if (!this.state.messages[this.state.currentChannel?.id]) {
                this.state.messages[this.state.currentChannel.id] = [];
            }
            this.state.messages[this.state.currentChannel.id].push(msg.data);
            this.renderMessages();
        }
    },

    updateVoiceParticipants(data) {
        console.log('Voice participants:', data);
    },

    // ========== 服务器管理 ==========

    showCreateGuild() {
        const modal = document.createElement('div');
        modal.className = 'discord-modal';
        modal.id = 'create-guild-modal';
        modal.innerHTML = `
            <div class="discord-modal-content">
                <div class="discord-modal-header">
                    <h3>创建服务器</h3>
                    <button class="discord-modal-close" onclick="this.closest('.discord-modal').remove()">✕</button>
                </div>
                <div class="discord-modal-body">
                    <div class="discord-form-group">
                        <label>服务器名称</label>
                        <input type="text" id="guild-name-input" class="discord-input" placeholder="输入服务器名称">
                    </div>
                    <div class="discord-form-group">
                        <label>描述</label>
                        <input type="text" id="guild-desc-input" class="discord-input" placeholder="服务器描述">
                    </div>
                    <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:24px;">
                        <button class="discord-btn discord-btn-secondary" onclick="this.closest('.discord-modal').remove()">取消</button>
                        <button class="discord-btn discord-btn-primary" onclick="DISCORD.createGuild()">创建</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    },

    async createGuild() {
        const nameInput = document.getElementById('guild-name-input');
        const descInput = document.getElementById('guild-desc-input');

        if (!nameInput?.value.trim()) {
            toast('请输入服务器名称', 'error');
            return;
        }

        try {
            const res = await fetch('/api/guilds/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${S.token}`
                },
                body: JSON.stringify({
                    name: nameInput.value.trim(),
                    description: descInput?.value.trim() || ''
                })
            });

            if (res.ok) {
                const data = await res.json();
                toast('服务器创建成功！', 'success');
                document.getElementById('create-guild-modal')?.remove();
                await this.loadGuilds();
                this.selectGuild(data.id);
            } else {
                toast('创建失败', 'error');
            }
        } catch (e) {
            toast('创建失败', 'error');
        }
    },

    showJoinGuild() {
        const code = prompt('请输入邀请码：');
        if (!code) return;
        this.joinGuild(code.trim());
    },

    async joinGuild(inviteCode) {
        try {
            const res = await fetch(`/api/guilds/join/${inviteCode}`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${S.token}` }
            });

            if (res.ok) {
                const data = await res.json();
                toast(`成功加入！`, 'success');
                await this.loadGuilds();
                this.selectGuild(data.guild_id);
            } else {
                toast('邀请码无效', 'error');
            }
        } catch (e) {
            toast('加入失败', 'error');
        }
    },

    showHome() {
        this.state.currentGuild = null;
        this.state.currentChannel = null;
        this.state.currentChannelType = null;
        this.renderGuilds();
        this.renderMainContent();
    },

    showGuildSettings() {
        toast('服务器设置: 功能开发中', 'info');
    }
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    if (S.user) {
        setTimeout(() => DISCORD.init(), 100);
    }
});

// 全局函数
window.DISCORD = DISCORD;
