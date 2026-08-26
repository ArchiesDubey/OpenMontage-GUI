import { el, fmtAgo, getJSON, subscribe, thumbURL } from "/ui/lib.js";

const grid = document.getElementById("grid");
const THEME_KEY = "backlot.theme";
let currentTheme = localStorage.getItem(THEME_KEY) === "light" ? "light" : "dark";

function applyTheme(theme) {
  currentTheme = theme === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = currentTheme;
  localStorage.setItem(THEME_KEY, currentTheme);
}

function renderThemeToggle() {
  const next = currentTheme === "light" ? "dark" : "light";
  return el("button", {
    class: "theme-toggle",
    type: "button",
    title: `Switch to ${next} theme`,
    "aria-label": `Switch to ${next} theme`,
    "aria-pressed": currentTheme === "light" ? "true" : "false",
    onclick: () => {
      applyTheme(next);
      const replacement = renderThemeToggle();
      document.querySelector(".theme-toggle").replaceWith(replacement);
    },
  }, el("span", { class: "theme-toggle-icon", "aria-hidden": "true" }, currentTheme === "light" ? "☾" : "☀"));
}

applyTheme(currentTheme);
document.getElementById("liveBadge").before(renderThemeToggle());

function miniRail(states) {
  const rail = el("div", { class: "mini-rail" });
  for (const s of states) {
    const cls = s.status === "completed" ? "d"
      : s.status === "in_progress" ? "a"
      : s.status === "awaiting_human" ? "w" : "";
    rail.append(el("i", { class: cls, title: `${s.name}: ${s.status}` }));
  }
  return rail;
}

function card(p) {
  const poster = el("div", { class: "lib-poster" });
  if (p.poster) {
    poster.append(el("img", { src: thumbURL(p.project_id, p.poster, 640), loading: "lazy", alt: "" }));
  } else {
    poster.append(el("span", { class: "lp-txt" }, "NO MEDIA YET"));
  }
  if (p.live && p.active_stage) {
    poster.append(el("span", { class: "lp-live" },
      el("span", { class: "dot" }),
      p.awaiting_human ? "◈ AWAITING YOU" : `LIVE · ${p.active_stage.toUpperCase()}`));
  } else if (p.awaiting_human) {
    poster.append(el("span", { class: "lp-live" }, "◈ AWAITING YOU"));
  }

  const meta = el("div", { class: "lb-meta" },
    el("span", { class: "chip" }, p.pipeline_type || "unknown"),
    p.scene_count ? el("span", { class: "chip" }, `${p.scene_count} scenes`) : null,
    p.render_count ? el("span", { class: "chip" }, `${p.render_count} renders`) : null,
    el("span", { class: "when" }, fmtAgo(p.last_activity)),
  );

  const staticSuffix = new URLSearchParams(location.search).has("static") ? "?static=1" : "";
  return el("a", { class: `lib-card${p.live ? " live-card" : ""}`, href: `/p/${p.project_id}${staticSuffix}`, style: "text-decoration:none;color:inherit" },
    poster,
    el("div", { class: "lib-body" },
      el("h3", {}, (p.title || p.project_id).toUpperCase()),
      meta,
      p.stage_states.length ? miniRail(p.stage_states) : null,
    ),
  );
}

async function render() {
  const projects = await getJSON("/api/projects");
  document.getElementById("count").textContent = `${projects.length} projects`;
  const liveCount = projects.filter((p) => p.live).length;
  const badge = document.getElementById("liveBadge");
  badge.classList.toggle("idle", liveCount === 0);
  document.getElementById("liveText").textContent = liveCount ? `${liveCount} LIVE` : "IDLE";
  grid.innerHTML = "";
  document.getElementById("empty").style.display = projects.length ? "none" : "block";
  for (const p of projects) grid.append(card(p));
}

render().catch(console.error);
if (!new URLSearchParams(location.search).has("static")) {
  subscribe("/api/library/events", () => render().catch(console.error));
}

// ---------------------------------------------------------------------------
// kickoff — start a production the way you'd brief the agent in chat
// ---------------------------------------------------------------------------

import { postJSON } from "/ui/lib.js";

let pipelines = null;
let agentMenu = null;

function slugify(t) {
  return (t.toLowerCase().match(/[a-z0-9]+/g) || []).join("-").slice(0, 60) || "production";
}

