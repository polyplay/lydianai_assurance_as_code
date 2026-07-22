import { ApiClient, defaultApiBaseUrl } from "./api/client.js";
import { createResources } from "./api/resources.js";
import { state, resetSession, selectProject, setToken } from "./state.js";
import {
  escapeHtml,
  formatError,
  setPage,
  setRouteStatus,
  toast,
} from "./components/ui.js";
import { renderOverview } from "./features/overview.js";
import { renderEvidence } from "./features/evidence.js";
import { renderImports } from "./features/imports.js";
import { renderTraceability } from "./features/traceability.js";
import { renderValidation } from "./features/validation.js";
import { renderImpact } from "./features/impact.js";
import { renderRelease } from "./features/release.js";
import { renderJobs } from "./features/jobs.js";
import { renderAdministration } from "./features/administration.js";

const elements = {
  loginView: document.querySelector("#login-view"),
  appView: document.querySelector("#app-view"),
  loginForm: document.querySelector("#login-form"),
  loginError: document.querySelector("#login-error"),
  apiBaseUrl: document.querySelector("#api-base-url"),
  projectSelect: document.querySelector("#project-select"),
  primaryNav: document.querySelector("#primary-nav"),
  actorSummary: document.querySelector("#actor-summary"),
  releaseState: document.querySelector("#release-state"),
  sessionDetails: document.querySelector("#session-details"),
  pageContent: document.querySelector("#page-content"),
  sidebar: document.querySelector("#sidebar"),
  navToggle: document.querySelector("#nav-toggle"),
};

const initialBaseUrl = defaultApiBaseUrl();
localStorage.removeItem("aac_api_base_url");
elements.apiBaseUrl.value = initialBaseUrl;

const client = new ApiClient({
  baseUrl: initialBaseUrl,
  tokenProvider: () => state.token,
  onUnauthorized: () => logout("Your session expired. Sign in again."),
});
const api = createResources(client);

const routes = {
  overview: renderOverview,
  work: renderOverview,
  evidence: renderEvidence,
  imports: renderImports,
  trace: renderTraceability,
  validation: renderValidation,
  impact: renderImpact,
  release: renderRelease,
  jobs: renderJobs,
  administration: renderAdministration,
};

const navigation = [
  {
    group: "Workspace",
    items: [
      { route: "overview", label: "Overview", capability: "project.read" },
      { route: "work", label: "My Work", capability: "project.read", count: "work" },
      { route: "jobs", label: "Jobs", capability: "job.read", count: "jobs" },
    ],
  },
  {
    group: "Evidence",
    items: [
      { route: "evidence", label: "Artefacts & Relationships", capability: "artefact.read" },
      { route: "imports", label: "Imports", capability: "import.read", count: "imports" },
      { route: "trace", label: "Traceability", capability: "trace.read" },
    ],
  },
  {
    group: "Assurance",
    items: [
      {
        route: "validation",
        label: "Validation",
        capability: "validation.read",
        count: "validation",
      },
      { route: "impact", label: "Impact & Suspects", capability: "trace.read", count: "suspects" },
      { route: "release", label: "Release", capability: "baseline.read" },
    ],
  },
  {
    group: "Management",
    items: [
      {
        route: "administration",
        label: "Administration",
        capability: "team.read",
      },
    ],
  },
];

let renderedRoute = "";

elements.loginForm.addEventListener("submit", handleLogin);
document.querySelector("#show-login-password").addEventListener("change", (event) => {
  document.querySelector("#login-password").type = event.target.checked ? "text" : "password";
});
elements.projectSelect.addEventListener("change", handleProjectChange);
document.querySelector("#signout-button").addEventListener("click", () => logout());
document.querySelector("#refresh-button").addEventListener("click", () => renderRoute(true));
elements.navToggle.addEventListener("click", toggleNavigation);
elements.primaryNav.addEventListener("click", (event) => {
  if (event.target.closest(".nav-link")) {
    resetRoutePosition();
  }
});
window.addEventListener("hashchange", () => {
  closeNavigation();
  renderRoute();
});

bootstrap();

async function bootstrap() {
  if (!state.token) {
    showLogin();
    return;
  }
  try {
    await loadSession();
  } catch {
    logout("Your saved session is no longer valid.");
  }
}

