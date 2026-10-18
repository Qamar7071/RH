/* =========================================================
   RH LABS EXTRAS
   Adds: WhatsApp button, FAQ, testimonials, case study popup,
   booking button, footer social links, Privacy link, analytics,
   and a "clean" launch mode that hides empty placeholders.

   Setup: in index.html, put this line just before </body>:
     <script src="extras.js"></script>
   ========================================================= */
const EXTRAS = {
  // true = hide empty project cards, unnamed team members, empty social icons and "Add photo" boxes
  hideEmpty: true,

  // Free consultation booking link (Calendly / Cal.com). Empty = no booking button.
  bookingUrl: "",

  // Company pages. Only filled links get an icon in the footer.
  social: { linkedin: "", github: "", instagram: "", facebook: "" },

  // Cloudflare Web Analytics token (Cloudflare > Analytics & Logs > Web Analytics). Empty = off.
  cloudflareToken: "",

  // First message when a visitor taps the WhatsApp button
  whatsappMessage: "Hi RH Labs, I'd like to discuss a project.",

  faqs: [
    { q: "How much does a website or chatbot cost?",
      a: "Every project gets a written quote based on what you need. Share your requirements through the form or WhatsApp and we usually send a quote within one working day. The first consultation is free." },
    { q: "How long does a project take?",
      a: "A simple website or an AI chatbot usually takes 1 to 3 weeks. An AI agent takes 2 to 6 weeks, depending on how many systems it connects to. The exact deadline is written in your quote." },
    { q: "Can the chatbot answer in Urdu?",
      a: "Yes. Our chatbots can answer in English, Urdu and Roman Urdu, using your own products, prices and FAQs." },
    { q: "Can you add a chatbot to my existing website?",
      a: "Yes. A chatbot can be added to most existing websites, and we can also connect it to WhatsApp." },
    { q: "How does payment work?",
      a: "Payment terms and method are agreed in writing in your quote before any work starts." },
    { q: "Who owns the code after the project?",
      a: "You do. After the project is complete we hand over the code, logins and documentation." },
    { q: "Do you work with clients outside Pakistan?",
      a: "Yes. We work online with clients in Pakistan and abroad, and we can meet clients in Islamabad in person." },
    { q: "Do you provide support after launch?",
      a: "Yes. We fix bugs and make small updates after launch, and we offer monthly maintenance plans." }
  ],

  // Real client reviews only, added with the client's permission. Empty list = section hidden.
  // Example: { quote: "...", name: "Ali Khan", role: "Owner", company: "Khan Traders", photo: "images/client-1.jpg" }
  testimonials: []
};
/* ========================================================= */

