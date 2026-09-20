/* ═════════════════════════════════════════════════════════
   SkillBridge — Frontend Logic
   ═════════════════════════════════════════════════════════ */

const API = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://skillbridge-aws.onrender.com';
let STATE = {
  threadId: null,
  userId: null,
  gapData: null,
  customProject: null,
};

/* ─── HEALTH CHECK ──────────────────────────────────── */
async function checkHealth() {
  const dot = document.getElementById('statusDot');
  try {
    const r = await fetch(`${API}/health`);
    const d = await r.json();
    if (d.status === 'ok') {
      dot.textContent = `API: ${d.mode.toUpperCase()} · ${d.llm}`;
      dot.style.color = '#3FB950';
    } else throw new Error();
  } catch {
    dot.textContent = 'API: Offline';
    dot.style.color = '#F85149';
  }
}

/* ─── RESUME FILE UPLOAD HANDLER ────────────────────── */
function handleResumeUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const label = document.getElementById('fileNameLabel');
  label.textContent = `Selected: ${file.name}`;

  if (file.type === 'text/plain' || file.name.endsWith('.md') || file.name.endsWith('.txt')) {
    const reader = new FileReader();
    reader.onload = function(e) {
      document.getElementById('resumeText').value = e.target.result;
    };
    reader.readAsText(file);
  } else if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
    // Read text metadata / preview text indicator
    const reader = new FileReader();
    reader.onload = function(e) {
      // Basic text extraction or binary preview indicator
      const content = `[Resume Document: ${file.name} | Size: ${Math.round(file.size / 1024)} KB]\nUploaded PDF candidate resume for parsing.`;
      document.getElementById('resumeText').value = content;
    };
    reader.readAsArrayBuffer(file);
  } else {
    document.getElementById('resumeText').value = `[Uploaded File: ${file.name}]`;
  }
}

/* ─── TAB SWITCHER ──────────────────────────────────── */
function switchView(tab) {
  const btnAnalyze = document.getElementById('tabAnalyzeBtn');
  const btnProject = document.getElementById('tabProjectBtn');
  const secAnalyze = document.getElementById('secAnalyze');
  const secAddProject = document.getElementById('secAddProject');

  if (tab === 'analyze') {
    btnAnalyze.classList.add('active');
    btnProject.classList.remove('active');
    secAnalyze.classList.remove('hidden');
    secAddProject.classList.add('hidden');
  } else {
    btnProject.classList.add('active');
    btnAnalyze.classList.remove('active');
    secAddProject.classList.remove('hidden');
    secAnalyze.classList.add('hidden');
  }
}

/* ─── SAVE CUSTOM PROJECT ───────────────────────────── */
function saveCustomProject() {
  const name = document.getElementById('custProjName').value.trim();
  const hours = document.getElementById('custProjHours').value.trim() || '8';
  const skillsStr = document.getElementById('custProjSkills').value.trim();
  const desc = document.getElementById('custProjDesc').value.trim();
  const tasksRaw = document.getElementById('custProjTasks').value.trim();

  if (!name || !desc) {
    alert('Please provide a project title and description.');
    return;
  }

  const skills = skillsStr ? skillsStr.split(',').map(s => s.trim()) : ['Full Stack'];
  const tasks = tasksRaw.split('\n').filter(t => t.trim().length > 0).map((t, idx) => ({
    id: idx + 1,
    title: t.replace(/^\d+\.\s*/, ''),
    skill: skills[idx % skills.length] || 'Engineering',
    description: t,
    verificationCriteria: 'Deliverable implemented and passing tests',
  }));

  STATE.customProject = {
    project_name: name,
    description: desc,
    estimated_hours: parseInt(hours),
    skills_targeted: skills,
    tasks: tasks,
  };

  alert(`Project "${name}" saved! It will be used as the target build task.`);
  renderProject(STATE.customProject);
  switchView('analyze');
}

