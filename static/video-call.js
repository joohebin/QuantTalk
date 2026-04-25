// QuantTalk 视频通话模块 v3.0

// TURN 服务器配置
const TURN_CONFIG = {
    urls: 'turn:18.183.23.89:3478',
    username: 'quanttalk',
    credential: 'QuantTalk2024Turn'
};

const STUN_CONFIG = {
    urls: 'stun:18.183.23.89:3478'
};

// 全局状态
const VC = {
    ws: null,
    roomId: null,
    localStream: null,
    peerConnections: {},  // peerId -> RTCPeerConnection
    remoteStreams: {},     // peerId -> MediaStream
    participants: {},      // userId -> {username, muted, video_on}
    muted: false,
    videoOff: false,
    isHost: false
};

// 打开视频通话模态框
function showVideoCallModal() {
    const modal = document.getElementById('modal');
    const body = document.getElementById('modal-body');

    body.innerHTML = `
        <div class="video-call-modal">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-semibold">视频通话</h3>
                <button onclick="closeModal()" class="text-gray-400 hover:text-white">✕</button>
            </div>

            <!-- 创建/加入房间 -->
            <div id="vc-start" class="space-y-3">
                <div class="input-group">
                    <label class="text-sm text-gray-400">房间 ID</label>
                    <input type="text" id="vc-room-id" class="input" placeholder="输入房间ID或留空创建新房间">
                </div>
                <button onclick="VC.start()" class="btn btn-primary w-full">开始通话</button>
            </div>

            <!-- 通话中界面 -->
            <div id="vc-active" class="hidden">
                <div class="mb-3 text-center">
                    <span class="text-sm text-green-400">● 通话中</span>
                    <span class="text-sm text-gray-500 ml-2">房间: <span id="vc-current-room"></span></span>
                </div>

                <!-- 视频网格 -->
                <div id="vc-video-grid" class="video-grid mb-4">
                    <!-- 本地视频 -->
                    <div class="video-container" id="vc-local-container">
                        <video id="vc-local-video" autoplay muted playsinline></video>
                        <div class="video-label" id="vc-local-name">你</div>
                    </div>
                </div>

                <!-- 控制栏 -->
                <div class="vc-controls flex justify-center gap-3">
                    <button onclick="VC.toggleMute()" id="vc-mute-btn" class="btn btn-ghost text-2xl" title="静音">🎤</button>
                    <button onclick="VC.toggleVideo()" id="vc-video-btn" class="btn btn-ghost text-2xl" title="开关摄像头">📹</button>
                    <button onclick="VC.shareScreen()" class="btn btn-ghost text-2xl" title="共享屏幕">🖥️</button>
                    <button onclick="VC.end()" class="btn btn-danger text-2xl" title="结束通话">📞</button>
                </div>

                <!-- 参与者和聊天 -->
                <div class="mt-4 grid grid-cols-2 gap-3">
                    <div>
                        <div class="text-sm text-gray-400 mb-2">参与者 (<span id="vc-participant-count">0</span>)</div>
                        <div id="vc-participants" class="text-xs text-gray-300 max-h-24 overflow-y-auto"></div>
                    </div>
                    <div>
                        <div class="text-sm text-gray-400 mb-2">文字聊天</div>
                        <div id="vc-chat" class="text-xs text-gray-300 max-h-24 overflow-y-auto border border-gray-700 rounded p-2"></div>
                        <div class="flex gap-1 mt-1">
                            <input type="text" id="vc-chat-input" class="input flex-1 text-xs py-1" placeholder="发送消息..." onkeypress="if(event.key==='Enter')VC.sendChat()">
                            <button onclick="VC.sendChat()" class="btn btn-ghost text-xs py-1">发送</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <style>
            .video-call-modal { min-width: 400px; }
            .video-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 8px;
                min-height: 200px;
            }
            .video-container {
                position: relative;
                background: #1a1a2e;
                border-radius: 8px;
                overflow: hidden;
                aspect-ratio: 16/9;
            }
            .video-container video {
                width: 100%;
                height: 100%;
                object-fit: cover;
            }
            .video-container.local video {
                transform: scaleX(-1);
            }
            .video-label {
                position: absolute;
                bottom: 4px;
                left: 4px;
                background: rgba(0,0,0,0.6);
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 11px;
            }
            .vc-controls button {
                width: 48px;
                height: 48px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .vc-controls button.active {
                background: rgba(239, 68, 68, 0.2);
                border-color: #ef4444;
            }
        </style>
    `;

    modal.style.display = 'flex';
}

