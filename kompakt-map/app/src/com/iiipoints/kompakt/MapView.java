package com.iiipoints.kompakt;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapShader;
import android.graphics.Canvas;
import android.graphics.DashPathEffect;
import android.graphics.Matrix;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.graphics.Shader;
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
import java.util.Set;

/**
 * The festival map (assets/map.json, built by tools/build_map.py). Geometry is drawn in map units;
 * labels are drawn by the app in screen space at a constant size (Mudita-style pills), placed so
 * they don't collide. Stage labels show the act playing now (starred if it's a favorite).
 * Icons appear only when zoomed in; categories can be hidden with the filter.
 */
final class MapView extends View {
    interface Listener {
        void onStage(String id);

        void onEmpty();
    }

    static final float ICON_ZOOM = 0.55f;   // screen px per map unit at which icons appear
    private static final int BLACK = 0xff000000, WHITE = 0xffffffff;

    private abstract static class Op {
        int lvl;
        String cat;

        abstract void draw(Canvas c);
    }

    static final class Label {
        String kind, id, text;
        float x, y, lx, ly, dir;
    }

    private final List<Op> ops = new ArrayList<>();
    final List<Label> labels = new ArrayList<>();
    private final Map<String, Typeface> fonts = new HashMap<>();
    private final Map<String, Paint> fills = new HashMap<>();
    private final Map<String, List<Object[]>> icons = new HashMap<>();
    private final RectF view = new RectF();
    private float scale = 1, offX, offY;
    private boolean placed;
    private float pendingX = Float.NaN, pendingY, pendingScale;
    private String selected;
    private Listener listener;
    private final GestureDetector gestures;
    private final ScaleGestureDetector scaler;

    Festival fest;
    Favorites favs;

    // you are here (map units); NaN = no fix
    float youX = Float.NaN, youY = Float.NaN, youAcc;
    private final Paint youFill = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint youRing = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint accRing = new Paint(Paint.ANTI_ALIAS_FLAG);

    void setYou(float x, float y, float acc) {
        youX = x;
        youY = y;
        youAcc = acc;
        invalidate();
    }

    boolean youOnMap() {
        return !Float.isNaN(youX) && view.contains(youX, youY);
    }
    Set<String> hiddenCats;

    // label paints
    private final Paint pillFill = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint pillLine = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint nameText = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint subText = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint smallText = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint halo = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint arrow = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final List<RectF> placedRects = new ArrayList<>();
    private final Map<String, RectF> stageHits = new HashMap<>();

