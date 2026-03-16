# Login Processing Flow - Mermaid Diagram

```mermaid
flowchart TD
    A[Start: Raw O365 Audit Log] --> B{Operation contains<br/>'UserLoginFailed' or 'Failed'?}

    B -->|Yes| C[is_success = False]
    B -->|No| D{Check ErrorNumber}

    C --> E[Get LogonError as<br/>failure_reason]
    D --> F{ErrorNumber in<br/>failure_error_codes?}

    F -->|Yes| G[is_success = False<br/>failure_reason = LogonError<br/>or 'Error: {code}']
    F -->|No| H{ErrorNumber = 50140<br/>'Strong Auth Required'?}

    H -->|Yes| I[is_success = True<br/>Not a failure]
    H -->|No| J{Check LogonError}

    G --> J
    E --> J
    I --> J

    J --> K{LogonError present?}

    K -->|Yes| L[is_success = False<br/>failure_reason = LogonError]
    K -->|No| M{Check ExtendedProperties}

    L --> N{Check Status.ErrorCode}
    M --> O{ResultStatusDetail<br/>!= 'Success'?}

    O -->|Yes| P[failure_reason = ResultStatusDetail]
    O -->|No| Q[failure_reason = null]
    N --> R{ErrorCode = 0?}

    R -->|Yes| S[is_success = True]
    R -->|No| T[is_success = False<br/>failure_reason = FailureReason]

    P --> U[Process Login Event]
    Q --> U
    S --> U
    T --> U
    I --> U

    U --> V[Insert into login_analytics<br/>with all required fields]
    V --> W[Mark audit_log as processed]
    W --> X[End]

    subgraph "Failure Error Codes"
        FC[50053: Account Locked<br/>50074: Password Expired<br/>50126: Invalid Credentials<br/>50127: User Does Not Exist<br/>and more...]
    end

    style C fill:#ffcccc
    style G fill:#ffcccc
    style L fill:#ffcccc
    style T fill:#ffcccc
    style I fill:#ccffcc
    style S fill:#ccffcc
```

## Key Processing Logic

### Success Detection (PR #20)
1. **Operation Check**: If Operation contains "UserLoginFailed" or "Failed" → **Failure**
2. **ErrorNumber Check**: Only these codes indicate failure:
   - `50053` - Account locked
   - `50074` - Password expired
   - `50126` - Invalid credentials
   - `50127` - User does not exist
   - `50140` - **SKIP** (Strong auth required - not a failure!)
   - And 11 more codes...
3. **LogonError Check**: If present → **Failure**
4. **ExtendedProperties Fallback**: Get ResultStatusDetail (skip "Success")
5. **Status.ErrorCode Fallback**: Final check

### Important Notes
- **ResultStatus: "Success"** means the API request was processed, NOT that login succeeded
- **ErrorNumber 50140** (UserStrongAuthClientAuthNRequiredInterrupt) is a warning, not a failure
- Actual login status is determined by Operation, ErrorNumber, and LogonError fields