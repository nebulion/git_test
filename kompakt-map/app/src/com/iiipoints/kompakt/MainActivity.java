package com.iiipoints.kompakt;

import android.app.Activity;
import android.content.Context;
import android.graphics.Paint;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.util.ArrayList;
import java.util.List;

/**
 * III Points 2026 for the Mudita Kompakt. One activity, a stack of plain screens, no transitions:
 * every navigation is a single full redraw, which is what an E Ink panel likes best.
 */
public class MainActivity extends Activity {
    private interface Screen {
        View build();
    }

    private final List<Screen> stack = new ArrayList<>();
    private Festival fest;
    private MapView map;           // kept so the map keeps its pan/zoom between visits
    private int stageDay = -1;     // day shown on stage screens (follows the festival clock by default)

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
        // Test/preview hooks: adb shell am start -n com.iiipoints.kompakt/.MainActivity
        //   --es now "2026-10-16 21:42" --es screen map|now|stages|legend|info|stage:<id>|map:<id>
        Festival.fakeNow = getIntent().getStringExtra("now");
        push(home());
        String screen = getIntent().getStringExtra("screen");
        if (screen != null) {
            if (screen.equals("map")) push(mapScreen(null));
            else if (screen.equals("now")) push(nowScreen());
            else if (screen.equals("stages")) push(stagesScreen());
            else if (screen.equals("legend")) push(legendScreen());
            else if (screen.equals("info")) push(infoScreen());
            else if (screen.startsWith("stage:")) push(stageScreen(screen.substring(6)));
            else if (screen.startsWith("map:")) push(mapScreen("stage:" + screen.substring(4)));
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (!stack.isEmpty()) show();   // refresh "now" information once when returning
    }