function kickField(label, input, hint) {
  return el("label", { class: "kick-field" },
    el("span", { class: "kick-label" }, label),
    input,
    hint ? el("span", { class: "gate-meta" }, hint) : null,
  );
}

async function openKickoff() {
  if (!pipelines) {
    try {
      const [p, a] = await Promise.all([
        getJSON("/api/pipelines"), getJSON("/api/agents"),
      ]);
      pipelines = p.pipelines;
      agentMenu = a.agents;
    } catch (err) { alert(`Could not load pipelines: ${err.message}`); return; }
  }

  const titleIn = el("input", {
    class: "kick-input", type: "text", placeholder: "e.g. Why Octopuses Are Basically Aliens",
  });
  const idHint = el("span", { class: "gate-meta" }, "");
  titleIn.addEventListener("input", () => {
    idHint.textContent = `project id: ${slugify(titleIn.value)}`;
  });
  const idIn = el("input", {
    class: "kick-input", type: "text", placeholder: "auto from title",
  });

  const pipeSel = el("select", { class: "agent-pick" });
  for (const p of pipelines || []) {
    pipeSel.append(el("option", { value: p.id },
      `${p.label} · ${p.stages} stages${p.description ? "" : ""}`));
  }
  const pipeDesc = el("div", { class: "kick-desc" },
    ((pipelines || [])[0] || {}).description || "");
  pipeSel.addEventListener("change", () => {
    const p = (pipelines || []).find((x) => x.id === pipeSel.value);
    pipeDesc.textContent = p ? p.description : "";
  });

  const briefTa = el("textarea", {
    class: "kick-input", rows: "5",
    placeholder: "Brief it like you'd say it to the agent — topic, angle, tone, "
      + "length, references…\n\nThe agent reads this before its first stage and "
      + "will come back at the first approval gate.",
  });

  const agentSel = el("select", { class: "agent-pick" });
  if (!agentMenu) agentSel.append(el("option", { value: "auto" }, "AUTO"));
  else {
    const ready = agentMenu.filter((a) => a.available);
    agentSel.append(el("option", { value: "auto" },
      `AUTO${ready.length ? ` · ${ready[0].label}` : ""}`));
    for (const a of agentMenu) {
      agentSel.append(el("option", {
        value: a.id, disabled: a.available ? null : "disabled",
        title: a.reason || a.hint,
      }, a.available ? a.label : `${a.label} — ${a.reason}`));
    }
  }

  const errLine = el("div", { class: "kick-error", style: "display:none" });
  const busy = { on: false };
  async function submit(launch) {
    if (busy.on) return;
    busy.on = true;
    errLine.style.display = "none";
    try {
      const res = await postJSON("/api/projects", {
        title: titleIn.value,
        project_id: idIn.value.trim() || undefined,
        pipeline_type: pipeSel.value,
        brief: briefTa.value,
        launch,
        agent: agentSel.value,
      });
      location.href = `/p/${res.project.project_id}`;
    } catch (err) {
      errLine.textContent = err.message;
      errLine.style.display = "block";
      busy.on = false;
    }
  }

  const overlay = el("div", { class: "kick-overlay" },
    el("div", { class: "kick-modal" },
      el("div", { class: "approval-eyebrow" }, "NEW PRODUCTION"),
      el("h2", { class: "kick-title" }, "Brief it. Pick a pipeline. Go."),
      kickField("TITLE", titleIn),
      kickField("PROJECT ID", idIn, "leave blank to derive from the title"),
      kickField("PIPELINE", pipeSel),
      pipeDesc,
      kickField("CREATIVE BRIEF", briefTa),
      kickField("AGENT", agentSel),
      errLine,
      el("div", { class: "kick-actions" },
        el("button", { class: "gate-changes kick-btn", type: "button",
          onclick: () => overlay.remove() }, "CANCEL"),
        el("button", { class: "kick-btn ghost", type: "button",
          onclick: () => submit(false) }, "CREATE ONLY"),
        el("button", { class: "gate-approve kick-btn primary", type: "button",
          onclick: () => submit(true) }, "CREATE & RUN AGENT ▶"),
      ),
    ),
  );
  overlay.addEventListener("click", (e) => { if (e.target === overlay) overlay.remove(); });
  document.body.append(overlay);
  titleIn.focus();
}

document.getElementById("newBtn").addEventListener("click", openKickoff);
