def classify_document(page_count: int, word_count: int, character_count: int, text: str) -> dict[str, str]:
    if word_count < 100 and page_count <= 2:
        return {
            "document_quality": "insufficient_rfp_detail",
            "status": "needs_more_detail",
            "reason": "Document has very little text and cannot support RFP analysis.",
        }

    if page_count >= 3 and word_count < 300:
        return {
            "document_quality": "extraction_needs_review",
            "status": "extraction_needs_review",
            "reason": "Document has multiple pages but very little extractable text. It may be scanned or image-based.",
        }

    if word_count >= 500:
        return {
            "document_quality": "valid_rfp",
            "status": "ready_for_private_chat",
            "reason": "Document contains enough text for private local analysis.",
        }

    return {
        "document_quality": "limited_but_valid",
        "status": "ready_for_private_chat",
        "reason": "Document has limited detail but can support basic private chat.",
    }
