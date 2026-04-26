export default function StatsPanel({ stats, repoInfo }) {
    if (!stats) return null;

    const { total_commits, total_additions, total_deletions, contributors } = stats;
    const contributorList = Object.entries(contributors || {});

    const initials = (name) => name.split(' ').map(p => p[0]).join('').toUpperCase().slice(0, 2);

    const netChange = total_additions - total_deletions;

    return (
        <div style={{ marginBottom: '20px' }}>
            {/* Main Stats */}
            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-label">Total Commits</div>
                    <div className="stat-value" style={{ color: 'var(--accent-blue)' }}>{total_commits}</div>
                    <div className="stat-sub">in selected range</div>
                </div>

                <div className="stat-card">
                    <div className="stat-label">Additions</div>
                    <div className="stat-value" style={{ color: 'var(--accent-green)' }}>+{total_additions.toLocaleString()}</div>
                    <div className="stat-sub">lines added</div>
                </div>

                <div className="stat-card">
                    <div className="stat-label">Deletions</div>
                    <div className="stat-value" style={{ color: 'var(--accent-red)' }}>-{total_deletions.toLocaleString()}</div>
                    <div className="stat-sub">lines removed</div>
                </div>

                <div className="stat-card">
                    <div className="stat-label">Contributors</div>
                    <div className="stat-value" style={{ color: 'var(--accent-purple)' }}>{contributorList.length}</div>
                    <div className="stat-sub">unique authors</div>
                </div>

                <div className="stat-card">
                    <div className="stat-label">Net Change</div>
                    <div className="stat-value" style={{ color: netChange >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                        {netChange >= 0 ? '+' : ''}{netChange.toLocaleString()}
                    </div>
                    <div className="stat-sub">net lines changed</div>
                </div>
            </div>

            {/* Contributors */}
            {contributorList.length > 0 && (
                <div className="glass-card" style={{ padding: '18px' }}>
                    <h3 style={{ fontSize: '0.92rem', fontWeight: 700, marginBottom: '3px' }}>Contributors</h3>
                    <p style={{ fontSize: '0.79rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>Breakdown by author</p>
                    <div className="contributors-grid">
                        {contributorList.map(([name, info]) => (
                            <div className="contributor-card" key={name}>
                                <div className="contributor-avatar">{initials(name)}</div>
                                <div className="contributor-info">
                                    <div className="contributor-name" title={name}>{name}</div>
                                    <div className="contributor-stats">
                                        {info.commits} commits &nbsp;·&nbsp;
                                        <span style={{ color: 'var(--accent-green)' }}>+{info.additions}</span>
                                        &nbsp;
                                        <span style={{ color: 'var(--accent-red)' }}>-{info.deletions}</span>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
