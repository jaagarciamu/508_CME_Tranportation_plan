"""Execute Homework 1 and export a styled HTML report and US Letter PDF."""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, fields
from pathlib import Path
from textwrap import dedent

import nbformat
from nbconvert import HTMLExporter
from nbconvert.preprocessors import ExecutePreprocessor, TagRemovePreprocessor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = PROJECT_ROOT / "notebooks" / "homework_1.ipynb"
TEMPLATE_ROOT = PROJECT_ROOT / "templates"
REPORTS_DIR = PROJECT_ROOT / "reports"
HTML_PATH = REPORTS_DIR / "homework_1.html"
PDF_PATH = REPORTS_DIR / "homework_1.pdf"

EXPECTED_SHAPE_TEXT = "Rows: 2,310\nColumns: 16"
EXPECTED_VALIDATION_TEXT = (
    "Validation passed: the dataset is non-empty and contains all 16 expected columns."
)


@dataclass(frozen=True)
class ReportStyle:
    """Editable report design settings used by HTML, PDF, and Matplotlib."""

    # Page geometry in centimeters (US Letter is 21.59 x 27.94 cm).
    margin_top_cm: float = 1.0
    margin_right_cm: float = 1.0
    margin_bottom_cm: float = 1.0
    margin_left_cm: float = 1.0

    # Font stacks for the exported HTML and PDF.
    body_font_family: str = '"Aptos", "Segoe UI", Arial, sans-serif'
    heading_font_family: str = '"Aptos Display", "Segoe UI", Arial, sans-serif'
    code_font_family: str = '"Cascadia Mono", Consolas, monospace'

    # Typography in points.
    body_font_pt: float = 8
    h1_font_pt: float = 16
    h2_font_pt: float = 13
    h3_font_pt: float = 11
    h4_font_pt: float = 10
    table_font_pt: float = 6
    wide_table_font_pt: float = 6
    code_font_pt: float = 5
    code_line_height: float = 1.25
    math_font_pt: float = 5
    line_height: float = 1.42

    # Paragraph and caption alignment.
    justify_body_text: bool = True
    caption_text_align: str = "center"

    # Table geometry in points.
    table_border_pt: float = 0.5
    table_cell_vertical_padding_pt: float = 3.0
    table_cell_horizontal_padding_pt: float = 5.0

    # Figure limits in centimeters and Matplotlib defaults.
    figure_max_width_cm: float = 17.0
    figure_max_height_cm: float = 19.0
    plot_width_in: float = 6.6
    plot_height_in: float = 4.0
    plot_dpi: int = 144
    plot_font_family: str = "DejaVu Sans"
    plot_font_pt: float = 9.5
    plot_title_pt: float = 11.5
    plot_label_pt: float = 9.5
    plot_tick_pt: float = 8.5
    plot_legend_pt: float = 8.5


# Edit these values to control the appearance of every subsequent export.
REPORT_STYLE = ReportStyle()

# Put one of these comments on the first non-empty line of a code cell:
#   # report: hide-code    -> hide code, keep its result
#   # report: hide-output  -> keep code, hide its result
#   # report: hide-cell    -> hide both code and result
#   # report: show         -> show both code and result
# With no marker, existing cell tags are preserved and normal cells remain visible.
REPORT_MARKERS = {
    "# report: hide-code": "hide-input",
    "# report: hide-output": "hide-output",
    "# report: hide-cell": "remove-cell",
    "# report: show": None,
}
REPORT_CONTROL_TAGS = {tag for tag in REPORT_MARKERS.values() if tag is not None}


def validate_report_style(style: ReportStyle) -> None:
    """Reject invalid geometry and typography before executing the notebook."""
    positive_fields = [
        field.name
        for field in fields(style)
        if field.name.endswith(("_cm", "_pt", "_in"))
        or field.name in {"line_height", "code_line_height"}
    ]
    for name in positive_fields:
        if getattr(style, name) <= 0:
            raise ValueError(f"REPORT_STYLE.{name} must be greater than zero.")
    if style.plot_dpi <= 0:
        raise ValueError("REPORT_STYLE.plot_dpi must be greater than zero.")
    if style.margin_left_cm + style.margin_right_cm >= 21.59:
        raise ValueError("Horizontal margins leave no printable page width.")
    if style.margin_top_cm + style.margin_bottom_cm >= 27.94:
        raise ValueError("Vertical margins leave no printable page height.")
    if style.figure_max_width_cm > 21.59 - style.margin_left_cm - style.margin_right_cm:
        raise ValueError("figure_max_width_cm exceeds the printable page width.")
    if style.figure_max_height_cm > 27.94 - style.margin_top_cm - style.margin_bottom_cm:
        raise ValueError("figure_max_height_cm exceeds the printable page height.")
    if style.caption_text_align not in {"left", "center", "right", "justify"}:
        raise ValueError(
            "REPORT_STYLE.caption_text_align must be left, center, right, or justify."
        )


