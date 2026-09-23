// Define geographic boundaries for the UK
const ukBounds = L.latLngBounds(
  L.latLng(49.8, -8.5), // South West
  L.latLng(60.9, 1.8)   // North East
);

// Initialize map centered on UK without default markers
const map = L.map('map', {
  maxBounds: ukBounds,
  maxBoundsViscosity: 1.0,
  minZoom: 5
}).setView([54.0, -2.5], 6);

// OpenStreetMap base tiles
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 18,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

// Store raw dataset and active map markers layer group
let allStations = [];
const markerGroup = L.layerGroup().addTo(map);

// Parse CSV once on page load
Papa.parse('../../data/fuel_prices.csv', {
  download: true,
  header: true,
  skipEmptyLines: true,
  complete: function(results) {
    allStations = results.data.filter(row => {
      const lat = parseFloat(row['forecourts.location.latitude']);
      const lng = parseFloat(row['forecourts.location.longitude']);
      return !isNaN(lat) && !isNaN(lng);
    });
  }
});

// Calculate distance in km between two lat/lng points (Haversine formula)
function getDistanceKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
  return R * (2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)));
}

// Format price value safely to 1 decimal place
function formatPrice(val) {
  if (!val || isNaN(val)) return null;
  return parseFloat(val).toFixed(1);
}

// Search location (Postcode or Place Name)
async function searchLocation() {
  const query = document.getElementById('location-input').value.trim();
  if (!query) return;

  let lat, lng;

  // 1. Try UK Postcode lookup first
  try {
    const pcRes = await fetch(`https://api.postcodes.io/postcodes/${encodeURIComponent(query)}`);
    const pcData = await pcRes.json();
    if (pcData.status === 200) {
      lat = pcData.result.latitude;
      lng = pcData.result.longitude;
    }
  } catch (e) {
    // Ignore and fallback to place lookup
  }

  // 2. Fallback to OpenStreetMap Nominatim for town/city names
  if (!lat || !lng) {
    try {
      const geoRes = await fetch(`https://nominatim.openstreetmap.org/search?format=json&countrycodes=gb&q=${encodeURIComponent(query)}`);
      const geoData = await geoRes.json();
      if (geoData && geoData.length > 0) {
        lat = parseFloat(geoData[0].lat);
        lng = parseFloat(geoData[0].lon);
      }
    } catch (e) {
      alert('Search failed. Please try again.');
      return;
    }
  }

  if (!lat || !lng) {
    alert('Location or postcode not found. Please try a valid UK city, town, or postcode.');
    return;
  }

  renderNearbyStations(lat, lng);
}

// Render nearby stations with price annotations and high/low formatting
function renderNearbyStations(centerLat, centerLng) {
  markerGroup.clearLayers();

  // Find stations within ~12km radius of searched location
  const searchRadiusKm = 12;
  const nearby = allStations.map(station => {
    const sLat = parseFloat(station['forecourts.location.latitude']);
    const sLng = parseFloat(station['forecourts.location.longitude']);
    const dist = getDistanceKm(centerLat, centerLng, sLat, sLng);
    const e10Val = parseFloat(station['forecourts.fuel_price.E10']);
    return { ...station, sLat, sLng, dist, e10Val };
  }).filter(s => s.dist <= searchRadiusKm);

  if (nearby.length === 0) {
    alert('No fuel stations found near this location in the dataset.');
    map.setView([centerLat, centerLng], 12);
    return;
  }

  // Calculate high and low E10 prices in local area for conditional formatting
  const validPrices = nearby.map(s => s.e10Val).filter(p => !isNaN(p));
  const minPrice = validPrices.length ? Math.min(...validPrices) : null;
  const maxPrice = validPrices.length ? Math.max(...validPrices) : null;

  const bounds = [];

  nearby.forEach(s => {
    const name = s['forecourts.trading_name'] || 'Fuel Station';
    const brand = s['forecourts.brand_name'] || '';
    const addr1 = s['forecourts.location.address_line_1'] || '';
    const city = s['forecourts.location.city'] || '';
    const postcode = s['forecourts.location.postcode'] || '';

    const e10Formatted = formatPrice(s['forecourts.fuel_price.E10']);
    const b7Formatted = formatPrice(s['forecourts.fuel_price.B7S']);

    const e10Display = e10Formatted ? `${e10Formatted}p` : 'N/A';
    const b7Display = b7Formatted ? `${b7Formatted}p` : 'N/A';

    // Determine conditional color class
    let priceClass = 'price-mid';
    if (s.e10Val && minPrice !== null && maxPrice !== null && minPrice !== maxPrice) {
      if (s.e10Val === minPrice) priceClass = 'price-low';
      else if (s.e10Val === maxPrice) priceClass = 'price-high';
    }

    // Custom map pin icon displaying rounded price
    const customIcon = L.divIcon({
      className: 'custom-price-pin',
      html: `<div class="marker-pill ${priceClass}">${e10Display}</div>`,
      iconSize: [60, 26],
      iconAnchor: [30, 13]
    });

    const is24hr = s['forecourts.amenities.twenty_four_hour_fuel'] === 'true';
    const carWash = s['forecourts.amenities.vehicle_services.car_wash'] === 'true';
    const isSupermarket = s['forecourts.is_supermarket_service_station'] === 'true';

    const popupContent = `
      <div class="popup-container">
        <div class="popup-title">${name}</div>
        <div class="popup-brand">${brand}</div>
        <div class="popup-address">${addr1}${city ? ', ' + city : ''}<br>${postcode}</div>
        
        <div class="price-grid">
          <div class="price-card">
            <div class="price-label">E10 Petrol</div>
            <div class="price-val">${e10Display}</div>
          </div>
          <div class="price-card">
            <div class="price-label">B7 Diesel</div>
            <div class="price-val">${b7Display}</div>
          </div>
        </div>

        <div class="badge-bar">
          ${is24hr ? '<span class="badge">24 Hours</span>' : ''}
          ${carWash ? '<span class="badge">Car Wash</span>' : ''}
          ${isSupermarket ? '<span class="badge">Supermarket</span>' : ''}
        </div>
      </div>
    `;

    L.marker([s.sLat, s.sLng], { icon: customIcon }).addTo(markerGroup).bindPopup(popupContent);
    bounds.push([s.sLat, s.sLng]);
  });

  map.fitBounds(bounds, { padding: [50, 50] });
}