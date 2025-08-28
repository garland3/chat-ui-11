"""
Tests for response builders.
"""

import os
import tempfile

from mcp_enhanced.responses import (
    artifact,
    create_mcp_response,
    deferred_artifact,
    error_response,
    success_response,
)


class TestResponses:
    def test_create_basic_response(self):
        """Test basic response creation"""
        result = create_mcp_response(results={"status": "completed"})

        assert "results" in result
        assert result["results"]["status"] == "completed"

    def test_create_response_with_artifacts(self):
        """Test response with artifacts"""
        artifacts = [artifact("test.txt", "/tmp/test.txt", description="Test file")]

        result = create_mcp_response(results={"status": "completed"}, artifacts=artifacts)

        assert "artifacts" in result
        assert len(result["artifacts"]) == 1
        assert result["artifacts"][0]["name"] == "test.txt"
        assert result["artifacts"][0]["path"] == "/tmp/test.txt"

    def test_artifact_creation(self):
        """Test artifact dictionary creation"""
        art = artifact(
            name="report.pdf",
            path="/tmp/user/report.pdf",
            description="Analysis report",
            category="report",
            viewer="pdf",
        )

        assert art["name"] == "report.pdf"
        assert art["path"] == "/tmp/user/report.pdf"
        assert art["description"] == "Analysis report"
        assert art["category"] == "report"
        assert art["viewer"] == "pdf"

    def test_artifact_with_auto_mime(self):
        """Test that MIME type is auto-detected"""
        art = artifact("test.json", "/tmp/test.json")
        assert "application/json" in art["mime"]

    def test_deferred_artifact_creation(self):
        """Test deferred artifact creation"""
        deferred = deferred_artifact(
            name="draft.md",
            path="/tmp/draft.md",
            reason="needs_editing",
            next_actions=["Complete sections", "Review"],
        )

        assert deferred["name"] == "draft.md"
        assert deferred["reason"] == "needs_editing"
        assert len(deferred["next_actions"]) == 2
        assert deferred["expires_hours"] == 72  # default

    def test_error_response(self):
        """Test error response creation"""
        error = error_response(
            "Something went wrong", reason="ValidationError", error_code="E_INVALID_INPUT"
        )

        assert error["results"]["error"] == "Something went wrong"
        assert error["meta_data"]["is_error"] is True
        assert error["meta_data"]["reason"] == "ValidationError"
        assert error["meta_data"]["error_code"] == "E_INVALID_INPUT"

    def test_success_response(self):
        """Test success response creation"""
        success = success_response({"items_processed": 42}, message="Processing complete")

        assert success["results"]["message"] == "Processing complete"
        assert success["results"]["items_processed"] == 42

    def test_artifact_with_real_file(self):
        """Test artifact creation with real file for size detection"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test content")
            temp_path = f.name

        try:
            # Create artifact from real file
            art = artifact("test.txt", temp_path)

            # Process through create_mcp_response to get size populated
            response = create_mcp_response(results={"status": "ok"}, artifacts=[art])

            # Should have size populated after processing
            assert "artifacts" in response
            processed_art = response["artifacts"][0]
            assert "size" in processed_art
            assert processed_art["size"] > 0
        finally:
            os.unlink(temp_path)
