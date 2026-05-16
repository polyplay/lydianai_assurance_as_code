# Logical Database Schema

## 1. Purpose

This document defines the logical relational-plus-graph-query database schema.

The schema is designed for canonical artefacts, relationship graph traversal, automatic versioning, baselines, Automotive SPICE PAM 4.0 CL3 process evidence, ISO 26262 software-system evidence, ISO 29119 test evidence, UNECE R155 cybersecurity evidence references, and UNECE R156 software update evidence references.

## 2. Design Principles

- The relational database is authoritative.
- Graph behavior is implemented with typed relationship tables and indexes.
- Artefacts are generic at the base level and typed through `artefact_type` plus JSON payload.
- Historical revisions are immutable.
- Deletion is soft deletion by lifecycle state or timestamp.
- Every table that belongs to project data is project-scoped.

## 3. Identity And Access Tables

### users

- `user_id` PK
- `username` unique
- `display_name`
- `email`
- `status`
- `password_hash`
- `password_updated_at`
- `last_login_at` nullable
- `created_at`
- `updated_at`

### roles

- `role_id` PK
- `role_name` unique: `admin`, `project_lead`, `quality_engineer`, `user`

### project_memberships

- `project_id` FK
- `user_id` FK
- `role_id` FK
- `created_at`

Unique: `project_id`, `user_id`, `role_id`

## 4. Project And Profile Tables

### projects

- `project_id` PK
- `project_key` unique
- `name`
- `description`
- `active_profile_id` FK
- `status`
- `created_at`
- `updated_at`

### project_configurations

- `project_config_id` PK
- `project_id` FK
- `version_update_mode`
- `sphinx_source_root`
- `baseline_policy_json`
- `validation_policy_json`
- `reporting_policy_json`
- `created_at`
- `updated_at`

### assurance_profiles

- `profile_id` PK
- `project_id` FK nullable for global profiles
- `name`
- `classification`
- `inherits_from_profile_id` FK nullable
- `profile_payload_json`
- `status`
- `created_at`
- `updated_at`

### tailoring_decisions

- `tailoring_decision_id` PK
- `project_id` FK
- `scope_type`
- `scope_id`
- `target_kind`
- `target_id`
- `previous_applicability`
- `tailored_applicability`
- `rationale`
- `evidence_refs_json`
- `requested_by` FK users
- `approved_by` FK users
- `approved_at`
- `status`

## 5. Artefact Tables

### artefacts

- `artefact_id` PK
- `project_id` FK
- `artefact_type`
- `title`
- `status`
- `owner_user_id` FK nullable
- `current_revision_id` FK nullable
- `source_kind`
- `source_tool`
- `source_object_id`
- `source_document`
- `current_fingerprint`
- `standards_refs_json`
- `work_product_kind`
- `review_expectation`
- `independence_expectation`
- `created_at`
- `updated_at`
- `deleted_at` nullable

Indexes:

- `project_id`, `artefact_type`
- `project_id`, `status`
- `project_id`, `source_document`, `source_object_id`

### artefact_revisions

- `artefact_revision_id` PK
- `artefact_id` FK
- `project_id` FK
- `revision_number`
- `payload_json`
- `metadata_json`
- `content_fingerprint`
- `change_reason`
- `changed_by` FK users nullable
- `changed_at`
- `import_run_id` FK nullable
- `change_set_id` FK nullable
- `audit_event_id` FK nullable

Unique: `artefact_id`, `revision_number`

## 6. Relationship Tables

### relationships

- `relationship_id` PK
- `project_id` FK
- `relationship_type`
- `source_artefact_id` FK
- `target_artefact_id` FK
- `status`
- `current_revision_id` FK nullable
- `created_at`
- `updated_at`
- `deleted_at` nullable

Indexes:

- `project_id`, `source_artefact_id`
- `project_id`, `target_artefact_id`
- `project_id`, `relationship_type`
- `project_id`, `source_artefact_id`, `relationship_type`
- `project_id`, `target_artefact_id`, `relationship_type`

### relationship_revisions

- `relationship_revision_id` PK
- `relationship_id` FK
- `project_id` FK
- `revision_number`
- `payload_json`
- `changed_by` FK users nullable
- `changed_at`
- `import_run_id` FK nullable
- `change_set_id` FK nullable
- `audit_event_id` FK nullable

Unique: `relationship_id`, `revision_number`

## 7. Import Tables

### import_runs

