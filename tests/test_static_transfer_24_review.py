from pathlib import Path

from main_review.static_transfer_24_review import run_static_transfer_24_review


def _run(tmp_path: Path, files: dict[str, str]):
    for relative, content in files.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return run_static_transfer_24_review(tmp_path, files)


def test_detects_lazy_ruby_state_after_shareability_boundary(tmp_path: Path):
    result = _run(
        tmp_path,
        {
            "cache.rb": """
module LocalCache
  def local_cache_key
    @local_cache_key ||= object_id.to_s
  end
end
""",
            "application.rb": """
class Application
  def ractorize!
    routes
    Ractor.make_shareable(self)
  end
end
""",
        },
    )
    assert [item["root_cause"] for item in result["findings"]] == [
        "lazy-state-initialized-after-freeze-or-shareability-boundary"
    ]


def test_allows_ruby_state_initialized_before_freeze(tmp_path: Path):
    result = _run(
        tmp_path,
        {
            "cache.rb": """
module LocalCache
  def initialize
    @local_cache_key = object_id.to_s
  end
  def local_cache_key
    @local_cache_key ||= object_id.to_s
  end
end
""",
            "application.rb": """
class Application
  def ractorize!
    Ractor.make_shareable(self)
  end
end
""",
        },
    )
    assert result["findings"] == []


def test_detects_retry_limit_hidden_behind_exception_path(tmp_path: Path):
    result = _run(
        tmp_path,
        {
            "Worker.php": """<?php
function waitForChildProcess($pid) { posix_kill($pid, SIGKILL); }
function process($job, $options) { try { $job->fire(); } catch (Exception $e) { handleJobException($job, $options, $e); } }
function handleJobException($job, $options, $e) { markJobAsFailedIfHasExceededMaxAttempts($job, $options->maxTries, $e); }
function markJobAsFailedIfHasExceededMaxAttempts($job, $max, $e) { if ($job->attempts() < $max) return; }
"""
        },
    )
    assert [item["root_cause"] for item in result["findings"]] == [
        "retry-limit-enforced-only-after-catchable-job-failure"
    ]


def test_allows_attempt_check_before_job_execution(tmp_path: Path):
    result = _run(
        tmp_path,
        {
            "Worker.php": """<?php
function waitForChildProcess($pid) { posix_kill($pid, SIGKILL); }
function process($job, $options) { if ($job->attempts() > $options->maxTries) fail($job); $job->fire(); }
function markJobAsFailedIfHasExceededMaxAttempts($job, $max, $e) { if ($job->attempts() < $max) return; }
"""
        },
    )
    assert result["findings"] == []


def test_detects_protocol_literal_version_mismatch(tmp_path: Path):
    result = _run(
        tmp_path,
        {
            "HTTPEncoder.swift": """
switch response {
case (1, 0, .networkAuthenticationRequired):
    self.writeStaticString("HTTP/1.1 511 Network Authentication Required\\r\\n")
}
"""
        },
    )
    assert [item["root_cause"] for item in result["findings"]] == [
        "protocol-fast-path-literal-disagrees-with-switch-discriminant"
    ]


def test_allows_protocol_literal_matching_discriminant(tmp_path: Path):
    result = _run(
        tmp_path,
        {
            "HTTPEncoder.swift": """
switch response {
case (1, 0, .networkAuthenticationRequired):
    self.writeStaticString("HTTP/1.0 511 Network Authentication Required\\r\\n")
}
"""
        },
    )
    assert result["findings"] == []
