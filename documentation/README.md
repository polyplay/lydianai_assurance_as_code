# LydianAI Assurance-as-Code Documentation

Existing Redis deployments: follow the [Valkey migration guide](valkey_migration.md)
before upgrading to the Valkey broker.

This folder contains operational and user-facing documentation.

The technical requirements and implementation specifications remain in `docs/`. This folder is for installers, administrators, project leads, quality engineers, and end users.

## Documents

- [Backend Installer Guide](backend_installer_guide.md)
- [Administrator Manual](admin_manual.md)
- [User Manual](user_manual.md)

## Licenses

The application's own code uses [Apache-2.0](../LICENSE). The default Valkey
server uses [BSD-3-Clause](../LICENSES/Valkey-8.1.10.txt). See
[Third-Party License Notices](../THIRD_PARTY_NOTICES.md) for the retained
attributions and other dependency license references, and the
[dependency audit](../docs/dependency_license_audit.md) for dated findings.

## Roles

The application uses these main roles:

- **Admin**: manages users, roles, project setup, repository connectors, and system configuration.
- **Project Lead**: manages project workflow, imports, scans, baselines, and project-level decisions.
- **Quality Engineer**: runs release checks, reviews evidence, releases baselines, and publishes repository approvals.
- **User**: creates and reviews evidence, artefacts, relationships, traceability, and reports within assigned projects.

