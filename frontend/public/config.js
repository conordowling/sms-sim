// Default used by `npm run dev`. In Docker this file is overwritten at
// container startup from the REFRESH_INTERVAL_SECONDS env var — see
// docker-entrypoint.sh.
window.APP_CONFIG = {
  refreshIntervalSeconds: 5,
};
