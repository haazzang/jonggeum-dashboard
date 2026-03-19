document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initTrendChart();
});

function initTabs() {
  const tabButtons = document.querySelectorAll("[data-tab-target]");
  const tabPanels = document.querySelectorAll("[data-tab-panel]");

  tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const target = button.dataset.tabTarget;

      tabButtons.forEach((item) => item.classList.toggle("is-active", item === button));
      tabPanels.forEach((panel) => {
        panel.classList.toggle("is-active", panel.dataset.tabPanel === target);
      });
    });
  });
}

function initTrendChart() {
  const chartRoot = document.querySelector("[data-trend-chart]");
  const payload = document.getElementById("trend-chart-data");

  if (!chartRoot || !payload) {
    return;
  }

  const trendData = JSON.parse(payload.textContent);
  if (!trendData.available || !trendData.default_key) {
    return;
  }

  const seriesButtons = Array.from(document.querySelectorAll("[data-series-key]"));
  const rangeButtons = Array.from(document.querySelectorAll("[data-range-days]"));
  const seriesSelect = document.querySelector("[data-series-select]");

  const titleNode = chartRoot.querySelector("[data-trend-title]");
  const periodNode = chartRoot.querySelector("[data-trend-period]");
  const latestNode = chartRoot.querySelector('[data-trend-stat="latest"]');
  const changeNode = chartRoot.querySelector('[data-trend-stat="change"]');
  const minNode = chartRoot.querySelector('[data-trend-stat="min"]');
  const maxNode = chartRoot.querySelector('[data-trend-stat="max"]');

  const gridNode = chartRoot.querySelector("[data-trend-grid]");
  const axisNode = chartRoot.querySelector("[data-trend-axis]");
  const areaNode = chartRoot.querySelector("[data-trend-area]");
  const lineNode = chartRoot.querySelector("[data-trend-line]");
  const pointNode = chartRoot.querySelector("[data-trend-point]");

  const state = {
    activeKey: trendData.default_key,
    rangeDays: "90",
  };

  const setActiveKey = (nextKey) => {
    if (!trendData.series[nextKey]) {
      return;
    }
    state.activeKey = nextKey;
    render();
  };

  const setRangeDays = (nextRange) => {
    state.rangeDays = nextRange;
    render();
  };

  seriesButtons.forEach((button) => {
    button.addEventListener("click", () => {
      setActiveKey(button.dataset.seriesKey);
    });
  });

  if (seriesSelect) {
    seriesSelect.addEventListener("change", () => {
      setActiveKey(seriesSelect.value);
    });
  }

  rangeButtons.forEach((button) => {
    button.addEventListener("click", () => {
      setRangeDays(button.dataset.rangeDays || "all");
    });
  });

  function render() {
    const activeSeries = trendData.series[state.activeKey];
    if (!activeSeries) {
      return;
    }

    const visibleWindow = sliceVisibleWindow(
      trendData.labels,
      activeSeries.values,
      state.rangeDays,
    );
    const stats = summarizeSeries(visibleWindow.values);

    titleNode.textContent = activeSeries.path;
    periodNode.textContent = buildPeriodLabel(visibleWindow.labels);
    latestNode.textContent = formatAmount(stats.latest);
    changeNode.textContent = formatChange(stats.change, stats.changeRatio);
    minNode.textContent = formatAmount(stats.min);
    maxNode.textContent = formatAmount(stats.max);

    drawTrendChart({
      labels: visibleWindow.labels,
      values: visibleWindow.values,
      gridNode,
      axisNode,
      areaNode,
      lineNode,
      pointNode,
    });

    seriesButtons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.seriesKey === state.activeKey);
    });
    rangeButtons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.rangeDays === state.rangeDays);
    });
    if (seriesSelect) {
      seriesSelect.value = state.activeKey;
    }
  }

  render();
}

function sliceVisibleWindow(labels, values, rangeDays) {
  if (rangeDays === "all") {
    return { labels, values };
  }

  const requestedDays = Number.parseInt(rangeDays, 10);
  if (!Number.isFinite(requestedDays) || requestedDays <= 0 || requestedDays >= labels.length) {
    return { labels, values };
  }

  const startIndex = Math.max(0, labels.length - requestedDays);
  return {
    labels: labels.slice(startIndex),
    values: values.slice(startIndex),
  };
}

function summarizeSeries(values) {
  const numericValues = values.filter((value) => Number.isFinite(value));
  if (!numericValues.length) {
    return {
      latest: null,
      change: null,
      changeRatio: null,
      min: null,
      max: null,
    };
  }

  const latest = numericValues[numericValues.length - 1];
  const first = numericValues[0];
  const change = latest - first;

  return {
    latest,
    change,
    changeRatio: first === 0 ? null : change / first,
    min: Math.min(...numericValues),
    max: Math.max(...numericValues),
  };
}

