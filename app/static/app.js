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
  localStorage.removeItem("meusProjetosFiltros");
  window.location.href = "/static/login.html";
}

function setMessage(elementId, text, type = "") {
  const element = document.getElementById(elementId);

  if (!element) {
    return;
  }

  element.textContent = text;
  element.className = type ? `message ${type}` : "message";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatList(items) {
  if (!items || items.length === 0) {
    return "<p>-</p>";
  }

  if (Array.isArray(items)) {
    return `<ul>${items.map(item => `<li>${escapeHtml(String(item))}</li>`).join("")}</ul>`;
  }

  return `<p>${escapeHtml(String(items))}</p>`;
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }

  try {
    const rawValue = String(value).trim();

    if (!rawValue) {
      return "-";
    }

    const hasTimezone = /[zZ]$|[+-]\d{2}:\d{2}$/.test(rawValue);
    const normalizedValue = hasTimezone ? rawValue : `${rawValue}Z`;

    const date = new Date(normalizedValue);

    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return date.toLocaleString("pt-BR", {
      dateStyle: "short",
      timeStyle: "medium",
    });
  } catch {
    return value;
  }
}

function formatTestCases(data) {
  if (data.test_cases && Array.isArray(data.test_cases) && data.test_cases.length > 0) {
    return formatList(data.test_cases);
  }

  if (data.tests && Array.isArray(data.tests) && data.tests.length > 0) {
    return formatList(data.tests);
  }

  const files = data.files || [];

  if (Array.isArray(files)) {
    const testFiles = files.filter(file => {
      const name = String(file).toLowerCase();
      return name.includes("test") || name.includes("teste");
    });

    if (testFiles.length > 0) {
      return `
        <p>Foram gerados arquivos de teste:</p>
        ${formatList(testFiles)}
        <p class="muted small">
          O conteúdo detalhado dos testes ainda não é retornado pela API.
          Ele será incluído em uma evolução futura do backend.
        </p>
      `;
    }
  }

  return `
    <p>Nenhum caso de teste estruturado foi retornado pela API.</p>
    <p class="muted small">
      A próxima evolução do backend poderá incluir um campo test_cases com os cenários detalhados.
    </p>
  `;
}

function clearSolutionResult() {
  const solutionResult = document.getElementById("solutionResult");
  const generateResult = document.getElementById("generateResult");

  if (solutionResult) {
    solutionResult.classList.add("hidden");
  }

  if (generateResult) {
    generateResult.classList.add("hidden");
    generateResult.textContent = "";
  }
}

function renderSolutionResult(data) {
  const solutionResult = document.getElementById("solutionResult");

  if (!solutionResult) {
    return;
  }

  const status = document.getElementById("solutionStatus");
  const userStory = document.getElementById("solutionUserStory");
  const acceptanceCriteria = document.getElementById("solutionAcceptanceCriteria");
  const technicalAnalysis = document.getElementById("solutionTechnicalAnalysis");
  const solutionPlan = document.getElementById("solutionPlan");
  const solutionTestCases = document.getElementById("solutionTestCases");
  const solutionFiles = document.getElementById("solutionFiles");
  const solutionRaw = document.getElementById("solutionRaw");

  if (status) {
    status.textContent = data.generation_mode || data.status || "generated";
  }

  if (userStory) {
    userStory.textContent = data.user_story || "-";
  }

  if (acceptanceCriteria) {
    acceptanceCriteria.innerHTML = formatList(data.acceptance_criteria || []);
  }

  if (technicalAnalysis) {
    technicalAnalysis.textContent = data.technical_analysis || "-";
  }

  if (solutionPlan) {
    solutionPlan.innerHTML = formatList(data.solution_plan || []);
  }

  if (solutionTestCases) {
    solutionTestCases.innerHTML = formatTestCases(data);
  }

  if (solutionFiles) {
    solutionFiles.innerHTML = formatList(data.files || []);
  }

  if (solutionRaw) {
    solutionRaw.textContent = JSON.stringify(data, null, 2);
  }

  solutionResult.classList.remove("hidden");
}

async function safeJson(response) {
  const text = await response.text();

  try {
    return JSON.parse(text);
  } catch {
    return {
      detail: text || `Erro ${response.status}`
    };
  }
}

function buildHttpErrorMessage(response, data) {
  if (response.status === 401) {
    return "Sessão expirada ou token inválido. Faça login novamente.";
  }

  if (response.status === 403) {
    return "Você não tem permissão para executar esta ação.";
  }

  if (response.status >= 500) {
    if (data && data.detail) {
      return typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    }
    return "Erro interno na API. Verifique o terminal do backend para mais detalhes.";
  }

  if (data && data.detail) {
    return typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
  }

  return `Erro ${response.status}`;
}

function buildConnectionErrorMessage(path) {
  return `Não foi possível conectar à API. Verifique se o backend está rodando em http://127.0.0.1:8002. Endpoint chamado: ${path}`;
}

function buildGenerateErrorMessage(error) {
  const rawMessage = error && error.message ? error.message : "Erro desconhecido.";

  if (
    rawMessage === "Failed to fetch" ||
    rawMessage.toLowerCase().includes("connection error") ||
    rawMessage.toLowerCase().includes("não foi possível conectar")
  ) {
    return rawMessage;
  }

  if (rawMessage.toLowerCase().includes("token")) {
    return `${rawMessage} Faça login novamente.`;
  }

  return rawMessage;
}


async function handleLogin(event) {
  event.preventDefault();

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;

  setMessage("loginMessage", "Entrando...");

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

    const data = await safeJson(response);

    if (!response.ok) {
      throw new Error(data.detail || "Erro ao fazer login.");
    }

    setToken(data.access_token);
    setMessage("loginMessage", "Login realizado com sucesso.", "success");

    window.location.href = "/static/dashboard.html";

  } catch (error) {
    setMessage("loginMessage", error.message, "error");
  }
}

