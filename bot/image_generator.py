"""
Image Generator Module
Provides flexible table-based image generation for various data displays
"""

from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Any, Optional, Tuple
import io
from datetime import datetime


class TableImageGenerator:
    """Generate beautiful table images with customizable styling"""

    # Default styling configuration
    DEFAULT_STYLE = {
        'background_color': (255, 255, 255),
        'gradient_strength': 15,  # 0 = no gradient, higher = stronger
        'padding': 25,
        'row_height': 45,
        'header_height': 40,
        'header_bg_color': (45, 45, 45),
        'header_text_color': (255, 255, 255),
        'header_border_color': (30, 30, 30),
        'card_shadow': True,
        'card_shadow_color': (200, 200, 200),
        'card_shadow_offset': 2,
        'alternating_rows': True,
        'row_color_1': (255, 255, 255),
        'row_color_2': (248, 248, 252),
        'row_border_color': (220, 220, 220),
        'outer_border_color': (60, 60, 60),
        'outer_border_width': 3,
        'logo_size': 80,
        'logo_top_margin': 10,
        'footer_text_color': (180, 180, 180),  # Light grey
        'footer_font_size': 22,
        'fixed_footer': 'CODEBLACK - 2026',  # Always shown
        'custom_footer': None,  # Optional additional footer
    }

    def __init__(self, style: Optional[Dict[str, Any]] = None):
        """
        Initialize the table image generator

        Args:
            style: Dictionary of style overrides for DEFAULT_STYLE
        """
        self.style = {**self.DEFAULT_STYLE, **(style or {})}
        self.fonts = self._load_fonts()

    def _load_fonts(self) -> Dict[str, Any]:
        """Load fonts with fallback support"""
        fonts = {}

        font_configs = {
            'header': ('arialbd.ttf', 15),
            'name_bold': ('arialbd.ttf', 14),
            'text_bold': ('arialbd.ttf', 12),
            'text_bold_large': ('arialbd.ttf', 16),  # For emphasized text like "REDACTED" group
            'regular': ('arial.ttf', 12),
            'id': ('arialbd.ttf', 14),
            'footer': ('arialbd.ttf', self.style['footer_font_size']),
        }

        for font_name, (font_file, size) in font_configs.items():
            try:
                fonts[font_name] = ImageFont.truetype(font_file, size)
            except:
                try:
                    # Try Linux font path
                    if 'bold' in font_name or 'bd' in font_file:
                        fonts[font_name] = ImageFont.truetype(
                            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size
                        )
                    else:
                        fonts[font_name] = ImageFont.truetype(
                            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size
                        )
                except:
                    fonts[font_name] = ImageFont.load_default()

        return fonts

    def generate_table(
        self,
        headers: List[str],
        rows: List[Dict[str, Any]],
        column_widths: Dict[str, int],
        logo_path: Optional[str] = None,
        footer_text: Optional[str] = None,
        title: Optional[str] = None,
        page_header: Optional[str] = None
    ) -> io.BytesIO:
        """
        Generate a table image

        Args:
            headers: List of column header names
            rows: List of row data dictionaries. Each dict should have:
                - Keys matching column names
                - Optional 'color' key for colored text (RGB tuple)
                - Optional 'style' key for cell styling
            column_widths: Dictionary mapping column keys to pixel widths
            logo_path: Optional path to logo image
            footer_text: Optional footer text
            title: Optional title text above the table

        Returns:
            BytesIO object containing the PNG image
        """
        # Calculate dimensions
        padding = self.style['padding']
        logo_height = self.style['logo_size'] + 30 if logo_path else 0
        page_header_height = 60 if page_header else 0
        title_height = 40 if title else 0
        header_height = self.style['header_height']
        row_height = self.style['row_height']
        # Always have footer height for fixed footer, add more if custom footer
        footer_height = 80 if footer_text else 60

        total_width = sum(column_widths.values()) + (padding * 2)
        total_height = (
            logo_height + page_header_height + title_height + padding + header_height +
            (len(rows) * row_height) + footer_height
        )

        # Create image with gradient background
        img = Image.new('RGB', (total_width, total_height),
                       color=self.style['background_color'])
        draw = ImageDraw.Draw(img)

        # Draw gradient background
        if self.style['gradient_strength'] > 0:
            for y in range(total_height):
                gradient_value = int(255 - (y / total_height) * self.style['gradient_strength'])
                draw.line([(0, y), (total_width, y)],
                         fill=(gradient_value, gradient_value, gradient_value))

        current_y = 0

        # Add logo if provided
        if logo_path:
            current_y = self._draw_logo(img, logo_path, total_width)

        # Add page header if provided (between logo and content)
        if page_header:
            current_y = self._draw_page_header(draw, page_header, total_width, current_y)

        # Add title if provided
        if title:
            current_y = self._draw_title(draw, title, total_width, current_y)

        # Draw table header
        header_y = current_y + padding
        header_positions = self._draw_header(
            draw, headers, column_widths, padding, header_y, total_width
        )

        # Draw table rows
        rows_start_y = header_y + header_height + 5
        self._draw_rows(
            draw, rows, column_widths, header_positions,
            rows_start_y, row_height
        )

        # Draw footer (always drawn for fixed footer)
        footer_y = total_height - footer_height
        self._draw_footer(draw, footer_text, total_width, footer_y)

        # Draw outer border
        draw.rectangle(
            [0, 0, total_width - 1, total_height - 1],
            outline=self.style['outer_border_color'],
            width=self.style['outer_border_width']
        )

        # Save to BytesIO
        output = io.BytesIO()
        img.save(output, 'PNG')
        output.seek(0)
        return output

    def generate_empty_message(
        self,
        message: str,
        logo_path: Optional[str] = None,
        page_header: Optional[str] = None
    ) -> io.BytesIO:
        """
        Generate a simple image with just a message (for when there's no data to display)

        Args:
            message: The message to display (e.g., "No online Player currently")
            logo_path: Optional path to logo image
            page_header: Optional page header text

        Returns:
            BytesIO object containing the PNG image
        """
        # Calculate dimensions
        padding = self.style['padding']
        logo_height = self.style['logo_size'] + 30 if logo_path else 0
        page_header_height = 60 if page_header else 0
        message_height = 100
        footer_height = 60

        total_width = 800
        total_height = logo_height + page_header_height + message_height + footer_height + padding * 2

        # Create image with gradient background
        img = Image.new('RGB', (total_width, total_height), color=self.style['background_color'])
        draw = ImageDraw.Draw(img)

        # Draw gradient background
        if self.style['gradient_strength'] > 0:
            for y in range(total_height):
                gradient_value = int(255 - (y / total_height) * self.style['gradient_strength'])
                draw.line([(0, y), (total_width, y)], fill=(gradient_value, gradient_value, gradient_value))

        current_y = 0

        # Add logo if provided
        if logo_path:
            current_y = self._draw_logo(img, logo_path, total_width)

        # Add page header if provided
        if page_header:
            current_y = self._draw_page_header(draw, page_header, total_width, current_y)

        # Draw the message
        try:
            message_font = ImageFont.truetype("arialbd.ttf", 24)
        except:
            try:
                message_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            except:
                message_font = self.fonts['header']

        message_bbox = draw.textbbox((0, 0), message, font=message_font)
        message_width = message_bbox[2] - message_bbox[0]
        message_x = (total_width - message_width) // 2
        message_y = current_y + 40

        draw.text(
            (message_x, message_y),
            message,
            fill=(100, 100, 100),
            font=message_font
        )

        # Draw footer
        footer_y = total_height - footer_height
        self._draw_footer(draw, None, total_width, footer_y)

        # Draw outer border
        draw.rectangle(
            [0, 0, total_width - 1, total_height - 1],
            outline=self.style['outer_border_color'],
            width=self.style['outer_border_width']
        )

        # Save to BytesIO
        output = io.BytesIO()
        img.save(output, 'PNG')
        output.seek(0)
        return output

    def _draw_logo(self, img: Image.Image, logo_path: str, total_width: int) -> int:
        """Draw logo at top center, returns Y position after logo"""
        try:
            logo = Image.open(logo_path)
            logo_size = self.style['logo_size']
            logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            logo_x = (total_width - logo_size) // 2
            logo_y = self.style['logo_top_margin']

            if logo.mode == 'RGBA':
                img.paste(logo, (logo_x, logo_y), logo)
            else:
                img.paste(logo, (logo_x, logo_y))

            return logo_y + logo_size + 10
        except Exception as e:
            print(f"Could not load logo: {e}")
            return 0

    def _draw_page_header(self, draw: ImageDraw.Draw, page_header: str,
                         total_width: int, current_y: int) -> int:
        """Draw page header text (large, centered, bold), returns Y position after header"""
        # Use a larger, bold font for the page header
        try:
            page_header_font = ImageFont.truetype("arialbd.ttf", 28)
        except:
            try:
                page_header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
            except:
                page_header_font = self.fonts['header']

        header_bbox = draw.textbbox((0, 0), page_header, font=page_header_font)
        header_width = header_bbox[2] - header_bbox[0]

        # Draw centered, with black color
        draw.text(
            ((total_width - header_width) // 2, current_y + 15),
            page_header,
            fill=(0, 0, 0),
            font=page_header_font
        )
        return current_y + 60

    def _draw_title(self, draw: ImageDraw.Draw, title: str,
                    total_width: int, current_y: int) -> int:
        """Draw title text, returns Y position after title"""
        title_bbox = draw.textbbox((0, 0), title, font=self.fonts['header'])
        title_width = title_bbox[2] - title_bbox[0]
        draw.text(
            ((total_width - title_width) // 2, current_y + 10),
            title,
            fill=(50, 50, 50),
            font=self.fonts['header']
        )
        return current_y + 40

    def _draw_header(
        self, draw: ImageDraw.Draw, headers: List[str],
        column_widths: Dict[str, int], padding: int,
        header_y: int, total_width: int
    ) -> List[int]:
        """Draw table header, returns list of column X positions"""
        # Draw header background
        draw.rectangle(
            [padding, header_y, total_width - padding, header_y + self.style['header_height']],
            fill=self.style['header_bg_color'],
            outline=self.style['header_border_color'],
            width=2
        )

        # Draw column headers
        x_pos = padding + 10
        header_positions = []

        for col_key, header_text in zip(column_widths.keys(), headers):
            draw.text(
                (x_pos, header_y + 12),
                header_text,
                fill=self.style['header_text_color'],
                font=self.fonts['header']
            )
            header_positions.append(x_pos)
            x_pos += column_widths[col_key]

        return header_positions

    def _draw_rows(
        self, draw: ImageDraw.Draw, rows: List[Dict[str, Any]],
        column_widths: Dict[str, int], header_positions: List[int],
        start_y: int, row_height: int
    ):
        """Draw all table rows"""
        padding = self.style['padding']
        total_width = sum(column_widths.values()) + (padding * 2)

        for i, row_data in enumerate(rows):
            y_pos = start_y + (i * row_height)

            # Draw card background with shadow
            if self.style['card_shadow']:
                card_rect = [padding + 5, y_pos, total_width - padding - 5,
                           y_pos + row_height - 5]
                shadow_offset = self.style['card_shadow_offset']
                draw.rectangle(
                    [card_rect[0] + shadow_offset, card_rect[1] + shadow_offset,
                     card_rect[2] + shadow_offset, card_rect[3] + shadow_offset],
                    fill=self.style['card_shadow_color']
                )
            else:
                card_rect = [padding, y_pos, total_width - padding, y_pos + row_height - 5]

            # Alternating row colors
            if self.style['alternating_rows'] and i % 2 == 0:
                card_color = self.style['row_color_1']
            else:
                card_color = self.style['row_color_2']

            draw.rectangle(
                card_rect,
                fill=card_color,
                outline=self.style['row_border_color'],
                width=1
            )

            # Draw cells
            for col_idx, (col_key, x_pos) in enumerate(zip(column_widths.keys(), header_positions)):
                cell_value = row_data.get(col_key, '')
                cell_style = row_data.get(f'{col_key}_style', {})

                self._draw_cell(
                    draw, cell_value, cell_style, x_pos, y_pos,
                    i, col_idx, col_key
                )

    def _draw_cell(
        self, draw: ImageDraw.Draw, value: Any, style: Dict[str, Any],
        x_pos: int, y_pos: int, row_idx: int, col_idx: int, col_key: str
    ):
        """Draw a single cell with optional styling"""
        # Determine text and color
        text = str(value)
        color = style.get('color', (0, 0, 0))
        font = self.fonts.get(style.get('font', 'regular'), self.fonts['regular'])

        # Handle special cell types
        cell_type = style.get('type', 'text')

        if cell_type == 'circle_number':
            # Draw filled circle with number
            circle_x = x_pos + 15
            circle_y = y_pos + 20
            draw.ellipse(
                [circle_x - 15, circle_y - 15, circle_x + 15, circle_y + 15],
                fill=style.get('circle_color', (255, 255, 255))
            )
            num_bbox = draw.textbbox((0, 0), text, font=self.fonts['id'])
            num_width = num_bbox[2] - num_bbox[0]
            draw.text(
                (circle_x - num_width // 2, circle_y - 8),
                text,
                fill=color,
                font=self.fonts['id']
            )
        elif cell_type == 'bullet_text':
            # Draw bullet point with text - use custom bullet_color from style if provided
            bullet_color = style.get('bullet_color', (100, 100, 255))
            draw.text((x_pos - 8, y_pos + 13), "•", fill=bullet_color, font=self.fonts['header'])
            draw.text((x_pos + 5, y_pos + 13), text[:15], fill=color, font=font)
        else:
            # Regular text
            y_offset = 13 if cell_type == 'text' else 14
            draw.text((x_pos, y_pos + y_offset), text, fill=color, font=font)

    def _draw_footer(
        self, draw: ImageDraw.Draw, footer_text: Optional[str],
        total_width: int, footer_y: int
    ):
        """Draw footer text with fixed and optional custom footer"""
        # Always draw the fixed footer
        fixed_footer = self.style['fixed_footer']
        fixed_bbox = draw.textbbox((0, 0), fixed_footer, font=self.fonts['footer'])
        fixed_width = fixed_bbox[2] - fixed_bbox[0]

        # If there's a custom footer, show both
        if footer_text and footer_text != fixed_footer:
            # Draw custom footer on top
            custom_bbox = draw.textbbox((0, 0), footer_text, font=self.fonts['footer'])
            custom_width = custom_bbox[2] - custom_bbox[0]
            draw.text(
                ((total_width - custom_width) // 2, footer_y + 5),
                footer_text,
                fill=self.style['footer_text_color'],
                font=self.fonts['footer']
            )
            # Draw fixed footer below
            draw.text(
                ((total_width - fixed_width) // 2, footer_y + 35),
                fixed_footer,
                fill=self.style['footer_text_color'],
                font=self.fonts['footer']
            )
        else:
            # Only draw fixed footer centered
            draw.text(
                ((total_width - fixed_width) // 2, footer_y + 15),
                fixed_footer,
                fill=self.style['footer_text_color'],
                font=self.fonts['footer']
            )

        # Draw date and time in bottom right corner
        current_datetime = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        try:
            date_font = ImageFont.truetype("arial.ttf", 10)
        except:
            try:
                date_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            except:
                date_font = self.fonts['regular']

        date_bbox = draw.textbbox((0, 0), current_datetime, font=date_font)
        date_width = date_bbox[2] - date_bbox[0]
        draw.text(
            (total_width - date_width - 10, footer_y + 40),
            current_datetime,
            fill=(0, 0, 0),
            font=date_font
        )


def generate_cop_live_scores_image(scores: List[Dict[str, Any]]) -> io.BytesIO:
    """
    Generate cop live scores table image with top 3 prominently displayed

    Args:
        scores: List of score dictionaries with keys: group, arrest_points

    Returns:
        BytesIO object containing the PNG image
    """
    from PIL import ImageDraw, ImageFont

    # Only show top 10 groups
    scores = scores[:10] if len(scores) > 10 else scores

    # Split top 3 and rest
    top_3 = scores[:3] if len(scores) >= 3 else scores
    rest = scores[3:] if len(scores) > 3 else []

    # Custom image generation for top 3 + table for rest
    style = TableImageGenerator.DEFAULT_STYLE.copy()

    # Calculate dimensions
    padding = 25
    logo_size = 80
    logo_height = logo_size + 30
    page_header_height = 60  # Space for page header

    # Top 3 section dimensions
    top3_card_width = 250
    top3_card_height = 150
    top3_spacing = 20
    top3_section_height = logo_height + page_header_height + top3_card_height + 80

    # Table section for rest
    if rest:
        row_height = 45
        header_height = 40
        table_height = header_height + (len(rest) * row_height) + 60
    else:
        table_height = 0

    footer_height = 60
    total_width = (top3_card_width * 3) + (top3_spacing * 4) + (padding * 2)
    total_height = top3_section_height + table_height + footer_height + padding

    # Create image
    img = Image.new('RGB', (total_width, total_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Draw gradient background
    for y in range(total_height):
        gradient_value = int(255 - (y / total_height) * 15)
        draw.line([(0, y), (total_width, y)], fill=(gradient_value, gradient_value, gradient_value))

    # Load logo
    try:
        logo = Image.open("media/REDACTED-round-logo.png")
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        logo_x = (total_width - logo_size) // 2
        logo_y = 10
        if logo.mode == 'RGBA':
            img.paste(logo, (logo_x, logo_y), logo)
        else:
            img.paste(logo, (logo_x, logo_y))
    except Exception as e:
        print(f"Could not load logo: {e}")

    # Load fonts
    try:
        font_page_header = ImageFont.truetype("arialbd.ttf", 28)  # Page header font
        font_rank_large = ImageFont.truetype("arialbd.ttf", 48)
        font_group_large = ImageFont.truetype("arialbd.ttf", 18)
        font_group_REDACTED = ImageFont.truetype("arialbd.ttf", 22)  # Bigger font for REDACTED
        font_points_large = ImageFont.truetype("arialbd.ttf", 24)
        font_label = ImageFont.truetype("arial.ttf", 12)
        font_header = ImageFont.truetype("arialbd.ttf", 15)
        font_regular = ImageFont.truetype("arialbd.ttf", 12)
        font_footer = ImageFont.truetype("arialbd.ttf", 22)  # Bigger footer font
    except:
        try:
            font_page_header = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)  # Page header font
            font_rank_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            font_group_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
            font_group_REDACTED = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)  # Bigger font for REDACTED
            font_points_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            font_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            font_header = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
            font_regular = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
            font_footer = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)  # Bigger footer font
        except:
            font_page_header = ImageFont.load_default()
            font_rank_large = ImageFont.load_default()
            font_group_large = ImageFont.load_default()
            font_group_REDACTED = ImageFont.load_default()
            font_points_large = ImageFont.load_default()
            font_label = ImageFont.load_default()
            font_header = ImageFont.load_default()
            font_regular = ImageFont.load_default()
            font_footer = ImageFont.load_default()

    # Draw page header
    page_header_text = "Top Cop Live Scores"
    header_bbox = draw.textbbox((0, 0), page_header_text, font=font_page_header)
    header_width = header_bbox[2] - header_bbox[0]
    draw.text(
        ((total_width - header_width) // 2, logo_height + 15),
        page_header_text,
        fill=(0, 0, 0),
        font=font_page_header
    )

    # Medal colors for top 3
    medal_colors = [
        (255, 215, 0),   # Gold
        (192, 192, 192), # Silver
        (205, 127, 50)   # Bronze
    ]

    # Draw top 3 cards in podium order: 2-1-3 (silver-gold-bronze)
    top3_y_start = logo_height + page_header_height + 30
    podium_order = [1, 0, 2]  # Render order: 2nd place (left), 1st place (center), 3rd place (right)

    for display_position, rank_index in enumerate(podium_order):
        if rank_index >= len(top_3):
            continue

        score = top_3[rank_index]
        i = rank_index  # Keep original rank for medal color
        x_pos = padding + top3_spacing + (display_position * (top3_card_width + top3_spacing))
        y_pos = top3_y_start

        # Card shadow
        shadow_offset = 4
        draw.rectangle(
            [x_pos + shadow_offset, y_pos + shadow_offset,
             x_pos + top3_card_width + shadow_offset, y_pos + top3_card_height + shadow_offset],
            fill=(180, 180, 180)
        )

        # Card background
        draw.rectangle(
            [x_pos, y_pos, x_pos + top3_card_width, y_pos + top3_card_height],
            fill=(255, 255, 255),
            outline=medal_colors[i],
            width=4
        )

        # Medal icon area at top with colored background
        medal_bar_height = 50
        draw.rectangle(
            [x_pos + 1, y_pos + 1, x_pos + top3_card_width - 1, y_pos + medal_bar_height],
            fill=medal_colors[i]
        )

        # Rank number in medal bar
        rank_text = str(i + 1)
        rank_bbox = draw.textbbox((0, 0), rank_text, font=font_rank_large)
        rank_width = rank_bbox[2] - rank_bbox[0]
        rank_height = rank_bbox[3] - rank_bbox[1]
        draw.text(
            (x_pos + (top3_card_width // 2) - rank_width // 2, y_pos - 2),
            rank_text,
            fill=(0, 0, 0),
            font=font_rank_large
        )

        # Group name
        group_name = score.get('group', 'Unknown')
        is_REDACTED = group_name.lower() == 'REDACTED'

        # Truncate if too long
        if len(group_name) > 18:
            group_name = group_name[:15] + "..."

        # Use bigger font for REDACTED
        group_font = font_group_REDACTED if is_REDACTED else font_group_large
        group_bbox = draw.textbbox((0, 0), group_name, font=group_font)
        group_width = group_bbox[2] - group_bbox[0]
        draw.text(
            (x_pos + (top3_card_width // 2) - group_width // 2, y_pos + medal_bar_height + 15),
            group_name,
            fill=(0, 0, 0),
            font=group_font
        )

        # Arrest points label
        label_text = "Arrest Points"
        label_bbox = draw.textbbox((0, 0), label_text, font=font_label)
        label_width = label_bbox[2] - label_bbox[0]
        draw.text(
            (x_pos + (top3_card_width // 2) - label_width // 2, y_pos + medal_bar_height + 45),
            label_text,
            fill=(100, 100, 100),
            font=font_label
        )

        # Arrest points value
        arrest_points = score.get('arrest_points', '0')
        points_bbox = draw.textbbox((0, 0), arrest_points, font=font_points_large)
        points_width = points_bbox[2] - points_bbox[0]
        draw.text(
            (x_pos + (top3_card_width // 2) - points_width // 2, y_pos + medal_bar_height + 65),
            arrest_points,
            fill=(34, 139, 34),
            font=font_points_large
        )

    # Draw rest of groups in table format
    if rest:
        table_y_start = top3_section_height

        # Table header
        header_y = table_y_start
        draw.rectangle(
            [padding, header_y, total_width - padding, header_y + header_height],
            fill=(45, 45, 45),
            outline=(30, 30, 30),
            width=2
        )

        # Column widths for rest table
        col_rank_x = padding + 20
        col_group_x = padding + 100
        col_points_x = total_width - padding - 200

        draw.text((col_rank_x, header_y + 12), "#", fill=(255, 255, 255), font=font_header)
        draw.text((col_group_x, header_y + 12), "Group Name", fill=(255, 255, 255), font=font_header)
        draw.text((col_points_x, header_y + 12), "Arrest Points", fill=(255, 255, 255), font=font_header)

        # Draw rows
        row_y_start = header_y + header_height + 5
        for i, score in enumerate(rest):
            row_idx = i + 3  # Start from rank 4
            y_pos = row_y_start + (i * row_height)

            # Row background
            card_rect = [padding + 5, y_pos, total_width - padding - 5, y_pos + row_height - 5]
            shadow_offset = 2
            draw.rectangle(
                [card_rect[0] + shadow_offset, card_rect[1] + shadow_offset,
                 card_rect[2] + shadow_offset, card_rect[3] + shadow_offset],
                fill=(200, 200, 200)
            )

            card_color = (255, 255, 255) if i % 2 == 0 else (248, 248, 252)
            draw.rectangle(card_rect, fill=card_color, outline=(220, 220, 220), width=1)

            # Rank number
            draw.text((col_rank_x + 10, y_pos + 15), str(row_idx + 1), fill=(0, 0, 0), font=font_regular)

            # Group name
            group_name = score.get('group', 'Unknown')
            is_REDACTED = group_name.lower() == 'REDACTED'
            group_font = font_group_large if is_REDACTED else font_regular
            draw.text((col_group_x, y_pos + 15), group_name, fill=(0, 0, 0), font=group_font)

            # Arrest points
            arrest_points = score.get('arrest_points', '0')
            draw.text((col_points_x, y_pos + 15), arrest_points, fill=(34, 139, 34), font=font_regular)

    # Footer
    footer_y = total_height - footer_height
    footer_text = "CODEBLACK - 2026"
    footer_bbox = draw.textbbox((0, 0), footer_text, font=font_footer)
    footer_width = footer_bbox[2] - footer_bbox[0]
    draw.text(
        ((total_width - footer_width) // 2, footer_y + 15),
        footer_text,
        fill=(180, 180, 180),  # Light grey
        font=font_footer
    )

    # Draw date and time in bottom right corner
    current_datetime = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    try:
        date_font = ImageFont.truetype("arial.ttf", 10)
    except:
        try:
            date_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        except:
            date_font = font_label

    date_bbox = draw.textbbox((0, 0), current_datetime, font=date_font)
    date_width = date_bbox[2] - date_bbox[0]
    draw.text(
        (total_width - date_width - 10, footer_y + 40),
        current_datetime,
        fill=(0, 0, 0),
        font=date_font
    )

    # Draw outer border
    draw.rectangle([0, 0, total_width - 1, total_height - 1], outline=(60, 60, 60), width=3)

    # Save to BytesIO
    output = io.BytesIO()
    img.save(output, 'PNG')
    output.seek(0)
    return output


def generate_online_players_image(players: List[Dict[str, Any]]) -> io.BytesIO:
    """
    Generate online players table image (convenience function)

    Args:
        players: List of player dictionaries with keys: name, occupation, wl, cash, playtime, ping, rgb_color

    Returns:
        BytesIO object containing the PNG image
    """
    generator = TableImageGenerator()

    # If no players online, create a simple message image
    if not players or len(players) == 0:
        return generator.generate_empty_message(
            message="No online Player currently",
            logo_path="media/REDACTED-round-logo.png",
            page_header="Current online Players"
        )

    # Define columns
    column_widths = {
        'num': 50,
        'name': 220,
        'occupation': 140,
        'wl': 90,
        'cash': 110,
        'playtime': 110,
        'ping': 70
    }

    headers = ['#', 'Player Name', 'Occupation', 'W/L', 'Cash', 'Playtime', 'Ping']

    # Format rows
    rows = []
    for i, player in enumerate(players):
        rgb = player.get('rgb_color')
        name_color = (rgb['r'], rgb['g'], rgb['b']) if rgb else (0, 0, 0)

        # Determine ping color
        try:
            ping_val = int(player.get('ping', '0')) if str(player.get('ping', '0')).isdigit() else 0
            if ping_val < 100:
                ping_color = (0, 200, 0)
            elif ping_val < 200:
                ping_color = (255, 165, 0)
            else:
                ping_color = (255, 0, 0)
        except:
            ping_color = (0, 0, 0)

        row = {
            'num': str(i + 1),
            'num_style': {'type': 'circle_number', 'color': (0, 0, 0)},
            'name': player.get('name', 'N/A'),
            'name_style': {'color': name_color, 'font': 'name_bold'},
            'occupation': player.get('occupation', 'N/A'),
            'occupation_style': {'type': 'bullet_text', 'color': (50, 50, 50),
                               'font': 'text_bold', 'bullet_color': name_color},
            'wl': player.get('wl', 'N/A'),
            'wl_style': {'color': (0, 0, 0)},
            'cash': player.get('cash', 'N/A'),
            'cash_style': {'color': (34, 139, 34)},
            'playtime': player.get('playtime', 'N/A'),
            'playtime_style': {'color': (0, 0, 0)},
            'ping': player.get('ping', 'N/A'),
            'ping_style': {'color': ping_color}
        }
        rows.append(row)

    return generator.generate_table(
        headers=headers,
        rows=rows,
        column_widths=column_widths,
        logo_path="media/REDACTED-round-logo.png",
        footer_text=None,  # Use fixed footer only
        page_header="Current online Players"
    )
