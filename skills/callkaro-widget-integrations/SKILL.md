---
name: callkaro-widget-integrations
description: Embed CallKaro voice and chat widgets and connect CRMs. Use when installing the voice widget on HTML React Next WordPress Shopify Webflow GTM, linking the chat widget from a site or mobile app, using CallKaro JS API, fixing a widget that loads but will not talk (HTTPS, CSP, Permissions-Policy), connecting HubSpot LeadSquared Heltar AI Sensy, verifying numbers, buying numbers, DND.
---

# CallKaro Widget and Integrations

Two separate products: the **voice widget** (one script tag, talks through the browser mic) and the **chat widget** (one URL, opened in a web view). Both are created at Dashboard, Embed Widgets (`/dashboard/widgets`). Creating one needs the Widgets subscription (Rs 3,000 per month, deducted from credits). Without it a chat widget still opens but refuses to start a conversation, send a message or upload a file.

Anyone who visits a page with a widget can start a conversation, with no sign-in, and each conversation is billed like any other call. Put it only where you want that.

## Voice widget install

One script tag before `</body>`. That is the whole integration, no key, no package.

```html
<script src="https://widget.callkaro.ai/w.js" data-ck-id="your-widget-id" defer></script>
```

Put it in the shared layout so every page gets it.

React: inject on mount, JSX script tags never run.

```jsx
import { useEffect } from "react"
export default function CallKaroWidget() {
  useEffect(() => {
    const s = document.createElement("script")
    s.src = "https://widget.callkaro.ai/w.js"
    s.defer = true
    s.dataset.ckId = "your-widget-id"
    document.body.appendChild(s)
    return () => s.remove()
  }, [])
  return null
}
```

