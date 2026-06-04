from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer


def main() -> None:
    output_dir = Path("uploads")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "sample_compliance_demo.pdf"

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(output_path), pagesize=A4)
    story = []

    story.append(Paragraph("Page 1: Customer Contact Details", styles["Title"]))
    story.append(Spacer(1, 16))
    story.append(Paragraph("Customer email: john@gmail.com", styles["BodyText"]))
    story.append(Paragraph("Customer phone: +91-9876543210", styles["BodyText"]))
    story.append(PageBreak())

    story.append(Paragraph("Page 2: Internal Project Strategy", styles["Title"]))
    story.append(Spacer(1, 16))
    story.append(
        Paragraph(
            "This document describes our confidential internal project strategy, proprietary roadmap, "
            "and trade secret pricing approach for the next product launch.",
            styles["BodyText"],
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("Page 3: Abusive Language Sample", styles["Title"]))
    story.append(Spacer(1, 16))
    story.append(
        Paragraph(
            "This page contains a harassment example for compliance testing: you are worthless and "
            "should be threatened until you stop speaking.",
            styles["BodyText"],
        )
    )

    doc.build(story)
    print(output_path)


if __name__ == "__main__":
    main()
