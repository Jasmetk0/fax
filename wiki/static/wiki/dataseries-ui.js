const DS_PALETTES = {
  Blues: ['#deebf7', '#9ecae1', '#6baed6', '#3182bd', '#08519c'],
};

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.ds-map').forEach(async (el) => {
    const category = el.dataset.category;
    const year = el.dataset.year;
    const paletteName = el.dataset.palette || 'Blues';
    const showLegend = el.dataset.legend === '1';
    const palette = DS_PALETTES[paletteName] || DS_PALETTES.Blues;
    const resp = await fetch(`/api/dataseries/category/${category}/?year=${year}`);
    const data = await resp.json();
    const bySlug = data.by_slug || {};
    const geoResp = await fetch('/static/wiki/geo/countries.geo.json');
    const geo = await geoResp.json();
    const values = Object.values(bySlug).map(parseFloat).filter((v) => !isNaN(v));
    values.sort((a, b) => a - b);
    const quantiles = [];
    for (let i = 1; i <= palette.length; i++) {
      const idx = Math.floor((values.length * i) / palette.length) - 1;
      quantiles.push(values[Math.max(0, idx)] || 0);
    }
    function getColor(v) {
      if (isNaN(v)) return '#ccc';
      for (let i = 0; i < quantiles.length; i++) {
        if (v <= quantiles[i]) return palette[i];
      }
      return palette[palette.length - 1];
    }
    const map = L.map(el).setView([20, 0], 2);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);
    L.geoJSON(geo, {
      style: (feature) => {
        const val = parseFloat(bySlug[feature.properties.slug]);
        return {
          fillColor: getColor(val),
          weight: 1,
          color: '#555',
          fillOpacity: 0.8,
        };
      },
    }).addTo(map);
    if (showLegend) {
      const legend = L.control({ position: 'bottomright' });
      legend.onAdd = function () {
        const div = L.DomUtil.create('div', 'ds-legend');
        let prev = values[0] || 0;
        quantiles.forEach((q, i) => {
          const color = palette[i];
          div.innerHTML += `<i style="background:${color}"></i> ${prev.toFixed(0)}&ndash;${q.toFixed(0)}<br>`;
          prev = q;
        });
        return div;
      };
      legend.addTo(map);
    }
  });
});
