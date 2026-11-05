"""Synthetic files are built in memory; no original resumes or binary fixtures."""
import base64
import io
import zipfile

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.documents import DocumentFailure, DocumentInput, extract_document
from app.main import app


def document(raw, filename="synthetic.txt", target="resume"):
    return DocumentInput(filename=filename, contentBase64=base64.b64encode(raw).decode(), target=target)


def pdf_bytes(text=None, pages=1, encrypted=False):
    writer = PdfWriter()
    for _ in range(pages):
        page = writer.add_blank_page(width=612, height=792)
        if text:
            font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
            page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
            stream = DecodedStreamObject()
            stream.set_data(f"BT /F1 12 Tf 50 700 Td ({text}) Tj ET".encode("ascii"))
            page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("synthetic-fixture-password")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def docx_bytes(xml):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", xml)
    return output.getvalue()


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "utf-16", "gb18030"])
def test_text_encodings_preserve_synthetic_material(encoding):
    text = "项目经历\n虚构课程平台使用 Java 和 Spring Boot 编写 REST API。"
    result = extract_document(document(text.encode(encoding)))
    assert result["text"] == text
    assert result["charCount"] == len(text)
    assert result["warnings"] == []


def test_markdown_keeps_editable_content_and_normalizes_newlines():
    result = extract_document(document(b"# Synthetic resume\r\nJava and Docker\rSQL", "SYNTHETIC.MD"))
    assert result["text"] == "# Synthetic resume\nJava and Docker\nSQL"
    assert result["format"] == "md"


def test_pdf_with_real_text_layer():
    result = extract_document(document(pdf_bytes("Synthetic Java Spring Boot resume"), "synthetic.pdf"))
    assert "Synthetic Java Spring Boot resume" in result["text"]
    assert result["format"] == "pdf"


@pytest.mark.parametrize("raw", [pdf_bytes(), pdf_bytes("Synthetic", encrypted=True), pdf_bytes("Synthetic", pages=31), b"not a pdf"], ids=["scan-only", "encrypted", "too-many-pages", "forged-extension"])
def test_unusable_pdf_is_rejected(raw):
    with pytest.raises(DocumentFailure):
        extract_document(document(raw, "synthetic.pdf"))


def test_docx_extracts_paragraphs_without_saving_archive():
    xml = b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Synthetic Java</w:t></w:r></w:p><w:p><w:r><w:t>Docker SQL</w:t></w:r></w:p></w:body></w:document>'
    result = extract_document(document(docx_bytes(xml), "synthetic.docx"))
    assert result["text"] == "Synthetic Java\nDocker SQL"


@pytest.mark.parametrize("raw", [b"<broken", b'<!DOCTYPE doc [<!ENTITY x "synthetic">]><doc>&x;</doc>', b"x" * (2 * 1024 * 1024 + 1)], ids=["malformed-xml", "entity", "expanded-size"])
def test_docx_malformed_entities_and_expansion_limits(raw):
    with pytest.raises(DocumentFailure):
        extract_document(document(docx_bytes(raw), "synthetic.docx"))


@pytest.mark.parametrize("raw,filename,target", [(b"", "empty.txt", "resume"), (b"\x00Java", "binary.txt", "resume"), (b"Java", "resume.exe", "resume"), (b"x" * 20001, "long.txt", "resume"), (b"x" * 12001, "long.txt", "jd"), (b"line\n" * 251, "lines.txt", "resume")], ids=["empty", "nul", "extension", "resume-limit", "jd-limit", "line-limit"])
def test_file_boundaries_are_enforced(raw, filename, target):
    with pytest.raises((DocumentFailure, ValidationError)):
        extract_document(document(raw, filename, target))


def test_invalid_base64_and_unknown_target():
    with pytest.raises(DocumentFailure):
        extract_document(DocumentInput(filename="bad.txt", contentBase64="%%%", target="resume"))
    with pytest.raises(ValidationError):
        document(b"Synthetic", target="other")


async def test_document_http_envelope_trace_and_private_error():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic") as client:
        response = await client.post("/internal/v1/documents/text", json=document(b"Synthetic Java resume").model_dump())
        assert response.status_code == 200
        assert set(response.json()) == {"code", "msg", "data"}
        assert response.headers["X-Trace-Id"] and response.headers["Cache-Control"] == "no-store"
        invalid = await client.post("/internal/v1/documents/text", json=document(b"SYNTHETIC_PRIVATE_CANARY", "bad.pdf").model_dump())
        assert invalid.status_code == 422
        assert "SYNTHETIC_PRIVATE_CANARY" not in invalid.text
        extra = await client.post("/internal/v1/documents/text", json={**document(b"Synthetic").model_dump(), "url": "https://example.invalid"})
        assert extra.status_code == 400
