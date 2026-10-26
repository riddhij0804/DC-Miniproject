/**
 * Online Auction System - Marketplace Home Controller
 * Manages category filtering, live search debounce, real-time countdown tickers, and catalog rendering.
 */

document.addEventListener('DOMContentLoaded', async () => {
  const state = {
    category: 'All',
    status: 'ALL',
    search: '',
    page: 1,
    pageSize: 12,
    timerInterval: null
  };

  const gridContainer = document.getElementById('auction-grid');
  const countBadge = document.getElementById('catalog-count');
  const searchInput = document.getElementById('search-input');
  const searchClearBtn = document.getElementById('search-clear-btn');
  const categoriesList = document.getElementById('categories-list');
  const statusPills = document.querySelectorAll('.status-pill');
  const featuredLotCard = document.getElementById('featured-lot-container');

  // 1. Initialize Categories
  async function loadCategories() {
    try {
      const categories = await api.getCategories();
      categoriesList.innerHTML = `
        <button class="category-chip ${state.category === 'All' ? 'active' : ''}" data-cat="All">
          All Lots
        </button>
      `;

      categories.forEach(cat => {
        const btn = document.createElement('button');
        btn.className = `category-chip ${state.category === cat ? 'active' : ''}`;
        btn.dataset.cat = cat;
        btn.textContent = cat;
        categoriesList.appendChild(btn);
      });

      // Bind click handlers
      categoriesList.querySelectorAll('.category-chip').forEach(chip => {
        chip.addEventListener('click', () => {
          categoriesList.querySelectorAll('.category-chip').forEach(c => c.classList.remove('active'));
          chip.classList.add('active');
          state.category = chip.dataset.cat;
          state.page = 1;
          fetchAndRender();
        });
      });
    } catch (err) {
      console.warn('Could not load dynamic categories, using defaults.', err);
    }
  }

  // 2. Status Pill Filters
  statusPills.forEach(pill => {
    pill.addEventListener('click', () => {
      statusPills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      state.status = pill.dataset.status;
      state.page = 1;
      fetchAndRender();
    });
  });

  // 3. Search Debounce & Clear
  let debounceTimeout = null;
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      const val = e.target.value.trim();
      state.search = val;
      state.page = 1;
      searchClearBtn.style.display = val.length > 0 ? 'block' : 'none';

      clearTimeout(debounceTimeout);
      debounceTimeout = setTimeout(() => {
        fetchAndRender();
      }, 280);
    });
  }

  if (searchClearBtn) {
    searchClearBtn.addEventListener('click', () => {
      searchInput.value = '';
      state.search = '';
      searchClearBtn.style.display = 'none';
      state.page = 1;
      fetchAndRender();
    });
  }

  // 4. Render Loading Skeletons
  function renderSkeletons() {
    gridContainer.innerHTML = Array(6).fill(0).map(() => `
      <div class="skeleton-card">
        <div class="skeleton-shimmer"></div>
      </div>
    `).join('');
  }

  // 5. Update Featured Lot in Hero
  function updateFeaturedLot(auctions) {
    if (!featuredLotCard) return;
    // Find active auction with highest bid or first active
    const featured = auctions.find(a => a.status === 'ACTIVE') || auctions[0];
    if (!featured) {
      featuredLotCard.style.display = 'none';
      return;
    }

    featuredLotCard.style.display = 'block';
    const countdown = api.getCountdown(featured.end_time);
    const priceDisplay = featured.highest_bid > 0
      ? api.formatCurrency(featured.highest_bid)
      : api.formatCurrency(featured.starting_price);

    featuredLotCard.innerHTML = `
      <div class="featured-image-wrapper">
        <div class="featured-badge-float">
          <span class="badge ${featured.status === 'ACTIVE' ? 'badge-live' : 'badge-upcoming'}">
            ${featured.status === 'ACTIVE' ? '<span class="pulse-dot"></span> LIVE AUCTION' : 'UPCOMING'}
          </span>
        </div>
        <img src="${featured.image_path}" alt="${featured.title}">
      </div>
      <div class="featured-body">
        <div class="featured-lot-tag">Lot ${featured.auction_id} • ${featured.category}</div>
        <h3 class="featured-title">${featured.title}</h3>
        <p class="featured-artist">${featured.artist_name}</p>
        <div class="card-timer-row ${featured.status === 'ACTIVE' ? 'timer-live' : ''}">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
          <span class="countdown-text" data-end="${featured.end_time}" data-status="${featured.status}">${countdown.text}</span>
        </div>
        <div class="featured-meta-row">
          <div>
            <div class="featured-price-label">${featured.highest_bid > 0 ? 'Current Highest Bid' : 'Starting Price'}</div>
            <div class="featured-price-val">${priceDisplay}</div>
          </div>
          <a href="/auction-details?id=${featured.auction_id}" class="btn btn-primary" style="padding: 0.6rem 1.15rem; font-size: 0.85rem;">
            View Lot & Bid
          </a>
        </div>
      </div>
    `;
  }

  // 6. Fetch and Render Catalog
  async function fetchAndRender() {
    renderSkeletons();
    try {
      const data = await api.getAuctions({
        search: state.search,
        category: state.category,
        status: state.status,
        page: state.page,
        pageSize: state.pageSize
      });

      const auctions = data.auctions || [];
      if (countBadge) {
        countBadge.textContent = `Showing ${auctions.length} of ${data.total_count} curated lots`;
      }

      // If on initial load or broad view, update hero featured lot
      if (state.category === 'All' && !state.search && state.status === 'ALL') {
        updateFeaturedLot(auctions);
      }

      if (auctions.length === 0) {
        gridContainer.innerHTML = `
          <div class="empty-state" style="grid-column: 1 / -1;">
            <div class="state-icon">🏛️</div>
            <h3 class="state-title">No lots found</h3>
            <p class="state-desc">There are no auction lots matching your selected criteria. Try resetting filters or searching with another term.</p>
            <button id="reset-filters-btn" class="btn btn-secondary">Clear All Filters</button>
          </div>
        `;

        const resetBtn = document.getElementById('reset-filters-btn');
        if (resetBtn) {
          resetBtn.addEventListener('click', () => {
            state.category = 'All';
            state.status = 'ALL';
            state.search = '';
            if (searchInput) searchInput.value = '';
            if (searchClearBtn) searchClearBtn.style.display = 'none';
            statusPills.forEach(p => p.classList.toggle('active', p.dataset.status === 'ALL'));
            categoriesList.querySelectorAll('.category-chip').forEach(c => c.classList.toggle('active', c.dataset.cat === 'All'));
            fetchAndRender();
          });
        }
        return;
      }

      gridContainer.innerHTML = auctions.map(auc => {
        const isLive = auc.status === 'ACTIVE';
        const isClosed = auc.status === 'CLOSED';
        const badgeMarkup = isLive
          ? `<span class="badge badge-live"><span class="pulse-dot"></span> Live Now</span>`
          : isClosed
            ? `<span class="badge badge-closed">Hammer Dropped</span>`
            : `<span class="badge badge-upcoming">Upcoming</span>`;

        const priceDisplay = auc.highest_bid > 0
          ? api.formatCurrency(auc.highest_bid)
          : api.formatCurrency(auc.starting_price);

        const priceLabel = auc.highest_bid > 0 ? 'Current Bid' : 'Starting Price';
        const countdown = api.getCountdown(auc.end_time);

        return `
          <article class="auction-card" data-id="${auc.auction_id}">
            <div class="card-image-box">
              <div class="card-badge-container">${badgeMarkup}</div>
              <img src="${auc.image_path}" alt="${auc.title}" loading="lazy">
            </div>
            <div class="card-content">
              <div class="card-category-tag">${auc.category} • Lot ${auc.auction_id}</div>
              <h3 class="card-title">${auc.title}</h3>
              <p class="card-artist">${auc.artist_name}</p>

              <div class="card-pricing-block">
                <div class="price-col">
                  <span class="price-label">${priceLabel}</span>
                  <span class="price-value ${isLive ? 'highlight-vermilion' : ''}">${priceDisplay}</span>
                </div>
                <div class="price-col" style="text-align: right;">
                  <span class="price-label">Total Bids</span>
                  <span class="price-value" style="font-size: 1.05rem;">${auc.total_bids || 0}</span>
                </div>
              </div>

              <div class="card-timer-row ${isLive ? 'timer-live' : ''}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
                <span class="countdown-text" data-end="${auc.end_time}" data-status="${auc.status}">
                  ${countdown.text}
                </span>
              </div>

              <a href="/auction-details?id=${auc.auction_id}" class="btn ${isLive ? 'btn-primary' : 'btn-secondary'}" style="width: 100%;">
                ${isLive ? 'Bid on this Lot' : 'View Catalog Lot'}
              </a>
            </div>
          </article>
        `;
      }).join('');

    } catch (err) {
      gridContainer.innerHTML = `
        <div class="error-state" style="grid-column: 1 / -1;">
          <div class="state-icon" style="color: var(--accent-vermilion);">⚠️</div>
          <h3 class="state-title">Backend Service Unavailable</h3>
          <p class="state-desc">Could not connect to the gRPC Auction House service (${err.message}). Ensure the Python gRPC server and Gateway are running.</p>
          <button id="retry-btn" class="btn btn-primary">Retry Connection</button>
        </div>
      `;
      const retryBtn = document.getElementById('retry-btn');
      if (retryBtn) retryBtn.addEventListener('click', fetchAndRender);
    }
  }

  // 7. Live Countdown Timer Ticker (Ticks every 1000ms)
  function startCountdownTicker() {
    if (state.timerInterval) clearInterval(state.timerInterval);
    state.timerInterval = setInterval(() => {
      const countdownElements = document.querySelectorAll('.countdown-text');
      countdownElements.forEach(el => {
        const endTime = el.dataset.end;
        const status = el.dataset.status;
        if (status === 'CLOSED') {
          el.textContent = 'Auction Closed';
          return;
        }
        const countdown = api.getCountdown(endTime);
        el.textContent = countdown.text;
      });
    }, 1000);
  }

  // Boot sequence
  await loadCategories();
  await fetchAndRender();
  startCountdownTicker();
});
