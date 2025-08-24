document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.ds-chart').forEach((el) => {
    const slug = el.dataset.series;
    const type = el.dataset.type || 'line';
    const from = el.dataset.from || null;
    const to = el.dataset.to || null;
    const height = parseInt(el.dataset.height || '200', 10);
    fetch(`/api/dataseries/${slug}/`)
      .then((r) => r.json())
      .then((data) => {
        const points = data.points.filter((p) => {
          if (from && p.key < from) return false;
          if (to && p.key > to) return false;
          return true;
        });
        const labels = points.map((p) => p.key);
        const values = points.map((p) => parseFloat(p.value));
        const canvas = document.createElement('canvas');
        canvas.height = height;
        el.appendChild(canvas);
        new Chart(canvas.getContext('2d'), {
          type: type,
          data: {
            labels: labels,
            datasets: [
              {
                label: data.title || slug,
                data: values,
                borderColor: 'rgb(75, 192, 192)',
                fill: false,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
          },
        });
      });
  });
});
