# OAuth Token Management Strategy: Token Decoupling

Managing OAuth between our application and third-party services requires a comprehensive strategy, from retry mechanisms to safely re-authenticating users when tokens expire.

## Token Decoupling Approach

The approach implemented is called **Token Decoupling**, which involves issuing our own application tokens (both refresh and access tokens) after successfully receiving the Provider Tokens.

This creates two distinct session layers where our app acts as a "middleman" that must keep its internal session synchronized with the third-party's authorization.

### Benefits

- **Prevents the "Double-Lock Problem"**: Avoids scenarios where a user is logged into your app but can't perform actions because the background connection to the service (e.g., Google, Slack) has expired.
- **Dual-level Authentication**: Handles authentication and authorization at both application and provider levels.

## Lazy Token Refresh Flow

Instead of automatically refreshing tokens on intervals, we only refresh when our application actually needs it. This prevents potential pitfalls like API overhead and rate limiting errors.

### Typical Flow

1. **Frontend Request**: Frontend sends the application Access Token to the required API endpoint
2. **Token Validation**: Validates the token/session and extracts info like `user_id`/`role`
3. **Provider Token Lookup**: Looks up the Provider Access Token in the DB using `user_id` as query key
4. **Expiry Check**: If `now() > expires_at - 5 minutes` (using a buffer), trigger the refresh flow
5. **Token Refresh**: Call the third party's `/token` endpoint using the provider refresh token
6. **Database Update**: Save the new tokens and updated `expires_at`
7. **Complete Request**: Proceed with the original request

### Summary

Use application tokens to manage application endpoints, while provider tokens handle resource server endpoints.

## Potential Problems and Solutions

### Session Disconnects (Synchronization Issues)

A user might directly access the third-party dashboard and remove our application, rendering our stored Provider tokens useless.

**Detection**: Backend receives `401 Unauthorized` or `invalid_grant` errors.

**Solution**:
- Add a `status` column to track token validity
- Set status to "disconnected" when issues detected
- Return error response to client requesting re-login

### Rate Limiting

Third-party services will throttle excessive requests.

**Solution**: Implement Exponential Backoff retry logic:
- On `429 (Too Many Requests)` errors, wait before retrying
- Increase wait time exponentially with each failure

### Third-Party Service Downtime

Don't assume third-party services are always available.

**Solution**: Build defensively with robust error handling:
- Wrap API calls in retry logic
- Show "Sync currently unavailable" messages instead of crashing
- Ensure app functionality during service outages

### Security Concerns

Never store third-party tokens as plain text - database leaks would compromise user accounts.

**Solution**:
- Encrypt `access_token` and `refresh_token` columns using AES-256
- Store encryption keys in environment variables or Secret Manager
- Keep keys completely separate from the database

## Architectural Decision: "Conflict vs. Convergence"

When a user tries to re-login through a third-party service where their `provider_user_id` already exists in our database, returning an "Already Existing" error (409 Conflict) is counterproductive for OAuth flows.

The goal should be **Idempotency** - performing the same operation multiple times produces the same result without side effects.

### Recommended Approach: Idempotent "Upsert" Workflow

Treat login as an Upsert (Update or Insert) operation.

#### Workflow Steps

When the third party redirects back to your URI with an authorization code:

1. **Exchange Code**: Receive `provider_user_id` and new tokens
2. **Database Lookup**: Check database for existing `provider_user_id`
3. **Branching Logic**:
   - **User Not Found**: Create new record (Insert)
   - **User Found**: Update existing record with new tokens (Update)
4. **Issue Session**: Generate fresh Internal App Token for frontend

#### Result

Whether it's the user's 1st or 100th login, the outcome remains consistent: they are logged in with the latest third-party credentials.
