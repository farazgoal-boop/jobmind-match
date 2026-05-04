window.addEventListener("DOMContentLoaded", () => {
  let installPrompt = null;
  const cards = document.querySelectorAll(".card");
  cards.forEach((card, i) => {
    card.animate(
      [
        { opacity: 0, transform: "translateY(10px)" },
        { opacity: 1, transform: "translateY(0)" }
      ],
      {
        duration: 320,
        delay: i * 70,
        fill: "forwards",
        easing: "ease-out"
      }
    );
  });

  document.querySelectorAll("[data-copy-query]").forEach((button) => {
    button.addEventListener("click", async () => {
      const query = button.getAttribute("data-copy-query") || "";
      if (!query) {
        return;
      }

      try {
        await navigator.clipboard.writeText(query);
        const originalText = button.textContent;
        button.textContent = "Copied";
        window.setTimeout(() => {
          button.textContent = originalText;
        }, 1000);
      } catch {
        button.textContent = "Copy failed";
      }
    });
  });

  const searchFocus = document.querySelector('[data-role="search-focus"]');
  const remoteOnly = document.querySelector('[data-role="remote-only"]');
  const juniorOnly = document.querySelector('[data-role="junior-only"]');
  const backendOnly = document.querySelector('input[name="backend_only"]');
  const regionPreference = document.querySelector('[data-role="region-preference"]');
  const installButton = document.querySelector('[data-role="install-app"]');

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/static/sw.js").catch(() => {
      // Keep the dashboard usable even if service worker registration fails.
    });
  }

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    installPrompt = event;
    installButton?.classList.remove("hidden");
  });

  installButton?.addEventListener("click", async () => {
    if (!installPrompt) {
      return;
    }
    installPrompt.prompt();
    await installPrompt.userChoice;
    installPrompt = null;
    installButton.classList.add("hidden");
  });

  document.querySelectorAll(".preset-chip").forEach((button) => {
    button.addEventListener("click", () => {
      if (searchFocus) {
        searchFocus.value = button.dataset.focus || "python";
      }
      if (remoteOnly) {
        remoteOnly.checked = button.dataset.remote === "true";
      }
      if (juniorOnly) {
        juniorOnly.checked = button.dataset.junior === "true";
      }
      if (backendOnly) {
        backendOnly.checked = button.dataset.backend === "true";
      }
      if (regionPreference && button.dataset.region) {
        regionPreference.value = button.dataset.region;
      }
    });
  });
});