def report_style_css(style: ReportStyle) -> str:
    """Build CSS variables and print geometry from the editable style settings."""
    body_text_align = "justify" if style.justify_body_text else "left"
    body_hyphens = "auto" if style.justify_body_text else "manual"
    return dedent(
        f"""
        :root {{
          --report-margin-top: {style.margin_top_cm:g}cm;
          --report-margin-right: {style.margin_right_cm:g}cm;
          --report-margin-bottom: {style.margin_bottom_cm:g}cm;
          --report-margin-left: {style.margin_left_cm:g}cm;
          --report-body-font-family: {style.body_font_family};
          --report-heading-font-family: {style.heading_font_family};
          --report-code-font-family: {style.code_font_family};
          --report-body-font-size: {style.body_font_pt:g}pt;
          --report-h1-font-size: {style.h1_font_pt:g}pt;
          --report-h2-font-size: {style.h2_font_pt:g}pt;
          --report-h3-font-size: {style.h3_font_pt:g}pt;
          --report-h4-font-size: {style.h4_font_pt:g}pt;
          --report-table-font-size: {style.table_font_pt:g}pt;
          --report-wide-table-font-size: {style.wide_table_font_pt:g}pt;
          --report-code-font-size: {style.code_font_pt:g}pt;
          --report-code-line-height: {style.code_line_height:g};
          --report-math-font-size: {style.math_font_pt:g}pt;
          --report-line-height: {style.line_height:g};
          --report-body-text-align: {body_text_align};
          --report-body-hyphens: {body_hyphens};
          --report-caption-text-align: {style.caption_text_align};
          --report-table-border-width: {style.table_border_pt:g}pt;
          --report-table-padding-y: {style.table_cell_vertical_padding_pt:g}pt;
          --report-table-padding-x: {style.table_cell_horizontal_padding_pt:g}pt;
          --report-figure-max-width: {style.figure_max_width_cm:g}cm;
          --report-figure-max-height: {style.figure_max_height_cm:g}cm;
          --jp-code-font-size: {style.code_font_pt:g}pt;
          --jp-code-presentation-font-size: {style.code_font_pt:g}pt;
          --jp-code-line-height: {style.code_line_height:g};
        }}

        @page {{
          size: Letter portrait;
          margin: {style.margin_top_cm:g}cm {style.margin_right_cm:g}cm
                  {style.margin_bottom_cm:g}cm {style.margin_left_cm:g}cm;
        }}
        """
    ).strip()


def matplotlib_setup_cell(style: ReportStyle) -> nbformat.NotebookNode:
    """Create an export-only hidden cell with consistent plotting defaults."""
    rc_params = {
        "figure.figsize": (style.plot_width_in, style.plot_height_in),
        "figure.dpi": style.plot_dpi,
        "savefig.dpi": style.plot_dpi,
        "font.family": style.plot_font_family,
        "font.size": style.plot_font_pt,
        "axes.titlesize": style.plot_title_pt,
        "axes.labelsize": style.plot_label_pt,
        "xtick.labelsize": style.plot_tick_pt,
        "ytick.labelsize": style.plot_tick_pt,
        "legend.fontsize": style.plot_legend_pt,
        "figure.titlesize": style.plot_title_pt,
    }
    source = "import matplotlib as mpl\n\nmpl.rcParams.update(" + repr(rc_params) + ")"
    return nbformat.v4.new_code_cell(source=source, metadata={"tags": ["hide-input"]})


def apply_report_markers(notebook: nbformat.NotebookNode) -> None:
    """Convert simple code comments to nbconvert tags in the in-memory notebook."""
    for cell in notebook.cells:
        if cell.cell_type != "code":
            continue

        lines = cell.source.splitlines(keepends=True)
        marker_index = next(
            (index for index, line in enumerate(lines) if line.strip()),
            None,
        )
        if marker_index is None:
            continue

        marker = lines[marker_index].strip().lower()
        if marker not in REPORT_MARKERS:
            continue

        tags = set(cell.metadata.get("tags", []))
        tags.difference_update(REPORT_CONTROL_TAGS)
        export_tag = REPORT_MARKERS[marker]
        if export_tag is not None:
            tags.add(export_tag)

        if tags:
            cell.metadata["tags"] = sorted(tags)
        else:
            cell.metadata.pop("tags", None)

        del lines[marker_index]
        cell.source = "".join(lines)