    @Override
    public void onBackPressed() {
        if (stack.size() > 1) {
            stack.remove(stack.size() - 1);
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
        View v = stack.get(stack.size() - 1).build();
        if (v.getParent() != null) ((ViewGroup) v.getParent()).removeView(v);
        setContentView(v);
        overridePendingTransition(0, 0);
    }

    private final View.OnClickListener back = new View.OnClickListener() {
        public void onClick(View v) {
            onBackPressed();
        }
    };

    private int currentDay() {
        Festival.Clock c = Festival.clock();
        if (c.day >= 0) return c.day;
        return c.before ? 0 : 1;
    }

    private static String titleCase(String s) {
        return s; // artist names keep the festival's own capitalisation
    }

    // ------------------------------------------------------------------------------------- home

    private Screen home() {
        return new Screen() {
            public View build() {
                Context c = MainActivity.this;
                LinearLayout root = Ui.column(c);
                LinearLayout head = Ui.column(c);
                head.setPadding(Ui.px(24), Ui.px(26), Ui.px(24), Ui.px(18));
                head.addView(Ui.text(c, "III POINTS", Ui.condBold, 66));
                TextView meta = Ui.text(c, "Mana Wynwood · Oct 16 & 17", Ui.semibold, 20);
                meta.setPadding(0, Ui.px(8), 0, 0);
                head.addView(meta);
                root.addView(head);
                root.addView(Ui.rule(c, 2));

                TextView now = Ui.text(c, statusLine(), Ui.semibold, 20);
                now.setPadding(Ui.px(24), Ui.px(14), Ui.px(24), Ui.px(14));
                root.addView(now);
                root.addView(Ui.rule(c, 2));

                LinearLayout list = Ui.column(c);
                addRow(list, "Map", null, new View.OnClickListener() {
                    public void onClick(View v) {
                        push(mapScreen(null));
                    }
                });
                addRow(list, "Now playing", null, new View.OnClickListener() {
                    public void onClick(View v) {
                        push(nowScreen());
                    }
                });
                addRow(list, "Stages", null, new View.OnClickListener() {
                    public void onClick(View v) {
                        push(stagesScreen());
                    }
                });
                addRow(list, "Legend", null, new View.OnClickListener() {
                    public void onClick(View v) {
                        push(legendScreen());
                    }
                });
                addRow(list, "Info", null, new View.OnClickListener() {
                    public void onClick(View v) {
                        push(infoScreen());
                    }
                });
                root.addView(Ui.scroll(c, list), new LinearLayout.LayoutParams(-1, 0, 1));
                return root;
            }
        };
    }

    private String statusLine() {
        Festival.Clock clock = Festival.clock();
        if (clock.day >= 0 && clock.live) {
            int playing = 0;
            for (Festival.Stage s : fest.stages) if (s.now(clock.day, clock.t) != null) playing++;
            return Festival.DAY_LONG[clock.day].split(",")[0] + " · live now\n" + playing + " stages playing · until 4:00 AM";
        }
        if (clock.day >= 0 && clock.t < Festival.OPEN) {
            return Festival.DAY_LONG[clock.day] + "\nDoors open 4:00 PM";
        }
        if (clock.before) return "Friday, Oct 16 & Saturday, Oct 17\nDoors 4:00 PM – 4:00 AM";
        return "See you next year.\nSchedule stays available offline.";
    }

    private void addRow(LinearLayout list, String title, String sub, View.OnClickListener l) {
        list.addView(Ui.listRow(this, title, sub, 30, l));
        list.addView(Ui.rule(this, 1));
    }

    // -------------------------------------------------------------------------------------- map

    private Screen mapScreen(final String focusId) {
        return new Screen() {
            public View build() {
                final Context c = MainActivity.this;
                LinearLayout root = Ui.column(c);
                root.addView(Ui.bar(c, "Map", "Legend", back, new View.OnClickListener() {
                    public void onClick(View v) {
                        push(legendScreen());
                    }
                }));
                root.addView(Ui.rule(c, 2));

                if (map == null) {
                    try {
                        map = new MapView(c);
                    } catch (Exception e) {
                        throw new RuntimeException("map.json", e);
                    }
                }
                final FrameLayout area = new FrameLayout(c);
                area.addView(map, new FrameLayout.LayoutParams(-1, -1));
                final FrameLayout callout = new FrameLayout(c);
                area.addView(callout, Ui.frame(-1, -2, Gravity.BOTTOM));
                map.setListener(new MapView.Listener() {
                    public void onHit(String id) {
                        map.select(id);
                        showCallout(callout, id);
                    }
                });
                if (focusId != null) {
                    MapView.Hit h = map.hit(focusId);
                    if (h != null) map.focus(h.r.centerX(), h.r.centerY() + 120, 0.95f * Ui.px(480) / 480f);
                    map.select(focusId);
                    showCallout(callout, focusId);
                } else {
                    map.select(null);
                }
                root.addView(area, new LinearLayout.LayoutParams(-1, 0, 1));
                root.addView(Ui.rule(c, 2));

                LinearLayout buttons = Ui.row(c);
                buttons.setPadding(Ui.px(14), Ui.px(12), Ui.px(14), Ui.px(12));
                buttons.addView(Ui.button(c, "−", 32, new View.OnClickListener() {
                    public void onClick(View v) {
                        map.zoomBy(1 / 1.6f, map.getWidth() / 2f, map.getHeight() / 2f);
                    }
                }), new LinearLayout.LayoutParams(Ui.px(70), Ui.px(50)));
                buttons.addView(Ui.spacer(c, Ui.px(10)));
                buttons.addView(Ui.button(c, "Fit", 22, new View.OnClickListener() {
                    public void onClick(View v) {
                        map.fit();
                    }
                }), new LinearLayout.LayoutParams(0, Ui.px(50), 1));
                buttons.addView(Ui.spacer(c, Ui.px(10)));
                buttons.addView(Ui.button(c, "+", 32, new View.OnClickListener() {
                    public void onClick(View v) {
                        map.zoomBy(1.6f, map.getWidth() / 2f, map.getHeight() / 2f);
                    }
                }), new LinearLayout.LayoutParams(Ui.px(70), Ui.px(50)));
                buttons.addView(Ui.spacer(c, Ui.px(10)));
                buttons.addView(Ui.button(c, "Now", 22, new View.OnClickListener() {
                    public void onClick(View v) {
                        push(nowScreen());
                    }
                }), new LinearLayout.LayoutParams(0, Ui.px(50), 1));
                root.addView(buttons);
                return root;
            }
        };
    }

    private void showCallout(FrameLayout holder, String id) {
        holder.removeAllViews();
        Context c = this;
        LinearLayout card = Ui.column(c);
        card.setBackground(Ui.outline(14, Ui.PAPER, 2.5f));
        card.setPadding(Ui.px(16), Ui.px(12), Ui.px(16), Ui.px(14));
        FrameLayout.LayoutParams lp = Ui.frame(-1, -2, Gravity.BOTTOM);
        lp.setMargins(Ui.px(14), 0, Ui.px(14), Ui.px(14));

        if (id.startsWith("stage:")) {
            final Festival.Stage s = fest.stage(id.substring(6));
            if (s == null) return;
            TextView name = Ui.text(c, (s.name + (s.host.isEmpty() || s.host.equalsIgnoreCase(s.name) ? "" : " · " + s.host)).toUpperCase(), Ui.condBold, 22);
            name.setSingleLine(true);
            name.setEllipsize(android.text.TextUtils.TruncateAt.END);
            card.addView(name);
            Festival.Clock clock = Festival.clock();
            int day = clock.day >= 0 ? clock.day : currentDay();
            Festival.Set now = clock.day >= 0 && clock.live ? s.now(day, clock.t) : null;
            Festival.Set next = s.next(day, clock.day >= 0 ? clock.t : 0);
            TextView big = Ui.text(c, now != null ? now.artist : next != null ? next.artist : "Nothing scheduled", Ui.bold, 25);
            big.setPadding(0, Ui.px(6), 0, 0);
            card.addView(big);
            String meta;
            if (now != null) {
                meta = "Now until " + Festival.time(now.end) + (next != null ? " · Next " + next.artist + " " + Festival.shortTime(next.start) : "");
            } else if (next != null) {
                meta = (clock.day >= 0 ? "Next · " : Festival.DAY_LABELS[day] + " · ") + Festival.time(next.start) + "–" + Festival.time(next.end);
            } else {
                meta = "Done for " + Festival.DAY_LONG[day].split(",")[0];
            }
            card.addView(Ui.text(c, meta, Ui.medium, 17));
            TextView open = Ui.button(c, "Full schedule", 19, new View.OnClickListener() {
                public void onClick(View v) {
                    push(stageScreen(s.id));
                }
            });
            LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(-1, Ui.px(46));
            blp.topMargin = Ui.px(10);
            card.addView(open, blp);
        } else if (id.equals("place:entrance")) {
            card.addView(Ui.text(c, "MAIN ENTRANCE", Ui.condBold, 22));
            card.addView(Ui.text(c, "NW 6th Ave at NW 23rd St. Box office, will call and ticket help are just inside.", Ui.medium, 18));
        } else {
            return;
        }
        holder.addView(card, lp);
    }

    // ----------------------------------------------------------------------------------- stages

    private Screen stagesScreen() {
        return new Screen() {
            public View build() {
                Context c = MainActivity.this;
                LinearLayout root = Ui.column(c);
                root.addView(Ui.bar(c, "Stages", null, back, null));
                root.addView(Ui.rule(c, 2));
                LinearLayout list = Ui.column(c);
                Festival.Clock clock = Festival.clock();
                for (final Festival.Stage s : fest.stages) {
                    String sub = hostLine(s);
                    if (clock.day >= 0 && clock.live) {
                        Festival.Set now = s.now(clock.day, clock.t);
                        if (now != null) sub = "Now: " + now.artist;
                    }
                    list.addView(Ui.listRow(c, s.name, sub, 28, new View.OnClickListener() {
                        public void onClick(View v) {
                            push(stageScreen(s.id));
                        }
                    }));
                    list.addView(Ui.rule(c, 1));
                }
                root.addView(Ui.scroll(c, list), new LinearLayout.LayoutParams(-1, 0, 1));
                return root;
            }
        };
    }

    private static String hostLine(Festival.Stage s) {
        String h = s.host;
        if (h.isEmpty() || h.equalsIgnoreCase(s.name)) return "Stage";
        h = h.charAt(0) + h.substring(1).toLowerCase();
        return h.replace("dj", "DJ").replace("l-acoustics", "L-Acoustics").replace("apple music", "Apple Music")
                .replace("wvum", "WVUM").replace("red bull", "Red Bull").replace("poplife", "Poplife")
                .replace("miami community radio", "Miami Community Radio").replace("otherworld", "Otherworld")
                .replace("masisi", "Masisi").replace("perreo del futuro", "Perreo del Futuro")
                .replace("1-800 bankroll", "1-800 Bankroll").replace("unforeseen", "Unforeseen")
                .replace(" fri ", " Fri ").replace(" sat ", " Sat ").replace("· sat", "· Sat");
    }

    private Screen stageScreen(final String id) {
        return new Screen() {
            public View build() {
                final Context c = MainActivity.this;
                final Festival.Stage s = fest.stage(id);
                LinearLayout root = Ui.column(c);
                root.addView(Ui.bar(c, s.name, "Map", back, new View.OnClickListener() {
                    public void onClick(View v) {
                        push(mapScreen("stage:" + s.id));
                    }
                }));
                root.addView(Ui.rule(c, 2));

                final Festival.Clock clock = Festival.clock();
                if (stageDay < 0) stageDay = currentDay();
                final LinearLayout list = Ui.column(c);

                // Fri / Sat segmented control
                final LinearLayout seg = Ui.row(c);
                seg.setBackground(Ui.outline(26, Ui.PAPER, 2));
                LinearLayout.LayoutParams slp = new LinearLayout.LayoutParams(-1, Ui.px(48));
                slp.setMargins(Ui.px(24), Ui.px(14), Ui.px(24), Ui.px(14));
                final TextView[] tabs = new TextView[2];
                for (int d = 0; d < 2; d++) {
                    final int day = d;
                    TextView t = Ui.text(c, Festival.DAY_LABELS[d], Ui.bold, 22);
                    t.setGravity(Gravity.CENTER);
                    t.setOnClickListener(new View.OnClickListener() {
                        public void onClick(View v) {
                            stageDay = day;
                            styleTabs(tabs, day);
                            fillSets(list, s, day, clock);
                        }
                    });
                    tabs[d] = t;
                    seg.addView(t, new LinearLayout.LayoutParams(0, -1, 1));
                }
                styleTabs(tabs, stageDay);
                root.addView(seg, slp);
                root.addView(Ui.rule(c, 1));
                fillSets(list, s, stageDay, clock);
                root.addView(Ui.scroll(c, list), new LinearLayout.LayoutParams(-1, 0, 1));
                return root;
            }
        };
    }

    private void styleTabs(TextView[] tabs, int on) {
        for (int i = 0; i < tabs.length; i++) {
            boolean sel = i == on;
            android.graphics.drawable.GradientDrawable g = new android.graphics.drawable.GradientDrawable();
            g.setColor(sel ? Ui.INK : Ui.PAPER);
            float r = Ui.px(24);
            g.setCornerRadii(i == 0 ? new float[]{r, r, 0, 0, 0, 0, r, r} : new float[]{0, 0, r, r, r, r, 0, 0});
            tabs[i].setBackground(g);
            tabs[i].setTextColor(sel ? Ui.PAPER : Ui.INK);
        }
    }

    private void fillSets(LinearLayout list, Festival.Stage s, int day, Festival.Clock clock) {
        Context c = this;
        list.removeAllViews();
        boolean today = clock.day == day;
        for (Festival.Set set : s.sets(day)) {
            boolean now = today && clock.live && set.start <= clock.t && clock.t < set.end;
            boolean past = (today && set.end <= clock.t) || (!clock.before && clock.day < 0) || (clock.day > day);
            LinearLayout r = Ui.row(c);
            r.setGravity(Gravity.TOP);
            r.setPadding(Ui.px(24), Ui.px(13), Ui.px(20), Ui.px(13));
            if (now) r.setBackgroundColor(Ui.INK);
            int col = now ? Ui.PAPER : Ui.INK;
            TextView t = Ui.text(c, Festival.time(set.start) + "\n–" + Festival.shortTime(set.end), Ui.semibold, 18);
            t.setTextColor(col);
            r.addView(t, new LinearLayout.LayoutParams(Ui.px(104), -2));
            LinearLayout right = Ui.column(c);
            right.setBackgroundColor(0);
            TextView a = Ui.text(c, set.artist + (now ? "  ◂ NOW" : ""), Ui.semibold, 23);
            a.setTextColor(col);
            right.addView(a);
            if (!set.note.isEmpty()) {
                TextView n = Ui.text(c, set.note, Ui.medium, 16);
                n.setTextColor(col);
                n.setPadding(0, Ui.px(4), 0, 0);
                right.addView(n);
            }
            if (past) {
                t.setPaintFlags(t.getPaintFlags() | Paint.STRIKE_THRU_TEXT_FLAG);
                a.setPaintFlags(a.getPaintFlags() | Paint.STRIKE_THRU_TEXT_FLAG);
            }
            r.addView(right, new LinearLayout.LayoutParams(0, -2, 1));
            list.addView(r);
            list.addView(Ui.rule(c, 1));
        }
        if (s.sets(day).isEmpty()) {
            TextView none = Ui.text(c, "No sets listed.", Ui.medium, 20);
            none.setPadding(Ui.px(24), Ui.px(20), Ui.px(24), Ui.px(20));
            list.addView(none);
        }
    }

    // -------------------------------------------------------------------------------------- now

    private Screen nowScreen() {
        return new Screen() {
            public View build() {
                final Context c = MainActivity.this;
                final Festival.Clock clock = Festival.clock();
                LinearLayout root = Ui.column(c);
                String stamp = clock.day >= 0 ? Festival.time(clock.t) : "";
                root.addView(Ui.bar(c, "Now playing", stamp.isEmpty() ? null : stamp, back, new View.OnClickListener() {
                    public void onClick(View v) {
                        show(); // manual refresh: one redraw, on demand
                    }
                }));
                root.addView(Ui.rule(c, 2));
                LinearLayout list = Ui.column(c);
                boolean live = clock.day >= 0 && clock.live;
                int day = clock.day >= 0 ? clock.day : currentDay();
                int t = clock.day >= 0 ? clock.t : 0;
                if (!live) {
                    TextView note = Ui.text(c, clock.day >= 0 && clock.t < Festival.OPEN
                            ? "Doors open at 4:00 PM. First sets:"
                            : clock.before ? "The festival hasn't started. First sets on " + Festival.DAY_LONG[0] + ":"
                            : clock.day >= 0 ? "That's a wrap for tonight." : "The festival is over.", Ui.semibold, 20);
                    note.setPadding(Ui.px(24), Ui.px(16), Ui.px(24), Ui.px(16));
                    list.addView(note);
                    list.addView(Ui.rule(c, 1));
                }
                for (final Festival.Stage s : fest.stages) {
                    Festival.Set now = live ? s.now(day, t) : null;
                    Festival.Set next = s.next(day, t);
                    if (now == null && next == null) continue;
                    final LinearLayout r = Ui.column(c);
                    r.setPadding(Ui.px(24), Ui.px(12), Ui.px(24), Ui.px(12));
                    final TextView st = Ui.text(c, s.name.toUpperCase(), Ui.condBold, 18);
                    st.setLetterSpacing(0.06f);
                    r.addView(st);
                    final TextView big = Ui.text(c, now != null ? now.artist : next.artist, Ui.bold, 25);
                    big.setPadding(0, Ui.px(4), 0, Ui.px(2));
                    r.addView(big);
                    String meta = now != null
                            ? "until " + Festival.time(now.end) + (next != null ? " · next " + next.artist + " " + Festival.shortTime(next.start) : "")
                            : (live ? "next at " : "") + Festival.time(next.start) + "–" + Festival.time(next.end);
                    final TextView m = Ui.text(c, meta, Ui.medium, 17);
                    r.addView(m);
                    r.setBackground(Ui.pressable(Ui.PAPER));
                    r.setOnClickListener(new View.OnClickListener() {
                        public void onClick(View v) {
                            push(stageScreen(s.id));
                        }
                    });
                    r.setOnTouchListener(new View.OnTouchListener() {
                        public boolean onTouch(View v, android.view.MotionEvent e) {
                            int a = e.getActionMasked();
                            int col = a == android.view.MotionEvent.ACTION_DOWN ? Ui.PAPER : Ui.INK;
                            if (a == android.view.MotionEvent.ACTION_DOWN || a == android.view.MotionEvent.ACTION_UP
                                    || a == android.view.MotionEvent.ACTION_CANCEL) {
                                st.setTextColor(col);
                                big.setTextColor(col);
                                m.setTextColor(col);
                            }
                            return false;
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

    // ----------------------------------------------------------------------------------- legend

    private static final String[][] LEGEND = {
            {"First aid", "firstaid", "ga"}, {"Accessible viewing", "accessible", "ga"}, {"Lockers", "lockers", "ga"},
            {"Food", "food", "ga"}, {"Water stations", "water", "ga"}, {"VIP water stations", "water", "vip"},
            {"VIP & VIP+ upgrade", "vip", "vip"}, {"VIP concierge", "vip", "vipring"}, {"VIP bar", "bar", "vip"},
            {"VIP food", "food", "vip"}, {"Merch", "merch", "ga"}, {"Table service", "table", "ga"},
            {"Info", "info", "ga"}, {"Ticket help", "tickets", "ga"}, {"Will call", "willcall", "ga"},
            {"Box office", "boxoffice", "vip"}, {"Lost & found", "lostfound", "ga"}, {"Restrooms", "restroom", "ga"},
            {"VIP restrooms", "restroom", "vip"}, {"GA+ restrooms", "restroom", "gaplus"}, {"Photo spot", "photo", "vip"},
    };

    private Screen legendScreen() {
        return new Screen() {
            public View build() {
                Context c = MainActivity.this;
                LinearLayout root = Ui.column(c);
                root.addView(Ui.bar(c, "Legend", null, back, null));
                root.addView(Ui.rule(c, 2));
                LinearLayout list = Ui.column(c);
                if (map == null) {
                    try {
                        map = new MapView(c);
                    } catch (Exception e) {
                        throw new RuntimeException(e);
                    }
                }
                for (String[] item : LEGEND) {
                    LinearLayout r = Ui.row(c);
                    r.setPadding(Ui.px(24), Ui.px(10), Ui.px(24), Ui.px(10));
                    r.addView(map.iconView(item[1], item[2], Ui.px(46)), new LinearLayout.LayoutParams(Ui.px(46), Ui.px(46)));
                    TextView t = Ui.text(c, item[0], Ui.semibold, 23);
                    t.setPadding(Ui.px(18), 0, 0, 0);
                    r.addView(t);
                    list.addView(r);
                    list.addView(Ui.rule(c, 1));
                }
                TextView key = Ui.text(c, "Black discs are open to everyone. White discs with a ring are VIP. "
                        + "Boxed names are stages: tap one on the map for who's playing.", Ui.medium, 18);
                key.setPadding(Ui.px(24), Ui.px(16), Ui.px(24), Ui.px(24));
                list.addView(key);
                root.addView(Ui.scroll(c, list), new LinearLayout.LayoutParams(-1, 0, 1));
                return root;
            }
        };
    }

    // ------------------------------------------------------------------------------------- info

    private Screen infoScreen() {
        return new Screen() {
            public View build() {
                Context c = MainActivity.this;
                LinearLayout root = Ui.column(c);
                root.addView(Ui.bar(c, "Info", null, back, null));
                root.addView(Ui.rule(c, 2));
                LinearLayout body = Ui.column(c);
                body.setPadding(Ui.px(24), Ui.px(16), Ui.px(24), Ui.px(24));
                String[][] parts = {
                        {"Hours", "Friday Oct 16 and Saturday Oct 17, 4:00 PM to 4:00 AM. Mana Wynwood, 2217 NW 5th Ave, Miami."},
                        {"Works offline", "Map and set times are stored on the phone. No connection is needed."},
                        {"Set times", fest.source + ". Times can change; check the official channels on the day."},
                        {"Map", "Black and white redraw of the official 2026 festival map for E Ink. "
                                + "Drag to pan, pinch or double tap to zoom, tap a stage name for its schedule."},
                        {"Unofficial", "Fan-made companion app, not affiliated with III Points or Mudita."},
                };
                for (String[] p : parts) {
                    TextView h = Ui.text(c, p[0], Ui.bold, 23);
                    h.setPadding(0, Ui.px(10), 0, Ui.px(4));
                    body.addView(h);
                    body.addView(Ui.text(c, p[1], Ui.regular, 19));
                }
                root.addView(Ui.scroll(c, body), new LinearLayout.LayoutParams(-1, 0, 1));
                return root;
            }
        };
    }
}
