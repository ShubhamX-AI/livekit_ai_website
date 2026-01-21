# Backend Modular Architecture Blueprint

This document is the blueprint for converting the LiveKit AI backend into a modular, API-driven platform. It describes the target architecture, data model, and execution flow at a high level so future work can follow a single, consistent plan.

## Goals

- API-driven configuration for agents, prompts, tools, and runtime settings.
- All configuration stored in MongoDB with versioning and audit history.
- Multi-tenant platform hosted on a single LiveKit server instance.
- Safe runtime reconfiguration without code changes or redeploys.
- Production-ready security model suitable for public API access.
- Endpoint list is defined in `backend/ARCHITECTURE-APIS.md`.
- File upload and knowledge base support are defined in this document.

## Production-Ready Auth Model (Recommended)

- Tenant API keys for server-to-server calls.
- Signed JWTs for end-user calls (short-lived, scoped to tenant/user/session).
- AWS-backed identity provider (Cognito or IAM auth integration) to issue/rotate keys.
- Request signing or HMAC for internal system-to-system calls.
- All requests include tenant_id and user_id claims for isolation and audit.

## Current State Summary

- Agent types are hard-coded in `backend/agent_session.py`.
- Agent prompts and tool bindings are defined inside agent classes.
- Inbound number routing uses a JSON file (`backend/inbound/config_manager.py`).
- The FastAPI layer (`backend/server.py`) exposes limited endpoints.

## Target Architecture Overview

- API Gateway (FastAPI): entry point for all client apps.
- Config Service: MongoDB-backed storage for all registry data.
- Agent Registry: manages agent definitions and versions.
- Prompt Registry: manages prompt templates and versions.
- Tool Registry: manages tool schemas and bindings.
- Runtime Config Service: merges model, TTS, voice, audio, and behavior config.
- Session Orchestrator: resolves configs and starts LiveKit sessions.
- Call Dispatch Service: outbound calls and inbound routing.
- Realtime Runtime: LiveKit AgentServer executes sessions using resolved config.

## Core MongoDB Collections

- tenants
  - name, api_keys, status, created_at
- users
  - tenant_id, external_id, display_name
- agents
  - tenant_id, agent_id, name, status, version, tags
- prompts
  - tenant_id, prompt_id, version, template, metadata
- tools
  - tenant_id, tool_id, schema, handler_ref, version
- agent_bindings
  - agent_id, prompt_version, tool_versions, runtime_config_version
- runtime_configs
  - llm, tts, voice, background_audio, welcome_message, safety
- sessions
  - tenant_id, session_id, agent_id, resolved_versions, status
- calls
  - tenant_id, call_id, session_id, direction, sip_metadata
- inbound_mappings
  - tenant_id, phone_number, agent_id, version
- audit_events
  - actor_id, action, entity, old_value, new_value, timestamp
- files
  - tenant_id, file_id, name, mime_type, size_bytes, storage_key, checksum, status
- file_chunks
  - tenant_id, file_id, chunk_id, text_ref, embedding_ref, status
- search_indexes
  - tenant_id, index_id, backend, status, metadata

## Runtime Flow (High Level)

1) Client app creates tenant or uses existing tenant.
2) Client creates an agent and assigns prompt/tool/runtime configs.
3) Client requests a session or dispatches a call.
4) Session Orchestrator resolves the latest pinned versions.
5) LiveKit AgentSession starts using resolved config.
6) Events and metrics are stored in audit_events.

## Modular Services and Responsibilities

- api_gateway
  - Authentication, authorization, validation.
- agent_registry
  - CRUD for agent metadata and versioning.
- prompt_registry
  - CRUD for prompt templates and versions.
- tool_registry
  - CRUD for tool schemas and bindings.
- runtime_config
  - LLM, TTS, background audio, welcome message, safety and policies.
- session_orchestrator
  - Resolve config, start/stop LiveKit sessions, track status.
- call_dispatch
  - Outbound calls, inbound mapping, SIP metadata generation.
- observability
  - Logging, audit trail, metrics, tracing.
- file_storage
  - Presigned uploads, metadata tracking, lifecycle rules.
- ingestion_pipeline
  - Parse, chunk, embed, and index documents asynchronously.
- vector_search
  - Query vector store and return ranked chunks.

## Codebase Refactor Targets

- `backend/server.py`
  - Split into route modules under `backend/routes/*`.
- `backend/agent_session.py`
  - Replace static agent map with dynamic config resolver.
- `backend/inbound/config_manager.py`
  - Replace JSON file with Mongo repository layer.
- Add `backend/db/*`
  - Mongo connection and repositories for each collection.
- Add `backend/services/*`
  - Business logic for registries and orchestration.

## Versioning and Safety

- All configs are immutable once published.
- Agent bindings point to specific prompt/tool/runtime versions.
- Rollbacks create a new binding with prior versions.
- Soft-delete and audit for all registry entities.
- Files are immutable once ingested; replacing a file creates a new version.

## Multi-Tenant Behavior

- Single LiveKit server instance supports multiple tenant apps.
- Tenant isolation enforced at data layer and auth layer.
- Tenant-scoped API keys and JWTs used for all access.
- User-level IDs returned for downstream apps to reference.
- Tenant-scoped buckets, prefixes, and vector namespaces.

## Migration Plan (Phased)

1) Create Mongo DB layer and migrate inbound mapping.
2) Implement registries for prompts, tools, agents.
3) Introduce runtime_config resolution and bindings.
4) Update session orchestration to use resolved configs.
5) Add audit logging and tenant scoping.
6) Add file storage, ingestion pipeline, and vector search.

## Non-Goals (For Now)

- No explicit API payloads in this document.
- No frontend or UI changes described here.

## File Upload and Knowledge Base (Production Design)

### Storage

- Raw files are stored in S3 using presigned uploads.
- MongoDB stores file metadata only (location, checksum, status, ownership).
- Use S3 lifecycle policies for retention and cleanup.

### Vector Search Backends

- Preferred options: Chroma or MongoDB Atlas Vector Search.
- Chroma is recommended for quick iteration; Atlas Vector Search is simpler ops if already on MongoDB Atlas.
- Embeddings are not stored in plain Mongo collections unless Atlas Vector Search is used.

### Ingestion Pipeline

1) Upload file to S3 using presigned URL.
2) Create file metadata record in MongoDB.
3) Async worker parses file, chunks text, and generates embeddings.
4) Store chunk metadata in MongoDB and embeddings in the chosen vector backend.
5) Mark file as ready for retrieval.

### Supported File Types (Initial)

- PDF
- TXT
- DOC/DOCX

### Agent Retrieval Flow

- Agent tool calls vector search with tenant scope and optional agent scope.
- Vector search returns ranked chunks; LLM answers with citations if needed.
