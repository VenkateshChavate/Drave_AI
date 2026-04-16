/**
 * Centralized API Configuration
 */
window.API_BASE = (window.location.protocol.startsWith('http')) 
  ? window.location.origin 
  : "http://20.94.193.165:8080";

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
      showAlert(data.error || "Login failed ❌");
      return;
    }

    // Clear previous session data
    localStorage.removeItem("drave_chats");
    localStorage.removeItem("drave_current");
    localStorage.setItem("token", data.token);
    localStorage.setItem("user", JSON.stringify(data.user));

    showSuccess("login", data.user.name);

    setTimeout(() => {
      window.location.replace("/");
    }, 1000);

  } catch (err) {
    console.log(err);
    showAlert("Backend not reachable on port 8080 ❌");
  }

  setLoading("loginBtn", false);
}

/* REGISTER */
async function handleRegister(){
  hideAlert();

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
      showAlert(data.error || "Register failed ❌");
      return;
    }

    // Clear previous session data
    localStorage.removeItem("drave_chats");
    localStorage.removeItem("drave_current");
    localStorage.setItem("token", data.token);
    localStorage.setItem("user", JSON.stringify(data.user));

    showSuccess("register", name);

    setTimeout(() => {
      window.location.href = "/";
    }, 1200);

  } catch (err) {
    console.log(err);
    showAlert("Backend not reachable on port 8080 ❌");
  }

  setLoading("regBtn", false);
}

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