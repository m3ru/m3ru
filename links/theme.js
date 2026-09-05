(() => {
  const root = document.documentElement;
  const systemTheme = window.matchMedia("(prefers-color-scheme: dark)");
  const storageKey = "m3ru-theme";

  // Run in the head so a saved preference applies before the page is painted.
  try {
    const saved = localStorage.getItem(storageKey);
    if (saved === "light" || saved === "dark") root.dataset.theme = saved;
  } catch {
    // System preference still works when browser storage is unavailable.
  }

  const isDark = () => root.dataset.theme
    ? root.dataset.theme === "dark"
    : systemTheme.matches;

  const updateButton = () => {
    const button = document.querySelector(".theme-toggle");
    if (!button) return;
    button.dataset.theme = isDark() ? "dark" : "light";
    const label = isDark() ? "Switch to light mode" : "Switch to dark mode";
    button.setAttribute("aria-label", label);
    button.title = label;
    button.hidden = false;
  };

  systemTheme.addEventListener("change", updateButton);
  document.addEventListener("DOMContentLoaded", () => {
    const button = document.querySelector(".theme-toggle");
    if (!button) return;
    button.addEventListener("click", () => {
      const theme = isDark() ? "light" : "dark";
      root.dataset.theme = theme;
      try {
        localStorage.setItem(storageKey, theme);
      } catch {
        // Keep the choice for this page even if it cannot be saved.
      }
      updateButton();
    });
    updateButton();
  });
})();
