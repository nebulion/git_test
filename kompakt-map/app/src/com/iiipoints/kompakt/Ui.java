package com.iiipoints.kompakt;

import android.app.Activity;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.StateListDrawable;
import android.text.TextUtils;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/**
 * All app styling lives here, kept deliberately simple so it can be aligned with Mudita Mindful Design
 * (MMD, docs on zeroheight; Android library com.mudita:MMD). Current choices:
 *   colour   pure black on white, no greys (MMD's E Ink colour scheme is black/white only)
 *   type     system sans-serif; sizes in "design px" of the 480 x 800 screen (MMD scale: 14-28 sp)
 *   shapes   9 px corners on buttons and segmented controls, 12-14 px on cards (MMD: 12 / 9 / 6 dp)
 *   states   pressed = inverted; no ripples, shadows or animation
 */
final class Ui {
    static final int INK = 0xff000000, PAPER = 0xffffffff;
    static Typeface regular, medium, semibold, bold, cond, condBold;
    private static float k = 1;

    static void init(Activity a) {
        k = a.getResources().getDisplayMetrics().widthPixels / 480f;
        // system font
        regular = Typeface.create("sans-serif", Typeface.NORMAL);
        medium = Typeface.create("sans-serif-medium", Typeface.NORMAL);
        semibold = medium;
        bold = Typeface.create("sans-serif", Typeface.BOLD);
        cond = bold;
        condBold = bold;
    }

    static int px(float design) {
        return Math.round(design * k);
    }

    static TextView text(Context c, String s, Typeface tf, float size) {
        TextView t = new TextView(c);
        t.setText(s);
        t.setTypeface(tf);
        t.setTextSize(TypedValue.COMPLEX_UNIT_PX, px(size));
        t.setTextColor(INK);
        t.setIncludeFontPadding(false);
        t.setLineSpacing(0, 1.12f);
        return t;
    }

    static LinearLayout column(Context c) {
        LinearLayout l = new LinearLayout(c);
        l.setOrientation(LinearLayout.VERTICAL);
        l.setBackgroundColor(PAPER);
        return l;
    }

    static LinearLayout row(Context c) {
        LinearLayout l = new LinearLayout(c);
        l.setOrientation(LinearLayout.HORIZONTAL);
        l.setGravity(Gravity.CENTER_VERTICAL);
        return l;
    }

    static ScrollView scroll(Context c, View child) {
        ScrollView s = new ScrollView(c);
        s.setOverScrollMode(View.OVER_SCROLL_NEVER);
        s.setVerticalFadingEdgeEnabled(false);
        s.setVerticalScrollBarEnabled(true);
        s.addView(child);
        return s;
    }

