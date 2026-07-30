# Icon set

UI icons are [Tabler Icons](https://tabler.io/icons) (MIT license, outline
style, 24x24, 2px stroke), vendored as an inline SVG `<symbol>` sprite at
the top of `app/templates/dashboard.html`'s `<body>` — no CDN, no npm
package, no build step, matching the rest of this app.

## Using an icon

```html
<svg class="icon"><use href="#tabler-search"/></svg>
```

`.icon` (styles.css) sizes it to `1em` (matches surrounding text) and
sets `stroke: currentColor` so it inherits the element's text color.
Override size with an inline `style="width:20px;height:20px"` when an
icon needs to be bigger than its text (e.g. a lone icon button).

## Adding a new icon

1. Find the icon at [tabler.io/icons](https://tabler.io/icons) and note
   its slug (e.g. `map-pin`).
2. Fetch the outline SVG:
   `curl -s https://raw.githubusercontent.com/tabler/tabler-icons/main/icons/outline/<slug>.svg`
3. Strip the leading comment block and the `<svg ...>`/`</svg>` wrapper,
   keep the inner `<path>` elements.
4. Add `<symbol id="tabler-<slug>" viewBox="0 0 24 24">...</symbol>` to
   the sprite in `dashboard.html`.
5. Reference it as `<svg class="icon"><use href="#tabler-<slug>"/></svg>`.

## Icons currently vendored

search, briefcase, settings, clipboard-list, file-text, link, bolt,
users, target, history, x, map-2, brand-github, brand-reddit, brand-x,
brand-whatsapp, code, brand-medium, brand-stackoverflow, rocket, flag,
palette, brand-telegram, brand-facebook, world, map-pin, download, trash,
table-export, braces, mail, brand-youtube, refresh, player-stop.
