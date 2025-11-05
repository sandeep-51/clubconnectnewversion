class MeetingRoom {
    constructor(meetingId, userName, currentUserId) {
        this.meetingId = meetingId;
        this.userName = userName;
        this.currentUserId = currentUserId;
        this.localStream = null;
        this.peerConnections = {};
        this.remoteVideos = {};
        this.participants = new Set();
        this.pendingIceCandidates = {};
        
        this.videoEnabled = true;
        this.audioEnabled = true;
        
        // WebRTC configuration
        this.rtcConfiguration = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' }
            ]
        };
        
        this.initializeMediaDevices();
        this.setupEventListeners();
        this.startSignaling();
    }
    
    async initializeMediaDevices() {
        try {
            this.localStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                },
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            
            const localVideo = document.getElementById('local-video');
            if (localVideo) {
                localVideo.srcObject = this.localStream;
                localVideo.muted = true;
            }
            
            this.updateMediaStatus();
            this.showNotification('Camera and microphone connected', 'success');
        } catch (error) {
            console.error('Error accessing media devices:', error);
            this.showNotification('Could not access camera/microphone. Please check permissions.', 'error');
        }
    }
    
    setupEventListeners() {
        const toggleVideoBtn = document.getElementById('toggle-video');
        const toggleAudioBtn = document.getElementById('toggle-audio');
        const endCallBtn = document.getElementById('end-call');
        const shareScreenBtn = document.getElementById('share-screen');
        
        if (toggleVideoBtn) {
            toggleVideoBtn.addEventListener('click', () => this.toggleVideo());
        }
        
        if (toggleAudioBtn) {
            toggleAudioBtn.addEventListener('click', () => this.toggleAudio());
        }
        
        if (endCallBtn) {
            endCallBtn.addEventListener('click', () => this.endCall());
        }
        
        if (shareScreenBtn) {
            shareScreenBtn.addEventListener('click', () => this.shareScreen());
        }
    }
    
    async startSignaling() {
        // Poll for signals every 1 second
        this.signalingInterval = setInterval(() => this.checkForSignals(), 1000);
    }
    
    async checkForSignals() {
        try {
            const response = await fetch(`/clubs/meeting/${this.meetingId}/webrtc/signals/`);
            const data = await response.json();
            
            if (data.status === 'success') {
                // Process signals first
                for (const signal of data.signals) {
                    await this.handleSignal(signal);
                }
                
                // Update participants list
                this.updateParticipantsList(data.participants);
                
                // Create peer connections for new participants
                // Only initiate offer if current user ID is lower (avoids glare)
                for (const participant of data.participants) {
                    if (!this.peerConnections[participant.id]) {
                        const shouldOffer = parseInt(this.currentUserId) < parseInt(participant.id);
                        await this.createPeerConnection(participant.id, participant.name, shouldOffer);
                    }
                }
            }
        } catch (error) {
            console.error('Error checking for signals:', error);
        }
    }
    
    async createPeerConnection(peerId, peerName, shouldOffer = true) {
        const pc = new RTCPeerConnection(this.rtcConfiguration);
        this.peerConnections[peerId] = pc;
        
        // Add local stream to peer connection
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => {
                pc.addTrack(track, this.localStream);
            });
        }
        
        // Handle incoming stream
        pc.ontrack = (event) => {
            console.log('Received remote track from', peerId);
            this.handleRemoteTrack(peerId, peerName, event.streams[0]);
        };
        
        // Handle ICE candidates
        pc.onicecandidate = (event) => {
            if (event.candidate) {
                this.sendSignal('ice-candidate', {
                    candidate: event.candidate
                }, peerId);
            }
        };
        
        // Handle connection state changes
        pc.onconnectionstatechange = () => {
            console.log(`Connection state with ${peerId}:`, pc.connectionState);
            if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
                this.removePeerConnection(peerId);
            }
        };
        
        // Only create and send offer if we should (glare avoidance)
        if (shouldOffer) {
            const offer = await pc.createOffer();
            await pc.setLocalDescription(offer);
            
            this.sendSignal('offer', {
                sdp: offer.sdp,
                type: offer.type
            }, peerId);
        }
    }
    
    async handleSignal(signal) {
        const {sender_id, sender_name, type, data} = signal;
        
        if (!this.peerConnections[sender_id]) {
            // Create peer connection if it doesn't exist
            await this.createPeerConnectionForSignal(sender_id, sender_name);
        }
        
        const pc = this.peerConnections[sender_id];
        
        try {
            if (type === 'offer') {
                console.log(`Received offer from ${sender_id}`);
                await pc.setRemoteDescription(new RTCSessionDescription(data));
                const answer = await pc.createAnswer();
                await pc.setLocalDescription(answer);
                
                this.sendSignal('answer', {
                    sdp: answer.sdp,
                    type: answer.type
                }, sender_id);
                console.log(`Sent answer to ${sender_id}`);
                
            } else if (type === 'answer') {
                console.log(`Received answer from ${sender_id}`);
                await pc.setRemoteDescription(new RTCSessionDescription(data));
                
            } else if (type === 'ice-candidate') {
                if (pc.remoteDescription) {
                    await pc.addIceCandidate(new RTCIceCandidate(data.candidate));
                } else {
                    // Queue ICE candidate if remote description not set yet
                    if (!this.pendingIceCandidates) {
                        this.pendingIceCandidates = {};
                    }
                    if (!this.pendingIceCandidates[sender_id]) {
                        this.pendingIceCandidates[sender_id] = [];
                    }
                    this.pendingIceCandidates[sender_id].push(data.candidate);
                }
            }
        } catch (error) {
            console.error('Error handling signal:', error);
        }
    }
    
    async createPeerConnectionForSignal(peerId, peerName) {
        const pc = new RTCPeerConnection(this.rtcConfiguration);
        this.peerConnections[peerId] = pc;
        
        // Add local stream to peer connection
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => {
                pc.addTrack(track, this.localStream);
            });
        }
        
        // Handle incoming stream
        pc.ontrack = (event) => {
            console.log('Received remote track from', peerId);
            this.handleRemoteTrack(peerId, peerName, event.streams[0]);
        };
        
        // Handle ICE candidates
        pc.onicecandidate = (event) => {
            if (event.candidate) {
                this.sendSignal('ice-candidate', {
                    candidate: event.candidate
                }, peerId);
            }
        };
        
        // Handle connection state changes
        pc.onconnectionstatechange = () => {
            console.log(`Connection state with ${peerId}:`, pc.connectionState);
            if (pc.connectionState === 'connected') {
                // Process any pending ICE candidates
                if (this.pendingIceCandidates && this.pendingIceCandidates[peerId]) {
                    this.pendingIceCandidates[peerId].forEach(async (candidate) => {
                        try {
                            await pc.addIceCandidate(new RTCIceCandidate(candidate));
                        } catch (e) {
                            console.error('Error adding pending ICE candidate:', e);
                        }
                    });
                    delete this.pendingIceCandidates[peerId];
                }
            } else if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
                this.removePeerConnection(peerId);
            }
        };
    }
    
    handleRemoteTrack(peerId, peerName, stream) {
        // Remove old video if exists
        if (this.remoteVideos[peerId]) {
            this.remoteVideos[peerId].remove();
        }
        
        // Create video element for remote stream
        const videoGrid = document.querySelector('.video-grid');
        const remoteVideoContainer = document.createElement('div');
        remoteVideoContainer.className = 'position-relative';
        remoteVideoContainer.style.cssText = 'width: 50%; height: 50%; float: left;';
        
        const remoteVideo = document.createElement('video');
        remoteVideo.id = `remote-video-${peerId}`;
        remoteVideo.autoplay = true;
        remoteVideo.playsInline = true;
        remoteVideo.srcObject = stream;
        remoteVideo.style.cssText = 'width: 100%; height: 100%; object-fit: cover;';
        
        const nameLabel = document.createElement('div');
        nameLabel.className = 'position-absolute bottom-0 start-0 p-2 bg-dark bg-opacity-75 m-3 rounded';
        nameLabel.innerHTML = `<small>${peerName}</small>`;
        
        remoteVideoContainer.appendChild(remoteVideo);
        remoteVideoContainer.appendChild(nameLabel);
        videoGrid.appendChild(remoteVideoContainer);
        
        this.remoteVideos[peerId] = remoteVideoContainer;
    }
    
    removePeerConnection(peerId) {
        if (this.peerConnections[peerId]) {
            this.peerConnections[peerId].close();
            delete this.peerConnections[peerId];
        }
        
        if (this.remoteVideos[peerId]) {
            this.remoteVideos[peerId].remove();
            delete this.remoteVideos[peerId];
        }
    }
    
    async sendSignal(type, data, receiverId) {
        try {
            await fetch('/clubs/meeting/webrtc/signal/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCookie('csrftoken')
                },
                body: JSON.stringify({
                    meeting_id: this.meetingId,
                    type: type,
                    data: data,
                    receiver_id: receiverId
                })
            });
        } catch (error) {
            console.error('Error sending signal:', error);
        }
    }
    
    toggleVideo() {
        if (this.localStream) {
            const videoTrack = this.localStream.getVideoTracks()[0];
            if (videoTrack) {
                this.videoEnabled = !this.videoEnabled;
                videoTrack.enabled = this.videoEnabled;
                this.updateMediaStatus();
                
                const btn = document.getElementById('toggle-video');
                const icon = btn.querySelector('i');
                if (this.videoEnabled) {
                    btn.classList.remove('btn-danger');
                    btn.classList.add('btn-secondary');
                    icon.classList.remove('fa-video-slash');
                    icon.classList.add('fa-video');
                } else {
                    btn.classList.remove('btn-secondary');
                    btn.classList.add('btn-danger');
                    icon.classList.remove('fa-video');
                    icon.classList.add('fa-video-slash');
                }
            }
        }
    }
    
    toggleAudio() {
        if (this.localStream) {
            const audioTrack = this.localStream.getAudioTracks()[0];
            if (audioTrack) {
                this.audioEnabled = !this.audioEnabled;
                audioTrack.enabled = this.audioEnabled;
                this.updateMediaStatus();
                
                const btn = document.getElementById('toggle-audio');
                const icon = btn.querySelector('i');
                if (this.audioEnabled) {
                    btn.classList.remove('btn-danger');
                    btn.classList.add('btn-secondary');
                    icon.classList.remove('fa-microphone-slash');
                    icon.classList.add('fa-microphone');
                } else {
                    btn.classList.remove('btn-secondary');
                    btn.classList.add('btn-danger');
                    icon.classList.remove('fa-microphone');
                    icon.classList.add('fa-microphone-slash');
                }
            }
        }
    }
    
    async shareScreen() {
        try {
            const screenStream = await navigator.mediaDevices.getDisplayMedia({
                video: { cursor: 'always' },
                audio: false
            });
            
            const screenTrack = screenStream.getVideoTracks()[0];
            
            // Replace video track in all peer connections
            Object.values(this.peerConnections).forEach(pc => {
                const senders = pc.getSenders();
                const videoSender = senders.find(sender => sender.track && sender.track.kind === 'video');
                if (videoSender) {
                    videoSender.replaceTrack(screenTrack);
                }
            });
            
            const localVideo = document.getElementById('local-video');
            if (localVideo) {
                localVideo.srcObject = screenStream;
            }
            
            screenTrack.onended = () => {
                // Switch back to camera
                const videoTrack = this.localStream.getVideoTracks()[0];
                Object.values(this.peerConnections).forEach(pc => {
                    const senders = pc.getSenders();
                    const videoSender = senders.find(sender => sender.track && sender.track.kind === 'video');
                    if (videoSender) {
                        videoSender.replaceTrack(videoTrack);
                    }
                });
                if (localVideo) {
                    localVideo.srcObject = this.localStream;
                }
            };
            
            this.showNotification('Screen sharing started', 'success');
        } catch (error) {
            console.error('Error sharing screen:', error);
            this.showNotification('Could not share screen', 'error');
        }
    }
    
    endCall() {
        // Stop signaling
        if (this.signalingInterval) {
            clearInterval(this.signalingInterval);
        }
        
        // Stop local stream
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
        }
        
        // Close all peer connections
        Object.keys(this.peerConnections).forEach(peerId => {
            this.removePeerConnection(peerId);
        });
        
        // Go back
        window.location.href = document.referrer || '/dashboard/';
    }
    
    updateMediaStatus() {
        const statusDiv = document.getElementById('media-status');
        if (statusDiv) {
            const videoStatus = this.videoEnabled ? 
                '<i class="fas fa-video text-success"></i> Video On' : 
                '<i class="fas fa-video-slash text-danger"></i> Video Off';
            const audioStatus = this.audioEnabled ? 
                '<i class="fas fa-microphone text-success"></i> Audio On' : 
                '<i class="fas fa-microphone-slash text-danger"></i> Audio Off';
            statusDiv.innerHTML = `${videoStatus} | ${audioStatus}`;
        }
    }
    
    showNotification(message, type) {
        const container = document.getElementById('notification-container');
        if (container) {
            const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
            const notification = document.createElement('div');
            notification.className = `alert ${alertClass} alert-dismissible fade show`;
            notification.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            container.appendChild(notification);
            
            setTimeout(() => {
                notification.remove();
            }, 5000);
        }
    }
    
    updateParticipantsList(participants) {
        const listElement = document.getElementById('participants-list');
        if (listElement) {
            // Keep the "You" entry
            const youEntry = listElement.querySelector('li:first-child');
            listElement.innerHTML = '';
            if (youEntry) {
                listElement.appendChild(youEntry);
            }
            
            // Add other participants
            participants.forEach(participant => {
                this.participants.add(participant.id);
                const li = document.createElement('li');
                li.className = 'list-group-item d-flex align-items-center bg-dark text-white border-secondary';
                li.innerHTML = `
                    <div class="avatar me-2">
                        <i class="fas fa-user-circle fa-2x text-primary"></i>
                    </div>
                    <div>
                        <div>${participant.name}</div>
                        <small class="text-success"><i class="fas fa-circle" style="font-size: 8px;"></i> Connected</small>
                    </div>
                `;
                listElement.appendChild(li);
            });
        }
    }
    
    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const meetingContainer = document.getElementById('meeting-container');
    if (meetingContainer) {
        const meetingId = meetingContainer.dataset.meetingId;
        const userName = meetingContainer.dataset.userName;
        const currentUserId = meetingContainer.dataset.currentUserId;
        
        if (meetingId && userName) {
            window.meetingRoom = new MeetingRoom(meetingId, userName, currentUserId);
        }
    }
});
