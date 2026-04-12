import React from "react";
import { StyleSheet, Text, View } from "react-native";

const DISCLAIMER =
  "These nutrition estimates are for general wellness and informational purposes only. They are not medical advice and should not be used to diagnose, treat, cure, or prevent any condition.";

export function DisclaimerBanner() {
  return (
    <View style={styles.container}>
      <Text style={styles.label}>Important</Text>
      <Text style={styles.text}>{DISCLAIMER}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#fef6d8",
    borderRadius: 18,
    padding: 16,
    borderWidth: 1,
    borderColor: "#d7b94b",
    gap: 8,
  },
  label: {
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 1.2,
    textTransform: "uppercase",
    color: "#7b5f00",
  },
  text: {
    fontSize: 14,
    lineHeight: 20,
    color: "#5c4a17",
  },
});

