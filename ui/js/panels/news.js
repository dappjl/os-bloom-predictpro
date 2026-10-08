import { fmtAge } from "../fmt.js";

// Headlines and links come from third-party RSS — escape before innerHTML,
// and only link out to http(s) URLs.
const esc = (s) => String(s).replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

export function renderNews(panel) {
  const body = document.querySelector("#panel-news .panel-body");
  body.innerHTML = panel.items.map((n) =>
    `<div class="news-item">
       ${/^https?:\/\//i.test(n.url)
         ? `<a href="${esc(n.url)}" target="_blank" rel="noopener">${esc(n.headline)}</a>`
         : `<span>${esc(n.headline)}</span>`}
       <div class="news-meta">${esc(n.feed)} · ${fmtAge(n.published_at)}</div>
     </div>`
  ).join("");
}
