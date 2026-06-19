const QUESTION_BANK_PATH = "./lituk_questions_422.json";
const STUDY_CONTENT_PATH = "./study_content.json";
const STUDY_PLAN_PATH = "./study_plan.json";
const TEST_DURATION_SECONDS = 45 * 60;
const PASS_MARK = 18;
const TOTAL_QUESTIONS = 24;
const ACTIVE_WINDOW_DAYS = 30;

const STORAGE_KEYS = {
  users: "lituk.users.v1",
  session: "lituk.session.v1",
  mockResults: "lituk.mock.results.v1",
  studyProgress: "lituk.study.progress.v1",
  studyPlan: "lituk.study.plan.v1",
};

const TOPIC_REQUIREMENTS = {
  "The values and principles of the UK": 1,
  "What is the UK?": 1,
  "A long and illustrious history": 8,
  "A modern, thriving society": 7,
  "The UK government, the law and your role": 7,
};

const appState = {
  currentUserId: null,
  users: [],
  bank: [],
  mock: {
    testQuestions: [],
    selectedAnswers: {},
    timeLeft: TEST_DURATION_SECONDS,
    timerId: null,
    submitted: false,
  },
  study: {
    loaded: false,
    topicNames: {},
    pages: [],
    planItems: [],
    currentPageId: null,
    pageStartedAt: null,
  },
};

const authSection = document.getElementById("auth-section");
const appShell = document.getElementById("app-shell");
const activeBanner = document.getElementById("active-banner");
const authMessage = document.getElementById("auth-message");
const showLoginBtn = document.getElementById("show-login");
const showRegisterBtn = document.getElementById("show-register");
const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");
const logoutBtn = document.getElementById("logout-btn");
const navLinks = Array.from(document.querySelectorAll(".nav-link"));
const profileMeta = document.getElementById("profile-meta");
const passwordForm = document.getElementById("password-form");
const profileMessage = document.getElementById("profile-message");

const dashDays = document.getElementById("dash-days");
const dashAttempts = document.getElementById("dash-attempts");
const dashBest = document.getElementById("dash-best");
const dashLatest = document.getElementById("dash-latest");

const studyPlanList = document.getElementById("study-plan-list");
const studyTopicFilter = document.getElementById("study-topic-filter");
const studyTopicProgress = document.getElementById("study-topic-progress");
const studyPageList = document.getElementById("study-page-list");
const studyReader = document.getElementById("study-reader");
const studyPageTitle = document.getElementById("study-page-title");
const studyPageMeta = document.getElementById("study-page-meta");
const studyPageContent = document.getElementById("study-page-content");
const studyPrevBtn = document.getElementById("study-prev-btn");
const studyNextBtn = document.getElementById("study-next-btn");
const studyCompleteBtn = document.getElementById("study-complete-btn");
const resumeStudyBtn = document.getElementById("resume-study-btn");

const startBtn = document.getElementById("start-btn");
const statusCard = document.getElementById("status-card");
const timerEl = document.getElementById("timer");
const answeredCountEl = document.getElementById("answered-count");
const liveScoreEl = document.getElementById("live-score");
const progressFillEl = document.getElementById("progress-fill");
const progressTextEl = document.getElementById("progress-text");
const jumpBtn = document.getElementById("jump-btn");
const testSection = document.getElementById("test-section");
const testForm = document.getElementById("test-form");
const submitBtn = document.getElementById("submit-btn");
const resultSection = document.getElementById("result-section");
const resultSummary = document.getElementById("result-summary");
const topicAnalysis = document.getElementById("topic-analysis");
const answerReview = document.getElementById("answer-review");

bootstrap();

function bootstrap() {
  appState.users = loadJson(STORAGE_KEYS.users, []);
  pruneExpiredUsers();
  appState.currentUserId = loadJson(STORAGE_KEYS.session, null);

  if (!findCurrentUser()) {
    setSession(null);
    showAuth();
  } else {
    showApp();
  }

  wireEvents();
}

