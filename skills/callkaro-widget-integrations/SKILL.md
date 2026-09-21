---
name: callkaro-widget-integrations
description: Embed CallKaro widget and connect CRMs. Use when installing widget on HTML React Next WordPress, using CallKaro JS API, connecting HubSpot LeadSquared Heltar AI Sensy, verifying numbers, buying numbers, DND.
---

# CallKaro Widget and Integrations

## Widget install

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

Next.js App Router: `next/script` with `strategy="afterInteractive"` in root layout. Pages Router: same in `_app` or `_document`. Never mix `defer` with `strategy`. WordPress: paste in `footer.php` before `</body>` via Appearance Theme File Editor.

Docs: https://docs.callkaro.ai/widget/install-on-your-website, customization, JS API, troubleshooting.

## Widget JS API

`window.CallKaro` appears after load (script uses defer, so poll or wait for click).

```js
CallKaro.open()
CallKaro.close()
CallKaro.on('open', fn).on('start', fn).on('end', fn)
CallKaro.widgetId
```

Open only from a click. Auto open on load gets mic blocked and annoys visitors. Opening shows the panel, visitor still presses Talk and grants mic. Close during a call ends it. Listeners stack and cannot be removed, errors inside callbacks only log.

## HubSpot

Flow: convert HubSpot account to developer, create Private legacy app, add scopes `crm.objects.contacts.read`, `crm.objects.contacts.write`, `crm.schemas.contacts.read`, `crm.schemas.contacts.write`, set webhook URL:

```
https://api.callkaro.ai/call/crm-webhook?agent_id=YOUR_AGENT_ID&type=hubspot&x_api_key=YOUR_API_KEY
```

Copy token into CallKaro, map contact fields to agent variables. New contacts then trigger calls.

## LeadSquared

Same shape as HubSpot: connect in Integrations, map fields, new leads trigger calls. Docs: https://docs.callkaro.ai/integrations/leadsquared

## Heltar and AI Sensy

Third party WhatsApp senders. Connect Heltar for templates, AI Sensy for campaigns. Each keeps its own dashboard, CallKaro only stores the link. Docs: https://docs.callkaro.ai/integrations/heltar and aisensy pages.

## Phone numbers

Buy: business verification first (India: GST plus CIN; outside India: any government registration proof, PDF or image). Then Phone Numbers Buy Phone Numbers, pick from table, credits deduct at once, billed monthly same date. Without verification you redirect to Compliances.

Verify personal numbers for pre verification testing: Dashboard Settings Verified Phone Numbers, Add, get 6 digit OTP on WhatsApp, enter, done. Verified means ready (cannot delete), Pending means OTP unsent (can delete, resend after 60s). After business approval you can test any number, no OTP needed.

DND: Dashboard Settings DND Phone Numbers. Calls to DND numbers never go out.
