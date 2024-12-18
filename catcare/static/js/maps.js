function initializeMap(containerId, lat, lon, interactive = true) {
    const mapOptions = {
        zoomControl: interactive,
        dragging: interactive,
        touchZoom: interactive
    };
    
    const map = L.map(containerId, mapOptions).setView([lat, lon], 13);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    L.marker([lat, lon]).addTo(map);
    
    if (interactive) {
        document.getElementById(containerId).addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }
    
    return map;
}