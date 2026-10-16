package com.iiipoints.kompakt;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.DashPathEffect;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.graphics.Typeface;
import android.view.GestureDetector;
import android.view.MotionEvent;
import android.view.ScaleGestureDetector;
import android.view.View;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

/**
 * Renders the black & white festival map from assets/map.json (a display list shared with
 * tools/build_map.py, which also writes the reference SVG). Pure black on white, no animation:
 * pan by dragging, zoom with pinch, double tap or the +/- buttons; tap a stage tag to select it.
 */
final class MapView extends View {
    interface Listener {
        void onHit(String id);
    }

    private static final int BLACK = 0xff000000, WHITE = 0xffffffff;

    private abstract static class Op {
        abstract void draw(Canvas c);
    }

    static final class Hit {
        final String id;
        final RectF r;

        Hit(String id, RectF r) {
            this.id = id;
            this.r = r;
        }
    }

    private final List<Op> ops = new ArrayList<>();
    final List<Hit> hits = new ArrayList<>();
    private final Map<String, Typeface> fonts = new HashMap<>();
    private final Map<String, List<Object[]>> icons = new HashMap<>();
    private final RectF view = new RectF();
    private float scale = 1, offX, offY;
    private boolean placed;
    private String selected;
    private Listener listener;
    private final Paint selPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint hatchPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final GestureDetector gestures;
    private final ScaleGestureDetector scaler;
    private float pendingFocusX = Float.NaN, pendingFocusY, pendingScale;

    MapView(Context ctx) throws Exception {
        super(ctx);
        setBackgroundColor(WHITE);
        selPaint.setStyle(Paint.Style.STROKE);
        selPaint.setColor(BLACK);
        selPaint.setStrokeWidth(7);
        hatchPaint.setColor(BLACK);
        hatchPaint.setStrokeWidth(2);
        load(ctx);
        gestures = new GestureDetector(ctx, new GestureDetector.SimpleOnGestureListener() {
            @Override
            public boolean onDown(MotionEvent e) {
                return true;
            }

            @Override
            public boolean onScroll(MotionEvent a, MotionEvent b, float dx, float dy) {
                offX -= dx;
                offY -= dy;
                clamp();
                invalidate();
                return true;
            }

            @Override
            public boolean onSingleTapConfirmed(MotionEvent e) {
                float mx = (e.getX() - offX) / scale, my = (e.getY() - offY) / scale;
                float slop = 14 / scale;
                Hit best = null;
                for (Hit h : hits) {
                    if (mx >= h.r.left - slop && mx <= h.r.right + slop && my >= h.r.top - slop && my <= h.r.bottom + slop) {
                        if (best == null || h.r.width() * h.r.height() < best.r.width() * best.r.height()) best = h;
                    }
                }
                if (best != null && listener != null) listener.onHit(best.id);
                return true;
            }

            @Override
            public boolean onDoubleTap(MotionEvent e) {
                zoomBy(1.6f, e.getX(), e.getY());
                return true;
            }
        });
        gestures.setIsLongpressEnabled(false);
        scaler = new ScaleGestureDetector(ctx, new ScaleGestureDetector.SimpleOnScaleGestureListener() {
            @Override
            public boolean onScale(ScaleGestureDetector d) {
                zoomBy(d.getScaleFactor(), d.getFocusX(), d.getFocusY());
                return true;
            }
        });
    }

    void setListener(Listener l) {
        listener = l;
    }

    void select(String id) {
        selected = id;
        invalidate();
    }

    // ---------------------------------------------------------------------------------------- view

    void fit() {
        if (getWidth() == 0) return;
        scale = Math.min(getWidth() / view.width(), getHeight() / view.height());
        offX = (getWidth() - view.width() * scale) / 2 - view.left * scale;
        offY = (getHeight() - view.height() * scale) / 2 - view.top * scale;
        invalidate();
    }

    void zoomBy(float f, float px, float py) {
        float min = Math.min(getWidth() / view.width(), getHeight() / view.height());
        float ns = Math.max(min, Math.min(scale * f, 2.2f));
        float k = ns / scale;
        offX = px - (px - offX) * k;
        offY = py - (py - offY) * k;
        scale = ns;
        clamp();
        invalidate();
    }

