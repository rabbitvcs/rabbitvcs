"""Cell renderer for directed graph.

This module contains the implementation of a custom GtkCellRenderer that
draws part of the directed graph based on the lines suggested by the code
in graph.py.

Because we're shiny, we use Cairo to do this, and because we're naughty
we cheat and draw over the bits of the TreeViewColumn that are supposed to
just be for the background.
"""
from __future__ import absolute_import

__copyright__ = "Copyright 2005 Canonical Ltd."
__author__    = "Scott James Remnant <scott@ubuntu.com>"

import math

import gtk
import gobject
import pango
import cairo

# Styles used when rendering revision graph edges
style_SOLID = 0
style_DASHED = 1

class CellRendererGraph(gtk.GenericCellRenderer):
    """Cell renderer for directed graph.

    Properties:
      node              (column, colour) tuple to draw revision node,
      in_lines          (start, end, colour, style) tuple list to draw inward lines,
      out_lines         (start, end, colour, style) tuple list to draw outward lines.
    """

    columns_len = 0

    __gproperties__ = {
        "graph":         ( gobject.TYPE_PYOBJECT, "graph",
                          "revision node instruction",
                          gobject.PARAM_WRITABLE
                        )
        }

    def do_set_property(self, property, value):
        """Set properties from GObject properties."""

        if not value:
            return

        if property.name == "graph":
            (self.node, self.in_lines, self.out_lines) = value
        else:
            raise AttributeError("no such property: '%s'" % property.name)

    def box_size(self, widget):
        """Calculate box size based on widget's font.

        Cache this as it's probably expensive to get.  It ensures that we
        draw the graph at least as large as the text.
        """
        try:
            return self._box_size
        except AttributeError:
            pango_ctx = widget.get_pango_context()
            font_desc = widget.get_style().font_desc
            metrics = pango_ctx.get_metrics(font_desc)

            ascent = pango.PIXELS(metrics.get_ascent())
            descent = pango.PIXELS(metrics.get_descent())

            self._box_size = ascent + descent + 1
            return self._box_size

    def set_colour(self, ctx, colour, bg, fg):
        """Set the context source colour.

        Picks a distinct colour based on an internal wheel; the bg
        parameter provides the value that should be assigned to the 'zero'
        colours and the fg parameter provides the multiplier that should be
        applied to the foreground colours.
        """

        if isinstance(colour, str):
            r, g, b = colour[1:3], colour[3:5], colour[5:7]
            colour_rgb = int(r, 16) / 255., int(g, 16) / 255., int(b, 16) / 255.
        else:
            if colour == 0:
                colour_rgb = gtklib.MAINLINE_COLOR
            else:
                colour_rgb = gtklib.LINE_COLORS[colour % len(gtklib.LINE_COLORS)]

        red   = (colour_rgb[0] * fg) or bg
        green = (colour_rgb[1] * fg) or bg
        blue  = (colour_rgb[2] * fg) or bg

        ctx.set_source_rgb(red, green, blue)

    def on_get_size(self, widget, cell_area):
        """Return the size we need for this cell.

        Each cell is drawn individually and is only as wide as it needs
        to be, we let the TreeViewColumn take care of making them all
        line up.
        """
        box_size = self.box_size(widget) + 1

        width = box_size * (self.columns_len + 1)
        height = box_size

        # FIXME I have no idea how to use cell_area properly
        return (0, 0, width, height)

    def on_render(self, window, widget, bg_area, cell_area, exp_area, flags):
        """Render an individual cell.

        Draws the cell contents using cairo, taking care to clip what we
        do to within the background area so we don't draw over other cells.
        Note that we're a bit naughty there and should really be drawing
        in the cell_area (or even the exposed area), but we explicitly don't
        want any gutter.

        We try and be a little clever, if the line we need to draw is going
        to cross other columns we actually draw it as in the .---' style
        instead of a pure diagonal ... this reduces confusion by an
        incredible amount.
        """
        ctx = window.cairo_create()
        ctx.rectangle(bg_area.x, bg_area.y, bg_area.width, bg_area.height)
        ctx.clip()

        box_size = self.box_size(widget)

        # Maybe draw branch head highlight under revision node
        if self.node:
            (column, colour) = self.node
            arc_start_position_x = cell_area.x + box_size * column + box_size / 2; 
            arc_start_position_y = cell_area.y + cell_area.height / 2;

        ctx.set_line_width(box_size / 8)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        
        # Draw lines into the cell
        if self.in_lines:
            for start, end, lcolour in self.in_lines:
                style = style_SOLID
                self.render_line (ctx, cell_area, box_size,
                             bg_area.y, bg_area.height,
                             start, end, lcolour, style)

        # Draw lines out of the cell
        if self.out_lines:
            for start, end, lcolour in self.out_lines:
                style = style_SOLID
                self.render_line (ctx, cell_area, box_size,
                             bg_area.y + bg_area.height, bg_area.height,
                             start, end, lcolour, style)

        # Draw the revision node in the right column
        if not self.node:
            return

        ctx.arc(arc_start_position_x, arc_start_position_y,
                    box_size / 5, 0, 2 * math.pi)
        self.set_colour(ctx, colour, 0.0, 0.5)
        ctx.stroke_preserve()
        self.set_colour(ctx, colour, 0.5, 1.0)
        ctx.fill()

    def render_line (self, ctx, cell_area, box_size, mid,
            height, start, end, colour, style):
        if start is None:
            x = cell_area.x + box_size * end + box_size / 2
            ctx.move_to(x, mid + height / 3)
            ctx.line_to(x, mid + height / 3)
            ctx.move_to(x, mid + height / 6)
            ctx.line_to(x, mid + height / 6)

        elif end is None:
            x = cell_area.x + box_size * start + box_size / 2
            ctx.move_to(x, mid - height / 3)
            ctx.line_to(x, mid - height / 3)
            ctx.move_to(x, mid - height / 6)
            ctx.line_to(x, mid - height / 6)
        else:
            startx = cell_area.x + box_size * start + box_size / 2
            endx = cell_area.x + box_size * end + box_size / 2

            ctx.move_to(startx, mid - height / 2)

            if start - end == 0 :
                ctx.line_to(endx, mid + height / 2)
            else:
                ctx.curve_to(startx, mid - height / 5,
                             startx, mid - height / 5,
                             startx + (endx - startx) / 2, mid)

                ctx.curve_to(endx, mid + height / 5,
                             endx, mid + height / 5 ,
                             endx, mid + height / 2)

        self.set_colour(ctx, colour, 0.0, 0.65)
        if style == style_DASHED:
            dashes = [1, 2]
            ctx.set_dash(dashes)
        ctx.stroke()
        ctx.set_dash([])
