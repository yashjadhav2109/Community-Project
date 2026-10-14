window.AdminModule = {
  async loadDashboardData() {
    try {
      const data = await Api.get("/api/admin/dashboard");
      document.getElementById("admin-kpis-container").innerHTML = Object.entries(data.kpis).map(([key, value]) => `
        <article class="stat-card"><span class="label">${App.escape(key.replaceAll("_", " "))}</span><strong class="value">${App.escape(value)}</strong></article>`).join("");
      document.getElementById("admin-users-table-body").innerHTML = data.users.map((user) => `
        <tr><td>${App.escape(user.name)}</td><td>${App.escape(user.email)}</td><td>${App.escape(user.role)}</td>
        <td>${App.escape(user.neighborhood)}</td><td>${Number(user.rating).toFixed(1)}</td><td>${App.escape(user.status)}</td>
        <td style="text-align:right"><button class="btn btn-outline btn-sm" onclick="AdminModule.setUserStatus(${user.id}, '${user.status === "active" ? "suspended" : "active"}')">${user.status === "active" ? "Suspend" : "Activate"}</button></td></tr>`).join("") || '<tr><td colspan="7">No registered users yet.</td></tr>';
      document.getElementById("admin-logs-stream").innerHTML = data.logs.map((log) => `<p class="audit-entry"><strong>${App.escape(log.action)}</strong> ${App.escape(log.details || "")} · ${App.escape(log.user_name || "System")} · ${App.escape(log.created_at)}</p>`).join("") || '<p class="empty-state">No activity recorded yet.</p>';
    } catch (error) {
      document.getElementById("admin-kpis-container").innerHTML = `<p class="empty-state">${App.escape(error.message)}</p>`;
    }
  },

  async setUserStatus(userId, status) {
    try {
      const result = await Api.put(`/api/admin/users/${userId}/status`, { status });
      App.toast(result.message);
      await this.loadDashboardData();
    } catch (error) {
      App.toast(error.message, "error");
    }
  },

  async previewReport(type) {
    App.openModal("report-modal");
    document.getElementById("report-modal-title").textContent = type.replaceAll("_", " ");
    document.getElementById("report-modal-body").textContent = "Loading report...";
    document.getElementById("report-modal-download-csv").href = `/api/reports/download/${type}?format=csv`;
    document.getElementById("report-modal-download-pdf").href = `/api/reports/download/${type}?format=pdf`;
    try {
      const data = await Api.get(`/api/reports/preview/${type}`);
      document.getElementById("report-modal-body").innerHTML = `<pre class="report-preview">${App.escape(JSON.stringify(data.report, null, 2))}</pre>`;
    } catch (error) {
      document.getElementById("report-modal-body").textContent = error.message;
    }
  }
};