import { api, clearAuth, getProfile, isAuthenticated } from "../api/client.js";

export async function requireSession(options = {}) {
  if (!isAuthenticated()) {
    window.location.href = "/static/pages/login.html";
    return null;
  }

  let profile;
  try {
    profile = await api.me();
  } catch (_) {
    clearAuth();
    window.location.href = "/static/pages/login.html";
    return null;
  }

  if (options.permission && !profile.permissions?.[options.permission]) {
    window.location.href = "/static/pages/deliveries.html";
    return null;
  }

  if (options.effectiveRoles && !options.effectiveRoles.includes(profile.effective_role)) {
    window.location.href = "/static/pages/deliveries.html";
    return null;
  }

  return profile;
}

export function renderTopbar(container, profile = getProfile()) {
  const links = [
    { href: "/static/pages/deliveries.html", label: "Доставки", show: true },
    { href: "/static/pages/profile.html", label: "Профиль", show: true },
    {
      href: "/static/pages/create-delivery.html",
      label: profile?.effective_role === "admin" ? "Создать доставку" : "Новая доставка",
      show: Boolean(profile?.permissions?.can_create_delivery),
    },
    {
      href: "/static/pages/admin.html",
      label: "Админ панель",
      show: Boolean(profile?.permissions?.can_manage_accounts),
    },
  ].filter((item) => item.show);

  container.innerHTML = `
    <div class="card topbar">
      <div>
        <div class="brand">Delivery Service</div>
        <div class="muted">${profile?.full_name || profile?.login || "Пользователь"} · ${profile?.effective_role || "guest"}</div>
      </div>
      <nav>
        ${links
          .map(
            (item) =>
              `<a class="button-link secondary inline-button" href="${item.href}">${item.label}</a>`
          )
          .join("")}
        <button id="logoutButton" class="inline-button">Выйти</button>
      </nav>
    </div>
  `;

  container.querySelector("#logoutButton")?.addEventListener("click", () => {
    clearAuth();
    window.location.href = "/static/pages/login.html";
  });
}

export function roleLabel(profile) {
  const labels = {
    admin: "Администратор",
    employee: "Сотрудник",
    courier: "Курьер",
    client: "Клиент",
  };
  return labels[profile?.effective_role] || profile?.effective_role || "Пользователь";
}

export function showMessage(element, text, type = "") {
  element.textContent = text;
  element.className = `message ${type}`.trim();
}

export function hideMessage(element) {
  element.textContent = "";
  element.className = "message hidden";
}
