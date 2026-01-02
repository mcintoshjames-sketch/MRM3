"""PDF Report Generation for Performance Monitoring Cycles and Validation Scorecards.

This module provides PDF generation classes for:
1. MonitoringCycleReportPDF - Performance monitoring cycle reports
2. ValidationScorecardPDF - Validation scorecard one-page exports

Features:
- Cover page with branding
- Executive summary with outcome breakdown
- Detailed results table with color-coded outcomes
- Breach analysis with narrative comments
- Time-series trend charts for breached metrics
- Approvals section
"""

from app.core.monitoring_constants import (
    OUTCOME_GREEN, OUTCOME_YELLOW, OUTCOME_RED, OUTCOME_NA, OUTCOME_UNCONFIGURED
)
from matplotlib.patches import Rectangle
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import io
import os
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from fpdf import FPDF

# Import matplotlib with Agg backend for server-side rendering
import matplotlib
matplotlib.use('Agg')


# Color constants (RGB tuples)
# Background colors for table cells
BG_GREEN = (220, 252, 231)      # Green-100
BG_YELLOW = (254, 249, 195)     # Yellow-100
BG_RED = (254, 226, 226)        # Red-100
BG_GRAY = (243, 244, 246)       # Gray-100 for N/A

# Text/marker colors for charts
COLOR_GREEN = (34, 197, 94)     # Green-500
COLOR_YELLOW = (234, 179, 8)    # Yellow-500
COLOR_RED = (239, 68, 68)       # Red-500
COLOR_GRAY = (156, 163, 175)    # Gray-400

# Header colors
HEADER_BG = (31, 41, 55)        # Gray-800
HEADER_TEXT = (255, 255, 255)   # White

# Section header colors
SECTION_BG = (243, 244, 246)    # Gray-100
SECTION_TEXT = (31, 41, 55)     # Gray-800

# Scorecard Rating Colors (background colors for cells)
SCORECARD_COLORS = {
    'Green': (165, 214, 167),    # #a5d6a7
    'Green-': (165, 214, 167),   # #a5d6a7
    'Yellow+': (255, 241, 118),  # #fff176
    'Yellow': (255, 241, 118),   # #fff176
    'Yellow-': (255, 235, 59),   # #ffeb3b
    'Red': (239, 154, 154),      # #ef9a9a
    'N/A': (245, 245, 245),      # Light gray
}


def scorecard_rating_to_color(rating: Optional[str]) -> Tuple[int, int, int]:
    """Get background color tuple for a scorecard rating."""
    if rating is None:
        return SCORECARD_COLORS['N/A']
    return SCORECARD_COLORS.get(rating, SCORECARD_COLORS['N/A'])


def outcome_to_bg_color(outcome: Optional[str]) -> Tuple[int, int, int]:
    """Get background color tuple for an outcome."""
    if outcome == OUTCOME_GREEN:
        return BG_GREEN
    elif outcome == OUTCOME_YELLOW:
        return BG_YELLOW
    elif outcome == OUTCOME_RED:
        return BG_RED
    else:
        return BG_GRAY


def outcome_to_chart_color(outcome: Optional[str]) -> str:
    """Get hex color for charts based on outcome."""
    if outcome == OUTCOME_GREEN:
        return '#22C55E'
    elif outcome == OUTCOME_YELLOW:
        return '#EAB308'
    elif outcome == OUTCOME_RED:
        return '#EF4444'
    else:
        return '#9CA3AF'


def format_threshold_range(min_val: Optional[float], max_val: Optional[float]) -> str:
    """Format a threshold range for display."""
    if min_val is not None and max_val is not None:
        return f"{min_val:.2f} - {max_val:.2f}"
    elif min_val is not None:
        return f">= {min_val:.2f}"
    elif max_val is not None:
        return f"<= {max_val:.2f}"
    else:
        return "N/A"


def generate_trend_chart(
    metric_name: str,
    data_points: List[Dict[str, Any]],
    yellow_min: Optional[float] = None,
    yellow_max: Optional[float] = None,
    red_min: Optional[float] = None,
    red_max: Optional[float] = None,
    width: float = 7,
    height: float = 3
) -> bytes:
    """Generate a PNG chart showing metric trend over time.

    Args:
        metric_name: Name of the metric for chart title
        data_points: List of dicts with keys: period_end_date, numeric_value, calculated_outcome.
            Optionally includes per-point thresholds: yellow_min/yellow_max/red_min/red_max.
        yellow_min/max: Yellow threshold boundaries (used when per-point values not provided)
        red_min/max: Red threshold boundaries (used when per-point values not provided)
        width/height: Figure size in inches

    Returns:
        PNG image bytes
    """
    if not data_points:
        return b''

    # Extract data
    dates = []
    values = []
    colors = []
    yellow_min_series = []
    yellow_max_series = []
    red_min_series = []
    red_max_series = []

    for dp in data_points:
        if dp.get('numeric_value') is not None:
            date = dp.get('period_end_date')
            if isinstance(date, str):
                date = datetime.fromisoformat(
                    date.replace('Z', '+00:00')).date()
            dates.append(date)
            values.append(dp['numeric_value'])
            colors.append(outcome_to_chart_color(dp.get('calculated_outcome')))
            yellow_min_series.append(dp.get('yellow_min'))
            yellow_max_series.append(dp.get('yellow_max'))
            red_min_series.append(dp.get('red_min'))
            red_max_series.append(dp.get('red_max'))

    if not dates:
        return b''

    # Create figure
    fig, ax = plt.subplots(figsize=(width, height), dpi=100)

    # Plot line and points
    ax.plot(dates, values, linestyle='-',
            color='#6B7280', linewidth=1.5, zorder=2)

    # Scatter points with outcome colors
    for i, (d, v, c) in enumerate(zip(dates, values, colors)):
        ax.scatter([d], [v], c=[c], s=60, zorder=3,
                   edgecolors='white', linewidths=1)

    def has_series_values(series: List[Optional[float]]) -> bool:
        return any(value is not None for value in series)

    has_dynamic_thresholds = any([
        has_series_values(yellow_min_series),
        has_series_values(yellow_max_series),
        has_series_values(red_min_series),
        has_series_values(red_max_series),
    ])

    # Calculate y-axis range for threshold bands/lines
    all_values = values.copy()
    if has_dynamic_thresholds:
        for series in (yellow_min_series, yellow_max_series, red_min_series, red_max_series):
            for value in series:
                if value is not None:
                    all_values.append(value)
    else:
        if yellow_min is not None:
            all_values.append(yellow_min)
        if yellow_max is not None:
            all_values.append(yellow_max)
        if red_min is not None:
            all_values.append(red_min)
        if red_max is not None:
            all_values.append(red_max)

    y_min = min(all_values) * 0.9 if all_values else 0
    y_max = max(all_values) * 1.1 if all_values else 1
    margin = (y_max - y_min) * 0.1
    y_min -= margin
    y_max += margin

    ax.set_ylim(y_min, y_max)

    def latest_threshold_value(series: List[Optional[float]]) -> Optional[float]:
        for value in reversed(series):
            if value is not None:
                return value
        return None

    def normalize_series(series: List[Optional[float]]) -> List[float]:
        return [float(value) if value is not None else float('nan') for value in series]

    def add_dynamic_line(series: List[Optional[float]], color: str, linestyle: str, label_prefix: str) -> None:
        if not has_series_values(series):
            return
        latest_value = latest_threshold_value(series)
        if latest_value is None:
            return
        label = f"{label_prefix} ({latest_value:.2f})"
        ax.plot(
            dates,
            normalize_series(series),
            color=color,
            linestyle=linestyle,
            linewidth=1.4,
            zorder=1,
            drawstyle='steps-post',
            label=label
        )

    # Draw threshold lines (dynamic per-period when available)
    if has_dynamic_thresholds:
        add_dynamic_line(yellow_max_series, '#EAB308', '--', 'Yellow Max')
        add_dynamic_line(yellow_min_series, '#EAB308', ':', 'Yellow Min')
        add_dynamic_line(red_max_series, '#EF4444', '--', 'Red Max')
        add_dynamic_line(red_min_series, '#EF4444', ':', 'Red Min')
    else:
        if yellow_max is not None:
            ax.axhline(y=yellow_max, color='#EAB308', linestyle='--', linewidth=1.5,
                       label=f'Yellow Max ({yellow_max:.2f})', zorder=1)
        if yellow_min is not None:
            ax.axhline(y=yellow_min, color='#EAB308', linestyle=':', linewidth=1.5,
                       label=f'Yellow Min ({yellow_min:.2f})', zorder=1)
        if red_max is not None:
            ax.axhline(y=red_max, color='#EF4444', linestyle='--', linewidth=1.5,
                       label=f'Red Max ({red_max:.2f})', zorder=1)
        if red_min is not None:
            ax.axhline(y=red_min, color='#EF4444', linestyle=':', linewidth=1.5,
                       label=f'Red Min ({red_min:.2f})', zorder=1)

    # Styling
    ax.set_xlabel('Period End Date', fontsize=9)
    ax.set_ylabel('Value', fontsize=9)
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)

    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45, ha='right', fontsize=8)
    plt.yticks(fontsize=8)

    # Add legend if we have threshold lines
    if has_dynamic_thresholds or any([yellow_min, yellow_max, red_min, red_max]):
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(
                loc='center left',
                bbox_to_anchor=(1.02, 0.5),
                fontsize=7,
                framealpha=0.9,
                ncol=1,
                borderaxespad=0.0,
                handlelength=1.6
            )

    # Tight layout with room on the right for the legend
    fig.tight_layout(rect=[0.0, 0.02, 0.78, 0.98])

    # Export to bytes
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', facecolor='white', edgecolor='none')
    plt.close(fig)
    buffer.seek(0)
    return buffer.getvalue()


