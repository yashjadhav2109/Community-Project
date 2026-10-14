(function () {
  async function request(path, options = {}, allowUnauthenticated = false) {
    const response = await fetch(path, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok || (!allowUnauthenticated && body.success === false)) {
      throw new Error(body.error || `Request failed (${response.status})`);
    }
    return body;
  }

  window.Api = {
    get: (path) => request(path),
    getAllowUnauthenticated: (path) => request(path, {}, true),
    post: (path, data) => request(path, { method: "POST", body: JSON.stringify(data) }),
    put: (path, data) => request(path, { method: "PUT", body: JSON.stringify(data) }),
    delete: (path) => request(path, { method: "DELETE" })
  };
})();