async function handleRegister(event) {
  event.preventDefault();

  const email = document.getElementById("registerEmail").value.trim();
  const password = document.getElementById("registerPassword").value;
  const passwordConfirm = document.getElementById("registerPasswordConfirm").value;
  const acceptTermsInput = document.getElementById("registerAcceptTerms");
  const accept_terms = acceptTermsInput ? acceptTermsInput.checked : false;

  setMessage("registerMessage", "Criando conta...");

  if (password.length < 8) {
    setMessage("registerMessage", "A senha precisa ter pelo menos 8 caracteres.", "error");
    return;
  }

  if (password !== passwordConfirm) {
    setMessage("registerMessage", "As senhas não conferem.", "error");
    return;
  }

  if (!accept_terms) {
    setMessage("registerMessage", "Para criar a conta, aceite os Termos de Uso e a Política de Privacidade.", "error");
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        email,
        password,
        accept_terms
      })
    });

    const data = await safeJson(response);

    if (!response.ok) {
      const detail = Array.isArray(data.detail)
        ? "Dados inválidos. Verifique o e-mail e a senha (mínimo de 8 caracteres)."
        : data.detail;
      throw new Error(detail || "Erro ao criar conta.");
    }

    setMessage(
      "registerMessage",
      "Conta criada com sucesso. Redirecionando para login...",
      "success"
    );

    setTimeout(() => {
      window.location.href = "/static/login.html";
    }, 1200);

  } catch (error) {
    setMessage("registerMessage", error.message, "error");
  }
}

// -1 significa sem limite (plano admin ou ilimitado).
function formatLimit(value) {
  return Number(value) === -1 ? "Ilimitado" : value;
}

async function apiGet(path) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: authHeaders()
  });

  const data = await safeJson(response);

  if (!response.ok) {
    throw new Error(data.detail || `Erro ${response.status}`);
  }

  return data;
}

async function apiPost(path, payload) {
  let response;

  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(payload)
    });
  } catch (error) {
    throw new Error(buildConnectionErrorMessage(path));
  }

  const data = await safeJson(response);

  if (!response.ok) {
    throw new Error(buildHttpErrorMessage(response, data));
  }

  return data;
}

async function apiPut(path, payload) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify(payload)
  });

  const data = await safeJson(response);

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
    if (monthlyLimit) monthlyLimit.textContent = formatLimit(me.monthly_generation_limit);
    if (monthlyUsage) monthlyUsage.textContent = me.monthly_usage;
    if (remainingGenerations) remainingGenerations.textContent = formatLimit(me.remaining_generations);
    if (userAdmin) userAdmin.textContent = me.is_admin ? "Sim" : "Não";

    if (adminLink && me.is_admin) {
      adminLink.classList.remove("hidden");
    }

  } catch (error) {
    clearToken();
    window.location.href = "/static/login.html";
  }
}

// ============================================================
// Fila de gerações: cria o job e consulta o status até terminar.
// ============================================================

const JOB_POLL_INTERVAL_MS = 2000;
const JOB_MAX_WAIT_MS = 10 * 60 * 1000;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function runGenerationJob(kind, bug, onProgress) {
  const job = await apiPost("/jobs", { kind, bug });
  const startedAt = Date.now();

  while (Date.now() - startedAt < JOB_MAX_WAIT_MS) {
    const current = await apiGet(`/jobs/${encodeURIComponent(job.id)}`);

    if (current.status === "succeeded") {
      return current.result;
    }

    if (current.status === "failed") {
      throw new Error(current.error_message || "A geração falhou.");
    }

    if (onProgress) {
      onProgress(current.status, Math.round((Date.now() - startedAt) / 1000));
    }

    await sleep(JOB_POLL_INTERVAL_MS);
  }

  throw new Error(
    "A geração está demorando mais que o normal. Ela continua em andamento; confira o histórico em alguns minutos."
  );
}

async function generateSolution() {
  const bugInput = document.getElementById("bugInput");

  if (!bugInput) {
    return;
  }

  const bug = bugInput.value.trim();

  if (!bug) {
    setMessage("generateMessage", "Informe a descrição do bug.", "error");
    return;
  }

  clearSolutionResult();
  setMessage("generateMessage", "Enviando para a fila de geração...");

  try {
    const data = await runGenerationJob("generate-solution", bug, (status, seconds) => {
      const label = status === "queued" ? "Na fila" : "Gerando solução técnica";
      setMessage("generateMessage", `${label}... (${seconds}s) Você pode continuar usando o sistema.`);
    });

    setMessage("generateMessage", "Solução gerada com sucesso.", "success");

    renderSolutionResult(data);

    await loadDashboard();
    await loadHistory();

  } catch (error) {
    let message = buildGenerateErrorMessage(error);

    if (message.includes("Limite mensal")) {
      message = `${message} Faça upgrade do plano ou aguarde o próximo ciclo mensal.`;
    }

    setMessage("generateMessage", `Erro ao gerar solução técnica: ${message}`, "error");
  }
}

async function loadHistory() {
  const historyList = document.getElementById("historyList");

  if (!historyList) {
    return;
  }

  historyList.innerHTML = `
    <div class="history-loading">
      <p>Carregando histórico...</p>
    </div>
  `;

  try {
    const data = await apiGet("/projects/history");

    if (!data.projects || data.projects.length === 0) {
      historyList.innerHTML = `
        <div class="empty-state">
          <h3>Nenhum projeto encontrado</h3>
          <p>Gere sua primeira solução técnica para que ela apareça aqui.</p>
        </div>
      `;
      return;
    }

    historyList.innerHTML = data.projects.map(project => {
      const projectName = project.project_name || "";
      const displayName = projectName || "Projeto sem nome";
      const status = project.status || "-";
      const createdAt = formatDateTime(project.created_at);
      const bug = project.bug || "-";
      const shortBug = bug.length > 180 ? `${bug.substring(0, 180)}...` : bug;
      const safeProjectName = escapeHtml(projectName);
      const filesContainerId = `projectFiles_${project.id}`;

      return `
        <article class="history-card">
          <div class="history-card-header">
            <div>
              <h3>${escapeHtml(displayName)}</h3>
              <p class="muted small">ID: ${project.id || "-"}</p>
            </div>
            <span class="badge">${escapeHtml(status)}</span>
          </div>

          <div class="history-meta">
            <span><strong>Criado em:</strong> ${escapeHtml(createdAt)}</span>
          </div>

          <p class="history-bug">
            <strong>Bug:</strong> ${escapeHtml(shortBug)}
          </p>

          <div class="history-actions">
            <button onclick="loadProjectFiles('${safeProjectName}', '${filesContainerId}')">
              Ver arquivos
            </button>

            <button onclick="downloadProjectZip('${safeProjectName}')">
              Baixar ZIP
            </button>
          </div>

          <div id="${filesContainerId}" class="project-files-box hidden"></div>

          <details class="history-details">
            <summary>Ver detalhes</summary>
            <div class="history-detail-content">
              <p><strong>Nome do projeto:</strong></p>
              <pre class="code-box">${escapeHtml(displayName)}</pre>

              <p><strong>Descrição completa do bug:</strong></p>
              <pre class="code-box">${escapeHtml(bug)}</pre>

              <p><strong>Resposta bruta do histórico:</strong></p>
              <pre class="code-box">${escapeHtml(JSON.stringify(project, null, 2))}</pre>
            </div>
          </details>
        </article>
      `;
    }).join("");

  } catch (error) {
    historyList.innerHTML = `
      <div class="empty-state error-state">
        <h3>Erro ao carregar histórico</h3>
        <p>${escapeHtml(error.message)}</p>
      </div>
    `;
  }
}

