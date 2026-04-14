from orchestrator.acceptance import ACCEPTANCE_QUESTIONS, run_acceptance


def test_acceptance_dataset_passes_with_fake_runner() -> None:
    report = run_acceptance(
        runner_name="fake",
        model="unused",
        base_url="http://localhost:11434",
    )

    assert report.total_cases == len(ACCEPTANCE_QUESTIONS)
    assert report.failed_cases == 0
    assert all(case.passed for case in report.case_results)