class MonitoringCycleReportPDF(FPDF):
    """Professional PDF report generator for completed monitoring cycles."""

    def __init__(
        self,
        cycle_data: Dict[str, Any],
        plan_data: Dict[str, Any],
        results: List[Dict[str, Any]],
        approvals: List[Dict[str, Any]],
        trend_data: Optional[Dict[int, List[Dict[str, Any]]]] = None,
        logo_path: Optional[str] = None
    ):
        """Initialize the PDF report.

        Args:
            cycle_data: Cycle information dict
            plan_data: Plan information dict
            results: List of result dicts with metric info
            approvals: List of approval dicts
            trend_data: Optional dict mapping metric_id to list of historical data points
            logo_path: Optional path to logo file
        """
        super().__init__(orientation='P', unit='mm', format='A4')
        self.cycle_data = cycle_data
        self.plan_data = plan_data
        self.results = results
        self.approvals = approvals
        self.trend_data = trend_data or {}
        self.logo_path = logo_path

        # Page settings
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(15, 15, 15)

        # Calculate summary stats
        self._calculate_summary()

    def _calculate_summary(self):
        """Calculate summary statistics from results."""
        self.summary = {
            'total': len(self.results),
            'green': 0,
            'yellow': 0,
            'red': 0,
            'na': 0
        }

        for result in self.results:
            outcome = result.get('calculated_outcome')
            if outcome == OUTCOME_GREEN:
                self.summary['green'] += 1
            elif outcome == OUTCOME_YELLOW:
                self.summary['yellow'] += 1
            elif outcome == OUTCOME_RED:
                self.summary['red'] += 1
            else:
                self.summary['na'] += 1

        self.summary['breaches'] = self.summary['yellow'] + self.summary['red']

    def header(self):
        """Add page header with logo."""
        # Logo
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                self.image(self.logo_path, x=15, y=8, h=12)
            except Exception:
                pass  # Skip if logo fails to load

        # Report title on right side
        self.set_font('helvetica', 'B', 10)
        self.set_text_color(*SECTION_TEXT)
        self.set_xy(150, 12)
        self.cell(45, 5, 'Performance Monitoring Report', align='R')

        self.ln(15)

    def footer(self):
        """Add page footer with page numbers and timestamp."""
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)

        # Page number
        self.cell(0, 5, f'Page {self.page_no()}/{{nb}}', align='C')

        # Cycle reference
        self.set_y(-10)
        cycle_id = self.cycle_data.get('cycle_id', '')
        self.cell(0, 5, f'Cycle ID: {cycle_id}', align='C')

    def add_cover_page(self):
        """Add the cover page with report overview."""
        self.add_page()

        # Main title
        self.set_font('helvetica', 'B', 24)
        self.set_text_color(*SECTION_TEXT)
        self.ln(30)
        self.cell(0, 15, 'Performance Monitoring Report', align='C')
        self.ln(20)

        # Plan name
        plan_name = self.plan_data.get('name', 'Monitoring Plan')
        self.set_font('helvetica', 'B', 16)
        self.cell(0, 10, plan_name, align='C')
        self.ln(15)

        # Period
        period_start = self.cycle_data.get('period_start_date', '')
        period_end = self.cycle_data.get('period_end_date', '')
        if isinstance(period_start, datetime):
            period_start = period_start.strftime('%Y-%m-%d')
        if isinstance(period_end, datetime):
            period_end = period_end.strftime('%Y-%m-%d')

        self.set_font('helvetica', '', 12)
        self.cell(
            0, 8, f'Monitoring Period: {period_start} to {period_end}', align='C')
        self.ln(10)

        # Completion info
        completed_at = self.cycle_data.get('completed_at', '')
        if isinstance(completed_at, datetime):
            completed_at = completed_at.strftime('%Y-%m-%d %H:%M')

        completed_by = self.cycle_data.get('completed_by', {})
        if isinstance(completed_by, dict):
            completed_by_name = completed_by.get(
                'full_name', completed_by.get('email', 'Unknown'))
        else:
            completed_by_name = str(
                completed_by) if completed_by else 'Unknown'

        self.cell(0, 8, f'Completed: {completed_at}', align='C')
        self.ln(8)
        self.cell(0, 8, f'Approved by: {completed_by_name}', align='C')
        self.ln(15)

        # Status badge
        status = self.cycle_data.get('status', 'APPROVED')
        self.set_fill_color(*BG_GREEN)
        self.set_font('helvetica', 'B', 14)
        badge_width = 40
        x = (210 - badge_width) / 2
        self.set_x(x)
        self.cell(badge_width, 10, status, border=1, align='C', fill=True)
        self.ln(25)

        # Quick summary box
        self._draw_summary_box()

    def _draw_summary_box(self):
        """Draw the executive summary box on cover page."""
        # Box dimensions
        box_x = 40
        box_y = self.get_y()
        box_w = 130
        box_h = 50

        # Draw box border
        self.set_draw_color(200, 200, 200)
        self.rect(box_x, box_y, box_w, box_h)

        # Title
        self.set_xy(box_x + 5, box_y + 5)
        self.set_font('helvetica', 'B', 11)
        self.set_text_color(*SECTION_TEXT)
        self.cell(box_w - 10, 6, 'Results Summary', align='C')

        # Metrics counts
        self.set_font('helvetica', '', 10)
        y_start = box_y + 15
        col_width = (box_w - 10) / 4

        # Row 1: Labels
        labels = ['GREEN', 'YELLOW', 'RED', 'N/A']
        counts = [self.summary['green'], self.summary['yellow'],
                  self.summary['red'], self.summary['na']]
        colors = [BG_GREEN, BG_YELLOW, BG_RED, BG_GRAY]

        for i, (label, count, color) in enumerate(zip(labels, counts, colors)):
            x = box_x + 5 + (i * col_width)

            # Color indicator
            self.set_fill_color(*color)
            self.set_xy(x + 5, y_start)
            self.cell(col_width - 10, 10, '', border=1, fill=True)

            # Count
            self.set_xy(x + 5, y_start)
            self.set_font('helvetica', 'B', 14)
            self.set_text_color(*SECTION_TEXT)
            self.cell(col_width - 10, 10, str(count), align='C')

            # Label
            self.set_xy(x + 5, y_start + 12)
            self.set_font('helvetica', '', 8)
            self.cell(col_width - 10, 5, label, align='C')

        # Total and breaches
        self.set_xy(box_x + 5, y_start + 25)
        self.set_font('helvetica', '', 10)
        self.cell(box_w - 10, 6,
                  f"Total Metrics: {self.summary['total']}  |  Threshold Breaches: {self.summary['breaches']}",
                  align='C')

        self.set_y(box_y + box_h + 10)

    def add_executive_summary(self):
        """Add executive summary section."""
        self.add_page()

        # Section header
        self._add_section_header('Executive Summary')
        self.ln(5)

        # Summary statistics
        self.set_font('helvetica', '', 10)
        self.set_text_color(*SECTION_TEXT)

        # Outcome breakdown table
        self.set_font('helvetica', 'B', 10)
        self.cell(0, 8, 'Outcome Distribution:', ln=True)
        self.ln(2)

        # Table header
        col_widths = [50, 30, 30]
        headers = ['Outcome', 'Count', 'Percentage']

        self.set_fill_color(*HEADER_BG)
        self.set_text_color(*HEADER_TEXT)
        self.set_font('helvetica', 'B', 9)

        for i, (header, width) in enumerate(zip(headers, col_widths)):
            self.cell(width, 8, header, border=1, align='C', fill=True)
        self.ln()

        # Table rows
        outcomes = [
            ('GREEN - Acceptable', self.summary['green'], BG_GREEN),
            ('YELLOW - Warning', self.summary['yellow'], BG_YELLOW),
            ('RED - Critical', self.summary['red'], BG_RED),
            ('N/A - Not Applicable', self.summary['na'], BG_GRAY),
        ]

        total = self.summary['total'] if self.summary['total'] > 0 else 1

        self.set_font('helvetica', '', 9)
        self.set_text_color(*SECTION_TEXT)

        for label, count, color in outcomes:
            self.set_fill_color(*color)
            pct = (count / total) * 100

            self.cell(col_widths[0], 7, label, border=1, fill=True)
            self.cell(col_widths[1], 7, str(count),
                      border=1, align='C', fill=True)
            self.cell(col_widths[2], 7, f'{pct:.1f}%',
                      border=1, align='C', fill=True)
            self.ln()

        # Total row
        self.set_font('helvetica', 'B', 9)
        self.set_fill_color(*SECTION_BG)
        self.cell(col_widths[0], 7, 'TOTAL', border=1, fill=True)
        self.cell(col_widths[1], 7, str(
            self.summary['total']), border=1, align='C', fill=True)
        self.cell(col_widths[2], 7, '100%', border=1, align='C', fill=True)
        self.ln(10)

        # Models in scope
        models = self.plan_data.get('models', [])
        if models:
            self.set_font('helvetica', 'B', 10)
            self.cell(0, 8, f'Models in Scope ({len(models)}):', ln=True)
            self.set_font('helvetica', '', 9)
            for model in models[:10]:  # Limit to first 10
                model_name = model.get('model_name', 'Unknown') if isinstance(
                    model, dict) else str(model)
                self.cell(0, 6, f'  - {model_name}', ln=True)
            if len(models) > 10:
                self.cell(0, 6, f'  ... and {len(models) - 10} more', ln=True)

        self.ln(5)

        # Key findings
        if self.summary['breaches'] > 0:
            self.set_font('helvetica', 'B', 10)
            self.set_text_color(*COLOR_RED)
            self.cell(
                0, 8, f'Attention Required: {self.summary["breaches"]} metric(s) breached thresholds', ln=True)
            self.set_text_color(*SECTION_TEXT)

    def add_results_table(self):
        """Add detailed results table section."""
        self.add_page()

        # Section header
        self._add_section_header('Detailed Results')
        self.ln(5)

        if not self.results:
            self.set_font('helvetica', 'I', 10)
            self.cell(0, 10, 'No results recorded for this cycle.', ln=True)
            return

        # Check if we have multiple models (need Model column)
        unique_models = set(r.get('model_name')
                            for r in self.results if r.get('model_name'))
        has_multiple_models = len(unique_models) > 1

        # Table setup - add Model column if multi-model plan
        if has_multiple_models:
            col_widths = [28, 35, 35, 22, 25, 25, 15]
            headers = ['Category', 'Metric', 'Model',
                       'Value', 'Yellow', 'Red', 'Result']
        else:
            col_widths = [35, 50, 25, 30, 30, 18]
            headers = ['Category', 'Metric', 'Value',
                       'Yellow Range', 'Red Range', 'Result']

        # Table header
        self.set_fill_color(*HEADER_BG)
        self.set_text_color(*HEADER_TEXT)
        self.set_font('helvetica', 'B', 7)

        for header, width in zip(headers, col_widths):
            self.cell(width, 8, header, border=1, align='C', fill=True)
        self.ln()

        # Table rows
        self.set_font('helvetica', '', 7)
        self.set_text_color(*SECTION_TEXT)

        # Sort by category, metric name, then model name
        sorted_results = sorted(
            self.results,
            key=lambda r: (
                r.get('category_name', r.get('kpm_category', 'ZZZ')),
                r.get('metric_name', r.get('kpm_name', 'ZZZ')),
                r.get('model_name', '') or ''
            )
        )

        for result in sorted_results:
            # Check if we need a new page
            if self.get_y() > 260:
                self.add_page()
                # Repeat header
                self.set_fill_color(*HEADER_BG)
                self.set_text_color(*HEADER_TEXT)
                self.set_font('helvetica', 'B', 7)
                for header, width in zip(headers, col_widths):
                    self.cell(width, 8, header, border=1, align='C', fill=True)
                self.ln()
                self.set_font('helvetica', '', 7)
                self.set_text_color(*SECTION_TEXT)

            # Get data
            category = result.get(
                'category_name', result.get('kpm_category', 'N/A'))[:18]
            metric = result.get(
                'metric_name', result.get('kpm_name', 'Unknown'))
            model_name = result.get('model_name', '-') or '-'

            value = result.get('numeric_value')
            if value is not None:
                value_str = f'{value:.3f}' if isinstance(
                    value, float) else str(value)
            else:
                outcome_value = result.get('outcome_value', {})
                if isinstance(outcome_value, dict):
                    value_str = outcome_value.get(
                        'label', outcome_value.get('code', '-'))
                else:
                    value_str = '-'

            yellow_range = format_threshold_range(
                result.get('yellow_min'),
                result.get('yellow_max')
            )
            red_range = format_threshold_range(
                result.get('red_min'),
                result.get('red_max')
            )

            outcome = result.get('calculated_outcome', 'N/A')

            # Set row color based on outcome
            bg_color = outcome_to_bg_color(outcome)
            self.set_fill_color(*bg_color)

            # Draw cells
            if has_multiple_models:
                self.cell(col_widths[0], 7, category, border=1, fill=True)
                self.cell(col_widths[1], 7, metric[:22], border=1, fill=True)
                self.cell(col_widths[2], 7,
                          model_name[:22], border=1, fill=True)
                self.cell(col_widths[3], 7, value_str[:10],
                          border=1, align='R', fill=True)
                self.cell(col_widths[4], 7, yellow_range[:12],
                          border=1, align='C', fill=True)
                self.cell(col_widths[5], 7, red_range[:12],
                          border=1, align='C', fill=True)
                self.cell(col_widths[6], 7, outcome[:8],
                          border=1, align='C', fill=True)
            else:
                self.cell(col_widths[0], 7, category, border=1, fill=True)
                self.cell(col_widths[1], 7, metric[:30], border=1, fill=True)
                self.cell(col_widths[2], 7, value_str[:12],
                          border=1, align='R', fill=True)
                self.cell(col_widths[3], 7, yellow_range,
                          border=1, align='C', fill=True)
                self.cell(col_widths[4], 7, red_range,
                          border=1, align='C', fill=True)
                self.cell(col_widths[5], 7, outcome[:8],
                          border=1, align='C', fill=True)
            self.ln()

    def add_breach_analysis(self):
        """Add breach analysis section for YELLOW/RED outcomes with inline trend charts."""
        # Filter to only breached results
        breaches = [
            r for r in self.results
            if r.get('calculated_outcome') in (OUTCOME_YELLOW, OUTCOME_RED)
        ]

        if not breaches:
            return  # Skip section if no breaches

        self.add_page()
        self._add_section_header('Breach Analysis')
        self.ln(5)

        self.set_font('helvetica', '', 9)
        self.set_text_color(*SECTION_TEXT)
        self.multi_cell(0, 5,
                        f'The following {len(breaches)} metric(s) exceeded threshold boundaries and require attention.')
        self.ln(5)

        version_number = self.cycle_data.get('plan_version_number')
        if version_number:
            effective_date = self.cycle_data.get('plan_version_effective_date')
            if isinstance(effective_date, datetime):
                effective_date = effective_date.date().isoformat()
            elif effective_date:
                effective_date = str(effective_date)
            else:
                effective_date = 'unknown date'
            self.set_font('helvetica', 'I', 8)
            self.set_text_color(100, 100, 100)
            self.cell(
                0,
                5,
                f'Thresholds reflect plan version v{version_number} (effective {effective_date}).',
                ln=True
            )
            self.set_text_color(*SECTION_TEXT)
            self.ln(2)

        for i, breach in enumerate(breaches, 1):
            # Check for page break - need ~120mm for breach + chart
            if self.get_y() > 160:
                self.add_page()

            # Breach header
            outcome = breach.get('calculated_outcome', 'YELLOW')
            bg_color = outcome_to_bg_color(outcome)

            metric_name = breach.get(
                'metric_name', breach.get('kpm_name', 'Unknown'))
            category = breach.get(
                'category_name', breach.get('kpm_category', ''))
            model_name = breach.get('model_name', '')

            # Include model name in header if present
            if model_name:
                header_text = f'{i}. {metric_name} ({category}) - {model_name} - {outcome}'
            else:
                header_text = f'{i}. {metric_name} ({category}) - {outcome}'

            self.set_fill_color(*bg_color)
            self.set_font('helvetica', 'B', 10)
            self.cell(0, 8, header_text[:80], border=1, fill=True, ln=True)

            self.set_font('helvetica', '', 9)

            # Value and threshold
            value = breach.get('numeric_value')
            if value is not None:
                value_str = f'{value:.4f}'
            else:
                outcome_value = breach.get('outcome_value', {})
                if isinstance(outcome_value, dict):
                    value_str = outcome_value.get('label', 'Qualitative')
                else:
                    value_str = 'Qualitative'

            self.cell(40, 6, 'Recorded Value:', border=0)
            self.cell(0, 6, value_str, border=0, ln=True)

            # Thresholds
            if outcome == OUTCOME_YELLOW:
                threshold_range = format_threshold_range(
                    breach.get('yellow_min'), breach.get('yellow_max')
                )
                self.cell(40, 6, 'Yellow Threshold:', border=0)
            else:
                threshold_range = format_threshold_range(
                    breach.get('red_min'), breach.get('red_max')
                )
                self.cell(40, 6, 'Red Threshold:', border=0)
            self.cell(0, 6, threshold_range, border=0, ln=True)

            # Narrative/Comments
            narrative = breach.get('narrative', '')
            if narrative:
                self.ln(2)
                self.set_font('helvetica', 'B', 9)
                self.cell(0, 6, 'Breach Justification / Comments:', ln=True)
                self.set_font('helvetica', '', 9)

                # Draw narrative in a box
                self.set_fill_color(250, 250, 250)
                self.set_draw_color(200, 200, 200)

                # Calculate text height
                self.set_x(15)
                start_y = self.get_y()
                self.multi_cell(180, 5, narrative, border=1, fill=True)
                self.ln(2)
            else:
                self.set_font('helvetica', 'I', 9)
                self.set_text_color(150, 150, 150)
                self.cell(0, 6, 'No justification provided.', ln=True)
                self.set_text_color(*SECTION_TEXT)

            # Add inline trend chart for this specific breach (if quantitative)
            self._add_inline_trend_chart(breach)

            self.ln(8)

    def _add_inline_trend_chart(self, breach: Dict[str, Any]):
        """Add trend chart inline after breach commentary (if quantitative with trend data)."""
        # Only add chart for quantitative metrics
        if breach.get('numeric_value') is None:
            return

        if not self.trend_data:
            return

        # Build composite key: metric_id + model_id (or just metric_id if no model)
        metric_id = breach.get('metric_id', breach.get('plan_metric_id'))
        model_id = breach.get('model_id')

        if metric_id is None:
            return

        # Try composite key first, then metric-only key
        trend_key = f"{metric_id}_{model_id}" if model_id else str(metric_id)
        trend_points = self.trend_data.get(trend_key)

        # Fallback to metric-only key for backwards compatibility
        if not trend_points:
            trend_points = self.trend_data.get(metric_id, [])

        if not trend_points or len(trend_points) < 2:
            return  # Need at least 2 points for a meaningful trend

        # Check for page break if needed (chart is ~70mm tall)
        if self.get_y() > 200:
            self.add_page()

        # Generate chart with model name in title if applicable
        metric_name = breach.get(
            'metric_name', breach.get('kpm_name', 'Unknown'))
        model_name = breach.get('model_name', '')
        if model_name:
            chart_title = f"Trend: {metric_name} - {model_name}"
        else:
            chart_title = f"Trend: {metric_name}"

        chart_bytes = generate_trend_chart(
            metric_name=chart_title,
            data_points=trend_points,
            yellow_min=breach.get('yellow_min'),
            yellow_max=breach.get('yellow_max'),
            red_min=breach.get('red_min'),
            red_max=breach.get('red_max'),
            width=6.2,  # Wider for readability with side legend
            height=2.0
        )

        if chart_bytes:
            try:
                self.ln(3)
                img_buffer = io.BytesIO(chart_bytes)
                self.image(img_buffer, x=16, w=178)
                self.ln(3)
            except Exception:
                pass  # Skip chart if it fails to render

    def add_trend_charts(self):
        """Legacy method - charts are now inline with breach analysis.

        Kept for backwards compatibility but does nothing since
        charts are now rendered in add_breach_analysis via _add_inline_trend_chart.
        """
        pass  # Charts now rendered inline with breach analysis

    def add_approvals_section(self):
        """Add approvals section."""
        if not self.approvals:
            return

        self.add_page()
        self._add_section_header('Approvals')
        self.ln(5)

        # Table setup
        col_widths = [40, 25, 35, 25, 30, 30]
        headers = ['Approver', 'Type', 'Region', 'Status', 'Date', 'Comments']

        # Table header
        self.set_fill_color(*HEADER_BG)
        self.set_text_color(*HEADER_TEXT)
        self.set_font('helvetica', 'B', 8)

        for header, width in zip(headers, col_widths):
            self.cell(width, 8, header, border=1, align='C', fill=True)
        self.ln()

        # Table rows
        self.set_font('helvetica', '', 8)
        self.set_text_color(*SECTION_TEXT)

        for approval in self.approvals:
            # Get approver name
            approver = approval.get('approver', {})
            if isinstance(approver, dict):
                approver_name = approver.get(
                    'full_name', approver.get('email', 'Unknown'))[:22]
            else:
                approver_name = str(approver)[:22] if approver else 'Pending'

            approval_type = approval.get('approval_type', 'Global')[:12]

            region = approval.get('region', {})
            if isinstance(region, dict):
                region_name = region.get('name', region.get('code', '-'))[:18]
            else:
                region_name = str(region)[:18] if region else '-'

            status = approval.get('approval_status', 'Pending')

            # Color code status
            if status == 'Approved':
                self.set_fill_color(*BG_GREEN)
            elif status == 'Rejected':
                self.set_fill_color(*BG_RED)  # Keep for historical records
            elif status == 'Sent Back':
                self.set_fill_color(*BG_YELLOW)
            else:
                self.set_fill_color(*BG_GRAY)

            approved_at = approval.get('approved_at', '')
            if isinstance(approved_at, datetime):
                date_str = approved_at.strftime('%Y-%m-%d')
            elif approved_at:
                date_str = str(approved_at)[:10]
            else:
                date_str = '-'

            raw_comments = approval.get('comments') or ''
            if not isinstance(raw_comments, str):
                raw_comments = str(raw_comments)
            comments = raw_comments[:15] + \
                ('...' if len(raw_comments) > 15 else '')

            # Draw cells
            self.cell(col_widths[0], 7, approver_name, border=1)
            self.cell(col_widths[1], 7, approval_type, border=1, align='C')
            self.cell(col_widths[2], 7, region_name, border=1, align='C')
            self.cell(col_widths[3], 7, status, border=1, align='C', fill=True)
            self.cell(col_widths[4], 7, date_str, border=1, align='C')
            self.cell(col_widths[5], 7, comments, border=1)
            self.ln()

    def _add_section_header(self, title: str):
        """Add a styled section header."""
        self.set_fill_color(*SECTION_BG)
        self.set_text_color(*SECTION_TEXT)
        self.set_font('helvetica', 'B', 12)
        self.cell(0, 10, title, border=0, fill=True, ln=True)
        self.set_draw_color(100, 100, 100)
        self.line(15, self.get_y(), 195, self.get_y())

    def generate(self) -> bytes:
        """Generate the complete PDF report.

        Returns:
            PDF file as bytes
        """
        self.alias_nb_pages()

        # Build the report
        self.add_cover_page()
        self.add_executive_summary()
        self.add_results_table()
        self.add_breach_analysis()
        self.add_trend_charts()
        self.add_approvals_section()

        # Return PDF bytes
        return bytes(self.output())


