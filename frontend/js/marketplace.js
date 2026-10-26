/**
 * Online Auction System - Marketplace Home Controller
 * Manages category filtering, live search debounce, real-time countdown tickers, catalog rendering,
 * and Member 2 Auction Creation Flow.
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
      if (searchClearBtn) {
        searchClearBtn.style.display = val.length > 0 ? 'block' : 'none';
      }

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

  // 5. Render Featured Lot in Hero
  function renderFeaturedLot(auction) {
    if (!featuredLotCard || !auction) return;

    const isLive = auction.status === 'ACTIVE';
    const countdown = api.getCountdown(auction.end_time);
    const highestBidDisplay = auction.highest_bid > 0
      ? api.formatCurrency(auction.highest_bid)
      : api.formatCurrency(auction.starting_price);

    featuredLotCard.innerHTML = `
      <div class="featured-image-box">
        <div class="card-badge-container">
          <span class="badge ${isLive ? 'badge-live' : 'badge-upcoming'}">
            ${isLive ? '<span class="pulse-dot"></span> Live Masterwork' : 'Upcoming Highlight'}
          </span>
        </div>
        <img src="${auction.image_path}" alt="${auction.title}">
      </div>
      <div class="featured-details">
        <div class="card-category-tag">${auction.category} • Lot ${auction.auction_id}</div>
        <h3 class="featured-lot-title">${auction.title}</h3>
        <p class="featured-artist">${auction.artist_name}</p>

        <div class="featured-pricing-row">
          <div>
            <span class="price-label">${auction.highest_bid > 0 ? 'Current Highest Bid' : 'Starting Bid'}</span>
            <div class="price-value highlight-vermilion" style="font-size: 1.4rem;">${highestBidDisplay}</div>
          </div>
          <div>
            <span class="price-label">Min. Advance</span>
            <div class="price-value" style="font-size: 1.1rem; color: var(--text-secondary);">${api.formatCurrency(auction.min_increment)}</div>
          </div>
        </div>

        <div class="card-timer-row ${isLive ? 'timer-live' : ''}" style="margin: 0.75rem 0 1.25rem 0;">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
          <span class="countdown-text" data-end="${auction.end_time}" data-status="${auction.status}">
            ${countdown.text}
          </span>
        </div>

        <a href="/auction-details?id=${auction.auction_id}" class="btn btn-vermilion" style="width: 100%; font-weight: 600;">
          ${isLive ? 'Enter Bidding Room' : 'View Full Provenance'}
        </a>
      </div>
    `;
  }

  // 6. Fetch and Render Catalog Grid
  async function fetchAndRender() {
    renderSkeletons();
    countBadge.textContent = 'Querying gRPC catalog...';

    try {
      const response = await api.getAuctions({
        search: state.search,
        category: state.category,
        status: state.status,
        page: state.page,
        pageSize: state.pageSize
      });

      const auctions = response.auctions || [];
      const totalCount = response.total_count || 0;

      countBadge.textContent = `${totalCount} lot${totalCount === 1 ? '' : 's'} available`;

      // Set featured lot on initial load
      if (auctions.length > 0 && state.category === 'All' && state.status === 'ALL' && !state.search) {
        const liveLot = auctions.find(a => a.status === 'ACTIVE') || auctions[0];
        renderFeaturedLot(liveLot);
      }

      if (auctions.length === 0) {
        gridContainer.innerHTML = `
          <div class="empty-state" style="grid-column: 1 / -1;">
            <div class="state-icon">🏛️</div>
            <h3 class="state-title">No matching auction lots found</h3>
            <p class="state-desc">Try clearing your search query or selecting a different fine art category.</p>
          </div>
        `;
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

  // ==========================================
  // Member 2: Auction Creation Modal Logic
  // ==========================================
  const modal = document.getElementById('create-auction-modal');
  const openModalBtns = [
    document.getElementById('nav-create-auction'),
    document.getElementById('hero-create-btn'),
    document.getElementById('btn-create-auction-catalog')
  ].filter(Boolean);

  const closeModalBtn = document.getElementById('modal-close-btn');
  const cancelModalBtn = document.getElementById('modal-cancel-btn');
  const createForm = document.getElementById('create-auction-form');
  const feedbackEl = document.getElementById('create-lot-feedback');
  const submitBtn = document.getElementById('modal-submit-btn');

  function openCreateModal() {
    const user = auth.getUser();
    if (!user) {
      alert('Please sign in with a Seller (e.g. seller_galerie) or Admin (admin_arthur) account to create auctions.');
      window.location.href = '/login';
      return;
    }
    if (user.role !== 'SELLER' && user.role !== 'ADMIN') {
      alert(`User ${user.display_name} has role '${user.role}'. Only SELLERS or ADMINS can create lots.`);
      return;
    }
    if (feedbackEl) {
      feedbackEl.style.display = 'none';
      feedbackEl.innerHTML = '';
    }
    if (modal) modal.classList.add('open');
  }

  function closeCreateModal() {
    if (modal) modal.classList.remove('open');
  }

  openModalBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      openCreateModal();
    });
  });

  if (closeModalBtn) closeModalBtn.addEventListener('click', closeCreateModal);
  if (cancelModalBtn) cancelModalBtn.addEventListener('click', closeCreateModal);

  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeCreateModal();
    });
  }

  if (createForm) {
    createForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const user = auth.getUser();
      if (!user) {
        alert('Please sign in first.');
        window.location.href = '/login';
        return;
      }

      const title = document.getElementById('lot-title').value.trim();
      const category = document.getElementById('lot-category').value;
      const artist = document.getElementById('lot-artist').value.trim() || 'Masterwork Studio';
      const description = document.getElementById('lot-description').value.trim();
      const price = parseFloat(document.getElementById('lot-price').value);
      const increment = parseFloat(document.getElementById('lot-increment').value) || 50;
      const durationHours = parseFloat(document.getElementById('lot-duration').value) || 24;

      // Rotate random artwork svg from assets
      const randomIdx = Math.floor(Math.random() * 6) + 1;
      const imagePath = `/assets/images/artwork_00${randomIdx}.svg`;

      submitBtn.disabled = true;
      submitBtn.textContent = 'Transmitting via gRPC...';

      if (feedbackEl) {
        feedbackEl.style.display = 'block';
        feedbackEl.innerHTML = `<span style="color: var(--text-secondary); font-size: 0.85rem;">⏳ Invoking AuctionService.CreateAuction RPC...</span>`;
      }

      try {
        const payload = {
          title,
          category,
          artist_name: artist,
          description,
          starting_price: price,
          min_increment: increment,
          duration_hours: durationHours,
          seller_id: user.user_id,
          image_path: imagePath
        };

        const res = await api.createAuction(payload);

        if (feedbackEl) {
          const lat = res.telemetry?.latency_ms ? `(${res.telemetry.latency_ms}ms)` : '';
          feedbackEl.innerHTML = `
            <div style="padding: 0.75rem; background: rgba(46, 125, 50, 0.1); border: 1px solid rgba(46, 125, 50, 0.3); border-radius: 4px; color: #2E7D32; font-size: 0.88rem;">
              <strong>✓ Auction Published!</strong> Lot ID: <code>${res.auction_id}</code> ${lat}<br>
              <span style="font-size: 0.8rem; color: var(--text-secondary);">Committed to SQLite via gRPC unary call. Refreshing catalog...</span>
            </div>
          `;
        }

        setTimeout(() => {
          closeCreateModal();
          createForm.reset();
          submitBtn.disabled = false;
          submitBtn.textContent = 'Publish Auction (gRPC)';
          // Reset to All category and view new lot
          state.category = 'All';
          state.status = 'ALL';
          state.search = '';
          fetchAndRender();
        }, 1200);

      } catch (err) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Publish Auction (gRPC)';
        if (feedbackEl) {
          feedbackEl.style.display = 'block';
          feedbackEl.innerHTML = `
            <div style="padding: 0.75rem; background: rgba(240, 68, 50, 0.1); border: 1px solid rgba(240, 68, 50, 0.3); border-radius: 4px; color: var(--accent-vermilion); font-size: 0.88rem;">
              <strong>Failed to create auction:</strong> ${err.message}
            </div>
          `;
        }
      }
    });
  }

  // Boot sequence
  await loadCategories();
  await fetchAndRender();
  startCountdownTicker();
});
