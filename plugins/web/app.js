(() => {
  "use strict";

  const brandName = document.body.dataset.brand || "Anime Eternals";

  // ---------------------------------------------------------------------
  // Telegram WebApp bootstrap (no-ops gracefully outside Telegram)
  // ---------------------------------------------------------------------
  const tg = window.Telegram && window.Telegram.WebApp;
  if (tg) {
    try {
      tg.ready();
      tg.expand();
    } catch (e) { /* not fatal */ }
  }
  const initData = tg ? tg.initData : "";

  if (tg) {
    try {
      tg.setHeaderColor && tg.setHeaderColor("#131310");
      tg.setBackgroundColor && tg.setBackgroundColor("#131310");
    } catch (e) { /* not fatal */ }
  }

  function authHeaders() {
    return initData ? { "X-Telegram-Init-Data": initData } : {};
  }

  function showWebsiteDown() {
    if (document.getElementById("website-down-overlay")) return;
    const overlay = document.createElement("div");
    overlay.id = "website-down-overlay";
    overlay.style.cssText = "position:fixed;inset:0;z-index:99999;background:#0d0d0d;display:flex;align-items:center;justify-content:center;padding:24px;text-align:center;";
    overlay.innerHTML = `
      <div style="max-width:340px;width:100%;background:#1a1a1a;border:1px solid rgba(255,255,255,0.08);border-radius:18px;padding:32px 24px;">
        <div style="font-size:42px;margin-bottom:12px;">⚠</div>
        <h1 style="font-size:20px;font-weight:700;margin:0 0 8px;color:#e8e8e8;">Website is temporarily down</h1>
        <p style="font-size:14px;color:rgba(255,255,255,0.55);line-height:1.45;margin:0 0 20px;">We're updating the service. Please try again in a few minutes.</p>
        <button type="button" style="border:none;border-radius:12px;padding:12px 22px;background:linear-gradient(135deg,#1f5628,#2d7a3a);color:#fff;font-weight:700;font-size:14px;cursor:pointer;width:100%;" onclick="location.reload()">Try Again</button>
      </div>`;
    document.body.appendChild(overlay);
  }

  async function api(path, options = {}) {
    let res;
    try {
      res = await fetch(path, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(),
          ...(options.headers || {}),
        },
      });
    } catch (e) {
      // Network / DNS / offline — show friendly down screen
      showWebsiteDown();
      throw new Error("Network error");
    }
    if (!res.ok) {
      if (res.status === 502 || res.status === 503 || res.status === 504) {
        showWebsiteDown();
      }
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `Request failed (${res.status})`);
    }
    return res.json();
  }

  function debounce(fn, ms) {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), ms);
    };
  }

  // ---------------------------------------------------------------------
  // Generated placeholder thumbnail — used whenever an image is missing
  // or fails to load, so nothing ever shows a broken image icon.
  // ---------------------------------------------------------------------
  function hashStr(str) {
    let h = 0;
    for (let i = 0; i < (str || "").length; i++) {
      h = str.charCodeAt(i) + ((h << 5) - h);
      h |= 0;
    }
    return Math.abs(h);
  }

  const PALETTES = [
    ["#3a0ca3", "#f72585"], ["#7209b7", "#4361ee"], ["#ff6b35", "#9d0208"],
    ["#0b132b", "#5bc0be"], ["#22223b", "#c9184a"], ["#231942", "#e0b1cb"],
    ["#03045e", "#00b4d8"], ["#590d22", "#ff8fa3"], ["#1b4332", "#95d5b2"],
    ["#3d0000", "#ff6d00"], ["#14213d", "#fca311"], ["#240046", "#5a189a"],
  ];

  function generatedThumb(title) {
    const h = hashStr(title);
    const [c1, c2] = PALETTES[h % PALETTES.length];
    const angle = 110 + (h % 140);
    const div = document.createElement("div");
    div.className = "generated-thumb";
    div.style.background = `linear-gradient(${angle}deg, ${c1}, ${c2})`;
    return div;
  }

  function thumbImg(container, src, title) {
    if (!src) {
      container.appendChild(generatedThumb(title));
      return;
    }
    const img = document.createElement("img");
    img.loading = "lazy";
    img.src = src;
    img.alt = title;
    img.onerror = () => img.replaceWith(generatedThumb(title));
    container.appendChild(img);
  }

  // ---------------------------------------------------------------------
  // Elements
  // ---------------------------------------------------------------------
  const el = (id) => document.getElementById(id);

  const appView = el("app-view");
  const searchView = el("search-view");
  const genreView = el("genre-view");
  const profileView = el("profile-view");
  const allViews = { app: appView, search: searchView, genre: genreView, profile: profileView };

  const searchViewInput = el("search-view-input");
  const searchResults = el("search-results");
  const searchResultsGroups = el("search-results-groups");
  const searchResultsEmpty = el("search-results-empty");
  const searchLanding = el("search-landing");
  const popularSearchList = el("popular-search-list");
  const popularSearchRefresh = el("popular-search-refresh");
  const recentSearchSection = el("recent-search-section");
  const recentSearchList = el("recent-search-list");
  const recentSearchClear = el("recent-search-clear");
  const genreTileGrid = el("genre-tile-grid");
  const genreBrowseGrid = el("genre-browse-grid");
  const genreViewTitle = el("genre-view-title");
  const genreLoadMoreBtn = el("genre-load-more");
  const genreEmptyNote = el("genre-empty");

  const pillTabs = document.querySelectorAll(".pill-tab[data-tab]");
  const tabAll = el("tab-all");
  const tabLibrary = el("tab-library");

  const scrollArea = el("scroll-area");
  const trendingRow = el("trending-row");
  const topAiringList = el("top-airing-list");
  const popularLoadMore = el("popular-load-more");
  const popularGridList = el("popular-grid-list");
  const popularGridLoadMoreBtn = el("popular-grid-load-more");

  const letterBar = el("letter-bar");
  const availableGroups = el("available-groups");
  const availableEmpty = el("available-empty");
  const dayBar = el("day-bar");
  const ongoingGroups = el("ongoing-groups");
  const ongoingEmpty = el("ongoing-empty");
  const finishedPanel = el("finished-panel");
  const ongoingPanel = el("ongoing-panel");
  const libraryModeTabs = document.querySelectorAll("[data-library-mode]");

  const navBtns = document.querySelectorAll(".nav-btn");

  const detailOverlay = el("detail-overlay");
  const detailPoster = el("detail-poster");
  const detailTitle = el("detail-title");
  const detailSubtitle = el("detail-subtitle");
  const detailMetaPills = el("detail-meta-pills");
  const detailGenres = el("detail-genres");
  const detailDescription = el("detail-description");
  const detailReadMore = el("detail-readmore");
  const detailRelated = el("detail-related");
  const detailActionArea = el("detail-action-area");
  const reportOpenBtn = el("report-open-btn");

  const linkOverlay = el("link-overlay");
  const linkInput = el("link-input");

  const headerSearchBtn = el("header-search-btn");
  const profileBtn = el("profile-btn");
  const notifBtn = el("notif-btn");
  const notifBadge = el("notif-badge");
  const notifOverlay = el("notif-overlay");
  const notifList = el("notif-list");
  const notifEmpty = el("notif-empty");
  const notifClose = el("notif-close");

  const reportOverlay = el("report-overlay");
  const reportDetails = el("report-details");
  let selectedReason = null;

  const profileCard = el("profile-card");

  const toast = el("toast");
  let toastTimer = null;

  function showToast(msg) {
    toast.textContent = msg;
    toast.classList.remove("hidden");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.add("hidden"), 2200);
  }

  // ---------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------
  let trending = [];
  let popular = [];
  let popularPage = 1;
  let popularHasNext = false;
  let mostPopular = [];
  let mostPopularPage = 1;
  let mostPopularHasNext = false;
  let mostPopularLoading = false;
  let available = [];
  let activeLetter = null;
  let activeDay = null;           // null = ALL days
  let libraryQuery = "";
  let libraryMode = "finished"; // "finished" | "ongoing"
  const WEEKDAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];
  const WEEKDAY_LABELS = { sunday: "SUN", monday: "MON", tuesday: "TUE", wednesday: "WED", thursday: "THU", friday: "FRI", saturday: "SAT" };
  let profile = null;

  const ALL_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
  // "#" comes first, same convention as Spotify/Apple Music/contacts apps,
  // and catches anything starting with a digit — e.g. "86 -Eighty Six-",
  // "5 Centimeters per Second", "009-1" — which would otherwise not match
  // any A-Z button and become an orphaned, unreachable group.
  const INDEX_KEYS = ["#", ...ALL_LETTERS];

  function indexKeyFor(title) {
    const ch = (title[0] || "").toUpperCase();
    return /[0-9]/.test(ch) ? "#" : ch;
  }

  function buildAvailableIndex() {
    // Matching purely by title text (the old approach) silently breaks
    // whenever the posted library entry's title and the AniList discovery
    // feed's title differ even slightly — different EN/romaji preference,
    // punctuation, a manually edited title, etc. — so a join link you just
    // added shows up in "Available" but the same anime in "All" still
    // looks unlinked. AniList ids are stable, so prefer matching on that
    // and only fall back to title text when an id isn't available.
    const byId = new Map();
    const byTitle = new Map();
    available.forEach((a) => {
      if (a.source === "anilist" && a.source_id != null) {
        byId.set(String(a.source_id), a);
      }
      byTitle.set(a.title.toLowerCase(), a);
    });
    return {
      match(item) {
        if (item.anilist_id != null) {
          const m = byId.get(String(item.anilist_id));
          if (m) return m;
        }
        return byTitle.get((item.title || "").toLowerCase()) || null;
      },
    };
  }

  // ---------------------------------------------------------------------
  // Top-level navigation (Home / Search / Profile)
  // ---------------------------------------------------------------------
  function showView(name) {
    Object.entries(allViews).forEach(([key, node]) => node.classList.toggle("hidden", key !== name));
    navBtns.forEach((b) => b.classList.toggle("active", b.dataset.nav === (name === "app" ? "home" : name)));
  }

  navBtns.forEach((btn) => btn.addEventListener("click", () => {
    const target = btn.dataset.nav;
    if (target === "home") showView("app");
    else if (target === "search") { showView("search"); renderSearchLanding(); }
    else if (target === "profile") { showView("profile"); openProfile(); }
  }));

  if (profileBtn) {
    profileBtn.addEventListener("click", () => { showView("profile"); openProfile(); });
  }

  // Header avatar — shows the user's real Telegram profile photo when the
  // client exposes one, falling back to the generic person icon otherwise.
  function renderHeaderAvatar() {
    if (!profileBtn) return;
    const photoUrl = tg && tg.initDataUnsafe && tg.initDataUnsafe.user && tg.initDataUnsafe.user.photo_url;
    if (!photoUrl) return;
    const img = document.createElement("img");
    img.src = photoUrl;
    img.alt = "Profile";
    img.className = "header-avatar-img";
    img.onerror = () => { profileBtn.innerHTML = "&#128100;"; };
    profileBtn.innerHTML = "";
    profileBtn.appendChild(img);
  }
  renderHeaderAvatar();

  // Header search icon is a shortcut into the dedicated Search page.
  if (headerSearchBtn) {
    headerSearchBtn.addEventListener("click", () => {
      showView("search");
      renderSearchLanding();
      setTimeout(() => searchViewInput.focus(), 50);
    });
  }

  document.querySelectorAll("[data-back]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.back;
      if (target === "home") showView("app");
      else if (target === "search") showView("search");
    });
  });

  // ---------------------------------------------------------------------
  // Poster / card builders
  // ---------------------------------------------------------------------
  function simplePosterCard(item, onOpen) {
    const card = document.createElement("div");
    card.className = "poster-card";

    // Prefer higher-quality poster when available
    const src = item.poster_url || item.cover_url || item.banner_url || "";
    const img = document.createElement("img");
    img.loading = "lazy";
    img.decoding = "async";
    img.src = src;
    img.alt = item.title || "";
    img.onerror = () => {
      img.replaceWith(generatedThumb(item.title || "Anime"));
    };
    card.appendChild(img);

    if (item.rating) {
      const rating = document.createElement("span");
      rating.className = "poster-rating";
      rating.textContent = "★ " + Number(item.rating).toFixed(1);
      card.appendChild(rating);
    }

    const meta = document.createElement("div");
    meta.className = "poster-meta";
    const title = document.createElement("p");
    title.className = "poster-title";
    title.textContent = item.title || "Untitled";
    meta.appendChild(title);
    // Genres removed from front/grid view — title only

    card.appendChild(meta);
    card.addEventListener("click", onOpen);
    return card;
  }

  function trendingCard(item, onOpen) {
    return posterScrollCard(item, onOpen, null, null);
  }

  function topAiringCard(item, onOpen) {
    return posterScrollCard(item, onOpen, null, null);
  }

  function popularGridCard(item, onOpen) {
    return posterScrollCard(item, onOpen, null, null);
  }

  function posterScrollCard(item, onOpen, badgeText, badgeClass) {
    const card = document.createElement("div");
    card.className = "poster-card";

    // Prefer higher-quality poster when available
    const src = item.poster_url || item.cover_url || item.banner_url || "";
    const img = document.createElement("img");
    img.loading = "lazy";
    img.decoding = "async";
    img.src = src;
    img.alt = item.title || "";
    img.onerror = () => {
      img.replaceWith(generatedThumb(item.title || "Anime"));
    };
    card.appendChild(img);

    if (badgeText) {
      const badge = document.createElement("span");
      badge.className = badgeClass;
      badge.textContent = badgeText;
      card.appendChild(badge);
    }

    if (item.rating) {
      const rating = document.createElement("span");
      rating.className = "poster-rating";
      rating.textContent = "★ " + Number(item.rating).toFixed(1);
      card.appendChild(rating);
    }

    const meta = document.createElement("div");
    meta.className = "poster-meta";
    const title = document.createElement("p");
    title.className = "poster-title";
    title.textContent = item.title || "Untitled";
    meta.appendChild(title);
    // Genres removed from front/grid view — title only
    card.appendChild(meta);

    card.addEventListener("click", onOpen);
    return card;
  }

  function matchesLibraryQuery(title) {
    return !libraryQuery || title.toLowerCase().includes(libraryQuery.toLowerCase());
  }

  // ---------------------------------------------------------------------
  // Render: Home "All" tab — Trending, Top Airing (+ Load more)
  // ---------------------------------------------------------------------

  // Shimmer placeholders shown the instant the Home tab opens, replaced as
  // soon as each section's real data arrives — makes first load (and any
  // cold-start delay while the server/cache spins back up) feel immediate
  // instead of showing blank space under each header.
  function renderSkeletonRow(container, count) {
    if (!container) return;
    container.innerHTML = "";
    for (let i = 0; i < count; i++) {
      const card = document.createElement("div");
      card.className = "skeleton-card";
      container.appendChild(card);
    }
  }

  function _emptyNote(text) {
    const p = document.createElement("p");
    p.className = "empty-note";
    p.style.padding = "8px 4px";
    p.textContent = text;
    return p;
  }

  function renderTrending() {
    if (!trendingRow) return;
    trendingRow.innerHTML = "";
    if (!trending.length) {
      trendingRow.appendChild(_emptyNote("No trending titles yet — retrying…"));
      return;
    }
    const availIndex = buildAvailableIndex();
    trending.forEach((item) => {
      const matched = availIndex.match(item);
      item.matchedJoinLink = matched && matched.join_link ? matched.join_link : null;
      trendingRow.appendChild(trendingCard(item, () => openDiscoverDetail(item)));
    });
  }

  function renderTopAiring() {
    if (!topAiringList) return;
    topAiringList.innerHTML = "";
    if (!popular.length) {
      topAiringList.appendChild(_emptyNote("No airing titles yet — retrying…"));
      return;
    }
    const availIndex = buildAvailableIndex();
    popular.forEach((item) => {
      const matched = availIndex.match(item);
      item.matchedJoinLink = matched && matched.join_link ? matched.join_link : null;
      topAiringList.appendChild(topAiringCard(item, () => openDiscoverDetail(item)));
    });
  }

  let popularLoading = false;
  async function loadMorePopular() {
    if (popularLoading || !popularHasNext) return;
    popularLoading = true;
    popularLoadMore.classList.remove("hidden");
    try {
      const data = await api(`/api/catalog/popular?page=${popularPage + 1}`);
      popularPage += 1;
      popular = popular.concat(data.results);
      popularHasNext = data.has_next;
      renderTopAiring();
    } catch (err) {
      showToast("Couldn't load more right now.");
    }
    popularLoadMore.classList.add("hidden");
    popularLoading = false;
  }

  // Discovery sections now live on the Search page — no home auto-load.

  function renderPopularGrid() {
    if (!popularGridList) return;
    popularGridList.innerHTML = "";
    if (!mostPopular.length) {
      popularGridList.appendChild(_emptyNote("No popular titles yet — retrying…"));
      if (popularGridLoadMoreBtn) popularGridLoadMoreBtn.classList.add("hidden");
      return;
    }
    const availIndex = buildAvailableIndex();
    mostPopular.forEach((item) => {
      const matched = availIndex.match(item);
      item.matchedJoinLink = matched && matched.join_link ? matched.join_link : null;
      popularGridList.appendChild(popularGridCard(item, () => openDiscoverDetail(item)));
    });
    popularGridLoadMoreBtn.classList.toggle("hidden", !mostPopularHasNext);
  }

  // Prefetch the next Popular page so "Load more" feels instant
  let mostPopularPrefetch = null; // { page, promise }

  function prefetchMostPopularPage(page) {
    if (!page || page < 2) return;
    if (mostPopularPrefetch && mostPopularPrefetch.page === page) return;
    mostPopularPrefetch = {
      page,
      promise: api(`/api/catalog/most-popular?page=${page}`)
        .then((data) => data)
        .catch(() => null),
    };
  }

  async function loadMorePopularGrid() {
    if (mostPopularLoading || !mostPopularHasNext) return;
    mostPopularLoading = true;
    popularGridLoadMoreBtn.disabled = true;
    popularGridLoadMoreBtn.textContent = "Loading…";
    const nextPage = mostPopularPage + 1;
    try {
      let data = null;
      if (mostPopularPrefetch && mostPopularPrefetch.page === nextPage) {
        data = await mostPopularPrefetch.promise;
        mostPopularPrefetch = null;
      }
      if (!data || !Array.isArray(data.results)) {
        data = await api(`/api/catalog/most-popular?page=${nextPage}`);
      }
      mostPopularPage = nextPage;
      mostPopular = mostPopular.concat(data.results || []);
      mostPopularHasNext = !!data.has_next;
      renderPopularGrid();
      // Warm the following page in the background
      if (mostPopularHasNext) prefetchMostPopularPage(mostPopularPage + 1);
    } catch (err) {
      showToast("Couldn't load more right now.");
    }
    popularGridLoadMoreBtn.disabled = false;
    popularGridLoadMoreBtn.textContent = "Load more";
    mostPopularLoading = false;
  }

  popularGridLoadMoreBtn.addEventListener("click", loadMorePopularGrid);

  // Home is Available-only (# + A–Z). Discovery (All) lives on Search page.
  function setPillTab(tab) {
    if (pillTabs && pillTabs.length) {
      pillTabs.forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
    }
    if (tabAll) tabAll.classList.toggle("hidden", tab !== "all");
    if (tabLibrary) tabLibrary.classList.toggle("hidden", tab !== "library");
    if (tab === "library") renderLibraryTab();
  }
  if (pillTabs && pillTabs.length) {
    pillTabs.forEach((b) => b.addEventListener("click", () => setPillTab(b.dataset.tab)));
  }

  // ---------------------------------------------------------------------
  // Render: Available/library tab (posted catalog, A–Z)
  // ---------------------------------------------------------------------
  function isFullyReleased(a) {
    const st = (a.status || "").toUpperCase();
    return st === "FINISHED" || st === "COMPLETED" || st === "CANCELLED" || st === "";
  }

  function pickGroupPrimary(group) {
    // All seasons card: prefer latest FULLY RELEASED season as the front cover.
    // When a newer season finishes airing it becomes the new primary automatically.
    const released = group.filter(isFullyReleased);
    const pool = released.length ? released : group.slice();
    pool.sort((x, y) => (y.year || 0) - (x.year || 0) || (y.id || 0) - (x.id || 0));
    return pool[0];
  }

  function isSoloCard(a) {
    // Own Finished card when Solo link is set, or legacy display_mode=solo.
    return !!(a && (a.solo_link || (a.display_mode || "group") === "solo"));
  }

  function primaryAvailableList() {
    // Franchise grouping for Finished tab:
    // - solo_link / display_mode "solo" → always its own card (can coexist with the group card)
    // - display_mode "group" (default) → one card per franchise = latest full release
    const bySourceId = new Map();
    available.forEach((a) => {
      if (a.source === "anilist" && a.source_id != null) bySourceId.set(String(a.source_id), a);
    });

    const visited = new Set();
    const primaries = [];

    // Solo titles (solo_link or display_mode=solo) always appear on their own
    available.forEach((a) => {
      if (isSoloCard(a)) {
        primaries.push(a);
        visited.add(String(a.id));
      }
    });

    available.forEach((start) => {
      const startKey = String(start.id);
      if (visited.has(startKey)) return;

      const group = [];
      const frontier = [start];
      const localSeen = new Set([startKey]);
      while (frontier.length) {
        const cur = frontier.pop();
        // Skip solo members — they already have their own card
        if (isSoloCard(cur)) continue;
        group.push(cur);
        (cur.related_ids || []).forEach((rid) => {
          const relItem = bySourceId.get(String(rid));
          if (relItem && !localSeen.has(String(relItem.id))) {
            localSeen.add(String(relItem.id));
            frontier.push(relItem);
          }
        });
      }
      group.forEach((g) => visited.add(String(g.id)));

      if (!group.length) return;
      primaries.push(pickGroupPrimary(group));
    });

    return primaries;
  }

  function isOngoing(a) {
    // Ongoing tab: ONLY currently airing seasons (AniList RELEASING).
    // FINISHED / CANCELLED / HIATUS / NOT_YET_RELEASED / blank never appear here.
    const st = (a.status || "").toUpperCase();
    return st === "RELEASING";
  }

  // Title-based schedule fallback when AniList has no airing day
  const TITLE_AIRING_DAY = [
    { day: "monday", re: /grand\s*blue/i },
    { day: "tuesday", re: /clevatess/i },
    { day: "thursday", re: /smoking\s*behind\s*the\s*supermarket/i },
    { day: "friday", re: /reincarnated\s*as\s*a\s*slime|tensei\s*shitara\s*slime/i },
    { day: "saturday", re: /bleach.*thousand|thousand[-\s]?year\s*blood/i },
    { day: "saturday", re: /detective\s*conan|case\s*closed|meitantei\s*conan/i },
    { day: "saturday", re: /pok[eé]mon/i },
    { day: "sunday", re: /mushoku\s*tensei|jobless\s*reincarnation/i },
    { day: "sunday", re: /\bone\s*piece\b/i },
  ];

  function effectiveAiringDay(a) {
    const stored = (a.airing_day || "").toLowerCase().trim();
    if (stored) return stored;
    const title = `${a.title || ""} ${a.alt_title || ""}`;
    for (const row of TITLE_AIRING_DAY) {
      if (row.re.test(title)) return row.day;
    }
    return null;
  }

  function effectiveJoinLink(anime) {
    // Ongoing tab prefers ongoing_link.
    // Finished: solo cards use solo_link; group cards use join_link (All seasons).
    if (!anime) return null;
    if (libraryMode === "ongoing") {
      return anime.ongoing_link || anime.solo_link || anime.join_link || anime.matchedJoinLink || null;
    }
    if ((anime.display_mode || "group") === "solo" || anime.solo_link) {
      return anime.solo_link || anime.join_link || anime.matchedJoinLink || null;
    }
    return anime.join_link || anime.matchedJoinLink || null;
  }

  function finishedList() {
    // Finished column: cards with any finished path (group join_link, solo_link, or match).
    // Fully-released titles with only ongoing_link still appear as a fallback.
    return primaryAvailableList().filter((a) => {
      if (a.join_link || a.solo_link || a.matchedJoinLink) return true;
      if (!isOngoing(a) && a.ongoing_link) return true;
      return false;
    });
  }

  function ongoingList() {
    // Only currently airing seasons (RELEASING / HIATUS). Previous seasons of
    // the same franchise drop out once their status is FINISHED. Each airing
    // season is its own card (no franchise merge on this tab).
    return available.filter((a) => isOngoing(a));
  }

  function lettersWithData() {
    return new Set(finishedList().map((a) => indexKeyFor(a.title)));
  }

  function daysWithData() {
    return new Set(ongoingList().map((a) => effectiveAiringDay(a)).filter(Boolean));
  }

  function filteredFinished() {
    let list = finishedList();
    if (libraryQuery.trim()) {
      list = list.filter((a) => matchesLibraryQuery(a.title));
    } else if (activeLetter) {
      list = list.filter((a) => indexKeyFor(a.title) === activeLetter);
    }
    return [...list].sort((a, b) => a.title.localeCompare(b.title));
  }

  function filteredOngoing() {
    // Flat list of currently airing titles — no weekday grouping or day filter.
    let list = ongoingList();
    if (libraryQuery.trim()) {
      list = list.filter((a) => matchesLibraryQuery(a.title));
    }
    return [...list].sort((a, b) => a.title.localeCompare(b.title));
  }

  function renderLetterBar() {
    if (!letterBar) return;
    letterBar.innerHTML = "";
    const has = lettersWithData();
    INDEX_KEYS.forEach((l) => {
      const btn = document.createElement("button");
      btn.className = "letter-btn" + (activeLetter === l ? " active" : "");
      btn.textContent = l;
      btn.disabled = !has.has(l);
      btn.addEventListener("click", () => {
        libraryQuery = "";
        activeLetter = activeLetter === l ? null : l;
        renderLibraryTab();
      });
      letterBar.appendChild(btn);
    });
  }

  function renderDayBar() {
    if (!dayBar) return;
    dayBar.innerHTML = "";
    const has = daysWithData();
    // ALL | Sun | Mon | ...
    const allBtn = document.createElement("button");
    allBtn.className = "letter-btn" + (activeDay == null ? " active" : "");
    allBtn.textContent = "ALL";
    allBtn.addEventListener("click", () => {
      libraryQuery = "";
      activeDay = null;
      renderLibraryTab();
    });
    dayBar.appendChild(allBtn);

    WEEKDAYS.forEach((d) => {
      const btn = document.createElement("button");
      // Always enabled — titles that don't air this day simply aren't listed here;
      // they still appear under ALL.
      btn.className = "letter-btn" + (activeDay === d ? " active" : "");
      btn.textContent = WEEKDAY_LABELS[d];
      btn.addEventListener("click", () => {
        libraryQuery = "";
        activeDay = d;
        renderLibraryTab();
      });
      dayBar.appendChild(btn);
    });
  }

  function renderGroupedGrid(container, emptyEl, list, groupKeyFn, labelFn) {
    if (!container) return;
    container.innerHTML = "";
    if (emptyEl) emptyEl.classList.toggle("hidden", list.length !== 0);

    const groups = {};
    list.forEach((a) => {
      const k = groupKeyFn(a);
      (groups[k] = groups[k] || []).push(a);
    });

    const keys = Object.keys(groups).sort((a, b) => {
      // ALL / TBA bucket first, then weekday order
      const rank = (k) => {
        if (k === "all" || k === "tba") return -1;
        const i = WEEKDAYS.indexOf(k);
        return i >= 0 ? i : 100;
      };
      const ra = rank(a), rb = rank(b);
      if (ra !== rb) return ra - rb;
      return a.localeCompare(b);
    });

    keys.forEach((key) => {
      const wrap = document.createElement("div");
      wrap.className = "letter-group";
      const label = (labelFn(key) || "").trim();
      if (label) {
        const header = document.createElement("div");
        header.className = "letter-group-header";
        header.innerHTML = `<span class="letter-group-label">${label}</span><span class="letter-group-line"></span>`;
        wrap.appendChild(header);
      }
      const grid = document.createElement("div");
      grid.className = "available-grid";
      groups[key].forEach((item) => {
        grid.appendChild(simplePosterCard(item, () => openLocalDetail(item)));
      });
      wrap.appendChild(grid);
      container.appendChild(wrap);
    });
  }

  function setLibraryMode(mode) {
    libraryMode = mode === "ongoing" ? "ongoing" : "finished";
    libraryModeTabs.forEach((b) => {
      b.classList.toggle("active", b.dataset.libraryMode === libraryMode);
    });
    if (finishedPanel) finishedPanel.classList.toggle("hidden", libraryMode !== "finished");
    if (ongoingPanel) ongoingPanel.classList.toggle("hidden", libraryMode !== "ongoing");
    renderLibraryTab();
  }

  if (libraryModeTabs && libraryModeTabs.length) {
    libraryModeTabs.forEach((b) => {
      b.addEventListener("click", () => setLibraryMode(b.dataset.libraryMode));
    });
  }

  let _airingDaysRefreshDone = false;

  async function autoRefreshAiringDays() {
    // Silent one-shot: pull fresh AniList status + airing_day so Ongoing is
    // accurate. Many library rows still say FINISHED after a new season started.
    if (_airingDaysRefreshDone) return;
    _airingDaysRefreshDone = true;
    try {
      // force:true so stale FINISHED / blank status rows get corrected too
      const result = await api("/api/admin/refresh-airing-days", {
        method: "POST",
        body: JSON.stringify({ force: true }),
      });
      if (result && ((result.updated || 0) > 0 || (result.status_updated || 0) > 0 || (result.failed || 0) >= 0)) {
        await loadAvailable();
        if (libraryMode === "ongoing") renderLibraryTab();
      }
    } catch (err) {
      _airingDaysRefreshDone = false;
    }
  }

  function renderLibraryTab() {
    if (libraryMode === "ongoing") {
      // Hide day chips — Ongoing is a flat list of airing titles
      if (dayBar) {
        dayBar.innerHTML = "";
        dayBar.classList.add("hidden");
      }
      const list = filteredOngoing();
      if (!ongoingGroups) return;
      // Single flat grid (A–Z by title), no weekday sections
      renderGroupedGrid(
        ongoingGroups,
        ongoingEmpty,
        list,
        () => "all",
        () => ""
      );
      // Still backfill airing_day/status in the background for accuracy
      autoRefreshAiringDays();
    } else {
      if (dayBar) dayBar.classList.add("hidden");
      renderLetterBar();
      const list = filteredFinished();
      renderGroupedGrid(
        availableGroups,
        availableEmpty,
        list,
        (a) => indexKeyFor(a.title),
        (k) => k
      );
    }
  }

  // ---------------------------------------------------------------------
  // Detail sheet (compact centered modal)
  // ---------------------------------------------------------------------
  let currentDetail = null;
  let currentContext = null; // "available" | "discover" | "genre"
  let descriptionExpanded = false;

  function openDetailSheet(anime, context) {
    const prevBannerSrc = currentDetail ? (currentDetail.banner_url || currentDetail.poster_url) : null;
    currentDetail = anime;
    currentContext = context;
    descriptionExpanded = false;

    const sheetMedia = detailPoster.parentElement;
    const hasRealBanner = !!anime.banner_url;
    const bannerSrc = anime.banner_url || anime.poster_url;

    // openDiscoverDetail (and friends) call this twice per tap: once
    // immediately with placeholder data, then again once the full AniList
    // details resolve. When it's the same artwork both times, skip
    // re-doing the poster/blurred-backdrop work below — reloading the
    // image and re-rasterizing the blur filter on every follow-up call is
    // what made back-to-back opens feel janky, since the browser did that
    // heavy repaint work even though nothing visually needed to change.
    if (bannerSrc !== prevBannerSrc) {
      sheetMedia.querySelectorAll(".generated-thumb").forEach((n) => n.remove());
      detailPoster.src = "";
      detailPoster.style.display = "";
      // A true banner is already wide, so a centered cover-crop looks right.
      // A portrait poster forced into that same short, wide box can't be
      // cover-cropped without zooming in hard and losing most of the art
      // (usually landing on a jarring close-up of just the eyes). Instead,
      // show it uncropped over a blurred version of itself as a backdrop.
      detailPoster.classList.toggle("poster-fallback", !hasRealBanner);
      sheetMedia.classList.toggle("has-blur-bg", !hasRealBanner && !!bannerSrc);
      if (!hasRealBanner && bannerSrc) {
        sheetMedia.style.setProperty("--banner-img", `url("${bannerSrc}")`);
      } else {
        sheetMedia.style.removeProperty("--banner-img");
      }
      if (bannerSrc) {
        detailPoster.src = bannerSrc;
        detailPoster.onerror = () => {
          detailPoster.style.display = "none";
          sheetMedia.classList.remove("has-blur-bg");
          const gen = generatedThumb(anime.title);
          gen.style.position = "absolute";
          gen.style.inset = "0";
          gen.style.zIndex = "1";
          sheetMedia.insertBefore(gen, detailPoster);
        };
      } else {
        detailPoster.style.display = "none";
        const gen = generatedThumb(anime.title);
        gen.style.position = "absolute";
        gen.style.inset = "0";
        sheetMedia.insertBefore(gen, detailPoster);
      }
    }

    detailTitle.textContent = anime.title;
    if (anime.alt_title) {
      detailSubtitle.textContent = anime.alt_title;
      detailSubtitle.classList.remove("hidden");
    } else {
      detailSubtitle.classList.add("hidden");
    }

    detailMetaPills.innerHTML = "";
    if (anime.format) addMetaPill(anime.format);
    if (anime.year) addMetaPill(String(anime.year));
    if (anime.duration) addMetaPill(`${anime.duration}m`);
    if (anime.rating) addMetaPill(`\u2605 ${anime.rating.toFixed(1)}`, true);

    detailGenres.innerHTML = "";
    (anime.genres || []).forEach((g) => {
      const pill = document.createElement("span");
      pill.className = "genre-pill";
      pill.textContent = g;
      detailGenres.appendChild(pill);
    });

    renderDescription();
    renderRelated(anime);
    renderDetailAction(anime, context);
    detailOverlay.classList.remove("hidden");
    document.body.style.overflow = "hidden";
  }

  function addMetaPill(text, isRating = false) {
    const pill = document.createElement("span");
    pill.className = "meta-pill" + (isRating ? " rating" : "");
    pill.textContent = text;
    detailMetaPills.appendChild(pill);
  }

  function renderDescription() {
    const text = currentDetail.description || "No synopsis available.";
    detailDescription.textContent = text;
    detailDescription.scrollTop = 0;
    detailDescription.classList.toggle("clamped", !descriptionExpanded);
    detailDescription.classList.toggle("expanded", descriptionExpanded);
    detailReadMore.classList.toggle("hidden", text.length < 180);
    detailReadMore.textContent = descriptionExpanded ? "Show Less" : "Read More";
  }

  function humanizeRelationType(type) {
    return (type || "")
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
      .join(" ");
  }

  function renderRelated(anime) {
    detailRelated.innerHTML = "";
    const related = anime.related_posted || [];
    detailRelated.classList.toggle("hidden", related.length === 0);
    related.forEach((rel) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "related-card";

      const thumb = document.createElement("div");
      thumb.className = "related-card-thumb";
      thumbImg(thumb, rel.poster_url, rel.title);
      card.appendChild(thumb);

      const text = document.createElement("div");
      text.className = "related-card-text";
      const label = document.createElement("span");
      label.className = "related-card-label";
      const typeLabel = humanizeRelationType(rel.relation_type).toUpperCase();
      if (rel.relation_type === "PREQUEL") label.textContent = "\u25c0 " + typeLabel;
      else if (rel.relation_type === "SEQUEL") label.textContent = typeLabel + " \u25b6";
      else label.textContent = typeLabel;
      const title = document.createElement("span");
      title.className = "related-card-title";
      title.textContent = rel.title;
      text.appendChild(label);
      text.appendChild(title);
      card.appendChild(text);

      card.addEventListener("click", () => openRelatedDetail(rel.id));
      detailRelated.appendChild(card);
    });
  }

  async function openRelatedDetail(localAnimeId) {
    try {
      const full = await api(`/api/anime/${localAnimeId}`);
      openDetailSheet(full, "available");
    } catch (err) {
      showToast("Couldn't load that title.");
    }
  }

  detailReadMore.addEventListener("click", () => {
    descriptionExpanded = !descriptionExpanded;
    renderDescription();
  });

  function closeDetailSheet() {
    detailOverlay.classList.add("hidden");
    document.body.style.overflow = "";
    currentDetail = null;
    currentContext = null;
  }
  el("detail-close").addEventListener("click", closeDetailSheet);
  detailOverlay.addEventListener("click", (e) => {
    if (e.target === detailOverlay) closeDetailSheet();
  });

  function openJoinUrl(url) {
    if (!url) return;
    if (tg && tg.openLink) tg.openLink(url);
    else window.open(url, "_blank");
  }

  function makeRequestButton(anime) {
    const requestBtn = document.createElement("button");
    requestBtn.className = "btn btn-primary";
    requestBtn.textContent = "Request";
    requestBtn.addEventListener("click", async () => {
      requestBtn.disabled = true;
      try {
        const result = await api("/api/request", {
          method: "POST",
          body: JSON.stringify({
            title: anime.title,
            source: anime.source || "anilist",
            source_id: anime.source_id ?? anime.anilist_id,
            poster_url: anime.poster_url,
            genres: anime.genres || [],
          }),
        });
        requestBtn.textContent = "\u2713 Requested";
        showToast(result.already_requested ? "You already requested this." : "Request sent!");
      } catch (err) {
        requestBtn.disabled = false;
        showToast(err.message || "Couldn't send request right now.");
      }
    });
    return requestBtn;
  }

  function renderDetailAction(anime, context) {
    detailActionArea.innerHTML = "";
    reportOpenBtn.classList.toggle("hidden", !["available", "ongoing", "discover", "genre"].includes(context));

    // Finished: solo card → solo_link; otherwise All-seasons join_link
    // Ongoing URL = ongoing_link only — never fall back for button split
    const finishedUrl = (
      (isSoloCard(anime) && anime.solo_link) ? anime.solo_link : null
    ) || anime.join_link || anime.solo_link || (
      (context === "discover" || context === "genre") ? (anime.matchedJoinLink || null) : null
    );
    const ongoingUrl = anime.ongoing_link || null;

    // PREVIOUS | ONGOING only when opened from the Ongoing library column.
    // Never key off libraryMode — Search/Home/Genre keep mode but use other contexts.
    const showOngoingSplit = context === "ongoing";

    const row = document.createElement("div");
    row.className = "action-row";

    if (showOngoingSplit && finishedUrl && ongoingUrl) {
      // Ongoing tab → PREVIOUS + fancy 𝙾𝙽𝙶𝙾𝙸𝙽𝙶
      const prevBtn = document.createElement("button");
      prevBtn.className = "btn btn-primary join-split-btn";
      prevBtn.textContent = "PREVIOUS";
      prevBtn.addEventListener("click", () => openJoinUrl(finishedUrl));
      const ongBtn = document.createElement("button");
      ongBtn.className = "btn btn-ongoing-fancy join-split-btn";
      ongBtn.textContent = "𝙾𝙽𝙶𝙾𝙸𝙽𝙶";
      ongBtn.addEventListener("click", () => openJoinUrl(ongoingUrl));
      row.appendChild(prevBtn);
      row.appendChild(ongBtn);
    } else if (showOngoingSplit && !finishedUrl && ongoingUrl) {
      // Ongoing tab, only ongoing link
      const ongBtn = document.createElement("button");
      ongBtn.className = "btn btn-ongoing-fancy";
      ongBtn.textContent = "𝙾𝙽𝙶𝙾𝙸𝙽𝙶";
      ongBtn.addEventListener("click", () => openJoinUrl(ongoingUrl));
      row.appendChild(ongBtn);
    } else if (showOngoingSplit && finishedUrl && !ongoingUrl) {
      // Ongoing column, no ongoing link set → show PREVIOUS + Request (not ONGOING)
      const prevBtn = document.createElement("button");
      prevBtn.className = "btn btn-primary join-split-btn";
      prevBtn.textContent = "PREVIOUS";
      prevBtn.addEventListener("click", () => openJoinUrl(finishedUrl));
      row.appendChild(prevBtn);
      row.appendChild(makeRequestButton(anime));
    } else if (showOngoingSplit && !finishedUrl && !ongoingUrl) {
      // Ongoing column, no links at all → Request only
      row.appendChild(makeRequestButton(anime));
    } else if (finishedUrl) {
      // Finished / Discover / etc. → single Join
      const joinBtn = document.createElement("button");
      joinBtn.className = "btn btn-primary";
      joinBtn.textContent = "• ᴊᴏɪɴ";
      joinBtn.addEventListener("click", () => openJoinUrl(finishedUrl));
      row.appendChild(joinBtn);
    } else if (ongoingUrl) {
      // No finished link but ongoing exists
      const ongBtn = document.createElement("button");
      ongBtn.className = "btn btn-ongoing-fancy";
      ongBtn.textContent = "𝙾𝙽𝙶𝙾𝙸𝙽𝙶";
      ongBtn.addEventListener("click", () => openJoinUrl(ongoingUrl));
      row.appendChild(ongBtn);
    } else {
      // Neither → Request
      row.appendChild(makeRequestButton(anime));
    }

    if (profile && profile.role === "admin" && (anime.id || anime.anilist_id || anime.source_id)) {
      const plus = document.createElement("button");
      plus.className = "plus-btn";
      plus.textContent = "+";
      plus.setAttribute("aria-label", "Set join link");
      plus.addEventListener("click", () => openLinkSheet(anime));
      row.appendChild(plus);
    }

    detailActionArea.appendChild(row);
  }

  async function openLocalDetail(item, forceContext) {
    // PREVIOUS|ONGOING only when opened from the Ongoing library column.
    // Search / Home matches must force "available" so PREVIOUS never appears there.
    const ctx = forceContext || (libraryMode === "ongoing" ? "ongoing" : "available");
    openDetailSheet(item, ctx);
    try {
      const full = await api(`/api/anime/${item.id}`);
      if (currentDetail && currentDetail.id === item.id) {
        openDetailSheet({ ...item, ...full }, ctx);
      }
      const merged = { ...item, ...full };
      // If synopsis / relations still missing, try AniList once more
      if (
        merged.source_id &&
        (!(merged.description || "").trim() || !(merged.related_posted || []).length)
      ) {
        try {
          const al = await api(`/api/anilist/${merged.source_id}`);
          if (currentDetail && currentDetail.id === item.id) {
            openDetailSheet({
              ...merged,
              ...al,
              id: merged.id,
              join_link: merged.join_link || al.join_link,
              solo_link: merged.solo_link || al.solo_link,
              ongoing_link: merged.ongoing_link || al.ongoing_link,
              related_posted: al.related_posted || merged.related_posted || [],
            }, ctx);
          }
        } catch (e) { /* non-fatal */ }
      }
      const st = (merged.status || "").toUpperCase();
      if (
        profile && profile.role === "admin" &&
        merged.id && merged.source_id &&
        !merged.airing_day &&
        (st === "RELEASING" || st === "NOT_YET_RELEASED")
      ) {
        try {
          const al = await api(`/api/anilist/${merged.source_id}`);
          const day = (al.airing_day || "").toLowerCase();
          if (day) {
            const result = await api(`/api/anime/${merged.id}/airing-day`, {
              method: "PATCH",
              body: JSON.stringify({ day }),
            });
            const updated = result.anime || {};
            const idx = available.findIndex((a) => a.id === merged.id);
            if (idx >= 0) available[idx] = { ...available[idx], airing_day: updated.airing_day };
            if (currentDetail && currentDetail.id === merged.id) {
              currentDetail.airing_day = updated.airing_day;
              openDetailSheet(currentDetail, ctx);
            }
            renderLibraryTab();
          }
        } catch (err) { /* non-fatal enrichment */ }
      }
    } catch (err) {
      if (currentDetail && currentDetail.description === "Loading synopsis...") {
        detailDescription.textContent = "Couldn't load full details.";
      }
    }
  }

  async function openDiscoverDetail(item) {
    // Prefer short synopsis from list payload so the sheet isn't stuck on
    // "Loading synopsis..." while AniList is slow / rate-limited.
    const preview = (item.description || item.synopsis || "").trim();
    openDetailSheet({
      ...item,
      description: preview || "Loading synopsis...",
      genres: item.genres || [],
    }, "discover");
    try {
      const full = await api(`/api/anilist/${item.anilist_id || item.source_id}`);
      if (currentDetail && (currentDetail.title === item.title || currentDetail.anilist_id === item.anilist_id)) {
        openDetailSheet({
          ...full,
          anilist_id: item.anilist_id || full.source_id,
          rating: item.rating ?? full.rating,
          matchedJoinLink: item.matchedJoinLink || full.join_link || full.ongoing_link,
          join_link: full.join_link || item.join_link,
          ongoing_link: full.ongoing_link || item.ongoing_link,
        }, "discover");
      }
    } catch (err) {
      if (currentDetail && !preview) detailDescription.textContent = "Couldn't load full details.";
    }
  }

  async function openGenreItemDetail(item) {
    const availIndex = buildAvailableIndex();
    const matched = availIndex.match(item);
    item.matchedJoinLink = matched && matched.join_link ? matched.join_link : null;
    openDetailSheet({ ...item, description: "Loading synopsis...", genres: [] }, "genre");
    try {
      const full = await api(`/api/anilist/${item.anilist_id}`);
      if (currentDetail && currentDetail.title === item.title) {
        openDetailSheet({ ...full, anilist_id: item.anilist_id, rating: item.rating ?? full.rating, matchedJoinLink: item.matchedJoinLink }, "genre");
      }
    } catch (err) {
      if (currentDetail) detailDescription.textContent = "Couldn't load full details.";
    }
  }

  // ---------------------------------------------------------------------
  // Set Join Link sheet (admin only)
  // Finished context → All seasons / Solo fields
  // Ongoing column   → only Ongoing link field
  // ---------------------------------------------------------------------
  let linkTargetAnime = null;
  let linkSheetType = "finished"; // "finished" | "ongoing"

  function setLinkSheetType(type) {
    linkSheetType = type === "ongoing" ? "ongoing" : "finished";
    const finishedFields = el("link-finished-fields");
    const fieldOng = el("link-ongoing-field");
    if (finishedFields) finishedFields.classList.toggle("hidden", linkSheetType !== "finished");
    if (fieldOng) fieldOng.classList.toggle("hidden", linkSheetType !== "ongoing");
    let focusEl;
    if (linkSheetType === "ongoing") {
      focusEl = el("ongoing-link-input");
    } else {
      const soloActive = el("link-mode-solo") && el("link-mode-solo").classList.contains("active");
      focusEl = soloActive ? el("solo-link-input") : linkInput;
    }
    if (focusEl) setTimeout(() => focusEl.focus(), 30);
  }

  function setFinishedMode(mode) {
    // Underline tabs: All seasons | Solo — each keeps its own independent link.
    const isSolo = mode === "solo";
    const btnGroup = el("link-mode-group");
    const btnSolo = el("link-mode-solo");
    const groupField = el("link-group-field");
    const soloField = el("link-solo-field");
    if (btnGroup) btnGroup.classList.toggle("active", !isSolo);
    if (btnSolo) btnSolo.classList.toggle("active", isSolo);
    if (groupField) groupField.classList.toggle("hidden", isSolo);
    if (soloField) soloField.classList.toggle("hidden", !isSolo);
    const focusEl = isSolo ? el("solo-link-input") : linkInput;
    if (focusEl) setTimeout(() => focusEl.focus(), 30);
  }

  function openLinkSheet(anime) {
    linkTargetAnime = anime;
    // Seasons + Solo are independent — load both, show one via underline tabs.
    if (linkInput) linkInput.value = anime.join_link || "";
    const soloInput = el("solo-link-input");
    if (soloInput) soloInput.value = anime.solo_link || "";
    const ongoingInput = el("ongoing-link-input");
    if (ongoingInput) ongoingInput.value = anime.ongoing_link || "";
    setFinishedMode(anime.solo_link ? "solo" : "group");
    // Ongoing link can only be set from the Ongoing column
    const preferOngoing = (typeof libraryMode !== "undefined" && libraryMode === "ongoing");
    setLinkSheetType(preferOngoing ? "ongoing" : "finished");
    linkOverlay.classList.remove("hidden");
  }

  (function wireLinkTabs() {
    const btnGroup = el("link-mode-group");
    const btnSolo = el("link-mode-solo");
    if (btnGroup) btnGroup.addEventListener("click", () => setFinishedMode("group"));
    if (btnSolo) btnSolo.addEventListener("click", () => setFinishedMode("solo"));
  })();

  function closeLinkSheet() {
    linkOverlay.classList.add("hidden");
    linkTargetAnime = null;
  }
  el("link-cancel").addEventListener("click", closeLinkSheet);
  linkOverlay.addEventListener("click", (e) => { if (e.target === linkOverlay) closeLinkSheet(); });

  const linkSaveBtn = el("link-save");
  linkSaveBtn.addEventListener("click", async () => {
    if (!linkTargetAnime || linkSaveBtn.disabled) return;
    const groupValue = (linkInput.value || "").trim();
    const soloInput = el("solo-link-input");
    const soloValue = soloInput ? (soloInput.value || "").trim() : "";
    const ongoingInput = el("ongoing-link-input");
    const ongoingValue = ongoingInput ? (ongoingInput.value || "").trim() : "";
    const isOngoingSheet = linkSheetType === "ongoing";

    // Need at least one URL when creating a new post
    if (!linkTargetAnime.id) {
      if (isOngoingSheet && !ongoingValue) {
        showToast("Paste an Ongoing join URL first");
        return;
      }
      if (!isOngoingSheet && !groupValue && !soloValue) {
        showToast("Paste a Seasons or Solo join URL first");
        return;
      }
    }

    linkSaveBtn.disabled = true;
    const originalLabel = linkSaveBtn.textContent;
    linkSaveBtn.textContent = "Saving…";
    try {
      let result;
      if (linkTargetAnime.id) {
        // Only send the fields relevant to the current sheet so we never
        // accidentally clear the other type of link.
        const body = isOngoingSheet
          ? { ongoing_link: ongoingValue }
          : { group_link: groupValue, solo_link: soloValue };
        result = await api(`/api/anime/${linkTargetAnime.id}/link`, {
          method: "PATCH",
          body: JSON.stringify(body),
        });
        if (result.status === "deleted") {
          closeLinkSheet();
          closeDetailSheet();
          showToast(result.propagated
            ? `Removed from library (and ${result.propagated} related title(s))`
            : "Removed from library");
          loadAvailable().catch(() => {});
          return;
        }
        const saved = result.anime || {};
        linkTargetAnime.join_link = saved.join_link || null;
        linkTargetAnime.solo_link = saved.solo_link || null;
        linkTargetAnime.ongoing_link = saved.ongoing_link || null;
        linkTargetAnime.display_mode = saved.display_mode || linkTargetAnime.display_mode;
        linkTargetAnime.matchedJoinLink =
          linkTargetAnime.solo_link || linkTargetAnime.join_link || linkTargetAnime.ongoing_link || null;
        if (currentDetail && currentDetail.id === linkTargetAnime.id) {
          currentDetail.join_link = linkTargetAnime.join_link;
          currentDetail.solo_link = linkTargetAnime.solo_link;
          currentDetail.ongoing_link = linkTargetAnime.ongoing_link;
          currentDetail.display_mode = linkTargetAnime.display_mode;
          currentDetail.matchedJoinLink = linkTargetAnime.matchedJoinLink;
        }
        const aidx = available.findIndex((a) => a.id === linkTargetAnime.id);
        if (aidx >= 0) {
          available[aidx] = {
            ...available[aidx],
            join_link: linkTargetAnime.join_link,
            solo_link: linkTargetAnime.solo_link,
            ongoing_link: linkTargetAnime.ongoing_link,
            display_mode: linkTargetAnime.display_mode,
          };
        }
      } else {
        // Discover/Genre — create library entry (Finished fields only from this sheet)
        const alId = linkTargetAnime.anilist_id || linkTargetAnime.source_id;
        if (!alId) {
          throw new Error("Missing AniList id — open the title again and retry");
        }
        const createBody = {
          group_link: isOngoingSheet ? "" : groupValue,
          solo_link: isOngoingSheet ? "" : soloValue,
          ongoing_link: isOngoingSheet ? ongoingValue : "",
          title: linkTargetAnime.title,
          alt_title: linkTargetAnime.alt_title,
          year: linkTargetAnime.year,
          poster_url: linkTargetAnime.poster_url,
          banner_url: linkTargetAnime.banner_url,
          description: linkTargetAnime.description,
          genres: linkTargetAnime.genres || [],
          rating: linkTargetAnime.rating,
          status: linkTargetAnime.status || "FINISHED",
          episodes: linkTargetAnime.episodes,
          format: linkTargetAnime.format,
        };
        result = await api(`/api/anime/link-anilist/${alId}`, {
          method: "POST",
          body: JSON.stringify(createBody),
        });
        const anime = result.anime || {};
        linkTargetAnime.id = anime.id;
        linkTargetAnime.join_link = anime.join_link || (isOngoingSheet ? null : groupValue) || null;
        linkTargetAnime.solo_link = anime.solo_link || (isOngoingSheet ? null : soloValue) || null;
        linkTargetAnime.ongoing_link = anime.ongoing_link || (isOngoingSheet ? ongoingValue : null) || null;
        linkTargetAnime.display_mode = anime.display_mode || (soloValue ? "solo" : "group");
        linkTargetAnime.matchedJoinLink =
          linkTargetAnime.solo_link || linkTargetAnime.join_link || linkTargetAnime.ongoing_link || null;
        // Optimistically add to local library so Finished column updates immediately
        if (anime.id) {
          const idx = available.findIndex((a) => a.id === anime.id);
          const row = {
            ...linkTargetAnime,
            ...anime,
            id: anime.id,
            join_link: linkTargetAnime.join_link,
            solo_link: linkTargetAnime.solo_link,
            ongoing_link: linkTargetAnime.ongoing_link,
            available: true,
          };
          if (idx >= 0) available[idx] = { ...available[idx], ...row };
          else available.push(row);
        }
        if (currentDetail && (currentDetail.anilist_id === alId || currentDetail.source_id === alId)) {
          currentDetail.id = anime.id;
          currentDetail.join_link = linkTargetAnime.join_link;
          currentDetail.solo_link = linkTargetAnime.solo_link;
          currentDetail.ongoing_link = linkTargetAnime.ongoing_link;
          currentDetail.matchedJoinLink = linkTargetAnime.matchedJoinLink;
        }
      }

      if (currentDetail) renderDetailAction(currentDetail, currentContext);
      // Capture before closeLinkSheet() nulls the target
      const savedJoin = !!(linkTargetAnime && (linkTargetAnime.join_link || linkTargetAnime.solo_link));
      const savedOngoing = !!(linkTargetAnime && linkTargetAnime.ongoing_link);
      const savedTitle = (linkTargetAnime && linkTargetAnime.title)
        || (currentDetail && currentDetail.title)
        || "";
      closeLinkSheet();
      showToast(result.propagated
        ? `Link saved — applied to ${result.propagated} related title(s) too`
        : "Link saved");
      // Refresh catalog, then jump to the matching Home column so the card is visible
      try {
        await loadAvailable();
      } catch (e) { /* ignore */ }
      if (savedJoin) {
        setLibraryMode("finished");
        showView("app");
        try {
          if (savedTitle && typeof indexKeyFor === "function") {
            activeLetter = indexKeyFor(savedTitle);
            activeDay = null;
            libraryQuery = "";
            renderLibraryTab();
          }
        } catch (e) { /* ignore */ }
      } else if (savedOngoing) {
        setLibraryMode("ongoing");
        showView("app");
      }
    } catch (err) {
      showToast(err.message || "Couldn't save link");
    } finally {
      linkSaveBtn.disabled = false;
      linkSaveBtn.textContent = originalLabel || "Save";
    }
  });

  // ---------------------------------------------------------------------
  // Report sheet
  // ---------------------------------------------------------------------
  reportOpenBtn.addEventListener("click", () => {
    selectedReason = null;
    reportDetails.value = "";
    document.querySelectorAll(".reason-btn").forEach((b) => b.classList.remove("selected"));
    reportOverlay.classList.remove("hidden");
  });
  document.querySelectorAll(".reason-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      selectedReason = btn.dataset.reason;
      document.querySelectorAll(".reason-btn").forEach((b) => b.classList.remove("selected"));
      btn.classList.add("selected");
    });
  });
  el("report-cancel").addEventListener("click", () => reportOverlay.classList.add("hidden"));
  reportOverlay.addEventListener("click", (e) => { if (e.target === reportOverlay) reportOverlay.classList.add("hidden"); });
  el("report-submit").addEventListener("click", async () => {
    if (!selectedReason) { showToast("Pick a reason first"); return; }
    if (!currentDetail) return;
    try {
      await api("/api/report", {
        method: "POST",
        body: JSON.stringify({
          anime_id: currentDetail.id || null,
          anime_title: currentDetail.title,
          reason: selectedReason,
          details: reportDetails.value.trim(),
        }),
      });
      reportOverlay.classList.add("hidden");
      showToast("Report submitted — thank you.");
    } catch (err) {
      showToast(err.message || "Couldn't submit report");
    }
  });

  // ---------------------------------------------------------------------
  // Search page
  // ---------------------------------------------------------------------
  const GENRES = ["Action", "Adventure", "Comedy", "Drama", "Fantasy", "Romance", "Sci-Fi", "Horror"];

  function renderSearchLanding() {
    searchViewInput.value = "";
    searchResults.classList.add("hidden");
    searchLanding.classList.remove("hidden");
    renderPopularSearches();
    renderRecentSearches();
    renderGenreTiles();
    // Discovery sections (Trending / Airing / Popular) live under Genres
    renderTrending();
    renderTopAiring();
    renderPopularGrid();
  }

  async function renderPopularSearches() {
    popularSearchList.innerHTML = "";
    let items = [];
    try {
      items = await api("/api/search/popular?limit=6");
    } catch (err) { /* silently empty */ }
    items.forEach((item) => {
      const row = document.createElement("div");
      row.className = "popular-search-row";
      row.innerHTML = `<span class="popular-search-icon">\u{1F50D}</span>
        <span class="popular-search-text">${escapeHtml(item.query)}</span>
        <span class="popular-search-arrow">\u2197</span>`;
      row.addEventListener("click", () => {
        searchViewInput.value = item.query;
        runLibrarySearch(item.query);
      });
      popularSearchList.appendChild(row);
    });
  }

  // Recent Searches is personal per-device history, kept in localStorage
  // only — it never touches the server/database, unlike Popular Searches
  // above (which is a shared aggregate everyone contributes to and reads).
  const RECENT_SEARCH_KEY = "touka-recent-searches";
  const RECENT_SEARCH_LIMIT = 10;

  function getLocalRecentSearches() {
    return []; // Recent Searches removed
    try {
      const raw = localStorage.getItem(RECENT_SEARCH_KEY);
      const items = raw ? JSON.parse(raw) : [];
      return Array.isArray(items) ? items : [];
    } catch (err) {
      return [];
    }
  }

  function addLocalRecentSearch(query) {
    // no-op — Recent Searches removed
  }


  function clearLocalRecentSearches() {
    try { localStorage.removeItem(RECENT_SEARCH_KEY); } catch (err) { /* not fatal */ }
  }

  function renderRecentSearches() {
    // Recent Searches UI removed
    if (recentSearchSection) recentSearchSection.classList.add("hidden");
    if (recentSearchList) recentSearchList.innerHTML = "";
  }


  recentSearchClear.addEventListener("click", () => {
    clearLocalRecentSearches();
    renderRecentSearches();
  });

  popularSearchRefresh.addEventListener("click", async () => {
    popularSearchRefresh.disabled = true;
    const original = popularSearchRefresh.textContent;
    popularSearchRefresh.textContent = "Refreshing…";
    try {
      await renderPopularSearches();
    } finally {
      popularSearchRefresh.disabled = false;
      popularSearchRefresh.textContent = original;
    }
  });

  const GENRE_SYMBOLS = {
    "Action": {
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 3.5 20.5 9.5 9.5 20.5 3.5 14.5Z"/><path d="M17.5 6.5 20.5 3.5"/><path d="M6.5 17.5 3.5 20.5"/><path d="M11 9 15 13"/></svg>',
    },
    "Adventure": {
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="m14.5 9.5-2 5-5 2 2-5Z"/></svg>',
    },
    "Comedy": {
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><path d="M8.5 9h.01"/><path d="M15.5 9h.01"/></svg>',
    },
    "Drama": {
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5c2 0 3 1.5 3 3.5S6 12 6 14c0 2 1.5 3 3.5 3"/><path d="M20 5c-2 0-3 1.5-3 3.5s1 3.5 1 5.5c0 2-1.5 3-3.5 3"/><circle cx="9" cy="8" r=".6" fill="currentColor" stroke="none"/><circle cx="15" cy="8" r=".6" fill="currentColor" stroke="none"/></svg>',
    },
    "Fantasy": {
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 3 11l9 10 9-10Z"/><path d="M12 3v18"/><path d="M3 11h18"/></svg>',
    },
    "Romance": {
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20s-7-4.4-9.5-9C.9 7.6 3 4 6.5 4 9 4 11 6 12 7.5 13 6 15 4 17.5 4 21 4 23.1 7.6 21.5 11 19 15.6 12 20 12 20Z"/></svg>',
    },
    "Sci-Fi": {
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2c2.5 2.5 4 6 4 10 0 3-1 6-4 10-3-4-4-7-4-10 0-4 1.5-7.5 4-10Z"/><circle cx="12" cy="10" r="1.6"/><path d="M9 17c-1.5 1-2.5 2.5-3 4.5 2-.5 3.5-1.5 4.5-3"/><path d="M15 17c1.5 1 2.5 2.5 3 4.5-2-.5-3.5-1.5-4.5-3"/></svg>',
    },
    "Horror": {
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 21V11a7 7 0 0 1 14 0v10l-2.5-2-2 2-2.5-2-2 2-2.5-2Z"/><path d="M9 11h.01"/><path d="M15 11h.01"/></svg>',
    },
  };

  function renderGenreTiles() {
    genreTileGrid.innerHTML = "";
    GENRES.forEach((g) => {
      const meta = GENRE_SYMBOLS[g] || {
        svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/></svg>',
      };
      const tile = document.createElement("div");
      tile.className = "genre-tile";
      const icon = document.createElement("span");
      icon.className = "genre-tile-icon";
      icon.innerHTML = meta.svg;
      tile.appendChild(icon);
      const name = document.createElement("span");
      name.className = "genre-tile-name";
      name.textContent = g;
      tile.appendChild(name);
      tile.addEventListener("click", () => openGenreView(g));
      genreTileGrid.appendChild(tile);
    });
  }

  function trackConfirmedSearch(title) {
    addLocalRecentSearch(title);
    api("/api/search/track", { method: "POST", body: JSON.stringify({ query: title } ) }).catch(() => {});
  }

  let searchQuery = "";
  let searchPage = 1;
  let searchHasNext = false;
  let searchLoading = false;
  let searchToken = 0;

  function searchResultRow(item, onOpen) {
    const row = document.createElement("div");
    row.className = "search-result-row";
    thumbImg(row, item.poster_url, item.title);
    const body = document.createElement("div");
    body.className = "search-result-body";
    const title = document.createElement("p");
    title.className = "search-result-title";
    title.textContent = item.title;
    body.appendChild(title);
    const meta = document.createElement("div");
    meta.className = "search-result-meta";
    if (item.year) {
      const year = document.createElement("span");
      year.className = "search-result-year";
      year.textContent = item.year;
      meta.appendChild(year);
    }
    if (item.rating) {
      const rating = document.createElement("span");
      rating.className = "search-result-rating";
      rating.textContent = "\u2605 " + item.rating.toFixed(1);
      meta.appendChild(rating);
    }
    body.appendChild(meta);
    if (item.genres && item.genres.length) {
      const genres = document.createElement("p");
      genres.className = "search-result-genres";
      genres.textContent = item.genres.join(", ");
      body.appendChild(genres);
    }
    row.appendChild(body);
    row.addEventListener("click", onOpen);
    return row;
  }

  async function runLibrarySearch(q) {
    const query = q.trim();
    if (!query) { renderSearchLanding(); return; }
    searchQuery = query;
    searchPage = 1;
    searchHasNext = false;
    searchLanding.classList.add("hidden");
    searchResults.classList.remove("hidden");
    searchResultsGroups.innerHTML = "";
    searchResultsEmpty.classList.add("hidden");
    searchResultsEmpty.textContent = "Searching AniList…";

    const qLower = query.toLowerCase();
    const availIndex = buildAvailableIndex();
    const localMatches = available.filter((a) => {
      const t = `${a.title || ""} ${a.alt_title || ""}`.toLowerCase();
      return t.includes(qLower);
    });
    localMatches.forEach((item) => {
      searchResultsGroups.appendChild(searchResultRow(item, () => {
        trackConfirmedSearch(item.title);
        openLocalDetail(item, "available"); // never PREVIOUS from Search
      }));
    });

    const myToken = ++searchToken;
    searchLoading = true;
    try {
      const data = await api(`/api/search/anime?q=${encodeURIComponent(query)}&page=1`);
      if (myToken !== searchToken) return;
      searchHasNext = !!(data && data.has_next);
      const seenIds = new Set(
        localMatches.map((a) => String(a.source_id || a.anilist_id || a.id)).filter(Boolean)
      );
      const localTitles = new Set(localMatches.map((a) => (a.title || "").toLowerCase()));
      (data.results || []).forEach((item) => {
        const idKey = String(item.anilist_id || item.source_id || "");
        if (idKey && seenIds.has(idKey)) return;
        if (localTitles.has((item.title || "").toLowerCase())) return;
        if (idKey) seenIds.add(idKey);
        const matched = availIndex.match(item);
        if (matched) {
          item.matchedJoinLink = matched.join_link || matched.ongoing_link || null;
          item.id = matched.id;
        }
        searchResultsGroups.appendChild(searchResultRow(item, () => {
          trackConfirmedSearch(item.title);
          if (matched) openLocalDetail({ ...matched, ...item }, "available"); // never PREVIOUS from Search
          else openDiscoverDetail(item);
        }));
      });
      const empty = searchResultsGroups.children.length === 0;
      searchResultsEmpty.textContent = empty ? "No anime found on AniList." : "";
      searchResultsEmpty.classList.toggle("hidden", !empty);
    } catch (err) {
      const empty = searchResultsGroups.children.length === 0;
      searchResultsEmpty.textContent = empty
        ? (err.message || "Search failed. Try again.")
        : "";
      searchResultsEmpty.classList.toggle("hidden", !empty);
    }
    searchLoading = false;
  }

  async function loadMoreSearchResults() {
    if (searchLoading || !searchHasNext || !searchQuery) return;
    searchLoading = true;
    const myToken = searchToken;
    try {
      const data = await api(`/api/search/anime?q=${encodeURIComponent(searchQuery)}&page=${searchPage + 1}`);
      if (myToken !== searchToken) return;
      searchPage += 1;
      searchHasNext = data.has_next;
      const availIndex = buildAvailableIndex();
      data.results.forEach((item) => {
        const matched = availIndex.match(item);
        item.matchedJoinLink = matched && matched.join_link ? matched.join_link : null;
        searchResultsGroups.appendChild(searchResultRow(item, () => openDiscoverDetail(item)));
      });
    } catch (err) { /* stop silently, user can keep scrolling to retry */ }
    searchLoading = false;
  }

  searchViewInput.addEventListener("input", debounce((e) => runLibrarySearch(e.target.value), 350));

  // Infinite scroll: the Search subview scrolls the document itself.
  window.addEventListener("scroll", debounce(() => {
    if (searchView.classList.contains("hidden") || searchResults.classList.contains("hidden")) return;
    const nearBottom = window.scrollY + window.innerHeight > document.documentElement.scrollHeight - 400;
    if (nearBottom) loadMoreSearchResults();
  }, 150));

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // ---------------------------------------------------------------------
  // Genre browse view — 3-col grid + Load more (faster feel)
  // ---------------------------------------------------------------------
  let genreViewName = "";
  let genrePage = 1;
  let genreHasNext = false;
  let genreLoading = false;
  let genrePrefetch = null; // { page, promise }
  let genreRequestId = 0;

  function showGenreSkeletons(count = 9) {
    genreBrowseGrid.innerHTML = "";
    for (let i = 0; i < count; i++) {
      const sk = document.createElement("div");
      sk.className = "skeleton-card";
      genreBrowseGrid.appendChild(sk);
    }
  }

  function updateGenreLoadMore() {
    if (!genreLoadMoreBtn) return;
    genreLoadMoreBtn.classList.toggle("hidden", !genreHasNext);
    genreLoadMoreBtn.disabled = genreLoading;
    genreLoadMoreBtn.textContent = genreLoading ? "Loading…" : "Load more";
  }

  function genreApiUrl(genre, page) {
    return `/api/genres/${encodeURIComponent(genre)}?page=${page}`;
  }

  async function openGenreView(genre) {
    showView("genre");
    genreViewName = genre;
    genrePage = 1;
    genreHasNext = false;
    genrePrefetch = null;
    genreViewTitle.textContent = genre;
    if (genreEmptyNote) {
      genreEmptyNote.textContent = "No titles found in this genre.";
      genreEmptyNote.classList.add("hidden");
    }
    if (genreLoadMoreBtn) genreLoadMoreBtn.classList.add("hidden");
    showGenreSkeletons(9);

    const reqId = ++genreRequestId;
    try {
      const data = await api(genreApiUrl(genre, 1));
      if (reqId !== genreRequestId) return;
      genreHasNext = !!data.has_next;
      genreBrowseGrid.innerHTML = "";
      const results = data.results || [];
      results.forEach((item) => {
        genreBrowseGrid.appendChild(simplePosterCard(item, () => openGenreItemDetail(item)));
      });
      if (genreEmptyNote) {
        genreEmptyNote.classList.toggle("hidden", results.length > 0);
      }
      updateGenreLoadMore();
      if (genreHasNext) prefetchGenreNext();
    } catch (err) {
      if (reqId !== genreRequestId) return;
      genreBrowseGrid.innerHTML = "";
      if (genreEmptyNote) {
        genreEmptyNote.textContent = "Couldn't load that genre right now.";
        genreEmptyNote.classList.remove("hidden");
      }
      showToast("Couldn't load that genre right now.");
      updateGenreLoadMore();
    }
  }

  function prefetchGenreNext() {
    if (!genreViewName || !genreHasNext) return;
    const nextPage = genrePage + 1;
    if (genrePrefetch && genrePrefetch.page === nextPage) return;
    genrePrefetch = {
      page: nextPage,
      promise: api(genreApiUrl(genreViewName, nextPage)).catch(() => null),
    };
  }

  async function loadMoreGenre() {
    if (genreLoading || !genreHasNext || !genreViewName) return;
    genreLoading = true;
    updateGenreLoadMore();
    const nextPage = genrePage + 1;
    const reqId = genreRequestId;
    try {
      let data = null;
      if (genrePrefetch && genrePrefetch.page === nextPage) {
        data = await genrePrefetch.promise;
        genrePrefetch = null;
      }
      if (!data) {
        data = await api(genreApiUrl(genreViewName, nextPage));
      }
      if (reqId !== genreRequestId) return;
      genrePage = nextPage;
      genreHasNext = !!(data && data.has_next);
      (data.results || []).forEach((item) => {
        genreBrowseGrid.appendChild(simplePosterCard(item, () => openGenreItemDetail(item)));
      });
      if (genreHasNext) prefetchGenreNext();
    } catch (err) {
      showToast("Couldn't load more right now.");
    }
    genreLoading = false;
    updateGenreLoadMore();
  }

  if (genreLoadMoreBtn) {
    genreLoadMoreBtn.addEventListener("click", () => loadMoreGenre());
  }
  // No auto-load on scroll — user must tap "Load more"

  // ---------------------------------------------------------------------
  // Profile
  // ---------------------------------------------------------------------
  function initials(name) {
    return (name || "?").trim().charAt(0).toUpperCase();
  }

  function openExternalLink(url) {
    if (!url) return;
    if (tg && tg.openTelegramLink && /t\.me\//i.test(url)) tg.openTelegramLink(url);
    else if (tg && tg.openLink) tg.openLink(url);
    else window.open(url, "_blank");
  }

  function makeHelpLinkCard(name, url) {
    const card = document.createElement("div");
    card.className = "help-card help-card--link";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "help-link-btn";
    btn.textContent = name;
    btn.addEventListener("click", () => openExternalLink(url));
    card.appendChild(btn);
    return card;
  }

  async function openProfile() {
    profileCard.innerHTML = `<p class="profile-hint">Loading profile\u2026</p>`;
    try {
      profile = await api("/api/profile");
      let help = {
        title: "ANIME NEXUS NETWORK",
        text: "",
        links: [],
        more_links: [],
        support_chat_url: "",
      };
      try {
        help = await api("/api/profile/help");
      } catch (e) { /* use defaults */ }

      const displayName = profile.first_name || profile.username || "User";
      const photoUrl = tg && tg.initDataUnsafe && tg.initDataUnsafe.user && tg.initDataUnsafe.user.photo_url;
      const avatarHtml = photoUrl
        ? `<img class="profile-avatar profile-avatar-img" src="${escapeHtml(photoUrl)}" alt="${escapeHtml(displayName)}" onerror="this.replaceWith(Object.assign(document.createElement('div'), {className: 'profile-avatar', textContent: '${initials(displayName)}'}))" />`
        : `<div class="profile-avatar">${initials(displayName)}</div>`;
      const links = Array.isArray(help.links) ? help.links : [];
      const moreLinks = Array.isArray(help.more_links) ? help.more_links : [];
      const supportUrl = (help.support_chat_url || "").trim();

      profileCard.innerHTML = `
        <div class="profile-header">
          ${avatarHtml}
          <div>
            <div class="profile-name">${escapeHtml(displayName)}</div>
            <div class="profile-username">${profile.username ? "@" + escapeHtml(profile.username) : "no username"}</div>
          </div>
        </div>
        <div class="profile-row"><span class="label">Telegram ID</span><span class="value">${profile.telegram_id}</span></div>
        <div class="profile-row"><span class="label">Registered in bot</span><span class="value">yes</span></div>
        <div class="profile-row"><span class="label">Role</span><span class="value">${escapeHtml(profile.role)}</span></div>
        <div class="profile-row"><span class="label">Access</span><span class="value">${escapeHtml(profile.access || "active")}</span></div>
      `;

      // Support Chat button always under Access
      {
        const supportWrap = document.createElement("div");
        supportWrap.className = "profile-support-wrap";
        const supportBtn = document.createElement("button");
        supportBtn.type = "button";
        supportBtn.className = "profile-support-btn";
        supportBtn.textContent = "sᴜᴘᴘᴏʀᴛ ᴄʜᴀᴛ\u{1F4AD}";
        supportBtn.addEventListener("click", () => {
          if (supportUrl) {
            openExternalLink(supportUrl);
          } else if (profile && profile.role === "admin") {
            showToast("Set Support Chat URL in Edit links first");
            openHelpEdit(help);
          } else {
            showToast("Support chat is not available yet");
          }
        });
        supportWrap.appendChild(supportBtn);
        profileCard.appendChild(supportWrap);
      }

      // Remove previous help stack
      const parent = profileCard.parentElement;
      if (parent) {
        parent.querySelectorAll(".help-stack, .help-card").forEach((n) => n.remove());
      }

      const stack = document.createElement("div");
      stack.className = "help-stack";

      // Intro card (title + description) — always shown
      const intro = document.createElement("div");
      intro.className = "help-card";
      intro.innerHTML = `
        <h3 class="help-card-title">${escapeHtml(help.title || "ANIME NEXUS NETWORK")}</h3>
        <p class="help-card-text">${escapeHtml(help.text || "")}</p>
      `;
      stack.appendChild(intro);

      // All channel links live behind MORE CHANNELS (not shown until tapped)
      const allChannelLinks = []
        .concat(links, moreLinks)
        .filter((l) => (l.name || "").trim() && (l.url || "").trim());

      if (allChannelLinks.length > 0) {
        const moreCard = document.createElement("div");
        moreCard.className = "help-card help-card--link";
        const moreBtn = document.createElement("button");
        moreBtn.type = "button";
        moreBtn.className = "help-link-btn help-more-btn";
        moreBtn.textContent = "MORE CHANNELS";
        const morePanel = document.createElement("div");
        morePanel.className = "more-channels-panel hidden";
        allChannelLinks.forEach((l) => {
          morePanel.appendChild(makeHelpLinkCard((l.name || "").trim(), (l.url || "").trim()));
        });
        moreBtn.addEventListener("click", () => {
          const nowHidden = morePanel.classList.toggle("hidden");
          moreBtn.textContent = nowHidden ? "MORE CHANNELS" : "HIDE CHANNELS";
        });
        moreCard.appendChild(moreBtn);
        stack.appendChild(moreCard);
        stack.appendChild(morePanel);
      }

      if (profile.role === "admin") {
        const admin = document.createElement("div");
        admin.className = "help-card-admin";
        const editBtn = document.createElement("button");
        editBtn.type = "button";
        editBtn.className = "edit-links-btn";
        editBtn.textContent = allChannelLinks.length ? "Edit links" : "Add links";
        editBtn.addEventListener("click", () => openHelpEdit(help));
        admin.appendChild(editBtn);
        stack.appendChild(admin);
      }

      if (parent) parent.insertBefore(stack, profileCard.nextSibling);
      else profileCard.appendChild(stack);
    } catch (err) {
      profileCard.innerHTML = `<p class="profile-hint">${escapeHtml(err.message || "Open this from inside Telegram to view your profile.")}</p>`;
    }
  }

  function openHelpEdit(help) {
    const overlay = el("help-edit-overlay");
    if (!overlay) return;
    el("help-edit-title").value = help.title || "";
    el("help-edit-text").value = help.text || "";
    const supportInput = el("help-edit-support");
    if (supportInput) supportInput.value = help.support_chat_url || "";
    // Main links UI removed — keep container empty so saves clear legacy main links.
    const box = el("help-edit-links");
    if (box) box.innerHTML = "";
    const moreBox = el("help-edit-more-links");
    if (moreBox) {
      moreBox.innerHTML = "";
      const moreLinks = (help.more_links && help.more_links.length)
        ? help.more_links
        : [{ name: "", url: "" }];
      moreLinks.forEach((l) => moreBox.appendChild(helpEditRow(l.name || "", l.url || "")));
    }
    overlay.classList.remove("hidden");
  }

  function helpEditRow(name, url) {
    const row = document.createElement("div");
    row.className = "help-edit-row";
    row.innerHTML = `
      <input type="text" class="help-edit-name" placeholder="Button name" value="" />
      <input type="text" class="help-edit-url" placeholder="https://t.me/..." value="" />
      <div class="help-edit-actions"><button type="button" class="help-edit-remove">Remove</button></div>
    `;
    row.querySelector(".help-edit-name").value = name;
    row.querySelector(".help-edit-url").value = url;
    row.querySelector(".help-edit-remove").addEventListener("click", () => row.remove());
    return row;
  }

  function closeHelpEdit() {
    const overlay = el("help-edit-overlay");
    if (overlay) overlay.classList.add("hidden");
  }

  function collectLinkRows(containerId) {
    const out = [];
    const box = el(containerId);
    if (!box) return out;
    box.querySelectorAll(".help-edit-row").forEach((row) => {
      const name = row.querySelector(".help-edit-name").value.trim();
      const url = row.querySelector(".help-edit-url").value.trim();
      if (name && url) out.push({ name, url });
    });
    return out;
  }

  (function wireHelpEdit() {
    const overlay = el("help-edit-overlay");
    if (!overlay) return;
    el("help-edit-cancel").addEventListener("click", closeHelpEdit);
    overlay.addEventListener("click", (e) => { if (e.target === overlay) closeHelpEdit(); });
    const addMore = el("help-edit-add-more");
    if (addMore) {
      addMore.addEventListener("click", () => {
        el("help-edit-more-links").appendChild(helpEditRow("", ""));
      });
    }
    el("help-edit-save").addEventListener("click", async () => {
      const title = el("help-edit-title").value.trim();
      const text = el("help-edit-text").value.trim();
      const supportInput = el("help-edit-support");
      const support_chat_url = supportInput ? supportInput.value.trim() : "";
      // Main links removed from UI — always clear them on save.
      const links = [];
      const more_links = collectLinkRows("help-edit-more-links");
      try {
        await api("/api/profile/help", {
          method: "PUT",
          body: JSON.stringify({ title, text, support_chat_url, links, more_links }),
        });
        closeHelpEdit();
        showToast("Profile links saved");
        openProfile();
      } catch (err) {
        showToast(err.message || "Could not save");
      }
    });
  })();

  // ---------------------------------------------------------------------
  // Notifications (request accepted/rejected) — the bell in the header
  // ---------------------------------------------------------------------
  let notifications = [];

  function renderNotifBadge(count) {
    notifBadge.classList.toggle("hidden", !count);
  }

  function timeAgo(ts) {
    if (!ts) return "";
    const diff = Math.max(0, Date.now() / 1000 - ts);
    if (diff < 60) return "just now";
    if (diff < 3600) return Math.floor(diff / 60) + "m ago";
    if (diff < 86400) return Math.floor(diff / 3600) + "h ago";
    return Math.floor(diff / 86400) + "d ago";
  }

  function renderNotifications() {
    notifList.innerHTML = "";
    notifEmpty.classList.toggle("hidden", notifications.length > 0);
    notifications.forEach((n) => {
      const accepted = n.status === "accepted";
      const card = document.createElement("div");
      card.className = "notif-card " + n.status + (n.seen ? "" : " unseen");

      const header = document.createElement("div");
      header.className = "notif-card-header";
      const icon = document.createElement("span");
      icon.className = "notif-card-icon";
      icon.textContent = accepted ? "\u2713" : "\u2717";
      const headline = document.createElement("span");
      headline.className = "notif-card-headline";
      headline.textContent = "ANIME REQUEST " + (accepted ? "ACCEPTED" : "REJECTED");
      const time = document.createElement("span");
      time.className = "notif-card-time";
      time.textContent = timeAgo(n.responded_at);
      header.appendChild(icon);
      header.appendChild(headline);
      header.appendChild(time);
      card.appendChild(header);

      const body = document.createElement("div");
      body.className = "notif-card-body";
      const thumb = document.createElement("div");
      thumb.className = "notif-thumb";
      thumbImg(thumb, n.poster_url, n.title);
      body.appendChild(thumb);

      const info = document.createElement("div");
      info.className = "notif-card-info";
      const title = document.createElement("div");
      title.className = "notif-card-title";
      title.textContent = n.title;
      info.appendChild(title);
      if (n.genres && n.genres.length) {
        const genres = document.createElement("div");
        genres.className = "notif-card-genres";
        genres.textContent = n.genres.join(" \u2022 ");
        info.appendChild(genres);
      }
      const note = document.createElement("div");
      note.className = "notif-card-note";
      note.textContent = n.note;
      info.appendChild(note);
      body.appendChild(info);
      card.appendChild(body);

      notifList.appendChild(card);
    });
  }

  async function loadNotifications() {
    try {
      const data = await api("/api/notifications");
      notifications = data.notifications || [];
      renderNotifBadge(data.unseen_count || 0);
    } catch (err) {
      notifications = [];
      renderNotifBadge(0);
    }
  }

  notifBtn.addEventListener("click", async () => {
    renderNotifications();
    notifOverlay.classList.remove("hidden");
    if (notifications.some((n) => !n.seen)) {
      try {
        await api("/api/notifications/seen", { method: "POST" });
      } catch (err) { /* badge will just recheck next load */ }
      notifications.forEach((n) => { n.seen = true; });
      renderNotifBadge(0);
      renderNotifications();
    }
  });
  notifClose.addEventListener("click", () => notifOverlay.classList.add("hidden"));
  notifOverlay.addEventListener("click", (e) => {
    if (e.target === notifOverlay) notifOverlay.classList.add("hidden");
  });

  // ---------------------------------------------------------------------
  // Data loading
  // ---------------------------------------------------------------------
  // Client-side AniList GraphQL — runs on the user's phone/network so
  // Koyeb datacenter IP blocks never empty the Home catalog.
  const ANILIST_GQL = "https://graphql.anilist.co";
  const DISCOVER_GQL = `
    query ($sort: [MediaSort], $page: Int, $status: MediaStatus) {
      Page(page: $page, perPage: 10) {
        pageInfo { hasNextPage }
        media(type: ANIME, sort: $sort, status: $status) {
          id
          title { romaji english }
          coverImage { extraLarge large }
          averageScore
          genres
          episodes
          description(asHtml: false)
        }
      }
    }`;

  function _mapAniMedia(m) {
    const score = m.averageScore;
    const title = (m.title && (m.title.english || m.title.romaji)) || "Untitled";
    const cover = (m.coverImage && (m.coverImage.extraLarge || m.coverImage.large)) || "";
    let synopsis = (m.description || "").replace(/<br\s*\/?>/gi, "\n").replace(/<\/?i>/gi, "").trim();
    if (synopsis.length > 140) synopsis = synopsis.slice(0, 140);
    return {
      title,
      poster_url: cover,
      rating: score ? Math.round((score / 10) * 10) / 10 : null,
      anilist_id: m.id,
      genres: (m.genres || []).slice(0, 3),
      episodes: m.episodes,
      synopsis,
    };
  }

  async function clientAniList(sort, page, status) {
    const variables = { sort: [sort], page: page || 1 };
    if (status) variables.status = status;
    const res = await fetch(ANILIST_GQL, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ query: DISCOVER_GQL, variables }),
    });
    if (!res.ok) throw new Error("AniList HTTP " + res.status);
    const payload = await res.json();
    if (payload.errors && !payload.data) throw new Error(JSON.stringify(payload.errors[0]));
    const pageData = payload.data && payload.data.Page;
    const media = (pageData && pageData.media) || [];
    return {
      results: media.map(_mapAniMedia),
      has_next: !!(pageData && pageData.pageInfo && pageData.pageInfo.hasNextPage),
      source: "client",
    };
  }

  async function loadDiscover() {
    renderSkeletonRow(trendingRow, 4);
    renderSkeletonRow(topAiringList, 4);
    renderSkeletonRow(popularGridList, 6);

    async function safeCatalog(path, clientFn) {
      try {
        const data = await api(path);
        if (data && Array.isArray(data.results) && data.results.length) return data;
      } catch (e) { /* fall through to client */ }
      // Server empty / failed → fetch AniList from the user's device
      try {
        if (typeof clientFn === "function") return await clientFn();
      } catch (e2) {
        return { results: [], has_next: false, error: String(e2 && e2.message || e2) };
      }
      return { results: [], has_next: false };
    }

    // Progressive paint
    try {
      const trendingData = await safeCatalog(
        "/api/catalog/trending",
        () => clientAniList("TRENDING_DESC", 1, null)
      );
      trending = Array.isArray(trendingData.results) ? trendingData.results : [];
      renderTrending();
    } catch (e) {
      trending = [];
      renderTrending();
    }

    try {
      const popularData = await safeCatalog(
        "/api/catalog/popular",
        () => clientAniList("POPULARITY_DESC", 1, "RELEASING")
      );
      popular = Array.isArray(popularData.results) ? popularData.results : [];
      popularHasNext = !!popularData.has_next;
      popularPage = 1;
      renderTopAiring();
    } catch (e) {
      popular = [];
      popularHasNext = false;
      renderTopAiring();
    }

    try {
      const mostPopularData = await safeCatalog(
        "/api/catalog/most-popular",
        () => clientAniList("POPULARITY_DESC", 1, null)
      );
      mostPopular = Array.isArray(mostPopularData.results) ? mostPopularData.results : [];
      mostPopularHasNext = !!mostPopularData.has_next;
      mostPopularPage = 1;
      renderPopularGrid();
      // Prefetch page 2 so the first "Load more" is instant
      if (mostPopularHasNext) prefetchMostPopularPage(2);
    } catch (e) {
      mostPopular = [];
      mostPopularHasNext = false;
      renderPopularGrid();
    }

    if (!trending.length && !popular.length && !mostPopular.length) {
      if (typeof showToast === "function") showToast("AniList unavailable — retrying…");
      setTimeout(() => { loadDiscover(); }, 10000);
    }
  }

  async function loadAvailable() {
    try {
      available = await api("/api/catalog/available");
    } catch (err) {
      available = [];
    }
    // Home is Available-only — always render the library
    renderLibraryTab();
    // After first catalog load, silently fill any missing airing days
    autoRefreshAiringDays();
    // Pull newly airing seasons of Finished franchises into Ongoing
    syncOngoingSeasons();
  }

  let _syncOngoingBusy = false;
  async function syncOngoingSeasons() {
    if (_syncOngoingBusy) return;
    _syncOngoingBusy = true;
    try {
      const res = await api("/api/catalog/sync-ongoing", { method: "POST", body: "{}" });
      if (res && ((res.added || 0) > 0 || (res.updated || 0) > 0)) {
        try {
          available = await api("/api/catalog/available");
          renderLibraryTab();
        } catch (e) { /* ignore */ }
      }
    } catch (err) {
      // non-fatal — Ongoing list just won't auto-expand this session
    } finally {
      _syncOngoingBusy = false;
    }
  }

  async function preloadProfile() {
    try {
      profile = await api("/api/profile");
    } catch (err) {
      profile = null;
    }
  }

  // ---------------------------------------------------------------------
  // Deep links from the bot: ?anime=<id> opens that post directly,
  // ?search=<text>&tab=library pre-fills the Search page with that title.
  // ---------------------------------------------------------------------
  function applyDeepLink() {
    const params = new URLSearchParams(window.location.search);
    const animeId = params.get("anime");
    const searchParam = params.get("search");

    if (animeId) {
      const match = available.find((a) => String(a.id) === String(animeId));
      if (match) openLocalDetail(match);
    } else if (searchParam) {
      showView("search");
      renderSearchLanding();
      searchViewInput.value = searchParam;
      runLibrarySearch(searchParam);
    }
  }

  (async function init() {
    document.title = brandName;
    await Promise.all([loadDiscover(), loadAvailable(), preloadProfile(), loadNotifications()]);
    applyDeepLink();
  })();

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") loadNotifications();
  });
})();