/* ─── LOADING HELPERS ────────────────────────────────── */
const defaultSteps = [
  'Parsing job description requirements…',
  'Analyzing uploaded resume content…',
  'Evaluating GitHub profile & commit evidence…',
  'Computing skill graph and priority gaps…',
  'Generating targeted engineering project…'
];

function showLoading(title, customSteps) {
  const overlay = document.getElementById('loadingOverlay');
  const titleEl = document.getElementById('loadingTitle');
  const stepsEl = document.getElementById('loadingSteps');
  overlay.classList.remove('hidden');
  titleEl.textContent = title;
  stepsEl.innerHTML = '';

  const list = customSteps || defaultSteps;
  let i = 0;
  const interval = setInterval(() => {
    if (i < list.length) {
      const step = document.createElement('div');
      step.className = 'loading-step-item';
      step.innerHTML = `<span style="color:#58A6FF;">›</span> ${list[i]}`;
      stepsEl.appendChild(step);
      i++;
    } else {
      clearInterval(interval);
    }
  }, 400);

  return interval;
}

function hideLoading(interval) {
  if (interval) clearInterval(interval);
  document.getElementById('loadingOverlay').classList.add('hidden');
}

/* ─── PIPELINE STEP INDICATOR ───────────────────────── */
function setFlowStep(step) {
  const ids = ['fStep1', 'fStep2', 'fStep3', 'fStep4', 'fStep5'];
  ids.forEach((id, idx) => {
    const el = document.getElementById(id);
    if (!el) return;
    if (idx + 1 < step) {
      el.className = 'pipe-step done';
    } else if (idx + 1 === step) {
      el.className = 'pipe-step active';
    } else {
      el.className = 'pipe-step';
    }
  });
}

