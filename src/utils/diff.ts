import { diff_match_patch } from 'diff-match-patch';

export interface DiffResult {
  originalHtml: string;
  modifiedHtml: string;
}

/**
 * Computes the difference between two strings and returns HTML representations
 * with deletions (red) and insertions (green) highlighted.
 */
export function computeTextDiff(original: string, modified: string): DiffResult {
  const dmp = new diff_match_patch();
  const diffs = dmp.diff_main(original, modified);
  
  // Cleanup for human readability (groups small changes)
  dmp.diff_cleanupSemantic(diffs);

  let originalHtml = '';
  let modifiedHtml = '';

  diffs.forEach(([operation, text]) => {
    switch (operation) {
      case 0: // Equal
        originalHtml += escapeHtml(text);
        modifiedHtml += escapeHtml(text);
        break;
      case -1: // Delete
        originalHtml += `<span class="bg-red-100 text-red-700 line-through decoration-2">${escapeHtml(text)}</span>`;
        break;
      case 1: // Insert
        modifiedHtml += `<span class="bg-green-100 text-green-700 underline decoration-2">${escapeHtml(text)}</span>`;
        break;
    }
  });

  return {
    originalHtml,
    modifiedHtml,
  };
}

function escapeHtml(text: string): string {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  };
  return text.replace(/[&<>"']/g, (m) => map[m]);
}
