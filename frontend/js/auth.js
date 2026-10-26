/**
 * Online Auction System - Authentication & Session Manager
 * Maintains user state, enforces role visibility, and syncs UI header elements.
 */

const STORAGE_KEY = 'online_auction_user';

const auth = {
  getUser() {
    try {
      const data = localStorage.getItem(STORAGE_KEY);
      return data ? JSON.parse(data) : null;
    } catch {
      return null;
    }
  },

  setUser(userData) {
    if (!userData) {
      localStorage.removeItem(STORAGE_KEY);
    } else {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(userData));
    }
    this.updateNav();
  },

  logout() {
    localStorage.removeItem(STORAGE_KEY);
    window.location.href = '/login';
  },

  isAdmin() {
    const user = this.getUser();
    return user && user.role === 'ADMIN';
  },

  isSellerOrAdmin() {
    const user = this.getUser();
    return user && (user.role === 'SELLER' || user.role === 'ADMIN');
  },

  updateNav() {
    const user = this.getUser();
    const userMenuContainer = document.getElementById('user-menu-area');
    const adminNavLinks = document.querySelectorAll('.admin-only');
    const sellerAdminLinks = document.querySelectorAll('.seller-admin-only');

    // Update Admin nav links visibility
    adminNavLinks.forEach(el => {
      if (this.isAdmin()) {
        el.style.display = 'inline-flex';
      } else {
        el.style.display = 'none';
      }
    });

    // Update Seller/Admin elements visibility
    sellerAdminLinks.forEach(el => {
      if (this.isSellerOrAdmin()) {
        el.style.display = 'inline-flex';
      } else {
        el.style.display = 'none';
      }
    });

    if (!userMenuContainer) return;

    if (user) {
      const initials = (user.display_name || user.username || 'U')
        .split(' ')
        .map(n => n[0])
        .join('')
        .slice(0, 2)
        .toUpperCase();

      const roleClass = user.role === 'ADMIN' ? 'role-admin' : (user.role === 'SELLER' ? 'role-seller' : '');
      const roleLabel = user.role === 'ADMIN' ? 'CURATOR' : user.role;

      userMenuContainer.innerHTML = `
        <div class="user-menu-pill">
          <div class="user-avatar-circle">${initials}</div>
          <span style="font-weight: 500;">${user.display_name || user.username}</span>
          <span class="user-role-badge ${roleClass}">${roleLabel}</span>
        </div>
        <button id="logout-btn" class="btn btn-secondary" style="padding: 0.35rem 0.75rem; font-size: 0.8rem;" title="Sign out">
          Sign out
        </button>
      `;

      const logoutBtn = document.getElementById('logout-btn');
      if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
          e.preventDefault();
          this.logout();
        });
      }
    } else {
      userMenuContainer.innerHTML = `
        <a href="/login" class="btn btn-primary" style="padding: 0.45rem 1rem; font-size: 0.85rem;">
          Sign In
        </a>
      `;
    }
  }
};

window.auth = auth;

// Automatically sync navigation bar on load
document.addEventListener('DOMContentLoaded', () => {
  auth.updateNav();
});