function wireEvents() {
  showLoginBtn.addEventListener("click", () => switchAuthTab("login"));
  showRegisterBtn.addEventListener("click", () => switchAuthTab("register"));

  loginForm.addEventListener("submit", onLoginSubmit);
  registerForm.addEventListener("submit", onRegisterSubmit);
  logoutBtn.addEventListener("click", logout);
  passwordForm.addEventListener("submit", onPasswordChangeSubmit);

  navLinks.forEach((btn) => {
    btn.addEventListener("click", () => switchView(btn.dataset.view));
  });

  startBtn.addEventListener("click", startNewTest);
  submitBtn.addEventListener("click", () => finalizeTest(false));
  jumpBtn.addEventListener("click", scrollToFirstUnanswered);

  studyTopicFilter.addEventListener("change", renderStudyPageList);
  resumeStudyBtn.addEventListener("click", resumeStudyPage);
  studyPrevBtn.addEventListener("click", () => moveStudyPage(-1));
  studyNextBtn.addEventListener("click", () => moveStudyPage(1));
  studyCompleteBtn.addEventListener("click", markCurrentPageCompleted);
}

function switchAuthTab(tab) {
  const isLogin = tab === "login";
  loginForm.classList.toggle("hidden", !isLogin);
  registerForm.classList.toggle("hidden", isLogin);
  showLoginBtn.classList.toggle("active", isLogin);
  showRegisterBtn.classList.toggle("active", !isLogin);
  authMessage.textContent = "";
}

function onRegisterSubmit(event) {
  event.preventDefault();
  const name = document.getElementById("register-name").value.trim();
  const email = document.getElementById("register-email").value.trim().toLowerCase();
  const password = document.getElementById("register-password").value;

  if (!name || !email || password.length < 8) {
    authMessage.textContent = "Provide valid name, email, and a password with 8+ characters.";
    return;
  }

  if (appState.users.some((u) => u.email === email)) {
    authMessage.textContent = "This email is already registered. Please login.";
    return;
  }

  const now = Date.now();
  const newUser = {
    id: crypto.randomUUID(),
    fullName: name,
    email,
    password,
    createdAt: now,
    activeUntil: now + ACTIVE_WINDOW_DAYS * 24 * 60 * 60 * 1000,
  };

  appState.users.push(newUser);
  saveUsers();
  setSession(newUser.id);

  registerForm.reset();
  authMessage.textContent = "Registration successful.";
  showApp();
}

function onLoginSubmit(event) {
  event.preventDefault();
  const email = document.getElementById("login-email").value.trim().toLowerCase();
  const password = document.getElementById("login-password").value;

  const user = appState.users.find((u) => u.email === email && u.password === password);
  if (!user) {
    authMessage.textContent = "Invalid email or password.";
    return;
  }

  if (Date.now() > user.activeUntil) {
    removeUser(user.id);
    authMessage.textContent = "Account expired and removed. Please register again.";
    return;
  }

  setSession(user.id);
  loginForm.reset();
  authMessage.textContent = "";
  showApp();
}

function onPasswordChangeSubmit(event) {
  event.preventDefault();
  const oldPassword = document.getElementById("old-password").value;
  const newPassword = document.getElementById("new-password").value;
  const user = findCurrentUser();

  if (!user) {
    logout();
    return;
  }

  if (oldPassword !== user.password) {
    profileMessage.textContent = "Current password does not match.";
    return;
  }

  if (newPassword.length < 8) {
    profileMessage.textContent = "New password must be at least 8 characters.";
    return;
  }

  user.password = newPassword;
  saveUsers();
  passwordForm.reset();
  profileMessage.textContent = "Password updated successfully.";
}

function showAuth() {
  authSection.classList.remove("hidden");
  appShell.classList.add("hidden");
  activeBanner.classList.add("hidden");
  clearInterval(appState.mock.timerId);
  switchAuthTab("login");
}

