const API_BASE = 'http://localhost:8001';

async function apiFetch(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    // Surface friendly error messages
    const msg = data.detail || `API error ${res.status}`;
    const err = new Error(msg);
    err.status = res.status;
    throw err;
  }
  return data;
}

export async function detectRepo(repoUrl, token) {
  return apiFetch('/api/detect', { repo_url: repoUrl, token });
}

export async function fetchCommits({ repoUrl, token, platform, giteaBaseUrl, since, until, author, branch, page = 1, perPage = 30, search = '' }) {
  return apiFetch('/api/commits', {
    repo_url: repoUrl,
    token,
    platform,
    gitea_base_url: giteaBaseUrl || null,
    since: since || null,
    until: until || null,
    author: author || null,
    branch: branch || null,
    page,
    per_page: perPage,
    search: search || null,
  });
}

export async function fetchCommitDetail({ repoUrl, token, platform, giteaBaseUrl, sha }) {
  return apiFetch('/api/commit/detail', {
    repo_url: repoUrl,
    token,
    platform,
    gitea_base_url: giteaBaseUrl || null,
    sha,
  });
}

/**
 * Trigger a CSV export download — POSTs to the backend, then creates a
 * temporary <a> element to initiate a browser download.
 */
export async function exportCommitsCSV({ repoUrl, token, platform, giteaBaseUrl, since, until, author, branch, search }) {
  const res = await fetch(`${API_BASE}/api/export/csv`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      repo_url: repoUrl,
      token,
      platform,
      gitea_base_url: giteaBaseUrl || null,
      since: since || null,
      until: until || null,
      author: author || null,
      branch: branch || null,
      search: search || null,
    }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Export failed (${res.status})`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const disposition = res.headers.get('content-disposition') || '';
  const nameMatch = disposition.match(/filename="?([^"]+)"?/);
  const filename = nameMatch ? nameMatch[1] : 'commits.csv';
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
