import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import React from "react";
import { StyleSheet, Text, View } from "react-native";
const mockHistory = [
    {
        id: "meal-1",
        title: "Grilled chicken, brown rice, broccoli",
        calories: 469,
        status: "completed",
    },
    {
        id: "meal-2",
        title: "Unknown upload",
        calories: 0,
        status: "rejected: non_food_image",
    },
];
export function HistoryScreen() {
    return (_jsxs(View, { style: styles.card, children: [_jsx(Text, { style: styles.title, children: "Saved History" }), _jsx(Text, { style: styles.body, children: "Authenticated users can review past analyses, download results, and see whether an upload was rejected, completed, or needs clarification." }), _jsx(View, { style: styles.rows, children: mockHistory.map((entry) => (_jsxs(View, { style: styles.row, children: [_jsxs(View, { style: styles.rowText, children: [_jsx(Text, { style: styles.rowTitle, children: entry.title }), _jsx(Text, { style: styles.rowStatus, children: entry.status })] }), _jsx(Text, { style: styles.rowValue, children: entry.calories ? `${entry.calories} kcal` : "Blocked" })] }, entry.id))) })] }));
}
const styles = StyleSheet.create({
    card: {
        backgroundColor: "#203328",
        borderRadius: 24,
        padding: 20,
        gap: 14,
    },
    title: {
        fontSize: 22,
        fontWeight: "800",
        color: "#f6f4ee",
    },
    body: {
        fontSize: 15,
        lineHeight: 22,
        color: "#d2dbd4",
    },
    rows: {
        gap: 12,
    },
    row: {
        backgroundColor: "rgba(255, 255, 255, 0.08)",
        borderRadius: 18,
        padding: 14,
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        gap: 12,
    },
    rowText: {
        flex: 1,
        gap: 4,
    },
    rowTitle: {
        fontSize: 15,
        fontWeight: "700",
        color: "#ffffff",
    },
    rowStatus: {
        fontSize: 13,
        color: "#b6c6bb",
    },
    rowValue: {
        fontSize: 14,
        fontWeight: "700",
        color: "#d6f8d4",
    },
});
