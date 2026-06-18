# Document Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build document management APIs with MinIO-backed upload, download, list, detail, update, and delete behavior aligned with the existing knowledge base API style.

**Architecture:** Reuse the current FastAPI layering pattern of route, schema, service, and model. Add a focused object storage service for MinIO access, but keep it lazily imported and dependency-friendly so tests can run against an in-memory fake backend without external services.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, httpx/TestClient, SQLite in-memory tests, MinIO Python SDK at runtime

---

### Task 1: Document API Contract

**Files:**
- Modify: `AGENTS.md`
- Modify: `backend/app/schemas/document.py`
- Test: `backend/tests/test_documents_api.py`

- [ ] Define request and response schema shapes for create, update, list, detail, and download metadata.
- [ ] Encode the contract in failing API tests first, including query-based `id`, optional `knowledge_base_id` filter, and unified response wrappers.

### Task 2: Object Storage Integration

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/core/config.py`
- Create: `backend/app/services/object_storage.py`
- Test: `backend/tests/test_documents_api.py`

- [ ] Add MinIO configuration fields and runtime dependency declaration.
- [ ] Implement upload, download, and delete operations behind a small storage abstraction that can be replaced in tests.

### Task 3: Document Service and Routes

**Files:**
- Modify: `backend/app/models/document.py`
- Modify: `backend/app/api/v1/documents.py`
- Create: `backend/app/services/document_service.py`
- Modify: `backend/app/schemas/document.py`
- Test: `backend/tests/test_documents_api.py`

- [ ] Implement service-layer create, list, detail, update, delete, and download lookup behavior.
- [ ] Implement FastAPI routes mirroring the knowledge base style and using multipart upload for create.

### Task 4: Verification and Frontend Usage Notes

**Files:**
- Modify: `AGENTS.md`
- Test: `backend/tests/test_documents_api.py`

- [ ] Run document API tests and startup tests.
- [ ] Summarize the implementation flow and frontend usage guidance after verification.
