package com.iiipoints.kompakt;

import android.graphics.Path;

/** Minimal SVG path-data parser (M L H V C S Q T Z, absolute and relative). */
final class SvgPath {
    private final String s;
    private int i;

    private SvgPath(String s) {
        this.s = s;
    }

    static Path parse(String d) {
        Path p = new Path();
        new SvgPath(d).into(p);
        return p;
    }

    private void into(Path p) {
        float x = 0, y = 0, sx = 0, sy = 0, cx = 0, cy = 0;
        char cmd = 'M', prev = ' ';
        while (true) {
            skip();
            if (i >= s.length()) break;
            char c = s.charAt(i);
            if (Character.isLetter(c)) {
                cmd = c;
                i++;
            } else if (cmd == 'M') {
                cmd = 'L';
            } else if (cmd == 'm') {
                cmd = 'l';
            }
            boolean rel = Character.isLowerCase(cmd);
            float ox = rel ? x : 0, oy = rel ? y : 0;
            switch (Character.toUpperCase(cmd)) {
                case 'M':
                    x = ox + num();
                    y = oy + num();
                    p.moveTo(x, y);
                    sx = x;
                    sy = y;
                    break;
                case 'L':
                    x = ox + num();
                    y = oy + num();
                    p.lineTo(x, y);
                    break;
                case 'H':
                    x = ox + num();
                    p.lineTo(x, y);
                    break;
                case 'V':
                    y = (rel ? y : 0) + num();
                    p.lineTo(x, y);
                    break;
                case 'C': {
                    float x1 = ox + num(), y1 = oy + num(), x2 = ox + num(), y2 = oy + num();
                    x = ox + num();
                    y = oy + num();
                    p.cubicTo(x1, y1, x2, y2, x, y);
                    cx = x2;
                    cy = y2;
                    break;
                }
                case 'S': {
                    boolean smooth = "CcSs".indexOf(prev) >= 0;
                    float x1 = smooth ? 2 * x - cx : x, y1 = smooth ? 2 * y - cy : y;
                    float x2 = ox + num(), y2 = oy + num();
                    x = ox + num();
                    y = oy + num();
                    p.cubicTo(x1, y1, x2, y2, x, y);
                    cx = x2;
                    cy = y2;
                    break;
                }
                case 'Q': {
                    float x1 = ox + num(), y1 = oy + num();
                    x = ox + num();
                    y = oy + num();
                    p.quadTo(x1, y1, x, y);
                    cx = x1;
                    cy = y1;
                    break;
                }
                case 'T': {
                    boolean smooth = "QqTt".indexOf(prev) >= 0;
                    float x1 = smooth ? 2 * x - cx : x, y1 = smooth ? 2 * y - cy : y;
                    x = ox + num();
                    y = oy + num();
                    p.quadTo(x1, y1, x, y);
                    cx = x1;
                    cy = y1;
                    break;
                }
                case 'Z':
                    p.close();
                    x = sx;
                    y = sy;
                    break;
                default:
                    return; // unsupported command: stop rather than loop forever
            }
            prev = cmd;
        }
    }

    private void skip() {
        while (i < s.length()) {
            char c = s.charAt(i);
            if (c == ' ' || c == ',' || c == '\n' || c == '\t' || c == '\r') i++;
            else break;
        }
    }

    private float num() {
        skip();
        int start = i;
        if (i < s.length() && (s.charAt(i) == '-' || s.charAt(i) == '+')) i++;
        boolean dot = false;
        while (i < s.length()) {
            char c = s.charAt(i);
            if (c >= '0' && c <= '9') {
                i++;
            } else if (c == '.' && !dot) {
                dot = true;
                i++;
            } else if ((c == 'e' || c == 'E') && i > start) {
                i++;
                if (i < s.length() && (s.charAt(i) == '-' || s.charAt(i) == '+')) i++;
            } else {
                break;
            }
        }
        return Float.parseFloat(s.substring(start, i));
    }
}