    static View rule(Context c, float thick) {
        View v = new View(c);
        v.setBackgroundColor(INK);
        v.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, Math.max(1, px(thick))));
        return v;
    }

    /** Pressed state = inverted block, the e-ink equivalent of a ripple. */
    static StateListDrawable pressable(int base) {
        StateListDrawable d = new StateListDrawable();
        GradientDrawable on = new GradientDrawable();
        on.setColor(INK);
        GradientDrawable off = new GradientDrawable();
        off.setColor(base);
        d.addState(new int[]{android.R.attr.state_pressed}, on);
        d.addState(new int[]{}, off);
        d.setExitFadeDuration(0);
        d.setEnterFadeDuration(0);
        return d;
    }

    static GradientDrawable outline(float radius, int fillColor, float stroke) {
        GradientDrawable g = new GradientDrawable();
        g.setColor(fillColor);
        g.setCornerRadius(px(radius));
        g.setStroke(Math.max(1, px(stroke)), INK);
        return g;
    }

    /** Header bar: back chevron, title, optional text action on the right. */
    static LinearLayout bar(Context c, String title, String action, View.OnClickListener back, View.OnClickListener onAction) {
        LinearLayout bar = row(c);
        bar.setPadding(px(6), 0, px(10), 0);
        bar.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, px(64)));
        if (back != null) {
            Glyph chev = new Glyph(c, Glyph.BACK);
            chev.setLayoutParams(new LinearLayout.LayoutParams(px(52), px(52)));
            chev.setOnClickListener(back);
            chev.setBackground(pressable(PAPER));
            bar.addView(chev);
        } else {
            bar.addView(spacer(c, px(18)));
        }
        TextView t = text(c, title, bold, 30);
        t.setSingleLine(true);
        t.setEllipsize(TextUtils.TruncateAt.END);
        bar.addView(t, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        if (action != null) {
            TextView a = text(c, action, semibold, 21);
            a.setPadding(px(12), px(14), px(12), px(14));
            if (onAction != null) {
                a.setOnClickListener(onAction);
                a.setBackground(outline(22, PAPER, 2));
                a.setPadding(px(16), px(9), px(16), px(9));
            }
            bar.addView(a);
        }
        return bar;
    }

    static View spacer(Context c, int w) {
        View v = new View(c);
        v.setLayoutParams(new LinearLayout.LayoutParams(w, 1));
        return v;
    }

    /** Pill button with inverted pressed state. */
    static TextView button(Context c, String label, float textSize, View.OnClickListener l) {
        final TextView b = text(c, label, bold, textSize);
        b.setGravity(Gravity.CENTER);
        StateListDrawable d = new StateListDrawable();
        d.addState(new int[]{android.R.attr.state_pressed}, outline(9, INK, 2));
        d.addState(new int[]{}, outline(9, PAPER, 2));
        d.setEnterFadeDuration(0);
        d.setExitFadeDuration(0);
        b.setBackground(d);
        b.setOnClickListener(l);
        b.setOnTouchListener(new View.OnTouchListener() {
            public boolean onTouch(View v, android.view.MotionEvent e) {
                int a = e.getActionMasked();
                b.setTextColor(a == android.view.MotionEvent.ACTION_DOWN ? PAPER : INK);
                if (a == android.view.MotionEvent.ACTION_UP || a == android.view.MotionEvent.ACTION_CANCEL) b.setTextColor(INK);
                return false;
            }
        });
        return b;
    }

    /** Small vector glyphs drawn with paths (no image assets, crisp at any density). */
    static final class Glyph extends View {
        static final int BACK = 0, CHEVRON = 1, LOCATE = 2;
        private final int kind;
        boolean on;
        private final Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        int color = INK;

        Glyph(Context c, int kind) {
            super(c);
            this.kind = kind;
            p.setStyle(Paint.Style.STROKE);
            p.setStrokeCap(Paint.Cap.SQUARE);
            p.setStrokeJoin(Paint.Join.MITER);
        }

        @Override
        protected void onDraw(Canvas c) {
            float w = getWidth(), h = getHeight();
            p.setColor(isPressed() ? PAPER : color);
            p.setStrokeWidth(px(3.2f));
            Path path = new Path();
            if (kind == LOCATE) {   // crosshair: ring, centre dot, four ticks
                float r = Math.min(w, h) * 0.22f, t = Math.min(w, h) * 0.12f;
                p.setStyle(Paint.Style.STROKE);
                c.drawCircle(w / 2, h / 2, r, p);
                c.drawLine(w / 2, h / 2 - r - t, w / 2, h / 2 - r + px(2), p);
                c.drawLine(w / 2, h / 2 + r - px(2), w / 2, h / 2 + r + t, p);
                c.drawLine(w / 2 - r - t, h / 2, w / 2 - r + px(2), h / 2, p);
                c.drawLine(w / 2 + r - px(2), h / 2, w / 2 + r + t, h / 2, p);
                p.setStyle(Paint.Style.FILL);
                if (on) c.drawCircle(w / 2, h / 2, r * 0.45f, p);
                p.setStyle(Paint.Style.STROKE);
                return;
            }
            if (kind == BACK) {
                float s = Math.min(w, h) * 0.2f;
                path.moveTo(w / 2 + s * 0.6f, h / 2 - s * 1.6f);
                path.lineTo(w / 2 - s, h / 2);
                path.lineTo(w / 2 + s * 0.6f, h / 2 + s * 1.6f);
            } else {
                float s = Math.min(w, h) * 0.28f;
                path.moveTo(w / 2 - s * 0.5f, h / 2 - s);
                path.lineTo(w / 2 + s * 0.5f, h / 2);
                path.lineTo(w / 2 - s * 0.5f, h / 2 + s);
            }
            c.drawPath(path, p);
        }

        @Override
        protected void drawableStateChanged() {
            super.drawableStateChanged();
            invalidate();
        }
    }

    /** A list row: title, optional subtitle, chevron; whole row inverts while pressed. */
    static LinearLayout listRow(Context c, String title, String sub, float titleSize, View.OnClickListener l) {
        final LinearLayout r = row(c);
        r.setPadding(px(24), px(14), px(18), px(14));
        r.setMinimumHeight(px(76));
        LinearLayout texts = column(c);
        texts.setBackgroundColor(0);
        final TextView t = text(c, title, semibold, titleSize);
        texts.addView(t);
        final TextView s = sub == null ? null : text(c, sub, medium, 18);
        if (s != null) {
            s.setPadding(0, px(5), 0, 0);
            texts.addView(s);
        }
        r.addView(texts, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        final Glyph g = new Glyph(c, Glyph.CHEVRON);
        g.setDuplicateParentStateEnabled(true);
        r.addView(g, new LinearLayout.LayoutParams(px(30), px(30)));
        r.setBackground(pressable(PAPER));
        r.setOnClickListener(l);
        r.setOnTouchListener(new View.OnTouchListener() {
            public boolean onTouch(View v, android.view.MotionEvent e) {
                int a = e.getActionMasked();
                boolean down = a == android.view.MotionEvent.ACTION_DOWN;
                if (down || a == android.view.MotionEvent.ACTION_UP || a == android.view.MotionEvent.ACTION_CANCEL) {
                    int col = down ? PAPER : INK;
                    t.setTextColor(col);
                    if (s != null) s.setTextColor(col);
                }
                return false;
            }
        });
        return r;
    }

    /** Star toggle drawn as a path: outline when off, filled when on. */
    static final class Star extends View {
        boolean on;
        private final Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);

        Star(Context c, boolean on) {
            super(c);
            this.on = on;
            p.setColor(INK);
            p.setStrokeJoin(Paint.Join.ROUND);
        }

        @Override
        protected void onDraw(Canvas c) {
            float cx = getWidth() / 2f, cy = getHeight() / 2f + px(1), R = Math.min(getWidth(), getHeight()) * 0.36f, r = R * 0.45f;
            Path path = new Path();
            for (int i = 0; i < 10; i++) {
                double a = -Math.PI / 2 + i * Math.PI / 5;
                float rr = i % 2 == 0 ? R : r;
                float x = (float) (cx + rr * Math.cos(a)), y = (float) (cy + rr * Math.sin(a));
                if (i == 0) path.moveTo(x, y);
                else path.lineTo(x, y);
            }
            path.close();
            p.setStyle(on ? Paint.Style.FILL_AND_STROKE : Paint.Style.STROKE);
            p.setStrokeWidth(px(2.2f));
            c.drawPath(path, p);
        }
    }

    /** Segmented control (Mudita pill toggle). Calls back with the chosen index. */
    interface OnPick {
        void pick(int i);
    }

    static LinearLayout segmented(Context c, String[] items, int sel, final OnPick cb) {
        final LinearLayout seg = row(c);
        seg.setBackground(outline(9, PAPER, 2));
        final TextView[] tabs = new TextView[items.length];
        for (int i = 0; i < items.length; i++) {
            final int idx = i;
            TextView t = text(c, items[i], bold, 20);
            t.setGravity(Gravity.CENTER);
            t.setOnClickListener(new View.OnClickListener() {
                public void onClick(View v) {
                    styleSeg(tabs, idx);
                    cb.pick(idx);
                }
            });
            tabs[i] = t;
            seg.addView(t, new LinearLayout.LayoutParams(0, -1, 1));
        }
        styleSeg(tabs, sel);
        return seg;
    }

    static void styleSeg(TextView[] tabs, int on) {
        float r = px(8);
        for (int i = 0; i < tabs.length; i++) {
            GradientDrawable g = new GradientDrawable();
            boolean sel = i == on;
            g.setColor(sel ? INK : PAPER);
            float[] radii = new float[8];
            if (i == 0) radii = new float[]{r, r, 0, 0, 0, 0, r, r};
            if (i == tabs.length - 1) radii = new float[]{0, 0, r, r, r, r, 0, 0};
            if (tabs.length == 1) radii = new float[]{r, r, r, r, r, r, r, r};
            g.setCornerRadii(radii);
            tabs[i].setBackground(g);
            tabs[i].setTextColor(sel ? PAPER : INK);
        }
    }

    static FrameLayout.LayoutParams frame(int w, int h, int gravity) {
        return new FrameLayout.LayoutParams(w, h, gravity);
    }
}
