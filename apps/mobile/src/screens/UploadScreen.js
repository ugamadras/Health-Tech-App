import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
const rejectionReasons = [
    "Reject non-food uploads before analysis.",
    "Reject unsafe image or text content, including sexual content.",
    "Ask for clarification when the photo is food-adjacent but uncertain.",
];
export function UploadScreen() {
    return (_jsxs(View, { style: styles.card, children: [_jsx(Text, { style: styles.title, children: "Capture And Validate" }), _jsx(Text, { style: styles.body, children: "The mobile client performs lightweight file checks, then sends the upload for moderation, food validation, and deterministic nutrition analysis." }), _jsx(View, { style: styles.list, children: rejectionReasons.map((reason) => (_jsx(Text, { style: styles.listItem, children: `\u2022 ${reason}` }, reason))) }), _jsxs(View, { style: styles.actions, children: [_jsx(Pressable, { style: styles.primaryButton, children: _jsx(Text, { style: styles.primaryButtonText, children: "Take Meal Photo" }) }), _jsx(Pressable, { style: styles.secondaryButton, children: _jsx(Text, { style: styles.secondaryButtonText, children: "Upload From Library" }) })] })] }));
}
const styles = StyleSheet.create({
    card: {
        backgroundColor: "#ffffff",
        borderRadius: 24,
        padding: 20,
        gap: 14,
        shadowColor: "#1d2a22",
        shadowOpacity: 0.08,
        shadowRadius: 20,
        shadowOffset: { width: 0, height: 8 },
    },
    title: {
        fontSize: 22,
        fontWeight: "800",
        color: "#203328",
    },
    body: {
        fontSize: 15,
        lineHeight: 22,
        color: "#415248",
    },
    list: {
        gap: 8,
    },
    listItem: {
        fontSize: 14,
        lineHeight: 20,
        color: "#5b6a60",
    },
    actions: {
        gap: 12,
    },
    primaryButton: {
        borderRadius: 16,
        paddingVertical: 14,
        paddingHorizontal: 16,
        backgroundColor: "#2d6b45",
    },
    primaryButtonText: {
        color: "#ffffff",
        textAlign: "center",
        fontWeight: "700",
    },
    secondaryButton: {
        borderRadius: 16,
        paddingVertical: 14,
        paddingHorizontal: 16,
        backgroundColor: "#e8efe9",
    },
    secondaryButtonText: {
        color: "#284734",
        textAlign: "center",
        fontWeight: "700",
    },
});
