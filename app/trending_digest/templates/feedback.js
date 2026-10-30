const labels = props.value.labels;
let current = { kind: "idle" };
let returnFocus = null;
let previousOverflow = null;

function setBusy(busy) {
  for (const id of ["save-config", "load-config", "generate-report"]) {
    const button = document.getElementById(id);
    if (button) button.disabled = busy;
  }
}

function restorePage() {
  if (previousOverflow !== null) {
    document.body.style.overflow = previousOverflow;
    previousOverflow = null;
  }
  setBusy(false);
  const target = returnFocus?.isConnected && returnFocus.getClientRects().length
    ? returnFocus : document.getElementById("generate-report");
  target?.focus();
}

function display(value) {
  const dialog = element.querySelector("dialog");
  if (!dialog) return;
  current = value || { kind: "idle" };
  if (current.kind === "idle") {
    if (dialog.open) dialog.close();
    return;
  }
  const busy = current.kind === "loading";
  dialog.dataset.kind = current.kind;
  dialog.setAttribute("role", current.kind === "error" ? "alertdialog" : "dialog");
  dialog.setAttribute("aria-busy", String(busy));
  // Provider/file errors are plain text. Never interpret a message as HTML.
  dialog.querySelector("h2").textContent = current.title;
  dialog.querySelector("p").textContent = current.message;
  const icon = dialog.querySelector(".feedback-icon");
  icon.textContent = busy ? "" : current.kind === "success" ? "✓"
    : current.kind === "error" ? "!" : "i";
  const close = dialog.querySelector("[data-dismiss]");
  close.textContent = current.close;
  close.hidden = busy;
  setBusy(busy);
  if (previousOverflow === null) {
    previousOverflow = document.body.style.overflow;
    returnFocus = document.activeElement;
    document.body.style.overflow = "hidden";
  }
  if (!dialog.dataset.bound) {
    dialog.dataset.bound = "true";
    close.addEventListener("click", () => dialog.close());
    dialog.addEventListener("cancel", event => {
      if (current.kind === "loading") event.preventDefault();
    });
    dialog.addEventListener("close", () => {
      current = { kind: "idle" };
      restorePage();
    });
  }
  if (!dialog.open) dialog.showModal();
  if (!busy) close.focus();
}

window.trendingFeedback = {
  loading(locale, operation) {
    const copy = labels[locale] || labels.en;
    display({ kind: "loading", ...copy[operation], close: copy.close });
  },
  failed(locale) {
    const copy = labels[locale] || labels.en;
    display({ kind: "error", title: copy.error, message: copy.connection, close: copy.close });
  },
};

watch("value", () => display(props.value));
window.addEventListener("offline", () => {
  if (current.kind === "loading") {
    window.trendingFeedback.failed(document.documentElement.lang);
  }
});
display(props.value);
