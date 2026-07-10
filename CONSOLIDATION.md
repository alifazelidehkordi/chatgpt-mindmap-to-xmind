# Repository Consolidation Audit

This document records the consolidation of the ChatGPT mind-map repositories into one canonical project.

## Canonical repository

The repository currently named `chatgpt-mindmap-to-xmind-v3` is the canonical successor and should be renamed to:

```
chatgpt-mindmap-to-xmind
```

It is the strongest implementation because it combines Patchright/Playwright automation, parallel workers, isolated browser profiles, output locks, long-generation handling, download salvage, and richer browser/network recovery.

## Repositories reviewed

| Repository | Decision | Reason |
|------------|----------|--------|
| `chatgpt-mindmap-to-xmind-v3` | Keep and rename | Current Playwright implementation and strongest failure handling |
| `chatgpt-mindmap-to-xmind` | Rename as legacy, then archive | Older Selenium implementation; duplicated by v2 |
| `chatgpt-mindmap-to-xmind-v2` | Archive | Same README blob as the original and shared commit lineage; temporary v3 changes were later reverted |
| `chatgpt-mindmap-pipeline` | Archive | Reliability-focused Selenium predecessor; its implemented fixes are already present or superseded in v3 |
| `chatgpt-mindmap-automation` | Archive | Older OPML-only Selenium subset |

## Duplicate evidence

At the time of review, the original and v2 repositories had the same README blob SHA:

```
7b30c099c5414bb3f4e4b6e807ac54bda9874c54
```

They also share the same early commits for browser reuse, cookie pruning, and temporary-chat recovery. The v2 history contains attempted v3 imports followed by explicit reverts stating that v3 lives in its own repository.

## Reliability comparison

The optimized pipeline documented these fixes:

- three attempts with browser reset between failures
- longer download waits
- `.crdownload` settling
- multiple download-click passes
- dead-browser recreation and warm-up
- OPML XML repair and validation
- automatic index/README input filtering
- `logs/last_batch_summary.json`
- PDF, DOCX, and Markdown input support

The canonical v3 repository already contains all of them and extends them:

### Retries and recovery

`scripts/batch_common.py` includes:

- `run_with_retries()` with three attempts by default
- fresh-chat recovery between non-download failures
- browser crash detection for EPIPE, closed targets, protocol errors, and disconnected sessions
- network-error detection and connectivity waits before retrying
- browser recreation with profile-lock cleanup
- temporary-chat recovery through live cookie pruning or driver recreation
- login-session synchronization for parallel workers

### OPML repair

`scripts/opml_utils.py` in v3 and `chatgpt-mindmap-pipeline` had the same blob SHA at review time:

```
c0d1f197271c54e5819601e142ad839c0b34ea99
```

The canonical batch layer invokes `repair_and_validate_opml()` when saving downloaded OPML, and the conversion path validates inputs again before generating XMind files.

### Downloads

The v3 browser core and batch runners add:

- settling checks for partial downloads
- generic and OPML-specific download-label handling
- sandbox-link fallback
- delayed multi-pass click retries
- response-time extension while generation is still active
- long-generation stop and post-stop salvage

### Batch summaries and partial success

Both PDF and Markdown runners write `logs/last_batch_summary.json` with success and failure counts, failed item names, paths, and timeout settings.

The pipeline invokes OPML-to-XMind conversion even when OPML generation returns a partial-failure exit code, so successful intermediate files are still converted.

### Parallel safety

V3 adds features not present in the optimized Selenium pipeline:

- per-output lock files
- stale-lock reclamation
- isolated profiles, downloads, and logs per worker
- worker range selection
- login-session copying instead of concurrent interactive login

## Merge decision

No pipeline-only reliability code needed to be transplanted. The v3 implementation is a strict functional superset of the reliability layer found in `chatgpt-mindmap-pipeline`.

The unique material worth carrying forward was the predecessor's explicit operational documentation. That information has been incorporated into the canonical README under **Reliability and recovery**.

## Safe rename and archive order

The requested canonical name is already occupied by the original repository. Archiving a repository does **not** release its name, so the original must be renamed before v3 can take the canonical name.

Use this order:

1. Rename the original repository:
   - `chatgpt-mindmap-to-xmind` → `chatgpt-mindmap-to-xmind-v1`
2. Rename the successor:
   - `chatgpt-mindmap-to-xmind-v3` → `chatgpt-mindmap-to-xmind`
3. Archive the four legacy repositories:
   - `chatgpt-mindmap-to-xmind-v1`
   - `chatgpt-mindmap-to-xmind-v2`
   - `chatgpt-mindmap-pipeline`
   - `chatgpt-mindmap-automation`
4. Confirm the canonical repository's default branch, description, topics, Actions permissions, branch protections, and external integrations after the rename.

## Post-rename checks

- Clone URL resolves to `alifazelidehkordi/chatgpt-mindmap-to-xmind`.
- README setup commands use `cd chatgpt-mindmap-to-xmind`.
- No active workflow, deployment, local remote, or documentation still relies on the `-v3` name.
- Archived repositories display a link to the canonical successor.
- The canonical repository remains public unless visibility is intentionally changed.
