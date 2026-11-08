// Preserve explicit decisions and conservatively retain results from older versions.
function mergeManualCorrections(previous, fresh) {
  const result = {...fresh};
  for (const [id, old] of Object.entries(previous)) {
    const legacy = old.origin === undefined;
    const statusManual = old.manual_status === true || (legacy && old.status !== undefined);
    const scoreManual = old.manual_score === true || (legacy && old.score !== undefined);
    if (!statusManual && !scoreManual) continue;
    const row = {...(result[id] || old)};
    if (statusManual) { row.status = old.status; row.manual_status = true; }
    if (scoreManual) { row.score = old.score; row.manual_score = true; }
    result[id] = row;
  }
  return result;
}
if (typeof module !== 'undefined') module.exports = {mergeManualCorrections};