function encodePathValue(value) {
  return String(value)
    .split("/")
    .map(part => encodeURIComponent(part))
    .join("/");
}

async function downloadBlob(path, filename) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "GET",
    headers: {
      "Authorization": `Bearer ${getToken()}`
    }
  });

  if (!response.ok) {
    const data = await safeJson(response);
    throw new Error(data.detail || `Erro ${response.status}`);
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();

  link.remove();
  window.URL.revokeObjectURL(url);
}

async function downloadProjectZip(projectName) {
  if (!projectName) {
    alert("Nome do projeto não informado.");
    return;
  }

  try {
    const encodedProjectName = encodeURIComponent(projectName);

    await downloadBlob(
      `/projects/generated/${encodedProjectName}/download`,
      `${projectName}.zip`
    );

  } catch (error) {
    alert(error.message);
  }
}

async function downloadProjectFile(projectName, filename) {
  if (!projectName || !filename) {
    alert("Projeto ou arquivo não informado.");
    return;
  }

  try {
    const encodedProjectName = encodeURIComponent(projectName);
    const encodedFilename = encodePathValue(filename);

    await downloadBlob(
      `/projects/generated/${encodedProjectName}/files/${encodedFilename}/download`,
      filename.split("/").pop()
    );

  } catch (error) {
    alert(error.message);
  }
}

