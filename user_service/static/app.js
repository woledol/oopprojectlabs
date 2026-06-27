const state = {
  token: localStorage.getItem("token") || "",
  user: null,
};

const authView = document.querySelector("#authView");
const workspaceView = document.querySelector("#workspaceView");
const userLabel = document.querySelector("#userLabel");
const logoutButton = document.querySelector("#logoutButton");
const toast = document.querySelector("#toast");
const emptyResult = document.querySelector("#emptyResult");
const resultContent = document.querySelector("#resultContent");
const resultName = document.querySelector("#resultName");
const resultMeta = document.querySelector("#resultMeta");
const resultReason = document.querySelector("#resultReason");
const historyList = document.querySelector("#historyList");

document.querySelector("#registerForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  await submitAuth("/api/register", {
    fullName: form.get("fullName"),
    username: form.get("username"),
    password: form.get("password"),
  });
});

document.querySelector("#loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  await submitAuth("/api/login", {
    username: form.get("username"),
    password: form.get("password"),
  });
});

document.querySelector("#predictForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    const response = await api("/api/predict", {
      method: "POST",
      body: JSON.stringify({ patronymic: form.get("patronymic") }),
    });
    renderResult(response);
    await loadHistory();
  } catch (error) {
    showToast(error.message);
  }
});

logoutButton.addEventListener("click", async () => {
  try {
    await api("/api/logout", { method: "POST" });
  } finally {
    state.token = "";
    state.user = null;
    localStorage.removeItem("token");
    render();
  }
});

async function submitAuth(path, payload) {
  try {
    const response = await api(path, {
      method: "POST",
      skipAuth: true,
      body: JSON.stringify(payload),
    });
    state.token = response.token;
    state.user = response.user;
    localStorage.setItem("token", state.token);
    render();
    await loadHistory();
  } catch (error) {
    showToast(error.message);
  }
}

async function loadMe() {
  if (!state.token) {
    render();
    return;
  }
  try {
    state.user = await api("/api/me");
    render();
    await loadHistory();
  } catch {
    state.token = "";
    localStorage.removeItem("token");
    render();
  }
}

async function loadHistory() {
  const response = await api("/api/history");
  renderHistory(response.items);
}

async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json; charset=utf-8",
    ...(options.headers || {}),
  };
  if (state.token && !options.skipAuth) {
    headers.Authorization = `Bearer ${state.token}`;
  }
  const response = await fetch(path, {
    ...options,
    headers,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || "Ошибка запроса.");
  }
  return data;
}

function render() {
  const isAuthorized = Boolean(state.token && state.user);
  authView.classList.toggle("hidden", isAuthorized);
  workspaceView.classList.toggle("hidden", !isAuthorized);
  logoutButton.classList.toggle("hidden", !isAuthorized);
  userLabel.textContent = isAuthorized ? state.user.fullName : "Гость";
}

function renderResult(result) {
  emptyResult.classList.add("hidden");
  resultContent.classList.remove("hidden");

  if (!result.bestName) {
    resultName.textContent = "Не найдено";
    resultMeta.textContent = `${result.patronymic} · уверенность 0%`;
    resultReason.textContent = "Нет подходящего правила.";
    return;
  }

  const best = result.candidates[0];
  resultName.textContent = result.bestName;
  resultMeta.textContent = `${result.patronymic} · уверенность ${Math.round(
    result.confidence * 100,
  )}%`;
  resultReason.textContent = best.reason;
}

function renderHistory(items) {
  historyList.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("li");
    empty.textContent = "История пуста";
    historyList.append(empty);
    return;
  }
  for (const item of items) {
    const row = document.createElement("li");
    const text = document.createElement("div");
    text.innerHTML = `<strong>${item.patronymic}</strong><br><span>${item.predictedName || "Не найдено"}</span>`;
    const confidence = document.createElement("span");
    confidence.textContent = `${Math.round(item.confidence * 100)}%`;
    row.append(text, confidence);
    historyList.append(row);
  }
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.remove("hidden");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.add("hidden"), 3200);
}

loadMe();
