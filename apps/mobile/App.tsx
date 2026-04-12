import React from "react";
import { SafeAreaView, ScrollView, StatusBar, StyleSheet, Text, View } from "react-native";
import { DisclaimerBanner } from "./src/components/DisclaimerBanner";
import { HistoryScreen } from "./src/screens/HistoryScreen";
import { UploadScreen } from "./src/screens/UploadScreen";

export default function App() {
  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="dark-content" />
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.eyebrow}>Meal Analyzer</Text>
        <Text style={styles.title}>Daily meal nutrition estimates, built for general wellness.</Text>
        <Text style={styles.subtitle}>
          Capture a meal, reject unsafe or non-food uploads, and return grounded calorie and nutrient
          estimates with clear guardrails.
        </Text>
        <DisclaimerBanner />
        <UploadScreen />
        <HistoryScreen />
      </ScrollView>
    </SafeAreaView>
  );
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

