(function () {
  const mapEl = document.getElementById("openfaxmap");
  const styleUrl = mapEl.dataset.styleUrl;
  const baseTiles = L.tileLayer(mapEl.dataset.tileUrl, {
    maxZoom: 19,
    attribution: mapEl.dataset.tileAttribution,
  });
  const map = L.map("openfaxmap", { zoomControl: true }).setView([0, 0], 2);
  const scale = L.control.scale({ metric: true, imperial: false }).addTo(map);
  let geoLayer = null;
  let customUnits = false;
  let unitLabel = localStorage.getItem("ofm.unitLabel") || "phx-km";
  let unitFactor = parseFloat(localStorage.getItem("ofm.unitFactor") || "1000");
  const statusEl = document.getElementById("ofm-status");
  const labelCheckbox = document.getElementById("ofm-labels");
  let labelsEnabled = labelCheckbox.checked;
  const LABEL_ZOOM = 14;
  const labelLayers = [];
  const LARGE_DATASET = 2000;

  function setStatus(msg) {
    statusEl.textContent = msg || "";
  }

  function updateScale() {
    scale._update();
    if (customUnits) {
      const txt = scale._mScale.innerHTML; // e.g. "500 m" or "2 km"
      const parts = txt.split(" ");
      let meters = parseFloat(parts[0]);
      if (parts[1] === "km") meters *= 1000;
      const custom = meters / unitFactor;
      scale._mScale.innerHTML = custom.toFixed(2) + " " + unitLabel;
    }
  }
  map.on("move", updateScale);

  function featureStyle(feature) {
    const tags = feature.properties?.tags || feature.properties || {};
    if (tags.amenity) {
      return {
        color: "#e11d48",
        fillColor: "#fda4af",
        radius: 6,
        weight: 1,
        fillOpacity: 0.8,
      };
    }
    if (tags.place) {
      return {
        color: "#7e22ce",
        fillColor: "#c084fc",
        radius: 5,
        weight: 1,
        fillOpacity: 0.8,
      };
    }
    if (tags.water || tags.natural === "water") {
      return { color: "#3b82f6", fillColor: "#3b82f6", weight: 1, fillOpacity: 0.5 };
    }
    if (tags.highway) {
      return { color: "#f97316", weight: 2 };
    }
    if (tags.building) {
      return { color: "#94a3b8", fillColor: "#cbd5e1", weight: 1, fillOpacity: 0.7 };
    }
    if (tags.landuse || tags.natural) {
      return { color: "#22c55e", fillColor: "#86efac", weight: 1, fillOpacity: 0.5 };
    }
    return { color: "#475569", weight: 1 };
  }

  function onEachFeature(feature, layer) {
    const tags = feature.properties?.tags || feature.properties || {};
    const name = tags.name;
    if (name) {
      layer._ofmName = name;
      labelLayers.push(layer);
    }
  }

  function refreshLabels() {
    const show = labelsEnabled && map.getZoom() >= LABEL_ZOOM;
    labelLayers.forEach((layer) => {
      if (show && !layer.getTooltip()) {
        layer.bindTooltip(layer._ofmName, {
          permanent: true,
          direction: "center",
          className: "ofm-label",
        });
      } else if (!show && layer.getTooltip()) {
        layer.unbindTooltip();
      }
    });
  }

  function loadGeoJSON(data) {
    if (geoLayer) geoLayer.remove();
    labelLayers.length = 0;
    const large = data.features && data.features.length > LARGE_DATASET;
    geoLayer = L.geoJSON(data, {
      style: featureStyle,
      onEachFeature,
      pointToLayer: (feature, latlng) => L.circleMarker(latlng, featureStyle(feature)),
    });
    geoLayer.addTo(map);
    fitToData();
    localStorage.setItem("ofm.dataset", JSON.stringify(data));
    refreshLabels();
    setStatus(large ? "Dataset je velký, zvažte tileserver." : "");
  }

  function fitToData() {
    if (geoLayer) {
      map.fitBounds(geoLayer.getBounds());
    }
  }

  function getTags(el) {
    const tags = {};
    el.querySelectorAll("tag").forEach((t) => {
      tags[t.getAttribute("k")] = t.getAttribute("v");
    });
    return tags;
  }

  function osmToGeoJSON(text) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(text, "application/xml");
    const nodes = {};
    doc.querySelectorAll("node").forEach((n) => {
      const id = n.getAttribute("id");
      const lat = parseFloat(n.getAttribute("lat"));
      const lon = parseFloat(n.getAttribute("lon"));
      nodes[id] = {
        type: "Feature",
        geometry: { type: "Point", coordinates: [lon, lat] },
        properties: { tags: getTags(n) },
      };
    });
    const features = [];
    doc.querySelectorAll("way").forEach((w) => {
      const refs = Array.from(w.querySelectorAll("nd")).map((nd) => nodes[nd.getAttribute("ref")]);
      const coords = refs.map((n) => n.geometry.coordinates);
      const tags = getTags(w);
      const isArea = tags.area === "yes" || tags.building || tags.landuse || tags.natural === "water";
      const geom = {
        type: isArea ? "Polygon" : "LineString",
        coordinates: isArea ? [coords] : coords,
      };
      features.push({ type: "Feature", geometry: geom, properties: { tags } });
    });
    Object.values(nodes).forEach((n) => features.push(n));
    return { type: "FeatureCollection", features };
  }

  document.getElementById("ofm-osm").addEventListener("change", (e) => {
    if (e.target.checked) {
      baseTiles.addTo(map);
    } else {
      baseTiles.remove();
    }
  });

  labelCheckbox.addEventListener("change", (e) => {
    labelsEnabled = e.target.checked;
    refreshLabels();
  });

  map.on("zoomend", refreshLabels);

  document.getElementById("ofm-units").addEventListener("change", (e) => {
    customUnits = e.target.checked;
    if (customUnits) {
      unitLabel = prompt("Název jednotky", unitLabel) || unitLabel;
      unitFactor = parseFloat(prompt("Kolik metrů je 1 jednotka?", unitFactor) || unitFactor);
      localStorage.setItem("ofm.unitLabel", unitLabel);
      localStorage.setItem("ofm.unitFactor", unitFactor);
    }
    updateScale();
  });

  document.getElementById("ofm-upload").addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setStatus("Načítání…");
    const reader = new FileReader();
    reader.onload = () => {
      const text = reader.result;
      try {
        if (file.name.endsWith(".osm")) {
          loadGeoJSON(osmToGeoJSON(text));
        } else {
          const data = JSON.parse(text);
          if (data.type !== "FeatureCollection") throw new Error("Invalid GeoJSON");
          loadGeoJSON(data);
        }
      } catch (err) {
        setStatus("Chyba validace dat");
        alert("Nepodařilo se načíst data");
      }
    };
    reader.readAsText(file);
  });

  document.getElementById("ofm-fit").addEventListener("click", fitToData);

  setStatus("Žádná data");
  const stored = localStorage.getItem("ofm.dataset");
  if (stored) {
    try {
      setStatus("Načítání…");
      loadGeoJSON(JSON.parse(stored));
    } catch (err) {
      console.warn("Invalid stored dataset", err);
      setStatus("Žádná data");
    }
  } else {
    setStatus("Načítání…");
    fetch("/mapa.geojson")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) {
          loadGeoJSON(data);
        } else {
          setStatus("Žádná data");
        }
      })
      .catch(() => setStatus("Žádná data"));
  }

  updateScale();
})();
