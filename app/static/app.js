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
    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return date.toLocaleString("pt-BR");
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

  setMessage("registerMessage", "Criando conta...");

  if (password !== passwordConfirm) {
    setMessage("registerMessage", "As senhas não conferem.", "error");
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
        password
      })
    });

    const data = await safeJson(response);

    if (!response.ok) {
      throw new Error(data.detail || "Erro ao criar conta.");
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

  if (!bugInput) {
    return;
  }

  const bug = bugInput.value.trim();

  if (!bug) {
    setMessage("generateMessage", "Informe a descrição do bug.", "error");
    return;
  }

  clearSolutionResult();
  setMessage("generateMessage", "Gerando solução técnica. Aguarde...");

  try {
    const data = await apiPost("/projects/generate-solution", { bug });

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


let projectsPageCache = [];

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

    renderProjectsPage(projectsPageCache);

  } catch (error) {
    projectsPageList.innerHTML = `
      <div class="empty-state error-state">
        <h3>Erro ao carregar projetos</h3>
        <p>${escapeHtml(error.message)}</p>
      </div>
    `;
  }
}

function filterProjectsPage() {
  const searchInput = document.getElementById("projectSearch");
  const term = searchInput ? searchInput.value.trim().toLowerCase() : "";

  if (!term) {
    renderProjectsPage(projectsPageCache);
    return;
  }

  const filteredProjects = projectsPageCache.filter(project => {
    const projectName = String(project.project_name || "").toLowerCase();
    const bug = String(project.bug || "").toLowerCase();
    const status = String(project.status || "").toLowerCase();
    const validationStatus = String(project.validation?.status || "").toLowerCase();

    return (
      projectName.includes(term) ||
      bug.includes(term) ||
      status.includes(term) ||
      validationStatus.includes(term)
    );
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
      <div class="history-meta">
        <span><strong>Validação:</strong> não disponível</span>
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
  renderProjectsValidationSummary(projects);

  const projectsPageList = document.getElementById("projectsPageList");

  if (!projectsPageList) {
    return;
  }

  if (!projects || projects.length === 0) {
    projectsPageList.innerHTML = `
      <div class="empty-state">
        <h3>Nenhum projeto encontrado</h3>
        <p>Gere uma solução técnica no dashboard para que ela apareça aqui.</p>
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


document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.getElementById("loginForm");
  const registerForm = document.getElementById("registerForm");

  if (loginForm) {
    loginForm.addEventListener("submit", handleLogin);
  }

  if (registerForm) {
    registerForm.addEventListener("submit", handleRegister);
  }
});