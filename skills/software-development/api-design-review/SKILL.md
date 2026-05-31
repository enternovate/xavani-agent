---
name: api-design-review
description: Review API designs for consistency, usability, and correctness before implementation.
categories:
  - software-development
platforms:
  - all
tags:
  - api
  - design
  - review
condition: Before implementing a new API or making breaking changes to an existing one.
---

# API Design Review

> "A good API is one where the right thing is the easy thing."

## When to use

- Designing a new REST/GraphQL/gRPC API.
- Reviewing API changes before merge.
- Evaluating API consistency across services.

## Prerequisites

- API spec (OpenAPI, GraphQL schema, or proto file).
- Understanding of the consumers.

## Steps

### 1. Resource naming (REST)

- Nouns, not verbs: `/users` not `/getUsers`.
- Plural for collections: `/users`, `/orders`.
- Nested for relationships: `/users/123/orders`.
- Consistent casing: kebab-case or snake_case, pick one.

### 2. HTTP methods

- `GET` — read (idempotent, cacheable).
- `POST` — create.
- `PUT` — full replace.
- `PATCH` — partial update.
- `DELETE` — remove.

### 3. Status codes

- `200` — success.
- `201` — created.
- `400` — client error (bad request).
- `401` — unauthenticated.
- `403` — unauthorized.
- `404` — not found.
- `409` — conflict.
- `500` — server error.

### 4. Error responses

Consistent error format:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Email is required",
    "details": [{"field": "email", "issue": "missing"}]
  }
}
```

### 5. Pagination

Use cursor-based or offset-based consistently:
```
GET /users?limit=20&cursor=abc123
```

### 6. Versioning

- URL path: `/v1/users` (most explicit).
- Header: `Accept: application/vnd.api+json;version=1`.
- Be consistent across all endpoints.

### 7. Authentication

- Bearer tokens in `Authorization` header.
- API keys in header, never in URL.
- Rate limiting with clear headers.

## Verification

- All endpoints follow naming conventions.
- Error responses are consistent.
- Pagination is implemented.
- Authentication is documented.
