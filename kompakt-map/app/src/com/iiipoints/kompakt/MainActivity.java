package com.iiipoints.kompakt;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.pm.PackageManager;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.graphics.Paint;
import android.os.Bundle;
import android.os.Handler;
import android.text.TextUtils;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

/**
 * III Points 2026 for the Mudita Kompakt. Three tabs: Map, Lineup, Favorites. Everything links up:
 * a stage on the map opens its lineup, any set in a list jumps to its stage on the map, and starred
 * artists show on the map and in Favorites. Screens are rebuilt in one go with no transitions, so each
 * navigation is a single clean E Ink redraw.
 */
public class MainActivity extends Activity {
    private interface Screen {
        View build();
    }

    private static final int TAB_MAP = 0, TAB_LINEUP = 1, TAB_FAVS = 2;

    private Festival fest;
    private Gps gps;
    private boolean tracking;            // "locate me" on (remembered while the app runs)
    private boolean recenter;            // centre the map on the next fix
    private Location lastFix;
    private Ui.Glyph locateBtn;
    private TextView mapSubtitle, lastSubtitle;
    private Favorites favs;
    private MapView map;
    private int tab = TAB_MAP;
    private final List<Screen> stack = new ArrayList<>();   // screens pushed over the tabs
    private int day = -1;                                    // day shown in lists (follows the clock by default)
    private int lineupMode = 0;                              // 0 = by stage, 1 = A-Z
    private String mapStage;                                 // stage selected on the map
    private final Handler tick = new Handler();
    private final Runnable minute = new Runnable() {
        public void run() {
            if (map != null && tab == TAB_MAP && stack.isEmpty()) map.invalidate();   // refresh "now" once a minute
            tick.postDelayed(this, 60_000);
        }
    };

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        Ui.init(this);
        try {
            fest = new Festival(this);
        } catch (Exception e) {
            throw new RuntimeException("lineup.json", e);
        }
        favs = new Favorites(this);
        try {
            gps = new Gps(this);
        } catch (Exception e) {
            throw new RuntimeException("gps.json", e);
        }
        testHooks();
        show();
    }

    /**
     * Preview/test hooks (adb shell am start -n com.iiipoints.kompakt/.MainActivity ...):
     * --es now "2026-10-16 21:42"  --es favs "Parcels,Four Tet"  --es screen map|lineup|az|favs|filter|info|stage:ID|mapstage:ID
     */
    private void testHooks() {
        Festival.fakeNow = getIntent().getStringExtra("now");
        String seed = getIntent().getStringExtra("favs");
        if (seed != null) {
            for (String name : seed.split(",")) {
                for (int d = 0; d < 2; d++) {
                    for (Festival.Set s : fest.sets(d)) {
                        if (s.artist.equalsIgnoreCase(name.trim()) && !favs.has(s)) favs.toggle(s);
                    }
                }
            }
        }
        String screen = getIntent().getStringExtra("screen");
        if (screen == null) return;
        if (screen.equals("lineup")) tab = TAB_LINEUP;
        else if (screen.equals("az")) {
            tab = TAB_LINEUP;
            lineupMode = 1;
        } else if (screen.equals("favs")) tab = TAB_FAVS;
        else if (screen.equals("filter")) stack.add(filterScreen());
        else if (screen.equals("info")) stack.add(infoScreen());
        else if (screen.startsWith("stage:")) stack.add(stageScreen(screen.substring(6)));
        else if (screen.startsWith("mapstage:")) mapStage = screen.substring(9);
        String loc = getIntent().getStringExtra("loc");          // --es loc "25.79826,-80.20353"
        if (loc != null) {
            Location l = new Location("test");
            l.setLatitude(Double.parseDouble(loc.split(",")[0]));
            l.setLongitude(Double.parseDouble(loc.split(",")[1]));
            l.setAccuracy(12);
            tracking = true;
            recenter = true;
            onFix(l);
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        show();
        tick.postDelayed(minute, 60_000);
        if (tracking) startGps();
    }

    @Override
    protected void onPause() {
        super.onPause();
        tick.removeCallbacks(minute);
        stopGps();   // no GPS in the background
    }

    // ------------------------------------------------------------------------------------- gps

    private final LocationListener listener = new LocationListener() {
        public void onLocationChanged(Location l) {
            onFix(l);
        }

        public void onStatusChanged(String p, int s, Bundle b) {
        }

        public void onProviderEnabled(String p) {
        }

        public void onProviderDisabled(String p) {
        }
    };

    private boolean hasPermission() {
        return android.os.Build.VERSION.SDK_INT < 23
                || checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED;
    }

    private void toggleLocate() {
        if (tracking) {
            tracking = false;
            stopGps();
            lastFix = null;
            if (map != null) map.setYou(Float.NaN, Float.NaN, 0);
            refreshLocateUi();
            return;
        }
        tracking = true;
        recenter = true;
        if (!hasPermission()) {
            requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION}, 1);
            return;
        }
        startGps();
        refreshLocateUi();
    }

    @Override
    public void onRequestPermissionsResult(int code, String[] perms, int[] results) {
        if (results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED) {
            startGps();
        } else {
            tracking = false;
        }
        refreshLocateUi();
    }

    /** GPS every 10 s / 5 m at most: enough for walking, gentle on the battery and the E Ink panel. */
    @SuppressWarnings("MissingPermission")
    private void startGps() {
        if (!hasPermission()) return;
        LocationManager lm = (LocationManager) getSystemService(LOCATION_SERVICE);
        if (lm == null) return;
        try {
            for (String p : new String[]{LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER}) {
                if (!lm.getAllProviders().contains(p)) continue;
                Location last = lm.getLastKnownLocation(p);
                if (last != null && (lastFix == null || last.getTime() > lastFix.getTime())) onFix(last);
                lm.requestLocationUpdates(p, 10_000, 5, listener);
            }
        } catch (SecurityException ignored) {
            tracking = false;
        }
    }

    private void stopGps() {
        LocationManager lm = (LocationManager) getSystemService(LOCATION_SERVICE);
        if (lm != null) lm.removeUpdates(listener);
    }

    private void onFix(Location l) {
        if (lastFix != null && l.getAccuracy() > lastFix.getAccuracy() * 2
                && l.getTime() - lastFix.getTime() < 30_000) return;   // ignore a much worse fix right after a good one
        lastFix = l;
        float[] p = gps.toMap(l.getLatitude(), l.getLongitude());
        MapView m = map();
        m.setYou(p[0], p[1], l.getAccuracy() * gps.unitsPerMetre());
        if (recenter && m.youOnMap()) {
            m.focus(p[0], p[1], Math.max(MapView.ICON_ZOOM, 0.7f));
            recenter = false;
        }
        refreshLocateUi();
    }

    private void refreshLocateUi() {
        if (locateBtn != null) {
            locateBtn.on = tracking && lastFix != null;
            locateBtn.invalidate();
        }
        if (mapSubtitle != null) mapSubtitle.setText(statusLine());
    }

    @Override
    public void onBackPressed() {
        if (!stack.isEmpty()) {
            stack.remove(stack.size() - 1);
            show();
        } else if (tab != TAB_MAP) {
            tab = TAB_MAP;
            show();
        } else if (mapStage != null) {
            mapStage = null;
            show();
        } else {
            super.onBackPressed();
        }
    }

    private void push(Screen s) {
        stack.add(s);
        show();
    }

    private void show() {
        View v = stack.isEmpty() ? tabs() : stack.get(stack.size() - 1).build();
        setContentView(v);
        overridePendingTransition(0, 0);
    }

    private final View.OnClickListener back = new View.OnClickListener() {
        public void onClick(View v) {
            onBackPressed();
        }
    };

    private int currentDay() {
        if (day >= 0) return day;
        Festival.Clock c = Festival.clock();
        if (c.day >= 0) return c.day;
        return c.before ? 0 : 1;
    }

    /** Jump to a stage on the map, with its card open. */
    private void showOnMap(String stageId) {
        stack.clear();
        tab = TAB_MAP;
        mapStage = stageId;
        MapView m = map();
        MapView.Label l = m.stageLabel(stageId);
        if (l != null) m.focus(l.x, l.y, Math.max(0.75f * Ui.px(480) / 480f, MapView.ICON_ZOOM));
        show();
    }

    // ------------------------------------------------------------------------------------ tabs

    private View tabs() {
        Context c = this;
        LinearLayout root = Ui.column(c);
        View content = tab == TAB_MAP ? mapTab() : tab == TAB_LINEUP ? lineupTab() : favsTab();
        root.addView(content, new LinearLayout.LayoutParams(-1, 0, 1));
        root.addView(Ui.rule(c, 2));
        LinearLayout bar = Ui.row(c);
        String[] names = {"Map", "Lineup", "Favorites"};
        for (int i = 0; i < 3; i++) {
            final int idx = i;
            LinearLayout item = Ui.column(c);
            item.setGravity(Gravity.CENTER_HORIZONTAL);
            item.setBackground(Ui.pressable(Ui.PAPER));
            TextView t = Ui.text(c, names[i], i == tab ? Ui.bold : Ui.medium, 21);
            t.setGravity(Gravity.CENTER);
            item.addView(t, new LinearLayout.LayoutParams(-1, 0, 1));
            View line = new View(c);
            line.setBackgroundColor(i == tab ? Ui.INK : Ui.PAPER);
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(Ui.px(64), Ui.px(4));
            lp.bottomMargin = Ui.px(6);
            item.addView(line, lp);
            item.setOnClickListener(new View.OnClickListener() {
                public void onClick(View v) {
                    if (tab != idx) {
                        tab = idx;
                        show();
                    }
                }
            });
            bar.addView(item, new LinearLayout.LayoutParams(0, Ui.px(62), 1));
        }
        root.addView(bar);
        return root;
    }

    private MapView map() {
        if (map == null) {
            try {
                map = new MapView(this);
            } catch (Exception e) {
                throw new RuntimeException("map.json", e);
            }
            map.fest = fest;
            map.favs = favs;
            map.hiddenCats = favs.hiddenCats;
        }
        if (map.getParent() != null) ((ViewGroup) map.getParent()).removeView(map);
        return map;
    }

    private LinearLayout topBar(String title, String subtitle, String[] actions, View.OnClickListener[] handlers, boolean withBack) {
        Context c = this;
        LinearLayout bar = Ui.row(c);
        bar.setPadding(withBack ? Ui.px(6) : Ui.px(22), Ui.px(6), Ui.px(12), Ui.px(6));
        bar.setMinimumHeight(Ui.px(64));
        if (withBack) {
            Ui.Glyph chev = new Ui.Glyph(c, Ui.Glyph.BACK);
            chev.setOnClickListener(back);
            chev.setBackground(Ui.pressable(Ui.PAPER));
            bar.addView(chev, new LinearLayout.LayoutParams(Ui.px(50), Ui.px(50)));
        }
        LinearLayout texts = Ui.column(c);
        texts.setBackgroundColor(0);
        TextView t = Ui.text(c, title, Ui.bold, 28);
        t.setSingleLine(true);
        t.setEllipsize(TextUtils.TruncateAt.END);
        texts.addView(t);
        if (subtitle != null) {
            TextView s = Ui.text(c, subtitle, Ui.medium, 16);
            lastSubtitle = s;
            s.setPadding(0, Ui.px(3), 0, 0);
            texts.addView(s);
        }
        bar.addView(texts, new LinearLayout.LayoutParams(0, -2, 1));
        for (int i = 0; actions != null && i < actions.length; i++) {
            TextView a = Ui.button(c, actions[i], 18, handlers[i]);
            a.setPadding(Ui.px(14), 0, Ui.px(14), 0);
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-2, Ui.px(42));
            lp.leftMargin = Ui.px(8);
            bar.addView(a, lp);
        }
        return bar;
    }

    private String statusLine() {
        if (tracking && lastFix == null) return "Finding your location\u2026";
        if (tracking && map != null && !map.youOnMap()) {
            double m = gps.metresFromVenue(lastFix.getLatitude(), lastFix.getLongitude());
            return m >= 1000 ? String.format(java.util.Locale.US, "You're %.1f km from the venue", m / 1000)
                    : "You're " + Math.round(m / 10) * 10 + " m from the venue";
        }
        Festival.Clock k = Festival.clock();
        if (k.day >= 0 && k.live) return Festival.DAY_LONG[k.day].split(",")[0] + " · live · " + Festival.time(k.t);
        if (k.day >= 0 && k.t < Festival.OPEN) return Festival.DAY_LONG[k.day] + " · doors 4:00 PM";
        if (k.before) return "Oct 16 & 17 · Mana Wynwood";
        return "Mana Wynwood";
    }

    // -------------------------------------------------------------------------------------- map

    private View mapTab() {
        final Context c = this;
        LinearLayout root = Ui.column(c);
        root.addView(topBar("III Points", statusLine(), new String[]{"Filter", "Info"},
                new View.OnClickListener[]{
                        new View.OnClickListener() {
                            public void onClick(View v) {
                                push(filterScreen());
                            }
                        },
                        new View.OnClickListener() {
                            public void onClick(View v) {
                                push(infoScreen());
                            }
                        }}, false));
        mapSubtitle = lastSubtitle;
        root.addView(Ui.rule(c, 2));

        final FrameLayout area = new FrameLayout(c);
        final MapView m = map();
        area.addView(m, new FrameLayout.LayoutParams(-1, -1));

        // zoom buttons, top right
        LinearLayout zoom = Ui.column(c);
        zoom.setBackgroundColor(0);
        TextView plus = Ui.button(c, "+", 28, new View.OnClickListener() {
            public void onClick(View v) {
                m.zoomBy(1.6f, m.getWidth() / 2f, m.getHeight() / 2f);
            }
        });
        TextView minus = Ui.button(c, "−", 28, new View.OnClickListener() {
            public void onClick(View v) {
                m.zoomBy(1 / 1.6f, m.getWidth() / 2f, m.getHeight() / 2f);
            }
        });
        zoom.addView(plus, new LinearLayout.LayoutParams(Ui.px(48), Ui.px(48)));
        LinearLayout.LayoutParams mlp = new LinearLayout.LayoutParams(Ui.px(48), Ui.px(48));
        mlp.topMargin = Ui.px(8);
        zoom.addView(minus, mlp);
        locateBtn = new Ui.Glyph(c, Ui.Glyph.LOCATE);
        locateBtn.setBackground(Ui.outline(9, Ui.PAPER, 2));
        locateBtn.on = tracking && lastFix != null;
        locateBtn.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                toggleLocate();
            }
        });
        LinearLayout.LayoutParams llp = new LinearLayout.LayoutParams(Ui.px(48), Ui.px(48));
        llp.topMargin = Ui.px(16);
        zoom.addView(locateBtn, llp);
        FrameLayout.LayoutParams zlp = Ui.frame(-2, -2, Gravity.TOP | Gravity.RIGHT);
        zlp.setMargins(0, Ui.px(10), Ui.px(10), 0);
        area.addView(zoom, zlp);

        final FrameLayout card = new FrameLayout(c);
        area.addView(card, Ui.frame(-1, -2, Gravity.BOTTOM));
        m.setListener(new MapView.Listener() {
            public void onStage(String id) {
                mapStage = id;
                m.select(id);
                stageCard(card, id);
            }

            public void onEmpty() {
                mapStage = null;
                m.select(null);
                card.removeAllViews();
            }
        });
        m.select(mapStage);
        if (mapStage != null) stageCard(card, mapStage);
        root.addView(area, new LinearLayout.LayoutParams(-1, 0, 1));
        return root;
    }

    /** Bottom card for a stage: now and next (with stars), and a way into its lineup. */
    private void stageCard(FrameLayout holder, final String id) {
        holder.removeAllViews();
        Context c = this;
        final Festival.Stage st = fest.stage(id);
        if (st == null) return;
        LinearLayout card = Ui.column(c);
        card.setBackground(Ui.outline(14, Ui.PAPER, 2.5f));
        card.setPadding(Ui.px(16), Ui.px(10), Ui.px(10), Ui.px(12));
        FrameLayout.LayoutParams lp = Ui.frame(-1, -2, Gravity.BOTTOM);
        lp.setMargins(Ui.px(10), 0, Ui.px(10), Ui.px(10));

        TextView name = Ui.text(c, st.name, Ui.bold, 24);
        card.addView(name);
        Festival.Clock k = Festival.clock();
        int d = currentDay();
        int t = k.day == d ? k.t : 0;
        Festival.Set now = k.day == d && k.live ? st.now(d, t) : null;
        Festival.Set next = st.next(d, now != null ? now.end : t);
        if (now != null) card.addView(setRow(now, "Now · until " + Festival.time(now.end), false, false));
        if (next != null) card.addView(setRow(next, (now != null || k.day == d ? "Next · " : Festival.DAY_LABELS[d] + " · ")
                + Festival.time(next.start), false, false));
        if (now == null && next == null) card.addView(Ui.text(c, "Done for " + Festival.DAY_LONG[d].split(",")[0], Ui.medium, 18));
        TextView open = Ui.button(c, "Full lineup", 19, new View.OnClickListener() {
            public void onClick(View v) {
                push(stageScreen(id));
            }
        });
        LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(-1, Ui.px(46));
        blp.topMargin = Ui.px(8);
        blp.rightMargin = Ui.px(6);
        card.addView(open, blp);
        holder.addView(card, lp);
    }

    // ----------------------------------------------------------------------------------- rows

    /**
     * One set: artist (bold) over a detail line, star toggle on the right. Now playing is inverted,
     * finished sets are struck through. Tapping the row jumps to the stage on the map (if mapLink).
     */
    private LinearLayout setRow(final Festival.Set s, String detail, boolean mapLink, boolean timeColumn) {
        Context c = this;
        Festival.Clock k = Festival.clock();
        boolean now = k.day == s.day && k.live && s.start <= k.t && k.t < s.end;
        boolean past = (k.day == s.day && s.end <= k.t) || k.day > s.day || (!k.before && k.day < 0);
        int fg = now ? Ui.PAPER : Ui.INK;
        final LinearLayout r = Ui.row(c);
        r.setPadding(timeColumn ? Ui.px(18) : 0, Ui.px(9), Ui.px(4), Ui.px(9));
        if (now) r.setBackgroundColor(Ui.INK);
        if (timeColumn) {
            TextView tm = Ui.text(c, Festival.time(s.start) + "\n–" + Festival.shortTime(s.end), Ui.semibold, 16);
            tm.setTextColor(fg);
            if (past) tm.setPaintFlags(tm.getPaintFlags() | Paint.STRIKE_THRU_TEXT_FLAG);
            r.addView(tm, new LinearLayout.LayoutParams(Ui.px(92), -2));
        }
        LinearLayout texts = Ui.column(c);
        texts.setBackgroundColor(0);
        TextView a = Ui.text(c, s.artist, Ui.bold, 21);
        a.setTextColor(fg);
        if (past) a.setPaintFlags(a.getPaintFlags() | Paint.STRIKE_THRU_TEXT_FLAG);
        texts.addView(a);
        if (detail != null && !detail.isEmpty()) {
            TextView d = Ui.text(c, detail, Ui.medium, 16);
            d.setTextColor(fg);
            d.setPadding(0, Ui.px(3), 0, 0);
            texts.addView(d);
        }
        r.addView(texts, new LinearLayout.LayoutParams(0, -2, 1));
        final Ui.Star star = new Ui.Star(c, favs.has(s));
        final boolean inverted = now;
        star.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                favs.toggle(s);
                star.on = favs.has(s);
                star.invalidate();
                if (map != null) map.invalidate();
            }
        });
        if (inverted) star.setBackground(Ui.outline(25, Ui.PAPER, 0));   // white disc so the star reads on black
        r.addView(star, new LinearLayout.LayoutParams(Ui.px(50), Ui.px(50)));
        if (mapLink) {
            r.setOnClickListener(new View.OnClickListener() {
                public void onClick(View v) {
                    showOnMap(s.stage.id);
                }
            });
        }
        return r;
    }

    private View dayToggle(final Runnable onChange) {
        LinearLayout seg = Ui.segmented(this, Festival.DAY_LABELS, currentDay(), new Ui.OnPick() {
            public void pick(int i) {
                day = i;
                onChange.run();
            }
        });
        return seg;
    }

    private void addSeg(LinearLayout root, View seg) {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, Ui.px(44));
        lp.setMargins(Ui.px(18), Ui.px(10), Ui.px(18), 0);
        root.addView(seg, lp);
    }

    // ---------------------------------------------------------------------------------- lineup

    private View lineupTab() {
        Context c = this;
        LinearLayout root = Ui.column(c);
        root.addView(topBar("Lineup", "Tap a set to see its stage on the map", null, null, false));
        root.addView(Ui.rule(c, 2));
        final LinearLayout list = Ui.column(c);
        final Runnable fill = new Runnable() {
            public void run() {
                fillLineup(list);
            }
        };
        addSeg(root, dayToggle(fill));
        LinearLayout modes = Ui.segmented(c, new String[]{"By stage", "A–Z"}, lineupMode, new Ui.OnPick() {
            public void pick(int i) {
                lineupMode = i;
                fill.run();
            }
        });
        addSeg(root, modes);
        View sp = new View(c);
        root.addView(sp, new LinearLayout.LayoutParams(1, Ui.px(10)));
        root.addView(Ui.rule(c, 1));
        fill.run();
        root.addView(Ui.scroll(c, list), new LinearLayout.LayoutParams(-1, 0, 1));
        return root;
    }

    private void fillLineup(LinearLayout list) {
        Context c = this;
        list.removeAllViews();
        int d = currentDay();
        Festival.Clock k = Festival.clock();
        if (lineupMode == 0) {
            for (final Festival.Stage st : fest.stages) {
                String sub = null;
                if (k.day == d && k.live) {
                    Festival.Set now = st.now(d, k.t);
                    if (now != null) sub = "Now: " + (favs.has(now) ? "★ " : "") + now.artist;
                }
                if (sub == null) {
                    int n = st.sets(d).size();
                    sub = n + " sets" + (st.sets(d).isEmpty() ? "" : " · from " + Festival.time(st.sets(d).get(0).start));
                }
                list.addView(Ui.listRow(c, st.name, sub, 25, new View.OnClickListener() {
                    public void onClick(View v) {
                        push(stageScreen(st.id));
                    }
                }));
                list.addView(Ui.rule(c, 1));
            }
        } else {
            List<Festival.Set> all = new ArrayList<>(fest.sets(d));
            Collections.sort(all, new Comparator<Festival.Set>() {
                public int compare(Festival.Set a, Festival.Set b) {
                    return sortKey(a.artist).compareTo(sortKey(b.artist));
                }
            });
            char letter = 0;
            for (Festival.Set s : all) {
                char l = sortKey(s.artist).isEmpty() ? '#' : sortKey(s.artist).charAt(0);
                if (!Character.isLetter(l)) l = '#';
                if (l != letter) {
                    letter = l;
                    TextView h = Ui.text(c, String.valueOf(l), Ui.condBold, 20);
                    h.setPadding(Ui.px(18), Ui.px(10), 0, Ui.px(2));
                    list.addView(h);
                    list.addView(Ui.rule(c, 1));
                }
                LinearLayout r = setRow(s, s.stage.name + " · " + Festival.time(s.start) + "–" + Festival.shortTime(s.end), true, false);
                r.setPadding(Ui.px(18), r.getPaddingTop(), r.getPaddingRight(), r.getPaddingBottom());
                list.addView(r);
                list.addView(Ui.rule(c, 1));
            }
        }
    }

    private static String sortKey(String artist) {
        String s = artist.toUpperCase(java.util.Locale.US).replaceAll("^[^A-Z0-9]+", "");
        return s.startsWith("THE ") ? s.substring(4) : s;
    }

    private Screen stageScreen(final String id) {
        return new Screen() {
            public View build() {
                Context c = MainActivity.this;
                final Festival.Stage st = fest.stage(id);
                LinearLayout root = Ui.column(c);
                String host = st.host.isEmpty() || st.host.equalsIgnoreCase(st.name) ? null : Festival.display(st.host);
                root.addView(topBar(st.name, host, new String[]{"Map"}, new View.OnClickListener[]{
                        new View.OnClickListener() {
                            public void onClick(View v) {
                                showOnMap(id);
                            }
                        }}, true));
                root.addView(Ui.rule(c, 2));
                final LinearLayout list = Ui.column(c);
                final Runnable fill = new Runnable() {
                    public void run() {
                        list.removeAllViews();
                        int d = currentDay();
                        for (Festival.Set s : st.sets(d)) {
                            list.addView(setRow(s, s.note, false, true));
                            list.addView(Ui.rule(MainActivity.this, 1));
                        }
                    }
                };
                addSeg(root, dayToggle(fill));
                root.addView(new View(c), new LinearLayout.LayoutParams(1, Ui.px(10)));
                root.addView(Ui.rule(c, 1));
                fill.run();
                root.addView(Ui.scroll(c, list), new LinearLayout.LayoutParams(-1, 0, 1));
                return root;
            }
        };
    }

    // ------------------------------------------------------------------------------- favorites

    private View favsTab() {
        Context c = this;
        LinearLayout root = Ui.column(c);
        root.addView(topBar("Favorites", "Your starred sets, in time order", null, null, false));
        root.addView(Ui.rule(c, 2));
        final LinearLayout list = Ui.column(c);
        final Runnable fill = new Runnable() {
            public void run() {
                fillFavs(list);
            }
        };
        addSeg(root, dayToggle(fill));
        root.addView(new View(c), new LinearLayout.LayoutParams(1, Ui.px(10)));
        root.addView(Ui.rule(c, 1));
        fill.run();
        root.addView(Ui.scroll(c, list), new LinearLayout.LayoutParams(-1, 0, 1));
        return root;
    }

    private void fillFavs(LinearLayout list) {
        Context c = this;
        list.removeAllViews();
        int d = currentDay();
        List<Festival.Set> mine = new ArrayList<>();
        for (Festival.Set s : fest.sets(d)) if (favs.has(s)) mine.add(s);
        if (mine.isEmpty()) {
            TextView t = Ui.text(c, favs.any()
                    ? "Nothing starred on " + Festival.DAY_LONG[d].split(",")[0] + "."
                    : "Tap the star next to any artist in the Lineup and they'll show up here, in time order.", Ui.medium, 19);
            t.setPadding(Ui.px(22), Ui.px(24), Ui.px(22), Ui.px(24));
            list.addView(t);
            return;
        }
        for (Festival.Set s : mine) {
            String clash = null;
            for (Festival.Set o : mine) {
                if (o != s && o.start < s.end && s.start < o.end) clash = o.artist;
            }
            String detail = s.stage.name + (clash != null ? "  ·  clashes with " + clash : "");
            list.addView(setRow(s, detail, true, true));
            list.addView(Ui.rule(c, 1));
        }
    }

    // ---------------------------------------------------------------------------------- filter

    private static final String[][] CATS = {
            {"food", "Food", "food", "ga"}, {"water", "Water", "water", "ga"}, {"restroom", "Restrooms", "restroom", "ga"},
            {"firstaid", "First aid", "firstaid", "ga"}, {"access", "Accessibility", "accessible", "ga"},
            {"help", "Info, lockers & tickets", "info", "ga"}, {"merch", "Merch", "merch", "ga"},
            {"photo", "Photo spots", "photo", "ga"}, {"gaplus", "GA+ restrooms", "restroom", "gaplus"},
            {"vip", "VIP facilities", "bar", "vip"},
    };

    private Screen filterScreen() {
        return new Screen() {
            public View build() {
                Context c = MainActivity.this;
                LinearLayout root = Ui.column(c);
                root.addView(topBar("Show on map", "Icons appear when you zoom in", null, null, true));
                root.addView(Ui.rule(c, 2));
                LinearLayout list = Ui.column(c);
                for (final String[] cat : CATS) {
                    final LinearLayout r = Ui.row(c);
                    r.setPadding(Ui.px(18), Ui.px(8), Ui.px(18), Ui.px(8));
                    r.addView(map().iconView(cat[2], cat[3], Ui.px(44)), new LinearLayout.LayoutParams(Ui.px(44), Ui.px(44)));
                    TextView t = Ui.text(c, cat[1], Ui.semibold, 21);
                    t.setPadding(Ui.px(14), 0, 0, 0);
                    r.addView(t, new LinearLayout.LayoutParams(0, -2, 1));
                    final TextView box = Ui.text(c, "", Ui.bold, 22);
                    box.setGravity(Gravity.CENTER);
                    final Runnable paint = new Runnable() {
                        public void run() {
                            boolean shown = !favs.hiddenCats.contains(cat[0]);
                            box.setText(shown ? "✓" : "");
                            box.setBackground(Ui.outline(6, Ui.PAPER, 2.5f));
                        }
                    };
                    paint.run();
                    r.addView(box, new LinearLayout.LayoutParams(Ui.px(36), Ui.px(36)));
                    r.setOnClickListener(new View.OnClickListener() {
                        public void onClick(View v) {
                            favs.setHidden(cat[0], !favs.hiddenCats.contains(cat[0]));
                            paint.run();
                        }
                    });
                    list.addView(r);
                    list.addView(Ui.rule(c, 1));
                }
                root.addView(Ui.scroll(c, list), new LinearLayout.LayoutParams(-1, 0, 1));
                return root;
            }
        };
    }

    // ------------------------------------------------------------------------------------ info

    private static final String[][] LEGEND = {
            {"First aid", "firstaid", "ga"}, {"Water", "water", "ga"}, {"Restrooms", "restroom", "ga"},
            {"GA+ restrooms", "restroom", "gaplus"}, {"Food", "food", "ga"}, {"Accessible viewing", "accessible", "ga"},
            {"Lockers", "lockers", "ga"}, {"Info", "info", "ga"}, {"Lost & found", "lostfound", "ga"},
            {"Ticket help", "tickets", "ga"}, {"Will call", "willcall", "ga"}, {"Box office", "boxoffice", "ga"},
            {"Merch", "merch", "ga"}, {"Photo spot", "photo", "ga"}, {"VIP (dashed ring)", "bar", "vip"},
    };

    private Screen infoScreen() {
        return new Screen() {
            public View build() {
                Context c = MainActivity.this;
                LinearLayout root = Ui.column(c);
                root.addView(topBar("Info", null, null, null, true));
                root.addView(Ui.rule(c, 2));
                LinearLayout body = Ui.column(c);
                body.setPadding(Ui.px(20), Ui.px(8), Ui.px(20), Ui.px(24));
                String[][] parts = {
                        {"Hours", "Fri Oct 16 & Sat Oct 17, 4:00 PM – 4:00 AM. Mana Wynwood, 2217 NW 5th Ave, Miami."},
                        {"The map", "Stages are hatched, dance floors dashed, VIP-only areas lightly striped. "
                                + "Stage labels show who's playing now; ★ marks your favorites. Tap a stage for now, next and its lineup."},
                        {"Works offline", "Map and set times live on the phone; no connection needed."},
                        {"Set times", fest.source + ". Times can change; check official channels on the day."},
                        {"Unofficial", "Fan-made companion app, not affiliated with III Points or Mudita."},
                };
                for (String[] p : parts) {
                    TextView h = Ui.text(c, p[0], Ui.bold, 22);
                    h.setPadding(0, Ui.px(14), 0, Ui.px(4));
                    body.addView(h);
                    body.addView(Ui.text(c, p[1], Ui.regular, 18));
                }
                TextView lh = Ui.text(c, "Legend", Ui.bold, 22);
                lh.setPadding(0, Ui.px(18), 0, Ui.px(6));
                body.addView(lh);
                for (String[] item : LEGEND) {
                    LinearLayout r = Ui.row(c);
                    r.setPadding(0, Ui.px(4), 0, Ui.px(4));
                    r.addView(map().iconView(item[1], item[2], Ui.px(40)), new LinearLayout.LayoutParams(Ui.px(40), Ui.px(40)));
                    TextView t = Ui.text(c, item[0], Ui.semibold, 19);
                    t.setPadding(Ui.px(14), 0, 0, 0);
                    r.addView(t);
                    body.addView(r);
                }
                root.addView(Ui.scroll(c, body), new LinearLayout.LayoutParams(-1, 0, 1));
                return root;
            }
        };
    }
}
