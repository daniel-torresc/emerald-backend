
### Performance Requirements

**MANDATORY: Meet these performance targets**
- API response time: < 200ms (p95)
- Page load time: < 2 seconds
- Time to interactive: < 3 seconds
- Database query time: < 100ms (p95)
- Implement caching for expensive operations
- Optimize database queries (use EXPLAIN)
- Use database indexes appropriately
- Implement pagination for large datasets

### Monitoring

**MANDATORY: Implement monitoring**
- Application health checks
- API endpoint metrics (response time, error rate)
- Database performance metrics
- Server resource usage (CPU, memory, disk)
- Error tracking and alerting
- User session tracking
- Business metrics tracking

### Logging for Monitoring

**MANDATORY: Log these events**
- All API requests (method, path, status, duration)
- Authentication events (login, logout, failed attempts)
- Authorization failures
- Database query performance (slow queries)
- External API calls
- Business-critical events
- Errors and exceptions
- System resource warnings

### Alerting

**MANDATORY: Set up alerts for**
- Error rate exceeds threshold
- Response time exceeds threshold
- Service downtime
- Database connection failures
- Disk space low
- High memory/CPU usage
- Security events (multiple failed logins)
- Payment failures
