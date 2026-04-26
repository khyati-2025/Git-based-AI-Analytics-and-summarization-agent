import { useState, useEffect, useCallback } from 'react';
import PlatformBadge from './components/PlatformBadge';
import RepoForm from './components/RepoForm';
import StatsPanel from './components/StatsPanel';
import CommitList from './components/CommitList';
import { detectRepo, fetchCommits, exportCommitsCSV } from './api/github';
import './index.css';

const RECENT_KEY = 'gitexplorer_recent';
const MAX_RECENT = 5;
const PER_PAGE = 30;

/* ─── Theme Toggle ──────────────────────────────────────────────────────── */
function ThemeToggle({ dark, onToggle }) {
  return (
    <button className="theme-toggle" onClick={onToggle} title={dark ? 'Switch to light mode' : 'Switch to dark mode'} aria-label="Toggle theme">
      {dark ? (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="5" /><line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" />
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
          <line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" />
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
        </svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
        </svg>
      )}
    </button>
  );
}

/* ─── Repo Info Banner ──────────────────────────────────────────────────── */
function RepoInfoBanner({ repoInfo, rateLimit, onReset }) {
  const { full_name, description, default_branch, stars, language, private: isPrivate, platform } = repoInfo;
  return (
    <div className="glass-card repo-info-banner">
      <div className="repo-info-left">
        <h2>{full_name}</h2>
        {description && <p>{description}</p>}
        <div className="repo-info-meta">
          <PlatformBadge platform={platform} />
          {isPrivate && (
            <span className="chip chip-orange">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0110 0v4" /></svg>
              Private
            </span>
          )}
          {language && <span className="chip chip-blue">{language}</span>}
          <span className="chip chip-purple">★ {stars}</span>
          <span className="chip chip-teal">⎇ {default_branch}</span>
          {rateLimit !== null && rateLimit !== undefined && (
            <span className={`chip ${rateLimit < 20 ? 'chip-red' : 'chip-green'}`} title="GitHub API requests remaining">
              {rateLimit} API calls left
            </span>
          )}
        </div>
      </div>
      <button className="btn btn-ghost btn-sm" onClick={onReset}>
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="1 4 1 10 7 10" /><path d="M3.51 15a9 9 0 102.13-9.36L1 10" /></svg>
        Switch Repo
      </button>
    </div>
  );
}

