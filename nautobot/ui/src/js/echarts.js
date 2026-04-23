/**
 * Get Nautobot theme overrides for ECharts options. These overrides are crucial for styling ECharts in compliance with
 * given theme, whether light or dark, because default ECharts color palettes are not compatible with Nautobot theme.
 * IMPORTANT: This function only returns an object with ECharts options **overrides**, not already overridden options!
 * @param {object} options - Base ECharts `options` object. Should be received from the server.
 * @param {string} theme - Theme, should either be `'light'` or `'dark'`.
 * @returns {object} ECharts options Nautobot theme overrides.
 */
export const getEchartsOptionsThemeOverrides = (options, theme) => {
  const borderColor = getComputedStyle(document.documentElement).getPropertyValue('--bs-border-color').trim();
  const secondaryColor = getComputedStyle(document.documentElement).getPropertyValue('--bs-secondary-color').trim();

  return {
    darkMode: theme === 'dark',
    ...(options.color
      ? {
          color: Array.isArray(options.color)
            ? options.color.map((colorObj) => colorObj?.[theme] || colorObj?.light || colorObj)
            : options.color,
        }
      : undefined),
    ...(options.legend
      ? { legend: { textStyle: { color: secondaryColor, ...options.legend.textStyle }, ...options.legend } }
      : undefined),
    ...(options.title
      ? {
          title: {
            subtextStyle: { color: secondaryColor, ...options.title.subtextStyle },
            textStyle: { color: secondaryColor, ...options.title.textStyle },
            ...options.title,
          },
        }
      : undefined),
    ...(options.xAxis
      ? {
          xAxis: {
            axisLabel: { color: secondaryColor, ...options.xAxis.axisLabel },
            axisLine: {
              lineStyle: { color: borderColor, ...options.xAxis.axisLine?.lineStyle },
              ...options.xAxis.axisLine,
            },
            splitLine: {
              lineStyle: { color: borderColor, ...options.xAxis.splitLine?.lineStyle },
              ...options.xAxis.splitLine,
            },
            ...options.xAxis,
          },
        }
      : undefined),
    ...(options.yAxis
      ? {
          yAxis: {
            axisLabel: { color: secondaryColor, ...options.yAxis.axisLabel },
            axisLine: {
              lineStyle: { color: borderColor, ...options.yAxis.axisLine?.lineStyle },
              ...options.yAxis.axisLine,
            },
            splitLine: {
              lineStyle: { color: borderColor, ...options.yAxis.splitLine?.lineStyle },
              ...options.yAxis.splitLine,
            },
            ...options.yAxis,
          },
        }
      : undefined),
  };
};
