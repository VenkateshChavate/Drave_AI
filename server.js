/**
 * Centralized API Configuration
 */
window.API_BASE = (window.location.protocol.startsWith('http')) 
  ? window.location.origin 
  : "http://127.0.0.1:5000";

/* ALERT */
function showAlert(msg){
  document.getElementById('alertBox').classList.add('show');
  document.getElementById('alertText').textContent = msg;
}

function hideAlert(){
  document.getElementById('alertBox').classList.remove('show');
}

/* LOADING */
function setLoading(id, on){
  const btn = document.getElementById(id);
  btn.classList.toggle('loading', on);
  btn.disabled = on;
}

/* LOGIN */
async function handleLogin(){
  hideAlert();
  toggleGlobalLoader(true);

  const email = document.getElementById('loginEmail').value;
  const password = document.getElementById('loginPassword').value;

  setLoading("loginBtn", true);

  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();

    if(!res.ok){
      toggleGlobalLoader(false);
      showAlert(data.error || "Login failed ❌");
      return setLoading("loginBtn", false);
    }

    // Save session data
    localStorage.setItem("token", data.token);
    localStorage.setItem("user", JSON.stringify(data.user));

    showSuccess("login", data.user.name);

    setTimeout(() => {
      window.location.replace("/");
    }, 1200);

  } catch (err) {
    console.log(err);
    toggleGlobalLoader(false);
    showAlert("Backend not reachable ❌");
    setLoading("loginBtn", false);
  }
}

/* REGISTER */
async function handleRegister(){
  hideAlert();
  toggleGlobalLoader(true);

  const name = document.getElementById('regName').value;
  const email = document.getElementById('regEmail').value;
  const password = document.getElementById('regPassword').value;

  setLoading("regBtn", true);

  try {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password })
    });

    const data = await res.json();

    if(!res.ok){
      toggleGlobalLoader(false);
      showAlert(data.error || "Register failed ❌");
      return setLoading("regBtn", false);
    }

    // Save session data
    localStorage.setItem("token", data.token);
    localStorage.setItem("user", JSON.stringify(data.user));

    showSuccess("register", name);

    setTimeout(() => {
      window.location.href = "/";
    }, 1200);

  } catch (err) {
    console.log(err);
    toggleGlobalLoader(false);
    showAlert("Backend not reachable ❌");
    setLoading("regBtn", false);
  }
}