/* ─── Recent Repos ──────────────────────────────────────────────────────── */
function RecentRepos({ onSelect }) {
  const [recent, setRecent] = useState([]);

  useEffect(() => {
    try {
      setRecent(JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'));
    } catch { /* ignore */ }
  }, []);

  if (!recent.length) return null;

  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>
        Recent Repos
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
        {recent.map((r) => (
          <button
            key={r.url}
            className="btn btn-ghost btn-sm"
            onClick={() => onSelect(r)}
            title={r.url}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 00-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0020 4.77 5.07 5.07 0 0019.91 1S18.73.65 16 2.48a13.38 13.38 0 00-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 005 4.77a5.44 5.44 0 00-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 009 18.13V22" /></svg>
            {r.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function saveRecent(repoInfo, repoUrl) {
  try {
    const prev = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]');
    const entry = { url: repoUrl, label: repoInfo.full_name || repoUrl };
    const filtered = prev.filter(r => r.url !== repoUrl);
    const next = [entry, ...filtered].slice(0, MAX_RECENT);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch { /* ignore */ }
}

/* ─── Pagination Controls ───────────────────────────────────────────────── */
function Pagination({ pagination, onPageChange }) {
  if (!pagination || pagination.total_pages <= 1) return null;
  const { page, total_pages, total, per_page } = pagination;
  const from = (page - 1) * per_page + 1;
  const to = Math.min(page * per_page, total);

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '16px', flexWrap: 'wrap', gap: '10px' }}>
      <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
        Showing {from}–{to} of {total} commits
      </span>
      <div style={{ display: 'flex', gap: '6px' }}>
        <button className="btn btn-ghost btn-sm" disabled={!pagination.has_prev} onClick={() => onPageChange(page - 1)}>
          ← Prev
        </button>
        <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', padding: '0 8px' }}>
          {page} / {total_pages}
        </span>
        <button className="btn btn-ghost btn-sm" disabled={!pagination.has_next} onClick={() => onPageChange(page + 1)}>
          Next →
        </button>
      </div>
    </div>
  );
}

/* ─── Search + Export Bar ───────────────────────────────────────────────── */
function SearchBar({ value, onChange, onExport, exporting, total }) {
  return (
    <div style={{ display: 'flex', gap: '10px', marginBottom: '14px', flexWrap: 'wrap', alignItems: 'center' }}>
      <div style={{ flex: 1, position: 'relative', minWidth: '200px' }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ position: 'absolute', left: '11px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }}>
          <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          className="form-input"
          style={{ paddingLeft: '34px' }}
          type="text"
          placeholder="Search commits, authors, SHA…"
          value={value}
          onChange={e => onChange(e.target.value)}
        />
      </div>
      <button
        className="btn btn-ghost btn-sm"
        onClick={onExport}
        disabled={exporting || total === 0}
        title="Export visible commits as CSV"
      >
        {exporting ? (
          <><span className="spinner" style={{ width: '13px', height: '13px' }} /> Exporting…</>
        ) : (
          <>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>
            Export CSV
          </>
        )}
      </button>
    </div>
  );
}

/* ─── App ───────────────────────────────────────────────────────────────── */
export default function App() {
  const [phase, setPhase] = useState('form');
  const [error, setError] = useState(null);
  const [repoInfo, setRepoInfo] = useState(null);
  const [commits, setCommits] = useState([]);
  const [stats, setStats] = useState(null);
  const [pagination, setPagination] = useState(null);
  const [rateLimit, setRateLimit] = useState(null);
  const [connParams, setConnParams] = useState(null);
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [paging, setPaging] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [dark, setDark] = useState(() => {
    try { return localStorage.getItem('theme') === 'dark'; } catch { return false; }
  });

  // Theme
  useEffect(() => {
    const root = document.documentElement;
    if (dark) { root.setAttribute('data-theme', 'dark'); localStorage.setItem('theme', 'dark'); }
    else { root.removeAttribute('data-theme'); localStorage.setItem('theme', 'light'); }
  }, [dark]);

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => { setSearch(searchInput); setCurrentPage(1); }, 400);
    return () => clearTimeout(t);
  }, [searchInput]);

  // Re-fetch when page or search changes
  useEffect(() => {
    if (!connParams) return;
    loadPage(connParams, currentPage, search);
  }, [currentPage, search]); // eslint-disable-line

  async function loadPage(params, page, searchVal) {
    setPaging(true);
    try {
      const result = await fetchCommits({ ...params, page, perPage: PER_PAGE, search: searchVal });
      setCommits(result.commits);
      setStats(result.stats);
      setPagination(result.pagination);
      if (result.rate_limit_remaining !== undefined) setRateLimit(result.rate_limit_remaining);
    } catch (e) {
      setError(e.message);
    } finally {
      setPaging(false);
    }
  }

  async function handleConnect({ repoUrl, token, since, until, author, branch }) {
    setPhase('loading');
    setError(null);
    setSearch('');
    setSearchInput('');
    setCurrentPage(1);

    try {
      const info = await detectRepo(repoUrl, token);
      setRepoInfo(info);
      if (info.rate_limit_remaining !== undefined) setRateLimit(info.rate_limit_remaining);

      const platform = info.platform;
      const giteaBaseUrl = info.base_url || null;
      const params = { repoUrl, token, platform, giteaBaseUrl, since, until, author, branch };
      setConnParams(params);
      saveRecent(info, repoUrl);

      const result = await fetchCommits({ ...params, page: 1, perPage: PER_PAGE, search: '' });
      setCommits(result.commits);
      setStats(result.stats);
      setPagination(result.pagination);
      if (result.rate_limit_remaining !== undefined) setRateLimit(result.rate_limit_remaining);
      setPhase('loaded');
    } catch (e) {
      setError(e.message);
      setPhase('error');
    }
  }

  function handleReset() {
    setPhase('form');
    setError(null);
    setRepoInfo(null);
    setCommits([]);
    setStats(null);
    setPagination(null);
    setConnParams(null);
    setSearch('');
    setSearchInput('');
    setCurrentPage(1);
    setRateLimit(null);
  }

  async function handleExport() {
    if (!connParams) return;
    setExporting(true);
    try {
      await exportCommitsCSV({ ...connParams, search });
    } catch (e) {
      alert(`Export failed: ${e.message}`);
    } finally {
      setExporting(false);
    }
  }

  function handleRecentSelect({ url }) {
    // Pre-fill the form URL — trigger a full re-mount by resetting phase
    setPhase('form');
  }

  return (
    <div className="app-layout">
      {/* Header */}
      <header className="app-header">
        <div className="logo">
          <span className="logo-dot" />
          GitExplorer
        </div>
        <div style={{ flex: 1 }} />
        {repoInfo && <PlatformBadge platform={repoInfo.platform} />}
        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>GitHub &amp; Gitea</span>
        <ThemeToggle dark={dark} onToggle={() => setDark(d => !d)} />
      </header>

      <main className="app-main">
        {/* Form phase */}
        {(phase === 'form' || phase === 'loading' || phase === 'error') && (
          <>
            <RecentRepos onSelect={handleRecentSelect} />
            <RepoForm onConnect={handleConnect} loading={phase === 'loading'} />
          </>
        )}

        {/* Error banner */}
        {phase === 'error' && error && (
          <div className="error-banner">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ flexShrink: 0 }}>
              <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <div>
              <strong>Connection Failed</strong>
              <div style={{ marginTop: '3px', opacity: 0.85 }}>{error}</div>
            </div>
          </div>
        )}

        {/* Loaded view */}
        {phase === 'loaded' && repoInfo && (
          <>
            <RepoInfoBanner repoInfo={repoInfo} rateLimit={rateLimit} onReset={handleReset} />
            <StatsPanel stats={stats} repoInfo={repoInfo} />

            <div className="glass-card" style={{ padding: '16px 18px', marginBottom: '14px' }}>
              <SearchBar
                value={searchInput}
                onChange={setSearchInput}
                onExport={handleExport}
                exporting={exporting}
                total={pagination?.total || 0}
              />
              {paging && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '0.83rem' }}>
                  <span className="spinner" /> Loading commits…
                </div>
              )}
            </div>

            <CommitList
              commits={commits}
              repoUrl={connParams.repoUrl}
              token={connParams.token}
              platform={connParams.platform}
              giteaBaseUrl={connParams.giteaBaseUrl}
            />

            <Pagination
              pagination={pagination}
              onPageChange={(p) => { setCurrentPage(p); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
            />
          </>
        )}

        {/* Landing info */}
        {phase === 'form' && (
          <div className="glass-card" style={{ padding: '36px', textAlign: 'center', marginTop: '14px' }}>
            <div style={{ color: 'var(--text-muted)', marginBottom: '14px' }}>
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
            </div>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '6px' }}>How it works</h3>
            <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginBottom: '22px' }}>
              Connect any GitHub or Gitea repository to explore its commit history.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '12px', textAlign: 'left' }}>
              {[
                { icon: '🔗', title: 'Paste URL', desc: 'Enter any GitHub or Gitea repository URL' },
                { icon: '🔑', title: 'Add Token', desc: 'Personal access token for authentication' },
                { icon: '🔍', title: 'Search', desc: 'Search commits by message, author, or SHA' },
                { icon: '📊', title: 'Explore', desc: 'Browse paginated commits, click for full diffs' },
                { icon: '📥', title: 'Export', desc: 'Download commit history as a CSV file' },
                { icon: '🕓', title: 'Recent', desc: 'Quickly reconnect to recently viewed repos' },
              ].map(({ icon, title, desc }) => (
                <div key={title} style={{ background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', padding: '14px', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: '1.3rem', marginBottom: '7px' }}>{icon}</div>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem', marginBottom: '3px' }}>{title}</div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>{desc}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
