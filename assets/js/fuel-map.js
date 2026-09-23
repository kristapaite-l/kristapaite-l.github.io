// Define geographic boundaries for the UK to prevent zooming out into the world
const ukBounds = L.latLngBounds(
  L.latLng(49.8, -8.5), // South West
  L.latLng(60.9, 1.8)   // North East
);

// Initialize map limited to UK bounds
const map = L.map('map', {
  maxBounds: ukBounds,
  maxBoundsViscosity: 1.0,
  minZoom: 5
}).setView([54.0, -2.5], 6);

// OpenStreetMap tiles (no API key required)
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 18,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

// Load and parse CSV dataset
Papa.parse('../../data/fuel_prices.csv', {
  download: true,
  header: true,
  skipEmptyLines: true,
  complete: function(results) {
    const bounds = [];

    results.data.forEach(row => {
      const lat = parseFloat(row['forecourts.location.latitude']);
      const lng = parseFloat(row['forecourts.location.longitude']);

      if (!isNaN(lat) && !isNaN(lng)) {
        const name = row['forecourts.trading_name'] || 'Fuel Station';
        const brand = row['forecourts.brand_name'] || '';
        const addr1 = row['forecourts.location.address_line_1'] || '';
        const city = row['forecourts.location.city'] || '';
        const postcode = row['forecourts.location.postcode'] || '';

        const e10 = row['forecourts.fuel_price.E10'] ? `${row['forecourts.fuel_price.E10']}p` : 'N/A';
        const b7s = row['forecourts.fuel_price.B7S'] ? `${row['forecourts.fuel_price.B7S']}p` : 'N/A';

        const is24hr = row['forecourts.amenities.twenty_four_hour_fuel'] === 'true';
        const carWash = row['forecourts.amenities.vehicle_services.car_wash'] === 'true';
        const isSupermarket = row['forecourts.is_supermarket_service_station'] === 'true';

        const popupContent = `
          <div class="popup-container">
            <div class="popup-title">${name}</div>
            <div class="popup-brand">${brand}</div>
            <div class="popup-address">${addr1}${city ? ', ' + city : ''}<br>${postcode}</div>
            
            <div class="price-grid">
              <div class="price-card">
                <div class="price-label">E10 Petrol</div>
                <div class="price-val">${e10}</div>
              </div>
              <div class="price-card">
                <div class="price-label">B7 Diesel</div>
                <div class="price-val">${b7s}</div>
              </div>
            </div>

            <div class="badge-bar">
              ${is24hr ? '<span class="badge">24 Hours</span>' : ''}
              ${carWash ? '<span class="badge">Car Wash</span>' : ''}
              ${isSupermarket ? '<span class="badge">Supermarket</span>' : ''}
            </div>
          </div>
        `;

        L.marker([lat, lng]).addTo(map).bindPopup(popupContent);
        bounds.push([lat, lng]);
      }
    });

    if (bounds.length > 0) {
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }
});

// Postcode Search Functionality
async function searchPostcode() {
  const query = document.getElementById('postcode-input').value.trim();
  if (!query) return;

  try {
    const response = await fetch(`https://api.postcodes.io/postcodes/${encodeURIComponent(query)}`);
    const data = await response.json();

    if (data.status === 200) {
      const { latitude, longitude } = data.result;
      map.setView([latitude, longitude], 13);
    } else {
      alert('Postcode not found. Please enter a valid UK postcode.');
    }
  } catch (error) {
    alert('Error locating postcode. Please try again.');
  }
}