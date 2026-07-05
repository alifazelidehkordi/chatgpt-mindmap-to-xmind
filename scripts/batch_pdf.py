from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import batch_common as common
import run_chatgpt_temporary_test as core


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_DIR = ROOT / "inputs"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "opml"
DEFAULT_PROMPT = ROOT / "prompts" / "prompt-mind-map.md"
LOCK_STALE_SECONDS = int(os.environ.get("BATCH_LOCK_STALE_SECONDS", "21600"))


def acquire_output_lock(output_path: Path) -> Path | None:
    lock_dir = output_path.parent / ".locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / f"{output_path.name}.lock"
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(lock_path, flags)
    except FileExistsError:
        if time.time() - lock_path.stat().st_mtime <= LOCK_STALE_SECONDS:
            return None
        lock_path.unlink(missing_ok=True)
        try:
            fd = os.open(lock_path, flags)
        except FileExistsError:
            return None
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(f"pid={os.getpid()} time={int(time.time())}\n")
    return lock_path


def release_output_lock(lock_path: Path | None) -> None:
    if lock_path is not None:
        lock_path.unlink(missing_ok=True)


def process_one(
    driver,
    prompt: str,
    input_path: Path,
    output_dir: Path,
    model: str | None,
    *,
    download_timeout: int,
    response_timeout: int,
    save_diagnostics: bool,
) -> bool:
    output_path = output_dir / f"{input_path.stem}.opml"
    common.batch_log(f"Processing: {input_path.name}")

    core.start_new_chat(driver)
    if model:
        core.select_model(driver, model)

    before_downloads = set(core.DOWNLOAD_DIR.glob("*"))
    core.attach_file(driver, input_path, native_upload=False)
    core.wait_for_file_upload_complete(driver, input_path)

    expected_assistant_count = core.assistant_message_count(driver) + 1
    core.send_message(driver, prompt)
    core.wait_until_idle(
        driver,
        timeout=response_timeout,
        min_assistant_count=expected_assistant_count,
    )

    time.sleep(2)
    downloaded = core.resolve_download(driver, before_downloads, timeout=download_timeout)
    if downloaded is None:
        common.batch_log("Retrying download click after link render wait...")
        time.sleep(5)
        downloaded = core.resolve_download(driver, before_downloads, timeout=download_timeout)

    if downloaded is None:
        response_text = core.latest_assistant_text(driver)
        if save_diagnostics:
            diagnostic_stem = core.safe_filename(input_path.stem)
            (output_dir / f"{diagnostic_stem}.last_response.txt").write_text(
                response_text,
                encoding="utf-8",
            )
            driver.save_screenshot(str(output_dir / f"{diagnostic_stem}.last_state.png"))
        common.batch_log(f"FAILED: no downloadable OPML detected for {input_path.name}")
        common.batch_log(
            "   Hint: check downloads/, enable --save-diagnostics, or rerun with --overwrite."
        )
        return False

    common.save_artifact_download(downloaded, output_path)
    common.batch_log(f"Saved OPML: {output_path}")
    return True