def execute_notebook(style: ReportStyle) -> nbformat.NotebookNode:
    """Execute the source notebook in memory and return the fresh result."""
    with NOTEBOOK_PATH.open(encoding="utf-8") as stream:
        notebook = nbformat.read(stream, as_version=4)

    apply_report_markers(notebook)
    notebook.cells.insert(0, matplotlib_setup_cell(style))
    executor = ExecutePreprocessor(timeout=180, kernel_name="python3")
    executor.preprocess(notebook, {"metadata": {"path": str(PROJECT_ROOT)}})
    return notebook


def notebook_output_text(notebook: nbformat.NotebookNode) -> str:
    """Collect plain-text outputs for deterministic validation checks."""
    output_parts: list[str] = []
    for cell in notebook.cells:
        for output in cell.get("outputs", []):
            if output.output_type == "stream":
                output_parts.append(output.get("text", ""))
            elif output.output_type in {"execute_result", "display_data"}:
                output_parts.append(output.get("data", {}).get("text/plain", ""))
    return "\n".join(output_parts)


def validate_execution(notebook: nbformat.NotebookNode) -> None:
    """Confirm that the expected dataset was loaded and validated."""
    output_text = notebook_output_text(notebook)
    for expected_text in (EXPECTED_SHAPE_TEXT, EXPECTED_VALIDATION_TEXT):
        if expected_text not in output_text:
            raise RuntimeError(f"Expected notebook output was not found: {expected_text!r}")


def render_html(notebook: nbformat.NotebookNode, style: ReportStyle) -> None:
    """Render the executed notebook with the report template and cell tags."""
    exporter = HTMLExporter(
        template_name="report",
        extra_template_basedirs=[str(TEMPLATE_ROOT)],
        embed_images=True,
    )
    tag_filter = TagRemovePreprocessor(
        enabled=True,
        remove_input_tags={"hide-input"},
        remove_all_outputs_tags={"hide-output"},
        remove_cell_tags={"remove-cell"},
    )
    exporter.register_preprocessor(tag_filter, enabled=True)

    body, _ = exporter.from_notebook_node(
        notebook,
        resources={
            "metadata": {"name": "Homework 1 Trip Generation"},
            "report_style_css": report_style_css(style),
        },
    )
    HTML_PATH.write_text(body, encoding="utf-8")


def find_browsers() -> list[Path]:
    """Find available Chrome and Edge executables in preferred order."""
    candidates = [
        shutil.which("chrome"),
        shutil.which("chrome.exe"),
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        shutil.which("msedge"),
        shutil.which("msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    ]
    browsers: list[Path] = []
    for candidate in candidates:
        browser = Path(candidate) if candidate else None
        if browser and browser.is_file() and browser not in browsers:
            browsers.append(browser)
    if not browsers:
        raise FileNotFoundError("Chrome or Edge is required to create the PDF.")
    return browsers


def render_pdf(browsers: list[Path]) -> Path:
    """Print the HTML to PDF, falling back to the next available browser."""
    failures: list[str] = []
    for index, browser in enumerate(browsers):
        if PDF_PATH.exists():
            for attempt in range(40):
                try:
                    PDF_PATH.unlink()
                    break
                except PermissionError:
                    if attempt == 39:
                        raise RuntimeError(
                            f"Close any program using {PDF_PATH.name} and run the export again."
                        )
                    time.sleep(0.25)

        profile_dir = PROJECT_ROOT / "tmp" / f"report-browser-profile-{index}-{time.time_ns()}"
        profile_dir.mkdir(parents=True, exist_ok=True)
        command = [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={profile_dir}",
            "--allow-file-access-from-files",
            "--no-pdf-header-footer",
            "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=2000",
            f"--print-to-pdf={PDF_PATH}",
            HTML_PATH.resolve().as_uri(),
        ]
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        if completed.returncode == 0:
            for _ in range(50):
                if PDF_PATH.is_file() and PDF_PATH.stat().st_size > 0:
                    return browser
                time.sleep(0.1)

        details = completed.stderr.strip() or completed.stdout.strip()
        failures.append(f"{browser.name}: {details or 'no PDF was created'}")

    raise RuntimeError("Browser PDF export failed. " + " | ".join(failures))


def main() -> int:
    """Build both report formats or return a nonzero exit code."""
    try:
        validate_report_style(REPORT_STYLE)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        notebook = execute_notebook(REPORT_STYLE)
        validate_execution(notebook)
        render_html(notebook, REPORT_STYLE)
        browsers = find_browsers()
        browser = render_pdf(browsers)
    except Exception as exc:
        print(f"Export failed: {exc}", file=sys.stderr)
        return 1

    print(f"HTML report: {HTML_PATH.relative_to(PROJECT_ROOT)}")
    print(f"PDF report:  {PDF_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Browser:     {browser}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
