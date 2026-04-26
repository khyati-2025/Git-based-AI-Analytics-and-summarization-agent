import { useState } from 'react';
import DiffViewer from './DiffViewer';

function CopyButton({ text, label = 'Copy' }) {
    const [copied, setCopied] = useState(false);
    const handleCopy = () => {
        navigator.clipboard.writeText(text).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 1800);
        });
    };
    return (
        <button
            onClick={handleCopy}
            className="btn btn-ghost btn-sm"
            title={`Copy ${label}`}
            style={{ padding: '3px 9px', fontSize: '0.72rem' }}
        >
            {copied ? (
                <>
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12" /></svg>
                    Copied!
                </>
            ) : (
                <>
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" /></svg>
                    {label}
                </>
            )}
        </button>
    );
}

const FILE_STATUS_COLOR = {
    added: 'var(--accent-green)',
    removed: 'var(--accent-red)',
    modified: 'var(--accent-blue)',
    renamed: 'var(--accent-orange)',
};

export default function CommitDetail({ detail, loading, error }) {
    const [activeFile, setActiveFile] = useState(0);

    if (loading) {
        return (
            <div className="commit-detail" style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-secondary)' }}>
                <span className="spinner" /> Loading diff…
            </div>
        );
    }

    if (error) {
        return (
            <div className="commit-detail">
                <div className="error-banner">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ flexShrink: 0 }}>
                        <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
                    </svg>
                    {error}
                </div>
            </div>
        );
    }

    if (!detail) return null;

    const { sha, author, email, message, timestamp, additions, deletions, files = [], url } = detail;
    const [subject, ...bodyLines] = message.split('\n');
    const body = bodyLines.join('\n').trim();
    const shortDate = timestamp ? new Date(timestamp).toLocaleString() : '';

    return (
        <div className="commit-detail">
            {/* Header */}
            <div className="commit-detail-header">
                <div style={{ flex: 1, minWidth: 0 }}>
                    <h4>{subject}</h4>
                    <p style={{ marginTop: '4px', display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.76rem', color: 'var(--text-muted)' }}>{sha.slice(0, 16)}…</span>
                        <CopyButton text={sha} label="SHA" />
                        {url && (
                            <a href={url} target="_blank" rel="noreferrer" className="btn btn-ghost btn-sm" style={{ padding: '3px 9px', fontSize: '0.72rem' }}>
                                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" /><polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" /></svg>
                                Open
                            </a>
                        )}
                    </p>
                    <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                        {author} &lt;{email}&gt; &nbsp;·&nbsp; {shortDate}
                    </p>
                </div>
                <div style={{ display: 'flex', gap: '7px', flexShrink: 0 }}>
                    <span className="chip chip-green">+{additions}</span>
                    <span className="chip chip-red">-{deletions}</span>
                    <span className="chip chip-blue">{files.length} file{files.length !== 1 ? 's' : ''}</span>
                </div>
            </div>

            {/* Full commit body if present */}
            {body && (
                <pre style={{
                    fontSize: '0.79rem',
                    color: 'var(--text-secondary)',
                    background: 'var(--bg-elevated)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '10px 14px',
                    marginBottom: '14px',
                    whiteSpace: 'pre-wrap',
                    fontFamily: 'inherit',
                    border: '1px solid var(--border)',
                    lineHeight: 1.6,
                }}>
                    {body}
                </pre>
            )}

            {files.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.84rem' }}>No file changes found for this commit.</div>
            ) : (
                <>
                    {/* File tabs */}
                    <div className="file-tabs">
                        {files.map((f, i) => (
                            <button
                                key={i}
                                className={`file-tab ${activeFile === i ? 'active' : ''}`}
                                onClick={() => setActiveFile(i)}
                                title={f.filename}
                            >
                                <span style={{
                                    width: '7px', height: '7px', borderRadius: '50%', flexShrink: 0,
                                    background: FILE_STATUS_COLOR[f.status] || 'var(--text-muted)',
                                    display: 'inline-block'
                                }} />
                                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                    {f.filename.split('/').pop()}
                                </span>
                                <span style={{ color: 'var(--accent-green)', fontSize: '0.7rem' }}>+{f.additions}</span>
                                <span style={{ color: 'var(--accent-red)', fontSize: '0.7rem' }}>-{f.deletions}</span>
                            </button>
                        ))}
                    </div>

                    {/* Diff for selected file */}
                    <DiffViewer file={files[activeFile]} />
                </>
            )}
        </div>
    );
}
