document.addEventListener("DOMContentLoaded", () => {
  // Theme Toggle Elements
  const themeToggleBtn = document.getElementById("themeToggleBtn");
  const sunIcon = themeToggleBtn ? themeToggleBtn.querySelector(".sun-icon") : null;
  const moonIcon = themeToggleBtn ? themeToggleBtn.querySelector(".moon-icon") : null;

  // Cookie Session Elements
  const openCookieModalBtn = document.getElementById("openCookieModalBtn");
  const cookieModal = document.getElementById("cookieModal");
  const closeCookieModalBtn = document.getElementById("closeCookieModalBtn");
  const activeCookieLabel = document.getElementById("activeCookieLabel");
  const browserRadioInputs = document.querySelectorAll('input[name="browserCookieOption"]');
  const customCookiesInput = document.getElementById("customCookiesInput");
  const uploadCookiesBtn = document.getElementById("uploadCookiesBtn");
  const clearCookiesFileBtn = document.getElementById("clearCookiesFileBtn");
  const customCookieStatus = document.getElementById("customCookieStatus");
  const saveCookieSettingsBtn = document.getElementById("saveCookieSettingsBtn");

  // Mode Switchers
  const singleModeBtn = document.getElementById("singleModeBtn");
  const bulkModeBtn = document.getElementById("bulkModeBtn");
  const singleInputSection = document.getElementById("singleInputSection");
  const bulkInputSection = document.getElementById("bulkInputSection");

  // Single Input Elements
  const urlInput = document.getElementById("urlInput");
  const analyzeBtn = document.getElementById("analyzeBtn");
  const btnText = analyzeBtn.querySelector(".btn-text");
  const spinner = analyzeBtn.querySelector(".spinner");
  const pasteBtn = document.getElementById("pasteBtn");
  const clearBtn = document.getElementById("clearBtn");
  const alertBox = document.getElementById("alertBox");
  const alertMessage = document.getElementById("alertMessage");

  // Bulk & Channel Elements
  const bulkUrlsInput = document.getElementById("bulkUrlsInput");
  const bulkPasteBtn = document.getElementById("bulkPasteBtn");
  const analyzeBulkBtn = document.getElementById("analyzeBulkBtn");
  const bulkBtnText = analyzeBulkBtn.querySelector(".bulk-btn-text");
  const bulkSpinner = analyzeBulkBtn.querySelector(".bulk-spinner");
  const bulkQueueContainer = document.getElementById("bulkQueueContainer");
  const bulkQueueList = document.getElementById("bulkQueueList");
  
  // Channel Header Elements
  const channelBanner = document.getElementById("channelBanner");
  const channelAvatar = document.getElementById("channelAvatar");
  const channelTitle = document.getElementById("channelTitle");
  const channelAuthor = document.getElementById("channelAuthor");
  const channelPlatformBadge = document.getElementById("channelPlatformBadge");
  const statTotalCount = document.getElementById("statTotalCount");
  const statLongCount = document.getElementById("statLongCount");
  const statShortCount = document.getElementById("statShortCount");

  // Filter Pills Elements
  const filterPills = document.querySelectorAll(".filter-pill");
  const pillCountAll = document.getElementById("pillCountAll");
  const pillCountLong = document.getElementById("pillCountLong");
  const pillCountShort = document.getElementById("pillCountShort");

  // Batch Action Buttons
  const downloadAllVideoBtn = document.getElementById("downloadAllVideoBtn");
  const downloadAllAudioBtn = document.getElementById("downloadAllAudioBtn");
  const downloadAllTranscriptBtn = document.getElementById("downloadAllTranscriptBtn");

  // Concurrency Controls
  const concurrencySelectBulk = document.getElementById("concurrencySelectBulk");

  // Result Section Elements (Single Video)
  const resultSection = document.getElementById("resultSection");
  const mediaThumbnail = document.getElementById("mediaThumbnail");
  const mediaDuration = document.getElementById("mediaDuration");
  const mediaPlatform = document.getElementById("mediaPlatform");
  const mediaTitle = document.getElementById("mediaTitle");
  const mediaAuthor = document.getElementById("mediaAuthor");
  const mediaViews = document.getElementById("mediaViews");
  const mediaViewsWrapper = document.getElementById("mediaViewsWrapper");
  const customTitleInput = document.getElementById("customTitleInput");
  const quickPreviewBtn = document.getElementById("quickPreviewBtn");
  const includeTranscriptCheck = document.getElementById("includeTranscriptCheck");

  // Feature 2: Trim Settings
  const trimStartInput = document.getElementById("trimStartInput");
  const trimEndInput = document.getElementById("trimEndInput");

  // Format Tabs & Grids
  const videoPresetsGrid = document.getElementById("videoPresetsGrid");
  const audioPresetsGrid = document.getElementById("audioPresetsGrid");
  const subtitlesGrid = document.getElementById("subtitlesGrid");
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabContents = document.querySelectorAll(".tab-content");

  // Active Downloads & Queue Badges (4-column grid)
  const activeDownloadsSection = document.getElementById("activeDownloadsSection");
  const tasksList = document.getElementById("tasksList");
  const activeCountBadge = document.getElementById("activeCountBadge");
  const queuedCountBadge = document.getElementById("queuedCountBadge");

  // Library Elements
  const libraryList = document.getElementById("libraryList");
  const historyCountBadge = document.getElementById("historyCountBadge");
  const openFolderLibraryBtn = document.getElementById("openFolderLibraryBtn");
  const refreshLibraryBtn = document.getElementById("refreshLibraryBtn");
  const clearHistoryBtn = document.getElementById("clearHistoryBtn");

  // Feature 7: Modal Player Elements
  const playerModal = document.getElementById("playerModal");
  const playerTitle = document.getElementById("playerTitle");
  const closeModalBtn = document.getElementById("closeModalBtn");
  const modalVideoPlayer = document.getElementById("modalVideoPlayer");
  const modalAudioWrap = document.getElementById("modalAudioWrap");
  const modalAudioPlayer = document.getElementById("modalAudioPlayer");

  let currentMediaData = null;
  let allBatchItems = [];
  let currentFilter = "all";
  let activeBrowserCookie = "auto";
  const activeTasks = new Map();

  // Initialize theme
  initTheme();

  // Load initial settings and library
  loadLibrary();
  initConcurrencySettings();
  loadCookieSettings();

  // Polling loop for active tasks (high frequency for real-time speed display)
  setInterval(pollActiveTasks, 600);

  // Theme Switching Logic
  function initTheme() {
    const savedTheme = localStorage.getItem("omni_theme") || "dark";
    applyTheme(savedTheme);

    if (themeToggleBtn) {
      themeToggleBtn.addEventListener("click", () => {
        const isCurrentlyLight = document.body.classList.contains("light-theme");
        const nextTheme = isCurrentlyLight ? "dark" : "light";
        applyTheme(nextTheme);
        localStorage.setItem("omni_theme", nextTheme);
      });
    }
  }

  function applyTheme(theme) {
    if (theme === "light") {
      document.body.classList.add("light-theme");
      if (sunIcon) sunIcon.classList.remove("hidden");
      if (moonIcon) moonIcon.classList.add("hidden");
    } else {
      document.body.classList.remove("light-theme");
      if (sunIcon) sunIcon.classList.add("hidden");
      if (moonIcon) moonIcon.classList.remove("hidden");
    }
  }

  // Cookie Settings Management
  async function loadCookieSettings() {
    try {
      const res = await fetch("/api/settings/cookies");
      if (res.ok) {
        const data = await res.json();
        activeBrowserCookie = data.browser || "auto";
        updateCookieUI(data);
      }
    } catch (e) {
      console.error("Failed to load cookie settings:", e);
    }
  }

  function updateCookieUI(data) {
    const browser = data.browser || "auto";
    const labels = {
      auto: "Auto (Chrome/Edge)",
      chrome: "Google Chrome",
      edge: "Microsoft Edge",
      firefox: "Mozilla Firefox",
      brave: "Brave Browser",
      custom: "Custom cookies.txt",
      none: "Disabled"
    };

    if (activeCookieLabel) {
      activeCookieLabel.textContent = labels[browser] || browser.toUpperCase();
    }

    // Update radio selections
    browserRadioInputs.forEach(radio => {
      radio.checked = (radio.value === browser);
    });

    // Update custom cookie status badge
    if (customCookieStatus) {
      if (data.has_custom_cookies) {
        customCookieStatus.textContent = `Active (${formatBytes(data.custom_cookies_size)})`;
        customCookieStatus.style.color = "var(--accent-emerald)";
        if (clearCookiesFileBtn) clearCookiesFileBtn.classList.remove("hidden");
      } else {
        customCookieStatus.textContent = "No custom file";
        customCookieStatus.style.color = "var(--text-dim)";
        if (clearCookiesFileBtn) clearCookiesFileBtn.classList.add("hidden");
      }
    }
  }

  if (openCookieModalBtn) {
    openCookieModalBtn.addEventListener("click", () => {
      cookieModal.classList.remove("hidden");
    });
  }

  if (closeCookieModalBtn) {
    closeCookieModalBtn.addEventListener("click", () => {
      cookieModal.classList.add("hidden");
    });
  }

  if (cookieModal) {
    cookieModal.addEventListener("click", (e) => {
      if (e.target === cookieModal) cookieModal.classList.add("hidden");
    });
  }

  if (saveCookieSettingsBtn) {
    saveCookieSettingsBtn.addEventListener("click", async () => {
      let selectedBrowser = "auto";
      browserRadioInputs.forEach(r => {
        if (r.checked) selectedBrowser = r.value;
      });

      try {
        const res = await fetch("/api/settings/cookies", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ browser: selectedBrowser })
        });
        if (res.ok) {
          activeBrowserCookie = selectedBrowser;
          await loadCookieSettings();
          cookieModal.classList.add("hidden");
          showSuccessAlert(`Browser session set to: ${selectedBrowser.toUpperCase()}`);
        }
      } catch (e) {
        showAlert("Failed to save cookie preference.");
      }
    });
  }

  if (uploadCookiesBtn) {
    uploadCookiesBtn.addEventListener("click", async () => {
      const content = customCookiesInput.value.trim();
      if (!content) {
        showAlert("Please paste your Netscape cookies text into the box.");
        return;
      }

      try {
        const res = await fetch("/api/upload-cookies", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content })
        });
        if (res.ok) {
          customCookiesInput.value = "";
          await loadCookieSettings();
          showSuccessAlert("Custom cookies.txt saved and activated!");
        }
      } catch (e) {
        showAlert("Failed to upload cookies.");
      }
    });
  }

  if (clearCookiesFileBtn) {
    clearCookiesFileBtn.addEventListener("click", async () => {
      try {
        const res = await fetch("/api/delete-cookies", { method: "POST" });
        if (res.ok) {
          await loadCookieSettings();
          showSuccessAlert("Custom cookies removed. Switched to Auto.");
        }
      } catch (e) {
        showAlert("Failed to delete cookies file.");
      }
    });
  }

  // Concurrency Setting Handlers
  async function initConcurrencySettings() {
    try {
      const res = await fetch("/api/settings/concurrency");
      if (res.ok) {
        const data = await res.json();
        if (concurrencySelectBulk) concurrencySelectBulk.value = String(data.max_concurrency);
      }
    } catch (e) {
      console.error("Could not fetch concurrency settings:", e);
    }
  }

  async function updateConcurrency(val) {
    const limit = parseInt(val, 10);
    if (concurrencySelectBulk) concurrencySelectBulk.value = String(limit);

    try {
      const res = await fetch("/api/settings/concurrency", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ max_concurrency: limit })
      });
      if (res.ok) {
        showSuccessAlert(`Download concurrency set to ${limit} active at a time.`);
      }
    } catch (e) {
      showAlert("Failed to update concurrency limit.");
    }
  }

  if (concurrencySelectBulk) {
    concurrencySelectBulk.addEventListener("change", (e) => {
      updateConcurrency(e.target.value);
    });
  }

  // Mode Toggling
  singleModeBtn.addEventListener("click", () => {
    singleModeBtn.classList.add("active");
    bulkModeBtn.classList.remove("active");
    singleInputSection.classList.remove("hidden");
    bulkInputSection.classList.add("hidden");
  });

  bulkModeBtn.addEventListener("click", () => {
    bulkModeBtn.classList.add("active");
    singleModeBtn.classList.remove("active");
    bulkInputSection.classList.remove("hidden");
    singleInputSection.classList.add("hidden");
  });

  // Single Input Listeners
  urlInput.addEventListener("input", () => {
    if (urlInput.value.trim().length > 0) {
      clearBtn.classList.remove("hidden");
    } else {
      clearBtn.classList.add("hidden");
    }
  });

  urlInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      analyzeLink();
    }
  });

  clearBtn.addEventListener("click", () => {
    urlInput.value = "";
    clearBtn.classList.add("hidden");
    urlInput.focus();
  });

  pasteBtn.addEventListener("click", async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text && text.trim()) {
        urlInput.value = text.trim();
        clearBtn.classList.remove("hidden");
        analyzeLink();
      }
    } catch (err) {
      showAlert("Could not read clipboard. Please paste manually.");
    }
  });

  analyzeBtn.addEventListener("click", () => {
    analyzeLink();
  });

  // Bulk Input Listeners (Feature 1)
  bulkPasteBtn.addEventListener("click", async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text && text.trim()) {
        bulkUrlsInput.value = (bulkUrlsInput.value.trim() ? bulkUrlsInput.value.trim() + "\n" : "") + text.trim();
      }
    } catch (err) {
      showAlert("Could not read clipboard.");
    }
  });

  analyzeBulkBtn.addEventListener("click", () => {
    analyzeBulkLinks();
  });

  // Filter Pills Event Listeners
  filterPills.forEach(pill => {
    pill.addEventListener("click", () => {
      filterPills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      currentFilter = pill.getAttribute("data-filter") || "all";
      renderFilteredBatchItems();
    });
  });

  // Batch Download Buttons (Hide top list immediately as requested)
  function getFilteredItems() {
    if (currentFilter === "long") {
      return allBatchItems.filter(i => i.type === "long");
    } else if (currentFilter === "short") {
      return allBatchItems.filter(i => i.type === "short");
    }
    return allBatchItems;
  }

  downloadAllVideoBtn.addEventListener("click", () => {
    const items = getFilteredItems();
    if (items.length === 0) {
      showAlert("No items to download in this category.");
      return;
    }
    const withTranscript = includeTranscriptCheck ? includeTranscriptCheck.checked : false;
    items.forEach(item => {
      triggerDirectDownload(item.url, "video", "best", item.title, null, null, null, withTranscript);
    });
    // Hide the top list Batch Items immediately
    bulkQueueContainer.classList.add("hidden");
    showSuccessAlert(`Queued ${items.length} videos! Ongoing downloads are displayed below in 4 columns.`);
    activeDownloadsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  downloadAllAudioBtn.addEventListener("click", () => {
    const items = getFilteredItems();
    if (items.length === 0) {
      showAlert("No items to download in this category.");
      return;
    }
    const withTranscript = includeTranscriptCheck ? includeTranscriptCheck.checked : false;
    items.forEach(item => {
      triggerDirectDownload(item.url, "audio", "mp3_best", item.title, null, null, null, withTranscript);
    });
    // Hide the top list Batch Items immediately
    bulkQueueContainer.classList.add("hidden");
    showSuccessAlert(`Queued ${items.length} audio tracks! Ongoing downloads are displayed below in 4 columns.`);
    activeDownloadsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  if (downloadAllTranscriptBtn) {
    downloadAllTranscriptBtn.addEventListener("click", () => {
      const items = getFilteredItems();
      if (items.length === 0) {
        showAlert("No items to download in this category.");
        return;
      }
      items.forEach(item => {
        triggerDirectDownload(item.url, "transcript", "txt", `${item.title}-transcript`);
      });
      // Hide the top list Batch Items immediately
      bulkQueueContainer.classList.add("hidden");
      showSuccessAlert(`Queued ${items.length} clean text transcripts (.txt)! Ongoing downloads are displayed below.`);
      activeDownloadsSection.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  // Tab switching
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      tabBtns.forEach(b => b.classList.remove("active"));
      tabContents.forEach(c => c.classList.remove("active"));

      btn.classList.add("active");
      const targetTab = btn.getAttribute("data-tab");
      document.getElementById(`${targetTab}Tab`).classList.add("active");
    });
  });

  // Folder open button (Downloads library in Windows Explorer)
  async function handleOpenFolder() {
    try {
      const res = await fetch("/api/open-folder", { method: "POST" });
      if (res.ok) {
        showSuccessAlert("Downloads folder opened in Windows Explorer!");
      }
    } catch (e) {
      showAlert("Failed to open downloads folder.");
    }
  }

  if (openFolderLibraryBtn) openFolderLibraryBtn.addEventListener("click", handleOpenFolder);

  refreshLibraryBtn.addEventListener("click", () => {
    loadLibrary();
  });

  // Clear History Button (Non-destructive: cleans app records, preserves files on disk)
  if (clearHistoryBtn) {
    clearHistoryBtn.addEventListener("click", async () => {
      if (confirm("Clear download history from the app? (Note: All files will remain safely stored on your hard drive).")) {
        try {
          const res = await fetch("/api/clear-history", { method: "POST" });
          if (res.ok) {
            showSuccessAlert("Download history cleared from app. Physical files remain safe on disk!");
            loadLibrary();
          } else {
            showAlert("Failed to clear history.");
          }
        } catch (e) {
          showAlert("Error clearing history.");
        }
      }
    });
  }

  // Feature 7: Quick Preview on result card
  quickPreviewBtn.addEventListener("click", () => {
    if (!currentMediaData) return;
    if (currentMediaData.direct_video_url) {
      openPlayerModal(currentMediaData.title, currentMediaData.direct_video_url, "video");
    } else {
      showAlert("Download the video to watch full master quality playback locally!");
    }
  });

  // Modal player close
  closeModalBtn.addEventListener("click", closePlayerModal);
  playerModal.addEventListener("click", (e) => {
    if (e.target === playerModal) closePlayerModal();
  });

  function openPlayerModal(title, streamUrl, type) {
    playerTitle.textContent = title;
    
    if (type === "audio") {
      modalVideoPlayer.classList.add("hidden");
      modalVideoPlayer.pause();
      modalAudioWrap.classList.remove("hidden");
      modalAudioPlayer.src = streamUrl;
      modalAudioPlayer.play().catch(() => {});
    } else {
      modalAudioWrap.classList.add("hidden");
      modalAudioPlayer.pause();
      modalVideoPlayer.classList.remove("hidden");
      modalVideoPlayer.src = streamUrl;
      modalVideoPlayer.play().catch(() => {});
    }

    playerModal.classList.remove("hidden");
  }

  function closePlayerModal() {
    modalVideoPlayer.pause();
    modalVideoPlayer.src = "";
    modalAudioPlayer.pause();
    modalAudioPlayer.src = "";
    playerModal.classList.add("hidden");
  }

  // Single Link / Channel Analysis
  async function analyzeLink() {
    const url = urlInput.value.trim();
    if (!url) {
      showAlert("Please enter or paste a valid video URL or channel name (@channel).");
      return;
    }

    hideAlert();
    setLoading(true);

    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          url: url,
          browser_cookies: activeBrowserCookie
        })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Failed to extract media information.");
      }

      currentMediaData = data;

      if (data.is_playlist || data.is_channel) {
        // Render as Channel / Playlist Batch View
        renderChannelView(data);
      } else {
        // Render as Single Video Card
        if (channelBanner) channelBanner.classList.add("hidden");
        if (bulkQueueContainer) bulkQueueContainer.classList.add("hidden");
        renderMediaResult(data);
      }
    } catch (err) {
      showAlert(err.message);
      resultSection.classList.add("hidden");
    } finally {
      setLoading(false);
    }
  }

  // Bulk Links Analysis (Feature 1)
  async function analyzeBulkLinks() {
    const rawText = bulkUrlsInput.value.trim();
    if (!rawText) {
      showAlert("Please enter at least one URL or channel name.");
      return;
    }

    const urls = rawText.split(/[\n,]+/).map(u => u.trim()).filter(u => u.length > 2);
    if (urls.length === 0) {
      showAlert("No valid URLs or channel handles found.");
      return;
    }

    hideAlert();
    setBulkLoading(true);

    try {
      const res = await fetch("/api/analyze-batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          urls: urls,
          browser_cookies: activeBrowserCookie
        })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to analyze batch.");
      }

      renderBulkQueue(data.results);
    } catch (err) {
      showAlert(err.message);
    } finally {
      setBulkLoading(false);
    }
  }

  // Render Channel Profile & Media View
  function renderChannelView(channelData) {
    resultSection.classList.add("hidden");

    // Populate Channel Banner
    if (channelBanner) {
      channelBanner.classList.remove("hidden");
      channelAvatar.src = channelData.thumbnail || "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=200&auto=format&fit=crop&q=60";
      channelTitle.textContent = channelData.title || "Channel";
      channelAuthor.textContent = `@${channelData.uploader || 'Creator'}`;
      channelPlatformBadge.textContent = channelData.platform || "YouTube";
      statTotalCount.textContent = channelData.item_count || channelData.items.length;
      statLongCount.textContent = channelData.long_count || 0;
      statShortCount.textContent = channelData.short_count || 0;
    }

    // Set batch items
    allBatchItems = channelData.items || [];
    currentFilter = "all";

    // Update filter pill counts
    if (pillCountAll) pillCountAll.textContent = allBatchItems.length;
    if (pillCountLong) pillCountLong.textContent = channelData.long_count || 0;
    if (pillCountShort) pillCountShort.textContent = channelData.short_count || 0;

    filterPills.forEach(p => {
      p.classList.toggle("active", p.getAttribute("data-filter") === "all");
    });

    renderFilteredBatchItems();
    bulkQueueContainer.classList.remove("hidden");
    bulkQueueContainer.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function renderBulkQueue(results) {
    if (channelBanner) channelBanner.classList.add("hidden");

    allBatchItems = [];
    let longCount = 0;
    let shortCount = 0;

    results.forEach(r => {
      if (r.status === "success" && r.data) {
        if (r.data.is_playlist || r.data.is_channel) {
          (r.data.items || []).forEach(item => {
            allBatchItems.push(item);
            if (item.type === "short") shortCount++;
            else longCount++;
          });
        } else {
          const item = {
            url: r.data.url,
            title: r.data.title,
            thumbnail: r.data.thumbnail,
            duration_formatted: r.data.duration_formatted,
            platform: r.data.platform,
            type: (r.data.duration && r.data.duration <= 60) ? "short" : "long",
            uploader: r.data.uploader
          };
          allBatchItems.push(item);
          if (item.type === "short") shortCount++;
          else longCount++;
        }
      }
    });

    if (allBatchItems.length === 0) {
      showAlert("Could not extract any valid items from the provided URLs.");
      bulkQueueContainer.classList.add("hidden");
      return;
    }

    if (pillCountAll) pillCountAll.textContent = allBatchItems.length;
    if (pillCountLong) pillCountLong.textContent = longCount;
    if (pillCountShort) pillCountShort.textContent = shortCount;

    currentFilter = "all";
    filterPills.forEach(p => {
      p.classList.toggle("active", p.getAttribute("data-filter") === "all");
    });

    renderFilteredBatchItems();
    bulkQueueContainer.classList.remove("hidden");
    bulkQueueContainer.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function renderFilteredBatchItems() {
    bulkQueueList.innerHTML = "";
    const itemsToDisplay = getFilteredItems();

    if (itemsToDisplay.length === 0) {
      bulkQueueList.innerHTML = `
        <div class="empty-state" style="padding: 24px; text-align: center; color: var(--text-muted);">
          <p>No media found in the "<strong>${currentFilter.toUpperCase()}</strong>" category.</p>
        </div>
      `;
      return;
    }

    itemsToDisplay.forEach((item, idx) => {
      const row = document.createElement("div");
      row.className = "bulk-item-row";

      const thumb = item.thumbnail || "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=200&auto=format&fit=crop&q=60";
      const duration = item.duration_formatted ? `• ${item.duration_formatted}` : "";
      const isShort = item.type === "short";
      const typeTag = isShort ? `<span class="tag-badge-short">⚡ Short</span>` : `<span class="tag-badge-long">🎬 Long</span>`;

      row.innerHTML = `
        <div class="bulk-item-info">
          <img src="${thumb}" class="bulk-item-thumb" alt="Thumbnail">
          <div style="min-width: 0;">
            <div class="bulk-item-title" title="${item.title}">${typeTag}${item.title}</div>
            <div style="font-size: 0.78rem; color: var(--text-muted);">${item.uploader || 'Creator'} • ${item.platform || 'Media'} ${duration}</div>
          </div>
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center;">
          <button class="btn btn-primary btn-sm dl-bulk-item-vid" title="Download MP4 Video">MP4 Video</button>
          <button class="btn btn-secondary btn-sm dl-bulk-item-aud" title="Download MP3 Audio">MP3 Audio</button>
          <button class="btn btn-secondary btn-sm dl-bulk-item-txt" title="Download Clean Text Transcript (.txt)">📝 Transcript</button>
        </div>
      `;

      row.querySelector(".dl-bulk-item-vid").addEventListener("click", () => {
        const withTranscript = includeTranscriptCheck ? includeTranscriptCheck.checked : false;
        triggerDirectDownload(item.url, "video", "best", item.title, null, null, null, withTranscript);
      });

      row.querySelector(".dl-bulk-item-aud").addEventListener("click", () => {
        const withTranscript = includeTranscriptCheck ? includeTranscriptCheck.checked : false;
        triggerDirectDownload(item.url, "audio", "mp3_best", item.title, null, null, null, withTranscript);
      });

      row.querySelector(".dl-bulk-item-txt").addEventListener("click", () => {
        triggerDirectDownload(item.url, "transcript", "txt", `${item.title}-transcript`);
      });

      bulkQueueList.appendChild(row);
    });
  }

  function setLoading(loading) {
    if (loading) {
      btnText.textContent = "Analyzing...";
      spinner.classList.remove("hidden");
      analyzeBtn.disabled = true;
    } else {
      btnText.textContent = "Analyze";
      spinner.classList.add("hidden");
      analyzeBtn.disabled = false;
    }
  }

  function setBulkLoading(loading) {
    if (loading) {
      bulkBtnText.textContent = "Analyzing Batch / Channel...";
      bulkSpinner.classList.remove("hidden");
      analyzeBulkBtn.disabled = true;
    } else {
      bulkBtnText.textContent = "Analyze All Links";
      bulkSpinner.classList.add("hidden");
      analyzeBulkBtn.disabled = false;
    }
  }

  function showAlert(msg) {
    alertBox.classList.remove("hidden", "success");
    alertMessage.textContent = msg;
    alertBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function showSuccessAlert(msg) {
    alertBox.classList.remove("hidden");
    alertBox.classList.add("success");
    alertMessage.textContent = msg;
    setTimeout(() => {
      alertBox.classList.add("hidden");
    }, 4000);
  }

  function hideAlert() {
    alertBox.classList.add("hidden");
  }

  // Render Result Card (Single Video)
  function renderMediaResult(data) {
    mediaTitle.textContent = data.title;
    mediaThumbnail.src = data.thumbnail || "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=600&auto=format&fit=crop&q=60";
    mediaDuration.textContent = data.duration_formatted || "Live / Stream";
    mediaPlatform.textContent = (data.platform || "MEDIA").toUpperCase();
    mediaAuthor.textContent = data.uploader;

    if (data.view_count) {
      mediaViewsWrapper.style.display = "flex";
      mediaViews.textContent = `${data.view_count} views`;
    } else {
      mediaViewsWrapper.style.display = "none";
    }

    customTitleInput.value = data.title;
    trimStartInput.value = "";
    trimEndInput.value = "";

    // Render presets & subtitles
    renderPresets(data.presets);
    renderSubtitles(data.subtitles || []);

    resultSection.classList.remove("hidden");
    resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function renderPresets(presets) {
    videoPresetsGrid.innerHTML = "";
    audioPresetsGrid.innerHTML = "";

    const videoPresets = presets.filter(p => p.type === "video");
    const audioPresets = presets.filter(p => p.type === "audio" || p.type === "transcript");

    videoPresets.forEach(preset => {
      const card = createPresetCard(preset);
      videoPresetsGrid.appendChild(card);
    });

    audioPresets.forEach(preset => {
      const card = createPresetCard(preset);
      audioPresetsGrid.appendChild(card);
    });
  }

  function renderSubtitles(subtitles) {
    subtitlesGrid.innerHTML = "";

    if (!subtitles || subtitles.length === 0) {
      subtitlesGrid.innerHTML = `
        <div style="grid-column: 1 / -1; display: flex; flex-direction: column; gap: 10px;">
          <p class="no-subs">No external subtitle tracks detected for this stream. You can still extract automatic transcript (.txt):</p>
          <button class="btn btn-secondary btn-sm dl-direct-txt-btn" style="align-self: flex-start;">
            📝 Download Transcript (.txt)
          </button>
        </div>
      `;
      const txtBtn = subtitlesGrid.querySelector(".dl-direct-txt-btn");
      if (txtBtn) {
        txtBtn.addEventListener("click", () => triggerDownload("transcript", "txt"));
      }
      return;
    }

    subtitles.forEach(sub => {
      const card = document.createElement("div");
      card.className = "sub-item-card";
      card.innerHTML = `
        <span class="sub-lang">${sub.name || sub.lang.toUpperCase()}</span>
        <div style="display: flex; gap: 6px;">
          <button class="btn btn-secondary btn-sm dl-sub-btn" data-lang="${sub.lang}" title="Download SRT Subtitles">
            SRT
          </button>
          <button class="btn btn-primary btn-sm dl-sub-txt-btn" data-lang="${sub.lang}" title="Download Clean Text Transcript (.txt)">
            📝 .TXT
          </button>
        </div>
      `;

      card.querySelector(".dl-sub-btn").addEventListener("click", () => {
        triggerDownload("subtitle", "srt", sub.lang);
      });

      card.querySelector(".dl-sub-txt-btn").addEventListener("click", () => {
        triggerDownload("transcript", "txt", sub.lang);
      });

      subtitlesGrid.appendChild(card);
    });
  }

  function createPresetCard(preset) {
    const card = document.createElement("div");
    card.className = "preset-card";

    const isVideo = preset.type === "video";
    const btnClass = isVideo ? "btn-primary" : "btn-secondary";

    card.innerHTML = `
      <div class="preset-info">
        <div class="preset-header">
          <span class="preset-label">${preset.label}</span>
          <span class="badge-local" style="font-size:0.68rem; padding: 1px 6px;">${preset.type.toUpperCase()}</span>
        </div>
        <span class="preset-desc">${preset.desc}</span>
      </div>
      <button class="btn ${btnClass} btn-dl-action" data-type="${preset.type}" data-quality="${preset.quality}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px;">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
        Download
      </button>
    `;

    const dlBtn = card.querySelector(".btn-dl-action");
    dlBtn.addEventListener("click", () => {
      triggerDownload(preset.type, preset.quality);
    });

    return card;
  }

  // Trigger Download with Trim & Transcript Companion Support
  async function triggerDownload(formatType, quality, subtitleLang = null) {
    if (!currentMediaData) return;

    const withTranscript = includeTranscriptCheck ? includeTranscriptCheck.checked : false;
    const payload = {
      url: currentMediaData.url,
      format_type: formatType,
      quality: quality,
      custom_title: customTitleInput.value.trim() || currentMediaData.title,
      start_time: trimStartInput.value.trim() || null,
      end_time: trimEndInput.value.trim() || null,
      subtitle_lang: subtitleLang,
      include_transcript: withTranscript,
      browser_cookies: activeBrowserCookie
    };

    await triggerDirectDownload(payload.url, payload.format_type, payload.quality, payload.custom_title, payload.start_time, payload.end_time, payload.subtitle_lang, payload.include_transcript);
  }

  async function triggerDirectDownload(url, formatType, quality, customTitle, startTime = null, endTime = null, subtitleLang = null, includeTranscript = false) {
    const payload = {
      url: url,
      format_type: formatType,
      quality: quality,
      custom_title: customTitle,
      start_time: startTime,
      end_time: endTime,
      subtitle_lang: subtitleLang,
      include_transcript: includeTranscript,
      browser_cookies: activeBrowserCookie
    };

    try {
      const res = await fetch("/api/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to start download");
      }

      const taskId = data.task_id;
      activeTasks.set(taskId, {
        id: taskId,
        title: payload.custom_title || url,
        status: "queued",
        progress: 0
      });

      renderTasks();
      activeDownloadsSection.classList.remove("hidden");
    } catch (err) {
      showAlert(`Error: ${err.message}`);
    }
  }

  // Pause / Resume / Cancel Task Handlers
  async function pauseTask(taskId) {
    try {
      await fetch(`/api/task/pause/${taskId}`, { method: "POST" });
      const t = activeTasks.get(taskId);
      if (t) {
        t.status = "paused";
        t.speed_formatted = "Paused";
        renderTasks();
      }
    } catch (e) {
      console.error("Error pausing task:", e);
    }
  }

  async function resumeTask(taskId) {
    try {
      await fetch(`/api/task/resume/${taskId}`, { method: "POST" });
      const t = activeTasks.get(taskId);
      if (t) {
        t.status = "queued";
        renderTasks();
      }
    } catch (e) {
      console.error("Error resuming task:", e);
    }
  }

  async function cancelTask(taskId) {
    try {
      await fetch(`/api/task/cancel/${taskId}`, { method: "POST" });
      activeTasks.delete(taskId);
      renderTasks();
    } catch (e) {
      console.error("Error cancelling task:", e);
    }
  }

  // Poll Active Tasks
  async function pollActiveTasks() {
    if (activeTasks.size === 0) {
      activeDownloadsSection.classList.add("hidden");
      return;
    }

    activeDownloadsSection.classList.remove("hidden");

    let activeCount = 0;
    let queuedCount = 0;

    for (const [taskId, task] of activeTasks.entries()) {
      try {
        const res = await fetch(`/api/progress/${taskId}`);
        if (!res.ok) continue;

        const data = await res.json();
        activeTasks.set(taskId, { ...task, ...data });

        if (data.status === "downloading" || data.status === "processing") {
          activeCount++;
        } else if (data.status === "queued") {
          queuedCount++;
        } else if (data.status === "completed") {
          activeTasks.delete(taskId);
          showSuccessAlert(`✓ "${data.filename}" downloaded! Saved directly to your computer.`);
          loadLibrary();
        } else if (data.status === "failed") {
          activeTasks.delete(taskId);
          showAlert(`Download failed: ${data.error || "Unknown error"}`);
        } else if (data.status === "cancelled") {
          activeTasks.delete(taskId);
        }
      } catch (err) {
        console.error("Error polling task:", err);
      }
    }

    if (activeCountBadge) activeCountBadge.textContent = `${activeCount} Downloading`;
    if (queuedCountBadge) queuedCountBadge.textContent = `${queuedCount} Queued`;

    renderTasks();
  }

  // Render 4-Column Task Grid with Real-Time Speed & Pause/Resume
  function renderTasks() {
    tasksList.innerHTML = "";

    activeTasks.forEach(task => {
      const taskCard = document.createElement("div");
      const isQueued = task.status === "queued";
      const isPaused = task.status === "paused";
      const isProcessing = task.status === "processing";
      const isDownloading = task.status === "downloading";

      taskCard.className = `task-card ${isQueued ? 'is-queued' : ''} ${isPaused ? 'is-paused' : ''}`;

      const title = task.title || task.url || "Media file";
      const progressVal = task.progress || 0;
      let progressBarClass = "progress-bar";

      let statusBadgeHtml = "";
      let speedText = "";
      let metaBottomHtml = "";

      if (isQueued) {
        const queueNum = task.queue_position ? `#${task.queue_position} in line` : "In Queue";
        statusBadgeHtml = `<span class="queued-pill">⏳ ${queueNum}</span>`;
        speedText = "Waiting for worker slot";
        progressBarClass = "progress-bar queued-bar";
        metaBottomHtml = `<span>Auto-starts next</span>`;
      } else if (isPaused) {
        statusBadgeHtml = `<span class="queued-pill" style="color:var(--text-muted); background:rgba(255,255,255,0.08);">⏸️ Paused</span>`;
        speedText = "Download Paused";
        metaBottomHtml = `<span>${progressVal.toFixed(1)}% paused</span>`;
      } else if (isProcessing) {
        statusBadgeHtml = `<span class="queued-pill" style="color:var(--accent-emerald); background:rgba(16,185,129,0.15);">⚙️ Finalizing</span>`;
        speedText = "Processing media...";
        metaBottomHtml = `<span>Almost done...</span>`;
      } else {
        // Real-time downloading speed
        const speed = task.speed_formatted || "Connecting...";
        statusBadgeHtml = `<span class="task-speed">⚡ ${speed}</span>`;
        const eta = task.eta_formatted ? `• ETA ${task.eta_formatted}` : "";
        const downloaded = task.downloaded_formatted ? `${task.downloaded_formatted} / ${task.total_formatted || '?'}` : "";
        metaBottomHtml = `<span>${progressVal.toFixed(1)}% ${downloaded ? '• ' + downloaded : ''}</span><span style="font-size:0.72rem;">${eta}</span>`;
      }

      // Action buttons (Pause/Resume & Cancel)
      let controlBtnHtml = "";
      if (isDownloading) {
        controlBtnHtml = `<button class="btn btn-ghost btn-sm task-ctrl-btn pause-task-btn" title="Pause Download">⏸️</button>`;
      } else if (isPaused) {
        controlBtnHtml = `<button class="btn btn-ghost btn-sm task-ctrl-btn resume-task-btn" title="Resume Download">▶️</button>`;
      }
      controlBtnHtml += `<button class="btn btn-ghost btn-sm task-ctrl-btn cancel-task-btn" title="Cancel Download">✕</button>`;

      taskCard.innerHTML = `
        <div class="task-info-row">
          <span class="task-title" title="${title}">${title}</span>
          <div style="display:flex; align-items:center; gap:4px;">
            ${statusBadgeHtml}
            ${controlBtnHtml}
          </div>
        </div>
        <div class="progress-container">
          <div class="${progressBarClass}" style="width: ${isQueued ? '100%' : progressVal + '%'};"></div>
        </div>
        <div class="task-meta-row">
          ${metaBottomHtml}
        </div>
      `;

      // Control event listeners
      const pauseBtn = taskCard.querySelector(".pause-task-btn");
      if (pauseBtn) pauseBtn.addEventListener("click", () => pauseTask(task.id));

      const resumeBtn = taskCard.querySelector(".resume-task-btn");
      if (resumeBtn) resumeBtn.addEventListener("click", () => resumeTask(task.id));

      const cancelBtn = taskCard.querySelector(".cancel-task-btn");
      if (cancelBtn) cancelBtn.addEventListener("click", () => cancelTask(task.id));

      tasksList.appendChild(taskCard);
    });
  }

  // Load Library / Downloaded Files
  async function loadLibrary() {
    try {
      const res = await fetch("/api/downloads");
      const data = await res.json();

      if (historyCountBadge) historyCountBadge.textContent = data.count || 0;

      if (!data.downloads || data.downloads.length === 0) {
        libraryList.innerHTML = `
          <div class="empty-state">
            <p>No downloads yet. Paste a link or channel name above to start downloading!</p>
          </div>
        `;
        return;
      }

      libraryList.innerHTML = "";

      data.downloads.forEach(file => {
        const fileCard = document.createElement("div");
        fileCard.className = "file-card";

        const isAudio = file.type === "audio";
        const isSub = file.type === "subtitle";
        const isTxt = file.type === "transcript";
        
        let iconSvg = `
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="23 7 16 12 23 17 23 7"></polygon>
            <rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect>
          </svg>
        `;

        if (isAudio) {
          iconSvg = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 18V5l12-2v13"></path>
              <circle cx="6" cy="18" r="3"></circle>
              <circle cx="18" cy="16" r="3"></circle>
            </svg>
          `;
        } else if (isSub || isTxt) {
          iconSvg = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
          `;
        }

        fileCard.innerHTML = `
          <div class="file-icon ${file.type}">
            ${iconSvg}
          </div>
          <div class="file-details">
            <div class="file-name" title="${file.filename}">${file.filename}</div>
            <div class="file-meta">
              <span>${file.size_formatted}</span>
              <span>•</span>
              <span>${file.extension.toUpperCase()}</span>
              <span>•</span>
              <span>${file.modified_formatted}</span>
            </div>
          </div>
          <div class="file-actions">
            ${!isSub && !isTxt ? `
            <button class="btn btn-play-preview play-file-btn" data-filename="${file.filename}" data-stream="${file.stream_url}" data-type="${file.type}" title="Play in App (Feature 7)">
              <svg viewBox="0 0 24 24" fill="currentColor" style="width:14px;height:14px;">
                <polygon points="5 3 19 12 5 21 5 3"></polygon>
              </svg>
              Play
            </button>` : ''}
            <a href="${file.download_url}" target="_blank" class="btn btn-ghost" title="Save browser copy" download>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
            </a>
            <button class="btn btn-danger-ghost delete-file-btn" data-filename="${file.filename}" title="Delete file from disk">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px;">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </div>
        `;

        // Feature 7: Play Button listener
        const playBtn = fileCard.querySelector(".play-file-btn");
        if (playBtn) {
          playBtn.addEventListener("click", () => {
            openPlayerModal(file.filename, file.stream_url, file.type);
          });
        }

        const deleteBtn = fileCard.querySelector(".delete-file-btn");
        deleteBtn.addEventListener("click", async () => {
          if (confirm(`Permanently delete "${file.filename}" from disk?`)) {
            await deleteFile(file.filename);
          }
        });

        libraryList.appendChild(fileCard);
      });
    } catch (err) {
      console.error("Failed to load library:", err);
    }
  }

  async function deleteFile(filename) {
    try {
      const res = await fetch("/api/delete-file", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename })
      });
      if (res.ok) {
        showSuccessAlert(`Deleted ${filename}`);
        loadLibrary();
      } else {
        showAlert("Could not delete file.");
      }
    } catch (e) {
      showAlert("Error deleting file.");
    }
  }

  function formatBytes(size) {
    if (!size) return "0 B";
    const units = ['B', 'KB', 'MB', 'GB'];
    let idx = 0;
    while (size >= 1024 && idx < units.length - 1) {
      size /= 1024;
      idx++;
    }
    return `${size.toFixed(1)} ${units[idx]}`;
  }
});