- `import_run_id` PK
- `project_id` FK
- `source_tool`
- `source_root`
- `state`
- `version_update_mode`
- `submitted_by` FK users nullable
- `submitted_at`
- `completed_at`
- `summary_json`
- `diagnostics_json`

### import_run_items

- `import_run_item_id` PK
- `import_run_id` FK
- `project_id` FK
- `source_object_id`
- `source_document`
- `artefact_type`
- `artefact_id` FK nullable
- `detected_change_type`
- `current_revision_id` FK nullable
- `previous_fingerprint` nullable
- `proposed_fingerprint` nullable
- `proposed_payload_json`
- `new_revision_id` FK nullable
- `decision_status`
- `decision_by` FK users nullable
- `decision_at`

## 8. Baseline Tables

### baselines

- `baseline_id` PK
- `project_id` FK
- `name`
- `description`
- `state`
- `created_by` FK users
- `created_at`
- `approved_by` FK users nullable
- `approved_at`
- `released_by` FK users nullable
- `released_at`
- `profile_id` FK
- `release_gate_status`
- `eligibility_result_json`
- `summary_json`

### baseline_artefact_revisions

- `baseline_id` FK
- `artefact_id` FK
- `artefact_revision_id` FK
- `artefact_type`

Primary key: `baseline_id`, `artefact_id`

### baseline_relationship_revisions

- `baseline_id` FK
- `relationship_id` FK
- `relationship_revision_id` FK
- `relationship_type`

Primary key: `baseline_id`, `relationship_id`

### release_gate_results

- `release_gate_result_id` PK
- `project_id` FK
- `baseline_id` FK
- `evaluation_number`
- `triggered_by` FK users
- `job_id` FK nullable
- `status`
- `result`
- `started_at`
- `completed_at`
- `evaluated_rules_count`
- `passed_rules_count`
- `blocking_issues_json`
- `warning_issues_json`
- `mandatory_artefact_gaps_json`
- `open_suspect_states_json`

Unique: `baseline_id`, `evaluation_number`

## 9. Validation And Rule Tables

### validation_rules

- `rule_id` PK
- `title`
- `source_basis_json`
- `standards_refs_json`
- `default_severity`
- `rule_payload_json`
- `status`

### validation_runs

- `validation_run_id` PK
- `project_id` FK
- `baseline_id` FK nullable
- `scope_json`
- `state`
- `trigger_event_id` FK nullable
- `started_at`
- `completed_at`
- `summary_json`

### validation_issues

- `validation_issue_id` PK
- `project_id` FK
- `validation_run_id` FK
- `baseline_id` FK nullable
- `rule_id` FK
- `severity`
- `status`
- `message`
- `affected_artefact_ids_json`
- `affected_relationship_ids_json`
- `remediation_hint`
- `created_at`
- `resolved_at`
- `suppressed_by` FK users nullable
- `suppression_reason`

## 10. Impact And Suspect Tables

### impact_analysis_runs

- `impact_analysis_id` PK
- `project_id` FK
- `state`
- `trigger_event_id` FK nullable
- `requested_by` FK users nullable
- `scope_json`
- `started_at`
- `completed_at`
- `summary_json`

### impact_analysis_items

- `impact_item_id` PK
- `impact_analysis_id` FK
- `impacted_artefact_id` FK nullable
- `impacted_relationship_id` FK nullable
- `impact_type`
- `reason_path_json`
- `retest_recommendation_json`

### suspect_states

- `suspect_state_id` PK
- `project_id` FK
- `artefact_id` FK
- `trigger_event_id` FK
- `reason`
- `status`
- `created_at`
- `cleared_by` FK users nullable
- `cleared_at`
- `clearance_reason`

## 11. Test, Evidence, Report Tables

### test_result_records

- `test_result_record_id` PK
- `project_id` FK
- `artefact_id` FK
- `test_specification_id` FK nullable
- `baseline_id` FK nullable
- `build_ref`
- `environment_ref`
- `verdict`
- `executed_at`
- `payload_json`

### evidence_references

- `evidence_id` PK
- `project_id` FK
- `evidence_type`
- `uri`
- `checksum`
- `metadata_json`
- `created_by` FK users nullable
- `created_at`

### generated_reports

- `report_id` PK
- `project_id` FK
- `baseline_id` FK nullable
- `report_type`
- `state`
- `format`
- `uri`
- `generated_by` FK users nullable
- `generated_at`
- `payload_ref_json`

## 12. Jobs And Audit Tables

### jobs