// 检测是否为 HTTPS
function isSecureContext() {
    return location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1';
}

// 获取用户友好的错误信息
function getMediaErrorMessage(err) {
    const name = err.name || '';
    const message = err.message || '';
    
    // NotAllowedError - 用户拒绝或权限未授予
    if (name === 'NotAllowedError' || message.includes('Permission denied') || message.includes('Permission denied')) {
        if (!isSecureContext()) {
            return '当前页面不安全（HTTP），请使用 HTTPS 访问才能使用摄像头/麦克风';
        }
        return '摄像头/麦克风权限被拒绝，请在浏览器设置中允许访问';
    }
    
    // NotFoundError - 没有找到设备
    if (name === 'NotFoundError' || message.includes('DevicesNotFoundError')) {
        return '未检测到摄像头或麦克风设备';
    }
    
    // NotReadableError - 设备被占用
    if (name === 'NotReadableError' || message.includes('NotReadableError')) {
        return '摄像头/麦克风被其他应用占用';
    }
    
    // OverconstrainedError - 设备不支持请求的参数
    if (name === 'OverconstrainedError') {
        return '摄像头不支持请求的画质设置';
    }
    
    // HTTP 环境
    if (!isSecureContext()) {
        return 'HTTP 页面无法访问摄像头，请使用 HTTPS 访问';
    }
    
    return '无法访问摄像头/麦克风: ' + (message || '未知错误');
}

// 开始视频通话
VC.start = async function() {
    // 检查是否为安全上下文
    if (!isSecureContext()) {
        toast('请使用 HTTPS 访问此页面以使用视频通话功能', 'error');
        // 显示 HTTPS 提示
        document.getElementById('modal-body').innerHTML = `
            <div class="text-center py-8">
                <div class="text-5xl mb-4">🔒</div>
                <h3 class="text-lg font-semibold mb-3">需要 HTTPS</h3>
                <p class="text-gray-400 text-sm mb-4">
                    视频通话需要安全连接（HTTPS）才能访问摄像头和麦克风。
                </p>
                <p class="text-xs text-gray-500 mb-4">
                    当前地址: ${location.href}
                </p>
                <p class="text-xs text-yellow-400">
                    请使用 <span class="font-mono">https://</span> 开头访问
                </p>
                <button onclick="closeModal()" class="btn btn-ghost mt-4">关闭</button>
            </div>
        `;
        return;
    }
    
    const roomIdInput = document.getElementById('vc-room-id');
    const roomId = roomIdInput.value.trim() || 'room_' + Date.now();

    VC.roomId = roomId;
    document.getElementById('vc-current-room').textContent = roomId;
    document.getElementById('vc-start').classList.add('hidden');
    document.getElementById('vc-active').classList.remove('hidden');

    // 获取本地媒体
    try {
        VC.localStream = await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: true
        });
        document.getElementById('vc-local-video').srcObject = VC.localStream;
    } catch (err) {
        console.error('Failed to get media:', err);
        toast(getMediaErrorMessage(err), 'error');
        // 显示错误提示界面
        document.getElementById('vc-video-grid').innerHTML = `
            <div class="col-span-2 text-center py-8">
                <div class="text-4xl mb-3">📷</div>
                <p class="text-gray-400 text-sm">${getMediaErrorMessage(err)}</p>
                <button onclick="VC.end()" class="btn btn-ghost mt-4">返回</button>
            </div>
        `;
        return;
    }

    // 连接信令服务器
    VC.connectSignaling();
};

