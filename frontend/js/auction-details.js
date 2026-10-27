/**
 * Online Auction System - Auction Details Controller
 * Member 1 & Member 2 Integrated Controller:
 * - Full lot details and countdown timer (Member 1)
 * - Atomic bid submission engine & validation (Member 2)
 * - Auction closure & winner selection (Member 2)
 * - Distributed Computing Activity & Telemetry Panel (Member 2)
 * - Two-browser live state synchronization (Member 2)
 * - Member 3 WebSocket integration hooks preserved
 */

document.addEventListener('DOMContentLoaded', async () => {
  const urlParams = new URLSearchParams(window.location.search);
  let auctionId = urlParams.get('id');
  if (!auctionId) {
    const pathParts = window.location.pathname.split('/');
    if (pathParts.length > 2 && pathParts[1] === 'auction') {
      auctionId = pathParts[2];
    }
  }

  if (!auctionId) auctionId = 'auc_001';

  const container = document.getElementById('details-container');
  let countdownTimer = null;
  let syncInterval = null;
  let currentAuctionState = null;
  let liveSocket = null;
  let liveReconnectTimer = null;
  let liveReconnectDelay = 1000;
  let liveConnectedAt = 0;
  const activityLog = [];

  // Helper to record activity telemetry
  function logActivity({ op, status, latencyMs, detail, isError = false }) {
    const timeStr = new Date().toLocaleTimeString();
    activityLog.unshift({ op, status, latencyMs, detail, isError, timeStr });
    if (activityLog.length > 20) activityLog.pop();
    renderActivityPanel();
  }

  async function loadLot() {
    try {
      const auction = await api.getAuction(auctionId);
      currentAuctionState = auction;
      renderLot(auction);
      exposeMember2Integration(auction);
      loadBidsHistory();
      startDistributedSync();
    } catch (err) {
      container.innerHTML = `
        <div class="error-state">
          <div class="state-icon" style="color: var(--accent-vermilion);">🏛️</div>
          <h3 class="state-title">Auction Lot Not Found</h3>
          <p class="state-desc">${err.message}</p>
          <a href="/marketplace" class="btn btn-primary">Return to Marketplace</a>
        </div>
      `;
    }
  }

  function renderLot(auc) {
    currentAuctionState = auc;
    const isLive = auc.status === 'ACTIVE';
    const isClosed = auc.status === 'CLOSED';
    const isUpcoming = auc.status === 'UPCOMING';
    const currentUser = auth.getUser();
    const isSellerOrAdmin = currentUser && (currentUser.role === 'ADMIN' || currentUser.user_id === auc.seller_id);

    const statusBadge = isLive
      ? `<span class="badge badge-live"><span class="pulse-dot"></span> Active Auction</span>`
      : isClosed
        ? `<span class="badge badge-closed">Auction Closed / Hammer Dropped</span>`
        : `<span class="badge badge-upcoming">Upcoming Lot</span>`;

    const countdown = api.getCountdown(isUpcoming ? auc.start_time : auc.end_time);
    if (isUpcoming) {
      countdown.text = countdown.isExpired
        ? 'Opening time reached — syncing with server'
        : `Opens in ${countdown.text}`;
    }
    const highestBidDisplay = auc.highest_bid > 0
      ? api.formatCurrency(auc.highest_bid)
      : 'No Bids Yet';

    container.innerHTML = `
      <div class="details-grid">
        <!-- Left Column: Artwork Stage -->
        <div class="artwork-stage">
          <div class="artwork-frame">
            <img src="${auc.image_path}" alt="${auc.title}" id="main-artwork-img">
          </div>
          <p class="artwork-caption">
            Lot ${auc.auction_id} • ${auc.category} • Certified Authenticity
          </p>

          <!-- Distributed Computing Activity Panel -->
          <div id="auction-activity-panel-container">
            <!-- Rendered by renderActivityPanel() -->
          </div>
        </div>

        <!-- Right Column: Lot Info & Pricing -->
        <div class="details-info-column">
          <!-- Winner Banner if Closed -->
          ${isClosed ? `
            <div class="winner-card">
              <div class="winner-card-title">
                <span>🏆</span> Auction Closed — Final Hammer Dropped
              </div>
              <p style="font-size: 0.95rem; margin-bottom: 0.5rem; color: #332B1F;">
                Winning Bidder: <strong>${auc.highest_bidder_name || 'No Bids Placed'}</strong>
              </p>
              <div style="font-size: 1.25rem; font-weight: 700; color: #17160F;">
                Final Price: ${auc.highest_bid > 0 ? api.formatCurrency(auc.highest_bid) : '$0.00 (Unsold)'}
              </div>
              <p style="font-size: 0.8rem; color: #777468; margin-top: 0.5rem;">
                Total bids submitted: ${auc.total_bids || 0} • Status confirmed by gRPC Engine.
              </p>
            </div>
          ` : ''}

          <div class="lot-header">
            <div style="margin-bottom: 0.65rem;">${statusBadge}</div>
            <div class="lot-category">${auc.category} • LOT ${auc.auction_id}</div>
            <h1 class="lot-title">${auc.title}</h1>
            <div class="lot-artist">Attributed to / Masterwork by ${auc.artist_name}</div>
          </div>

          <!-- Description Box -->
          <div class="lot-description-box">
            <h4 style="font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.5rem; color: var(--text-secondary);">
              Curator's Catalog Notes &amp; Provenance
            </h4>
            <p>${auc.description}</p>
          </div>

          <!-- Pricing & Time Dashboard -->
          <div class="pricing-dashboard">
            <div class="price-summary-grid">
              <div>
                <span class="price-label">Starting Price</span>
                <div class="price-value" style="font-size: 1.25rem;">${api.formatCurrency(auc.starting_price)}</div>
              </div>
              <div>
                <span class="price-label">Current Highest Bid</span>
                <div class="highlight-price-large ${isLive ? 'live-active' : ''}" id="val-highest-bid">${highestBidDisplay}</div>
              </div>
              <div>
                <span class="price-label">Min. Bid Increment</span>
                <div class="price-value" style="font-size: 1.15rem; color: var(--text-secondary);">${api.formatCurrency(auc.min_increment)}</div>
              </div>
              <div>
                <span class="price-label">Next Minimum Acceptable Bid</span>
                <div class="price-value" id="val-min-next-bid" style="font-size: 1.25rem; font-weight: 700;">${api.formatCurrency(auc.min_next_bid)}</div>
              </div>
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem;">
              <div class="card-timer-row ${isLive ? 'timer-live' : ''}" style="margin: 0; font-size: 0.92rem;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
                <span id="detail-countdown-text" data-end="${auc.end_time}">${countdown.text}</span>
              </div>
              <div style="font-size: 0.85rem; color: var(--text-secondary);">
                <span>Total Placed Bids: <strong id="val-total-bids">${auc.total_bids || 0}</strong></span>
                ${auc.highest_bidder_name ? ` • Leader: <strong>${auc.highest_bidder_name}</strong>` : ''}
              </div>
            </div>

            <div style="margin-top: 1.25rem; padding-top: 1rem; border-top: 1px solid var(--border-subtle); font-size: 0.8rem; color: var(--text-secondary); display: flex; justify-content: space-between;">
              <span>Opened: ${api.formatDateTime(auc.start_time)}</span>
              <span>Scheduled Close: ${api.formatDateTime(auc.end_time)}</span>
            </div>
          </div>

          <!-- ============================================================= -->
          <!-- MEMBER 2 INTEGRATION: Bidding Engine & Concurrency Control -->
          <!-- ============================================================= -->
          <div id="member2-bidding-container" class="member2-integration-container">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
              <span class="integration-badge">Member 2 • Bidding &amp; Concurrency Engine</span>
              <span style="font-size: 0.75rem; color: var(--text-secondary); font-family: monospace;">gRPC Unary &bull; WAL Sync</span>
            </div>

            ${isLive ? `
              <!-- Quick Bid Preset Buttons -->
              <div class="bidding-quick-buttons">
                <button class="quick-inc-btn" data-inc="${auc.min_increment}">+ Min Inc (${api.formatCurrency(auc.min_increment)})</button>
                <button class="quick-inc-btn" data-inc="100">+$100</button>
                <button class="quick-inc-btn" data-inc="250">+$250</button>
                <button class="quick-inc-btn" data-inc="500">+$500</button>
                <button class="quick-inc-btn" data-inc="1000">+$1,000</button>
              </div>

              <!-- Main Bidding Input & Button -->
              <div class="mock-bidding-form" style="display: flex; gap: 0.75rem; align-items: stretch;">
                <div class="bid-input-wrap" style="flex: 1;">
                  <span class="currency-sym">$</span>
                  <input type="number" id="member2-bid-input" class="bid-input-field" 
                         value="${auc.min_next_bid}" min="${auc.min_next_bid}" step="${auc.min_increment}">
                </div>
                <button id="member2-place-bid-btn" class="btn btn-vermilion" style="font-weight: 600; padding: 0.75rem 1.5rem; white-space: nowrap;">
                  Place Validated Bid
                </button>
              </div>

              <div id="member2-feedback" style="margin-top: 0.85rem; font-size: 0.85rem;">
                <span style="color: var(--text-secondary);">
                  • Bids are validated by the gRPC service and committed atomically to SQLite in WAL mode.
                </span>
              </div>

              <!-- Authorized Seller / Curator Close Auction Button -->
              ${isSellerOrAdmin ? `
                <div style="margin-top: 1.25rem; padding-top: 0.85rem; border-top: 1px dashed var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
                  <span style="font-size: 0.8rem; color: var(--text-secondary);">
                    Curator / Seller Authority: You can close this lot now.
                  </span>
                  <button id="btn-close-auction" class="btn btn-secondary" style="font-size: 0.8rem; padding: 0.4rem 0.85rem; border-color: var(--accent-vermilion); color: var(--accent-vermilion);">
                    🔨 Drop Hammer &amp; Close Lot
                  </button>
                </div>
              ` : ''}

            ` : `
              <div style="padding: 1.25rem; background: var(--bg-primary); border-radius: 4px; font-size: 0.9rem; color: var(--text-secondary); text-align: center;">
                ${isClosed 
                  ? '<strong>Bidding is closed for this lot.</strong> Final sale recorded and confirmed on database ledger.' 
                  : '<strong>Bidding opens when this lot goes live.</strong> Pre-registered bids will activate at open time.'}
              </div>
            `}
          </div>

          <!-- Live Bid History Table -->
          <div id="member2-bid-history-container" style="margin-top: 2rem; background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1.25rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
              <h4 style="font-size: 0.95rem; font-weight: 600;">Verified Bids Ledger</h4>
              <button id="btn-refresh-bids" class="btn btn-secondary" style="padding: 0.2rem 0.6rem; font-size: 0.75rem;" title="Refresh bids ledger">
                ↻ Refresh Ledger
              </button>
            </div>
            <div id="bids-table-wrapper" style="overflow-x: auto;">
              <p style="font-size: 0.85rem; color: var(--text-secondary);">Querying gRPC bid log...</p>
            </div>
          </div>

          <div style="margin-top: 2rem;">
            <a href="/marketplace" class="btn btn-secondary">
              ← Return to Catalog
            </a>
          </div>
        </div>
      </div>
    `;

    renderActivityPanel();
    bindEventHandlers(auc);
  }

  // Render the Activity & Distributed Telemetry Panel
  function renderActivityPanel() {
    const target = document.getElementById('auction-activity-panel-container');
    if (!target) return;

    const latest = activityLog[0] || {
      op: 'System Ready',
      status: 'IDLE',
      latencyMs: '0.0',
      detail: 'gRPC service listening on port 50051; Web Gateway on 8000',
      timeStr: new Date().toLocaleTimeString()
    };

    const isOk = !latest.isError;
    const isReject = latest.status === 'REJECTED';

    target.innerHTML = `
      <div class="activity-panel">
        <div class="activity-panel-header">
          <div class="activity-panel-title">
            <span class="pulse-dot"></span> Auction Activity &amp; Telemetry
          </div>
          <span class="activity-pipeline-badge">gRPC Unary &bull; WAL</span>
        </div>

        <div style="font-size: 0.72rem; color: #8C8678; margin-bottom: 0.75rem; font-family: monospace;">
          Distributed Path: Client &rarr; Gateway (:8000) &rarr; gRPC (:50051) &rarr; SQLite
        </div>

        <div class="activity-metrics-grid">
          <div class="metric-pill">
            <div class="metric-pill-label">Latest RPC</div>
            <div class="metric-pill-value" style="color: #60A5FA;">${latest.op}</div>
          </div>
          <div class="metric-pill">
            <div class="metric-pill-label">Status</div>
            <div class="metric-pill-value ${isReject ? 'rejected' : (isOk ? '' : 'rejected')}">${latest.status}</div>
          </div>
          <div class="metric-pill">
            <div class="metric-pill-label">Roundtrip</div>
            <div class="metric-pill-value">${latest.latencyMs ? latest.latencyMs + 'ms' : '--'}</div>
          </div>
        </div>

        <div class="activity-log-feed">
          ${activityLog.length === 0 ? `
            <div class="activity-log-entry">
              <span style="color: #8C8678;">[${latest.timeStr}] Engine synchronized with database state.</span>
            </div>
          ` : activityLog.map(item => `
            <div class="activity-log-entry">
              <span>
                <span class="log-op-tag">[${item.op}]</span>
                <span style="color: #EDE8DC;">${item.detail}</span>
              </span>
              <span class="${item.isError || item.status === 'REJECTED' ? 'log-status-err' : 'log-status-ok'}">
                ${item.status} ${item.latencyMs ? '(' + item.latencyMs + 'ms)' : ''}
              </span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  // Load and render bid history table from /api/auctions/{auctionId}/bids
  async function loadBidsHistory() {
    const wrapper = document.getElementById('bids-table-wrapper');
    if (!wrapper) return;

    try {
      const bids = await api.getBids(auctionId);
      if (!bids || bids.length === 0) {
        wrapper.innerHTML = `
          <p style="font-size: 0.85rem; color: var(--text-secondary); padding: 0.75rem 0;">
            No bids recorded yet. Place the opening bid to lead this auction lot!
          </p>
        `;
        return;
      }

      wrapper.innerHTML = `
        <table class="bids-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Collector / Bidder</th>
              <th>Role</th>
              <th>Amount</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${bids.map((b, idx) => `
              <tr class="${idx === 0 ? 'highest-row' : ''}">
                <td>${api.formatDateTime(b.timestamp)}</td>
                <td><strong>${b.bidder_name}</strong> ${idx === 0 ? '🏆' : ''}</td>
                <td><span class="user-role-badge">${b.bidder_username || 'BUYER'}</span></td>
                <td style="font-weight: 700; color: ${idx === 0 ? 'var(--accent-vermilion)' : 'var(--text-primary)'};">
                  ${api.formatCurrency(b.bid_amount)}
                </td>
                <td><span style="color: #2E7D32; font-weight: 500;">✓ COMMITTED</span></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    } catch (e) {
      wrapper.innerHTML = `<p style="font-size: 0.85rem; color: var(--accent-vermilion);">Failed to load bid history: ${e.message}</p>`;
    }
  }

  // Bind interactive bidding, increment buttons, and closure controls
  function bindEventHandlers(auc) {
    // 1. Ticking countdown
    if (countdownTimer) clearInterval(countdownTimer);
    const countdownEl = document.getElementById('detail-countdown-text');
    if (countdownEl && (auc.status === 'ACTIVE' || auc.status === 'UPCOMING')) {
      countdownTimer = setInterval(() => {
        const target = auc.status === 'UPCOMING' ? auc.start_time : auc.end_time;
        const cd = api.getCountdown(target);
        countdownEl.textContent = auc.status === 'UPCOMING' && !cd.isExpired
          ? `Opens in ${cd.text}`
          : cd.text;
        if (cd.isExpired) {
          countdownEl.textContent = auc.status === 'UPCOMING'
            ? 'Opening time reached — syncing with server'
            : 'Deadline reached — awaiting server confirmation';
          clearInterval(countdownTimer);
          syncCurrentLot();
        }
      }, 1000);
    }

    // 2. Refresh bids button
    const refreshBidsBtn = document.getElementById('btn-refresh-bids');
    if (refreshBidsBtn) {
      refreshBidsBtn.addEventListener('click', () => {
        loadBidsHistory();
        syncCurrentLot();
      });
    }

    // 3. Quick increment buttons
    const bidInput = document.getElementById('member2-bid-input');
    const quickButtons = document.querySelectorAll('.quick-inc-btn');
    quickButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const inc = parseFloat(btn.dataset.inc);
        const currentVal = parseFloat(bidInput.value) || auc.min_next_bid;
        const currentHigh = auc.highest_bid > 0 ? auc.highest_bid : auc.starting_price;
        // If currentVal is below currentHigh + inc, set it to currentHigh + inc
        const targetVal = Math.max(currentVal + inc, currentHigh + inc);
        bidInput.value = targetVal;
        btn.style.transform = 'scale(0.95)';
        setTimeout(() => { btn.style.transform = ''; }, 120);
      });
    });

    // 4. Place Bid button
    const placeBidBtn = document.getElementById('member2-place-bid-btn');
    const feedbackEl = document.getElementById('member2-feedback');

    if (placeBidBtn && bidInput) {
      placeBidBtn.addEventListener('click', async () => {
        const currentUser = auth.getUser();
        if (!currentUser) {
          alert('Please sign in first to place a bid on this lot.');
          window.location.href = '/login';
          return;
        }

        const amount = parseFloat(bidInput.value);
        if (isNaN(amount) || amount <= 0) {
          feedbackEl.innerHTML = `<span style="color: var(--accent-vermilion); font-weight: 600;">⚠️ Please enter a valid bid amount.</span>`;
          return;
        }

        placeBidBtn.disabled = true;
        placeBidBtn.textContent = 'Transmitting gRPC...';
        feedbackEl.innerHTML = `<span style="color: var(--text-secondary);">⏳ Transmitting bid via gRPC to AuctionService.PlaceBid...</span>`;

        const t0 = performance.now();
        try {
          const res = await api.placeBid(auc.auction_id, currentUser.user_id, amount);
          const roundtripMs = Math.round(performance.now() - t0);

          if (res.success) {
            feedbackEl.innerHTML = `
              <div style="padding: 0.65rem 0.85rem; background: rgba(46, 125, 50, 0.1); border: 1px solid rgba(46, 125, 50, 0.3); border-radius: 4px; color: #2E7D32;">
                <strong>✓ Bid Accepted!</strong> ${res.message}<br>
                <span style="font-size: 0.78rem; color: var(--text-secondary);">
                  Committed to SQLite via gRPC unary call in ${res.telemetry?.latency_ms || roundtripMs}ms.
                </span>
              </div>
            `;

            logActivity({
              op: 'PlaceBid',
              status: 'COMMITTED',
              latencyMs: res.telemetry?.latency_ms || roundtripMs,
              detail: `Bid $${amount.toLocaleString()} accepted by ${currentUser.display_name}.`
            });

            // Update displayed values
            auc.highest_bid = res.current_highest_bid;
            auc.highest_bidder_name = currentUser.display_name;
            auc.min_next_bid = round(auc.highest_bid + auc.min_increment, 2);
            auc.total_bids = (auc.total_bids || 0) + 1;

            const highEl = document.getElementById('val-highest-bid');
            if (highEl) {
              highEl.textContent = api.formatCurrency(auc.highest_bid);
              highEl.classList.add('live-active');
            }
            const minNextEl = document.getElementById('val-min-next-bid');
            if (minNextEl) minNextEl.textContent = api.formatCurrency(auc.min_next_bid);
            const totalBidsEl = document.getElementById('val-total-bids');
            if (totalBidsEl) totalBidsEl.textContent = auc.total_bids;

            bidInput.value = auc.min_next_bid;
            bidInput.min = auc.min_next_bid;

            loadBidsHistory();
            exposeMember2Integration(auc);

          } else {
            // Rejected by engine
            feedbackEl.innerHTML = `
              <div style="padding: 0.65rem 0.85rem; background: rgba(240, 68, 50, 0.1); border: 1px solid rgba(240, 68, 50, 0.3); border-radius: 4px; color: var(--accent-vermilion);">
                <strong>✗ Bid Rejected:</strong> ${res.message}<br>
                <span style="font-size: 0.78rem; color: var(--text-secondary);">
                  Latest committed highest bid: ${api.formatCurrency(res.current_highest_bid)}.
                </span>
              </div>
            `;

            logActivity({
              op: 'PlaceBid',
              status: 'REJECTED',
              latencyMs: res.telemetry?.latency_ms || roundtripMs,
              detail: res.message,
              isError: true
            });

            if (res.current_highest_bid > auc.highest_bid) {
              auc.highest_bid = res.current_highest_bid;
              auc.min_next_bid = round(auc.highest_bid + auc.min_increment, 2);
              bidInput.value = auc.min_next_bid;
              const highEl = document.getElementById('val-highest-bid');
              if (highEl) highEl.textContent = api.formatCurrency(auc.highest_bid);
              const minNextEl = document.getElementById('val-min-next-bid');
              if (minNextEl) minNextEl.textContent = api.formatCurrency(auc.min_next_bid);
            }
          }

        } catch (err) {
          const roundtripMs = Math.round(performance.now() - t0);
          feedbackEl.innerHTML = `
            <div style="padding: 0.65rem 0.85rem; background: rgba(240, 68, 50, 0.1); border: 1px solid rgba(240, 68, 50, 0.3); border-radius: 4px; color: var(--accent-vermilion);">
              <strong>✗ Request Failed:</strong> ${err.message}
            </div>
          `;

          logActivity({
            op: 'PlaceBid',
            status: 'ERROR',
            latencyMs: roundtripMs,
            detail: err.message,
            isError: true
          });
        } finally {
          placeBidBtn.disabled = false;
          placeBidBtn.textContent = 'Place Validated Bid';
        }
      });
    }

    // 5. Close Auction Button (Seller / Admin)
    const closeAuctionBtn = document.getElementById('btn-close-auction');
    if (closeAuctionBtn) {
      closeAuctionBtn.addEventListener('click', async () => {
        const currentUser = auth.getUser();
        if (!confirm(`Are you sure you want to drop the hammer and close auction '${auc.title}'? This action is permanent.`)) {
          return;
        }

        closeAuctionBtn.disabled = true;
        closeAuctionBtn.textContent = 'Dropping Hammer...';

        const t0 = performance.now();
        try {
          const res = await api.closeAuction(auc.auction_id, currentUser.user_id);
          const roundtripMs = Math.round(performance.now() - t0);

          logActivity({
            op: 'CloseAuction',
            status: 'CLOSED',
            latencyMs: res.telemetry?.latency_ms || roundtripMs,
            detail: `Hammer dropped! Final price: $${res.final_price?.toLocaleString() || '0'}. Winner: ${res.winner_name || 'None'}.`
          });

          alert(`Auction closed successfully! Final sale price: ${api.formatCurrency(res.final_price)}. Winner: ${res.winner_name || 'None'}`);
          loadLot();

        } catch (err) {
          alert(`Failed to close auction: ${err.message}`);
          closeAuctionBtn.disabled = false;
          closeAuctionBtn.textContent = '🔨 Drop Hammer & Close Lot';
        }
      });
    }
  }

  // Distributed Sync Poller: enables two-browser-session live demonstration
  function startDistributedSync() {
    if (syncInterval) clearInterval(syncInterval);
    syncInterval = setInterval(() => {
      syncCurrentLot();
    }, 2500);
  }

  async function syncCurrentLot() {
    if (!currentAuctionState) return;

    try {
      const fresh = await api.getAuction(auctionId);
      if (!fresh) return;

      const previous = currentAuctionState;
      const bidChanged = fresh.highest_bid !== previous.highest_bid
        || fresh.total_bids !== previous.total_bids
        || fresh.highest_bidder_id !== previous.highest_bidder_id;
      const statusChanged = fresh.status !== previous.status;
      if (!bidChanged && !statusChanged) return;

      if (bidChanged) {
        logActivity({
          op: 'BID_ACCEPTED',
          status: 'DELIVERED',
          latencyMs: 0,
          detail: `${fresh.highest_bidder_name || 'A collector'} now leads at ${api.formatCurrency(fresh.highest_bid)}.`
        });
      }
      if (statusChanged) {
        logActivity({
          op: 'AUCTION_STATUS',
          status: fresh.status,
          latencyMs: 0,
          detail: fresh.status === 'CLOSED'
            ? 'Auction closed by the server; final result loaded from persisted state.'
            : `Auction status changed to ${fresh.status}.`
        });
      }

      currentAuctionState = fresh;
      renderLot(fresh);
      exposeMember2Integration(fresh);
      loadBidsHistory();
    } catch {
      // Background poll silently continues
    }
  }

  function setLiveConnectionStatus(status) {
    const statusEl = document.getElementById('live-connection-status');
    if (statusEl) statusEl.textContent = status;
  }

  function connectLiveUpdates() {
    if (liveSocket && (liveSocket.readyState === WebSocket.OPEN || liveSocket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    setLiveConnectionStatus('Connecting to live updates…');
    liveSocket = new WebSocket(`${protocol}//${window.location.host}/ws/live`);

    liveSocket.addEventListener('open', () => {
      liveConnectedAt = Date.now();
      setLiveConnectionStatus('Live updates connected');
      liveSocket.send(JSON.stringify({ action: 'subscribe', auction_id: auctionId }));
      syncCurrentLot();
    });

    liveSocket.addEventListener('message', (message) => {
      let event;
      try {
        event = JSON.parse(message.data);
      } catch {
        setLiveConnectionStatus('Received an invalid live update');
        return;
      }

      if (event.type === 'STREAM_ERROR' || event.type === 'ERROR') {
        setLiveConnectionStatus(event.message || 'Live updates unavailable');
        if (event.type === 'STREAM_ERROR' && liveSocket) liveSocket.close();
        return;
      }
      if (event.auction_id === auctionId) {
        syncCurrentLot();
      }
    });

    liveSocket.addEventListener('close', () => {
      liveSocket = null;
      setLiveConnectionStatus('Live updates disconnected; reconnecting…');
      if (Date.now() - liveConnectedAt >= 30000) liveReconnectDelay = 1000;
      if (liveReconnectTimer) clearTimeout(liveReconnectTimer);
      liveReconnectTimer = setTimeout(connectLiveUpdates, liveReconnectDelay);
      liveReconnectDelay = Math.min(liveReconnectDelay * 2, 15000);
    });

    liveSocket.addEventListener('error', () => {
      setLiveConnectionStatus('Live update connection error; reconnecting…');
      if (liveSocket) liveSocket.close();
    });
  }

  function round(val, dec) {
    return Number(Math.round(val + 'e' + dec) + 'e-' + dec);
  }

  // Expose JavaScript API Context for Member 2 & Member 3 hooks
  function exposeMember2Integration(auction) {
    window.AuctionDetailsContext = {
      auctionId: auction.auction_id,
      startingPrice: auction.starting_price,
      currentHighestBid: auction.highest_bid,
      minIncrement: auction.min_increment,
      minNextBid: auction.min_next_bid,
      status: auction.status,
      currentUser: auth.getUser(),
      onBidSubmit: async (bidData) => {
        console.log('[Member 2 Integration Hook] Bid payload received:', bidData);
        return await api.placeBid(bidData.auctionId, bidData.bidderId, bidData.amount);
      }
    };

    window.dispatchEvent(
      new CustomEvent('auction:lot-loaded', { detail: window.AuctionDetailsContext })
    );
  }

  await loadLot();
  connectLiveUpdates();

  window.addEventListener('beforeunload', () => {
    if (liveReconnectTimer) clearTimeout(liveReconnectTimer);
    if (countdownTimer) clearInterval(countdownTimer);
    if (syncInterval) clearInterval(syncInterval);
    if (liveSocket) liveSocket.close();
  });
});
