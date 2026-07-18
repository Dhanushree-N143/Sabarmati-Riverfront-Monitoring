const humanCount = document.getElementById('humanCount');
const dangerCard = document.getElementById('dangerCard');
const dangerText = document.getElementById('dangerText');
const dangerIcon = document.getElementById('dangerIcon');
const logContainer = document.getElementById('logContainer');
const themeToggle = document.getElementById('themeToggle');
const processedFeed = document.getElementById('processedFeed');
const startBtn = document.getElementById('startBtn');
const body = document.body;

// === 1. SOUND SETUP (MP3 File) ===
// This loads your file. Make sure it is named 'alert.mp3'
const alertSound = new Audio('alert.mp3');

function playAlertSound() {
    // Only play if it's not already playing to avoid "echo" spam
    if (alertSound.paused) {
        alertSound.currentTime = 0; // Rewind to start
        alertSound.play().catch(error => {
            console.log("Audio blocked by browser. Click the page to enable.");
        });
    }
}

// === 2. THEME HANDLING ===
if (localStorage.getItem('theme') === 'dark') {
    body.classList.add('dark-mode');
    themeToggle.textContent = 'Light Mode';
}
themeToggle.addEventListener('click', () => {
    body.classList.toggle('dark-mode');
    localStorage.setItem('theme', body.classList.contains('dark-mode') ? 'dark' : 'light');
    themeToggle.textContent = body.classList.contains('dark-mode') ? 'Light Mode' : 'Dark Mode';
});

// === 3. LOGGING ===
function addLog(message, type = 'info') {
    const div = document.createElement('div');
    div.className = `log-entry ${type}`;
    div.innerText = `[${new Date().toLocaleTimeString()}] ${message}`;
    logContainer.appendChild(div);
    logContainer.scrollTop = logContainer.scrollHeight;
}
document.getElementById('clearLogs').addEventListener('click', () => logContainer.innerHTML = '');

// === 4. VIDEO & WEBSOCKET LOGIC ===
let socket;
let video = document.getElementById('sourceVideo');
let canvas = document.getElementById('captureCanvas');
let ctx = canvas.getContext('2d');
let isStreaming = false;
let isBusy = false; 

startBtn.addEventListener('click', async () => {
    try {
        const stream = await navigator.mediaDevices.getDisplayMedia({
            video: { cursor: 'never' }, 
            audio: false
        });
        
        video.srcObject = stream;
        await video.play();
        
        connectWebSocket();
        startBtn.style.display = 'none';
        processedFeed.style.opacity = 1;
        addLog('Connected to Drone Feed.', 'info');

        // Play the sound once silently on click to "Unlock" audio permission
        alertSound.play().then(() => {
            alertSound.pause();
            alertSound.currentTime = 0;
        }).catch(e => console.log("Audio unlock failed"));

        stream.getVideoTracks()[0].onended = () => {
            startBtn.style.display = 'block';
            isStreaming = false;
            addLog('Drone Feed Disconnected.', 'danger');
        };
    } catch (err) {
        console.error('Error:', err);
        addLog('Failed to select source.', 'danger');
    }
});

function connectWebSocket() {
    socket = new WebSocket('ws://localhost:8080/ws');
    
    socket.onopen = () => {
        isStreaming = true;
        isBusy = false;
        sendFrame(); 
        addLog('Geo-Fence Active. Scanning...', 'success');
    };
    
    socket.onmessage = (event) => {
        isBusy = false; 
        const data = JSON.parse(event.data);
        processedFeed.src = data.image;
        humanCount.textContent = data.humans;
        updateDangerStatus(data.danger);
        
        if (isStreaming) requestAnimationFrame(sendFrame);
    };
    
    socket.onclose = () => {
        isStreaming = false;
        addLog('Server Disconnected.', 'danger');
    };
}

function sendFrame() {
    if (!isStreaming || isBusy) return; 
    
    if (video.videoWidth > 0) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const dataURL = canvas.toDataURL('image/jpeg', 0.6);
        
        if (socket.readyState === WebSocket.OPEN) {
            isBusy = true; 
            socket.send(dataURL);
        }
    }
}

// === 5. DANGER & SOUND LOGIC ===
let lastAlertTime = 0;

function updateDangerStatus(isDanger) {
    if (isDanger) {
        dangerCard.classList.add('danger');
        dangerText.textContent = 'BREACH DETECTED';
        dangerIcon.textContent = '🚨';
        
        const now = Date.now();
        // Play sound max once every 3 seconds (so it doesn't overlap weirdly)
        if (now - lastAlertTime > 3000) {
            playAlertSound();
            addLog('⚠️ PERIMETER BREACH!', 'target');
            lastAlertTime = now;
        }
    } else {
        dangerCard.classList.remove('danger');
        dangerText.textContent = 'SECURE';
        dangerIcon.textContent = '🛡️';
    }
}