window.MatchingModule = {
  async loadJobs() {
    const list = document.getElementById("matching-job-list");
    if (!list) return;
    list.innerHTML = '<p class="empty-state">Loading open jobs...</p>';
    try {
      const data = await Api.get("/api/jobs?status=open");
      list.innerHTML = data.jobs.length ? data.jobs.map((job) => `
        <button class="job-match-option" type="button" onclick="MatchingModule.loadMatches(${job.id})">
          <strong>${App.escape(job.title)}</strong><span>${App.escape(job.category)} · ${App.escape(job.neighborhood)}</span>
          <small>Budget ₹${Number(job.budget).toLocaleString("en-IN")}</small>
        </button>`).join("") : '<p class="empty-state">No open jobs to match yet. Post a request to get started.</p>';
    } catch (error) {
      list.innerHTML = `<p class="empty-state">${App.escape(error.message)}</p>`;
    }
  },

  async loadMatches(jobId) {
    const results = document.getElementById("matching-results-list");
    results.innerHTML = '<p class="empty-state">Finding the closest skill providers...</p>';
    try {
      const data = await Api.get(`/api/jobs/${jobId}/matches`);
      results.innerHTML = `<h3>${App.escape(data.job.title)}</h3><p>${data.match_count} matching provider${data.match_count === 1 ? "" : "s"}</p>` +
        (data.matches.length ? data.matches.map((match) => `
          <article class="match-result">
            <div><strong>${App.escape(match.title)}</strong><span>${App.escape(match.provider.name)} · ${App.escape(match.neighborhood)}</span></div>
            <strong class="match-score">${Number(match.match_score).toFixed(0)}%</strong>
            <button class="btn btn-outline btn-sm" onclick="MessagingModule.startConversation(${match.provider.id})">Message</button>
          </article>`).join("") : '<p class="empty-state">No active providers match this request yet.</p>');
    } catch (error) {
      results.innerHTML = `<p class="empty-state">${App.escape(error.message)}</p>`;
    }
  }
};