def run_batch(
    input_dir: Path,
    output_dir: Path,
    prompt_path: Path,
    overwrite: bool = False,
    limit: int | None = None,
    model: str | None = None,
    save_diagnostics: bool = False,
    max_attempts: int = 3,
    download_timeout: int = 90,
    response_timeout: int = 600,
    close_delay: int = 20,
    skip_warmup: bool = False,
    keep_browser: bool = False,
    start_index: int | None = None,
    end_index: int | None = None,
) -> int:
    core.LOG_FILE.write_text("", encoding="utf-8")
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        raise FileNotFoundError(input_dir)
    if not prompt_path.exists():
        raise FileNotFoundError(prompt_path)

    input_files = common.collect_input_files(input_dir)
    if start_index is not None or end_index is not None:
        start = 1 if start_index is None else start_index
        end = len(input_files) if end_index is None else end_index
        if start < 1 or end < start:
            raise ValueError("--start-index/--end-index must be a valid 1-based range")
        input_files = input_files[start - 1 : end]
    if limit is not None:
        input_files = input_files[:limit]
    if not input_files:
        common.batch_log(f"No PDF, DOCX, MD, or TEX files found in {input_dir}")
        return 1

    prompt = prompt_path.read_text(encoding="utf-8").strip()
    if not prompt:
        raise ValueError("Prompt file is empty.")

    common.batch_log(f"Input folder: {input_dir}")
    common.batch_log(f"Output folder: {output_dir}")
    common.batch_log(f"File count: {len(input_files)}")
    common.batch_log(f"Max attempts per file: {max_attempts}")
    common.batch_log(f"Download timeout: {download_timeout}s")
    common.batch_log(f"Response timeout: {response_timeout}s")

    driver = common.bootstrap_session(model, skip_warmup=skip_warmup)
    successes = 0
    failures: list[str] = []

    try:
        for index, input_path in enumerate(input_files, start=1):
            output_path = output_dir / f"{input_path.stem}.opml"
            if output_path.exists() and not overwrite:
                common.batch_log(f"Skipping existing ({index}/{len(input_files)}): {output_path.name}")
                successes += 1
                continue

            lock_path = acquire_output_lock(output_path)
            if lock_path is None:
                common.batch_log(
                    f"Skipping claimed by another worker ({index}/{len(input_files)}): {output_path.name}"
                )
                successes += 1
                continue

            if output_path.exists() and not overwrite:
                common.batch_log(f"Skipping existing ({index}/{len(input_files)}): {output_path.name}")
                release_output_lock(lock_path)
                successes += 1
                continue

            common.batch_log(f"Starting file {index}/{len(input_files)}")

            def attempt(driver_obj):
                return process_one(
                    driver_obj,
                    prompt,
                    input_path,
                    output_dir,
                    model,
                    download_timeout=download_timeout,
                    response_timeout=response_timeout,
                    save_diagnostics=save_diagnostics,
                )

            try:
                ok, driver = common.run_with_retries(
                    input_path.name,
                    driver,
                    model,
                    attempt,
                    max_attempts=max_attempts,
                    skip_warmup=skip_warmup,
                )
            finally:
                release_output_lock(lock_path)
            if ok:
                successes += 1
            else:
                failures.append(input_path.name)
            common.prune_driver_cookies(driver)

        common.batch_log(f"Batch complete. Successes: {successes}. Failures: {len(failures)}.")
        if failures:
            common.batch_log("Failed files:")
            for name in failures:
                common.batch_log(f"- {name}")

        common.write_batch_summary(
            mode="pdf-opml",
            successes=successes,
            failures=failures,
            output_dir=output_dir,
            extra={
                "input_dir": str(input_dir),
                "max_attempts": max_attempts,
                "download_timeout": download_timeout,
                "response_timeout": response_timeout,
            },
        )
        return 0 if not failures else 2
    finally:
        if keep_browser:
            common.batch_log("Keeping browser open (--keep-browser).")
        else:
            common.batch_log(f"Closing browser in {close_delay} seconds...")
            time.sleep(close_delay)
            common.quit_driver(driver)


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch convert PDF/DOCX/MD files to OPML via ChatGPT web.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--model", default=None)
    parser.add_argument("--save-diagnostics", action="store_true")
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--download-timeout", type=int, default=90)
    parser.add_argument("--response-timeout", type=int, default=600)
    parser.add_argument("--close-delay", type=int, default=20)
    parser.add_argument("--no-warm-up", action="store_true")
    parser.add_argument("--keep-browser", action="store_true")
    parser.add_argument("--start-index", type=int, help="1-based first input file to process")
    parser.add_argument("--end-index", type=int, help="1-based last input file to process")
    args = parser.parse_args()

    try:
        return run_batch(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            prompt_path=args.prompt,
            overwrite=args.overwrite,
            limit=args.limit,
            model=args.model,
            save_diagnostics=args.save_diagnostics,
            max_attempts=args.max_attempts,
            download_timeout=args.download_timeout,
            response_timeout=args.response_timeout,
            close_delay=args.close_delay,
            skip_warmup=args.no_warm_up,
            keep_browser=args.keep_browser,
            start_index=args.start_index,
            end_index=args.end_index,
        )
    except Exception as exc:
        core.log(f"ERROR: {exc}")
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())