Next.js App Router: `next/script` with `strategy="afterInteractive"` in root layout. Pages Router: same in `_app` or `_document`. Never mix `defer` with `strategy`. WordPress: use a child theme or a header/footer plugin (an edit to the theme's `footer.php` is lost on the next theme update). Shopify: `theme.liquid`. Webflow: Footer Code, then publish. Google Tag Manager: a Custom HTML tag on the All Pages trigger.

It loads but will not talk? Check these in order:

1. **HTTPS.** Browsers only give the mic to secure origins. On `http://` the launcher and panel work and starting a conversation always fails. `http://localhost` is exempt.
2. **Content-Security-Policy.** Allow `script-src https://widget.callkaro.ai; frame-src https://widget.callkaro.ai; connect-src https://backend.callkaro.ai;`.
3. **Permissions-Policy.** A header such as `microphone=()` blocks the mic delegation: the widget loads and conversations fail to start.
4. **Two snippets on one page.** Only one widget runs per page; the second is ignored. Usual cause: the snippet is in both the layout and a template.
5. **Widget state.** Paused hides the launcher and declines conversations. Deleted stops it on every site. Edits reach the live site in about a minute.

Docs: https://docs.callkaro.ai/widget/voice/install-on-your-website, and `/widget/voice/customization`, `/widget/voice/javascript-api`, `/widget/voice/troubleshooting`.

## Widget JS API

`window.CallKaro` appears after load (script uses defer, so poll or wait for click).

```js
CallKaro.open()
CallKaro.close()
CallKaro.on('open', fn).on('start', fn).on('end', fn)
CallKaro.widgetId
```

Events and payloads: `open` `{}`, `close` `{}`, `ready` `{ widgetId }` (fires after the panel is opened the first time, not on page load), `start` `{ state: 'start', sessionId }`, `end` `{ state: 'end' }`.

Open only from a click. Auto open on load gets mic blocked and annoys visitors. Opening shows the panel, visitor still presses Talk and grants mic. Close during a call ends it. Listeners stack and cannot be removed, errors inside callbacks only log. There is no transcript access and no way to start a conversation from code.

## Chat widget

A chat widget is one URL, not a script:

```
https://widget.callkaro.ai/chat.html?w=YOUR_WIDGET_ID
```

- Website: a plain `<a>` link or an `<iframe>`. iOS: `SFSafariViewController`. Android: Custom Tabs (a `WebView` needs `domStorageEnabled = true`). React Native and Flutter: a WebView wrapper (snippets on the install page). On native, prefer the system browser tab over a WebView unless the chat has to sit inside your own navigation.
- Optional query params: `&uid=user_8271` to tie the chat to your user, `&vars={"plan":"Growth"}` (URL-encoded JSON) to pass variables. **`uid` is an unauthenticated claim**: anyone can put any value in the URL, so never use it to show private data.
- The agent behind it must be a **Guided flow** agent and must be **published**; the chat widget runtime runs only flow agents.
- Limits: 5,000 cards per flow, 200 turns per conversation, 12 hours to resume a conversation, 10 concurrent chats per teammate on human handoff, 8 s for an API card.
- Docs: `/widget/chat/introduction`, `install`, `card-types`, `ai-card`, `chat-routing`, `human-handoff`, `knowledge-base`, `ticket-fallback`, `variables`, `troubleshooting`, and `build-with-claude` for the flow spec.

## HubSpot

Flow: convert HubSpot account to developer, create Private legacy app, add scopes `crm.objects.contacts.read`, `crm.objects.contacts.write`, `crm.schemas.contacts.read`, `crm.schemas.contacts.write`, set webhook URL:

```
https://api.callkaro.ai/call/crm-webhook?agent_id=YOUR_AGENT_ID&type=hubspot&x_api_key=YOUR_API_KEY
```

Copy token into CallKaro, map contact fields to agent variables (agent, Variable Source tab, source `hubspot`). New contacts then trigger calls (pick the trigger event in HubSpot, for example Contact Created).

The Integrations page (`/dashboard/integrations`) lists seven providers: AI Sensy, Heltar, HubSpot, HubSpot Plus (one-click connect through CallKaro's HubSpot app, and the one that enables call write-back under an agent's Formatting, HubSpot Call Properties tab), Instagram, LeadSquared and Shopify. The steps above are the classic HubSpot private-app route.

The CRM webhook URL also takes `min_trigger_time`, `max_trigger_time`, `carry_over`, `num_of_retries` and `gap_between_retries` as query params. The integration pages give the gap in **hours** (`2,4,6`) while the outbound API uses minutes and spells it `number_of_retries`; test one lead before trusting either.

## LeadSquared

Not the same shape as HubSpot. CallKaro needs three values from LeadSquared (Host URL, Access Key, Secret Key), and LeadSquared calls the same `crm-webhook` URL with `type=leadsquared` on the Lead Created trigger. **Set the webhook Content-Type to `application/json`**: LeadSquared often defaults to `form` and the webhook then fails. The API key can go in the `X-API-KEY` header or the `x_api_key` query param. Docs: https://docs.callkaro.ai/integrations/leadsquared

## Heltar and AI Sensy

Third party WhatsApp senders. Connect Heltar for templates, AI Sensy for campaigns. Each keeps its own dashboard, but CallKaro stores their credentials: the Heltar API key, and for AI Sensy an API key (Basic) or API key plus Project ID plus App Password (Pro). Sends are set up per agent in the WhatsApp Configuration tab as an in-call or post-call action. For AI Sensy the Campaign Name must match AI Sensy's exactly, including case. Templates must already be approved in that provider. Docs: https://docs.callkaro.ai/integrations/heltar and aisensy pages.

## Phone numbers

Buy: business verification first (India: GST plus CIN; outside India: any government registration proof, PDF or image). Then Phone Numbers Buy Phone Numbers, pick from table, credits deduct at once, billed monthly same date. Without verification you redirect to Compliances.

Verify personal numbers for pre verification testing: Dashboard Settings Verified Phone Numbers, Add, get 6 digit OTP on WhatsApp, enter, done. Verified means ready (cannot delete), Pending means the OTP was sent but not yet entered (can delete, resend after 60s). After business approval you can test any number, no OTP needed.

DND: Dashboard Settings DND Phone Numbers. Calls to DND numbers never go out; to call one again, remove it from the list first.

Renting: marking a number as spam does not stop billing, only unrenting does. An unrented number cannot be recovered, and there are no refunds for a part month or for spam-marked numbers.