async function loadProjectFiles(projectName, containerId) {
  const container = document.getElementById(containerId);

  if (!container) {
    return;
  }

  if (!projectName) {
    container.classList.remove("hidden");
    container.innerHTML = `
      <div class="empty-state error-state">
        <p>Nome do projeto não encontrado no histórico.</p>
      </div>
    `;
    return;
  }

  container.classList.remove("hidden");
  container.innerHTML = "<p>Carregando arquivos...</p>";

  try {
    const encodedProjectName = encodeURIComponent(projectName);
    const data = await apiGet(`/projects/generated/${encodedProjectName}/files`);

    if (!data.files || data.files.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <p>Nenhum arquivo encontrado para este projeto.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <h4>Arquivos do projeto</h4>
      <div class="project-files-list">
        ${data.files.map(filename => `
          <div class="project-file-item">
            <span>${escapeHtml(filename)}</span>

            <div class="project-file-actions">
              <button onclick="viewProjectFile('${escapeHtml(projectName)}', '${escapeHtml(filename)}', '${containerId}')">
                Ver conteúdo
              </button>

              <button onclick="downloadProjectFile('${escapeHtml(projectName)}', '${escapeHtml(filename)}')">
                Baixar
              </button>

              <button onclick="viewProjectWordText('${escapeHtml(projectName)}', '${escapeHtml(filename)}', '${containerId}')">
                Texto Word
              </button>
            </div>
          </div>
        `).join("")}
      </div>

      <div id="${containerId}_content" class="project-file-content"></div>
    `;

  } catch (error) {
    container.innerHTML = `
      <div class="empty-state error-state">
        <p>${escapeHtml(error.message)}</p>
      </div>
    `;
  }
}

async function viewProjectFile(projectName, filename, containerId) {
  const contentBox = document.getElementById(`${containerId}_content`);

  if (!contentBox) {
    return;
  }

  contentBox.innerHTML = "<p>Carregando conteúdo do arquivo...</p>";

  try {
    const encodedProjectName = encodeURIComponent(projectName);
    const encodedFilename = encodePathValue(filename);

    const data = await apiGet(
      `/projects/generated/${encodedProjectName}/files/${encodedFilename}`
    );

    contentBox.innerHTML = `
      <h4>Conteúdo: ${escapeHtml(filename)}</h4>
      <pre class="code-box">${escapeHtml(data.content || "")}</pre>
    `;

  } catch (error) {
    contentBox.innerHTML = `
      <div class="empty-state error-state">
        <p>${escapeHtml(error.message)}</p>
      </div>
    `;
  }
}

async function viewProjectWordText(projectName, filename, containerId) {
  const contentBox = document.getElementById(`${containerId}_content`);

  if (!contentBox) {
    return;
  }

  contentBox.innerHTML = "<p>Gerando texto limpo para Word...</p>";

  try {
    const encodedProjectName = encodeURIComponent(projectName);
    const encodedFilename = encodePathValue(filename);

    const response = await fetch(
      `${API_BASE}/projects/generated/${encodedProjectName}/files/${encodedFilename}/word-text`,
      {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${getToken()}`
        }
      }
    );

    if (!response.ok) {
      const data = await safeJson(response);
      throw new Error(data.detail || `Erro ${response.status}`);
    }

    const text = await response.text();

    contentBox.innerHTML = `
      <h4>Texto para Word: ${escapeHtml(filename)}</h4>
      <pre class="code-box">${escapeHtml(text)}</pre>
    `;

  } catch (error) {
    contentBox.innerHTML = `
      <div class="empty-state error-state">
        <p>${escapeHtml(error.message)}</p>
      </div>
    `;
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
        <h3>${escapeHtml(user.email)}</h3>

        <p><strong>ID:</strong> ${user.id}</p>
        <p><strong>Plano:</strong> ${escapeHtml(user.plan)}</p>
        <p><strong>Limite mensal:</strong> ${formatLimit(user.monthly_generation_limit)}</p>
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


let projectsPageCache = [];

const PROJECT_FILTERS_STORAGE_KEY = "meusProjetosFiltros";

function saveProjectFilters() {
  const searchInput = document.getElementById("projectSearch");
  const validationFilterInput = document.getElementById("projectValidationFilter");
  const sourceFilterInput = document.getElementById("projectSourceFilter");

  const filters = {
    search: searchInput ? searchInput.value : "",
    validation: validationFilterInput ? validationFilterInput.value : "all",
    source: sourceFilterInput ? sourceFilterInput.value : "all",
  };

  localStorage.setItem(PROJECT_FILTERS_STORAGE_KEY, JSON.stringify(filters));
}

function restoreProjectFilters() {
  const searchInput = document.getElementById("projectSearch");
  const validationFilterInput = document.getElementById("projectValidationFilter");
  const sourceFilterInput = document.getElementById("projectSourceFilter");

  const savedFilters = localStorage.getItem(PROJECT_FILTERS_STORAGE_KEY);

  if (!savedFilters) {
    return;
  }

  try {
    const filters = JSON.parse(savedFilters);

    if (searchInput && typeof filters.search === "string") {
      searchInput.value = filters.search;
    }

    if (validationFilterInput && typeof filters.validation === "string") {
      validationFilterInput.value = filters.validation;
    }

    if (sourceFilterInput && typeof filters.source === "string") {
      sourceFilterInput.value = filters.source;
    }
  } catch (error) {
    localStorage.removeItem(PROJECT_FILTERS_STORAGE_KEY);
  }
}

function clearSavedProjectFilters() {
  localStorage.removeItem(PROJECT_FILTERS_STORAGE_KEY);
}

async function loadProjectsPage() {
  const projectsPageList = document.getElementById("projectsPageList");
  const projectsPageMessage = document.getElementById("projectsPageMessage");

  if (!projectsPageList) {
    return;
  }

  if (projectsPageMessage) {
    projectsPageMessage.textContent = "";
    projectsPageMessage.className = "message";
  }

  projectsPageList.innerHTML = `
    <div class="history-loading">
      <p>Carregando projetos...</p>
    </div>
  `;

  try {
    const data = await apiGet("/projects/history");
    projectsPageCache = data.projects || [];

    restoreProjectFilters();
    filterProjectsPage();

  } catch (error) {
    projectsPageList.innerHTML = `
      <div class="empty-state error-state">
        <h3>Erro ao carregar projetos</h3>
        <p>${escapeHtml(error.message)}</p>
      </div>
    `;
  }
}

function projectMatchesSourceFilter(project, sourceFilter) {
  if (!sourceFilter || sourceFilter === "all") {
    return true;
  }

  const source = project.source || "";
  const projectId = Number(project.id);

  if (sourceFilter === "database") {
    return source === "database" || (!source && projectId >= 0);
  }

  if (sourceFilter === "generated_files") {
    return source === "generated_files" || projectId < 0;
  }

  return true;
}

function projectMatchesValidationFilter(project, validationFilter) {
  if (!validationFilter || validationFilter === "all") {
    return true;
  }

  const validation = project.validation;

  if (validationFilter === "without_validation") {
    return !validation;
  }

  if (!validation) {
    return false;
  }

  const validationStatus = validation.status || "unknown";
  const checks = validation.checks || {};
  const hasRequirementsImportCheck = Object.prototype.hasOwnProperty.call(checks, "requirements_match_imports");

  if (validationFilter === "valid") {
    return validationStatus === "valid";
  }

  if (validationFilter === "invalid") {
    return validationStatus !== "valid";
  }

  if (validationFilter === "requirements_imports_ok") {
    return hasRequirementsImportCheck && checks.requirements_match_imports === true;
  }

  if (validationFilter === "requirements_imports_error") {
    return hasRequirementsImportCheck && checks.requirements_match_imports === false;
  }

  if (validationFilter === "requirements_imports_unavailable") {
    return !hasRequirementsImportCheck;
  }

  return true;
}

function clearProjectFilters() {
  const searchInput = document.getElementById("projectSearch");
  const validationFilterInput = document.getElementById("projectValidationFilter");
  const sourceFilterInput = document.getElementById("projectSourceFilter");

  if (searchInput) {
    searchInput.value = "";
  }

  if (validationFilterInput) {
    validationFilterInput.value = "all";
  }

  if (sourceFilterInput) {
    sourceFilterInput.value = "all";
  }

  clearSavedProjectFilters();
  renderProjectsPage(projectsPageCache);
}

function filterProjectsPage() {
  saveProjectFilters();

  const searchInput = document.getElementById("projectSearch");
  const validationFilterInput = document.getElementById("projectValidationFilter");
  const sourceFilterInput = document.getElementById("projectSourceFilter");

  const term = searchInput ? searchInput.value.trim().toLowerCase() : "";
  const validationFilter = validationFilterInput ? validationFilterInput.value : "all";
  const sourceFilter = sourceFilterInput ? sourceFilterInput.value : "all";

  const filteredProjects = projectsPageCache.filter(project => {
    const projectName = String(project.project_name || "").toLowerCase();
    const bug = String(project.bug || "").toLowerCase();
    const status = String(project.status || "").toLowerCase();
    const validationStatus = String(project.validation?.status || "").toLowerCase();
    const sourceLabel = typeof getProjectSourceLabel === "function"
      ? String(getProjectSourceLabel(project)).toLowerCase()
      : "";

    const textMatches = !term || (
      projectName.includes(term) ||
      bug.includes(term) ||
      status.includes(term) ||
      validationStatus.includes(term) ||
      sourceLabel.includes(term)
    );

    const validationMatches = projectMatchesValidationFilter(project, validationFilter);
    const sourceMatches = projectMatchesSourceFilter(project, sourceFilter);

    return textMatches && validationMatches && sourceMatches;
  });

  renderProjectsPage(filteredProjects);
}

function formatValidationCheck(value) {
  return value ? "OK" : "ERRO";
}

function renderProjectValidation(project) {
  const validation = project.validation;

  if (!validation) {
    return `
      <div class="history-validation">
        <p><strong>Validação:</strong> <span class="badge">não disponível</span></p>
        <p class="muted small">
          Este projeto pode ter sido gerado antes da validação automática
          ou não possui o campo validation no metadata.json.
        </p>
      </div>
    `;
  }

  const checks = validation.checks || {};
  const errors = validation.errors || [];
  const validationStatus = validation.status || "unknown";
  const requirementsImportStatus = Object.prototype.hasOwnProperty.call(checks, "requirements_match_imports")
    ? formatValidationCheck(checks.requirements_match_imports)
    : "não disponível";

  const missingImportDependencies = validation.missing_import_dependencies || [];
  const missingImportDependenciesHtml = missingImportDependencies.length
    ? `<span><strong>Dependências ausentes:</strong> ${escapeHtml(missingImportDependencies.join(", "))}</span>`
    : "";

  const errorHtml = errors.length
    ? `
      <div class="history-validation-errors">
        <strong>Erros:</strong>
        <ul>
          ${errors.map(error => `<li>${escapeHtml(error)}</li>`).join("")}
        </ul>
      </div>
    `
    : "";

  return `
    <div class="history-validation">
      <p><strong>Validação:</strong> <span class="badge">${escapeHtml(validationStatus)}</span></p>
      <div class="history-meta">
        <span><strong>main.py:</strong> ${formatValidationCheck(checks.main_py_compiles)}</span>
        <span><strong>README.md:</strong> ${formatValidationCheck(checks.readme_exists)}</span>
        <span><strong>requirements.txt:</strong> ${formatValidationCheck(checks.requirements_exists)}</span>
        <span><strong>FastAPI app:</strong> ${formatValidationCheck(checks.app_declared)}</span>
        <span><strong>Dependências:</strong> ${formatValidationCheck(checks.required_dependencies_present)}</span>
        <span><strong>Requirements x imports:</strong> ${requirementsImportStatus}</span>
        ${missingImportDependenciesHtml}
      </div>
      ${errorHtml}
    </div>
  `;
}


function getProjectSourceFilterLabel(value) {
  const labels = {
    all: "Todos",
    database: "Banco",
    generated_files: "Arquivos locais",
  };

  return labels[value] || "Todos";
}

function getProjectValidationFilterLabel(value) {
  const labels = {
    all: "Todos",
    valid: "Válidos",
    invalid: "Inválidos",
    without_validation: "Sem validação",
    requirements_imports_ok: "Requirements x imports OK",
    requirements_imports_error: "Requirements x imports com erro",
    requirements_imports_unavailable: "Requirements x imports não disponível",
  };

  return labels[value] || "Todos";
}

function buildProjectsEmptyStateMessage() {
  const searchInput = document.getElementById("projectSearch");
  const validationFilterInput = document.getElementById("projectValidationFilter");
  const sourceFilterInput = document.getElementById("projectSourceFilter");

  const term = searchInput ? searchInput.value.trim() : "";
  const validationFilter = validationFilterInput ? validationFilterInput.value : "all";
  const sourceFilter = sourceFilterInput ? sourceFilterInput.value : "all";

  const validationFilterLabel = getProjectValidationFilterLabel(validationFilter);
  const sourceFilterLabel = getProjectSourceFilterLabel(sourceFilter);

  const hasTextFilter = term.length > 0;
  const hasValidationFilter = validationFilter !== "all";
  const hasSourceFilter = sourceFilter !== "all";
  const hasAnyProjectLoaded = Array.isArray(projectsPageCache) && projectsPageCache.length > 0;

  if (hasTextFilter && hasValidationFilter && hasSourceFilter) {
    return {
      title: "Nenhum projeto encontrado",
      description: `Nenhum projeto encontrado para o texto "${term}" com os filtros "${validationFilterLabel}" e "${sourceFilterLabel}". Altere a busca, selecione "Todos" ou gere um novo projeto.`,
    };
  }

  if (hasTextFilter && hasValidationFilter) {
    return {
      title: "Nenhum projeto encontrado",
      description: `Nenhum projeto encontrado para o texto "${term}" com o filtro de validação "${validationFilterLabel}". Altere a busca, selecione "Todos" ou gere um novo projeto.`,
    };
  }

  if (hasTextFilter && hasSourceFilter) {
    return {
      title: "Nenhum projeto encontrado",
      description: `Nenhum projeto encontrado para o texto "${term}" com o filtro de origem "${sourceFilterLabel}". Altere a busca, selecione "Todos" ou gere um novo projeto.`,
    };
  }

  if (hasValidationFilter && hasSourceFilter) {
    return {
      title: "Nenhum projeto encontrado",
      description: `Nenhum projeto encontrado para os filtros "${validationFilterLabel}" e "${sourceFilterLabel}". Altere os filtros para "Todos" ou gere um novo projeto.`,
    };
  }

  if (hasTextFilter) {
    return {
      title: "Nenhum projeto encontrado",
      description: `Nenhum projeto encontrado para o texto "${term}". Altere a busca ou gere um novo projeto.`,
    };
  }

  if (hasValidationFilter) {
    return {
      title: "Nenhum projeto encontrado",
      description: `Nenhum projeto encontrado para o filtro selecionado: "${validationFilterLabel}". Altere o filtro para "Todos" ou gere um novo projeto com esse tipo de validação.`,
    };
  }

  if (hasSourceFilter) {
    return {
      title: "Nenhum projeto encontrado",
      description: `Nenhum projeto encontrado para o filtro de origem selecionado: "${sourceFilterLabel}". Altere o filtro para "Todos" ou gere um novo projeto.`,
    };
  }

  if (!hasAnyProjectLoaded) {
    return {
      title: "Nenhum projeto encontrado",
      description: "Gere uma solução técnica no dashboard para que ela apareça aqui.",
    };
  }

  return {
    title: "Nenhum projeto encontrado",
    description: "Nenhum projeto corresponde aos critérios selecionados.",
  };
}

function renderProjectsActiveFilters() {
  const activeFiltersBox = document.getElementById("projectsActiveFilters");

  if (!activeFiltersBox) {
    return;
  }

  const searchInput = document.getElementById("projectSearch");
  const validationFilterInput = document.getElementById("projectValidationFilter");
  const sourceFilterInput = document.getElementById("projectSourceFilter");

  const term = searchInput ? searchInput.value.trim() : "";
  const validationFilter = validationFilterInput ? validationFilterInput.value : "all";
  const sourceFilter = sourceFilterInput ? sourceFilterInput.value : "all";

  const validationFilterLabel = getProjectValidationFilterLabel(validationFilter);
  const sourceFilterLabel = getProjectSourceFilterLabel(sourceFilter);

  const activeFilters = [];

  if (term.length > 0) {
    activeFilters.push(`<span><strong>Busca:</strong> ${escapeHtml(term)}</span>`);
  }

  if (validationFilter !== "all") {
    activeFilters.push(`<span><strong>Validação:</strong> ${escapeHtml(validationFilterLabel)}</span>`);
  }

  if (sourceFilter !== "all") {
    activeFilters.push(`<span><strong>Origem:</strong> ${escapeHtml(sourceFilterLabel)}</span>`);
  }

  if (activeFilters.length === 0) {
    activeFiltersBox.innerHTML = `
      <p class="muted small"><strong>Filtros ativos:</strong> nenhum filtro ativo</p>
    `;
    return;
  }

  activeFiltersBox.innerHTML = `
    <p><strong>Filtros ativos</strong></p>
    <div class="history-meta">
      ${activeFilters.join("")}
    </div>
  `;
}

function renderProjectsFilteredCount(projects) {
  const counterBox = document.getElementById("projectsFilteredCount");

  if (!counterBox) {
    return;
  }

  const displayedCount = projects ? projects.length : 0;
  const totalCount = Array.isArray(projectsPageCache) ? projectsPageCache.length : 0;

  if (totalCount === 0) {
    counterBox.innerHTML = `
      <p class="muted small"><strong>Projetos exibidos:</strong> 0</p>
    `;
    return;
  }

  if (displayedCount === totalCount) {
    counterBox.innerHTML = `
      <p class="muted small"><strong>Projetos exibidos:</strong> ${displayedCount}</p>
    `;
    return;
  }

  counterBox.innerHTML = `
    <p class="muted small"><strong>Projetos exibidos:</strong> ${displayedCount} de ${totalCount}</p>
  `;
}

function renderProjectsValidationSummary(projects) {
  const summaryBox = document.getElementById("projectsValidationSummary");

  if (!summaryBox) {
    return;
  }

  const total = projects ? projects.length : 0;

  if (total === 0) {
    summaryBox.innerHTML = "";
    return;
  }

  let validCount = 0;
  let invalidCount = 0;
  let unavailableCount = 0;
  let requirementsImportsOkCount = 0;
  let requirementsImportsErrorCount = 0;
  let requirementsImportsUnavailableCount = 0;

  projects.forEach(project => {
    const validation = project.validation;

    if (!validation) {
      unavailableCount += 1;
      requirementsImportsUnavailableCount += 1;
      return;
    }

    const validationStatus = validation.status || "unknown";
    const checks = validation.checks || {};

    if (validationStatus === "valid") {
      validCount += 1;
    } else {
      invalidCount += 1;
    }

    if (Object.prototype.hasOwnProperty.call(checks, "requirements_match_imports")) {
      if (checks.requirements_match_imports) {
        requirementsImportsOkCount += 1;
      } else {
        requirementsImportsErrorCount += 1;
      }
    } else {
      requirementsImportsUnavailableCount += 1;
    }
  });

  summaryBox.innerHTML = `
    <p><strong>Resumo da validação</strong></p>
    <div class="history-meta">
      <span><strong>Projetos:</strong> ${total}</span>
      <span><strong>Válidos:</strong> ${validCount}</span>
      <span><strong>Inválidos:</strong> ${invalidCount}</span>
      <span><strong>Sem validação:</strong> ${unavailableCount}</span>
      <span><strong>Requirements x imports OK:</strong> ${requirementsImportsOkCount}</span>
      <span><strong>Requirements x imports com erro:</strong> ${requirementsImportsErrorCount}</span>
      <span><strong>Requirements x imports não disponível:</strong> ${requirementsImportsUnavailableCount}</span>
    </div>
  `;
}

function renderProjectsPage(projects) {
  renderProjectsActiveFilters();
  renderProjectsFilteredCount(projects);
  renderProjectsValidationSummary(projects);

  const projectsPageList = document.getElementById("projectsPageList");

  if (!projectsPageList) {
    return;
  }

  if (!projects || projects.length === 0) {
    const emptyState = buildProjectsEmptyStateMessage();

    projectsPageList.innerHTML = `
      <div class="empty-state">
        <h3>${escapeHtml(emptyState.title)}</h3>
        <p>${escapeHtml(emptyState.description)}</p>
      </div>
    `;
    return;
  }

  projectsPageList.innerHTML = projects.map(project => {
    const projectName = project.project_name || "";
    const displayName = projectName || "Projeto sem nome";
    const status = project.status || "-";
    const createdAt = formatDateTime(project.created_at);
    const bug = project.bug || "-";
    const shortBug = bug.length > 260 ? `${bug.substring(0, 260)}...` : bug;
    const safeProjectName = escapeHtml(projectName);
    const filesContainerId = `projectsPageFiles_${project.id}`;

    return `
      <article class="history-card project-page-card">
        <div class="history-card-header">
          <div>
            <h3>${escapeHtml(displayName)}</h3>
            <p class="muted small">ID: ${project.id || "-"}</p>
          </div>
          <span class="badge">${escapeHtml(status)}</span>
        </div>

        <div class="history-meta">
          <span><strong>Criado em:</strong> ${escapeHtml(createdAt)}</span>
        </div>

        <p class="history-bug">
          <strong>Bug:</strong> ${escapeHtml(shortBug)}
        </p>

        ${renderProjectValidation(project)}

        <div class="history-actions">
          <button onclick="loadProjectFiles('${safeProjectName}', '${filesContainerId}')">
            Ver arquivos
          </button>

          <button onclick="downloadProjectZip('${safeProjectName}')">
            Baixar ZIP
          </button>
        </div>

        <div id="${filesContainerId}" class="project-files-box hidden"></div>

        <details class="history-details">
          <summary>Ver detalhes</summary>
          <div class="history-detail-content">
            <p><strong>Nome do projeto:</strong></p>
            <pre class="code-box">${escapeHtml(displayName)}</pre>

            <p><strong>Descrição completa do bug:</strong></p>
            <pre class="code-box">${escapeHtml(bug)}</pre>

            <p><strong>Resposta bruta do histórico:</strong></p>
            <pre class="code-box">${escapeHtml(JSON.stringify(project, null, 2))}</pre>
          </div>
        </details>
      </article>
    `;
  }).join("");
}


// ============================================================
// Planos e assinatura (Asaas)
// ============================================================

const PLAN_LABELS = { free: "Free", pro: "Pro", team: "Team", admin: "Admin" };

const SUBSCRIPTION_STATUS_LABELS = {
  pending: "Aguardando pagamento",
  active: "Ativa",
  past_due: "Pagamento em atraso",
  canceled: "Cancelada"
};

function formatMoney(value) {
  return Number(value).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatDate(value) {
  if (!value) return "-";
  const iso = String(value).endsWith("Z") ? value : `${value}Z`;
  return new Date(iso).toLocaleDateString("pt-BR");
}

async function loadPlansPage() {
  const statusBox = document.getElementById("subscriptionStatus");
  const grid = document.getElementById("plansGrid");

  if (!statusBox || !grid) return;

  try {
    const [catalog, mine] = await Promise.all([
      apiGet("/billing/plans"),
      apiGet("/billing/subscription")
    ]);

    renderSubscriptionStatus(mine);
    renderPlans(catalog, mine);
  } catch (error) {
    setMessage("subscriptionMessage", error.message, "error");
  }
}

function renderSubscriptionStatus(mine) {
  const statusBox = document.getElementById("subscriptionStatus");
  const sub = mine.subscription;

  let html = `<p><strong>Plano atual:</strong> <span class="badge">${escapeHtml(PLAN_LABELS[mine.current_plan] || mine.current_plan)}</span></p>`;

  if (sub) {
    html += `
      <p><strong>Assinatura:</strong> plano ${escapeHtml(PLAN_LABELS[sub.plan] || sub.plan)} — ${escapeHtml(SUBSCRIPTION_STATUS_LABELS[sub.status] || sub.status)}</p>
      <p><strong>Valor:</strong> ${formatMoney(sub.value)}/mês</p>
    `;

    if (sub.current_period_end) {
      const label = sub.status === "canceled" ? "Acesso até" : "Pago até";
      html += `<p><strong>${label}:</strong> ${formatDate(sub.current_period_end)}</p>`;
    }

    const actions = [];

    if (sub.invoice_url && ["pending", "past_due"].includes(sub.status)) {
      actions.push(`<button onclick="window.open('${escapeHtml(sub.invoice_url)}', '_blank', 'noopener')">Pagar fatura</button>`);
    }

    if (["pending", "active", "past_due"].includes(sub.status)) {
      actions.push(`<button class="danger" onclick="cancelSubscription()">Cancelar assinatura</button>`);
    }

    if (actions.length) {
      html += `<div class="actions">${actions.join("")}</div>`;
    }
  } else {
    html += `<p class="muted">Você ainda não tem assinatura. Escolha um plano abaixo.</p>`;
  }

  statusBox.innerHTML = html;
}

function renderPlans(catalog, mine) {
  const grid = document.getElementById("plansGrid");
  const sub = mine.subscription;
  const hasPaidAccess = sub && ["active", "past_due"].includes(sub.status);

  grid.innerHTML = catalog.plans.map((plan) => {
    const isCurrent = mine.current_plan === plan.plan;
    const price = plan.price > 0 ? `${formatMoney(plan.price)} <small>/mês</small>` : "Grátis";

    let button = "";
    if (plan.plan !== "free") {
      if (!catalog.billing_enabled) {
        button = `<button disabled>Em breve</button>`;
      } else if (isCurrent) {
        button = `<button disabled>Plano atual</button>`;
      } else if (hasPaidAccess) {
        button = `<button disabled title="Cancele a assinatura atual para trocar de plano">Assinar</button>`;
      } else {
        button = `<button onclick="showCheckout('${plan.plan}', '${escapeHtml(plan.name)}')">Assinar</button>`;
      }
    }

    return `
      <article class="card plan-card ${isCurrent ? "current" : ""}">
        <h2>${escapeHtml(plan.name)}</h2>
        <p class="plan-price">${price}</p>
        <p>${escapeHtml(String(plan.monthly_generation_limit))} gerações por mês</p>
        <div class="actions">${button}</div>
      </article>
    `;
  }).join("");
}

function showCheckout(plan, name) {
  document.getElementById("checkoutPlan").value = plan;
  document.getElementById("checkoutPlanName").textContent = name;
  document.getElementById("checkoutCard").classList.remove("hidden");
  setMessage("checkoutMessage", "");
  document.getElementById("checkoutName").focus();
}

function hideCheckout() {
  document.getElementById("checkoutCard").classList.add("hidden");
}

async function handleCheckout(event) {
  event.preventDefault();

  const plan = document.getElementById("checkoutPlan").value;
  const name = document.getElementById("checkoutName").value.trim();
  const cpf_cnpj = document.getElementById("checkoutDocument").value.trim();
  const acceptTermsInput = document.getElementById("checkoutAcceptTerms");
  const accept_terms = acceptTermsInput ? acceptTermsInput.checked : false;

  if (!accept_terms) {
    setMessage("checkoutMessage", "Para assinar, aceite os Termos de Uso e a Política de Privacidade.", "error");
    return;
  }

  setMessage("checkoutMessage", "Gerando sua fatura...");

  try {
    const data = await apiPost("/billing/checkout", { plan, name, cpf_cnpj, accept_terms });

    if (data.invoice_url) {
      setMessage("checkoutMessage", "Abrindo a página de pagamento...", "success");
      window.location.href = data.invoice_url;
    } else {
      setMessage("checkoutMessage", "Assinatura criada. A fatura será enviada para o seu e-mail.", "success");
      await loadPlansPage();
    }
  } catch (error) {
    setMessage("checkoutMessage", error.message, "error");
  }
}

async function cancelSubscription() {
  const confirmed = window.confirm(
    "Cancelar a assinatura? Você mantém o acesso até o fim do período já pago."
  );

  if (!confirmed) return;

  try {
    await apiPost("/billing/cancel", {});
    setMessage("subscriptionMessage", "Assinatura cancelada.", "success");
    await loadPlansPage();
  } catch (error) {
    setMessage("subscriptionMessage", error.message, "error");
  }
}


// ------------------------------------------------------------
// Esqueci minha senha
// ------------------------------------------------------------

async function handleForgotPassword(event) {
  event.preventDefault();

  const email = document.getElementById("forgotEmail").value.trim();
  const button = event.target.querySelector("button[type=submit]");

  setMessage("forgotMessage", "Enviando...");
  if (button) button.disabled = true;

  try {
    const response = await fetch(`${API_BASE}/auth/forgot-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email })
    });
    const data = await safeJson(response);

    if (!response.ok) {
      const detail = Array.isArray(data.detail) ? "Informe um e-mail válido." : data.detail;
      throw new Error(detail || "Não foi possível enviar agora. Tente novamente.");
    }

    setMessage("forgotMessage", data.detail, "success");
  } catch (error) {
    setMessage("forgotMessage", error.message, "error");
  } finally {
    if (button) button.disabled = false;
  }
}

function getResetTokenFromUrl() {
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  return params.get("token") || "";
}

function setupResetPage() {
  const form = document.getElementById("resetForm");
  if (!form) return;

  if (!getResetTokenFromUrl()) {
    form.classList.add("hidden");
    document.getElementById("resetMissingToken").classList.remove("hidden");
  }
}

async function handleResetPassword(event) {
  event.preventDefault();

  const token = getResetTokenFromUrl();
  const password = document.getElementById("resetPassword").value;
  const confirm = document.getElementById("resetPasswordConfirm").value;

  if (password.length < 8) {
    setMessage("resetMessage", "A senha precisa ter pelo menos 8 caracteres.", "error");
    return;
  }

  if (password !== confirm) {
    setMessage("resetMessage", "As senhas não conferem.", "error");
    return;
  }

  setMessage("resetMessage", "Salvando...");

  try {
    const response = await fetch(`${API_BASE}/auth/reset-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, password })
    });
    const data = await safeJson(response);

    if (!response.ok) {
      const detail = Array.isArray(data.detail)
        ? "Este link é inválido ou expirou. Peça um novo em \"Esqueci minha senha\"."
        : data.detail;
      throw new Error(detail || "Não foi possível alterar a senha.");
    }

    // Tira o token da barra de endereços e encerra a sessão antiga deste navegador.
    history.replaceState(null, "", window.location.pathname);
    clearToken();
    document.getElementById("resetForm").classList.add("hidden");
    setMessage("resetMessage", "Senha alterada. Redirecionando para o login...", "success");

    setTimeout(() => {
      window.location.href = "/static/login.html";
    }, 1800);
  } catch (error) {
    setMessage("resetMessage", error.message, "error");
  }
}

