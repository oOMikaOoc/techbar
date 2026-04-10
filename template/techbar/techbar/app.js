import * as zebar from "https://esm.sh/zebar@3.0";

const leftSection = document.getElementById("left-section");
const centerSection = document.getElementById("center-section");
const rightSection = document.getElementById("right-section");
const AUTO_RETURN_DELAY_MS = 2 * 60 * 1000;
const CLICK_FEEDBACK_MS = 350;

let sysinfoElements = [];
let clockElements = [];

let configData = null;
let currentViewName = null;
let previousViewName = null;
let autoReturnTimerId = null;

const providers = zebar.createProviderGroup({
  cpu: { type: "cpu" },
  memory: { type: "memory" }
});

async function loadConfig() {
  const response = await fetch("./jzone.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Impossible de charger jzone.json (${response.status})`);
  }

  return response.json();
}

function isVisible(item) {
  return item?.visible !== false;
}

function getLabel(item) {
  const icon = item.icon?.trim() ? `${item.icon} ` : "";
  return `${icon}${item.label ?? ""}`.trim();
}

function getItemColor(item) {
  if (!item || typeof item !== "object") {
    return null;
  }

  return item.backgroundColor ?? item.backgroundcolor ?? item.bgColor ?? item.bgcolor ?? null;
}

function setElementBackgroundColor(element, color) {
  if (!element) return;

  if (!color) {
    element.style.removeProperty("--custom-bg-color");
    element.classList.remove("has-custom-bg");
    return;
  }

  element.style.setProperty("--custom-bg-color", color);
  element.classList.add("has-custom-bg");
}

function normalizeArgs(args) {
  if (Array.isArray(args)) {
    return args.filter((arg) => arg !== undefined && arg !== null).map((arg) => String(arg));
  }

  if (typeof args === "string" && args.trim()) {
    return [args.trim()];
  }

  return [];
}

async function runShell(program, args = []) {
  try {
    console.log("[techbar] shell_spawn", { program, args });
    await zebar.shellSpawn(program, args);
  } catch (err) {
    console.error(`Erreur lancement commande "${program}" :`, err);
  }
}

function buildCmdExecArgs(target, args = []) {
  return ["/c", String(target), ...normalizeArgs(args)];
}

async function launchUrl(target) {
  if (!target) return;
  await runShell("explorer.exe", [String(target)]);
}

async function launchFolder(target) {
  if (!target) return;
  await runShell("cmd.exe", ["/c", "start", "", String(target)]);
}

async function launchFile(target) {
  if (!target) return;
  await runShell("explorer.exe", [String(target)]);
}

async function launchApp(item) {
  if (!item?.target) return;
  const args = normalizeArgs(item.args);

  if (args.length) {
    await runShell("cmd.exe", buildCmdExecArgs(item.target, args));
    return;
  }

  await runShell("explorer.exe", [String(item.target)]);
}

async function launchCommand(item) {
  if (!item?.target) return;

  if (item.useShell !== false) {
    await runShell("cmd.exe", ["/c", String(item.target), ...normalizeArgs(item.args)]);
    return;
  }

  await launchApp(item);
}

function clearAutoReturnTimer() {
  if (!autoReturnTimerId) return;
  clearTimeout(autoReturnTimerId);
  autoReturnTimerId = null;
}

function scheduleAutoReturn() {
  clearAutoReturnTimer();

  const defaultView = configData?.defaultView ?? "main";
  if (!currentViewName || currentViewName === defaultView) {
    return;
  }

  autoReturnTimerId = setTimeout(() => {
    previousViewName = defaultView;
    renderView(defaultView);
  }, AUTO_RETURN_DELAY_MS);
}

function triggerButtonFeedback(button, isNavigation = false) {
  if (!button) return;

  button.classList.add("is-launching");

  if (!isNavigation) {
    window.setTimeout(() => {
      button.classList.remove("is-launching");
    }, CLICK_FEEDBACK_MS);
  }
}