function showApp() {
  const user = findCurrentUser();
  if (!user) {
    showAuth();
    return;
  }

  const remaining = getRemainingDays(user.activeUntil);
  if (remaining <= 0) {
    removeUser(user.id);
    authMessage.textContent = "Your 30-day window expired and account data was removed.";
    showAuth();
    return;
  }

  authSection.classList.add("hidden");
  appShell.classList.remove("hidden");
  activeBanner.classList.remove("hidden");
  activeBanner.textContent = `${remaining} day${remaining === 1 ? "" : "s"} remaining in your active access window.`;

  switchView("dashboard");
  renderProfile();
  renderDashboard();
}

function switchView(viewName) {
  if (viewName !== "study") {
    closeActiveStudyPage();
  }

  const views = ["dashboard", "study", "practice", "mock", "profile"];
  views.forEach((name) => {
    const panel = document.getElementById(`view-${name}`);
    panel.classList.toggle("hidden", name !== viewName);
  });

  navLinks.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === viewName);
  });

  if (viewName === "dashboard") {
    renderDashboard();
  }

  if (viewName === "study") {
    ensureStudyData().then(() => {
      renderStudyView();
    });
  }

  if (viewName !== "mock") {
    clearInterval(appState.mock.timerId);
  }
}

function renderProfile() {
  const user = findCurrentUser();
  if (!user) {
    return;
  }

  const joined = new Date(user.createdAt).toLocaleDateString();
  const activeUntil = new Date(user.activeUntil).toLocaleDateString();
  profileMeta.textContent = `${user.fullName} (${user.email}) | Joined: ${joined} | Active until: ${activeUntil}`;
  profileMessage.textContent = "";
}

function renderDashboard() {
  const user = findCurrentUser();
  if (!user) {
    return;
  }

  const userResults = loadMockResults().filter((row) => row.userId === user.id);
  dashDays.textContent = String(getRemainingDays(user.activeUntil));
  dashAttempts.textContent = String(userResults.length);

  if (userResults.length === 0) {
    dashBest.textContent = "-";
    dashLatest.textContent = "No attempts yet";
    return;
  }

  const best = Math.max(...userResults.map((r) => r.correct));
  const latest = userResults[userResults.length - 1];
  dashBest.textContent = `${best}/${TOTAL_QUESTIONS}`;
  dashLatest.textContent = `${latest.correct}/${TOTAL_QUESTIONS} (${latest.pass ? "Pass" : "Fail"})`;
}

function logout() {
  closeActiveStudyPage();
  setSession(null);
  clearInterval(appState.mock.timerId);
  resetMockState();
  showAuth();
}

function findCurrentUser() {
  if (!appState.currentUserId) {
    return null;
  }
  return appState.users.find((u) => u.id === appState.currentUserId) || null;
}

function setSession(userId) {
  appState.currentUserId = userId;
  localStorage.setItem(STORAGE_KEYS.session, JSON.stringify(userId));
}

function saveUsers() {
  localStorage.setItem(STORAGE_KEYS.users, JSON.stringify(appState.users));
}

function removeUser(userId) {
  appState.users = appState.users.filter((u) => u.id !== userId);
  saveUsers();

  const nextResults = loadMockResults().filter((r) => r.userId !== userId);
  localStorage.setItem(STORAGE_KEYS.mockResults, JSON.stringify(nextResults));

  const allProgress = loadJson(STORAGE_KEYS.studyProgress, {});
  delete allProgress[userId];
  localStorage.setItem(STORAGE_KEYS.studyProgress, JSON.stringify(allProgress));

  const allPlan = loadJson(STORAGE_KEYS.studyPlan, {});
  delete allPlan[userId];
  localStorage.setItem(STORAGE_KEYS.studyPlan, JSON.stringify(allPlan));

  if (appState.currentUserId === userId) {
    setSession(null);
  }
}

