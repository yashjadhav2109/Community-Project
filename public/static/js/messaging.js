window.MessagingModule = {
  selectedUserId: null,

  async loadConversations() {
    const list = document.getElementById("conversations-list");
    try {
      const data = await Api.get("/api/messages/conversations");
      list.innerHTML = data.conversations.length ? data.conversations.map((conversation) => `
        <button class="conv-item ${Number(this.selectedUserId) === conversation.user.id ? "active" : ""}" onclick="MessagingModule.openThread(${conversation.user.id})">
          <strong>${App.escape(conversation.user.name)}</strong>
          <span>${App.escape(conversation.last_message?.content || "Start a conversation")}</span>
          ${conversation.unread_count ? `<small>${conversation.unread_count} new</small>` : ""}
        </button>`).join("") : '<p class="empty-state">No conversations yet. Contact a skill provider to start one.</p>';
    } catch (error) {
      list.innerHTML = `<p class="empty-state">${App.escape(error.message)} <button class="btn btn-outline btn-sm" onclick="App.openAuth('login')">Log in</button></p>`;
    }
  },

  async startConversation(userId) {
    if (!App.currentUser) return App.openAuth("login");
    this.selectedUserId = Number(userId);
    App.switchTab("messages");
    await this.openThread(this.selectedUserId);
  },

  async openThread(userId) {
    this.selectedUserId = Number(userId);
    const pane = document.getElementById("chat-messages-container");
    pane.innerHTML = '<p class="empty-state">Loading messages...</p>';
    try {
      const data = await Api.get(`/api/messages/thread/${userId}`);
      document.getElementById("chat-header-info").innerHTML = `<h4>${App.escape(data.other_user?.name || "Conversation")}</h4>`;
      pane.innerHTML = data.messages.length ? data.messages.map((message) => `
        <div class="chat-message ${message.sender_id === App.currentUser?.id ? "mine" : "theirs"}">
          <p>${App.escape(message.content)}</p><small>${App.escape(message.sender_name)} · ${App.escape(message.created_at)}</small>
        </div>`).join("") : '<p class="empty-state">No messages yet. Say hello.</p>';
      pane.scrollTop = pane.scrollHeight;
      await this.loadConversations();
    } catch (error) {
      pane.innerHTML = `<p class="empty-state">${App.escape(error.message)}</p>`;
    }
  },

  async sendMessage(event) {
    event.preventDefault();
    if (!App.currentUser) return App.openAuth("login");
    if (!this.selectedUserId) return App.toast("Choose a conversation or contact a provider first.", "error");
    const input = document.getElementById("chat-input-text");
    const content = input.value.trim();
    if (!content) return;
    try {
      await Api.post("/api/messages", { receiver_id: this.selectedUserId, content });
      input.value = "";
      await this.openThread(this.selectedUserId);
    } catch (error) {
      App.toast(error.message, "error");
    }
  }
};