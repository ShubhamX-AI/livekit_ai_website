# Architecture API Endpoints

This document lists the explicit API endpoints implied by the modular architecture. It is intentionally high level and does not include payload schemas or request/response examples.

## Auth and Tenant

- POST /api/tenants
- GET /api/tenants/{tenant_id}
- PATCH /api/tenants/{tenant_id}
- POST /api/tenants/{tenant_id}/keys
- GET /api/tenants/{tenant_id}/keys
- DELETE /api/tenants/{tenant_id}/keys/{key_id}

## Users

- POST /api/tenants/{tenant_id}/users
- GET /api/tenants/{tenant_id}/users
- GET /api/tenants/{tenant_id}/users/{user_id}
- PATCH /api/tenants/{tenant_id}/users/{user_id}
- DELETE /api/tenants/{tenant_id}/users/{user_id}

## Agents

- POST /api/tenants/{tenant_id}/agents
- GET /api/tenants/{tenant_id}/agents
- GET /api/tenants/{tenant_id}/agents/{agent_id}
- PATCH /api/tenants/{tenant_id}/agents/{agent_id}
- DELETE /api/tenants/{tenant_id}/agents/{agent_id}

## Prompts

- POST /api/tenants/{tenant_id}/prompts
- GET /api/tenants/{tenant_id}/prompts
- GET /api/tenants/{tenant_id}/prompts/{prompt_id}
- POST /api/tenants/{tenant_id}/prompts/{prompt_id}/versions
- GET /api/tenants/{tenant_id}/prompts/{prompt_id}/versions
- GET /api/tenants/{tenant_id}/prompts/{prompt_id}/versions/{version_id}
- DELETE /api/tenants/{tenant_id}/prompts/{prompt_id}/versions/{version_id}

## Tools

- POST /api/tenants/{tenant_id}/tools
- GET /api/tenants/{tenant_id}/tools
- GET /api/tenants/{tenant_id}/tools/{tool_id}
- POST /api/tenants/{tenant_id}/tools/{tool_id}/versions
- GET /api/tenants/{tenant_id}/tools/{tool_id}/versions
- GET /api/tenants/{tenant_id}/tools/{tool_id}/versions/{version_id}
- DELETE /api/tenants/{tenant_id}/tools/{tool_id}/versions/{version_id}

## Runtime Configs

- POST /api/tenants/{tenant_id}/runtime-configs
- GET /api/tenants/{tenant_id}/runtime-configs
- GET /api/tenants/{tenant_id}/runtime-configs/{config_id}
- POST /api/tenants/{tenant_id}/runtime-configs/{config_id}/versions
- GET /api/tenants/{tenant_id}/runtime-configs/{config_id}/versions
- GET /api/tenants/{tenant_id}/runtime-configs/{config_id}/versions/{version_id}
- DELETE /api/tenants/{tenant_id}/runtime-configs/{config_id}/versions/{version_id}

## Agent Bindings

- POST /api/tenants/{tenant_id}/agents/{agent_id}/bindings
- GET /api/tenants/{tenant_id}/agents/{agent_id}/bindings
- GET /api/tenants/{tenant_id}/agents/{agent_id}/bindings/{binding_id}
- POST /api/tenants/{tenant_id}/agents/{agent_id}/bindings/{binding_id}/activate
- DELETE /api/tenants/{tenant_id}/agents/{agent_id}/bindings/{binding_id}

## Sessions

- POST /api/tenants/{tenant_id}/sessions
- GET /api/tenants/{tenant_id}/sessions
- GET /api/tenants/{tenant_id}/sessions/{session_id}
- POST /api/tenants/{tenant_id}/sessions/{session_id}/start
- POST /api/tenants/{tenant_id}/sessions/{session_id}/stop
- POST /api/tenants/{tenant_id}/sessions/{session_id}/attach
- DELETE /api/tenants/{tenant_id}/sessions/{session_id}

## LiveKit Tokens

- POST /api/tenants/{tenant_id}/tokens

## Calls (Dispatch)

- POST /api/tenants/{tenant_id}/calls
- GET /api/tenants/{tenant_id}/calls
- GET /api/tenants/{tenant_id}/calls/{call_id}
- POST /api/tenants/{tenant_id}/calls/{call_id}/start
- POST /api/tenants/{tenant_id}/calls/{call_id}/stop

## Inbound Routing

- POST /api/tenants/{tenant_id}/inbound-mappings
- GET /api/tenants/{tenant_id}/inbound-mappings
- GET /api/tenants/{tenant_id}/inbound-mappings/{mapping_id}
- PATCH /api/tenants/{tenant_id}/inbound-mappings/{mapping_id}
- DELETE /api/tenants/{tenant_id}/inbound-mappings/{mapping_id}

## Files and Knowledge Base

- POST /api/tenants/{tenant_id}/files
- GET /api/tenants/{tenant_id}/files
- GET /api/tenants/{tenant_id}/files/{file_id}
- DELETE /api/tenants/{tenant_id}/files/{file_id}
- POST /api/tenants/{tenant_id}/files/{file_id}/ingest
- GET /api/tenants/{tenant_id}/files/{file_id}/status
- POST /api/tenants/{tenant_id}/agents/{agent_id}/files
- GET /api/tenants/{tenant_id}/agents/{agent_id}/files

## Vector Search

- POST /api/tenants/{tenant_id}/search

## Audit and Metrics

- GET /api/tenants/{tenant_id}/audit-events
- GET /api/tenants/{tenant_id}/metrics

## Health

- GET /health
