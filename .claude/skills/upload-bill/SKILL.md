---
name: upload-bill
description: Upload a bill (facture) to the Dynamobile signup tool. Use when the user provides a bill/invoice/receipt as a PDF or image and asks to add, upload, or register it as a bill (facture) in the accounting tool.
---

# Upload a bill to dyn-signup

Turn a bill document (PDF or image) into an `accounts.Bill` record.

## Preferred: the MCP tool

If an `upload_bill` MCP tool is available (dyn-signup connector configured),
use it instead of the curl flow below: extract the fields (see "Steps" step
2), confirm them with the user, then call the tool — pass the document as
`file_base64` when you can read the raw file. This also works in sandboxes
whose network proxy blocks direct calls to the app.

To set the connector up, the user (treasurer) opens `/tokens/new/` on the
app while logged in, generates a token, and pastes the displayed MCP URL
into claude.ai → Settings → Connectors (or `claude mcp add --transport http
dyn-signup <url>` for Claude Code).

## Fallback: direct API with curl

## Configuration

- `DYN_SIGNUP_URL` (env var) — base URL of the deployed tool, e.g. `https://inscriptions.dynamobile.net` (use `http://localhost:8000` for local dev). Ask the user if missing.
- Token — stored in `~/.config/dyn-signup/token`. If the file is missing, or the API answers 401, obtain a fresh token with the device flow below.

## Getting a token (device flow)

1. Start a device authorization:

   ```bash
   curl -sS -X POST "$DYN_SIGNUP_URL/api/auth/device/" -F "client_name=Claude Code"
   ```

   The response contains `device_code`, `verification_url` and `interval`.

2. **Give the `verification_url` to the user** and ask them to open it in
   their browser and click "Approuver" (they must be logged in as treasurer).

3. Poll until approved (`device_code` expires after 15 minutes):

   ```bash
   for i in $(seq 1 60); do
     RESPONSE=$(curl -sS -X POST "$DYN_SIGNUP_URL/api/auth/device/token/" -F "device_code=$DEVICE_CODE")
     echo "$RESPONSE" | grep -q '"approved"' && break
     sleep 5
   done
   ```

   Statuses: `pending` (keep polling), `approved` (response contains `token`,
   returned only once — save it immediately), `expired`/`invalid` (start over).

4. Save the token:

   ```bash
   mkdir -p ~/.config/dyn-signup
   echo "$TOKEN" > ~/.config/dyn-signup/token
   chmod 600 ~/.config/dyn-signup/token
   ```

The user can revoke tokens at any time in the admin under "jetons API"; a
revoked token gets 401, in which case just run the device flow again.

## Steps

1. **Read the bill document** the user provided (the Read tool handles PDFs
   and images).
2. **Extract the fields:**
   - `name` — short label: vendor + what it is, e.g. `"Brico - matériel signalisation"`. If an invoice number is visible, append it.
   - `amount` — the total including VAT, as a positive decimal with a dot separator, e.g. `123.45`. Bills are stored as positive amounts.
   - `date` — the invoice/bill date (not the due date), ISO format `YYYY-MM-DD`.
3. **Confirm with the user** before uploading: show the extracted name,
   amount and date, and wait for their approval. Never upload unconfirmed
   data.
4. **Upload:**

   ```bash
   curl -sS -X POST "$DYN_SIGNUP_URL/api/bills/" \
     -H "Authorization: Bearer $(cat ~/.config/dyn-signup/token)" \
     -F "file=@/path/to/bill.pdf" \
     -F "name=Brico - matériel signalisation" \
     -F "amount=123.45" \
     -F "date=2026-07-05"
   ```

5. **Report the result** to the user:
   - `201` — success; give the user the admin link: `$DYN_SIGNUP_URL` + the `admin_url` field from the response.
   - `409` — a bill with the same name, amount and date already exists (the response lists `existing_ids`). Tell the user; do not retry with altered data to bypass the check unless they explicitly say it is a different bill.
   - `400` — validation errors are in the response body; fix the fields and retry.
   - `401` — token missing, wrong or revoked; run the device flow again.

## Notes

- One document = one bill. If the user provides several documents, process
  them one at a time, confirming each.
- If the document is unreadable or the total is ambiguous (multiple totals,
  handwriting), ask the user rather than guessing.
- The server must be running a version that includes the token endpoints
  and their migration (`accounts/0021_apitoken_deviceauthorization`). If
  `/api/auth/device/` returns 404 or a server error, the app probably needs
  to be redeployed and `manage.py migrate` run — tell the user rather than
  retrying.
