const API_BASE = "";

function getToken() {
  return localStorage.getItem("access_token");
}

function setToken(token) {
  localStorage.setItem("access_token", token);
}

function clearToken() {
  localStorage.removeItem("access_token");
}

function authHeaders() {
  const token = getToken();

  return {
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json"
  };
}

function requireAuth() {
  if (!getToken()) {
    window.location.href = "/static/login.html";
  }
}

function logout() {
  clearToken();
  window.location.href = "/static/login.html";
}

async function handleLogin(event) {
  event.preventDefault();

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const message = document.getElementById("loginMessage");

  message.textContent = "Entrando...";
  message.className = "message";

  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", password);

  try {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded"
      },
      body: formData
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Erro ao fazer login.");
    }

    setToken(data.access_token);

    message.textContent = "Login realizado com sucesso.";
    message.className = "message success";

    window.location.href = "/static/dashboard.html";

  } catch (error) {
    message.textContent = error.message;
    message.className = "message error";
  }
}

async function apiGet(path) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: authHeaders()
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || `Erro ${response.status}`);
  }

  return data;
}

async function apiPost(path, payload) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload)
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || `Erro ${response.status}`);
  }

  return data;
}

async function apiPut(path, payload) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify(payload)
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || `Erro ${response.status}`);
  }

  return data;
}

async function loadDashboard() {
  try {
    const me = await apiGet("/auth/me");

    const userEmail = document.getElementById("userEmail");
    const userPlan = document.getElementById("userPlan");
    const monthlyLimit = document.getElementById("monthlyLimit");
    const monthlyUsage = document.getElementById("monthlyUsage");
    const remainingGenerations = document.getElementById("remainingGenerations");
    const userAdmin = document.getElementById("userAdmin");
    const adminLink = document.getElementById("adminLink");

    if (userEmail) userEmail.textContent = me.email;
    if (userPlan) userPlan.textContent = me.plan;
    if (monthlyLimit) monthlyLimit.textContent = me.monthly_generation_limit;
    if (monthlyUsage) monthlyUsage.textContent = me.monthly_usage;
    if (remainingGenerations) remainingGenerations.textContent = me.remaining_generations;
    if (userAdmin) userAdmin.textContent = me.is_admin ? "Sim" : "Não";

    if (adminLink && me.is_admin) {
      adminLink.classList.remove("hidden");
    }

  } catch (error) {
    clearToken();
    window.location.href = "/static/login.html";
  }
}

async function generateSolution() {
  const bugInput = document.getElementById("bugInput");
  const message = document.getElementById("generateMessage");
  const resultBox = document.getElementById("generateResult");

  const bug = bugInput.value.trim();

  if (!bug) {
    message.textContent = "Informe a descrição do bug.";
    message.className = "message error";
    return;
  }

  message.textContent = "Gerando solução técnica...";
  message.className = "message";
  resultBox.textContent = "";

  try {
    const data = await apiPost("/projects/generate-solution", { bug });

    message.textContent = "Solução gerada com sucesso.";
    message.className = "message success";

    resultBox.textContent = JSON.stringify(data, null, 2);

    await loadDashboard();
    await loadHistory();

  } catch (error) {
    message.textContent = error.message;
    message.className = "message error";
  }
}

async function loadHistory() {
  const historyList = document.getElementById("historyList");

  if (!historyList) {
    return;
  }

  historyList.innerHTML = "<p>Carregando histórico...</p>";

  try {
    const data = await apiGet("/projects/history");

    if (!data.projects || data.projects.length === 0) {
      historyList.innerHTML = "<p>Nenhum projeto encontrado.</p>";
      return;
    }

    historyList.innerHTML = data.projects.map(project => `
      <div class="list-item">
        <h3>${project.project_name || "Projeto sem nome"}</h3>
        <p><strong>Status:</strong> ${project.status || "-"}</p>
        <p><strong>Criado em:</strong> ${project.created_at || "-"}</p>
        <p><strong>Bug:</strong> ${project.bug || "-"}</p>
      </div>
    `).join("");

  } catch (error) {
    historyList.innerHTML = `<p class="message error">${error.message}</p>`;
  }
}

async function loadAdminUsers() {
  const adminUsersList = document.getElementById("adminUsersList");
  const message = document.getElementById("adminMessage");

  if (!adminUsersList) {
    return;
  }

  adminUsersList.innerHTML = "<p>Carregando usuários...</p>";

  if (message) {
    message.textContent = "";
    message.className = "message";
  }

  try {
    const data = await apiGet("/admin/users");

    if (!data.users || data.users.length === 0) {
      adminUsersList.innerHTML = "<p>Nenhum usuário encontrado.</p>";
      return;
    }

    adminUsersList.innerHTML = data.users.map(user => `
      <div class="list-item">
        <h3>${user.email}</h3>

        <p><strong>ID:</strong> ${user.id}</p>
        <p><strong>Plano:</strong> ${user.plan}</p>
        <p><strong>Limite mensal:</strong> ${user.monthly_generation_limit}</p>
        <p><strong>Ativo:</strong> ${user.is_active ? "Sim" : "Não"}</p>
        <p><strong>Admin:</strong> ${user.is_admin ? "Sim" : "Não"}</p>

        <div class="actions">
          <button onclick="changeUserPlan(${user.id}, 'free')">Free</button>
          <button onclick="changeUserPlan(${user.id}, 'pro')">Pro</button>
          <button onclick="changeUserPlan(${user.id}, 'team')">Team</button>

          <button 
            onclick="toggleUserStatus(${user.id}, ${!user.is_active})" 
            class="${user.is_active ? "danger" : "success"}">
            ${user.is_active ? "Desativar" : "Ativar"}
          </button>

          <button 
            onclick="toggleUserAdmin(${user.id}, ${!user.is_admin})" 
            class="secondary">
            ${user.is_admin ? "Remover Admin" : "Promover Admin"}
          </button>
        </div>
      </div>
    `).join("");

  } catch (error) {
    adminUsersList.innerHTML = "";

    if (message) {
      message.textContent = error.message;
      message.className = "message error";
    }
  }
}

async function changeUserPlan(userId, plan) {
  try {
    await apiPut(`/admin/users/${userId}/plan`, { plan });
    await loadAdminUsers();
  } catch (error) {
    alert(error.message);
  }
}

async function toggleUserStatus(userId, isActive) {
  try {
    await apiPut(`/admin/users/${userId}/status`, { is_active: isActive });
    await loadAdminUsers();
  } catch (error) {
    alert(error.message);
  }
}

async function toggleUserAdmin(userId, isAdmin) {
  try {
    await apiPut(`/admin/users/${userId}/admin`, { is_admin: isAdmin });
    await loadAdminUsers();
  } catch (error) {
    alert(error.message);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.getElementById("loginForm");

  if (loginForm) {
    loginForm.addEventListener("submit", handleLogin);
  }
});