async function handleLogin(event) {
  event.preventDefault();
  elements.loginError.hidden = true;
  const submit = elements.loginForm.querySelector("button[type=submit]");
  submit.disabled = true;
  submit.textContent = "Signing in...";
  try {
    const baseUrl = elements.apiBaseUrl.value.trim() || defaultApiBaseUrl();
    client.setBaseUrl(baseUrl);
    const response = await api.login(
      document.querySelector("#login-username").value.trim(),
      document.querySelector("#login-password").value,
    );
    setToken(response.data.access_token);
    document.querySelector("#login-password").value = "";
    await loadSession();
  } catch (error) {
    elements.loginError.textContent = error.message;
    elements.loginError.hidden = false;
  } finally {
    submit.disabled = false;
    submit.textContent = "Sign in";
  }
}

async function loadSession() {
  setRouteStatus("Loading session...");
  const [meResponse, projectsResponse] = await Promise.all([api.me(), api.projects()]);
  state.user = meResponse.data;
  state.projects = projectsResponse.data;
  if (!state.projects.length) {
    if (state.user.roles?.includes("admin")) {
      selectProject("");
      showApplication();
      renderProjectBootstrap();
      return;
    }
    throw new Error("No projects are available to this account.");
  }
  if (!state.projects.some((project) => project.project_id === state.projectId)) {
    selectProject(state.projects[0].project_id);
  }
  populateProjects();
  await refreshWorkspace();
  showApplication();
  if (!window.location.hash) {
    window.location.hash = "#/overview";
  }
  await renderRoute();
}

async function handleProjectChange() {
  selectProject(elements.projectSelect.value);
  renderedRoute = "";
  await refreshWorkspace();
  await renderRoute();
}

async function refreshWorkspace() {
  const response = await api.workspace(state.projectId);
  state.workspace = response.data;
  renderNavigation();
  renderActor();
  renderReleaseState();
}

async function renderRoute(refresh = false) {
  if (!state.token || !state.projectId || !state.workspace) {
    return;
  }
  const route = currentRoute();
  const routeChanged = route !== renderedRoute;
  const renderer = routes[route] || renderOverview;
  if (routeChanged) {
    resetRoutePosition();
  }
  setActiveNavigation(route);
  setRouteStatus(refresh ? "Refreshing..." : "Loading...");
  elements.pageContent.innerHTML = '<div class="card">Loading current project data...</div>';
  try {
    if (refresh) {
      await refreshWorkspace();
    }
    await renderer({
      api,
      state,
      root: elements.pageContent,
      refreshWorkspace,
      refresh: () => renderRoute(true),
      navigate: (path) => {
        window.location.hash = `#/${path}`;
      },
      notify: toast,
      reloadSession: loadSession,
      isCurrentRoute: (name) => currentRoute() === name,
    });
    renderedRoute = route;
    if (routeChanged) {
      resetRoutePosition();
      document.querySelector("#main-content").focus({ preventScroll: true });
    }
    setRouteStatus("Current data loaded.");
  } catch (error) {
    elements.pageContent.innerHTML = formatError(error);
    renderedRoute = route;
    if (routeChanged) {
      resetRoutePosition();
      document.querySelector("#main-content").focus({ preventScroll: true });
    }
    setRouteStatus("The current view could not be loaded.");
  }
}

function renderProjectBootstrap() {
  elements.projectSelect.innerHTML = '<option value="">No projects</option>';
  elements.primaryNav.innerHTML = "";
  elements.actorSummary.textContent = state.user.user.display_name;
  elements.releaseState.textContent = "Create the first project to begin.";
  setPage({
    eyebrow: "Administration",
    title: "Create the first project",
    description: "A project provides the controlled boundary for roles, evidence, and releases.",
  });
  setRouteStatus("No project exists.");
  elements.pageContent.innerHTML = `
    <section class="card" style="max-width: 760px">
      <form id="bootstrap-project-form" class="form-grid">
        <label class="field-required">Project key<input name="project_key" required></label>
        <label class="field-required">Name<input name="name" required></label>
        <label class="full">Description<textarea name="description"></textarea></label>
        <label>ASIL level<select name="asil_level">
          <option value="QM">QM</option><option value="ASIL_A">ASIL A</option>
          <option value="ASIL_B">ASIL B</option><option value="ASIL_C">ASIL C</option>
          <option value="ASIL_D" selected>ASIL D</option>
        </select></label>
        <label>ASPICE target capability<input name="aspice_capability" type="number"
          min="1" max="3" value="3"></label>
        <div class="full"><button class="button primary" type="submit">Create project</button></div>
      </form>
    </section>`;
  const form = document.querySelector("#bootstrap-project-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    button.textContent = "Creating...";
    try {
      const response = await api.createProject(projectPayload(form));
      selectProject(response.data.project_id);
      await loadSession();
    } catch (error) {
      toast(error.message, "error");
      button.disabled = false;
      button.textContent = "Create project";
    }
  });
}