// 连接 WebSocket 信令服务器
VC.connectSignaling = function() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/ws/room/${VC.roomId}?token=${S.token}`;

    VC.ws = new WebSocket(wsUrl);

    VC.ws.onopen = function() {
        console.log('Signaling connected');
        toast('已连接到通话房间', 'success');
    };

    VC.ws.onmessage = function(event) {
        const msg = JSON.parse(event.data);
        VC.handleMessage(msg);
    };

    VC.ws.onclose = function() {
        console.log('Signaling disconnected');
        toast('通话连接已断开', 'error');
    };

    VC.ws.onerror = function(err) {
        console.error('WebSocket error:', err);
    };
};

// 处理信令消息
VC.handleMessage = async function(msg) {
    switch (msg.type) {
        case 'room_joined':
            // 加入房间成功
            console.log('[WebRTC] 加入房间成功，收到已有参与者:', msg.participants);
            VC.participants = {};
            msg.participants.forEach(p => {
                VC.participants[p.user_id] = p;
                VC.updateParticipantsUI();
                // 向每个已有参与者发起连接
                VC.createPeerConnection(p.user_id, true);
            });
            break;

        case 'user_joined':
            // 新用户加入
            VC.participants[msg.user_id] = { username: msg.username, muted: false, video_on: true };
            VC.updateParticipantsUI();
            toast(`${msg.username} 加入了通话`, 'info');
            // 向新加入的用户发起连接
            VC.createPeerConnection(msg.user_id, true);
            break;

        case 'user_left':
            // 用户离开
            if (msg.user_id in VC.participants) {
                delete VC.participants[msg.user_id];
            }
            // 关闭对应的 peer connection
            if (VC.peerConnections[msg.user_id]) {
                VC.peerConnections[msg.user_id].close();
                delete VC.peerConnections[msg.user_id];
            }
            // 移除视频元素
            const remoteEl = document.getElementById(`vc-remote-${msg.user_id}`);
            if (remoteEl) remoteEl.remove();
            VC.updateParticipantsUI();
            toast(`${msg.username} 离开了通话`, 'info');
            break;

        case 'offer':
            // 收到 offer，需要回复 answer
            await VC.handleOffer(msg.from, msg.sdp);
            break;

        case 'answer':
            // 收到 answer
            await VC.handleAnswer(msg.from, msg.sdp);
            break;

        case 'ice_candidate':
            // 收到 ICE candidate
            await VC.handleIceCandidate(msg.from, msg.candidate);
            break;

        case 'participant_updated':
            // 参与者状态更新
            if (VC.participants[msg.user_id]) {
                if (msg.muted !== undefined) VC.participants[msg.user_id].muted = msg.muted;
                if (msg.video_on !== undefined) VC.participants[msg.user_id].video_on = msg.video_on;
                VC.updateParticipantsUI();
            }
            break;

        case 'chat':
            VC.addChatMessage(msg.from_username, msg.content);
            break;

        case 'error':
            toast(msg.message, 'error');
            break;
    }
};

// 创建 peer connection
VC.createPeerConnection = async function(peerId, isInitiator) {
    console.log('[WebRTC] 创建 PeerConnection:', { peerId, isInitiator });
    
    const pc = new RTCPeerConnection({
        iceServers: [STUN_CONFIG, TURN_CONFIG]
    });

    VC.peerConnections[peerId] = pc;
    console.log('[WebRTC] PeerConnection 已创建');

    // 添加本地轨道
    VC.localStream.getTracks().forEach(track => {
        pc.addTrack(track, VC.localStream);
    });

    // 处理 ICE candidate
    pc.onicecandidate = function(event) {
        console.log('[WebRTC] ICE candidate:', event.candidate);
        if (event.candidate) {
            VC.ws.send(JSON.stringify({
                type: 'ice_candidate',
                to: peerId,
                candidate: event.candidate
            }));
        }
    };

    // 处理远程轨道
    pc.ontrack = function(event) {
        console.log('[WebRTC] 收到远程轨道:', peerId, event.streams);
        VC.remoteStreams[peerId] = event.streams[0];
        VC.addRemoteVideo(peerId, event.streams[0]);
    };

    // 连接状态变化
    pc.onconnectionstatechange = function() {
        console.log(`[WebRTC] Peer ${peerId} connection state:`, pc.connectionState);
    };

    // ICE 连接状态
    pc.oniceconnectionstatechange = function() {
        console.log(`[WebRTC] Peer ${peerId} ICE state:`, pc.iceConnectionState);
    };

    if (isInitiator) {
        // 发起者创建 offer
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        VC.ws.send(JSON.stringify({
            type: 'offer',
            to: peerId,
            sdp: pc.localDescription
        }));
    }

    return pc;
};

// 处理 offer
VC.handleOffer = async function(from, sdp) {
    console.log('[WebRTC] 收到 Offer from:', from);
    // 如果还没有 peer connection，先创建
    if (!VC.peerConnections[from]) {
        await VC.createPeerConnection(from, false);
    }
    const pc = VC.peerConnections[from];
    await pc.setRemoteDescription(new RTCSessionDescription(sdp));
    const answer = await pc.createAnswer();
    await pc.setLocalDescription(answer);
    VC.ws.send(JSON.stringify({
        type: 'answer',
        to: from,
        sdp: pc.localDescription
    }));
    console.log('[WebRTC] 已发送 Answer to:', from);
};

// 处理 answer
VC.handleAnswer = async function(from, sdp) {
    console.log('[WebRTC] 收到 Answer from:', from);
    const pc = VC.peerConnections[from];
    if (pc) {
        await pc.setRemoteDescription(new RTCSessionDescription(sdp));
    }
};

// 处理 ICE candidate
VC.handleIceCandidate = async function(from, candidate) {
    console.log('[WebRTC] 收到 ICE candidate from:', from, candidate);
    const pc = VC.peerConnections[from];
    if (pc && candidate) {
        try {
            await pc.addIceCandidate(new RTCIceCandidate(candidate));
        } catch (err) {
            console.error('[WebRTC] Error adding ICE candidate:', err);
        }
    }
};

// 添加远程视频
VC.addRemoteVideo = function(peerId, stream) {
    const grid = document.getElementById('vc-video-grid');
    const container = document.createElement('div');
    container.id = `vc-remote-${peerId}`;
    container.className = 'video-container';
    container.innerHTML = `
        <video id="vc-video-${peerId}" autoplay playsinline></video>
        <div class="video-label" id="vc-name-${peerId}">${VC.participants[peerId]?.username || 'User' + peerId}</div>
    `;
    grid.appendChild(container);
    document.getElementById(`vc-video-${peerId}`).srcObject = stream;
};

// 更新参与者 UI
VC.updateParticipantsUI = function() {
    const container = document.getElementById('vc-participants');
    const count = document.getElementById('vc-participant-count');
    count.textContent = Object.keys(VC.participants).length;

    if (container) {
        container.innerHTML = Object.entries(VC.participants).map(([id, p]) => `
            <div class="flex items-center gap-2 py-1">
                <span class="w-2 h-2 rounded-full ${p.muted ? 'bg-red-500' : 'bg-green-500'}"></span>
                <span>${p.username}</span>
                ${!p.video_on ? '📷✕' : ''}
            </div>
        `).join('') + `
            <div class="flex items-center gap-2 py-1">
                <span class="w-2 h-2 rounded-full ${VC.muted ? 'bg-red-500' : 'bg-green-500'}"></span>
                <span>${S.user?.username} (你)</span>
            </div>
        `;
    }
};

// 切换静音
VC.toggleMute = function() {
    VC.muted = !VC.muted;
    VC.localStream.getAudioTracks().forEach(track => {
        track.enabled = !VC.muted;
    });
    const btn = document.getElementById('vc-mute-btn');
    btn.textContent = VC.muted ? '🔇' : '🎤';
    btn.classList.toggle('active', VC.muted);
    VC.ws?.send(JSON.stringify({ type: 'mute', muted: VC.muted }));
};

// 切换视频
VC.toggleVideo = function() {
    VC.videoOff = !VC.videoOff;
    VC.localStream.getVideoTracks().forEach(track => {
        track.enabled = !VC.videoOff;
    });
    const btn = document.getElementById('vc-video-btn');
    btn.textContent = VC.videoOff ? '📹✕' : '📹';
    btn.classList.toggle('active', VC.videoOff);
    VC.ws?.send(JSON.stringify({ type: 'video_toggle', video_on: !VC.videoOff }));
};

// 共享屏幕
VC.shareScreen = async function() {
    // 检查 HTTPS
    if (!isSecureContext()) {
        toast('屏幕共享需要 HTTPS 连接', 'error');
        return;
    }
    
    try {
        const screenStream = await navigator.mediaDevices.getDisplayMedia({
            video: true,
            audio: false
        });

        // 替换视频轨道
        const videoTrack = screenStream.getVideoTracks()[0];
        const sender = Object.values(VC.peerConnections)[0]?.getSenders().find(s => s.track?.kind === 'video');

        if (sender) {
            sender.replaceTrack(videoTrack);
        }

        // 更新本地视频
        document.getElementById('vc-local-video').srcObject = screenStream;
        toast('屏幕共享已开启', 'success');

        // 屏幕共享结束时
        videoTrack.onended = function() {
            VC.toggleVideo();
            VC.toggleVideo();
            toast('屏幕共享已结束', 'info');
        };
    } catch (err) {
        console.error('Screen share failed:', err);
        if (err.name === 'NotAllowedError') {
            toast('屏幕共享被拒绝或用户取消了操作', 'error');
        } else {
            toast('屏幕共享失败', 'error');
        }
    }
};

// 发送聊天消息
VC.sendChat = function() {
    const input = document.getElementById('vc-chat-input');
    const content = input.value.trim();
    if (!content) return;

    VC.ws?.send(JSON.stringify({
        type: 'chat',
        content: content
    }));
    input.value = '';
    VC.addChatMessage(S.user?.username || '你', content, true);
};

// 添加聊天消息
VC.addChatMessage = function(username, content, isSelf = false) {
    const container = document.getElementById('vc-chat');
    if (!container) return;

    const msg = document.createElement('div');
    msg.className = isSelf ? 'text-sky-400' : 'text-gray-300';
    msg.innerHTML = `<strong>${username}:</strong> ${esc(content)}`;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
};

// 结束通话
VC.end = function() {
    // 关闭所有 peer connections
    Object.values(VC.peerConnections).forEach(pc => pc.close());
    VC.peerConnections = {};

    // 停止本地媒体
    VC.localStream?.getTracks().forEach(track => track.stop());

    // 关闭 WebSocket
    VC.ws?.close();

    // 重置状态
    VC.localStream = null;
    VC.participants = {};
    VC.roomId = null;
    VC.ws = null;

    // 关闭模态框
    closeModal();
    toast('通话已结束', 'info');
};

// 在导航栏添加视频通话按钮
function addVideoCallButton() {
    const navRight = document.getElementById('nav-right');
    if (navRight && S.user) {
        const btn = document.createElement('button');
        btn.className = 'p-2 rounded-lg hover:bg-white/5 transition text-gray-400';
        btn.innerHTML = '📹';
        btn.title = '视频通话';
        btn.onclick = showVideoCallModal;
        navRight.appendChild(btn);
    }
}

// 在页面加载后添加按钮
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(addVideoCallButton, 500);
});

// 每次渲染导航后重新添加
const originalRenderNav = window.renderNav;
if (originalRenderNav) {
    window.renderNav = function() {
        originalRenderNav();
        addVideoCallButton();
    };
}

console.log('Video call module loaded');