    /** Centre the map on a map-space point at the given scale (applied once laid out). */
    void focus(float mx, float my, float s) {
        if (getWidth() == 0) {
            pendingFocusX = mx;
            pendingFocusY = my;
            pendingScale = s;
            return;
        }
        scale = s;
        offX = getWidth() / 2f - mx * s;
        offY = getHeight() / 2f - my * s;
        clamp();
        invalidate();
    }

    Hit hit(String id) {
        for (Hit h : hits) if (h.id.equals(id)) return h;
        return null;
    }

    private void clamp() {
        float w = view.width() * scale, h = view.height() * scale;
        float minX = getWidth() - (view.right * scale), maxX = -view.left * scale;
        float minY = getHeight() - (view.bottom * scale), maxY = -view.top * scale;
        offX = w <= getWidth() ? (getWidth() - w) / 2 - view.left * scale : Math.max(minX, Math.min(maxX, offX));
        offY = h <= getHeight() ? (getHeight() - h) / 2 - view.top * scale : Math.max(minY, Math.min(maxY, offY));
    }

    @Override
    protected void onSizeChanged(int w, int h, int ow, int oh) {
        if (!Float.isNaN(pendingFocusX)) {
            float x = pendingFocusX;
            pendingFocusX = Float.NaN;
            focus(x, pendingFocusY, pendingScale);
            placed = true;
        } else if (!placed) {
            // open on the middle of the grounds, readable size
            focus(860, 900, Math.max(0.55f, w / 900f));
            placed = true;
        } else {
            clamp();
        }
    }

    @Override
    public boolean onTouchEvent(MotionEvent e) {
        scaler.onTouchEvent(e);
        if (!scaler.isInProgress()) gestures.onTouchEvent(e);
        return true;
    }

    @Override
    protected void onDraw(Canvas c) {
        c.save();
        c.translate(offX, offY);
        c.scale(scale, scale);
        for (Op op : ops) op.draw(c);
        if (selected != null) {
            Hit h = hit(selected);
            if (h != null) {
                RectF r = new RectF(h.r);
                r.inset(-9, -9);
                c.drawRoundRect(r, 8, 8, selPaint);
            }
        }
        c.restore();
    }

    // ---------------------------------------------------------------------------------------- load

    private void load(Context ctx) throws Exception {
        JSONObject iconDoc = new JSONObject(Festival.readAsset(ctx, "icons.json"));
        for (Iterator<String> it = iconDoc.keys(); it.hasNext(); ) {
            String k = it.next();
            JSONArray arr = iconDoc.getJSONArray(k);
            List<Object[]> list = new ArrayList<>();
            for (int i = 0; i < arr.length(); i++) {
                JSONArray o = arr.getJSONArray(i);
                String kind = o.getString(0);
                boolean bg = "bg".equals(o.optString(o.length() - 1));
                if (kind.equals("p")) list.add(new Object[]{"p", SvgPath.parse(o.getString(1)), bg});
                else if (kind.equals("c")) list.add(new Object[]{"c", (float) o.getDouble(1), (float) o.getDouble(2), (float) o.getDouble(3), bg});
                else if (kind.equals("t")) list.add(new Object[]{"t", o.getString(1), (float) o.getDouble(2), bg});
            }
            icons.put(k, list);
        }

        JSONObject doc = new JSONObject(Festival.readAsset(ctx, "map.json"));
        JSONArray v = doc.getJSONArray("view");
        view.set((float) v.getDouble(0), (float) v.getDouble(1), (float) (v.getDouble(0) + v.getDouble(2)),
                (float) (v.getDouble(1) + v.getDouble(3)));
        JSONObject f = doc.getJSONObject("fonts");
        for (Iterator<String> it = f.keys(); it.hasNext(); ) {
            String k = it.next();
            fonts.put(k, Typeface.createFromAsset(ctx.getAssets(), "fonts/" + f.getString(k)));
        }
        JSONArray arr = doc.getJSONArray("ops");
        for (int i = 0; i < arr.length(); i++) ops.add(compile(arr.getJSONObject(i)));
        JSONArray h = doc.getJSONArray("hits");
        for (int i = 0; i < h.length(); i++) {
            JSONObject o = h.getJSONObject(i);
            float x = (float) o.getDouble("x"), y = (float) o.getDouble("y");
            hits.add(new Hit(o.getString("id"), new RectF(x, y, x + (float) o.getDouble("w"), y + (float) o.getDouble("h"))));
        }
    }

    private static int col(String c) {
        return "w".equals(c) ? WHITE : BLACK;
    }