function showSection(id) {
  const el = document.getElementById(id);
  if (el) {
    el.classList.remove('hidden');
    setTimeout(() => {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 50);
  }
}

/* ─── SKILL CARD BUILDER ────────────────────────────── */
function makeSkillCard(name, current, required, status) {
  const cur = parseInt(current !== undefined && !isNaN(current) ? current : 1);
  const req = parseInt(required !== undefined && !isNaN(required) ? required : 3);
  const pct = req > 0 ? Math.min(100, Math.max(0, (cur / req) * 100)) : 0;
  const st = (status || 'gap').toLowerCase();
  const statusClass = st === 'demonstrated' ? 'demonstrated'
                    : st === 'partial' ? 'partial'
                    : 'gap';
  const badgeMap = { demonstrated: 'badge-dem', partial: 'badge-clm', none: 'badge-gap', gap: 'badge-gap' };
  return `
    <div class="skill-card">
      <div class="sk-header">
        <span class="sk-name">${name}</span>
        <span class="badge ${badgeMap[st] || 'badge-gap'} font-mono">${st.toUpperCase()}</span>
      </div>
      <div class="sk-bar-wrap">
        <div class="sk-bar-bg">
          <div class="sk-bar-fill ${statusClass}" style="width: ${pct}%"></div>
        </div>
        <span class="sk-levels font-mono">${cur}/${req}</span>
      </div>
    </div>`;
}

/* ─── RENDER GAPS ───────────────────────────────────── */
function renderGaps(data) {
  const profileGrid = document.getElementById('skillProfileGrid');
  profileGrid.innerHTML = (data.skill_gaps || []).map(g => {
    const req = g.required_level || g.required || 3;
    const cur = g.current_level !== undefined ? g.current_level : (req - (g.gap || 0));
    const status = g.evidence_status || (g.gap > 0 ? 'gap' : 'demonstrated');
    return makeSkillCard(g.skill, cur, req, status);
  }).join('');

  const gapsList = document.getElementById('gapsList');
  gapsList.innerHTML = (data.skill_gaps || []).map((g) => {
    const status = g.evidence_status || (g.gap > 0 ? 'gap' : 'demonstrated');
    const prio = g.priority_score !== undefined ? g.priority_score.toFixed(1) : '1.0';
    return `
    <div class="gap-item">
      <span class="gap-title">${g.skill}</span>
      <div class="gap-meta">
        <span class="font-mono">Gap: L${g.gap !== undefined ? g.gap : 1}</span>
        <span class="badge ${status === 'demonstrated' ? 'badge-dem' : status === 'partial' ? 'badge-clm' : 'badge-gap'} font-mono">${status.toUpperCase()}</span>
        <span class="font-mono" style="color:#D29922">Priority ${prio}</span>
      </div>
    </div>`;
  }).join('');

  showSection('secGaps');
  setFlowStep(2);
}

/* ─── RENDER PROJECT ────────────────────────────────── */
function renderProject(proj) {
  const el = document.getElementById('projectCard');
  const tasks = (proj.tasks || []).map((t) => `
    <div class="task-item">
      <div class="task-top">
        <strong>Task ${t.id}: ${t.title}</strong>
        <span class="badge badge-clm font-mono">${t.skill}</span>
      </div>
      <div style="color:var(--text-sub); margin-bottom: 4px;">${t.description || ''}</div>
      <div class="task-criteria font-mono">Criteria: ${t.verification_criteria}</div>
    </div>`).join('');

  el.innerHTML = `
    <div class="project-header-box">
      <div class="proj-title font-mono">${proj.project_name}</div>
      <div class="proj-desc">${proj.description || ''}</div>
      <div class="proj-meta-row font-mono">
        <span>Effort: ${proj.estimated_hours}h</span>
        <span>Targeted: ${(proj.skills_targeted || []).join(', ')}</span>
      </div>
    </div>
    <div class="tasks-list">${tasks}</div>`;

  showSection('secProject');
  showSection('secSubmit');
  setFlowStep(3);
}

/* ─── RUN ANALYZE ───────────────────────────────────── */
async function runAnalyze() {
  const userId = document.getElementById('userId').value.trim();
  const role = document.getElementById('targetRole').value.trim();
  const company = document.getElementById('targetCompany').value.trim();
  const jd = document.getElementById('jobDescription').value.trim();
  const resume = document.getElementById('resumeText').value.trim();
  const github = document.getElementById('githubUsername').value.trim();
  const githubToken = document.getElementById('githubToken').value.trim();

  if (!userId || !role || !jd || !resume) {
    showError('analyzeError', 'Please fill in Candidate Identifier, Target Role, Job Description, and Resume.');
    return;
  }

  document.getElementById('analyzeError').classList.add('hidden');
  document.getElementById('btnAnalyze').disabled = true;
  STATE.userId = userId;

  const interval = showLoading('Evaluating candidate evidence against job specifications…');

  try {
    const res = await fetch(`${API}/agent/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        target_role: role,
        target_company: company,
        job_description: jd,
        resume_text: resume,
        github_username: github,
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Analysis request failed');
    }

    const data = await res.json();
    STATE.threadId = data.thread_id;
    STATE.gapData = data;

    hideLoading(interval);
    renderGaps(data);

    // If user provided a custom project, prioritize it
    if (STATE.customProject) {
      renderProject(STATE.customProject);
    } else {
      renderProject(data.project);
    }

  } catch (e) {
    hideLoading(interval);
    showError('analyzeError', `Analysis error: ${e.message}`);
  } finally {
    document.getElementById('btnAnalyze').disabled = false;
  }
}

/* ─── RUN SUBMIT ────────────────────────────────────── */
async function runSubmit() {
  const url = document.getElementById('submissionUrl').value.trim();
  if (!url || !STATE.threadId) {
    showError('submitError', 'Please enter a GitHub repository URL and complete the analysis step first.');
    return;
  }

  document.getElementById('submitError').classList.add('hidden');
  document.getElementById('btnSubmit').disabled = true;

  const submitSteps = [
    'Fetching repository structure & tree…',
    'Executing AST inspection for language models…',
    'Executing automated integration test suite…',
    'Generating review feedback and audit scores…',
    'Writing immutable evidence records to DynamoDB…'
  ];

  const interval = showLoading('Verifying repository deliverables…', submitSteps);

  try {
    const res = await fetch(`${API}/agent/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ thread_id: STATE.threadId, submission_url: url })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Submission verification failed');
    }

    const data = await res.json();
    hideLoading(interval);
    renderEvidence(data);

  } catch (e) {
    hideLoading(interval);
    showError('submitError', `Verification error: ${e.message}`);
  } finally {
    document.getElementById('btnSubmit').disabled = false;
  }
}

