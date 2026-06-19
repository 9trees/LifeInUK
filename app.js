const QUESTION_BANK_PATH = "./lituk_questions_422.json";
const TEST_DURATION_SECONDS = 45 * 60;
const PASS_MARK = 18;
const TOTAL_QUESTIONS = 24;
const ACTIVE_WINDOW_DAYS = 30;

const STORAGE_KEYS = {
  users: "lituk.users.v1",
  session: "lituk.session.v1",
  mockResults: "lituk.mock.results.v1",
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
    appState.users = activeUsers;
    saveUsers();
    localStorage.setItem(STORAGE_KEYS.mockResults, JSON.stringify(keptResults));
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
