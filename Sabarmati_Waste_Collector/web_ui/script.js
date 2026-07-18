// Function to switch between tabs
function showTab(tabId) {
    // Hide all tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    // Deactivate all buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });

    // Show the selected tab content
    document.getElementById(tabId).classList.add('active');

    // Activate the corresponding button
    document.querySelector(`[onclick="showTab('${tabId}')"]`).classList.add('active');
}

// Function to map command character to full text
function getCommandText(cmd) {
    switch (cmd) {
        case 'F': return 'FORWARD (F)';
        case 'L': return 'LEFT (L)';
        case 'R': return 'RIGHT (R)';
        case 'C': return 'CENTER (C)'; // C is the AI's internal logic for F
        default: return 'STOP (S)';
    }
}

// Function to fetch status data from the FastAPI backend
function fetchStatus() {
    fetch('/status_data')
        .then(response => {
            if (!response.ok) {
                // Handle network error
                document.getElementById('detection-status').textContent = 'Error';
                document.getElementById('detection-status').classList.remove('online');
                document.getElementById('detection-status').classList.add('offline');
                document.getElementById('ui-status').textContent = 'Backend Error';
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            const commandText = getCommandText(data.command);

            // Update Status tab fields
            document.getElementById('espIp').textContent = data.ip;
            document.getElementById('latest-cmd-full').textContent = commandText;
            document.getElementById('detection-count').textContent = data.count;
            document.getElementById('ui-status').textContent = 'Connected';

            // Assume Roboflow is online if data is successfully received
            document.getElementById('detection-status').textContent = 'Online';
            document.getElementById('detection-status').classList.remove('offline');
            document.getElementById('detection-status').classList.add('online');
        })
        .catch(error => {
            // This runs if the fetch fails (Backend is down)
            document.getElementById('ui-status').textContent = 'Offline';
            document.getElementById('detection-status').textContent = 'Offline';
            document.getElementById('detection-status').classList.remove('online');
            document.getElementById('detection-status').classList.add('offline');
            console.error('Error fetching status:', error);
        });
}

// Initialize the dashboard on load
document.addEventListener('DOMContentLoaded', () => {
    // Start with the Video Feed tab active
    showTab('feed'); 

    // Fetch status data every 300 milliseconds
    setInterval(fetchStatus, 300); 
});