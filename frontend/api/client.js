const API_BASE = "/api";
const TOKEN_KEY = "delivery_token";
const ROLE_KEY = "delivery_role";
const PROFILE_KEY = "delivery_profile";

function authHeaders() {
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let detail = "Ошибка запроса";
    try {
      const data = await response.json();
      if (Array.isArray(data.detail)) {
        detail = data.detail
          .map((item) => {
            const path = Array.isArray(item.loc) ? item.loc.slice(1).join(".") : "field";
            return `${path}: ${item.msg}`;
          })
          .join("; ");
      } else {
        detail = data.detail || detail;
      }
    } catch (_) {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return null;
  }
  return response.json();
}

export function saveAuth(token, role) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(ROLE_KEY, role);
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ROLE_KEY);
  localStorage.removeItem(PROFILE_KEY);
}

export function getRole() {
  return localStorage.getItem(ROLE_KEY);
}

export function isAuthenticated() {
  return Boolean(localStorage.getItem(TOKEN_KEY));
}

export function saveProfile(profile) {
  localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
  localStorage.setItem(ROLE_KEY, profile.role);
}

export function getProfile() {
  const raw = localStorage.getItem(PROFILE_KEY);
  return raw ? JSON.parse(raw) : null;
}

export const api = {
  listLoginPageUsers: () => request("/auth/login-page-users"),
  register: (payload) => request("/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload) => request("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  me: async () => {
    const profile = await request("/auth/me");
    saveProfile(profile);
    return profile;
  },
  listClients: () => request("/clients"),
  createClient: (payload) => request("/clients", { method: "POST", body: JSON.stringify(payload) }),
  createAdminAccount: (payload) => request("/admin/accounts", { method: "POST", body: JSON.stringify(payload) }),
  listBranches: () => request("/reference/branches"),
  listCities: () => request("/reference/cities"),
  listStatuses: () => request("/reference/statuses"),
  listDeliveries: () => request("/deliveries"),
  getDelivery: (id) => request(`/deliveries/${id}`),
  createDelivery: (payload) => request("/deliveries", { method: "POST", body: JSON.stringify(payload) }),
  requestRecipientCourier: (id, payload) =>
    request(`/deliveries/${id}/recipient-courier-request`, { method: "POST", body: JSON.stringify(payload) }),
  updateDeliveryStatus: (id, payload) =>
    request(`/deliveries/${id}/status`, { method: "PATCH", body: JSON.stringify(payload) }),
  listCouriers: () => request("/couriers"),
  assignCourier: (deliveryId, payload) =>
    request(`/couriers/assign/${deliveryId}`, { method: "POST", body: JSON.stringify(payload) }),
  selfAssignDelivery: (deliveryId) => request(`/couriers/self-assign/${deliveryId}`, { method: "POST" }),
  getHistory: (deliveryId) => request(`/history/delivery/${deliveryId}`),
};
