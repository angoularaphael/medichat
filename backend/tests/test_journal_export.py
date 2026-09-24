def test_journal_export_csv_and_pdf(client):
    confirmed = client.post(
        "/api/care/confirm",
        json={"crew_member_code": "elisa", "drug_code": "paracetamol", "dose_mg": 500},
    )
    assert confirmed.status_code == 200

    csv_response = client.get("/api/journal/export.csv")
    assert csv_response.status_code == 200
    assert "text/csv" in csv_response.headers["content-type"]
    assert "attachment" in csv_response.headers["content-disposition"]
    text = csv_response.content.decode("utf-8-sig")
    assert "horodatage;origine;action;resume;detail" in text
    assert "care_confirm" in text

    pdf_response = client.get("/api/journal/export.pdf")
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF")
    assert b"care_confirm" in pdf_response.content
    assert b"%%EOF" in pdf_response.content
