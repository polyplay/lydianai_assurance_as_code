const defaultState = {
  token: sessionStorage.getItem("aac_token") || "",
  user: null,
  projects: [],
  projectId: localStorage.getItem("aac_project_id") || "",
  workspace: null,
};

export const state = { ...defaultState };

export function setToken(token) {
  state.token = token;
  if (token) {
    sessionStorage.setItem("aac_token", token);
  } else {
    sessionStorage.removeItem("aac_token");
  }
}

export function selectProject(projectId) {
  state.projectId = projectId;
  state.workspace = null;
  if (projectId) {
    localStorage.setItem("aac_project_id", projectId);
  } else {
    localStorage.removeItem("aac_project_id");
  }
}

export function resetSession() {
  setToken("");
  state.user = null;
  state.projects = [];
  state.workspace = null;
}
