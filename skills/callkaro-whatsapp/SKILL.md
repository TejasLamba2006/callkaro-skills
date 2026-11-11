---
name: callkaro-whatsapp
description: Run WhatsApp on CallKaro. Use when connecting numbers, managing templates, sending via API, building campaign CSVs, reading inbox history, handling delivery status.
---

# CallKaro WhatsApp

Three providers: WhatsApp Facebook (direct Meta), Heltar, AI Sensy. This skill covers the direct path plus shared concepts.

Docs: https://docs.callkaro.ai/whatsapp/signup

## Connect (Facebook)

Dashboard WhatsApp Signup, or `https://callkaro.ai/dashboard/whatsapp/signup`. Contact support to enable, or Continue with Facebook. One WABA links to one CallKaro account only.

Phone options: your own spare number (never on WhatsApp, gets OTP by SMS or call) or a CallKaro purchased number (set as agent inbound, OTP arrives as a call, find it in Call History recording within 4 to 5 min). Enter the 6 digit OTP.

To send at scale: add card plus GST in Meta Business settings and finish business verification. To receive: hit Subscribe on the WhatsApp page.

## Templates

Send only approved templates outside the 24h window, and **the first message to a user must always be a template**; free-form text is allowed only within 24 hours of the customer's last message. Language resolves to the approved one if you omit `language_code`, otherwise `"en"`.

Template statuses: APPROVED, PENDING, REJECTED, PAUSED (and IN_APPEAL). A template can be edited only when APPROVED, REJECTED or PAUSED, once per day and at most 10 times a month. A deleted template cannot be recovered. Templates made in Meta Business Manager sync to CallKaro.

Send API `POST https://api.callkaro.ai/whatsapp/send-template`:

```bash
curl -X POST "https://api.callkaro.ai/whatsapp/send-template" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: $KEY" \
  -d '{"phone_number_id": "123456789012345", "to_number": "919876543210",
    "template_name": "order_shipped",
    "components": [{"type": "body", "parameters": [{"type": "text", "text": "Rahul"}, {"type": "text", "text": "#1234"}]}],
    "metadata": {"plan_type": "Gold", "City": "Delhi"}}'
```

Response includes `message_id`, `contact_updated`, `metadata_ignored`. Creates the contact as outbound if new, never reclassifies existing ones. **A 200 does not mean the user received it**, only that the send was accepted; a rejected send is stored with Meta's reason and is not retried for you.

Optional body fields: `wa_campaign_id` (1 to 64 letters, digits, `_` or `-`; attributes the send to a campaign and follow-ups inherit it), `agent_id` (tag only), `extra` (stored on the message row, not written to the contact). Errors: 400 `whatsapp_error` with Meta's reason (footer max 60, body max 1024 characters), 400 "WhatsApp Business Account not linked", 403 "phone_number_id does not belong to this account".

`components` fills this message only. `metadata` saves onto the contact and persists. Send a value in both if you want both jobs done.

Metadata rules: attribute must already exist under Contacts Attributes. Matching ignores case, spaces, underscores, hyphens. Blank values skip, hand edited values are never overwritten, failed sends save nothing. Max 50 keys, values max 1000 chars, over limit returns 400. Always check `metadata_ignored` on first integration, typos still send the message.

## Campaigns

Create at `/dashboard/whatsapp/campaign/create`, analytics at `/dashboard/whatsapp/campaign`. CSV rules: first column always `phone` in international format. Then `header_0`, `body_0`, `body_1`, `button_0` matching template `{{1}}`, `{{2}}` slots.

```csv
phone,body_0,body_1
+919876543210,John,ORD123
```

Test with your own number first. The template must be APPROVED and the sending number `CLOUD_API`. The follow-up block can nudge non repliers: minimum delay 60 minutes (shorter risks Meta flagging the sender as spam), and it is a Follow-up Template **or** a Follow-up Call, not both.

Analytics: "Sent" means the message reached Meta and includes delivered and read. Read counts run low because recipients with read receipts off are not counted.

CLI (`cku wa-campaigns`, dashboard login): `list`, `analytics <id>`, `timeseries <id> [--start --end]`, `export <id> [--fields a,b --include-chat --file out.csv]`, `send --set @body.json`. See `callkaro-cli`.

## History API

`GET https://api.callkaro.ai/whatsapp/messages?user_phone_number=919876543210&limit=50` with `X-API-KEY`. Add `agent_phone_number` to scope to one sender. Returns oldest first, exactly what the agent sees. `limit` defaults to 50 and is capped at 200; a larger value is silently reduced, not rejected. Another account's number returns an empty list, not an error.

Each message: `name` inbound or outbound, `time` IST, `status`, `type`, `body` (templates and media flattened to readable text), `msg_id` (wamid), `content_link` for media, `tool_calls` for agent function use. Excludes failed sends, internal developer rows, and anything before a chat reset.

Status truth: `read` and `delivered` mean arrived. `sent` means accepted by WhatsApp, not on the phone yet. Do not treat `sent` as delivered.

## Inbox

WhatsApp Inbox page holds the same threads. Subscribe first or inbound never arrives.

CLI (`cku inbox`, dashboard login): `list`, `unread`, `contact <phone>`, `handoffs`, `release <fromId> --channel whatsapp`, `deassign <phone>`, `clear <phone> --yes`. See `callkaro-cli`.
