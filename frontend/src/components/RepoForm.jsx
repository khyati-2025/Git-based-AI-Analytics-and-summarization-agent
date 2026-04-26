import { useState, useEffect } from 'react';
import PlatformBadge from './PlatformBadge';

function detectPlatformFromUrl(url) {
    if (!url) return null;
    try {
        const u = new URL(url);
        if (u.hostname.includes('github.com')) return 'github';
        return 'gitea';
    } catch {
        return null;
    }
}

export default function RepoForm({ onConnect, loading }) {
    const [repoUrl, setRepoUrl] = useState('');
    const [token, setToken] = useState('');
    const [since, setSince] = useState('');
    const [until, setUntil] = useState('');
    const [author, setAuthor] = useState('');
    const [branch, setBranch] = useState('');
    const [platform, setPlatform] = useState(null);

    useEffect(() => {
        setPlatform(detectPlatformFromUrl(repoUrl));
    }, [repoUrl]);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!repoUrl.trim() || !token.trim()) return;
        onConnect({ repoUrl: repoUrl.trim(), token: token.trim(), since, until, author: author.trim(), branch: branch.trim() });
    };

    return (
        <div className="glass-card repo-form-card">
            <h1 className="repo-form-title">
                Git Repository Explorer
            </h1>
            <p className="repo-form-sub">
                Connect to any GitHub or Gitea repository to explore commits, changes, and diffs with line-level detail.
            </p>

            <form onSubmit={handleSubmit}>
                <div className="repo-form-grid">
                    {/* Row 1 */}
                    <div className="form-group span-2">
                        <label className="form-label">Repository URL</label>
                        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                            <input
                                className="form-input mono"
                                type="url"
                                placeholder="https://github.com/owner/repo  or  https://gitea.example.com/owner/repo"
                                value={repoUrl}
                                onChange={e => setRepoUrl(e.target.value)}
                                required
                                style={{ flex: 1 }}
                            />
                            {platform && <PlatformBadge platform={platform} />}
                        </div>
                    </div>

                    {/* Row 2 */}
                    <div className="form-group span-2">
                        <label className="form-label">Access Token</label>
                        <input
                            className="form-input mono"
                            type="password"
                            placeholder="ghp_xxxx  (GitHub)  or  Gitea personal access token"
                            value={token}
                            onChange={e => setToken(e.target.value)}
                            required
                        />
                    </div>

                    {/* Row 3 – Filters */}
                    <div className="form-group">
                        <label className="form-label">Since Date</label>
                        <input className="form-input" type="date" value={since} onChange={e => setSince(e.target.value)} />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Until Date</label>
                        <input className="form-input" type="date" value={until} onChange={e => setUntil(e.target.value)} />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Author / Username</label>
                        <input className="form-input" type="text" placeholder="Leave blank for all" value={author} onChange={e => setAuthor(e.target.value)} />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Branch</label>
                        <input className="form-input" type="text" placeholder="Leave blank for default" value={branch} onChange={e => setBranch(e.target.value)} />
                    </div>
                </div>

                <div className="repo-form-actions">
                    <button className="btn btn-primary" type="submit" disabled={loading || !repoUrl || !token}>
                        {loading ? (
                            <><span className="spinner" /> Connecting…</>
                        ) : (
                            <>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M15 3h4a2 2 0 012 2v4M9 21H5a2 2 0 01-2-2v-4M21 9l-9 9M3 15l9-9" />
                                </svg>
                                Connect &amp; Load Commits
                            </>
                        )}
                    </button>
                </div>
            </form>
        </div>
    );
}