    MapView(Context ctx) throws Exception {
        super(ctx);
        setBackgroundColor(WHITE);
        load(ctx);
        pillFill.setColor(WHITE);
        pillLine.setStyle(Paint.Style.STROKE);
        pillLine.setColor(BLACK);
        pillLine.setStrokeWidth(Ui.px(2.2f));
        nameText.setTypeface(Ui.bold);
        nameText.setTextSize(Ui.px(19));
        nameText.setTextAlign(Paint.Align.CENTER);
        subText.setTypeface(Ui.semibold);
        subText.setTextSize(Ui.px(13.5f));
        subText.setTextAlign(Paint.Align.CENTER);
        smallText.setTypeface(Ui.semibold);
        smallText.setTextSize(Ui.px(13));
        smallText.setTextAlign(Paint.Align.CENTER);
        halo.set(smallText);
        halo.setStyle(Paint.Style.STROKE);
        halo.setStrokeWidth(Ui.px(4));
        halo.setColor(WHITE);
        halo.setStrokeJoin(Paint.Join.ROUND);
        youFill.setColor(BLACK);
        youRing.setColor(WHITE);
        youRing.setStyle(Paint.Style.STROKE);
        youRing.setStrokeWidth(Ui.px(4));
        accRing.setColor(BLACK);
        accRing.setStyle(Paint.Style.STROKE);
        accRing.setStrokeWidth(Ui.px(1.5f));
        accRing.setPathEffect(new DashPathEffect(new float[]{Ui.px(5), Ui.px(4)}, 0));
        arrow.setColor(BLACK);
        arrow.setStrokeWidth(Ui.px(3.5f));
        arrow.setStrokeCap(Paint.Cap.ROUND);

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
                String hit = null;
                for (Map.Entry<String, RectF> en : stageHits.entrySet()) {
                    RectF r = new RectF(en.getValue());
                    r.inset(-Ui.px(8), -Ui.px(8));
                    if (r.contains(e.getX(), e.getY())) hit = en.getKey();
                }
                if (hit == null) {   // tap on a stage's drawing
                    float mx = (e.getX() - offX) / scale, my = (e.getY() - offY) / scale;
                    float best = 60;
                    for (Label l : labels) {
                        if (!"stage".equals(l.kind)) continue;
                        float d = (float) Math.hypot(l.x - mx, l.y - my);
                        if (d < best) {
                            best = d;
                            hit = l.id;
                        }
                    }
                }
                if (listener != null) {
                    if (hit != null) listener.onStage(hit);
                    else listener.onEmpty();
                }
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

    void select(String stageId) {
        selected = stageId;
        invalidate();
    }

    Label stageLabel(String id) {
        for (Label l : labels) if ("stage".equals(l.kind) && l.id.equals(id)) return l;
        return null;
    }

    // ------------------------------------------------------------------------------------ view

    private float minScale() {
        return Math.min(getWidth() / view.width(), getHeight() / view.height());
    }

    void fit() {
        if (getWidth() == 0) return;
        scale = minScale();
        clamp();
        invalidate();
    }

    void zoomBy(float f, float px, float py) {
        float ns = Math.max(minScale(), Math.min(scale * f, 2.4f));
        float k = ns / scale;
        offX = px - (px - offX) * k;
        offY = py - (py - offY) * k;
        scale = ns;
        clamp();
        invalidate();
    }

    /** Centre a map point; s <= 0 keeps the current zoom (at least the icon zoom). */
    void focus(float mx, float my, float s) {
        if (getWidth() == 0) {
            pendingX = mx;
            pendingY = my;
            pendingScale = s;
            return;
        }
        if (s > 0) scale = s;
        offX = getWidth() / 2f - mx * scale;
        offY = getHeight() / 2f - my * scale;
        clamp();
        invalidate();
    }

    private void clamp() {
        float w = view.width() * scale, h = view.height() * scale;
        float minX = getWidth() - view.right * scale, maxX = -view.left * scale;
        float minY = getHeight() - view.bottom * scale, maxY = -view.top * scale;
        offX = w <= getWidth() ? (getWidth() - w) / 2 - view.left * scale : Math.max(minX, Math.min(maxX, offX));
        offY = h <= getHeight() ? (getHeight() - h) / 2 - view.top * scale : Math.max(minY, Math.min(maxY, offY));
    }

    @Override
    protected void onSizeChanged(int w, int h, int ow, int oh) {
        if (!Float.isNaN(pendingX)) {
            float x = pendingX;
            pendingX = Float.NaN;
            focus(x, pendingY, pendingScale);
            placed = true;
        } else if (!placed) {
            focus(view.centerX(), view.centerY(), Math.max(ICON_ZOOM, w / 900f));   // middle of the grounds, icons visible
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

    // ------------------------------------------------------------------------------------ draw

    @Override
    protected void onDraw(Canvas c) {
        boolean detail = scale >= ICON_ZOOM;
        c.save();
        c.translate(offX, offY);
        c.scale(scale, scale);
        for (Op op : ops) {
            if (op.lvl > 0 && !detail) continue;
            if (op.cat != null && hiddenCats != null && hiddenCats.contains(op.cat)) continue;
            op.draw(c);
        }
        c.restore();
        drawLabels(c, detail);
        drawYou(c);
    }

    /** You-are-here: black dot in a white ring and a black outer ring; dashed circle = GPS accuracy. */
    private void drawYou(Canvas c) {
        if (Float.isNaN(youX)) return;
        float x = sx(youX), y = sy(youY);
        float acc = youAcc * scale;
        if (acc > Ui.px(14)) c.drawCircle(x, y, acc, accRing);
        c.drawCircle(x, y, Ui.px(11), youFill);
        c.drawCircle(x, y, Ui.px(7.5f), youRing);
        c.drawCircle(x, y, Ui.px(4), youFill);
    }

    private float sx(float x) {
        return offX + x * scale;
    }

    private float sy(float y) {
        return offY + y * scale;
    }

    private boolean free(RectF r) {
        for (RectF p : placedRects) if (RectF.intersects(p, r)) return false;
        return true;
    }

    private void drawLabels(Canvas c, boolean detail) {
        placedRects.clear();
        stageHits.clear();
        Festival.Clock clock = Festival.clock();
        // entrances first (always shown), then stages, then minor labels if there is room
        for (Label l : labels) if ("entrance".equals(l.kind)) drawEntrance(c, l);
        for (Label l : labels) if ("stage".equals(l.kind)) drawStage(c, l, clock);
        if (!detail) return;
        for (Label l : labels) {
            if ("attraction".equals(l.kind) || "place".equals(l.kind) || "zone".equals(l.kind)) {
                float x = sx(l.x), y = sy(l.y);
                Paint p = smallText;
                Paint.Align al = Paint.Align.CENTER;
                if ("place".equals(l.kind)) {
                    x += 20 * scale + Ui.px(4);
                    al = Paint.Align.LEFT;
                }
                p.setTextAlign(al);
                halo.setTextAlign(al);
                float w = p.measureText(l.text);
                float left = al == Paint.Align.LEFT ? x : x - w / 2;
                RectF r = new RectF(left, y - Ui.px(10), left + w, y + Ui.px(5));
                if (!free(r)) continue;
                placedRects.add(r);
                c.drawText(l.text, x, y + Ui.px(4), halo);
                c.drawText(l.text, x, y + Ui.px(4), p);
            }
        }
        smallText.setTextAlign(Paint.Align.CENTER);
        halo.setTextAlign(Paint.Align.CENTER);
    }

    private void drawStage(Canvas c, Label l, Festival.Clock clock) {
        String sub = null;
        boolean star = false;
        if (fest != null) {
            Festival.Stage st = fest.stage(l.id);
            if (st != null && clock.day >= 0) {
                Festival.Set now = clock.live ? st.now(clock.day, clock.t) : null;
                Festival.Set next = st.next(clock.day, clock.t);
                if (now != null) {
                    sub = now.artist;
                    star = favs != null && favs.has(now);
                } else if (next != null) {
                    sub = "Next " + Festival.shortTime(next.start) + " " + next.artist;
                    star = favs != null && favs.has(next);
                }
            }
        }
        boolean sel = l.id.equals(selected);
        if (scale < ICON_ZOOM && !sel) {   // zoomed out: names only
            sub = null;
            star = false;
        }
        float padX = Ui.px(12);
        String subShown = sub == null ? null : (star ? "★ " : "") + ellipsize(sub, subText, Ui.px(170));
        float w = Math.max(nameText.measureText(l.text), subShown == null ? 0 : subText.measureText(subShown)) + 2 * padX;
        float h = subShown == null ? Ui.px(32) : Ui.px(48);
        float x = sx(l.lx), y = sy(l.ly);
        RectF r = new RectF(x - w / 2, y - h / 2, x + w / 2, y + h / 2);
        // nudge away from labels already placed
        float[][] tries = {{0, 0}, {0, h * 0.8f}, {0, -h * 0.8f}, {w * 0.6f, 0}, {-w * 0.6f, 0}, {0, h * 1.6f}, {0, -h * 1.6f}};
        boolean found = false;
        for (float[] t : tries) {
            RectF q = new RectF(r);
            q.offset(t[0], t[1]);
            if (free(q)) {
                r = q;
                found = true;
                break;
            }
        }
        if (!found && !sel) {   // no room: keep it tappable, but don't draw over another label
            stageHits.put(l.id, r);
            return;
        }
        placedRects.add(r);
        stageHits.put(l.id, r);
        float rad = Ui.px(12);
        pillFill.setColor(sel ? BLACK : WHITE);
        c.drawRoundRect(r, rad, rad, pillFill);
        c.drawRoundRect(r, rad, rad, pillLine);
        int fg = sel ? WHITE : BLACK;
        nameText.setColor(fg);
        subText.setColor(fg);
        if (subShown == null) {
            c.drawText(l.text, r.centerX(), r.centerY() + Ui.px(6.5f), nameText);
        } else {
            c.drawText(l.text, r.centerX(), r.top + Ui.px(21), nameText);
            c.drawText(subShown, r.centerX(), r.top + Ui.px(39), subText);
        }
    }

    private static String ellipsize(String s, Paint p, float max) {
        if (p.measureText(s) <= max) return s;
        while (s.length() > 2 && p.measureText(s + "…") > max) s = s.substring(0, s.length() - 1);
        return s.trim() + "…";
    }

    private void drawEntrance(Canvas c, Label l) {
        double a = Math.toRadians(l.dir);
        float tx = sx(l.x), ty = sy(l.y);
        float back = Ui.px(46);
        float bx = (float) (tx - back * Math.cos(a)), by = (float) (ty - back * Math.sin(a));
        c.drawLine(bx, by, tx, ty, arrow);
        Path head = new Path();
        float hl = Ui.px(11);
        head.moveTo(tx, ty);
        head.lineTo((float) (tx - hl * Math.cos(a - 0.5)), (float) (ty - hl * Math.sin(a - 0.5)));
        head.lineTo((float) (tx - hl * Math.cos(a + 0.5)), (float) (ty - hl * Math.sin(a + 0.5)));
        head.close();
        arrow.setStyle(Paint.Style.FILL);
        c.drawPath(head, arrow);
        arrow.setStyle(Paint.Style.STROKE);
        float w = nameText.measureText(l.text) * 0.8f + Ui.px(22), h = Ui.px(30);
        float cx = (float) (bx - (w / 2 + Ui.px(2)) * Math.cos(a)), cy = (float) (by - (h / 2 + Ui.px(2)) * Math.sin(a));
        RectF r = new RectF(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2);
        placedRects.add(r);
        pillFill.setColor(WHITE);
        c.drawRoundRect(r, Ui.px(9), Ui.px(9), pillFill);
        pillLine.setStrokeWidth(Ui.px(3));
        c.drawRoundRect(r, Ui.px(9), Ui.px(9), pillLine);
        pillLine.setStrokeWidth(Ui.px(2.2f));
        float size = nameText.getTextSize();
        nameText.setTextSize(size * 0.8f);
        nameText.setColor(BLACK);
        c.drawText(l.text, r.centerX(), r.centerY() + Ui.px(5), nameText);
        nameText.setTextSize(size);
    }

    // ------------------------------------------------------------------------------------ load

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
        // map text uses the system font too (map.json's font names only matter for the SVG previews)
        fonts.put("b6", Ui.semibold);
        fonts.put("b7", Ui.bold);
        JSONObject pats = doc.getJSONObject("patterns");
        for (Iterator<String> it = pats.keys(); it.hasNext(); ) {
            String k = it.next();
            fills.put(k, patternPaint(pats.getJSONObject(k)));
        }
        fills.put("w", solid(WHITE));
        fills.put("b", solid(BLACK));
        JSONArray arr = doc.getJSONArray("ops");
        for (int i = 0; i < arr.length(); i++) {
            JSONObject o = arr.getJSONObject(i);
            Op op = compile(o);
            op.lvl = o.optInt("lvl", 0);
            op.cat = o.optString("cat", null);
            ops.add(op);
        }
        JSONArray ls = doc.getJSONArray("labels");
        for (int i = 0; i < ls.length(); i++) {
            JSONObject o = ls.getJSONObject(i);
            Label l = new Label();
            l.kind = o.getString("kind");
            l.id = o.getString("id");
            l.text = o.getString("t");
            l.x = (float) o.getDouble("x");
            l.y = (float) o.getDouble("y");
            l.lx = (float) o.optDouble("lx", l.x);
            l.ly = (float) o.optDouble("ly", l.y);
            l.dir = (float) o.optDouble("dir", 0);
            labels.add(l);
        }
    }

    private static Paint solid(int color) {
        Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        p.setStyle(Paint.Style.FILL);
        p.setColor(color);
        return p;
    }

    /** Fill patterns as tiled bitmaps in map units (4 px per unit), so they scale with the map. */
    private static Paint patternPaint(JSONObject p) throws Exception {
        final int Q = 4;
        String kind = p.getString("kind");
        float g = (float) p.getDouble("gap");
        boolean stagger = p.optBoolean("stagger", false) || kind.equals("tufts");
        int w = Math.round(g * Q), h = Math.round((stagger ? 2 * g : g) * Q);
        Bitmap bm = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888);
        Canvas c = new Canvas(bm);
        c.drawColor(WHITE);
        Paint ink = solid(BLACK);
        Matrix m = new Matrix();
        m.setScale(1f / Q, 1f / Q);
        if (kind.equals("lines")) {
            c.drawRect(0, 0, (float) p.getDouble("width") * Q, h, ink);
            m.postRotate((float) p.getDouble("angle") - 90);
        } else if (kind.equals("dots")) {
            float r = (float) p.getDouble("r") * Q;
            c.drawCircle(w / 2f, g * Q / 2f, r, ink);
            if (stagger) {
                c.drawCircle(0, g * 1.5f * Q, r, ink);
                c.drawCircle(w, g * 1.5f * Q, r, ink);
            }
        } else if (kind.equals("tufts")) {
            Paint s = new Paint(Paint.ANTI_ALIAS_FLAG);
            s.setStyle(Paint.Style.STROKE);
            s.setStrokeWidth(1.1f * Q);
            s.setStrokeCap(Paint.Cap.ROUND);
            float[][] at = {{g / 2, g / 2}, {0, g * 1.5f}, {g, g * 1.5f}};
            for (float[] t : at) {
                float x = t[0] * Q, y = t[1] * Q;
                c.drawLine(x - 3 * Q, y + 3 * Q, x - 1 * Q, y - 2 * Q, s);
                c.drawLine(x, y + 3 * Q, x, y - 3 * Q, s);
                c.drawLine(x + 3 * Q, y + 3 * Q, x + 1 * Q, y - 2 * Q, s);
            }
        }
        BitmapShader sh = new BitmapShader(bm, Shader.TileMode.REPEAT, Shader.TileMode.REPEAT);
        sh.setLocalMatrix(m);
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
        paint.setShader(sh);
        return paint;
    }

    private static int col(String c) {
        return "w".equals(c) ? WHITE : BLACK;
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

    private Op compile(final JSONObject o) throws Exception {
        switch (o.getString("o")) {
            case "poly": {
                final Path path = polyline(o.getJSONArray("p"), true);
                final Paint fp = fills.get(o.getString("f"));
                final Paint sp = o.getDouble("s") > 0 ? stroke(o.getDouble("s"), o.getString("c")) : null;
                return new Op() {
                    void draw(Canvas c) {
                        if (fp != null) c.drawPath(path, fp);
                        if (sp != null) c.drawPath(path, sp);
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
            case "text": {
                final String t = o.getString("t");
                final float x = (float) o.getDouble("x"), y = (float) o.getDouble("y"), rot = (float) o.optDouble("r", 0);
                final Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
                p.setTypeface(fonts.get(o.getString("font")));
                p.setTextSize((float) o.getDouble("sz"));
                p.setColor(col(o.getString("c")));
                String a = o.getString("a");
                p.setTextAlign("l".equals(a) ? Paint.Align.LEFT : "r".equals(a) ? Paint.Align.RIGHT : Paint.Align.CENTER);
                return new Op() {
                    void draw(Canvas c) {
                        c.save();
                        if (rot != 0) c.rotate(rot, x, y);
                        c.drawText(t, x, y, p);
                        c.restore();
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

    /** White disc, black glyph. GA: solid ring; GA+: double ring; VIP: dashed ring (+ inner ring for concierge). */
    Op iconOp(String kind, final float x, final float y, final float r, final String style) {
        final List<Object[]> parts = icons.get(kind);
        final boolean vip = style.equals("vip") || style.equals("vipring");
        final Paint disc = solid(WHITE);
        final Paint ring = stroke(vip ? 2.5 : 3.5, "b");
        if (vip) ring.setPathEffect(new DashPathEffect(new float[]{5, 3.5f}, 0));
        final Paint inner = stroke(1.6, "b");
        final Paint fg = solid(BLACK), bg = solid(WHITE);
        final Paint text = new Paint(Paint.ANTI_ALIAS_FLAG);
        text.setTypeface(fonts.get("b7"));
        text.setTextAlign(Paint.Align.CENTER);
        final float s = r / 12f * 0.82f;
        return new Op() {
            void draw(Canvas c) {
                c.drawCircle(x, y, r + 3, disc);
                c.drawCircle(x, y, r, ring);
                if (style.equals("gaplus") || style.equals("vipring")) c.drawCircle(x, y, r - 5, inner);
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
                        text.setColor((Boolean) part[3] ? WHITE : BLACK);
                        c.drawText((String) part[1], 12, 12 + size * 0.36f, text);
                    }
                }
                c.restore();
            }
        };
    }

    /** One legend pictogram as a standalone view (Legend / Filter screens). */
    View iconView(final String kind, final String style, final int sizePx) {
        final Op op = iconOp(kind, sizePx / 2f, sizePx / 2f, sizePx / 2f - 4, style);
        return new View(getContext()) {
            @Override
            protected void onDraw(Canvas c) {
                op.draw(c);
            }
        };
    }
}
