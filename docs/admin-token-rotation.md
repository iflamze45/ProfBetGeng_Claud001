# ADMIN_TOKEN Rotation Runbook

## When to Rotate
- Any time the token may have been exposed (logs, screenshots, chat)
- Every 90 days as routine hygiene
- When offboarding anyone who had access

## Steps (zero downtime — old token rejected the moment new one is live)

### 1. Generate new token
```bash
python3 -c "import secrets; print('pbg_' + secrets.token_urlsafe(32))"
```
Save the output — you will need it for steps 2 and 3.

### 2. Set on Render
Tell Claude: *"Rotate the PBG admin token"* and use the secure key input flow,
or set it manually in the Render dashboard:
Dashboard → profbetgeng-api → Environment → ADMIN_TOKEN

### 3. Set on Vercel (frontend)
Dashboard → frontend project → Settings → Environment Variables → VITE_ADMIN_TOKEN
Then trigger a redeploy so the frontend picks up the new value.

### 4. Verify
```bash
# Should return 200
curl -s -o /dev/null -w "%{http_code}" -X POST https://profbetgeng.onrender.com/api/v1/keys \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: <NEW_TOKEN>" \
  -d '{"label": "rotation-verify", "owner": "admin"}'

# Should return 403
curl -s -o /dev/null -w "%{http_code}" -X POST https://profbetgeng.onrender.com/api/v1/keys \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: <OLD_TOKEN>" \
  -d '{"label": "rotation-verify", "owner": "admin"}'
```

### 5. Clean up test key (optional)
The test key created in step 4 can be deactivated via Supabase:
```sql
UPDATE api_keys SET is_active = false WHERE name = 'rotation-verify';
```

## Notes
- The backend validates the token on every request — no restart needed
- If Render redeploys before Vercel, the frontend key creation will fail temporarily (seconds only)
- Store the current token in 1Password or equivalent — never in git or chat