/* LOADER STYLES */
const loaderStyle = document.createElement("style");
loaderStyle.textContent = `
  #globalLoader {
    position: fixed;
    inset: 0;
    background: var(--bg);
    z-index: 10000;
    display: none;
    align-items: center;
    justify-content: center;
  }
  #globalLoader.active { display: flex; }
  .loader {
    position: absolute;
    top: 50%;
    margin-left: -50px;
    left: 50%;
    animation: speeder 0.4s linear infinite;
    z-index: 9999;
  }
  .loader > span {
    height: 5px;
    width: 35px;
    background: #e63946;
    position: absolute;
    top: -19px;
    left: 60px;
    border-radius: 2px 10px 1px 0;
  }
  .base span {
    position: absolute;
    width: 0; height: 0;
    border-top: 6px solid transparent;
    border-right: 100px solid #e63946;
    border-bottom: 6px solid transparent;
  }
  .base span:before {
    content: "";
    height: 22px; width: 22px;
    border-radius: 50%;
    background: #e63946;
    position: absolute;
    right: -110px; top: -16px;
  }
  .base span:after {
    content: "";
    position: absolute;
    width: 0; height: 0;
    border-top: 0 solid transparent;
    border-right: 55px solid #e63946;
    border-bottom: 16px solid transparent;
    top: -16px; right: -98px;
  }
  .face {
    position: absolute;
    height: 12px; width: 20px;
    background: #e63946;
    border-radius: 20px 20px 0 0;
    transform: rotate(-40deg);
    right: -125px; top: -15px;
  }
  .face:after {
    content: "";
    height: 12px; width: 12px;
    background: #e63946;
    right: 4px; top: 7px;
    position: absolute;
    transform: rotate(40deg);
    transform-origin: 50% 50%;
    border-radius: 0 0 0 2px;
  }
  .loader > span > span:nth-child(1),
  .loader > span > span:nth-child(2),
  .loader > span > span:nth-child(3),
  .loader > span > span:nth-child(4) {
    width: 30px;
    height: 1px;
    background: #e63946;
    position: absolute;
    animation: fazer1 0.2s linear infinite;
  }
  .loader > span > span:nth-child(2) {
    top: 3px;
    animation: fazer2 0.4s linear infinite;
  }
  .loader > span > span:nth-child(3) {
    top: 1px;
    animation: fazer3 0.4s linear infinite;
    animation-delay: -1s;
  }
  .loader > span > span:nth-child(4) {
    top: 4px;
    animation: fazer4 1s linear infinite;
    animation-delay: -1s;
  }
  @keyframes fazer1 { 0% { left: 0; } 100% { left: -80px; opacity: 0; } }
  @keyframes fazer2 { 0% { left: 0; } 100% { left: -100px; opacity: 0; } }
  @keyframes fazer3 { 0% { left: 0; } 100% { left: -50px; opacity: 0; } }
  @keyframes fazer4 { 0% { left: 0; } 100% { left: -150px; opacity: 0; } }
  @keyframes speeder {
    0% { transform: translate(2px, 1px) rotate(0deg); }
    10% { transform: translate(-1px, -3px) rotate(-1deg); }
    20% { transform: translate(-2px, 0px) rotate(1deg); }
    30% { transform: translate(1px, 2px) rotate(0deg); }
    40% { transform: translate(1px, -1px) rotate(1deg); }
    50% { transform: translate(-1px, 3px) rotate(-1deg); }
    60% { transform: translate(-1px, 1px) rotate(0deg); }
    70% { transform: translate(3px, 1px) rotate(-1deg); }
    80% { transform: translate(-2px, -1px) rotate(1deg); }
    90% { transform: translate(2px, 1px) rotate(0deg); }
    100% { transform: translate(1px, -2px) rotate(-1deg); }
  }
  .longfazers {
    position: absolute; width: 100%; height: 100%;
    top: 0; left: 0; pointer-events: none;
  }
  .longfazers span { position: absolute; height: 2px; width: 20%; background: #e63946; }
  .longfazers span:nth-child(1) { top: 20%; animation: lf 0.6s linear infinite; animation-delay: -5s; }
  .longfazers span:nth-child(2) { top: 40%; animation: lf2 0.8s linear infinite; animation-delay: -1s; }
  .longfazers span:nth-child(3) { top: 60%; animation: lf3 0.6s linear infinite; }
  .longfazers span:nth-child(4) { top: 80%; animation: lf4 0.5s linear infinite; animation-delay: -3s; }
  @keyframes lf { 0% { left: 200%; } 100% { left: -200%; opacity: 0; } }
  @keyframes lf2 { 0% { left: 200%; } 100% { left: -200%; opacity: 0; } }
  @keyframes lf3 { 0% { left: 200%; } 100% { left: -100%; opacity: 0; } }
  @keyframes lf4 { 0% { left: 200%; } 100% { left: -100%; opacity: 0; } }
`;
document.head.appendChild(loaderStyle);

/* GLOBAL LOADER HANDLER */
function toggleGlobalLoader(show) {
  let loaderContainer = document.getElementById('globalLoader');
  if (!loaderContainer) {
    loaderContainer = document.createElement('div');
    loaderContainer.id = 'globalLoader';
    loaderContainer.innerHTML = `
      <div class="loader">
        <span><span></span><span></span><span></span><span></span></span>
        <div class="base"><span></span><div class="face"></div></div>
      </div>
      <div class="longfazers"><span></span><span></span><span></span><span></span></div>
    `;
    document.body.appendChild(loaderContainer);
  }
  loaderContainer.classList.toggle('active', show);
}