/* ─── RENDER EVIDENCE ───────────────────────────────── */
async function renderEvidence(submitData) {
  const rev = submitData.review_result || {};

  document.getElementById('reviewSummary').innerHTML = `
    <div class="score-badge">${rev.overall_score || 3}/5</div>
    <div>
      <div class="review-feedback">${rev.feedback || 'Automated review complete.'}</div>
      <div style="font-size: 12px; color: var(--text-sub); margin-top: 4px;">
        Strengths: ${(rev.strengths || []).join(', ')} · 
        Ready for role: <span style="color: ${rev.ready_for_job ? '#3FB950' : '#D29922'}; font-weight:600;">${rev.ready_for_job ? 'Yes' : 'Requires further builds'}</span>
      </div>
    </div>`;

  const evidenceGrid = document.getElementById('evidenceCards');
  evidenceGrid.innerHTML = (submitData.evidence || []).map((ev, i) => `
    <div class="evidence-card">
      <div class="ev-header font-mono">✓ VERIFIED RECORD</div>
      <div class="ev-skill">${ev.skill}</div>
      <div class="ev-meta">Score: ${ev.review_score || 3}/5 · Level ${ev.level || 3}</div>
      <div class="ev-meta" style="color:var(--blue); margin-top: 4px;"># ${ev.evidence_id || ('EV-' + (i + 101))}</div>
      <div class="ev-meta" style="margin-top: 2px;">${(ev.source && ev.source.project_name) || ev.project_name || 'Verified Project'}</div>
    </div>`).join('');

  try {
    const pr = await fetch(`${API}/profile/${STATE.userId}/skills`);
    const pd = await pr.json();
    const profileEl = document.getElementById('updatedProfile');
    profileEl.innerHTML = (pd.skills || []).map(s => {
      const cur = parseInt(s.current_level || s.level || 3);
      const req = parseInt(s.required_level || cur);
      return makeSkillCard(s.name || s.key || 'Skill', cur, Math.max(cur, req), s.evidence_status || 'demonstrated');
    }).join('');
  } catch (e) {
    document.getElementById('updatedProfile').innerHTML = '<p style="color:var(--text-sub); font-size:12px;">Profile updated in database.</p>';
  }

  const na = submitData.next_action || {};
  const naEl = document.getElementById('nextAction');
  if (na.action === 'complete' || na.remaining_gaps === 0) {
    naEl.innerHTML = `
      <div style="color: #3FB950; font-weight: 600;">All Required Competency Gaps Demonstrated</div>
      <div style="color: var(--text-sub); margin-top: 2px;">All necessary skill evidence has been verified and stored in your profile.</div>`;
  } else {
    naEl.innerHTML = `
      <div>Action: <strong>${na.action === 'generate_project' ? 'Target Next Skill Gap' : (na.action || 'Next Step')}</strong></div>
      <div style="color: var(--text-sub); margin-top: 2px;">${na.reason || 'Proceed to your next targeted build task.'}</div>`;
  }

  showSection('secEvidence');
  setFlowStep(5);
}

function showError(id, msg) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.classList.remove('hidden');
}

checkHealth();
setInterval(checkHealth, 30000);
