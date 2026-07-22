const projectPath = (projectId, suffix = "") =>
  `/projects/${encodeURIComponent(projectId)}${suffix}`;

export function createResources(client) {
  return {
    login: (username, password) =>
      client.post(
        "/auth/login",
        { username, password },
        { suppressUnauthorizedCallback: true },
      ),
    me: () => client.get("/users/me"),
    projects: () => client.get("/projects"),
    createProject: (payload) => client.post("/projects", payload),
    workspace: (projectId) => client.get(projectPath(projectId, "/workspace")),
    project: (projectId) => client.get(projectPath(projectId)),
    projectConfig: (projectId) => client.get(projectPath(projectId, "/config")),
    updateProjectConfig: (projectId, payload) =>
      client.put(projectPath(projectId, "/config"), payload),
    members: (projectId) => client.get(projectPath(projectId, "/members")),
    addMember: (projectId, payload) => client.post(projectPath(projectId, "/members"), payload),
    removeMember: (projectId, userId) =>
      client.delete(projectPath(projectId, `/members/${encodeURIComponent(userId)}`)),
    users: () => client.get("/users"),
    createUser: (payload) => client.post("/users", payload),

    schemas: (projectId) => client.get(projectPath(projectId, "/schemas")),
    schema: (projectId, type) =>
      client.get(projectPath(projectId, `/schemas/${encodeURIComponent(type)}`)),
    updateSchema: (projectId, type, payload) =>
      client.put(projectPath(projectId, `/schemas/${encodeURIComponent(type)}`), payload),
    artefacts: (projectId) => client.get(projectPath(projectId, "/artefacts")),
    artefact: (projectId, artefactId) =>
      client.get(projectPath(projectId, `/artefacts/${encodeURIComponent(artefactId)}`)),
    createArtefact: (projectId, payload) =>
      client.post(projectPath(projectId, "/artefacts"), payload),
    updateArtefact: (projectId, artefactId, payload) =>
      client.put(projectPath(projectId, `/artefacts/${encodeURIComponent(artefactId)}`), payload),
    deleteArtefact: (projectId, artefactId, payload) =>
      client.delete(
        projectPath(projectId, `/artefacts/${encodeURIComponent(artefactId)}`),
        payload,
      ),
    artefactAction: (projectId, artefactId, action, payload) =>
      client.post(
        projectPath(projectId, `/artefacts/${encodeURIComponent(artefactId)}/${action}`),
        payload,
      ),
    artefactRevisions: (projectId, artefactId) =>
      client.get(projectPath(projectId, `/artefacts/${encodeURIComponent(artefactId)}/revisions`)),

    relationships: (projectId) => client.get(projectPath(projectId, "/relationships")),
    createRelationship: (projectId, payload) =>
      client.post(projectPath(projectId, "/relationships"), payload),
    updateRelationship: (projectId, relationshipId, payload) =>
      client.put(
        projectPath(projectId, `/relationships/${encodeURIComponent(relationshipId)}`),
        payload,
      ),
    deleteRelationship: (projectId, relationshipId, payload) =>
      client.delete(
        projectPath(projectId, `/relationships/${encodeURIComponent(relationshipId)}`),
        payload,
      ),

    imports: (projectId) => client.get(projectPath(projectId, "/imports")),
    importRun: (projectId, importId) =>
      client.get(projectPath(projectId, `/imports/${encodeURIComponent(importId)}`)),
    startImport: (projectId, payload) =>
      client.post(projectPath(projectId, "/imports/sphinx"), payload),
    importDecisions: (projectId, importId, decisions) =>
      client.post(
        projectPath(projectId, `/imports/${encodeURIComponent(importId)}/decisions`),
        { decisions },
      ),
    cancelImport: (projectId, importId) =>
      client.post(projectPath(projectId, `/imports/${encodeURIComponent(importId)}/cancel`), {}),

    validationStatus: (projectId) =>
      client.get(projectPath(projectId, "/validation/status")),
    validationIssues: (projectId) =>
      client.get(projectPath(projectId, "/validation/issues")),
    runValidation: (projectId, payload = { type: "project", mode: "baseline" }) =>
      client.post(projectPath(projectId, "/validation/run"), payload),
    validationIssueAction: (projectId, issueId, action, payload = {}) =>
      client.post(
        projectPath(
          projectId,
          `/validation/issues/${encodeURIComponent(issueId)}/${action}`,
        ),
        payload,
      ),

    trace: (projectId, artefactId, direction = "") =>
      client.get(
        projectPath(
          projectId,
          `/trace/${encodeURIComponent(artefactId)}${direction ? `/${direction}` : ""}`,
        ),
      ),
    traceabilityMatrix: (projectId) =>
      client.get(projectPath(projectId, "/traceability-matrix")),
    runImpact: (projectId, artefactId) =>
      client.post(projectPath(projectId, "/impact"), { artefact_id: artefactId }),
    suspects: (projectId) => client.get(projectPath(projectId, "/suspect-states")),
    clearSuspect: (projectId, suspectId, payload) =>
      client.post(
        projectPath(projectId, `/suspect-states/${encodeURIComponent(suspectId)}/clear`),
        payload,
      ),

    baselines: (projectId) => client.get(projectPath(projectId, "/baselines")),
    createBaseline: (projectId, payload) =>
      client.post(projectPath(projectId, "/baselines"), payload),
    baselineAction: (projectId, baselineId, action, payload = {}) =>
      client.post(
        projectPath(projectId, `/baselines/${encodeURIComponent(baselineId)}/${action}`),
        payload,
      ),
    runReleaseGate: (projectId, baselineId) =>
      client.post(projectPath(projectId, "/release-gate/run"), { baseline_id: baselineId }),
    latestGate: (projectId, baselineId) =>
      client.get(
        projectPath(
          projectId,
          `/baselines/${encodeURIComponent(baselineId)}/release-gate/results/latest`,
        ),
      ),
    publishRepositoryApproval: (projectId, baselineId, detailsUrl = null) =>
      client.post(
        projectPath(
          projectId,
          `/baselines/${encodeURIComponent(baselineId)}/repository-approvals`,
        ),
        { baseline_id: baselineId, details_url: detailsUrl || null },
      ),

    reports: (projectId) => client.get(projectPath(projectId, "/reports")),
    report: (projectId, reportId) =>
      client.get(projectPath(projectId, `/reports/${encodeURIComponent(reportId)}`)),
    generateReport: (projectId, payload) =>
      client.post(projectPath(projectId, "/reports"), payload),
    deleteReport: (projectId, reportId) =>
      client.delete(projectPath(projectId, `/reports/${encodeURIComponent(reportId)}`)),

    jobs: (projectId) => client.get(projectPath(projectId, "/jobs")),
    job: (jobId) => client.get(`/jobs/${encodeURIComponent(jobId)}`),
    cancelJob: (jobId) => client.post(`/jobs/${encodeURIComponent(jobId)}/cancel`, {}),

    connectors: (projectId) => client.get(projectPath(projectId, "/repo-connectors")),
    createConnector: (projectId, payload) =>
      client.post(projectPath(projectId, "/repo-connectors"), payload),
    connectorAction: (projectId, connectorId, action, payload = {}) =>
      client.post(
        projectPath(
          projectId,
          `/repo-connectors/${encodeURIComponent(connectorId)}/${action}`,
        ),
        payload,
      ),
    deleteConnector: (projectId, connectorId) =>
      client.delete(
        projectPath(projectId, `/repo-connectors/${encodeURIComponent(connectorId)}`),
      ),
    auditEvents: (projectId) => client.get(projectPath(projectId, "/audit-events")),
  };
}