// ------------------------------------------------------------
// Páginas públicas (vendas, termos, privacidade)
// ------------------------------------------------------------

function formatVersionDate(value) {
  // "2026-09-30" -> "30/09/2026"
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value || "");
  return match ? `${match[3]}/${match[2]}/${match[1]}` : (value || "");
}

async function loadLegalInfo() {
  const needsInfo = document.querySelector("[data-legal], [data-legal-seller], [data-legal-mailto]");
  if (!needsInfo) return;

  let info;

  try {
    const response = await fetch(`${API_BASE}/legal/info`);
    if (!response.ok) return;
    info = await response.json();
  } catch (error) {
    return;
  }

  info.terms_version_br = formatVersionDate(info.terms_version);

  document.querySelectorAll("[data-legal]").forEach((element) => {
    const value = info[element.dataset.legal];
    if (value) element.textContent = value;
  });

  const sellerParts = [];
  if (info.seller_name) sellerParts.push(info.seller_name);
  if (info.seller_document) sellerParts.push(`${info.seller_document_label} ${info.seller_document}`);
  if (info.seller_city) sellerParts.push(info.seller_city);

  document.querySelectorAll("[data-legal-seller]").forEach((element) => {
    element.textContent = sellerParts.join(" · ");
  });

  document.querySelectorAll("[data-legal-mailto]").forEach((element) => {
    if (info.contact_email) {
      element.href = `mailto:${info.contact_email}`;
    } else {
      element.classList.add("hidden");
    }
  });
}