function pruneExpiredUsers() {
  const now = Date.now();
  const activeUsers = appState.users.filter((u) => now <= u.activeUntil);
  if (activeUsers.length !== appState.users.length) {
    const activeIds = new Set(activeUsers.map((u) => u.id));
    const keptResults = loadMockResults().filter((r) => activeIds.has(r.userId));
    const keptProgress = Object.fromEntries(
      Object.entries(loadJson(STORAGE_KEYS.studyProgress, {})).filter(([userId]) => activeIds.has(userId))
    );
    const keptPlan = Object.fromEntries(
      Object.entries(loadJson(STORAGE_KEYS.studyPlan, {})).filter(([userId]) => activeIds.has(userId))
    );
    appState.users = activeUsers;
    saveUsers();
    localStorage.setItem(STORAGE_KEYS.mockResults, JSON.stringify(keptResults));
    localStorage.setItem(STORAGE_KEYS.studyProgress, JSON.stringify(keptProgress));
    localStorage.setItem(STORAGE_KEYS.studyPlan, JSON.stringify(keptPlan));
  }
}

function getRemainingDays(activeUntilMs) {
  const diff = activeUntilMs - Date.now();
  return Math.max(0, Math.ceil(diff / (24 * 60 * 60 * 1000)));
}

function loadMockResults() {
  return loadJson(STORAGE_KEYS.mockResults, []);
}

function saveMockResult(result) {
  const current = loadMockResults();
  current.push(result);
  localStorage.setItem(STORAGE_KEYS.mockResults, JSON.stringify(current));
}

function loadJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

async function ensureStudyData() {
  if (appState.study.loaded) {
    return;
  }

  const [studyResp, planResp] = await Promise.all([fetch(STUDY_CONTENT_PATH), fetch(STUDY_PLAN_PATH)]);
  if (!studyResp.ok) {
    throw new Error(`Could not load ${STUDY_CONTENT_PATH}`);
  }
  if (!planResp.ok) {
    throw new Error(`Could not load ${STUDY_PLAN_PATH}`);
  }

  const studyData = await studyResp.json();
  const planData = await planResp.json();

  appState.study.topicNames = studyData.topic_names || {};
  appState.study.pages = (studyData.pages || []).sort((a, b) => {
    if (a.topic_code !== b.topic_code) {
      return a.topic_code - b.topic_code;
    }
    return a.sequence_no - b.sequence_no;
  });
  appState.study.planItems = (planData.items || []).sort((a, b) => a.order_no - b.order_no);
  appState.study.loaded = true;

  initializeStudyFilter();
}

function initializeStudyFilter() {
  if (studyTopicFilter.options.length > 0) {
    return;
  }

  const allOption = document.createElement("option");
  allOption.value = "all";
  allOption.textContent = "All Topics";
  studyTopicFilter.appendChild(allOption);

  Object.entries(appState.study.topicNames).forEach(([code, name]) => {
    const option = document.createElement("option");
    option.value = String(code);
    option.textContent = `Topic ${code}: ${name}`;
    studyTopicFilter.appendChild(option);
  });
}

function renderStudyView() {
  renderStudyPlan();
  renderStudyPageList();

  const progress = getUserStudyProgress();
  if (progress.lastPageId && appState.study.pages.some((p) => p.id === progress.lastPageId)) {
    openStudyPage(progress.lastPageId, false);
  }
}

function renderStudyPlan() {
  const plan = getUserStudyPlan();
  studyPlanList.innerHTML = "";

  appState.study.planItems.forEach((item) => {
    const row = document.createElement("label");
    row.className = "study-plan-item";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = Boolean(plan[item.id]);
    checkbox.addEventListener("change", () => {
      const latest = getUserStudyPlan();
      latest[item.id] = checkbox.checked;
      setUserStudyPlan(latest);
    });

    const textWrap = document.createElement("span");
    const weekText = item.week_no > 0 ? `Week ${item.week_no}` : "Prep";
    textWrap.textContent = `${weekText}: ${item.title}`;

    row.appendChild(checkbox);
    row.appendChild(textWrap);
    studyPlanList.appendChild(row);
  });
}

