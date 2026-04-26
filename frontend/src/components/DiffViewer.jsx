const STATUS_CLASS = {
    added: 'chip-green',
    removed: 'chip-red',
    modified: 'chip-blue',
    renamed: 'chip-orange',
};

function DiffLine({ line }) {
    const typeClass = {
        addition: 'diff-line-addition',
        deletion: 'diff-line-deletion',
        hunk: 'diff-line-hunk',
        context: 'diff-line-context',
    }[line.type] || '';

    const sign = { addition: '+', deletion: '-', hunk: '…', context: ' ' }[line.type] || '';

    return (
        <tr className={typeClass}>
            <td className="diff-gutter diff-gutter-old">{line.old_line ?? ''}</td>
            <td className="diff-gutter diff-gutter-sep">{line.new_line ?? ''}</td>
            <td className="diff-sign">{sign}</td>
            <td className="diff-content">{line.content}</td>
        </tr>
    );
}

export default function DiffViewer({ file }) {
    if (!file) return null;

    const { filename, status, additions, deletions, diff_lines = [] } = file;
    const statusCls = STATUS_CLASS[status] || 'chip-blue';

    if (diff_lines.length === 0) {
        return (
            <div className="diff-viewer">
                <div className="diff-header">
                    <span className="diff-filename">{filename}</span>
                    <span style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                        No diff available (binary or empty)
                    </span>
                </div>
            </div>
        );
    }

    return (
        <div className="diff-viewer">
            <div className="diff-header">
                <span className="diff-filename">{filename}</span>
                <div className="diff-file-stats">
                    <span className="chip chip-green">+{additions}</span>
                    <span className="chip chip-red">-{deletions}</span>
                    <span className={`chip ${statusCls}`} style={{ textTransform: 'capitalize' }}>{status}</span>
                </div>
            </div>
            <div className="diff-body">
                <table className="diff-table">
                    <tbody>
                        {diff_lines.map((line, i) => (
                            <DiffLine key={i} line={line} />
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
