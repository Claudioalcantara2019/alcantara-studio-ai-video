from fastapi.testclient import TestClient

import main


def test_cancel_queued_job():
    client = TestClient(main.app)

    job_id = "test-cancel-queued"
    main.jobs[job_id] = {
        "jobId": job_id,
        "status": "queued",
        "stage": "queued",
        "progress": 0,
        "message": "Job aguardando a GPU...",
    }

    response = client.delete(f"/jobs/{job_id}")
    assert response.status_code == 200
    assert main.jobs[job_id]["cancelRequestedAt"]
    assert main.cancel_events[job_id].is_set()

    main.cancel_events.pop(job_id, None)
    main.jobs.pop(job_id, None)


def test_cancel_completed_job_rejected():
    client = TestClient(main.app)

    job_id = "test-completed"
    main.jobs[job_id] = {
        "jobId": job_id,
        "status": "completed",
        "stage": "completed",
    }

    response = client.delete(f"/jobs/{job_id}")
    assert response.status_code == 409

    main.jobs.pop(job_id, None)


def test_cancel_unknown_job():
    client = TestClient(main.app)

    response = client.delete("/jobs/does-not-exist")
    assert response.status_code == 404


def test_cancelled_job_cannot_be_cancelled_twice():
    client = TestClient(main.app)

    job_id = "test-cancelled"
    main.jobs[job_id] = {
        "jobId": job_id,
        "status": "cancelled",
        "stage": "cancelled",
    }

    response = client.delete(f"/jobs/{job_id}")
    assert response.status_code == 409

    main.jobs.pop(job_id, None)
