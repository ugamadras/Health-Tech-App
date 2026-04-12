import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import React from "react";
import { SafeAreaView, ScrollView, StatusBar, StyleSheet, Text } from "react-native";
import { DisclaimerBanner } from "./src/components/DisclaimerBanner";
import { HistoryScreen } from "./src/screens/HistoryScreen";
import { UploadScreen } from "./src/screens/UploadScreen";
export default function App() {
    return (_jsxs(SafeAreaView, { style: styles.safeArea, children: [_jsx(StatusBar, { barStyle: "dark-content" }), _jsxs(ScrollView, { contentContainerStyle: styles.container, children: [_jsx(Text, { style: styles.eyebrow, children: "Meal Analyzer" }), _jsx(Text, { style: styles.title, children: "Daily meal nutrition estimates, built for general wellness." }), _jsx(Text, { style: styles.subtitle, children: "Capture a meal, reject unsafe or non-food uploads, and return grounded calorie and nutrient estimates with clear guardrails." }), _jsx(DisclaimerBanner, {}), _jsx(UploadScreen, {}), _jsx(HistoryScreen, {})] })] }));
}
const styles = StyleSheet.create({
    safeArea: {
        flex: 1,
        backgroundColor: "#f7f4ed",
    },
    container: {
        padding: 24,
        gap: 20,
    },
    eyebrow: {
        fontSize: 14,
        letterSpacing: 1.6,
        textTransform: "uppercase",
        color: "#7a5c3e",
        fontWeight: "700",
    },
    title: {
        fontSize: 30,
        lineHeight: 36,
        color: "#1d2a22",
        fontWeight: "800",
    },
    subtitle: {
        fontSize: 16,
        lineHeight: 24,
        color: "#42534a",
    },
});