    private static Paint fill(String f) {
        Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        p.setStyle(Paint.Style.FILL);
        p.setColor(col(f));
        return p;
    }

    private static Paint stroke(double w, String c) {
        Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        p.setStyle(Paint.Style.STROKE);
        p.setStrokeWidth((float) w);
        p.setColor(col(c));
        p.setStrokeJoin(Paint.Join.ROUND);
        p.setStrokeCap(Paint.Cap.ROUND);
        return p;
    }

    private static Path polyline(JSONArray p, boolean close) throws Exception {
        Path path = new Path();
        for (int i = 0; i < p.length(); i += 2) {
            float x = (float) p.getDouble(i), y = (float) p.getDouble(i + 1);
            if (i == 0) path.moveTo(x, y);
            else path.lineTo(x, y);
        }
        if (close) path.close();
        return path;
    }

    /** Fill a shape with 45 degree hatching (black lines on white). */
    private void hatch(Canvas c, Path path) {
        RectF b = new RectF();
        path.computeBounds(b, true);
        c.save();
        c.clipPath(path);
        c.drawColor(WHITE);
        float d = b.width() + b.height();
        for (float k = -b.height(); k < b.width(); k += 8) {
            c.drawLine(b.left + k, b.bottom, b.left + k + d, b.bottom - d, hatchPaint);
        }
        c.restore();
    }

