/**
 * Online Auction System - API Client
 * Centralized communication layer bridging browser views to FastAPI Gateway and gRPC backend.
 */

const API_BASE = window.location.origin;

const api = {
  /**
   * Submits demo or custom user login
   */
  async login(username) {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username.trim() })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Login failed.');
    }
    return data;
  },

  /**
   * Retrieves list of pre-configured demo users
   */
  async getDemoUsers() {
    const res = await fetch(`${API_BASE}/api/auth/demo-users`);
    if (!res.ok) throw new Error('Failed to load demo accounts.');
    return await res.json();
  },

  /**
   * Retrieves catalog auctions with optional search, category, and status filters
   */
  async getAuctions({ search = '', category = '', status = '', page = 1, pageSize = 12 } = {}) {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (category && category !== 'All') params.append('category', category);
    if (status && status !== 'ALL') params.append('status', status);
    params.append('page', page);
    params.append('page_size', pageSize);

    const res = await fetch(`${API_BASE}/api/auctions?${params.toString()}`);
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Failed to retrieve auctions from gRPC server.');
    }
    return data;
  },

  /**
   * Retrieves full details for a single auction lot
   */
  async getAuction(auctionId) {
    const res = await fetch(`${API_BASE}/api/auctions/${encodeURIComponent(auctionId)}`);
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || `Auction '${auctionId}' could not be found.`);
    }
    return data;
  },

  /**
   * Retrieves all unique art categories
   */
  async getCategories() {
    const res = await fetch(`${API_BASE}/api/categories`);
    if (!res.ok) return ['Art', 'Paintings', 'Sculptures', 'Vintage', 'Collectibles'];
    const data = await res.json();
    return data.categories || [];
  },

  /**
   * Checks gateway and gRPC backend health
   */
  async checkHealth() {
    try {
      const res = await fetch(`${API_BASE}/health`);
      return await res.json();
    } catch (e) {
      return { gateway_status: 'unreachable', grpc_backend_connected: false };
    }
  },

  /**
   * Currency formatter helper ($X,XXX.00)
   */
  formatCurrency(val) {
    const num = Number(val) || 0;
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(num);
  },

  /**
   * Formats ISO timestamp to readable date & time
   */
  formatDateTime(isoStr) {
    if (!isoStr) return 'TBA';
    try {
      const date = new Date(isoStr);
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short'
      });
    } catch {
      return isoStr;
    }
  },

  /**
   * Computes human-readable countdown remaining between now and target ISO date
   */
  getCountdown(targetIso) {
    if (!targetIso) return { text: 'Ending soon', isExpired: false };
    const diff = new Date(targetIso).getTime() - Date.now();
    if (diff <= 0) {
      return { text: 'Auction Closed', isExpired: true };
    }

    const hours = Math.floor(diff / (1000 * 60 * 60));
    const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const secs = Math.floor((diff % (1000 * 60)) / 1000);

    if (hours > 24) {
      const days = Math.floor(hours / 24);
      const remHours = hours % 24;
      return { text: `${days}d ${remHours}h remaining`, isExpired: false };
    }

    const pad = (n) => String(n).padStart(2, '0');
    return { text: `${pad(hours)}:${pad(mins)}:${pad(secs)} remaining`, isExpired: false };
  }
};

window.api = api;
