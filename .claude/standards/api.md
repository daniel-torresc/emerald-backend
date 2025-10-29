### RESTful Conventions

**MANDATORY: Follow REST principles strictly**

#### Resource Naming
- Use plural nouns for resources: `/users`, `/products`, `/orders`
- Use lowercase letters only
- Use hyphens for multi-word resources: `/order-items`
- NEVER use verbs in endpoint names
- Use nested resources for relationships: `/users/{id}/posts`

#### HTTP Methods
- `GET`: Retrieve resource(s) - MUST be idempotent and safe
- `POST`: Create new resource - Returns 201 Created
- `PUT`: Replace entire resource - MUST be idempotent
- `PATCH`: Partially update resource - MUST be idempotent
- `DELETE`: Remove resource - Returns 204 No Content

#### URL Structure
```
GET    /api/v1/resources          # List resources (paginated)
POST   /api/v1/resources          # Create resource
GET    /api/v1/resources/{id}     # Get single resource
PUT    /api/v1/resources/{id}     # Replace resource
PATCH  /api/v1/resources/{id}     # Update resource
DELETE /api/v1/resources/{id}     # Delete resource
```

### Response Standards

**MANDATORY: Use consistent response format**

#### Success Response Structure
```json
{
  "data": { /* single object or array */ },
  "meta": {
    "timestamp": "ISO 8601 datetime",
    "request_id": "unique-request-id"
  }
}
```

#### Paginated List Response
```json
{
  "data": [ /* array of resources */ ],
  "meta": {
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5,
    "timestamp": "ISO 8601 datetime"
  }
}
```

#### Error Response Structure
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": [ /* array of specific errors */ ]
  },
  "meta": {
    "timestamp": "ISO 8601 datetime",
    "request_id": "unique-request-id"
  }
}
```

### Status Codes

**MANDATORY: Use appropriate HTTP status codes**
- `200 OK`: Successful GET, PUT, PATCH
- `201 Created`: Successful POST, include Location header
- `204 No Content`: Successful DELETE
- `400 Bad Request`: Client errors, validation failures
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Authenticated but insufficient permissions
- `404 Not Found`: Resource doesn't exist
- `409 Conflict`: Resource conflict (duplicate, constraint violation)
- `422 Unprocessable Entity`: Semantic validation errors
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server errors (should be rare)
- `503 Service Unavailable`: Temporary unavailability

### Versioning

**MANDATORY: Use URL versioning**
- Include version in URL path: `/api/v1/`
- Start with v1
- Increment major version for breaking changes
- Maintain previous versions for 6 months minimum
- Document deprecation timeline
- Use API version in all endpoints

### Pagination

**MANDATORY: Implement pagination for ALL list endpoints**
- Use query parameters: `?page=1&page_size=20`
- Default page size: 20 items
- Maximum page size: 100 items
- Include pagination metadata in response
- Return empty array (not error) for pages beyond last page

### Filtering and Sorting

**MANDATORY: Support filtering and sorting**
- Use query parameters for filters: `?status=active&category=electronics`
- Use `sort_by` and `order` parameters: `?sort_by=created_at&order=desc`
- Document all available filters and sort options
- Validate filter values
- Return 400 for invalid filter parameters
