window.App = {
  currentUser: null,
  categories: [],
  neighborhoods: [],

  escape(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
  },

  async init() {
    try {
      const metadata = await Api.get("/api/meta");
      this.categories = metadata.categories || [];
      this.neighborhoods = metadata.neighborhoods || [];
      this.populateSelects();
      const auth = await Api.get("/api/auth/me");
      this.currentUser = auth.user || null;
      this.renderUser();
      await Promise.all([this.loadSkills(), this.loadJobs()]);
      this.bindFilters();
    } catch (error) {
      this.toast(`The application could not start: ${error.message}`, "error");
    }
  },

  populateSelects() {
    document.querySelectorAll("select.category-select").forEach((select) => {
      const first = select.querySelector("option[value='']")?.outerHTML || '<option value="">Select category</option>';
      select.innerHTML = first + this.categories.map((category) => `<option value="${this.escape(category)}">${this.escape(category)}</option>`).join("");
    });
    document.querySelectorAll("select.neighborhood-select").forEach((select) => {
      select.innerHTML = this.neighborhoods.map((place) => `<option value="${this.escape(place)}">${this.escape(place)}</option>`).join("");
      if (this.currentUser?.neighborhood) select.value = this.currentUser.neighborhood;
    });
  },

  renderUser() {
    const profile = document.getElementById("nav-user-profile");
    const actions = document.getElementById("nav-auth-actions");
    if (!this.currentUser) {
      profile.innerHTML = "";
      actions.style.display = "flex";
      return;
    }
    actions.style.display = "none";
    profile.innerHTML = `<span class="user-greeting">Hi, ${this.escape(this.currentUser.name)}</span> <button class="btn btn-outline btn-sm" type="button" onclick="App.logout()">Log out</button>`;
  },

  bindFilters() {
    const reloadSkills = () => this.loadSkills();
    ["skill-category-filter", "skill-neighborhood-filter", "skill-rate-filter"].forEach((id) => document.getElementById(id).addEventListener("change", reloadSkills));
    document.getElementById("skill-search-input").addEventListener("input", () => {
      clearTimeout(this.searchTimer);
      this.searchTimer = setTimeout(reloadSkills, 250);
    });
    ["job-category-filter", "job-neighborhood-filter"].forEach((id) => document.getElementById(id).addEventListener("change", () => this.loadJobs()));
    document.getElementById("skill-rate-filter").addEventListener("input", (event) => {
      document.getElementById("rate-val-display").textContent = `₹${event.target.value}`;
    });
  },

  async loadSkills() {
    const grid = document.getElementById("skills-cards-grid");
    const params = new URLSearchParams();
    const category = document.getElementById("skill-category-filter").value;
    const neighborhood = document.getElementById("skill-neighborhood-filter").value;
    const search = document.getElementById("skill-search-input").value.trim();
    const maxRate = document.getElementById("skill-rate-filter").value;
    if (category) params.set("category", category);
    if (neighborhood) params.set("neighborhood", neighborhood);
    if (search) params.set("search", search);
    if (maxRate) params.set("max_rate", maxRate);
    try {
      const data = await Api.get(`/api/skills?${params}`);
      grid.innerHTML = data.skills.length ? data.skills.map((skill) => `
        <article class="listing-card">
          <div class="listing-card-top"><span class="listing-category">${this.escape(skill.category)}</span><span class="listing-rating">★ ${Number(skill.provider_rating).toFixed(1)}</span></div>
          <h3>${this.escape(skill.title)}</h3>
          <p>${this.escape(skill.description)}</p>
          <div class="listing-meta"><span>${this.escape(skill.provider_name)}</span><span>${this.escape(skill.neighborhood)}</span><span>₹${Number(skill.hourly_rate).toLocaleString("en-IN")}/hr</span></div>
          <div class="listing-actions"><button class="btn btn-primary btn-sm" onclick="MessagingModule.startConversation(${skill.user_id})">Message provider</button>${this.currentUser?.id === skill.user_id ? `<button class="btn btn-outline btn-sm" onclick="App.removeSkill(${skill.id})">Remove</button>` : ""}</div>
        </article>`).join("") : '<p class="empty-state">No skills match these filters yet. Join the community and publish the first listing.</p>';
    } catch (error) {
      grid.innerHTML = `<p class="empty-state">Could not load skills: ${this.escape(error.message)}</p>`;
    }
  },

  async loadJobs() {
    const grid = document.getElementById("jobs-cards-grid");
    const params = new URLSearchParams({ status: "open" });
    const category = document.getElementById("job-category-filter").value;
    const neighborhood = document.getElementById("job-neighborhood-filter").value;
    if (category) params.set("category", category);
    if (neighborhood) params.set("neighborhood", neighborhood);
    try {
      const data = await Api.get(`/api/jobs?${params}`);
      grid.innerHTML = data.jobs.length ? data.jobs.map((job) => `
        <article class="listing-card">
          <div class="listing-card-top"><span class="listing-category">${this.escape(job.category)}</span><span class="urgency-${this.escape(job.urgency)}">${this.escape(job.urgency)}</span></div>
          <h3>${this.escape(job.title)}</h3><p>${this.escape(job.description)}</p>
          <div class="listing-meta"><span>By ${this.escape(job.requester_name)}</span><span>${this.escape(job.neighborhood)}</span><span>Budget ₹${Number(job.budget).toLocaleString("en-IN")}</span></div>
          <div class="listing-actions"><button class="btn btn-primary btn-sm" onclick="MatchingModule.loadMatches(${job.id}); App.switchTab('matching')">Find matches</button><button class="btn btn-outline btn-sm" onclick="MessagingModule.startConversation(${job.user_id})">Contact requester</button></div>
        </article>`).join("") : '<p class="empty-state">No open requests yet. Post a job to find nearby help.</p>';
    } catch (error) {
      grid.innerHTML = `<p class="empty-state">Could not load jobs: ${this.escape(error.message)}</p>`;
    }
  },

  switchTab(tab) {
    document.querySelectorAll(".tab-view").forEach((view) => { view.style.display = view.id === `view-${tab}` ? "block" : "none"; });
    document.querySelectorAll(".nav-link-btn").forEach((button) => button.classList.toggle("active", button.dataset.tab === tab));
    if (tab === "matching") MatchingModule.loadJobs();
    if (tab === "messages") MessagingModule.loadConversations();
    if (tab === "admin") AdminModule.loadDashboardData();
  },

  openModal(id) { document.getElementById(id)?.classList.add("show"); },
  closeModal(id) { document.getElementById(id)?.classList.remove("show"); },

  openAuth(mode) {
    this.setAuthMode(mode);
    this.openModal("auth-modal");
  },

  setAuthMode(mode) {
    const registering = mode === "register";
    document.getElementById("register-form").style.display = registering ? "block" : "none";
    document.getElementById("login-form").style.display = registering ? "none" : "block";
    document.getElementById("auth-modal-title").textContent = registering ? "Join the community" : "Welcome back";
  },

  async handleRegister(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form.entries());
    try {
      const data = await Api.post("/api/auth/register", payload);
      this.currentUser = data.user;
      this.renderUser();
      this.closeModal("auth-modal");
      this.toast(data.message);
      await this.init();
    } catch (error) { this.toast(error.message, "error"); }
  },

  async handleLogin(event) {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
    try {
      const data = await Api.post("/api/auth/login", payload);
      this.currentUser = data.user;
      this.renderUser();
      this.closeModal("auth-modal");
      this.toast(data.message);
      await this.loadSkills();
    } catch (error) { this.toast(error.message, "error"); }
  },

  async logout() {
    try {
      await Api.post("/api/auth/logout", {});
      this.currentUser = null;
      this.renderUser();
      this.toast("You are logged out.");
    } catch (error) { this.toast(error.message, "error"); }
  },

  requireUser() {
    if (this.currentUser) return true;
    this.openAuth("register");
    this.toast("Create an account or log in to continue.", "error");
    return false;
  },

  async handlePostSkill(event) {
    event.preventDefault();
    if (!this.requireUser()) return;
    const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
    try {
      const data = await Api.post("/api/skills", payload);
      event.currentTarget.reset();
      this.closeModal("post-skill-modal");
      this.toast(data.message);
      await this.loadSkills();
    } catch (error) { this.toast(error.message, "error"); }
  },

  async handlePostJob(event) {
    event.preventDefault();
    if (!this.requireUser()) return;
    const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
    try {
      const data = await Api.post("/api/jobs", payload);
      event.currentTarget.reset();
      this.closeModal("post-job-modal");
      this.toast(data.message);
      await this.loadJobs();
    } catch (error) { this.toast(error.message, "error"); }
  },

  async removeSkill(id) {
    if (!this.requireUser() || !confirm("Remove this skill listing?")) return;
    try {
      const data = await Api.delete(`/api/skills/${id}`);
      this.toast(data.message);
      await this.loadSkills();
    } catch (error) { this.toast(error.message, "error"); }
  },

  openReview(revieweeId, jobId, name) {
    document.getElementById("review-reviewee-id").value = revieweeId;
    document.getElementById("review-job-id").value = jobId || "";
    document.getElementById("review-target-name").textContent = name || "Community Member";
    this.openModal("review-modal");
  },

  async submitReview(event) {
    event.preventDefault();
    if (!this.requireUser()) return;
    const payload = {
      reviewee_id: document.getElementById("review-reviewee-id").value,
      job_id: document.getElementById("review-job-id").value || null,
      rating: document.getElementById("review-rating-select").value,
      comment: document.getElementById("review-comment-text").value
    };
    try {
      const data = await Api.post("/api/reviews", payload);
      this.closeModal("review-modal");
      this.toast(data.message);
    } catch (error) { this.toast(error.message, "error"); }
  },

  toast(message, type = "success") {
    const container = document.getElementById("toast-container");
    const item = document.createElement("div");
    item.className = `toast ${type === "error" ? "toast-error" : ""}`;
    item.textContent = message;
    container.appendChild(item);
    setTimeout(() => item.remove(), 4500);
  }
};

document.addEventListener("DOMContentLoaded", () => App.init());