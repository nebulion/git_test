package com.iiipoints.kompakt;

import android.content.Context;
import android.content.SharedPreferences;

import java.util.HashSet;
import java.util.Set;

/** Starred artists and map filter settings, kept on the phone (SharedPreferences). */
final class Favorites {
    private final SharedPreferences prefs;
    private final Set<String> stars;
    final Set<String> hiddenCats;

    Favorites(Context c) {
        prefs = c.getSharedPreferences("kompakt", Context.MODE_PRIVATE);
        stars = new HashSet<>(prefs.getStringSet("stars", new HashSet<String>()));
        Set<String> def = new HashSet<>();
        def.add("vip");
        def.add("gaplus");
        hiddenCats = new HashSet<>(prefs.getStringSet("hidden", def));
    }

    boolean has(Festival.Set s) {
        return stars.contains(s.key());
    }

    void toggle(Festival.Set s) {
        if (!stars.remove(s.key())) stars.add(s.key());
        prefs.edit().putStringSet("stars", new HashSet<>(stars)).apply();
    }

    boolean any() {
        return !stars.isEmpty();
    }

    void setHidden(String cat, boolean hidden) {
        if (hidden) hiddenCats.add(cat);
        else hiddenCats.remove(cat);
        prefs.edit().putStringSet("hidden", new HashSet<>(hiddenCats)).apply();
    }
}