class ValidationScorecardPDF(FPDF):
    """Professional PDF generator for one-page Validation Scorecard export.

    Generates a formal scorecard document suitable for inclusion in validation reports,
    containing:
    - Header with model metadata and submission type
    - Overall assessment with rating badge and narrative
    - Criteria table grouped by sections with color-coded ratings
    - Footer with model usage and region checkboxes
    """

    def __init__(
        self,
        validation_request: Dict[str, Any],
        model: Dict[str, Any],
        scorecard_data: Dict[str, Any],
        dependencies: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        logo_path: Optional[str] = None,
        all_regions: Optional[List[str]] = None,
        all_categories: Optional[List[str]] = None,
        all_validation_types: Optional[List[str]] = None
    ):
        """Initialize the Validation Scorecard PDF.

        Args:
            validation_request: Validation request data with validation_type
            model: Model data with owner, model_type, deployed_regions
            scorecard_data: Scorecard response with criteria_details, section_summaries, overall_assessment
            dependencies: Optional dict with 'upstream' and 'downstream' lists
            logo_path: Optional path to company logo
            all_regions: Optional list of all available region names
            all_categories: Optional list of all available model type categories
            all_validation_types: Optional list of all available validation types
        """
        super().__init__(orientation='P', unit='mm', format='A4')
        self.validation_request = validation_request
        self.model = model
        self.scorecard_data = scorecard_data
        self.dependencies = dependencies or {'upstream': [], 'downstream': []}
        self.logo_path = logo_path
        self.all_regions = all_regions or [
            'United States', 'United Kingdom', 'EMEA', 'APAC', 'Canada']
        self.all_categories = all_categories or [
            'Scoring', 'Pricing', 'Risk Management', 'Forecasting', 'Regulatory', 'Other']
        self.all_validation_types = all_validation_types or [
            'New Model', 'New/Modified Payoff', 'Changes to Existing Model', 'Re-validation']

        # Page settings
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(10, 10, 10)

        # Group criteria by section
        self._group_criteria_by_section()

    def _group_criteria_by_section(self):
        """Group criteria details by section for table rendering."""
        self.sections = {}
        criteria_details = self.scorecard_data.get('criteria_details', [])

        for criterion in criteria_details:
            section_code = criterion.get('section_code', 'OTHER')
            if section_code not in self.sections:
                self.sections[section_code] = {
                    'criteria': [],
                    'name': None
                }
            self.sections[section_code]['criteria'].append(criterion)

        # Get section names from section_summaries
        for summary in self.scorecard_data.get('section_summaries', []):
            section_code = summary.get('section_code')
            if section_code in self.sections:
                self.sections[section_code]['name'] = summary.get(
                    'section_name', section_code)

    def header(self):
        """Add minimal header - logo only."""
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                self.image(self.logo_path, x=10, y=8, h=10)
            except Exception:
                pass

        # Add Title
        self.set_font('helvetica', 'B', 16)
        self.set_xy(0, 10)
        self.cell(0, 10, 'Scorecard', align='C', ln=True)
        self.ln(5)

    def footer(self):
        """Add page footer."""
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)

        # Request reference
        request_id = self.validation_request.get('request_id', '')
        model_name = self.model.get('model_name', '')
        self.cell(
            0, 5, f'Validation Request #{request_id} - {model_name}', align='C')

    def add_header_section(self):
        """Add the header section with model metadata and checkboxes."""
        self.set_font('helvetica', '', 9)
        self.set_text_color(0, 0, 0)

        start_y = self.get_y()

        # Left side: Model Info
        self.set_xy(10, start_y)
        self.set_font('helvetica', 'B', 9)
        self.cell(40, 5, 'Model Developer/Owner:')
        self.set_xy(50, start_y)
        self.set_font('helvetica', '', 9)
        self.cell(80, 5, self._get_owner_name())

        # Business Line (under Owner)
        self.set_xy(10, start_y + 6)
        self.set_font('helvetica', 'B', 9)
        self.cell(40, 5, 'Business Line:')
        self.set_xy(50, start_y + 6)
        self.set_font('helvetica', '', 9)
        self.cell(80, 5, self.model.get('business_line', '') or 'Unknown')

        self.set_xy(10, start_y + 12)
        self.set_font('helvetica', 'B', 9)
        self.cell(40, 5, 'Model Name:')
        self.set_xy(50, start_y + 12)
        self.set_font('helvetica', '', 9)
        self.cell(80, 5, self.model.get('model_name', 'Unknown'))

        self.set_xy(10, start_y + 18)
        self.set_font('helvetica', 'B', 9)
        self.cell(40, 5, 'Related Models:')
        self.set_xy(50, start_y + 18)
        self.set_font('helvetica', '', 9)
        self.multi_cell(80, 5, self._get_related_models_text())

        # Right side: Submission Type
        right_x = 140
        self.set_xy(right_x, start_y)
        self.set_font('helvetica', 'B', 9)
        self.cell(30, 5, 'Submission Type:')
        self.set_font('helvetica', '', 9)

        validation_type = self._get_validation_type()
        submission_types = self.all_validation_types

        curr_y = start_y + 6
        for stype in submission_types:
            self.set_xy(right_x, curr_y)
            # Check if type matches exactly (case-insensitive)
            is_checked = (validation_type.lower() == stype.lower())

            self._draw_checkbox(right_x, curr_y + 1, is_checked)
            self.set_xy(right_x + 5, curr_y)
            self.cell(50, 5, stype)
            curr_y += 5

        self.ln(10)

    def _add_metadata_row(self, label: str, value: str):
        """Add a label-value row in metadata section."""
        x = self.get_x()
        self.set_font('helvetica', 'B', 9)
        self.cell(35, 5, label)
        self.set_font('helvetica', '', 9)
        # Truncate long values
        max_len = 40
        display_value = value[:max_len] + \
            '...' if len(value) > max_len else value
        self.cell(55, 5, display_value, ln=True)
        self.set_x(x)

    def _draw_checkbox(self, x: float, y: float, checked: bool):
        """Draw a checkbox at position."""
        self.set_draw_color(100, 100, 100)
        self.rect(x, y, 3, 3)
        if checked:
            self.set_fill_color(31, 41, 55)
            self.rect(x + 0.5, y + 0.5, 2, 2, 'F')

    def _get_owner_name(self) -> str:
        """Get model owner name."""
        if 'owner_name' in self.model:
            return self.model['owner_name'] or 'Unknown'

        owner = self.model.get('owner', {})
        if isinstance(owner, dict):
            return owner.get('full_name', owner.get('email', 'Unknown'))
        return str(owner) if owner else 'Unknown'

    def _get_related_models_text(self) -> str:
        """Get related models text from dependencies."""
        upstream = self.dependencies.get('upstream', [])
        downstream = self.dependencies.get('downstream', [])

        related = []
        for dep in upstream[:2]:  # Limit to 2 upstream
            # Handle both nested (feeder_model) and flat (model_name) structures
            if 'feeder_model' in dep:
                name = dep.get('feeder_model', {}).get('model_name', '')
            else:
                name = dep.get('model_name', '')

            if name:
                related.append(name)

        for dep in downstream[:2]:  # Limit to 2 downstream
            # Handle both nested (consumer_model) and flat (model_name) structures
            if 'consumer_model' in dep:
                name = dep.get('consumer_model', {}).get('model_name', '')
            else:
                name = dep.get('model_name', '')

            if name:
                related.append(name)

        if not related:
            return 'None'
        return ', '.join(related[:3])  # Max 3 names

    def _get_validation_type(self) -> str:
        """Get validation type label."""
        val_type = self.validation_request.get('validation_type', {})
        if isinstance(val_type, dict):
            return val_type.get('label', val_type.get('code', ''))
        return str(val_type) if val_type else ''

    def add_overall_assessment(self):
        """Add overall assessment section with rating badge and narrative."""
        self._add_section_header('Overall Assessment')
        self.ln(3)

        overall = self.scorecard_data.get('overall_assessment', {})
        rating = overall.get('rating', 'N/A')
        narrative = overall.get('overall_assessment_narrative', '')

        # Rating badge
        badge_color = scorecard_rating_to_color(rating)
        self.set_fill_color(*badge_color)
        self.set_font('helvetica', 'B', 12)
        self.set_text_color(*SECTION_TEXT)

        badge_width = 35
        badge_x = 10
        self.set_x(badge_x)
        self.cell(badge_width, 10, rating or 'N/A',
                  border=1, align='C', fill=True)

        # Score info
        numeric_score = overall.get('numeric_score', 0)
        rated_sections = overall.get('rated_sections_count', 0)
        total_sections = overall.get('sections_count', 0)

        self.set_font('helvetica', '', 9)
        self.set_x(badge_x + badge_width + 5)
        self.cell(
            0, 10, f'Score: {numeric_score} | Sections Rated: {rated_sections}/{total_sections}')
        self.ln(12)

        # Narrative
        if narrative:
            self.set_font('helvetica', 'B', 9)
            self.cell(0, 5, 'Summary:', ln=True)
            self.set_font('helvetica', '', 9)
            self.set_fill_color(250, 250, 250)
            self.multi_cell(190, 5, narrative, border=1, fill=True)
        else:
            self.set_font('helvetica', 'I', 9)
            self.set_text_color(128, 128, 128)
            self.cell(0, 5, 'No overall assessment narrative provided.', ln=True)
            self.set_text_color(*SECTION_TEXT)

        self.ln(3)

    def add_scorecard_table(self):
        """Add the main scorecard criteria table."""
        self._add_section_header('Scorecard Assessment')
        self.ln(3)

        # Column widths (total = 190mm)
        # Criteria, Rating, Description, Comments
        col_widths = [60, 18, 56, 56]
        headers = ['Criteria', 'Rating', 'Description', 'Comments']

        # Table header
        self.set_fill_color(*HEADER_BG)
        self.set_text_color(*HEADER_TEXT)
        self.set_font('helvetica', 'B', 7)

        for header, width in zip(headers, col_widths):
            self.cell(width, 7, header, border=1, align='C', fill=True)
        self.ln()

        # Sort sections by code (1.0, 2.0, 3.0, etc.)
        sorted_sections = sorted(self.sections.items(), key=lambda x: x[0])

        self.set_font('helvetica', '', 7)
        self.set_text_color(*SECTION_TEXT)

        # Create a lookup for section summaries
        section_summaries = {
            s.get('section_code'): s
            for s in self.scorecard_data.get('section_summaries', [])
        }

        for section_code, section_data in sorted_sections:
            # Check for page break
            if self.get_y() > 250:
                self.add_page()
                # Repeat header
                self.set_fill_color(*HEADER_BG)
                self.set_text_color(*HEADER_TEXT)
                self.set_font('helvetica', 'B', 7)
                for header, width in zip(headers, col_widths):
                    self.cell(width, 7, header, border=1, align='C', fill=True)
                self.ln()
                self.set_font('helvetica', '', 7)
                self.set_text_color(*SECTION_TEXT)

            # Get section summary data
            summary = section_summaries.get(section_code, {})
            section_name = section_data.get('name', section_code)
            section_description = section_data.get('description') or ''
            section_rating = summary.get('rating', 'N/A')

            # Section header row
            self.set_fill_color(*SECTION_BG)
            self.set_font('helvetica', 'B', 7)

            # 1. Section Name (spans first column)
            self.cell(
                col_widths[0], 6, f'{section_code} - {section_name}', border=1, fill=True)

            # 2. Section Rating (spans Rating column)
            rating_bg = scorecard_rating_to_color(section_rating)
            self.set_fill_color(*rating_bg)
            self.cell(col_widths[1], 6, section_rating,
                      border=1, align='C', fill=True)

            # 3. Remaining columns (Description + Comments)
            self.set_fill_color(*SECTION_BG)
            self.cell(sum(col_widths[2:]), 6,
                      section_description, border=1, fill=True)

            self.ln()
            self.set_font('helvetica', '', 7)

            # Criteria rows
            for criterion in section_data['criteria']:
                # Check for page break
                if self.get_y() > 265:
                    self.add_page()
                    # Repeat header
                    self.set_fill_color(*HEADER_BG)
                    self.set_text_color(*HEADER_TEXT)
                    self.set_font('helvetica', 'B', 7)
                    for header, width in zip(headers, col_widths):
                        self.cell(width, 7, header, border=1,
                                  align='C', fill=True)
                    self.ln()
                    self.set_font('helvetica', '', 7)
                    self.set_text_color(*SECTION_TEXT)

                self._draw_criterion_row(criterion, col_widths)

    def _draw_criterion_row(self, criterion: Dict[str, Any], col_widths: List[int]):
        """Draw a single criterion row with wrapped text."""
        criterion_name = criterion.get(
            'criterion_name', criterion.get('criterion_code', ''))
        rating = criterion.get('rating', '')
        description = criterion.get('description', '') or ''
        comments = criterion.get('comments', '') or ''

        # Calculate row height based on content
        # Estimate characters per line
        chars_per_line_desc = max(1, int(col_widths[2] / 1.6))
        chars_per_line_comm = max(1, int(col_widths[3] / 1.6))

        desc_lines = max(1, len(description) //
                         chars_per_line_desc + 1) if description else 1
        comm_lines = max(1, len(comments) //
                         chars_per_line_comm + 1) if comments else 1
        name_lines = max(1, len(criterion_name) // 35 + 1)

        max_lines = min(4, max(desc_lines, comm_lines,
                        name_lines))  # Cap at 4 lines
        row_height = max(6, max_lines * 4)

        # Rating color
        rating_color = scorecard_rating_to_color(rating)

        # Starting Y position
        y_start = self.get_y()
        x_start = self.get_x()

        # Criteria name cell
        self.set_fill_color(255, 255, 255)
        self.rect(x_start, y_start, col_widths[0], row_height)
        self.set_xy(x_start + 1, y_start + 1)
        self.set_font('helvetica', '', 7)
        self.multi_cell(col_widths[0] - 2, 4, criterion_name[:80], border=0)

        # Rating cell (centered, colored)
        self.set_fill_color(*rating_color)
        x_rating = x_start + col_widths[0]
        self.rect(x_rating, y_start, col_widths[1], row_height, 'DF')
        self.set_xy(x_rating, y_start + (row_height - 4) / 2)
        self.set_font('helvetica', 'B', 7)
        self.cell(col_widths[1], 4, rating or '-', align='C')
        self.set_font('helvetica', '', 7)

        # Description cell
        self.set_fill_color(255, 255, 255)
        x_desc = x_rating + col_widths[1]
        self.rect(x_desc, y_start, col_widths[2], row_height)
        self.set_xy(x_desc + 1, y_start + 1)
        # Truncate description
        max_desc_chars = chars_per_line_desc * max_lines
        truncated_desc = description[:max_desc_chars] + \
            '...' if len(description) > max_desc_chars else description
        self.multi_cell(col_widths[2] - 2, 4, truncated_desc, border=0)

        # Comments cell
        x_comm = x_desc + col_widths[2]
        self.rect(x_comm, y_start, col_widths[3], row_height)
        self.set_xy(x_comm + 1, y_start + 1)
        # Truncate comments
        max_comm_chars = chars_per_line_comm * max_lines
        truncated_comm = comments[:max_comm_chars] + \
            '...' if len(comments) > max_comm_chars else comments
        self.multi_cell(col_widths[3] - 2, 4, truncated_comm, border=0)

        # Draw all borders
        self.set_draw_color(200, 200, 200)
        self.line(x_start, y_start, x_start + sum(col_widths), y_start)
        self.line(x_start, y_start + row_height, x_start +
                  sum(col_widths), y_start + row_height)
        for i, w in enumerate(col_widths):
            x = x_start + sum(col_widths[:i+1])
            self.line(x, y_start, x, y_start + row_height)
        self.line(x_start, y_start, x_start, y_start + row_height)

        # Move to next row
        self.set_xy(x_start, y_start + row_height)

    def add_footer_metadata(self):
        """Add footer section with Model Usage and Region checkboxes."""
        # Check if we need a new page
        if self.get_y() > 240:
            self.add_page()

        self.ln(5)
        self._add_section_header('Model Classification')
        self.ln(3)

        # Two column layout - wider left column for Model Usage + Type
        left_col_width = 115
        right_col_x = 135
        right_col_width = 60

        # Model Usage (left column)
        self.set_font('helvetica', 'B', 8)
        self.cell(left_col_width, 5, 'Model Usage:', ln=False)

        # Region of Usage (right column header)
        self.set_x(right_col_x)
        self.cell(right_col_width, 5, 'Region of Usage:', ln=True)

        model_category = self._get_model_category()
        deployed_regions = self._get_deployed_regions()

        # Model usage options (from ModelTypeCategory)
        usage_types = self.all_categories

        self.set_font('helvetica', '', 7)

        # Determine max rows needed (max of usage types or regions)
        regions = self.all_regions
        num_rows = max(len(usage_types), len(regions))

        for i in range(num_rows):
            # Model Usage (left column)
            if i < len(usage_types):
                usage = usage_types[i]
                self.set_x(15)
                checked = model_category and usage.lower() == model_category.lower()

                # Append specific model type if checked
                if checked:
                    specific_type = self._get_model_type()
                    if specific_type:
                        usage = f"{usage} ({specific_type})"

                self._draw_checkbox(self.get_x(), self.get_y() + 1, checked)
                self.set_x(self.get_x() + 5)
                self.cell(left_col_width - 5, 4, usage, ln=False)

            # Region checkbox (right column)
            if i < len(regions):
                region = regions[i]
                self.set_x(right_col_x)

                checked = any(region.lower() in r.lower()
                              for r in deployed_regions)
                self._draw_checkbox(self.get_x(), self.get_y() + 1, checked)
                self.set_x(self.get_x() + 5)
                self.cell(right_col_width - 5, 4, region)

            self.ln()

        # Regulatory Categories (below columns)
        self.ln(2)
        self.set_font('helvetica', 'B', 8)
        self.cell(35, 5, 'Regulatory Categories:', ln=False)
        self.set_font('helvetica', '', 8)
        reg_cats = self._get_regulatory_categories()
        self.cell(0, 5, reg_cats if reg_cats else 'None', ln=True)

    def _get_regulatory_categories(self) -> str:
        """Get comma-separated list of regulatory categories."""
        cats = self.model.get('regulatory_categories', [])
        return ', '.join(cats)

    def _get_model_type(self) -> str:
        """Get model type label."""
        model_type = self.model.get('model_type', {})
        if isinstance(model_type, dict):
            return model_type.get('label', model_type.get('code', ''))
        return str(model_type) if model_type else ''

    def _get_model_category(self) -> str:
        """Get model category name."""
        return self.model.get('model_category', '') or ''

    def _get_deployed_regions(self) -> List[str]:
        """Get list of deployed region names."""
        regions = self.model.get('deployed_regions', [])
        region_names = []
        for region in regions:
            if isinstance(region, dict):
                region_names.append(region.get('name', region.get('code', '')))
            else:
                region_names.append(str(region))
        return region_names

    def _add_section_header(self, title: str):
        """Add a styled section header."""
        self.set_fill_color(*SECTION_BG)
        self.set_text_color(*SECTION_TEXT)
        self.set_font('helvetica', 'B', 10)
        self.cell(0, 7, title, border=0, fill=True, ln=True)
        self.set_draw_color(100, 100, 100)
        self.line(15, self.get_y(), 195, self.get_y())

    def generate(self) -> bytes:
        """Generate the complete Validation Scorecard PDF.

        Returns:
            PDF file as bytes
        """
        self.add_page()

        # Build the report sections
        self.add_header_section()
        self.add_overall_assessment()
        self.add_scorecard_table()
        self.add_footer_metadata()

        # Return PDF bytes
        return bytes(self.output())


def generate_validation_scorecard_pdf(
    validation_request: Dict[str, Any],
    model: Dict[str, Any],
    scorecard_data: Dict[str, Any],
    dependencies: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    logo_path: Optional[str] = None,
    all_regions: Optional[List[str]] = None,
    all_categories: Optional[List[str]] = None,
    all_validation_types: Optional[List[str]] = None
) -> bytes:
    """Generate a Validation Scorecard PDF.

    Args:
        validation_request: Validation request data
        model: Model data with relationships
        scorecard_data: Scorecard response from API
        dependencies: Optional upstream/downstream dependencies
        logo_path: Optional path to company logo
        all_regions: Optional list of all available region names
        all_categories: Optional list of all available model type categories
        all_validation_types: Optional list of all available validation types

    Returns:
        PDF file as bytes
    """
    pdf = ValidationScorecardPDF(
        validation_request=validation_request,
        model=model,
        scorecard_data=scorecard_data,
        dependencies=dependencies,
        logo_path=logo_path,
        all_regions=all_regions,
        all_categories=all_categories,
        all_validation_types=all_validation_types
    )
    return pdf.generate()