// Show loader on initial page load (refresh)
toggleGlobalLoader(true);
window.addEventListener('load', () => {
  // Small delay to ensure the animation is visible during fast refreshes
  setTimeout(() => toggleGlobalLoader(false), 600);
});

/* THEME MANAGEMENT */
function toggleTheme() {
  const isLight = document.documentElement.classList.toggle('light-theme');
  localStorage.setItem('drave_theme', isLight ? 'light' : 'dark');
  updateThemeIcons();
}

function updateThemeIcons() {
  const isLight = document.documentElement.classList.contains('light-theme');
  const sun = document.querySelector('.sun-icon');
  const moon = document.querySelector('.moon-icon');
  if (sun && moon) {
    sun.style.display = isLight ? 'block' : 'none';
    moon.style.display = isLight ? 'none' : 'block';
  }
}

function initTheme() {
  const savedTheme = localStorage.getItem('drave_theme') || 'dark';
  document.documentElement.classList.toggle('light-theme', savedTheme === 'light');
  if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', updateThemeIcons);
  } else {
    updateThemeIcons();
  }
}
initTheme();

/* SUCCESS */
function showSuccess(mode, name){
  document.getElementById('loginForm').classList.remove('active');
  document.getElementById('registerForm').classList.remove('active');

  const screen = document.getElementById('successScreen');
  screen.classList.add('show');

  document.getElementById('successTitle').textContent =
    mode === "register"
      ? `Welcome, ${name}! 🎉`
      : `Welcome back, ${name}!`;
}

/* UI HELPERS */
function switchTab(tab){
  if(document.getElementById('successScreen')) 
    document.getElementById('successScreen').classList.remove('show');

  document.querySelectorAll('.tab-btn').forEach((b, i) => {
    b.classList.toggle('active',
      (i === 0 && tab === 'login') || (i === 1 && tab === 'register'));
  });

  document.getElementById('loginForm').classList.toggle('active', tab === 'login');
  document.getElementById('registerForm').classList.toggle('active', tab === 'register');

  document.getElementById('formTitle').textContent =
    tab === 'login' ? 'Welcome back' : 'Create account';
  document.getElementById('formSub').textContent =
    tab === 'login'
      ? 'Sign in to continue your conversations.'
      : 'Join Drave and start chatting.';

  hideAlert();
}

function switchTabLink(e, tab){
  e.preventDefault();
  switchTab(tab);
}

function togglePw(inputId, btn){
  const input = document.getElementById(inputId);
  const isText = input.type === 'text';
  input.type = isText ? 'password' : 'text';
  btn.innerHTML = isText
    ? `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`
    : `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`;
}

function checkStrength(val){
  const wrap = document.getElementById('strengthWrap');
  const label = document.getElementById('strengthLabel');
  const bars = [
    document.getElementById('sb1'), document.getElementById('sb2'),
    document.getElementById('sb3'), document.getElementById('sb4')
  ];

  if(!val){ wrap.classList.remove('visible'); return; }
  wrap.classList.add('visible');

  let score = 0;
  if(val.length >= 8) score++;
  if(/[A-Z]/.test(val)) score++;
  if(/[0-9]/.test(val)) score++;
  if(/[^A-Za-z0-9]/.test(val)) score++;

  const colors = ['#ef4444','#f97316','#eab308','#22c55e'];
  const labels = ['Weak','Fair','Good','Strong'];

  bars.forEach((b, i) => {
    b.style.background = i < score ? colors[score - 1] : 'var(--surface3)';
  });
  label.textContent = labels[score - 1] || 'Weak';
  label.style.color = colors[score - 1] || '#ef4444';
}

document.addEventListener('keydown', e => {
  if(e.key !== 'Enter') return;
  const loginActive = document.getElementById('loginForm').classList.contains('active');
  loginActive ? handleLogin() : handleRegister();
});