function renderStudyPageList() {
  const filter = studyTopicFilter.value || "all";
  const progress = getUserStudyProgress();

  const selectedPages = appState.study.pages.filter((page) => {
    if (filter === "all") {
      return true;
    }
    return String(page.topic_code) === filter;
  });

  studyPageList.innerHTML = "";
  selectedPages.forEach((page) => {
    const pageProgress = progress.pages[page.id] || {};
    const status = pageProgress.completedAt ? "Completed" : pageProgress.visits ? "Visited" : "Not started";

    const button = document.createElement("button");
    button.type = "button";
    button.className = "study-page-item";
    button.addEventListener("click", () => openStudyPage(page.id, true));

    button.innerHTML = `
      <strong>Topic ${page.topic_code}.${page.sequence_no}: ${page.title}</strong>
      <span>${status}</span>
    `;

    studyPageList.appendChild(button);
  });

  renderStudyTopicProgress(selectedPages, progress);
}

function renderStudyTopicProgress(selectedPages, progress) {
  if (selectedPages.length === 0) {
    studyTopicProgress.textContent = "No pages for selected topic.";
    return;
  }

  const completed = selectedPages.filter((page) => progress.pages[page.id]?.completedAt).length;
  const pct = Math.round((completed / selectedPages.length) * 100);
  studyTopicProgress.textContent = `${completed}/${selectedPages.length} pages completed (${pct}%).`;
}