async function executeItem(item) {
  switch (item.type) {
    case "url":
      await launchUrl(item.target);
      break;

    case "folder":
      await launchFolder(item.target);
      break;

    case "app":
      await launchApp(item);
      break;

    case "file":
      await launchFile(item.target);
      break;

    case "command":
      await launchCommand(item);
      break;

    case "view":
      if (item.targetView) {
        goToView(item.targetView);
      }
      break;

    case "back":
      goBack();
      break;

    default:
      console.warn("Type non géré :", item);
      break;
  }
}

function createButtonElement(item) {
  const btn = document.createElement("div");
  btn.className = "btn";
  btn.textContent = getLabel(item);
  setElementBackgroundColor(btn, getItemColor(item));

  if (item.type === "view") {
    btn.classList.add("nav-btn");
    if (item.targetView === currentViewName) {
      btn.classList.add("is-active");
    }
  }

  if (item.type === "back") {
    btn.classList.add("back-btn");
  }

  btn.addEventListener("click", async () => {
    const isNavigation = item.type === "view" || item.type === "back";
    triggerButtonFeedback(btn, isNavigation);
    await executeItem(item);
  });

  return btn;
}

function createSpecialElement(item) {
  if (item.type === "sysinfo") {
    const box = document.createElement("div");
    box.className = "info-box";
    box.textContent = "CPU --% | RAM --%";
    sysinfoElements.push(box);
    return box;
  }

  if (item.type === "clock") {
    const box = document.createElement("div");
    box.className = "info-box";
    box.textContent = "--:--";
    clockElements.push(box);
    return box;
  }

  const fallback = document.createElement("div");
  fallback.className = "error-box";
  fallback.textContent = `Type spécial inconnu: ${item.type}`;
  return fallback;
}

function createItemElement(item) {
  if (!isVisible(item)) {
    return null;
  }

  if (item.type === "clock" || item.type === "sysinfo") {
    return createSpecialElement(item);
  }

  return createButtonElement(item);
}

function renderSection(sectionElement, items = []) {
  sectionElement.innerHTML = "";

  items.filter(isVisible).forEach((item) => {
    const element = createItemElement(item);
    if (element) {
      sectionElement.appendChild(element);
    }
  });
}

function renderView(viewName) {
  if (!configData?.views?.[viewName]) {
    console.error(`Vue introuvable: ${viewName}`);
    return;
  }

  currentViewName = viewName;
  sysinfoElements = [];
  clockElements = [];

  const view = configData.views[viewName];

  renderSection(leftSection, view.left ?? []);
  renderSection(centerSection, view.center ?? []);
  renderSection(rightSection, view.right ?? []);

  scheduleAutoReturn();
  updateClock();
  updateSysinfo(providers.outputMap);
}

function goToView(viewName) {
  if (!configData?.views?.[viewName]) {
    console.error(`Vue cible introuvable: ${viewName}`);
    return;
  }

  previousViewName = currentViewName;
  renderView(viewName);
}

function goBack() {
  const fallbackView = configData?.defaultView ?? "main";
  const targetView = previousViewName || fallbackView;

  previousViewName = fallbackView;
  renderView(targetView);
}

function updateClock() {
  if (!clockElements.length) return;

  const now = new Date();
  const text = now.toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit"
  });

  clockElements.forEach((element) => {
    element.textContent = text;
  });
}

function updateSysinfo(outputMap) {
  if (!sysinfoElements.length) return;

  const cpu = outputMap?.cpu?.usage;
  const memory = outputMap?.memory?.usage;

  const cpuText = Number.isFinite(cpu) ? `${Math.round(cpu)}%` : "--%";
  const memoryText = Number.isFinite(memory) ? `${Math.round(memory)}%` : "--%";
  const finalText = `CPU ${cpuText} | RAM ${memoryText}`;

  sysinfoElements.forEach((element) => {
    element.textContent = finalText;
  });
}

async function init() {
  try {
    configData = await loadConfig();

    const defaultView = configData.defaultView || "main";
    renderView(defaultView);

    updateClock();
    setInterval(updateClock, 1000);

    updateSysinfo(providers.outputMap);
    providers.onOutput(() => {
      updateSysinfo(providers.outputMap);
    });
  } catch (error) {
    console.error(error);
    rightSection.innerHTML = `<div class="error-box">Erreur chargement config</div>`;
  }
}

init();