    private Op compile(final JSONObject o) throws Exception {
        String kind = o.getString("o");
        switch (kind) {
            case "poly": {
                final Path path = polyline(o.getJSONArray("p"), true);
                final String f = o.getString("f");
                final Paint fp = "n".equals(f) || "h".equals(f) ? null : fill(f);
                final boolean hatched = "h".equals(f);
                final Paint sp = o.getDouble("s") > 0 ? stroke(o.getDouble("s"), o.getString("c")) : null;
                return new Op() {
                    void draw(Canvas c) {
                        if (hatched) hatch(c, path);
                        if (fp != null) c.drawPath(path, fp);
                        if (sp != null) c.drawPath(path, sp);
                    }
                };
            }
            case "path": {
                final Path path = SvgPath.parse(o.getString("d"));
                final Paint fp = fill(o.getString("f"));
                return new Op() {
                    void draw(Canvas c) {
                        c.drawPath(path, fp);
                    }
                };
            }
            case "line": {
                final Path path = polyline(o.getJSONArray("p"), false);
                final Paint sp = stroke(o.getDouble("s"), o.getString("c"));
                JSONArray d = o.optJSONArray("d");
                if (d != null) sp.setPathEffect(new DashPathEffect(new float[]{(float) d.getDouble(0), (float) d.getDouble(1)}, 0));
                return new Op() {
                    void draw(Canvas c) {
                        c.drawPath(path, sp);
                    }
                };
            }
            case "circle": {
                final float x = (float) o.getDouble("x"), y = (float) o.getDouble("y"), r = (float) o.getDouble("r");
                final Paint fp = "n".equals(o.getString("f")) ? null : fill(o.getString("f"));
                final Paint sp = o.getDouble("s") > 0 ? stroke(o.getDouble("s"), o.getString("c")) : null;
                return new Op() {
                    void draw(Canvas c) {
                        if (fp != null) c.drawCircle(x, y, r, fp);
                        if (sp != null) c.drawCircle(x, y, r, sp);
                    }
                };
            }
            case "ellipse": {
                float x = (float) o.getDouble("x"), y = (float) o.getDouble("y");
                float rx = (float) o.getDouble("rx"), ry = (float) o.getDouble("ry");
                final RectF r = new RectF(x - rx, y - ry, x + rx, y + ry);
                final Paint sp = stroke(o.getDouble("s"), o.getString("c"));
                JSONArray d = o.optJSONArray("d");
                if (d != null) sp.setPathEffect(new DashPathEffect(new float[]{(float) d.getDouble(0), (float) d.getDouble(1)}, 0));
                return new Op() {
                    void draw(Canvas c) {
                        c.drawOval(r, sp);
                    }
                };
            }
            case "rect": {
                final float x = (float) o.getDouble("x"), y = (float) o.getDouble("y");
                final RectF r = new RectF(x, y, x + (float) o.getDouble("w"), y + (float) o.getDouble("h"));
                final float rx = (float) o.optDouble("rx", 0), rot = (float) o.optDouble("r", 0);
                final Paint fp = "n".equals(o.getString("f")) ? null : fill(o.getString("f"));
                final Paint sp = o.getDouble("s") > 0 ? stroke(o.getDouble("s"), o.getString("c")) : null;
                if (sp != null) sp.setStrokeJoin(Paint.Join.MITER);
                return new Op() {
                    void draw(Canvas c) {
                        if (rot != 0) {
                            c.save();
                            c.rotate(rot, r.centerX(), r.centerY());
                        }
                        if (fp != null) c.drawRoundRect(r, rx, rx, fp);
                        if (sp != null) c.drawRoundRect(r, rx, rx, sp);
                        if (rot != 0) c.restore();
                    }
                };
            }
            case "text": {
                final String t = o.getString("t");
                final float x = (float) o.getDouble("x"), y = (float) o.getDouble("y");
                final float rot = (float) o.optDouble("r", 0);
                final Paint p = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.SUBPIXEL_TEXT_FLAG);
                p.setTypeface(fonts.get(o.getString("font")));
                p.setTextSize((float) o.getDouble("sz"));
                p.setColor(col(o.getString("c")));
                String a = o.getString("a");
                p.setTextAlign("l".equals(a) ? Paint.Align.LEFT : "r".equals(a) ? Paint.Align.RIGHT : Paint.Align.CENTER);
                double fit = o.optDouble("fit", 0);
                if (fit > 0) {
                    float w = p.measureText(t);
                    if (w > fit) p.setTextScaleX((float) (fit / w));
                }
                return new Op() {
                    void draw(Canvas c) {
                        if (rot != 0) {
                            c.save();
                            c.rotate(rot, x, y);
                            c.drawText(t, x, y, p);
                            c.restore();
                        } else {
                            c.drawText(t, x, y, p);
                        }
                    }
                };
            }
            case "icon":
                return iconOp(o.getString("k"), (float) o.getDouble("x"), (float) o.getDouble("y"),
                        (float) o.getDouble("r"), o.getString("st"));
            default:
                return new Op() {
                    void draw(Canvas c) {
                    }
                };
        }
    }

    /** Legend pictogram in a disc. ga / gaplus: black disc, white glyph. vip / vipring: white disc, black ring and glyph. */
    Op iconOp(String kind, final float x, final float y, final float r, final String style) {
        final List<Object[]> parts = icons.get(kind);
        final boolean dark = style.equals("ga") || style.equals("gaplus");
        final Paint disc = fill(dark ? "b" : "w");
        final Paint ring = stroke(3, "b");
        final Paint inner = stroke(1.6, dark ? "w" : "b");
        final Paint fg = fill(dark ? "w" : "b");
        final Paint bg = fill(dark ? "b" : "w");
        final Paint text = new Paint(Paint.ANTI_ALIAS_FLAG);
        text.setTypeface(fonts.get("bc8"));
        text.setTextAlign(Paint.Align.CENTER);
        final float s = r / 12f * 0.82f;
        return new Op() {
            void draw(Canvas c) {
                c.drawCircle(x, y, r, disc);
                if (!dark) c.drawCircle(x, y, r, ring);
                if (style.equals("gaplus")) c.drawCircle(x, y, r - 4, inner);
                if (style.equals("vipring")) c.drawCircle(x, y, r - 5.5f, inner);
                if (parts == null) return;
                c.save();
                c.translate(x - 12 * s, y - 12 * s);
                c.scale(s, s);
                for (Object[] part : parts) {
                    String k = (String) part[0];
                    if (k.equals("p")) {
                        c.drawPath((Path) part[1], (Boolean) part[2] ? bg : fg);
                    } else if (k.equals("c")) {
                        c.drawCircle((Float) part[1], (Float) part[2], (Float) part[3], (Boolean) part[4] ? bg : fg);
                    } else {
                        float size = (Float) part[2];
                        text.setTextSize(size);
                        text.setColor((Boolean) part[3] ? bg.getColor() : fg.getColor());
                        c.drawText((String) part[1], 12, 12 + size * 0.36f, text);
                    }
                }
                c.restore();
            }
        };
    }

    /** Draws one legend pictogram outside the map (used by the Legend screen). */
    View iconView(final String kind, final String style, final int sizePx) {
        final Op op = iconOp(kind, sizePx / 2f, sizePx / 2f, sizePx / 2f - 2, style);
        View v = new View(getContext()) {
            @Override
            protected void onDraw(Canvas c) {
                op.draw(c);
            }
        };
        return v;
    }
}
