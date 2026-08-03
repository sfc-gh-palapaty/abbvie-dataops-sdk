#!/usr/bin/env python3
"""Add Lane 6 (Business Documents → OSI Ontology) to DataOps SDK flow.excalidraw."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

DIAGRAM = Path(__file__).resolve().parents[1].parent / "DataOps SDK flow.excalidraw"


def _id() -> str:
    return uuid.uuid4().hex[:16]


def _seed() -> int:
    return int(time.time() * 1000) % 2_000_000_000


def rect(x, y, w, h, *, stroke="#1971c2", bg="#a5d8ff", group=None, bound=None):
    return {
        "id": _id(),
        "type": "rectangle",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "angle": 0,
        "strokeColor": stroke,
        "backgroundColor": bg,
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [group] if group else [],
        "frameId": None,
        "roundness": {"type": 3},
        "seed": _seed(),
        "version": 1,
        "versionNonce": _seed(),
        "isDeleted": False,
        "boundElements": bound or [],
        "updated": int(time.time() * 1000),
        "link": None,
        "locked": False,
    }


def text_el(x, y, content, *, size=16, color="#0b2a45", group=None, width=200):
    return {
        "id": _id(),
        "type": "text",
        "x": x,
        "y": y,
        "width": width,
        "height": size * 1.25 * content.count("\n") + size * 1.25,
        "angle": 0,
        "strokeColor": color,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [group] if group else [],
        "frameId": None,
        "roundness": None,
        "seed": _seed(),
        "version": 1,
        "versionNonce": _seed(),
        "isDeleted": False,
        "boundElements": [],
        "updated": int(time.time() * 1000),
        "link": None,
        "locked": False,
        "text": content,
        "fontSize": size,
        "fontFamily": 5,
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": None,
        "originalText": content,
        "autoResize": True,
        "lineHeight": 1.25,
    }


def arrow(x1, y1, x2, y2, *, label=None, start_bind=None, end_bind=None):
    aid = _id()
    elements = [
        {
            "id": aid,
            "type": "arrow",
            "x": x1,
            "y": y1,
            "width": x2 - x1,
            "height": y2 - y1,
            "angle": 0,
            "strokeColor": "#2f9e44",
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 2,
            "strokeStyle": "solid",
            "roughness": 1,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "roundness": {"type": 2},
            "seed": _seed(),
            "version": 1,
            "versionNonce": _seed(),
            "isDeleted": False,
            "boundElements": [],
            "updated": int(time.time() * 1000),
            "link": None,
            "locked": False,
            "startBinding": start_bind,
            "endBinding": end_bind,
            "lastCommittedPoint": None,
            "startArrowhead": None,
            "endArrowhead": "arrow",
            "points": [[0, 0], [x2 - x1, y2 - y1]],
        }
    ]
    if label:
        elements.append(
            text_el(
                x1 + (x2 - x1) / 2 - 40,
                y1 + (y2 - y1) / 2 - 20,
                label,
                size=12,
                color="#2f9e44",
                width=100,
            )
        )
    return elements, aid


def dashed_lane(x, y, w, h):
    return {
        "id": _id(),
        "type": "rectangle",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "angle": 0,
        "strokeColor": "#868e96",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "dashed",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": {"type": 3},
        "seed": _seed(),
        "version": 1,
        "versionNonce": _seed(),
        "isDeleted": False,
        "boundElements": [],
        "updated": int(time.time() * 1000),
        "link": None,
        "locked": False,
    }


def main() -> None:
    data = json.loads(DIAGRAM.read_text(encoding="utf-8"))
    group = _id()
    new_elements = []

    # Lane label
    new_elements.append(
        text_el(28, 648, "Lane 6: Business Documents → OSI Ontology", size=18, color="#1971c2", width=420)
    )

    # Dashed swimlane
    new_elements.append(dashed_lane(220, 678, 920, 130))

    # Boxes left → right
    sharepoint = rect(240, 700, 140, 86, stroke="#e67700", bg="#ffe8cc", group=group)
    pipeline = rect(420, 700, 160, 86, stroke="#1971c2", bg="#d0ebff", group=group)
    git_out = rect(620, 700, 150, 86, stroke="#2f9e44", bg="#d3f9d8", group=group)
    materialize = rect(800, 700, 200, 86, stroke="#7048e8", bg="#e5dbff", group=group)

    new_elements.extend([sharepoint, pipeline, git_out, materialize])

    new_elements.append(text_el(252, 718, "SharePoint\n(S3 demo)", size=14, width=116))
    new_elements.append(text_el(432, 712, "Ontology Pipeline\n(parse + OSI build)", size=13, width=136))
    new_elements.append(text_el(632, 712, "OSI YAML\ngit/outputs/", size=14, width=126))
    new_elements.append(text_el(812, 708, "Materialization\nSnowflake Semantic View\nAWS / OSI platforms", size=12, width=176))

    # Sub-labels under boxes
    new_elements.append(text_el(248, 792, "pharma_erd.md\nbusiness_rules.md\nsource_to_target.csv", size=11, color="#495057", width=124))
    new_elements.append(text_el(428, 792, "abbvie-dataops\nontology adapter", size=11, color="#495057", width=144))
    new_elements.append(text_el(628, 792, "versioned in git\nmanifest.json", size=11, color="#495057", width=134))
    new_elements.append(text_el(818, 792, "SYSTEM$CREATE_\nSEMANTIC_VIEW_\nFROM_OSSIE_YAML", size=10, color="#495057", width=164))

    # Arrows between boxes
    bind = lambda eid: {"elementId": eid, "focus": 0.5, "gap": 4}
    for (x1, y1, x2, y2, sb, eb) in [
        (380, 743, 420, 743, sharepoint["id"], pipeline["id"]),
        (580, 743, 620, 743, pipeline["id"], git_out["id"]),
        (770, 743, 800, 743, git_out["id"], materialize["id"]),
    ]:
        els, _ = arrow(x1, y1, x2, y2, start_bind=bind(sb), end_bind=bind(eb))
        new_elements.extend(els)

    # CI/CD → ontology pipeline
    els, ci_arrow = arrow(208, 470, 500, 700, label="ontology\nmanifest")
    new_elements.extend(els)

    # Ontology → OpenLineage (up-right)
    els, _ = arrow(580, 700, 980, 436, label="lineage events")
    new_elements.extend(els)

    # Update flow description text if present
    for el in data["elements"]:
        if el.get("type") == "text" and el.get("text", "").startswith("Flow:"):
            el["text"] = (
                "Flow:\n"
                "       → CI/CD invokes SDK in every pipeline\n"
                "       → Apps execute SDK based on individual manifests\n"
                "       → Pipelines emit lineage to OpenLineage\n"
                "       → OpenLineage forwards to Alation\n"
                "       → Lane 6: SharePoint/S3 docs → OSI YAML → Semantic Views"
            )
            el["originalText"] = el["text"]
            el["height"] = 220

        # Wire CI/CD box to new arrow
        if el.get("id") == "mobwv896nek32qcppsn":
            el.setdefault("boundElements", []).append({"id": ci_arrow, "type": "arrow"})

        # Wire OpenLineage box
        if el.get("id") == "mobwv8976t8yob86k5b":
            el.setdefault("boundElements", []).append({"id": ci_arrow, "type": "arrow"})

    data["elements"].extend(new_elements)
    DIAGRAM.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Added {len(new_elements)} elements to {DIAGRAM}")


if __name__ == "__main__":
    main()
