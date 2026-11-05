import base64
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import Literal

from pydantic import Field
from pypdf import PdfReader

from .models import StrictModel


class DocumentInput(StrictModel):
    filename: str = Field(min_length=1, max_length=160)
    contentBase64: str = Field(min_length=1, max_length=2796204)
    target: Literal["resume", "jd"]


class DocumentFailure(ValueError):
    pass


def extract_document(payload):
    try:
        raw = base64.b64decode(payload.contentBase64, validate=True)
        if not raw or len(raw) > 2 * 1024 * 1024:
            raise DocumentFailure()
        suffix = payload.filename.rsplit(".", 1)[-1].lower()
        if suffix in {"txt", "md"}:
            if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
                text = raw.decode("utf-16")
            else:
                try:
                    text = raw.decode("utf-8-sig")
                except UnicodeDecodeError:
                    text = raw.decode("gb18030")
            if "\x00" in text:
                raise DocumentFailure()
        elif suffix == "pdf":
            if not raw.startswith(b"%PDF-"):
                raise DocumentFailure()
            pdf = PdfReader(io.BytesIO(raw), strict=True)
            if pdf.is_encrypted or len(pdf.pages) > 30:
                raise DocumentFailure()
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        elif suffix == "docx":
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                if len(archive.infolist()) > 500 or sum(item.file_size for item in archive.infolist()) > 20 * 1024 * 1024:
                    raise DocumentFailure()
                info = archive.getinfo("word/document.xml")
                if info.file_size > 2 * 1024 * 1024:
                    raise DocumentFailure()
                xml = archive.read(info)
                if b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
                    raise DocumentFailure()
                document = ET.fromstring(xml)
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                text = "\n".join("".join(paragraph.itertext()) for paragraph in document.findall(".//w:p", ns))
        else:
            raise DocumentFailure()
        text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        maximum = 20000 if payload.target == "resume" else 12000
        if not text or len(text) > maximum or len([line for line in text.splitlines() if line.strip()]) > 250:
            raise DocumentFailure()
        return {"text": text, "filename": re.split(r"[/\\]", payload.filename)[-1], "format": suffix, "charCount": len(text), "warnings": []}
    except DocumentFailure:
        raise
    except Exception:
        raise DocumentFailure() from None
