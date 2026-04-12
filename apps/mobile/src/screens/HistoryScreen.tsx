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
  return (
    <View style={styles.card}>
      <Text style={styles.title}>Saved History</Text>
      <Text style={styles.body}>
        Authenticated users can review past analyses, download results, and see whether an upload was
        rejected, completed, or needs clarification.
      </Text>
      <View style={styles.rows}>
        {mockHistory.map((entry) => (
          <View key={entry.id} style={styles.row}>
            <View style={styles.rowText}>
              <Text style={styles.rowTitle}>{entry.title}</Text>
              <Text style={styles.rowStatus}>{entry.status}</Text>
            </View>
            <Text style={styles.rowValue}>{entry.calories ? `${entry.calories} kcal` : "Blocked"}</Text>
          </View>
        ))}
      </View>
    </View>
  );
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