function openStudyPage(pageId, fromUserAction) {
  closeActiveStudyPage();

  const page = appState.study.pages.find((p) => p.id === pageId);
  if (!page) {
    return;
  }

  appState.study.currentPageId = pageId;
  appState.study.pageStartedAt = Date.now();

  const progress = getUserStudyProgress();
  const entry = progress.pages[pageId] || { visits: 0, timeSpentSeconds: 0 };
  entry.visits = (entry.visits || 0) + 1;
  entry.lastViewedAt = Date.now();
  progress.pages[pageId] = entry;
  progress.lastPageId = pageId;
  setUserStudyProgress(progress);

  studyReader.classList.remove("hidden");
  studyPageTitle.textContent = page.title;
  studyPageMeta.textContent = `Topic ${page.topic_code}.${page.sequence_no} | Source: ${page.source_file}`;

  studyPageContent.innerHTML = "";
  (page.content_blocks || []).forEach((block) => {
    if (block.type === "bullet") {
      const li = document.createElement("li");
      li.textContent = block.text;

      let list = studyPageContent.querySelector("ul");
      if (!list) {
        list = document.createElement("ul");
        studyPageContent.appendChild(list);
      }
      list.appendChild(li);
      return;
    }

    const paragraph = document.createElement("p");
    paragraph.textContent = block.text;
    studyPageContent.appendChild(paragraph);
  });

  updateStudyReaderButtons();
  if (fromUserAction) {
    studyReader.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  renderStudyPageList();
}

function updateStudyReaderButtons() {
  const index = appState.study.pages.findIndex((page) => page.id === appState.study.currentPageId);
  studyPrevBtn.disabled = index <= 0;
  studyNextBtn.disabled = index < 0 || index >= appState.study.pages.length - 1;

  const progress = getUserStudyProgress();
  const isCompleted = Boolean(progress.pages[appState.study.currentPageId]?.completedAt);
  studyCompleteBtn.textContent = isCompleted ? "Completed" : "Mark as Completed";
  studyCompleteBtn.disabled = isCompleted;
}

function moveStudyPage(delta) {
  const index = appState.study.pages.findIndex((page) => page.id === appState.study.currentPageId);
  if (index < 0) {
    return;
  }
  const nextIndex = index + delta;
  if (nextIndex < 0 || nextIndex >= appState.study.pages.length) {
    return;
  }

  openStudyPage(appState.study.pages[nextIndex].id, true);
}

function markCurrentPageCompleted() {
  if (!appState.study.currentPageId) {
    return;
  }

  const progress = getUserStudyProgress();
  const entry = progress.pages[appState.study.currentPageId] || { visits: 0, timeSpentSeconds: 0 };
  entry.completedAt = Date.now();
  progress.pages[appState.study.currentPageId] = entry;
  setUserStudyProgress(progress);

  updateStudyReaderButtons();
  renderStudyPageList();
}

function resumeStudyPage() {
  const progress = getUserStudyProgress();
  if (progress.lastPageId) {
    openStudyPage(progress.lastPageId, true);
    return;
  }

  if (appState.study.pages.length > 0) {
    openStudyPage(appState.study.pages[0].id, true);
  }
}

function closeActiveStudyPage() {
  if (!appState.study.currentPageId || !appState.study.pageStartedAt) {
    return;
  }

  const elapsed = Math.max(1, Math.round((Date.now() - appState.study.pageStartedAt) / 1000));
  const progress = getUserStudyProgress();
  const entry = progress.pages[appState.study.currentPageId] || { visits: 0, timeSpentSeconds: 0 };
  entry.timeSpentSeconds = (entry.timeSpentSeconds || 0) + elapsed;
  entry.lastViewedAt = Date.now();
  progress.pages[appState.study.currentPageId] = entry;
  setUserStudyProgress(progress);

  appState.study.pageStartedAt = null;
}

function getUserStudyProgress() {
  const user = findCurrentUser();
  if (!user) {
    return { pages: {}, lastPageId: null };
  }

  const all = loadJson(STORAGE_KEYS.studyProgress, {});
  return all[user.id] || { pages: {}, lastPageId: null };
}

function setUserStudyProgress(progress) {
  const user = findCurrentUser();
  if (!user) {
    return;
  }

  const all = loadJson(STORAGE_KEYS.studyProgress, {});
  all[user.id] = progress;
  localStorage.setItem(STORAGE_KEYS.studyProgress, JSON.stringify(all));
}

function getUserStudyPlan() {
  const user = findCurrentUser();
  if (!user) {
    return {};
  }

  const all = loadJson(STORAGE_KEYS.studyPlan, {});
  return all[user.id] || {};
}

function setUserStudyPlan(planState) {
  const user = findCurrentUser();
  if (!user) {
    return;
  }

  const all = loadJson(STORAGE_KEYS.studyPlan, {});
  all[user.id] = planState;
  localStorage.setItem(STORAGE_KEYS.studyPlan, JSON.stringify(all));
}

async function startNewTest() {
  clearInterval(appState.mock.timerId);
  resetMockState();

  try {
    if (appState.bank.length === 0) {
      const response = await fetch(QUESTION_BANK_PATH);
      if (!response.ok) {
        throw new Error(`Could not load ${QUESTION_BANK_PATH}`);
      }
      appState.bank = await response.json();
    }

    appState.mock.testQuestions = buildMockTest(appState.bank);
    renderTest();
    startTimer();

    statusCard.classList.remove("hidden");
    testSection.classList.remove("hidden");
    resultSection.classList.add("hidden");

    updateLiveMetrics();
  } catch (error) {
    window.alert(`Failed to start test: ${error.message}`);
  }
}

function resetMockState() {
  appState.mock.testQuestions = [];
  appState.mock.selectedAnswers = {};
  appState.mock.timeLeft = TEST_DURATION_SECONDS;
  appState.mock.submitted = false;

  testForm.innerHTML = "";
  topicAnalysis.innerHTML = "";
  answerReview.innerHTML = "";
  resultSummary.innerHTML = "";

  statusCard.classList.add("hidden");
  testSection.classList.add("hidden");
  resultSection.classList.add("hidden");
}

function buildMockTest(allQuestions) {
  const grouped = groupByTopic(allQuestions);
  const selected = [];

  for (const [topic, requiredCount] of Object.entries(TOPIC_REQUIREMENTS)) {
    const pool = grouped[topic] || [];
    if (pool.length < requiredCount) {
      throw new Error(`Not enough questions in topic '${topic}'. Needed ${requiredCount}, found ${pool.length}.`);
    }

    const shuffled = shuffleArray([...pool]);
    selected.push(...shuffled.slice(0, requiredCount));
  }

  const finalSet = shuffleArray(selected);
  if (finalSet.length !== TOTAL_QUESTIONS) {
    throw new Error(`Expected ${TOTAL_QUESTIONS} questions but selected ${finalSet.length}.`);
  }

  return finalSet;
}

function groupByTopic(questions) {
  return questions.reduce((acc, q) => {
    if (!acc[q.topic]) {
      acc[q.topic] = [];
    }
    acc[q.topic].push(q);
    return acc;
  }, {});
}

function renderTest() {
  testForm.innerHTML = "";

  appState.mock.testQuestions.forEach((q, qIndex) => {
    const qWrap = document.createElement("article");
    qWrap.className = "question";

    const qTitle = document.createElement("h3");
    qTitle.textContent = `${qIndex + 1}. ${q.question.text.replace(/\r\n/g, " ")}`;

    const optionWrap = document.createElement("div");
    optionWrap.className = "options";

    q.answers.forEach((ans, aIndex) => {
      const id = `q${qIndex}_a${aIndex}`;
      const label = document.createElement("label");
      label.className = "option-label";
      label.setAttribute("for", id);

      const input = document.createElement("input");
      input.type = "radio";
      input.name = `q-${qIndex}`;
      input.id = id;
      input.value = String(aIndex);
      input.addEventListener("change", () => {
        appState.mock.selectedAnswers[qIndex] = aIndex;
        updateLiveMetrics();
      });

      const text = document.createElement("span");
      text.textContent = ans.text;

      label.appendChild(input);
      label.appendChild(text);
      optionWrap.appendChild(label);
    });

    qWrap.appendChild(qTitle);
    qWrap.appendChild(optionWrap);
    testForm.appendChild(qWrap);
  });
}

function startTimer() {
  renderTimer();
  appState.mock.timerId = setInterval(() => {
    appState.mock.timeLeft -= 1;
    renderTimer();

    if (appState.mock.timeLeft <= 0) {
      finalizeTest(true);
    }
  }, 1000);
}

function renderTimer() {
  const mins = String(Math.max(0, Math.floor(appState.mock.timeLeft / 60))).padStart(2, "0");
  const secs = String(Math.max(0, appState.mock.timeLeft % 60)).padStart(2, "0");
  timerEl.textContent = `${mins}:${secs}`;
  timerEl.classList.toggle("warn", appState.mock.timeLeft <= 300);
}

function updateLiveMetrics() {
  const answeredCount = Object.keys(appState.mock.selectedAnswers).length;
  answeredCountEl.textContent = `${answeredCount} / ${TOTAL_QUESTIONS}`;

  const currentCorrect = appState.mock.testQuestions.reduce((acc, q, idx) => {
    const chosen = appState.mock.selectedAnswers[idx];
    if (chosen === undefined) {
      return acc;
    }
    return acc + (q.answers[chosen]?.correct ? 1 : 0);
  }, 0);

  liveScoreEl.textContent = String(currentCorrect);

  const completionPct = Math.round((answeredCount / TOTAL_QUESTIONS) * 100);
  progressFillEl.style.width = `${completionPct}%`;
  progressTextEl.textContent = `${completionPct}% completed`;

  const unanswered = TOTAL_QUESTIONS - answeredCount;
  submitBtn.textContent = unanswered > 0 ? `Submit Test (${unanswered} left)` : "Submit Test";
}

function finalizeTest(fromTimeout) {
  if (appState.mock.submitted) {
    return;
  }

  if (!fromTimeout) {
    const unanswered = TOTAL_QUESTIONS - Object.keys(appState.mock.selectedAnswers).length;
    if (unanswered > 0) {
      const proceed = window.confirm(`You still have ${unanswered} unanswered question(s). Submit anyway?`);
      if (!proceed) {
        scrollToFirstUnanswered();
        return;
      }
    }
  }

  appState.mock.submitted = true;
  clearInterval(appState.mock.timerId);

  const scored = scoreTest(appState.mock.testQuestions, appState.mock.selectedAnswers);
  renderResults(scored, fromTimeout);

  const user = findCurrentUser();
  if (user) {
    saveMockResult({
      userId: user.id,
      correct: scored.correct,
      total: scored.total,
      pass: scored.pass,
      percentage: scored.percentage,
      createdAt: Date.now(),
    });
  }

  renderDashboard();
  resultSection.classList.remove("hidden");
  testSection.classList.add("hidden");
}

function scrollToFirstUnanswered() {
  const firstUnansweredIndex = appState.mock.testQuestions.findIndex(
    (_, idx) => appState.mock.selectedAnswers[idx] === undefined
  );
  if (firstUnansweredIndex === -1) {
    return;
  }

  const firstUnansweredQuestion = testForm.children[firstUnansweredIndex];
  if (!firstUnansweredQuestion) {
    return;
  }

  firstUnansweredQuestion.scrollIntoView({ behavior: "smooth", block: "start" });
}

function scoreTest(questions, selectedAnswers) {
  let correct = 0;
  const topicStats = {};
  const review = [];

  for (let i = 0; i < questions.length; i += 1) {
    const question = questions[i];
    const selectedIndex = selectedAnswers[i];
    const selectedAnswer = selectedIndex !== undefined ? question.answers[selectedIndex] : null;
    const correctAnswer = question.answers.find((a) => a.correct);
    const isCorrect = Boolean(selectedAnswer && selectedAnswer.correct);

    if (isCorrect) {
      correct += 1;
    }

    if (!topicStats[question.topic]) {
      topicStats[question.topic] = { correct: 0, total: 0 };
    }

    topicStats[question.topic].total += 1;
    if (isCorrect) {
      topicStats[question.topic].correct += 1;
    }

    review.push({
      questionText: question.question.text,
      topic: question.topic,
      selected: selectedAnswer ? selectedAnswer.text : "No answer",
      correct: correctAnswer ? correctAnswer.text : "Unknown",
      isCorrect,
      explanation: question.explanation?.text || "No explanation available.",
    });
  }

  return {
    correct,
    total: questions.length,
    pass: correct >= PASS_MARK,
    percentage: Math.round((correct / questions.length) * 100),
    topicStats,
    review,
  };
}

function renderResults(scored, fromTimeout) {
  const statusClass = scored.pass ? "pass" : "fail";
  const statusText = scored.pass ? "PASS" : "FAIL";
  const timeoutText = fromTimeout ? "Time expired. Test auto-submitted." : "Test submitted.";

  resultSummary.innerHTML = `
    <p>${timeoutText}</p>
    <p><strong>Score:</strong> ${scored.correct} / ${scored.total} (${scored.percentage}%)</p>
    <p><strong>Pass Mark:</strong> ${PASS_MARK} / ${TOTAL_QUESTIONS}</p>
    <p class="${statusClass}">${statusText}</p>
  `;

  topicAnalysis.innerHTML = "";
  Object.keys(TOPIC_REQUIREMENTS).forEach((topic) => {
    const stats = scored.topicStats[topic] || { correct: 0, total: 0 };
    const pct = stats.total ? Math.round((stats.correct / stats.total) * 100) : 0;

    const row = document.createElement("div");
    row.className = "topic-row";
    row.innerHTML = `
      <div><strong>${topic}</strong></div>
      <div>${stats.correct} / ${stats.total} correct (${pct}%)</div>
      <div class="topic-bar-wrap"><div class="topic-bar" style="width: ${pct}%"></div></div>
    `;

    topicAnalysis.appendChild(row);
  });

  answerReview.innerHTML = "";
  scored.review.forEach((item, index) => {
    const div = document.createElement("div");
    div.className = "answer-item";
    div.innerHTML = `
      <strong>Q${index + 1}. ${item.questionText.replace(/\r\n/g, " ")}</strong>
      <div><em>Topic:</em> ${item.topic}</div>
      <div class="${item.isCorrect ? "answer-correct" : "answer-wrong"}">
        Your answer: ${item.selected}
      </div>
      <div>Correct answer: ${item.correct}</div>
      <div><em>Explanation:</em> ${item.explanation}</div>
    `;
    answerReview.appendChild(div);
  });
}

function shuffleArray(arr) {
  for (let i = arr.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}