(function () {
  "use strict";
  const $ = (s, root) => (root || document).querySelector(s);
  const $$ = (s, root) => Array.from((root || document).querySelectorAll(s));
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const site = typeof SITE !== "undefined" ? SITE : {};
  const projects = typeof PROJECTS !== "undefined" ? PROJECTS : [];
  const rawWa = String(site.whatsappNumber || "").replace(/\D/g, "");
  const waNumber = /0{7}$/.test(rawWa) ? "" : rawWa;  // placeholder number = no WhatsApp button
  const ARROW = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>';

  /* ---------- styles ---------- */
  const css = `
.wa-float{position:fixed;z-index:49;right:max(37px,calc(29px + env(safe-area-inset-right,0px)));bottom:calc(122px + env(safe-area-inset-bottom,0px));width:54px;height:54px;border-radius:50%;background:#1FA855;color:#fff;display:grid;place-items:center;box-shadow:0 12px 26px -10px rgba(16,110,55,.7);text-decoration:none;transition:transform .15s,background .15s}
.wa-float:hover{background:#178A45;transform:translateY(-2px)}
.wa-float svg{width:28px;height:28px}
#chat-launch[aria-expanded="true"] ~ .wa-float{display:none}
@media (max-width:520px){.wa-float{right:max(26px,calc(18px + env(safe-area-inset-right,0px)));bottom:calc(96px + env(safe-area-inset-bottom,0px));width:50px;height:50px}}

.faq-grid{display:grid;grid-template-columns:minmax(0,.8fr) minmax(0,1.2fr);gap:40px 64px;align-items:start}
.faq-side{display:flex;flex-direction:column;gap:16px;min-width:0}
.faq-side p:not(.eyebrow){margin:0;color:var(--muted,#5A6A82)}
.faq-side .row{display:flex;flex-wrap:wrap;gap:10px;margin-top:6px}
.faq-list{display:flex;flex-direction:column;gap:12px;min-width:0}
.faq-item{background:var(--white,#fff);border:1px solid var(--line,#E2E8F1);border-radius:14px;overflow:hidden}
.faq-item[open]{border-color:var(--blue-line,#BCD0F5);box-shadow:0 6px 18px -12px rgba(11,27,51,.3)}
.faq-item summary{list-style:none;cursor:pointer;display:flex;align-items:center;justify-content:space-between;gap:16px;padding:18px 20px;font-weight:700;font-size:1rem}
.faq-item summary::-webkit-details-marker{display:none}
.faq-item summary::after{content:"+";flex:none;width:30px;height:30px;border-radius:8px;background:var(--blue-soft,#EAF1FE);color:var(--blue,#1D5BF0);display:grid;place-items:center;font-size:1.2rem;font-weight:700}
.faq-item[open] summary::after{content:"\\2212"}
.faq-item p{margin:0;padding:0 20px 20px;color:var(--muted,#5A6A82)}
@media (max-width:900px){.faq-grid{grid-template-columns:minmax(0,1fr)}}

.tm-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),380px));justify-content:center;gap:24px}
.tm{display:flex;flex-direction:column;gap:18px;padding:28px;background:var(--white,#fff);border:1px solid var(--line,#E2E8F1);border-radius:16px;min-width:0}
.tm-q{width:34px;height:34px;color:var(--blue,#1D5BF0)}
.tm blockquote{margin:0;font-size:1.02rem;line-height:1.65}
.tm-who{margin-top:auto;display:flex;align-items:center;gap:12px;padding-top:16px;border-top:1px solid var(--line,#E2E8F1)}
.tm-av{width:46px;height:46px;border-radius:50%;flex:none;background:var(--blue,#1D5BF0);color:#fff;display:grid;place-items:center;font-weight:800;overflow:hidden}
.tm-av img{width:100%;height:100%;object-fit:cover}
.tm-who strong{display:block;line-height:1.3}
.tm-role{display:block;font-size:.86rem;color:var(--muted,#5A6A82)}

.cs-link{display:inline-flex;align-items:center;gap:6px;padding:0;border:none;background:none;color:var(--blue,#1D5BF0);font-family:inherit;font-weight:700;font-size:.9rem;line-height:1.3;cursor:pointer}
.cs-link svg{width:15px;height:15px;transition:transform .15s}
.cs-link:hover svg{transform:translateX(3px)}
html.cs-open{overflow:hidden}
.cs-modal{width:min(920px,calc(100vw - 32px));max-height:calc(100vh - 48px);padding:0;border:none;border-radius:20px;background:var(--white,#fff);color:var(--ink,#0B1B33);box-shadow:0 40px 90px -30px rgba(0,0,0,.55);overflow:auto}
.cs-modal::backdrop{background:rgba(8,20,45,.6)}
.cs-cover{position:relative;aspect-ratio:16/7;max-width:100%;background:linear-gradient(135deg,var(--blue-soft,#EAF1FE),var(--blue-soft-2,#D6E4FD))}
.cs-cover img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.cs-close{position:sticky;top:12px;float:right;margin:12px 12px -56px 0;z-index:2;width:44px;height:44px;border-radius:12px;border:none;background:rgba(255,255,255,.95);color:var(--ink,#0B1B33);display:grid;place-items:center;cursor:pointer;box-shadow:0 6px 16px -8px rgba(0,0,0,.4)}
.cs-close svg{width:20px;height:20px}
.cs-body{padding:28px 32px 32px;display:flex;flex-direction:column;gap:18px}
.cs-meta{margin:-8px 0 0;color:var(--muted,#5A6A82);font-weight:600;font-size:.92rem}
.cs-blocks{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}
.cs-block{padding:18px;border-radius:14px;background:var(--alt,#F5F8FD);border:1px solid var(--line,#E2E8F1);min-width:0}
.cs-block h4{margin:0 0 6px;font-size:.78rem;letter-spacing:.08em;text-transform:uppercase;color:var(--blue,#1D5BF0)}
.cs-block p{margin:0;font-size:.95rem}
.cs-block.result{background:var(--blue-soft,#EAF1FE);border-color:var(--blue-line,#BCD0F5)}
.cs-sub{margin:4px 0 0;font-size:1rem}
.cs-features{margin:0;padding-left:1.2em;display:grid;gap:6px;color:var(--ink,#0B1B33)}
.cs-tech{display:flex;flex-wrap:wrap;gap:6px;list-style:none;margin:0;padding:0}
.cs-tech li{font-size:.8rem;font-weight:600;background:var(--alt,#F5F8FD);border:1px solid var(--line,#E2E8F1);border-radius:6px;padding:4px 10px}
.cs-gallery{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.cs-gallery img{width:100%;border-radius:12px;border:1px solid var(--line,#E2E8F1);display:block}
.cs-actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:6px}
@media (max-width:700px){.cs-blocks,.cs-gallery{grid-template-columns:minmax(0,1fr)}.cs-body{padding:22px 18px 24px}}

.foot-socials{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}
.foot-socials a{width:40px;height:40px;border-radius:10px;display:grid;place-items:center;border:1px solid var(--on-dark-line,#1E2F4D);color:var(--on-dark,#EEF3FB);text-decoration:none}
.foot-socials a:hover{background:var(--blue,#1D5BF0);border-color:var(--blue,#1D5BF0)}
.foot-socials svg{width:19px;height:19px}
.foot-base a{color:inherit}
.booking-row{display:flex;flex-wrap:wrap;gap:10px}
.trust-book{display:inline-flex;margin-top:6px;font-weight:700;font-size:.86rem;text-decoration:none}

.rh-clean .slot:not(.loaded) .ph{display:none}
.rh-clean .slot:not(.loaded)::after{content:attr(data-initial);position:absolute;inset:0;display:grid;place-items:center;font-size:clamp(3rem,10vw,6rem);font-weight:800;color:var(--blue,#1D5BF0);opacity:.35}
.empty-note{grid-column:1/-1;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:16px 24px;padding:28px;border:1.5px dashed var(--blue-line,#BCD0F5);border-radius:16px;background:var(--white,#fff)}
.empty-note p{margin:0;color:var(--muted,#5A6A82);max-width:56ch}
`;
  const style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  /* ---------- small helpers ---------- */
  function loadImage(base, onload) {
    if (!base) return;
    const exts = /\.[a-z0-9]+$/i.test(base) ? [""] : [".png", ".jpg", ".jpeg", ".webp", ".svg"];
    const img = new Image();
    let i = 0;
    img.onload = () => onload(img.src);
    img.onerror = () => { i++; if (i < exts.length) img.src = base + exts[i]; };
    img.src = base + exts[0];
  }
  function section(id, cls, inner) {
    const s = document.createElement("section");
    s.className = "section" + (cls ? " " + cls : "");
    s.id = id;
    s.innerHTML = `<div class="wrap">${inner}</div>`;
    return s;
  }
  const waUrl = text => waNumber ? "https://wa.me/" + waNumber + (text ? "?text=" + encodeURIComponent(text) : "") : "";
  const contact = $("#contact");

  /* ---------- WhatsApp floating button ---------- */
  if (waNumber) {
    const a = document.createElement("a");
    a.className = "wa-float";
    a.href = waUrl(EXTRAS.whatsappMessage);
    a.target = "_blank"; a.rel = "noopener";
    a.setAttribute("aria-label", "Chat with us on WhatsApp");
    a.title = "WhatsApp: " + (site.whatsappDisplay || "");
    a.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 19.5l1.2-3.6A8 8 0 1 1 8.6 18.6z"/><path d="M9.2 8.6c.3 2.6 2.4 4.8 5.2 5.4l.9-1.2 1.8.8-.5 1.7c-3.7.3-7.6-3.2-8-7.4l1.6-.6.9 1.6z" fill="currentColor" stroke="none"/></svg>';
    document.body.appendChild(a);
  }

  /* ---------- Testimonials (only when real ones exist) ---------- */
  const tms = (EXTRAS.testimonials || []).filter(t => t && t.quote && t.name);
  if (tms.length && contact) {
    const cards = tms.map((t, i) => `<figure class="tm">
        <svg class="tm-q" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor"><path d="M10 7H6a3 3 0 0 0-3 3v4h4v4l3-4zm11 0h-4a3 3 0 0 0-3 3v4h4v4l3-4z"/></svg>
        <blockquote>${esc(t.quote)}</blockquote>
        <figcaption class="tm-who"><span class="tm-av" data-tm="${i}">${esc(t.name.trim().charAt(0).toUpperCase())}</span>
          <span><strong>${esc(t.name)}</strong><span class="tm-role">${esc([t.role, t.company].filter(Boolean).join(", "))}</span></span></figcaption>
      </figure>`).join("");
    const sec = section("testimonials", "", `
      <div class="section-head center"><p class="eyebrow">Testimonials</p><h2>What Our Clients Say</h2></div>
      <div class="tm-grid">${cards}</div>`);
    contact.parentNode.insertBefore(sec, contact);
    tms.forEach((t, i) => loadImage(t.photo, src => {
      const av = $(`.tm-av[data-tm="${i}"]`, sec);
      av.innerHTML = `<img src="${esc(src)}" alt="">`;
    }));
  }

  /* ---------- FAQ ---------- */
  const faqs = (EXTRAS.faqs || []).filter(f => f && f.q && f.a);
  if (faqs.length && contact) {
    const items = faqs.map((f, i) => `<details class="faq-item"${i === 0 ? " open" : ""}><summary>${esc(f.q)}</summary><p>${esc(f.a)}</p></details>`).join("");
    const waBtn = waNumber ? `<a class="btn btn-outline" href="${esc(waUrl(EXTRAS.whatsappMessage))}" target="_blank" rel="noopener">WhatsApp Us</a>` : "";
    const sec = section("faq", "alt", `
      <div class="faq-grid">
        <div class="faq-side">
          <p class="eyebrow">FAQ</p>
          <h2>Frequently Asked Questions</h2>
          <p>Quick answers to what clients usually ask. Still have a question? Ask our assistant or message us.</p>
          <div class="row"><button class="btn btn-primary" type="button" data-open-chat>Ask the Assistant</button>${waBtn}</div>
        </div>
        <div class="faq-list">${items}</div>
      </div>`);
    contact.parentNode.insertBefore(sec, contact);
    const chatBtn = $("[data-open-chat]", sec);
    chatBtn.addEventListener("click", () => { const l = $("#chat-launch"); if (l && l.getAttribute("aria-expanded") !== "true") l.click(); });
    const companyList = $$(".foot-col h4").find(h => h.textContent.trim() === "Company");
    if (companyList) {
      const li = document.createElement("li");
      li.innerHTML = '<a href="#faq">FAQ</a>';
      companyList.parentElement.querySelector("ul").appendChild(li);
    }
  }

  /* ---------- Booking link ---------- */
  if (EXTRAS.bookingUrl) {
    const url = esc(EXTRAS.bookingUrl);
    const contactText = $("#contact .contact-left > p");
    if (contactText) {
      const row = document.createElement("div");
      row.className = "booking-row";
      row.innerHTML = `<a class="btn btn-primary" href="${url}" target="_blank" rel="noopener">Book a Free 30-min Call ${ARROW}</a>`;
      contactText.after(row);
    }
    const trust = $$(".trust-item h4").find(h => /consultation/i.test(h.textContent));
    if (trust) {
      const a = document.createElement("a");
      a.className = "trust-book"; a.href = EXTRAS.bookingUrl; a.target = "_blank"; a.rel = "noopener";
      a.textContent = "Book a call →";
      trust.parentElement.appendChild(a);
    }
  }

  /* ---------- Footer: social links + Privacy Policy ---------- */
  const SOC = {
    linkedin: ["LinkedIn", '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="3"/><path d="M8 10.5V17M8 7.2v.1M12 17v-3.6a2.4 2.4 0 0 1 4.8 0V17M12 10.5V17"/></svg>'],
    github: ["GitHub", '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m8 8-4 4 4 4M16 8l4 4-4 4M13.5 5l-3 14"/></svg>'],
    instagram: ["Instagram", '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" aria-hidden="true"><rect x="3.5" y="3.5" width="17" height="17" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.2" cy="6.8" r=".8" fill="currentColor"/></svg>'],
    facebook: ["Facebook", '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="3"/><path d="M15 8h-1.5A2.5 2.5 0 0 0 11 10.5V21M8.5 13H15"/></svg>']
  };
  const footBrand = $(".site-footer .foot-grid > div");
  const socials = Object.keys(SOC).filter(k => (EXTRAS.social || {})[k]);
  if (footBrand && socials.length) {
    const box = document.createElement("div");
    box.className = "foot-socials";
    box.innerHTML = socials.map(k => `<a href="${esc(EXTRAS.social[k])}" target="_blank" rel="noopener" aria-label="${SOC[k][0]}" title="${SOC[k][0]}">${SOC[k][1]}</a>`).join("");
    footBrand.appendChild(box);
  }
  const footBase = $(".site-footer .foot-base");
  if (footBase && !$('a[href="privacy.html"]', footBase)) {
    const span = document.createElement("span");
    span.innerHTML = '<a href="privacy.html">Privacy Policy</a>';
    footBase.insertBefore(span, footBase.children[1] || null);
  }
  const formNote = $("#project-form .form-foot small");
  if (formNote && !$("a", formNote)) formNote.innerHTML += ' See our <a href="privacy.html">Privacy Policy</a>.';

  /* ---------- Team: "Hire Me" becomes "Work With Us" ---------- */
  $$(".pactions a.btn-primary").forEach(a => { if (/hire me/i.test(a.textContent)) a.textContent = "Work With Us"; });

  /* ---------- Case study popup (projects with a "problem" filled in) ---------- */
  const cards = $$("#project-grid .project");
  const hasStory = p => p && (p.problem || p.solution || p.result);
  let dialog = null;

  function buildDialog() {
    dialog = document.createElement("dialog");
    dialog.className = "cs-modal";
    dialog.setAttribute("aria-labelledby", "cs-title");
    document.body.appendChild(dialog);
    dialog.addEventListener("click", e => { if (e.target === dialog) dialog.close(); });
    dialog.addEventListener("close", () => {
      document.documentElement.classList.remove("cs-open");
      try { if (/^#p\d+$/.test(location.hash)) history.replaceState(null, "", location.pathname + location.search); } catch (e) {}
    });
  }
  function openCase(i) {
    const p = projects[i];
    if (!hasStory(p)) return;
    if (!dialog) buildDialog();
    const list = arr => (arr || []).filter(Boolean);
    const meta = [p.client, p.year].filter(Boolean).join(" · ");
    const block = (label, text, cls) => text ? `<div class="cs-block${cls ? " " + cls : ""}"><h4>${label}</h4><p>${esc(text)}</p></div>` : "";
    const links = [];
    if (p.demo) links.push(`<a class="btn btn-primary btn-sm" href="${esc(p.demo)}" target="_blank" rel="noopener">Live Demo</a>`);
    if (p.github) links.push(`<a class="btn btn-outline btn-sm" href="${esc(p.github)}" target="_blank" rel="noopener">GitHub</a>`);
    links.push(`<a class="btn btn-outline btn-sm" href="#contact" data-cs-close>Start a Similar Project</a>`);
    dialog.innerHTML = `
      <button class="cs-close" type="button" aria-label="Close" data-cs-close><svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg></button>
      <div class="cs-cover" hidden></div>
      <div class="cs-body">
        ${p.category ? `<span class="ptag">${esc(p.category)}</span>` : ""}
        <h2 id="cs-title">${esc(p.title || "Project")}</h2>
        ${meta ? `<p class="cs-meta">${esc(meta)}</p>` : ""}
        ${p.description ? `<p style="margin:0;color:var(--muted,#5A6A82)">${esc(p.description)}</p>` : ""}
        <div class="cs-blocks">${block("Problem", p.problem)}${block("Solution", p.solution)}${block("Result", p.result, "result")}</div>
        ${list(p.features).length ? `<h4 class="cs-sub">Key features</h4><ul class="cs-features">${list(p.features).map(f => `<li>${esc(f)}</li>`).join("")}</ul>` : ""}
        ${list(p.tech).length ? `<h4 class="cs-sub">Technology</h4><ul class="cs-tech">${list(p.tech).map(t => `<li>${esc(t)}</li>`).join("")}</ul>` : ""}
        ${list(p.gallery).length ? `<h4 class="cs-sub">Screenshots</h4><div class="cs-gallery"></div>` : ""}
        <div class="cs-actions">${links.join("")}</div>
      </div>`;
    loadImage(p.image, src => { const c = $(".cs-cover", dialog); if (c) { c.innerHTML = `<img src="${esc(src)}" alt="">`; c.hidden = false; } });
    const gal = $(".cs-gallery", dialog);
    list(p.gallery).forEach(g => loadImage(g, src => {
      if (!gal) return;
      const img = document.createElement("img");
      img.src = src; img.alt = (p.title || "Project") + " screenshot"; img.loading = "lazy";
      gal.appendChild(img);
    }));
    $$("[data-cs-close]", dialog).forEach(b => b.addEventListener("click", () => dialog.close()));
    document.documentElement.classList.add("cs-open");
    if (typeof dialog.showModal === "function") dialog.showModal(); else dialog.setAttribute("open", "");
    try { history.replaceState(null, "", "#p" + (i + 1)); } catch (e) {}
  }
  cards.forEach((card, i) => {
    if (!hasStory(projects[i])) return;
    const body = $(".project-body", card);
    let links = $(".plinks", body);
    if (!links) { links = document.createElement("div"); links.className = "plinks"; body.appendChild(links); }
    const btn = document.createElement("button");
    btn.type = "button"; btn.className = "cs-link";
    btn.innerHTML = "View case study " + ARROW;
    btn.addEventListener("click", () => openCase(i));
    links.prepend(btn);
  });
  const deep = /^#p(\d+)$/.exec(location.hash);
  if (deep) setTimeout(() => openCase(+deep[1] - 1), 300);

  /* ---------- Clean launch mode ---------- */
  if (EXTRAS.hideEmpty) {
    document.documentElement.classList.add("rh-clean");
    cards.forEach(card => { if ($("h3.empty", card)) card.remove(); });
    $$("#project-grid .ptag").forEach(t => { if (t.textContent.trim() === "Category") t.remove(); });
    $$("#project-grid p.empty").forEach(p => p.remove());
    const grid = $("#project-grid");
    if (grid && !$(".project", grid)) {
      grid.innerHTML = `<div class="empty-note"><div><h3>Our first client case studies are on the way.</h3>
        <p>We are a new studio and take on a small number of projects at a time, so every client gets the full team's attention.</p></div>
        <a class="btn btn-primary" href="#contact">Start a Project</a></div>`;
    }
    $$(".profile").forEach(pr => {
      if ($(".pname.empty", pr)) { pr.remove(); return; }
      const name = ($(".pname", pr) || {}).textContent || "";
      const slot = $(".slot", pr);
      if (slot) slot.setAttribute("data-initial", name.trim().charAt(0).toUpperCase());
      $$(".pbio.empty", pr).forEach(b => b.remove());
    });
    $$(".social.off").forEach(s => s.remove());
    const count = $("#team-count");
    if (count) count.textContent = Math.max(1, $$(".profile").length);
  }

  /* ---------- Cloudflare Web Analytics ---------- */
  if (EXTRAS.cloudflareToken) {
    const s = document.createElement("script");
    s.defer = true;
    s.src = "https://static.cloudflareinsights.com/beacon.min.js";
    s.setAttribute("data-cf-beacon", JSON.stringify({ token: EXTRAS.cloudflareToken }));
    document.body.appendChild(s);
  }
})();
