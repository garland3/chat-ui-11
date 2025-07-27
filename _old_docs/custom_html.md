# Using `custom_html` in MCP Responses

This document explains how to return and design custom HTML from an MCP server for rendering in the Chat UI frontend.

---

## How to Invoke `custom_html`

- In your MCP tool response, include a field named `custom_html` containing your HTML string.
- Example response:

```json
{
  "content": "Here is a chart.",
  "custom_html": "<div><canvas id='myChart'></canvas><script>/* chart code */</script></div>"
}
```
- The frontend will automatically render this HTML in the Canvas panel when received.

---

## Frontend Handling

- The frontend listens for tool responses with a `custom_html` field.
- The HTML is sanitized using [DOMPurify](https://github.com/cure53/DOMPurify) before rendering to prevent XSS and unsafe code.
- The Canvas panel auto-opens to display the custom UI.

---

## Designing Custom HTML

### General Guidelines
- Use responsive layouts (CSS Grid, Flexbox) for best results.
- Keep content within the Canvas panel's width and height constraints.
- Use standard HTML elements and CSS. Tailwind classes are supported if included in the project.
- Avoid absolute positioning or fixed sizes that may break on small screens.

### JavaScript Limitations
- You can include `<script>` tags in your HTML.
- Only standard browser APIs are available. You **cannot** access Chat UI internals or global variables.
- All JS is sanitized; unsafe code will be stripped.
- Avoid inline event handlers (e.g., `onclick`) if possible; prefer adding listeners via script.
- Do not rely on external JS libraries unless you include a CDN `<script src=...>` tag in your HTML.

### DOM & CSS Limitations
- Only safe HTML elements and attributes are allowed (per DOMPurify rules).
- You cannot modify elements outside the Canvas panel.
- Custom styles should not override global UI styles.
- Use scoped CSS or inline styles for your components.

---

## Example Use Cases
- Interactive charts and graphs (e.g., Chart.js via CDN)
- Custom forms and input widgets
- Dashboard-style data displays
- Rich formatted reports

---

## Security Notes
- All custom HTML is sanitized before rendering.
- Unsafe tags, attributes, or scripts will be removed.
- Test your HTML with DOMPurify to ensure compatibility.

---

## Developer Tips
- Always include both `content` (text) and `custom_html` (UI) fields in your response.
- Test your HTML in isolation before deploying.
- Make your UI responsive and accessible.
- Avoid dependencies on Chat UI internals.

---

For more details, see `MCP_UI_MODIFICATION.md`.