- `job_id` PK
- `project_id` FK nullable
- `job_type`
- `state`
- `submitted_by` FK users nullable
- `submitted_at`
- `started_at`
- `completed_at`
- `progress_percent`
- `result_ref_json`
- `error_json`

### audit_events

- `audit_event_id` PK
- `project_id` FK nullable
- `event_type`
- `actor_user_id` FK nullable
- `actor_type`
- `correlation_id`
- `causation_id`
- `affected_artefact_ids_json`
- `affected_relationship_ids_json`
- `payload_json`
- `created_at`

## 12.1 Standards Traceability Tables

### standards_references

- `standards_reference_id` PK
- `standard`
- `edition`
- `part_or_process`
- `clause_or_process_id`
- `title`
- `reference_type`
- `source_access`
- `review_status`
- `created_at`
- `updated_at`

### artefact_standard_mappings

- `artefact_type`
- `standards_reference_id` FK
- `required_content_json`
- `review_expectation`
- `independence_expectation`
- `verification_method_expectation`

Primary key: `artefact_type`, `standards_reference_id`

### rule_standard_mappings

- `rule_id` FK
- `standards_reference_id` FK
- `mapping_rationale`
- `review_status`

Primary key: `rule_id`, `standards_reference_id`

## 13. Repository Integration Tables

### connector_secrets

- `connector_secret_id` PK
- `project_id` FK
- `secret_type`
- `encrypted_payload`
- `key_id`
- `status`
- `created_by`
- `last_rotated_at`
- `last_used_at`

### repository_connectors

- `repository_connector_id` PK
- `project_id` FK
- `provider`
- `name`
- `owner`
- `repository`
- `repository_url`
- `default_branch`
- `auth_mode`
- `app_id`
- `installation_id`
- `access_token_secret_id` FK
- `private_key_secret_id` FK
- `webhook_secret_id` FK
- `scan_policy_json`
- `mapping_policy_json`
- `status`
- `last_scan_run_id`
- `last_revision_id`
- `created_by`

Unique key: `project_id`, `provider`, `owner`, `repository`

### repository_scan_runs

- `repository_scan_run_id` PK
- `repository_connector_id` FK
- `project_id` FK
- `job_id` FK
- `trigger`
- `state`
- `requested_by`
- `commit_sha`
- `branch`
- `pull_request_id`
- `started_at`
- `completed_at`
- `summary_json`
- `diagnostics_json`

### repository_revisions

- `repository_revision_id` PK
- `repository_connector_id` FK
- `project_id` FK
- `scan_run_id`
- `commit_sha`
- `branch`
- `tag`
- `commit_timestamp`
- `author_name`
- `author_email`
- `message`
- `tree_sha`
- `mapping_fingerprint`
- `status`
- `metadata_json`

Unique key: `repository_connector_id`, `commit_sha`

### repository_webhook_deliveries

- `repository_webhook_delivery_id` PK
- `repository_connector_id` FK
- `project_id` FK
- `delivery_id`
- `event_type`
- `action`
- `signature_valid`
- `state`
- `payload_hash`
- `received_at`
- `processed_at`
- `diagnostics_json`

Unique key: `repository_connector_id`, `delivery_id`

### repository_check_runs

- `repository_check_run_id` PK
- `repository_connector_id` FK
- `project_id` FK
- `validation_run_id` FK
- `release_gate_result_id` FK
- `baseline_id` FK
- `commit_sha`
- `github_check_run_id`
- `check_type`
- `status`
- `conclusion`
- `details_url`
- `summary`
- `requested_by`
- `error_json`

### baseline_repository_revisions

- `baseline_id` FK
- `repository_connector_id` FK
- `repository_revision_id` FK
- `commit_sha`

Primary key: `baseline_id`, `repository_connector_id`

## 14. Logical Graph Query Model

Forward traversal uses:

```sql
SELECT * FROM relationships
WHERE project_id = :project_id
  AND source_artefact_id = :artefact_id
  AND deleted_at IS NULL;
```

Backward traversal uses:

```sql
SELECT * FROM relationships
WHERE project_id = :project_id
  AND target_artefact_id = :artefact_id
  AND deleted_at IS NULL;
```

Transitive traversal shall be implemented in the graph service using relationship indexes or recursive SQL where supported.

## 15. Standards Review Gap

The schema supports ISO 26262, Automotive SPICE PAM 4.0 CL3, ISO 29119, UNECE R155, and UNECE R156 evidence patterns at resource level. Clause-exact table coverage shall be validated later against licensed standards and project process definitions.
