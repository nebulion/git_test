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
 * Mudita-style building blocks: black on white, large type, hairline dividers, outlined pill
 * buttons, inverted pressed/selected states, no ripples, shadows or animation.
 * Sizes are given in "design px" of the 480 x 800 Kompakt screen and scaled to the real width.
 */
final class Ui {
    static final int INK = 0xff000000, PAPER = 0xffffffff;
    static Typeface regular, medium, semibold, bold, cond, condBold;
    private static float k = 1;

    static void init(Activity a) {
        k = a.getResources().getDisplayMetrics().widthPixels / 480f;
        regular = Typeface.createFromAsset(a.getAssets(), "fonts/Barlow-400.ttf");
        medium = Typeface.createFromAsset(a.getAssets(), "fonts/Barlow-500.ttf");
        semibold = Typeface.createFromAsset(a.getAssets(), "fonts/Barlow-600.ttf");
        bold = Typeface.createFromAsset(a.getAssets(), "fonts/Barlow-700.ttf");
        cond = Typeface.createFromAsset(a.getAssets(), "fonts/BarlowCondensed-700.ttf");
        condBold = Typeface.createFromAsset(a.getAssets(), "fonts/BarlowCondensed-800.ttf");
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
        d.addState(new int[]{android.R.attr.state_pressed}, outline(26, INK, 2));
        d.addState(new int[]{}, outline(26, PAPER, 2));
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
        static final int BACK = 0, CHEVRON = 1;
        private final int kind;
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

    static FrameLayout.LayoutParams frame(int w, int h, int gravity) {
        return new FrameLayout.LayoutParams(w, h, gravity);
    }
}
