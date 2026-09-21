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

Send only approved templates outside the 24h window. Language resolves to the approved one if you omit `language_code`.

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

Response includes `message_id`, `contact_updated`, `metadata_ignored`. Creates the contact as outbound if new, never reclassifies existing ones.

`components` fills this message only. `metadata` saves onto the contact and persists. Send a value in both if you want both jobs done.

Metadata rules: attribute must already exist under Contacts Attributes. Matching ignores case, spaces, underscores, hyphens. Blank values skip, hand edited values are never overwritten, failed sends save nothing. Max 50 keys, values max 1000 chars, over limit returns 400. Always check `metadata_ignored` on first integration, typos still send the message.

## Campaigns

Create at `/dashboard/whatsapp/campaign/create`, analytics at `/dashboard/whatsapp/campaign`. CSV rules: first column always `phone` in international format. Then `header_0`, `body_0`, `body_1`, `button_0` matching template `{{1}}`, `{{2}}` slots.

```csv
phone,body_0,body_1
+919876543210,John,ORD123
```

Test with your own number first. Follow-up block can nudge non repliers.

## History API

`GET https://api.callkaro.ai/whatsapp/messages?user_phone_number=919876543210&limit=50` with `X-API-KEY`. Add `agent_phone_number` to scope to one sender. Returns oldest first, exactly what the agent sees.

Each message: `name` inbound or outbound, `time` IST, `status`, `type`, `body` (templates and media flattened to readable text), `msg_id` (wamid), `content_link` for media, `tool_calls` for agent function use. Excludes failed sends, internal developer rows, and anything before a chat reset.

Status truth: `read` and `delivered` mean arrived. `sent` means accepted by WhatsApp, not on the phone yet. Do not treat `sent` as delivered.

## Inbox

WhatsApp Inbox page holds the same threads. Subscribe first or inbound never arrives.
