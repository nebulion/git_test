package com.iiipoints.kompakt;

import android.content.Context;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.List;
import java.util.Locale;
import java.util.TimeZone;

/** Lineup data (assets/lineup.json) and festival clock. Times are minutes from the festival day's midnight. */
final class Festival {
    static final String[] DAYS = {"fri", "sat"};
    static final String[] DAY_LABELS = {"Fri 16", "Sat 17"};
    static final String[] DAY_LONG = {"Friday, Oct 16", "Saturday, Oct 17"};
    static final int OPEN = 16 * 60;
    static final int CLOSE = 28 * 60;
    private static final int[][] DATES = {{2026, 10, 16}, {2026, 10, 17}};

    static final class Set {
        final int start, end;
        final String artist, note;
        Stage stage;
        int day;

        Set(int start, int end, String artist, String note) {
            this.start = start;
            this.end = end;
            this.artist = display(artist);
            this.note = display(note);
        }

        /** Key used for favorites: one artist (favoriting an artist stars all their sets). */
        String key() {
            return artist.toUpperCase(Locale.US);
        }
    }

    private static final java.util.Set<String> KEEP = new java.util.HashSet<>(java.util.Arrays.asList(
            "DJ", "MD", "MPH", "INVT", "VTSS", "GZA", "ML", "II", "III", "EZ", "JBZ", "RES_", "HAAI", "VIP", "R/V"));

    /** "BELTRAN B2B BEN STERLING" -> "Beltran b2b Ben Sterling"; acronyms and names with digits stay as written. */
    static String display(String s) {
        if (s == null || s.isEmpty()) return "";
        StringBuilder out = new StringBuilder();
        for (String w : s.trim().split("\\s+")) {
            if (out.length() > 0) out.append(' ');
            String lw = w.toLowerCase(Locale.US);
            if (lw.equals("b2b")) out.append("b2b");
            else if (KEEP.contains(w) || w.matches(".*[0-9].*")) out.append(w);
            else out.append(Character.toUpperCase(lw.charAt(0))).append(lw.substring(1));
        }
        return out.toString();
    }

    static final class Stage {
        final String id, name, host;
        final List<List<Set>> days = new ArrayList<>();

        Stage(String id, String name, String host) {
            this.id = id;
            this.name = name;
            this.host = host;
        }

        List<Set> sets(int day) {
            return days.get(day);
        }

        /** Set playing at time t on the given day, or null. */
        Set now(int day, int t) {
            for (Set s : days.get(day)) if (s.start <= t && t < s.end) return s;
            return null;
        }

        /** First set starting at or after t, or null. */
        Set next(int day, int t) {
            for (Set s : days.get(day)) if (s.start >= t) return s;
            return null;
        }
    }

    /** Where we are in the festival right now. */
    static final class Clock {
        final int day;        // 0 = Friday, 1 = Saturday, -1 = before/after
        final int t;          // minutes since the festival day's midnight
        final boolean live;   // doors open
        final boolean before; // before the festival started

        Clock(int day, int t, boolean live, boolean before) {
            this.day = day;
            this.t = t;
            this.live = live;
            this.before = before;
        }
    }

    final List<Stage> stages = new ArrayList<>();
    final String source;

    Festival(Context ctx) throws Exception {
        JSONObject doc = new JSONObject(readAsset(ctx, "lineup.json"));
        source = doc.optString("source");
        JSONArray st = doc.getJSONArray("stages");
        for (int i = 0; i < st.length(); i++) {
            JSONObject o = st.getJSONObject(i);
            Stage stage = new Stage(o.getString("id"), o.getString("name"), o.optString("host"));
            JSONObject sets = o.getJSONObject("sets");
            for (String day : DAYS) {
                List<Set> list = new ArrayList<>();
                JSONArray arr = sets.optJSONArray(day);
                for (int j = 0; arr != null && j < arr.length(); j++) {
                    JSONArray r = arr.getJSONArray(j);
                    Set set = new Set(minutes(r.getString(0)), minutes(r.getString(1)), r.getString(2),
                            r.length() > 3 ? r.getString(3) : "");
                    set.stage = stage;
                    set.day = stage.days.size();
                    list.add(set);
                }
                stage.days.add(list);
            }
            stages.add(stage);
        }
    }

    /** All sets of a day, in start order. */
    List<Set> sets(int day) {
        List<Set> all = new ArrayList<>();
        for (Stage s : stages) all.addAll(s.sets(day));
        java.util.Collections.sort(all, new java.util.Comparator<Set>() {
            public int compare(Set a, Set b) {
                return a.start != b.start ? a.start - b.start : a.artist.compareToIgnoreCase(b.artist);
            }
        });
        return all;
    }

    Stage stage(String id) {
        for (Stage s : stages) if (s.id.equals(id)) return s;
        return null;
    }

    /** Optional fixed time for previews/tests, e.g. "2026-10-16 21:42" (festival local time). */
    static String fakeNow;

    static Clock clock() {
        Calendar c = Calendar.getInstance(TimeZone.getTimeZone("America/New_York"));
        if (fakeNow != null) {
            try {
                String[] p = fakeNow.split("[- :]");
                c.set(Integer.parseInt(p[0]), Integer.parseInt(p[1]) - 1, Integer.parseInt(p[2]),
                        Integer.parseInt(p[3]), Integer.parseInt(p[4]), 0);
            } catch (RuntimeException ignored) {
                // malformed: use the real clock
            }
        }
        int y = c.get(Calendar.YEAR), m = c.get(Calendar.MONTH) + 1, d = c.get(Calendar.DAY_OF_MONTH);
        int mins = c.get(Calendar.HOUR_OF_DAY) * 60 + c.get(Calendar.MINUTE);
        for (int i = 0; i < DATES.length; i++) {
            int[] dt = DATES[i];
            if (y == dt[0] && m == dt[1] && d == dt[2] && mins >= 12 * 60) {
                return new Clock(i, mins, mins >= OPEN, false);
            }
            if (y == dt[0] && m == dt[1] && d == dt[2] + 1 && mins < 12 * 60) {
                int t = mins + 24 * 60;
                return new Clock(i, t, t < CLOSE, false);
            }
        }
        boolean before = y < 2026 || (y == 2026 && (m < 10 || (m == 10 && d < 16)));
        return new Clock(-1, mins, false, before);
    }

    static int minutes(String hhmm) {
        int colon = hhmm.indexOf(':');
        return Integer.parseInt(hhmm.substring(0, colon)) * 60 + Integer.parseInt(hhmm.substring(colon + 1));
    }

    /** 1290 -> "9:30 PM" */
    static String time(int t) {
        int h = (t / 60) % 24, m = t % 60;
        return String.format(Locale.US, "%d:%02d %s", (h + 11) % 12 + 1, m, h < 12 ? "AM" : "PM");
    }

    /** 1290 -> "9:30" */
    static String shortTime(int t) {
        int h = (t / 60) % 24, m = t % 60;
        return String.format(Locale.US, "%d:%02d", (h + 11) % 12 + 1, m);
    }

    static String readAsset(Context ctx, String name) throws Exception {
        InputStream in = ctx.getAssets().open(name);
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buf = new byte[16384];
        for (int n; (n = in.read(buf)) > 0; ) out.write(buf, 0, n);
        in.close();
        return out.toString("UTF-8");
    }
}