function buildPeriodLabel(labels) {
  if (!labels.length) {
    return "-";
  }
  return `${labels[0]} ~ ${labels[labels.length - 1]}`;
}

function drawTrendChart({ labels, values, gridNode, axisNode, areaNode, lineNode, pointNode }) {
  const width = 760;
  const height = 320;
  const padding = { top: 18, right: 18, bottom: 42, left: 60 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const baseline = padding.top + plotHeight;

  const numericValues = values.filter((value) => Number.isFinite(value));
  if (!numericValues.length) {
    gridNode.innerHTML = "";
    axisNode.innerHTML = "";
    areaNode.setAttribute("d", "");
    lineNode.setAttribute("d", "");
    pointNode.style.display = "none";
    return;
  }

  let minValue = Math.min(...numericValues);
  let maxValue = Math.max(...numericValues);
  if (minValue === maxValue) {
    const adjustment = Math.max(Math.abs(minValue) * 0.08, 1);
    minValue -= adjustment;
    maxValue += adjustment;
  }

  const span = maxValue - minValue || 1;
  const buildX = (index) => {
    if (labels.length <= 1) {
      return padding.left + plotWidth / 2;
    }
    return padding.left + (plotWidth * index) / (labels.length - 1);
  };
  const buildY = (value) => padding.top + ((maxValue - value) / span) * plotHeight;

  const points = values
    .map((value, index) => {
      if (!Number.isFinite(value)) {
        return null;
      }
      return {
        x: buildX(index),
        y: buildY(value),
        value,
      };
    })
    .filter(Boolean);

  const linePath = points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
    .join(" ");
  const areaPath = points.length
    ? `${linePath} L ${points[points.length - 1].x.toFixed(2)} ${baseline.toFixed(2)} L ${points[0].x.toFixed(2)} ${baseline.toFixed(2)} Z`
    : "";

  const yTicks = 5;
  const gridMarkup = [];
  for (let tick = 0; tick < yTicks; tick += 1) {
    const ratio = tick / (yTicks - 1);
    const y = padding.top + plotHeight * ratio;
    const value = maxValue - span * ratio;
    gridMarkup.push(
      `<line x1="${padding.left}" y1="${y.toFixed(2)}" x2="${(padding.left + plotWidth).toFixed(2)}" y2="${y.toFixed(2)}"></line>`,
    );
    gridMarkup.push(
      `<text x="${padding.left - 10}" y="${(y + 4).toFixed(2)}">${formatCompactAmount(value)}</text>`,
    );
  }
  gridNode.innerHTML = gridMarkup.join("");

  const xTickIndexes = buildTickIndexes(labels.length);
  const axisMarkup = xTickIndexes
    .map((index) => {
      const x = buildX(index);
      return `<text x="${x.toFixed(2)}" y="${height - 12}" text-anchor="middle">${formatDateLabel(labels[index])}</text>`;
    })
    .join("");
  axisNode.innerHTML = axisMarkup;

  areaNode.setAttribute("d", areaPath);
  lineNode.setAttribute("d", linePath);

  const lastPoint = points[points.length - 1];
  pointNode.style.display = "block";
  pointNode.setAttribute("cx", lastPoint.x.toFixed(2));
  pointNode.setAttribute("cy", lastPoint.y.toFixed(2));
}

function buildTickIndexes(length) {
  if (length <= 1) {
    return [0];
  }

  const steps = Math.min(4, length - 1);
  const indexes = new Set([0, length - 1]);
  for (let step = 1; step < steps; step += 1) {
    indexes.add(Math.round(((length - 1) * step) / steps));
  }
  return Array.from(indexes).sort((left, right) => left - right);
}

function formatDateLabel(value) {
  if (!value || value.length < 10) {
    return value || "-";
  }
  return value.slice(5).replace("-", ".");
}

function formatAmount(value) {
  if (!Number.isFinite(value)) {
    return "-";
  }
  return `${new Intl.NumberFormat("ko-KR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(value)}억원`;
}

function formatCompactAmount(value) {
  if (!Number.isFinite(value)) {
    return "-";
  }
  return new Intl.NumberFormat("ko-KR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

function formatPercent(value) {
  if (!Number.isFinite(value)) {
    return "-";
  }
  return `${new Intl.NumberFormat("ko-KR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value * 100)}%`;
}

function formatChange(change, changeRatio) {
  if (!Number.isFinite(change)) {
    return "-";
  }

  const sign = change > 0 ? "+" : "";
  const changeText = `${sign}${new Intl.NumberFormat("ko-KR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(change)}억원`;

  if (!Number.isFinite(changeRatio)) {
    return changeText;
  }
  return `${changeText} (${sign}${formatPercent(changeRatio)})`;
}
