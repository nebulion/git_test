package com.iiipoints.kompakt;

import android.content.Context;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * GPS -> map coordinates, using assets/gps.json (tools/gps_calibrate.py). The official map is not to
 * scale, so each axis is mapped piecewise-linearly between real street centrelines (from OpenStreetMap).
 */
final class Gps {
    private final double lat0, lon0, kx, ky;
    private final double[][] northToU, eastToW;

    Gps(Context c) throws Exception {
        JSONObject d = new JSONObject(Festival.readAsset(c, "gps.json"));
        lat0 = d.getDouble("lat0");
        lon0 = d.getDouble("lon0");
        kx = d.getDouble("kx");
        ky = d.getDouble("ky");
        northToU = knots(d.getJSONArray("north_to_u"));
        eastToW = knots(d.getJSONArray("east_to_w"));
    }

    private static double[][] knots(JSONArray a) throws Exception {
        double[][] k = new double[a.length()][2];
        for (int i = 0; i < a.length(); i++) {
            k[i][0] = a.getJSONArray(i).getDouble(0);
            k[i][1] = a.getJSONArray(i).getDouble(1);
        }
        return k;
    }

    private static double interp(double[][] k, double v) {
        int i = 0;
        while (i < k.length - 2 && v > k[i + 1][0]) i++;
        double[] a = k[i], b = k[i + 1];
        return a[1] + (v - a[0]) * (b[1] - a[1]) / (b[0] - a[0]);
    }

    /** {u, w}: map coordinates (the diagram map draws ground coordinates directly). */
    float[] toMap(double lat, double lon) {
        double east = (lon - lon0) * kx, north = (lat - lat0) * ky;
        return new float[]{(float) interp(northToU, north), (float) interp(eastToW, east)};
    }

    /** Map units per metre around the venue (for the accuracy ring). */
    float unitsPerMetre() {
        return (float) Math.abs((northToU[northToU.length - 1][1] - northToU[0][1])
                / (northToU[northToU.length - 1][0] - northToU[0][0]));
    }

    /** Straight-line distance in metres from the venue centre. */
    double metresFromVenue(double lat, double lon) {
        double east = (lon - lon0) * kx, north = (lat - lat0) * ky;
        return Math.hypot(east + 60, north + 10);
    }
}
