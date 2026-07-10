class RAGApp {
  constructor() {
    this.isAuthenticated = false;
    this.currentUser = null;
    this.init();
  }

  async init() {
    console.log('[RAG] Initializing application');
    this.attachEventListeners();
    await this.checkAuth();
    await this.loadRepositories();
  }

  attachEventListeners() {
    // Auth
    const loginBtn = document.getElementById('login-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const loginForm = document.getElementById('login-form');

    if (loginForm) {
      loginForm.addEventListener('submit', (e) => this.handleLogin(e));
    }
    if (loginBtn) {
      loginBtn.addEventListener('click', () => this.toggleAuthForm());
    }
    if (logoutBtn) {
      logoutBtn.addEventListener('click', () => this.handleLogout());
    }

    // Search
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
      searchForm.addEventListener('submit', (e) => this.handleSearch(e));
    }

    // Repository management
    const addRepoBtn = document.getElementById('add-repo-btn');
    const repoForm = document.getElementById('repo-form');
    if (addRepoBtn) {
      addRepoBtn.addEventListener('click', () => this.toggleRepoForm());
    }
    if (repoForm) {
      repoForm.addEventListener('submit', (e) => this.handleAddRepository(e));
    }
  }

  async checkAuth() {
    try {
      const response = await fetch('/api/health');
      const data = await response.json();
      // In production, check actual auth status
      this.updateAuthUI(false);
    } catch (error) {
      console.error('[RAG] Auth check failed:', error);
    }
  }

  async handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (response.ok) {
        const data = await response.json();
        this.isAuthenticated = true;
        this.currentUser = data.user;
        this.updateAuthUI(true);
        this.showNotification('Logged in successfully', 'success');
        document.getElementById('login-form').reset();
        this.toggleAuthForm();
      } else {
        this.showNotification('Login failed', 'error');
      }
    } catch (error) {
      console.error('[RAG] Login error:', error);
      this.showNotification('Login error: ' + error.message, 'error');
    }
  }

  async handleLogout() {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
      this.isAuthenticated = false;
      this.currentUser = null;
      this.updateAuthUI(false);
      this.showNotification('Logged out', 'success');
    } catch (error) {
      console.error('[RAG] Logout error:', error);
    }
  }

  updateAuthUI(isAuth) {
    const authSection = document.getElementById('auth-section');
    const loginBtn = document.getElementById('login-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const userInfo = document.getElementById('user-info');

    if (isAuth) {
      loginBtn?.classList.add('hidden');
      logoutBtn?.classList.remove('hidden');
      if (userInfo && this.currentUser) {
        userInfo.textContent = `Logged in as ${this.currentUser.email}`;
      }
    } else {
      loginBtn?.classList.remove('hidden');
      logoutBtn?.classList.add('hidden');
      if (userInfo) {
        userInfo.textContent = '';
      }
    }
  }

  toggleAuthForm() {
    const form = document.getElementById('login-form');
    form?.classList.toggle('hidden');
  }

  toggleRepoForm() {
    const form = document.getElementById('repo-form');
    form?.classList.toggle('hidden');
  }

  async loadRepositories() {
    try {
      const response = await fetch('/api/repositories');
      if (response.ok) {
        const data = await response.json();
        this.displayRepositories(data.repositories);
      }
    } catch (error) {
      console.error('[RAG] Failed to load repositories:', error);
    }
  }

  displayRepositories(repos) {
    const container = document.getElementById('repositories-list');
    if (!container) return;

    container.innerHTML = repos.map(repo => `
      <div class="repository-item card">
        <h3>${repo.owner}/<strong>${repo.name}</strong></h3>
        <p>Branch: <code>${repo.branch}</code></p>
        <p>Status: <span class="badge ${repo.status === 'complete' ? 'success' : ''}">${repo.status}</span></p>
        <p>Indexed: ${repo.indexed_at ? new Date(repo.indexed_at).toLocaleDateString() : 'Never'}</p>
      </div>
    `).join('');
  }

  async handleAddRepository(e) {
    e.preventDefault();
    const owner = document.getElementById('repo-owner').value;
    const name = document.getElementById('repo-name').value;
    const branch = document.getElementById('repo-branch').value || 'main';

    try {
      const response = await fetch('/api/repositories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ owner, name, branch }),
      });

      if (response.ok) {
        this.showNotification('Repository added for indexing', 'success');
        document.getElementById('repo-form').reset();
        this.toggleRepoForm();
        await this.loadRepositories();
      } else {
        this.showNotification('Failed to add repository', 'error');
      }
    } catch (error) {
      console.error('[RAG] Add repository error:', error);
      this.showNotification('Error: ' + error.message, 'error');
    }
  }

  async handleSearch(e) {
    e.preventDefault();
    const query = document.getElementById('search-input').value;

    if (!query.trim()) {
      this.showNotification('Please enter a search query', 'error');
      return;
    }

    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '<div class="loading"></div> Searching...';

    try {
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, limit: 5 }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';
      let sources = [];

      resultsDiv.innerHTML = '<div class="response-container"><div id="response-text"></div><div id="sources"></div></div>';
      const responseDiv = document.getElementById('response-text');

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.delta) {
                fullResponse += data.delta;
                responseDiv.textContent = fullResponse;
              }
              if (data.sources) {
                sources = data.sources;
              }
            } catch (e) {
              // Ignore parse errors
            }
          }
        }
      }

      // Display sources
      if (sources.length > 0) {
        const sourcesDiv = document.getElementById('sources');
        sourcesDiv.innerHTML = '<h4>Sources:</h4><ul>' + sources.map(s =>
          `<li>${s.repository} - ${s.file} (lines ${s.lines})</li>`
        ).join('') + '</ul>';
      }
    } catch (error) {
      console.error('[RAG] Search error:', error);
      resultsDiv.innerHTML = `<div class="error">Error: ${error.message}</div>`;
    }
  }

  showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
      notification.classList.add('show');
    }, 10);

    setTimeout(() => {
      notification.classList.remove('show');
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.ragApp = new RAGApp();
});
