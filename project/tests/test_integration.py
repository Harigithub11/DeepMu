import pytest
import asyncio
import tempfile
import os
from io import BytesIO

class TestEndToEndWorkflow:
    """End-to-end workflow testing"""

    @pytest.mark.asyncio
    async def test_complete_document_workflow(
        self,
        app_client,
        test_document,
        test_api_key,
        test_jwt_token
    ):
        """Test complete document workflow: upload -> process -> search -> analyze"""

        headers = {
            "Authorization": f"Bearer {test_jwt_token}",
            "X-DeepMu-API-Key": test_api_key
        }

        # Step 1: Upload document
        with open(test_document['path'], 'rb') as f:
            files = {"file": ("test_document.txt", f, "text/plain")}
            data = {"title": test_document['title'], "process_immediately": "true"}

            upload_response = await app_client.post(
                "/api/v1/documents/upload",
                files=files,
                data=data,
                headers=headers
            )

        assert upload_response.status_code == 201
        upload_data = upload_response.json()
        document_id = upload_data['document_id']

        # Step 2: Wait for processing (simulate)
        await asyncio.sleep(2)

        # Step 3: Check processing status
        status_response = await app_client.get(
            f"/api/v1/documents/{document_id}/status"
        )
        assert status_response.status_code == 200

        # Step 4: Search for the document
        search_response = await app_client.post(
            "/api/v1/search/hybrid",
            json={"text": "test document", "limit": 10},
            headers=headers
        )
        assert search_response.status_code == 200
        search_data = search_response.json()
        assert len(search_data['results']) > 0

        # Step 5: Analyze the document
        analysis_response = await app_client.post(
            "/api/v1/research/analyze",
            json={
                "document_id": document_id,
                "title": test_document['title'],
                "content": test_document['content'],
                "metadata": {"domain": "deepmu.tech"}
            },
            headers=headers
        )
        assert analysis_response.status_code == 200
        analysis_data = analysis_response.json()
        assert 'analysis' in analysis_data
        assert analysis_data['confidence_score'] > 0

        # Step 6: Clean up - delete document
        delete_response = await app_client.delete(
            f"/api/v1/documents/{document_id}",
            headers=headers
        )
        assert delete_response.status_code == 200

    @pytest.mark.asyncio
    async def test_search_accuracy(self, app_client, test_api_key):
        """Test search result accuracy and relevance"""
        headers = {"X-DeepMu-API-Key": test_api_key}

        test_queries = [
            ("artificial intelligence", ["ai", "machine", "learning"]),
            ("document processing", ["document", "process", "text"]),
            ("vector search", ["vector", "search", "similarity"])
        ]

        for query, expected_keywords in test_queries:
            response = await app_client.post(
                "/api/v1/search/hybrid",
                json={"text": query, "limit": 10},
                headers=headers
            )

            assert response.status_code == 200
            data = response.json()

            # Check response structure
            assert 'results' in data
            assert 'search_time' in data
            assert 'backends_used' in data

            # Verify search quality (if results exist)
            if data['results']:
                # Check that results contain relevant keywords
                all_content = ' '.join([
                    result.get('content', '') + ' ' + result.get('title', '')
                    for result in data['results']
                ]).lower()

                keyword_matches = sum(1 for keyword in expected_keywords if keyword in all_content)
                relevance_score = keyword_matches / len(expected_keywords)

                # At least 50% of expected keywords should appear in results
                assert relevance_score >= 0.5, f"Low relevance for query '{query}': {relevance_score}"
