import { useState } from 'react';
import CommitDetail from './CommitDetail';
import { fetchCommitDetail } from '../api/github';

function classifyCommit(message) {
    const msg = message.toLowerCase();
    if (/fix|bug|issue|patch/.test(msg)) return { label: 'bugfix', cls: 'chip-red' };
    if (/feat|add|implement/.test(msg)) return { label: 'feature', cls: 'chip-green' };
    if (/doc|readme|markdown/.test(msg)) return { label: 'docs', cls: 'chip-teal' };
    if (/refactor|cleanup|restructure/.test(msg)) return { label: 'refactor', cls: 'chip-purple' };
    if (/test|spec|coverage/.test(msg)) return { label: 'test', cls: 'chip-orange' };
    return { label: 'other', cls: 'chip-blue' };
}

function formatRelTime(isoStr) {
    if (!isoStr) return '';
    const diff = Date.now() - new Date(isoStr).getTime();
    const s = Math.floor(diff / 1000);
    if (s < 60) return `${s}s ago`;
    const m = Math.floor(s / 60);
    if (m < 60) return `${m}m ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h ago`;
    const d = Math.floor(h / 24);
    if (d < 30) return `${d}d ago`;
    return new Date(isoStr).toLocaleDateString();
}

function CommitRow({ commit, repoUrl, token, platform, giteaBaseUrl }) {
    const [expanded, setExpanded] = useState(false);
    const [detail, setDetail] = useState(null);
    const [loadingD, setLoadingD] = useState(false);
    const [errorD, setErrorD] = useState(null);

    const category = classifyCommit(commit.message);

    const handleExpand = async () => {
        const next = !expanded;
        setExpanded(next);
        if (next && !detail) {
            setLoadingD(true);
            setErrorD(null);
            try {
                const d = await fetchCommitDetail({ repoUrl, token, platform, giteaBaseUrl, sha: commit.sha });
                setDetail(d);
            } catch (e) {
                setErrorD(e.message);
            } finally {
                setLoadingD(false);
            }
        }
    };

    return (
        <div className={`commit-card ${expanded ? 'expanded' : ''}`}>
            <div className="commit-row" onClick={handleExpand}>
                <div className="commit-icon">{commit.short_sha}</div>
                <div className="commit-info">
                    <div className="commit-message">{commit.message.split('\n')[0]}</div>
                    <div className="commit-meta">
                        <span>
                            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2M12 11a4 4 0 100-8 4 4 0 000 8z" />
                            </svg>
                            {commit.author}
                        </span>
                        <span>
                            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
                            </svg>
                            {formatRelTime(commit.timestamp)}
                        </span>
                        <span>{new Date(commit.timestamp).toLocaleDateString()}</span>
                        <span className={`chip ${category.cls}`} style={{ padding: '1px 7px', fontSize: '0.7rem' }}>{category.label}</span>
                    </div>
                </div>

                <div className="commit-stats">
                    <span className="chip chip-blue">{commit.files_changed} file{commit.files_changed !== 1 ? 's' : ''}</span>
                    <span className="chip chip-green">+{commit.additions}</span>
                    <span className="chip chip-red">-{commit.deletions}</span>
                </div>

                <svg className={`commit-expand-icon ${expanded ? 'rotated' : ''}`} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="9 18 15 12 9 6" />
                </svg>
            </div>

            {expanded && (
                <CommitDetail
                    detail={detail}
                    loading={loadingD}
                    error={errorD}
                />
            )}
        </div>
    );
}

export default function CommitList({ commits, repoUrl, token, platform, giteaBaseUrl }) {
    if (!commits || commits.length === 0) {
        return (
            <div className="glass-card">
                <div className="empty-state">
                    <div className="icon" style={{ display: 'flex', justifyContent: 'center', marginBottom: '16px', color: 'var(--text-muted)' }}>
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                            <rect x="2" y="3" width="20" height="14" rx="2" ry="2" /><path d="M8 21h8" /><path d="M12 17v4" />
                        </svg>
                    </div>
                    <h3>No commits found</h3>
                    <p>Try adjusting your date range or filters, then reconnect.</p>
                </div>
            </div>
        );
    }

    return (
        <div>
            <div className="commits-header">
                <h3>Commits <span style={{ color: 'var(--text-secondary)', fontWeight: 400 }}>({commits.length})</span></h3>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Click any commit to view file diffs</span>
            </div>
            <div className="commits-list">
                {commits.map(c => (
                    <CommitRow
                        key={c.sha}
                        commit={c}
                        repoUrl={repoUrl}
                        token={token}
                        platform={platform}
                        giteaBaseUrl={giteaBaseUrl}
                    />
                ))}
            </div>
        </div>
    );
}
