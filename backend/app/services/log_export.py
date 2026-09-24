import csv
import io
import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.entities import DecisionLog, SecurityAlert

COLUMNS = ("horodatage", "origine", "action", "resume", "detail")


def _iso(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def collect_rows(db: Session, *, include_alerts: bool, limit: int = 1000) -> list[dict]:
    decisions = (
        db.query(DecisionLog)
        .order_by(DecisionLog.created_at.desc())
        .limit(limit)
        .all()
    )
    rows = [
        {
            "horodatage": _iso(entry.created_at),
            "origine": "decision",
            "action": entry.action,
            "resume": entry.summary,
            "detail": json.dumps(
                {"payload": entry.payload or {}, "stock": entry.stock_snapshot},
                ensure_ascii=False,
            ),
        }
        for entry in decisions
    ]
    if include_alerts:
        alerts = (
            db.query(SecurityAlert)
            .order_by(SecurityAlert.created_at.desc())
            .limit(limit)
            .all()
        )
        for alert in alerts:
            payload = alert.payload or {}
            rows.append(
                {
                    "horodatage": _iso(alert.created_at),
                    "origine": alert.source or "alerte",
                    "action": str(payload.get("alert") or "alerte"),
                    "resume": str(payload.get("message") or "Alerte reseau"),
                    "detail": json.dumps(payload, ensure_ascii=False),
                }
            )
    rows.sort(key=lambda row: row["horodatage"], reverse=True)
    return rows


def to_csv(rows: list[dict]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, delimiter=";", lineterminator="\n")
    writer.writeheader()
    if rows:
        writer.writerows(rows)
    else:
        writer.writerow(
            {
                "horodatage": "",
                "origine": "decision",
                "action": "vide",
                "resume": "Aucune entree",
                "detail": "",
            }
        )
    return buffer.getvalue().encode("utf-8-sig")


def _pdf_text(value: str) -> bytes:
    raw = value.encode("cp1252", errors="replace")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _wrap(text: str, width: int = 90) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        if len(current) + 1 + len(word) <= width:
            current = f"{current} {word}"
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def to_pdf(rows: list[dict]) -> bytes:
    lines = ["EIR - Journal de mission", "Export local. Aucune copie n'est envoyee vers la Terre.", ""]
    if not rows:
        lines.append("Aucune entree.")
    for row in rows:
        lines.extend(
            _wrap(f"{row['horodatage']} | {row['origine']} | {row['action']}")
        )
        lines.extend(_wrap(f"  {row['resume']}"))
        lines.append("")
    return _render_pdf(lines)


def _render_pdf(lines: list[str]) -> bytes:
    chunks = [lines[index : index + 40] for index in range(0, len(lines), 40)] or [[]]
    count = len(chunks)
    objects: list[bytes] = [b""] * (3 + count * 2)
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{4 + index} 0 R" for index in range(count))
    objects[1] = f"<< /Type /Pages /Count {count} /Kids [{kids}] >>".encode()
    objects[2] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    for index, chunk in enumerate(chunks):
        stream = _page_stream(chunk)
        content_id = 4 + count + index
        objects[3 + index] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Contents {content_id} 0 R /Resources << /Font << /F1 3 0 R >> >> >>"
        ).encode()
        objects[3 + count + index] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"
        )
    return _pack(objects)


def _page_stream(lines: list[str]) -> bytes:
    parts = [b"BT", b"/F1 11 Tf", b"40 800 Td", b"14 TL"]
    for line in lines:
        parts.append(b"(" + _pdf_text(line) + b") '")
    parts.append(b"ET")
    return b"\n".join(parts)


def _pack(objects: list[bytes]) -> bytes:
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output += f"{index} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(output)
    output += f"xref\n0 {len(objects) + 1}\n".encode()
    output += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        output += f"{offset:010d} 00000 n \n".encode()
    output += (
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    )
    return bytes(output)
