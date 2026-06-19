const QUESTION_BANK_PATH = "./lituk_questions_422.json";
const TEST_DURATION_SECONDS = 45 * 60;
const PASS_MARK = 18;
const TOTAL_QUESTIONS = 24;

const TOPIC_REQUIREMENTS = {
  "The values and principles of the UK": 1,
  "What is the UK?": 1,
  "A long and illustrious history": 8,
  "A modern, thriving society": 7,
  "The UK government, the law and your role": 7,
};

const state = {
  bank: [],
  testQuestions: [],
  selectedAnswers: {},
  timeLeft: TEST_DURATION_SECONDS,
  timerId: null,
  submitted: false,
};

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

startBtn.addEventListener("click", startNewTest);
submitBtn.addEventListener("click", () => finalizeTest(false));
jumpBtn.addEventListener("click", scrollToFirstUnanswered);

async function startNewTest() {
  clearInterval(state.timerId);
  resetStateForNewTest();

  try {
    if (state.bank.length === 0) {
      const response = await fetch(QUESTION_BANK_PATH);
      if (!response.ok) {
        throw new Error(`Could not load ${QUESTION_BANK_PATH}`);
      }
      state.bank = await response.json();
    }

    state.testQuestions = buildMockTest(state.bank);
    renderTest();
    startTimer();

    statusCard.classList.remove("hidden");
    testSection.classList.remove("hidden");
    resultSection.classList.add("hidden");

    updateLiveMetrics();
  } catch (error) {
    alert(`Failed to start test: ${error.message}`);
  }
}

function resetStateForNewTest() {
  state.testQuestions = [];
  state.selectedAnswers = {};
  state.timeLeft = TEST_DURATION_SECONDS;
  state.submitted = false;
  testForm.innerHTML = "";
  topicAnalysis.innerHTML = "";
  answerReview.innerHTML = "";
  resultSummary.innerHTML = "";
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

  state.testQuestions.forEach((q, qIndex) => {
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
        state.selectedAnswers[qIndex] = aIndex;
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
  state.timerId = setInterval(() => {
    state.timeLeft -= 1;
    renderTimer();

    if (state.timeLeft <= 0) {
      finalizeTest(true);
    }
  }, 1000);
}

function renderTimer() {
  const mins = String(Math.max(0, Math.floor(state.timeLeft / 60))).padStart(2, "0");
  const secs = String(Math.max(0, state.timeLeft % 60)).padStart(2, "0");
  timerEl.textContent = `${mins}:${secs}`;
  timerEl.classList.toggle("warn", state.timeLeft <= 300);
}

function updateLiveMetrics() {
  const answeredCount = Object.keys(state.selectedAnswers).length;
  answeredCountEl.textContent = `${answeredCount} / ${TOTAL_QUESTIONS}`;

  const currentCorrect = state.testQuestions.reduce((acc, q, idx) => {
    const chosen = state.selectedAnswers[idx];
    if (chosen === undefined) {
      return acc;
    }
    return acc + (q.answers[chosen]?.correct ? 1 : 0);
  }, 0);

  liveScoreEl.textContent = `${currentCorrect}`;

  const completionPct = Math.round((answeredCount / TOTAL_QUESTIONS) * 100);
  progressFillEl.style.width = `${completionPct}%`;
  progressTextEl.textContent = `${completionPct}% completed`;

  const unanswered = TOTAL_QUESTIONS - answeredCount;
  submitBtn.textContent = unanswered > 0 ? `Submit Test (${unanswered} left)` : "Submit Test";
}

function finalizeTest(fromTimeout) {
  if (state.submitted) {
    return;
  }

  if (!fromTimeout) {
    const unanswered = TOTAL_QUESTIONS - Object.keys(state.selectedAnswers).length;
    if (unanswered > 0) {
      const proceed = window.confirm(`You still have ${unanswered} unanswered question(s). Submit anyway?`);
      if (!proceed) {
        scrollToFirstUnanswered();
        return;
      }
    }
  }

  state.submitted = true;
  clearInterval(state.timerId);

  const scored = scoreTest(state.testQuestions, state.selectedAnswers);
  renderResults(scored, fromTimeout);

  resultSection.classList.remove("hidden");
  testSection.classList.add("hidden");
}

function scrollToFirstUnanswered() {
  const firstUnansweredIndex = state.testQuestions.findIndex((_, idx) => state.selectedAnswers[idx] === undefined);
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
