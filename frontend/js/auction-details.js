/**
 * Online Auction System - Auction Details Controller
 * Loads full lot details from gRPC server, runs real-time countdown,
 * and exposes the Member 2 Bidding Engine Integration Hook.
 */

document.addEventListener('DOMContentLoaded', async () => {
  const urlParams = new URLSearchParams(window.location.search);
  // Support both /auction-details?id=auc_001 and /auction/auc_001
  let auctionId = urlParams.get('id');
  if (!auctionId) {
    const pathParts = window.location.pathname.split('/');
    if (pathParts.length > 2 && pathParts[1] === 'auction') {
      auctionId = pathParts[2];
    }
  }

  // Fallback to default auc_001 if not provided
  if (!auctionId) auctionId = 'auc_001';

  const container = document.getElementById('details-container');
  let countdownTimer = null;

  async function loadLot() {
    try {
      const auction = await api.getAuction(auctionId);
      renderLot(auction);
      exposeMember2Integration(auction);
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
    const isLive = auc.status === 'ACTIVE';
    const isClosed = auc.status === 'CLOSED';
    const isUpcoming = auc.status === 'UPCOMING';

    const statusBadge = isLive
      ? `<span class="badge badge-live"><span class="pulse-dot"></span> Active Auction</span>`
      : isClosed
        ? `<span class="badge badge-closed">Auction Closed / Hammer Dropped</span>`
        : `<span class="badge badge-upcoming">Upcoming Lot</span>`;

    const countdown = api.getCountdown(auc.end_time);
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
        </div>

        <!-- Right Column: Lot Info & Pricing -->
        <div class="details-info-column">
          <div class="lot-header">
            <div style="margin-bottom: 0.65rem;">${statusBadge}</div>
            <div class="lot-category">${auc.category} • LOT ${auc.auction_id}</div>
            <h1 class="lot-title">${auc.title}</h1>
            <div class="lot-artist">Attributed to / Masterwork by ${auc.artist_name}</div>
          </div>

          <!-- Description Box -->
          <div class="lot-description-box">
            <h4 style="font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.5rem; color: var(--text-secondary);">
              Curator's Catalog Notes & Provenance
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
                <div class="highlight-price-large ${isLive ? 'live-active' : ''}">${highestBidDisplay}</div>
              </div>
              <div>
                <span class="price-label">Min. Bid Increment</span>
                <div class="price-value" style="font-size: 1.15rem; color: var(--text-secondary);">${api.formatCurrency(auc.min_increment)}</div>
              </div>
              <div>
                <span class="price-label">Next Minimum Acceptable Bid</span>
                <div class="price-value" style="font-size: 1.25rem; font-weight: 700;">${api.formatCurrency(auc.min_next_bid)}</div>
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
                <span>Total Placed Bids: <strong>${auc.total_bids || 0}</strong></span>
              </div>
            </div>

            <!-- Timestamps breakdown -->
            <div style="margin-top: 1.25rem; padding-top: 1rem; border-top: 1px solid var(--border-subtle); font-size: 0.8rem; color: var(--text-secondary); display: flex; justify-content: space-between;">
              <span>Opened: ${api.formatDateTime(auc.start_time)}</span>
              <span>Scheduled Close: ${api.formatDateTime(auc.end_time)}</span>
            </div>
          </div>

          <!-- ============================================================= -->
          <!-- MEMBER 2 INTEGRATION POINT: Bidding Engine Mounting Container -->
          <!-- ============================================================= -->
          <div id="member2-bidding-container" class="member2-integration-container">
            <span class="integration-badge">Member 2 Integration Point • Bidding Engine</span>
            <p class="integration-note">
              This interactive container is the designated mount point for <strong>Member 2's Bid Submission Engine</strong> 
              using gRPC bidirectional streaming (<code>PlaceBid</code>). Data contract and context are passed via <code>window.AuctionDetailsContext</code>.
            </p>

            ${isLive ? `
              <div class="mock-bidding-form">
                <div class="bid-input-wrap">
                  <span class="currency-sym">$</span>
                  <input type="number" id="member2-bid-input" class="bid-input-field" 
                         value="${auc.min_next_bid}" min="${auc.min_next_bid}" step="${auc.min_increment}">
                </div>
                <button id="member2-place-bid-btn" class="btn btn-vermilion" style="font-weight: 600;">
                  Place Bid ($${auc.min_next_bid.toLocaleString()})
                </button>
              </div>
              <div id="member2-feedback" style="margin-top: 0.75rem; font-size: 0.82rem; color: var(--text-secondary);">
                • Bids must be equal to or greater than minimum next bid of ${api.formatCurrency(auc.min_next_bid)}.
              </div>
            ` : `
              <div style="padding: 1rem; background: var(--bg-primary); border-radius: 4px; font-size: 0.88rem; color: var(--text-secondary);">
                ${isClosed ? 'Bidding is closed for this lot. Hammer has dropped.' : 'Bidding opens when auction goes live.'}
              </div>
            `}
          </div>

          <!-- Bid History Placeholder Container (Member 2 & 3 Shared) -->
          <div id="member2-bid-history-container" style="margin-top: 2rem; background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1.25rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.85rem;">
              <h4 style="font-size: 0.95rem; font-weight: 600;">Live Bidding History</h4>
              <span style="font-size: 0.75rem; color: var(--text-secondary);">Live Stream Log</span>
            </div>
            <p style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5;">
              Member 3 WebSocket / gRPC bidirectional streaming bids will stream into this table in real-time.
              Highest registered bidder: <strong>${auc.highest_bidder_name || 'None'}</strong>.
            </p>
          </div>

          <div style="margin-top: 2rem;">
            <a href="/marketplace" class="btn btn-secondary">
              ← Return to Catalog
            </a>
          </div>
        </div>
      </div>
    `;

    // Real-time ticking countdown
    if (countdownTimer) clearInterval(countdownTimer);
    const countdownEl = document.getElementById('detail-countdown-text');
    if (countdownEl && isLive) {
      countdownTimer = setInterval(() => {
        const cd = api.getCountdown(auc.end_time);
        countdownEl.textContent = cd.text;
      }, 1000);
    }

    // Attach mock interaction handler for testing & demonstration
    const bidBtn = document.getElementById('member2-place-bid-btn');
    const bidInput = document.getElementById('member2-bid-input');
    const feedbackEl = document.getElementById('member2-feedback');

    if (bidBtn && bidInput) {
      bidBtn.addEventListener('click', () => {
        const currentUser = auth.getUser();
        if (!currentUser) {
          alert('Please sign in first to place a bid on this lot.');
          window.location.href = '/login';
          return;
        }

        const amount = parseFloat(bidInput.value);
        if (isNaN(amount) || amount < auc.min_next_bid) {
          feedbackEl.innerHTML = `<span style="color: var(--accent-vermilion); font-weight: 600;">Bid must be at least ${api.formatCurrency(auc.min_next_bid)}</span>`;
          return;
        }

        // Notify that the interface hook is ready for Member 2's streaming RPC
        feedbackEl.innerHTML = `
          <span style="color: #2E7D32; font-weight: 600;">
            ✓ Bid intent ($${amount.toLocaleString()} by ${currentUser.display_name}) dispatched to Member 2 hook: <code>window.AuctionDetailsContext.onBidSubmit(...)</code>
          </span>
        `;

        if (window.AuctionDetailsContext && typeof window.AuctionDetailsContext.onBidSubmit === 'function') {
          window.AuctionDetailsContext.onBidSubmit({
            auctionId: auc.auction_id,
            bidderId: currentUser.user_id,
            amount: amount
          });
        }
      });
    }
  }

  // Expose JavaScript API Context for Member 2 integration
  function exposeMember2Integration(auction) {
    window.AuctionDetailsContext = {
      auctionId: auction.auction_id,
      startingPrice: auction.starting_price,
      currentHighestBid: auction.highest_bid,
      minIncrement: auction.min_increment,
      minNextBid: auction.min_next_bid,
      status: auction.status,
      currentUser: auth.getUser(),
      // Member 2 attaches their handler here:
      onBidSubmit: (bidData) => {
        console.log('[Member 2 Integration Hook] Bid payload received:', bidData);
      }
    };

    window.dispatchEvent(
      new CustomEvent('auction:lot-loaded', { detail: window.AuctionDetailsContext })
    );
  }

  await loadLot();
});