async function loadPublicPlans() {
  const container = document.getElementById("publicPlans");
  if (!container) return;

  let catalog;

  try {
    const response = await fetch(`${API_BASE}/billing/plans`);
    if (!response.ok) return;
    catalog = await response.json();
  } catch (error) {
    // Mantém a tabela estática que já está no HTML.
    return;
  }

  if (!catalog.plans || !catalog.plans.length) return;

  container.innerHTML = catalog.plans.map((plan) => {
    const isFree = Number(plan.price) === 0;
    const featured = plan.plan === "pro";
    const price = isFree
      ? "Grátis"
      : `${escapeHtml(formatMoney(plan.price))}<span>/mês</span>`;
    const limit = Number(plan.monthly_generation_limit) === -1
      ? "Gerações ilimitadas"
      : `${plan.monthly_generation_limit} gerações por mês`;
    const label = isFree ? "Criar conta" : `Assinar o ${escapeHtml(plan.name)}`;
    const buttonClass = featured ? "site-button" : "site-button site-button-outline";

    return `
      <article class="price-card${featured ? " price-card-featured" : ""}">
        <h3>${escapeHtml(plan.name)}</h3>
        <p class="price">${price}</p>
        <p class="price-limit">${escapeHtml(limit)}</p>
        <a class="${buttonClass}" href="/static/register.html">${label}</a>
      </article>
    `;
  }).join("");
}


document.addEventListener("DOMContentLoaded", () => {
  loadLegalInfo();

  const loginForm = document.getElementById("loginForm");
  const registerForm = document.getElementById("registerForm");

  if (loginForm) {
    loginForm.addEventListener("submit", handleLogin);
  }

  if (registerForm) {
    registerForm.addEventListener("submit", handleRegister);
  }

  const forgotForm = document.getElementById("forgotForm");

  if (forgotForm) {
    forgotForm.addEventListener("submit", handleForgotPassword);
  }

  const resetForm = document.getElementById("resetForm");

  if (resetForm) {
    setupResetPage();
    resetForm.addEventListener("submit", handleResetPassword);
  }

  const checkoutForm = document.getElementById("checkoutForm");

  if (checkoutForm) {
    checkoutForm.addEventListener("submit", handleCheckout);
  }
});