function projectPayload(form) {
  return {
    project_key: form.elements.project_key.value.trim(),
    name: form.elements.name.value.trim(),
    description: form.elements.description.value.trim(),
    assurance_configuration: {
      asil_level: form.elements.asil_level.value,
      aspice_default_capability_level: Number(form.elements.aspice_capability.value),
    },
  };
}

function renderNavigation() {
  const capabilities = state.workspace.capabilities;
  elements.primaryNav.innerHTML = navigation
    .map((group) => {
      const items = group.items
        .filter((item) => capabilities[item.capability])
        .map(
          (item) => `<a class="nav-link" href="#/${escapeHtml(item.route)}"
            data-route="${escapeHtml(item.route)}">${escapeHtml(item.label)}
            ${navCount(item.count)}</a>`,
        )
        .join("");
      return items
        ? `<div class="nav-group"><p class="nav-group-title">${escapeHtml(
            group.group,
          )}</p>${items}</div>`
        : "";
    })
    .join("");
  setActiveNavigation(currentRoute());
}

function navCount(kind) {
  if (!kind) {
    return "";
  }
  const summary = state.workspace.summary;
  const values = {
    work: state.workspace.actionable_work.reduce((total, item) => total + item.count, 0),
    jobs: summary.jobs.active,
    imports: summary.imports.waiting_for_user,
    validation: summary.validation.open,
    suspects: summary.suspects.open,
  };
  return values[kind] ? `<span class="nav-count">${escapeHtml(values[kind])}</span>` : "";
}

function renderActor() {
  const actor = state.workspace.actor;
  elements.actorSummary.textContent = `${actor.display_name} · ${
    actor.effective_roles.join(", ") || "no role"
  }`;
  elements.sessionDetails.innerHTML = `
    <dt>User</dt><dd>${escapeHtml(actor.username)}</dd>
    <dt>Roles</dt><dd>${escapeHtml(actor.effective_roles.join(", ") || "none")}</dd>
    <dt>Project</dt><dd>${escapeHtml(state.workspace.project.project_key)}</dd>
  `;
}

function renderReleaseState() {
  const readiness = state.workspace.release_readiness;
  elements.releaseState.innerHTML = `<strong>Release readiness</strong><br>
    <span class="status ${escapeHtml(readiness.state)}">${escapeHtml(
      readiness.state.replaceAll("_", " "),
    )}</span>`;
}

function populateProjects() {
  elements.projectSelect.innerHTML = state.projects
    .map(
      (project) =>
        `<option value="${escapeHtml(project.project_id)}" ${
          project.project_id === state.projectId ? "selected" : ""
        }>${escapeHtml(project.project_key)} · ${escapeHtml(project.name)}</option>`,
    )
    .join("");
}

function setActiveNavigation(route) {
  for (const link of document.querySelectorAll(".nav-link")) {
    const active = link.dataset.route === route;
    link.classList.toggle("active", active);
    if (active) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  }
}

function currentRoute() {
  return window.location.hash.replace(/^#\//, "").split("?")[0] || "overview";
}

function resetRoutePosition() {
  window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  document.querySelector("#main-content").scrollTo?.({ top: 0, left: 0, behavior: "auto" });
}

function showLogin() {
  elements.loginView.hidden = false;
  elements.appView.hidden = true;
  window.scrollTo(0, 0);
  window.setTimeout(() => document.querySelector("#login-username").focus(), 0);
}

function showApplication() {
  elements.loginView.hidden = true;
  elements.appView.hidden = false;
  window.scrollTo(0, 0);
}

function logout(message = "") {
  resetSession();
  showLogin();
  if (message) {
    elements.loginError.textContent = message;
    elements.loginError.hidden = false;
  }
}

function toggleNavigation() {
  const open = elements.sidebar.classList.toggle("open");
  elements.navToggle.setAttribute("aria-expanded", String(open));
  elements.navToggle.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
}

function closeNavigation() {
  elements.sidebar.classList.remove("open");
  elements.navToggle.setAttribute("aria-expanded", "false");
  elements.navToggle.setAttribute("aria-label", "Open navigation");
}
